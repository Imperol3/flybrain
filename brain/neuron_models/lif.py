"""Vectorized leaky integrate-and-fire (LIF) neuron model math.

Pure state-update functions, no connectome/stimulus/timing-loop concerns —
those live in simulation.engine.lif_engine. This module only knows how one
population of neurons' (v, g, refractory) state evolves by one timestep
given a synaptic conductance input.

Model (attributed to Shiu et al. 2024; see config.LIF_PARAMS for the
provenance note and citation):

    dv/dt = (v_reset - v + g) / tau_membrane      (only while not refractory)
    dg/dt = -g / tau_synapse

Conductance g is advanced by an exact exponential decay (stable for any
timestep) and then incremented by whatever synaptic input arrived this step
(computed upstream by the engine, after applying synaptic delay and the
w_synapse_mV per-synapse scaling). The membrane voltage is advanced by a
forward-Euler step of the above ODE, clamped to v_reset during the
refractory period, and reset to v_reset on spike.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import config


@dataclass
class LifState:
    v: np.ndarray                 # membrane potential, mV
    g: np.ndarray                 # synaptic conductance state, mV
    refractory_remaining_ms: np.ndarray

    @classmethod
    def initial(cls, n_neurons: int, v_reset_mV: float) -> "LifState":
        return cls(
            v=np.full(n_neurons, v_reset_mV, dtype=np.float64),
            g=np.zeros(n_neurons, dtype=np.float64),
            refractory_remaining_ms=np.zeros(n_neurons, dtype=np.float64),
        )


def step(
    state: LifState,
    synaptic_input: np.ndarray,
    dt_ms: float,
    params: dict = config.LIF_PARAMS,
) -> tuple[LifState, np.ndarray]:
    """Advance all neurons by one timestep.

    `synaptic_input` is the conductance increment (mV) delivered to each
    neuron this step (already delay-shifted and weight-scaled by the caller).

    Returns (new_state, spiked) where `spiked` is a boolean array.
    """
    v_reset = params["v_reset_mV"]
    v_threshold = params["v_threshold_mV"]
    tau_mbr = params["tau_membrane_ms"]
    tau_syn = params["tau_synapse_ms"]
    t_refractory = params["t_refractory_ms"]

    decay = np.exp(-dt_ms / tau_syn)
    g_new = state.g * decay + synaptic_input

    not_refractory = state.refractory_remaining_ms <= 0.0
    dv = (dt_ms / tau_mbr) * (v_reset - state.v + g_new)
    v_candidate = np.where(not_refractory, state.v + dv, v_reset)

    spiked = not_refractory & (v_candidate >= v_threshold)
    v_new = np.where(spiked, v_reset, v_candidate)

    refractory_new = np.where(
        spiked,
        t_refractory,
        np.maximum(state.refractory_remaining_ms - dt_ms, 0.0),
    )

    return LifState(v=v_new, g=g_new, refractory_remaining_ms=refractory_new), spiked
