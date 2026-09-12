"""Timestep loop driving the whole-connectome LIF simulation.

Consumes the sparse connectome built by brain.connectivity.build_connectome
and steps brain.neuron_models.lif forward, injecting external sensory drive
and propagating spikes through the network with a fixed synaptic delay.

Never materializes a dense per-timestep spike matrix (brief section 7/18):
only actual spike events (time, neuron_index) are recorded, keeping memory
proportional to activity rather than to n_neurons * n_steps.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

import config
from brain.neuron_models.lif import LifState, step as lif_step


@dataclass
class SimulationResult:
    dataset_version: str
    n_neurons: int
    dt_ms: float
    duration_ms: float
    seed: int
    spike_times_ms: np.ndarray       # 1D, one entry per spike event
    spike_neuron_indices: np.ndarray  # 1D, matching spike_times_ms
    silenced_indices: tuple[int, ...] = field(default_factory=tuple)

    @property
    def n_steps(self) -> int:
        return int(round(self.duration_ms / self.dt_ms))

    def spike_counts_per_neuron(self) -> np.ndarray:
        counts = np.zeros(self.n_neurons, dtype=np.int64)
        if self.spike_neuron_indices.size:
            np.add.at(counts, self.spike_neuron_indices, 1)
        return counts

    def spike_count_for(self, indices) -> int:
        indices = set(int(i) for i in indices)
        if not self.spike_neuron_indices.size:
            return 0
        return int(np.isin(self.spike_neuron_indices, list(indices)).sum())

    def n_active_neurons(self) -> int:
        return int(np.unique(self.spike_neuron_indices).size) if self.spike_neuron_indices.size else 0

    def first_spike_time_for(self, indices) -> float | None:
        """Earliest spike time (ms) among `indices`, or None if none of them ever spiked."""
        indices = set(int(i) for i in indices)
        if not indices or not self.spike_neuron_indices.size:
            return None
        mask = np.isin(self.spike_neuron_indices, list(indices))
        times = self.spike_times_ms[mask]
        return float(times.min()) if times.size else None

    def peak_firing_rate_hz(self, indices, window_ms: float = 1.0) -> float:
        """Peak firing rate (Hz) across `indices`, in sliding windows of `window_ms`."""
        indices = set(int(i) for i in indices)
        if not indices or not self.spike_neuron_indices.size:
            return 0.0
        mask = np.isin(self.spike_neuron_indices, list(indices))
        times = self.spike_times_ms[mask]
        if times.size == 0:
            return 0.0
        n_bins = max(1, int(np.ceil(self.duration_ms / window_ms)))
        bin_edges = np.arange(n_bins + 1) * window_ms
        counts, _ = np.histogram(times, bins=bin_edges)
        peak_count = counts.max() if counts.size else 0
        n_pop = len(indices)
        # rate per neuron in this window, in Hz
        return float(peak_count / n_pop / (window_ms / 1000.0))

    def time_series(
        self, population_indices: dict[str, np.ndarray], bin_ms: float = config.DEFAULT_TIME_SERIES_BIN_MS
    ) -> list[dict]:
        """Per-bin spike counts for named populations plus total active-neuron
        count, across the whole run — e.g. [{"t_ms": 0.0, "LC4": 0, "LPLC2": 0,
        "DNp01": 0, "active_neurons": 0}, {"t_ms": 5.0, ...}, ...].

        This is the raw material for later time-series visualization (brief
        section 12: "save the time series, not just totals") and is
        deliberately independent of any interpretation threshold.
        """
        n_bins = max(1, int(np.ceil(self.duration_ms / bin_ms)))
        bin_edges = np.arange(n_bins + 1) * bin_ms
        rows = []
        for i in range(n_bins):
            t0, t1 = bin_edges[i], bin_edges[i + 1]
            if self.spike_times_ms.size:
                mask = (self.spike_times_ms >= t0) & (self.spike_times_ms < t1)
                idx_in_bin = self.spike_neuron_indices[mask]
            else:
                idx_in_bin = np.array([], dtype=np.int64)
            row = {"t_ms": float(t0)}
            for name, indices in population_indices.items():
                row[name] = int(np.isin(idx_in_bin, indices).sum()) if idx_in_bin.size else 0
            row["active_neurons"] = int(np.unique(idx_in_bin).size) if idx_in_bin.size else 0
            rows.append(row)
        return rows


def run(
    connectome: sp.csr_matrix,
    n_neurons: int,
    dataset_version: str,
    dt_ms: float = config.DEFAULT_TIMESTEP_MS,
    duration_ms: float = config.DEFAULT_SIMULATION_DURATION_MS,
    seed: int = 0,
    external_input_fn=None,
    silenced_indices: tuple[int, ...] = (),
    params: dict = config.LIF_PARAMS,
) -> SimulationResult:
    """Run the whole-connectome LIF simulation for `duration_ms`.

    `external_input_fn(step_index, dt_ms) -> np.ndarray[n_neurons]` supplies
    the externally-injected conductance for this step (e.g. from a looming
    stimulus encoder). It is added directly, without synaptic delay, since it
    represents sensory transduction rather than a network synapse.

    `silenced_indices` are neuron indices whose OUTBOUND synaptic effect is
    zeroed for this run: they still receive external/sensory drive and can
    still fire, but their spikes do not propagate to postsynaptic partners.
    This matches the brief's causal-test framing (sensory stimulation still
    occurs; only the outbound effect is removed) without mutating the base
    connectome file on disk.

    `seed` is threaded through via numpy.random.default_rng for determinism
    and forward compatibility; the V0 LIF model itself has no stochastic
    term, so the result is deterministic for any seed value given identical
    (connectome, params, stimulus, duration) — see
    docs/BIOLOGICAL_ASSUMPTIONS.md.
    """
    np.random.default_rng(seed)  # validates seed; reserved for future stochastic terms

    n_steps = int(round(duration_ms / dt_ms))
    delay_steps = max(1, int(round(params["t_synaptic_delay_ms"] / dt_ms)))
    w_synapse = params["w_synapse_mV"]

    if silenced_indices:
        # Zero the OUTBOUND rows of silenced neurons via a sparse diagonal
        # mask multiply rather than direct CSR element assignment, which
        # avoids an expensive sparsity-structure change and scales to the
        # full whole-brain connectome.
        mask = np.ones(n_neurons, dtype=connectome.dtype)
        mask[list(silenced_indices)] = 0
        connectome = (sp.diags(mask, dtype=connectome.dtype) @ connectome).tocsr()

    state = LifState.initial(n_neurons, params["v_reset_mV"])
    delay_buffer: deque[np.ndarray] = deque(
        (np.zeros(n_neurons, dtype=np.float64) for _ in range(delay_steps)),
        maxlen=delay_steps,
    )

    spike_times: list[float] = []
    spike_indices: list[int] = []

    for t in range(n_steps):
        recurrent_input = delay_buffer.popleft()
        external_input = (
            external_input_fn(t, dt_ms) if external_input_fn is not None else np.zeros(n_neurons)
        )
        total_input = recurrent_input + external_input

        state, spiked = lif_step(state, total_input, dt_ms, params)

        spiking_idx = np.flatnonzero(spiked)
        if spiking_idx.size:
            now_ms = t * dt_ms
            spike_times.extend([now_ms] * spiking_idx.size)
            spike_indices.extend(spiking_idx.tolist())
            contribution = np.asarray(
                connectome[spiking_idx, :].sum(axis=0)
            ).reshape(-1) * w_synapse
        else:
            contribution = np.zeros(n_neurons, dtype=np.float64)

        delay_buffer.append(contribution)

    return SimulationResult(
        dataset_version=dataset_version,
        n_neurons=n_neurons,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        seed=seed,
        spike_times_ms=np.array(spike_times, dtype=np.float64),
        spike_neuron_indices=np.array(spike_indices, dtype=np.int64),
        silenced_indices=tuple(silenced_indices),
    )
