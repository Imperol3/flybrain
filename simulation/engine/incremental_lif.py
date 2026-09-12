"""State-preserving segments for interactive, closed-loop LIF simulation.

The formal experiment runner remains in ``lif_engine.run``. This module is
the interactive counterpart: it keeps membrane voltage, synaptic state and
the delay buffer alive between short windows so the viewer does not restart
the brain every time the body moves.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

import config
from brain.neuron_models.lif import LifState, step as lif_step
from simulation.engine.lif_engine import SimulationResult


@dataclass
class IncrementalLifState:
    lif_state: LifState
    delay_buffer: deque[np.ndarray]
    elapsed_ms: float = 0.0


def initialize(n_neurons: int, dt_ms: float, params: dict) -> IncrementalLifState:
    delay_steps = max(1, int(round(params["t_synaptic_delay_ms"] / dt_ms)))
    return IncrementalLifState(
        lif_state=LifState.initial(n_neurons, params["v_reset_mV"]),
        delay_buffer=deque(
            (np.zeros(n_neurons, dtype=np.float64) for _ in range(delay_steps)),
            maxlen=delay_steps,
        ),
    )


def mask_outbound(connectome: sp.csr_matrix, n_neurons: int, silenced_indices=()) -> sp.csr_matrix:
    """Return a reusable CSR matrix with selected outbound rows suppressed."""
    if not silenced_indices:
        return connectome
    mask = np.ones(n_neurons, dtype=connectome.dtype)
    mask[list(silenced_indices)] = 0
    return (sp.diags(mask, dtype=connectome.dtype) @ connectome).tocsr()


def run_segment(
    *,
    connectome: sp.csr_matrix,
    n_neurons: int,
    dataset_version: str,
    state: IncrementalLifState,
    duration_ms: float,
    dt_ms: float = config.DEFAULT_TIMESTEP_MS,
    external_input_fn=None,
    params: dict = config.LIF_PARAMS,
    seed: int = 0,
) -> tuple[SimulationResult, IncrementalLifState]:
    """Advance an existing network state without resetting it."""
    np.random.default_rng(seed)
    n_steps = int(round(duration_ms / dt_ms))
    w_synapse = params["w_synapse_mV"]
    spike_times: list[float] = []
    spike_indices: list[int] = []

    for step_index in range(n_steps):
        recurrent_input = state.delay_buffer.popleft()
        external_input = (
            external_input_fn(step_index, dt_ms)
            if external_input_fn is not None
            else np.zeros(n_neurons, dtype=np.float64)
        )
        state.lif_state, spiked = lif_step(
            state.lif_state, recurrent_input + external_input, dt_ms, params
        )
        spiking_idx = np.flatnonzero(spiked)
        if spiking_idx.size:
            local_time_ms = step_index * dt_ms
            spike_times.extend([local_time_ms] * spiking_idx.size)
            spike_indices.extend(spiking_idx.tolist())
            contribution = (
                np.asarray(connectome[spiking_idx, :].sum(axis=0)).reshape(-1)
                * w_synapse
            )
        else:
            contribution = np.zeros(n_neurons, dtype=np.float64)
        state.delay_buffer.append(contribution)

    state.elapsed_ms += duration_ms
    return (
        SimulationResult(
            dataset_version=dataset_version,
            n_neurons=n_neurons,
            dt_ms=dt_ms,
            duration_ms=duration_ms,
            seed=seed,
            spike_times_ms=np.asarray(spike_times, dtype=np.float64),
            spike_neuron_indices=np.asarray(spike_indices, dtype=np.int64),
        ),
        state,
    )
