"""Generic sensory-drive-signal -> injected-conductance encoder.

This is the seam between "external stimulus" (brain.sensory.looming, or any
future stimulus module) and the neuron model: it knows nothing about looming
specifically, only how to take a per-timestep scalar drive signal and turn
it into an injected conductance vector on named neuron populations, resolved
through brain.neurons.registry. Keeping this generic means a new stimulus
type only needs to produce a drive signal array; it does not need to know
about the connectome or simulation engine.
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def make_external_input_fn(
    drive_signal: np.ndarray,
    population_indices: dict[str, np.ndarray],
    n_neurons: int,
    gain_mV_per_unit: dict[str, float] | float = 1.0,
) -> Callable[[int, float], np.ndarray]:
    """Build the `external_input_fn(step, dt_ms)` callback consumed by simulation.engine.lif_engine.run.

    `population_indices`: population name -> array of connectome matrix indices to drive.
    `gain_mV_per_unit`: either one gain applied to every listed population, or a
      per-population dict. This is an exposed interface parameter, not a
      biological constant — see docs/BIOLOGICAL_ASSUMPTIONS.md.
    """
    if isinstance(gain_mV_per_unit, (int, float)):
        gains = {name: float(gain_mV_per_unit) for name in population_indices}
    else:
        gains = dict(gain_mV_per_unit)
        missing = set(population_indices) - set(gains)
        if missing:
            raise ValueError(f"Missing gain_mV_per_unit entries for population(s): {sorted(missing)}")

    n_steps = len(drive_signal)

    def external_input_fn(step: int, _dt_ms: float) -> np.ndarray:
        vec = np.zeros(n_neurons, dtype=np.float64)
        if step >= n_steps:
            return vec
        value = drive_signal[step]
        if value == 0.0:
            return vec
        for name, indices in population_indices.items():
            vec[indices] = value * gains[name]
        return vec

    return external_input_fn
