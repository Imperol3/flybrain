"""Composes the four architecture layers (data / neuron model / interface / interpretation)
for one deterministic simulation run.

This is the ONLY module allowed to import from all four layers at once
(brief section 15). Everything downstream (experiments/) should go through
here rather than reaching into brain.* or simulation.engine.* directly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

import config
from brain.motor import descending
from brain.neurons.registry import NeuronRegistry
from brain.sensory import encoders, looming
from simulation.engine import lif_engine


@dataclass(frozen=True)
class SessionResult:
    condition_name: str
    dataset_version: str
    seed: int
    parameters: dict
    lc4_spike_count: int
    lplc2_spike_count: int
    dnp01_spike_count: int
    dnp01_peak_firing_rate_hz: float
    n_active_neurons: int
    simulation_duration_ms: float
    wall_clock_runtime_s: float
    escape_triggered: bool
    silenced_populations: tuple[str, ...] = field(default_factory=tuple)
    time_series: tuple[dict, ...] = field(default_factory=tuple)
    first_sensory_spike_time_ms: float | None = None
    first_dnp01_spike_time_ms: float | None = None
    escape_trigger_time_ms: float | None = None
    lateralized: dict = field(default_factory=dict)


def _population_indices(registry: NeuronRegistry, names) -> dict[str, np.ndarray]:
    return {name: registry.population_indices(name) for name in names}


def _flatten_indices(index_map: dict[str, np.ndarray]) -> tuple[int, ...]:
    if not index_map:
        return ()
    return tuple(int(i) for arr in index_map.values() for i in arr)


def _lateralized_sensory_indices(
    registry: NeuronRegistry, sensory_populations: tuple[str, ...], azimuth_deg: float
) -> dict[str, np.ndarray]:
    """Coarse hemifield model for routing sensory drive by stimulus azimuth.

    Negative azimuth -> stimulate only that population's LEFT-side neurons
    (registry population "{name}_L"); positive -> RIGHT-side only; azimuth
    exactly 0, or no side-split available for that population, -> both
    sides (unchanged from pre-Phase-0D behavior).

    This is a deliberate, documented SIMPLIFICATION — a binary hemifield
    split, not a retinotopic/receptive-field model of the visual system.
    See docs/BIOLOGICAL_ASSUMPTIONS.md for the decision record. It exists
    because azimuth_deg was previously stored but never used anywhere in
    the sensory encoding (every stimulus drove both eyes identically
    regardless of the angle it claimed to come from) — a prerequisite gap
    for any steering/lateralization experiment (Phase 0D).
    """
    indices: dict[str, np.ndarray] = {}
    for name in sensory_populations:
        qualified = None
        if azimuth_deg < 0:
            qualified = f"{name}_L"
        elif azimuth_deg > 0:
            qualified = f"{name}_R"
        if qualified and qualified in registry.populations:
            indices[name] = registry.population_indices(qualified)
        else:
            indices[name] = registry.population_indices(name)
    return indices


def _lateralized_sensory_readout(registry: NeuronRegistry, sim_result, sensory_populations: tuple[str, ...]) -> dict:
    """Left/right spike counts for each sensory population, independent of
    which side was actually driven this run — lets a caller confirm the
    hemifield routing worked (the undriven side stayed silent) rather than
    just trusting it did.
    """
    out: dict = {}
    for name in sensory_populations:
        left_key, right_key = f"{name}_L", f"{name}_R"
        if left_key in registry.populations:
            out[f"{name.lower()}_left_spike_count"] = sim_result.spike_count_for(
                registry.population_indices(left_key)
            )
        if right_key in registry.populations:
            out[f"{name.lower()}_right_spike_count"] = sim_result.spike_count_for(
                registry.population_indices(right_key)
            )
    return out


def _steering_readout(registry: NeuronRegistry, sim_result, duration_ms: float) -> dict:
    """DNa02_L/DNa02_R spike counts, mean firing rates, and their
    difference (the steering signal) — see brain.motor.descending for why
    this is kept as an interpretation, not baked into the neuron model.
    Returns {} if DNa02_L/DNa02_R aren't identifiable in this connectome
    build (e.g. an older fixture without side data).
    """
    if "DNa02_L" not in registry.populations or "DNa02_R" not in registry.populations:
        return {}
    left_indices = registry.population_indices("DNa02_L")
    right_indices = registry.population_indices("DNa02_R")
    duration_s = duration_ms / 1000.0
    left_count = sim_result.spike_count_for(left_indices)
    right_count = sim_result.spike_count_for(right_indices)
    left_rate = left_count / len(left_indices) / duration_s
    right_rate = right_count / len(right_indices) / duration_s
    return {
        "dna02_left_spike_count": left_count,
        "dna02_right_spike_count": right_count,
        "dna02_left_firing_rate_hz": left_rate,
        "dna02_right_firing_rate_hz": right_rate,
        "steering_signal_hz": left_rate - right_rate,
    }


def run_looming_session(
    registry: NeuronRegistry,
    connectome: sp.csr_matrix,
    stimulus_params: looming.LoomingStimulusParams,
    *,
    condition_name: str = "looming",
    dt_ms: float = config.DEFAULT_TIMESTEP_MS,
    sensory_populations: tuple[str, ...] = ("LC4", "LPLC2"),
    silenced_populations: tuple[str, ...] = (),
    gain_mV_per_unit: dict[str, float] | float = 16.0,
    lif_params: dict = config.LIF_PARAMS,
    escape_threshold_rate_hz: float = descending.DEFAULT_ESCAPE_RATE_THRESHOLD_HZ,
    escape_window_ms: float = descending.DEFAULT_ESCAPE_WINDOW_MS,
    time_series_bin_ms: float = config.DEFAULT_TIME_SERIES_BIN_MS,
) -> SessionResult:
    """Run one deterministic looming (or receding/static) session end to end.

    Deterministic given (connectome, lif_params, stimulus_params, seed,
    dt_ms/duration): the RNG seed is threaded through
    simulation.engine.lif_engine.run for forward compatibility even though
    the V0 model has no stochastic term (see docs/BIOLOGICAL_ASSUMPTIONS.md).
    """
    sensory_indices = _lateralized_sensory_indices(registry, sensory_populations, stimulus_params.azimuth_deg)
    dnp01_indices = registry.population_indices(config.DESCENDING_OUTPUT_POPULATION)
    silenced_indices = _flatten_indices(_population_indices(registry, silenced_populations))

    drive_signal = looming.generate_drive_signal(dt_ms, stimulus_params)
    external_input_fn = encoders.make_external_input_fn(
        drive_signal, sensory_indices, registry.n_neurons, gain_mV_per_unit=gain_mV_per_unit
    )

    start = time.perf_counter()
    sim_result = lif_engine.run(
        connectome=connectome,
        n_neurons=registry.n_neurons,
        dataset_version=registry.dataset_version,
        dt_ms=dt_ms,
        duration_ms=stimulus_params.simulation_duration_ms,
        seed=stimulus_params.seed,
        external_input_fn=external_input_fn,
        silenced_indices=silenced_indices,
        params=lif_params,
    )
    wall_clock_s = time.perf_counter() - start

    escape_obs = descending.interpret_descending_activity(
        sim_result, dnp01_indices, threshold_rate_hz=escape_threshold_rate_hz, window_ms=escape_window_ms
    )

    # Reporting always uses the FULL bilateral population, independent of
    # which side was actually driven (that's `sensory_indices` above) — so
    # lc4_spike_count etc. keep one stable meaning regardless of azimuth.
    # The lateralized L/R breakdown lives in `lateralized`, not by silently
    # narrowing these fields.
    full_sensory_indices = _population_indices(registry, sensory_populations)
    lc4_indices = full_sensory_indices.get("LC4", np.array([], dtype=np.int64))
    lplc2_indices = full_sensory_indices.get("LPLC2", np.array([], dtype=np.int64))
    all_sensory_indices = _flatten_indices(full_sensory_indices)
    first_sensory_spike_time_ms = sim_result.first_spike_time_for(all_sensory_indices)

    time_series_populations = dict(full_sensory_indices)
    time_series_populations[config.DESCENDING_OUTPUT_POPULATION] = dnp01_indices
    time_series = tuple(
        sim_result.time_series(time_series_populations, bin_ms=time_series_bin_ms)
    )

    lateralized = {
        **_lateralized_sensory_readout(registry, sim_result, sensory_populations),
        **_steering_readout(registry, sim_result, stimulus_params.simulation_duration_ms),
    }

    return SessionResult(
        condition_name=condition_name,
        dataset_version=registry.dataset_version,
        seed=stimulus_params.seed,
        parameters={
            "stimulus": vars(stimulus_params),
            "dt_ms": dt_ms,
            "sensory_populations": list(sensory_populations),
            "gain_mV_per_unit": gain_mV_per_unit,
            "lif_params": dict(lif_params),
            "escape_threshold_rate_hz": escape_threshold_rate_hz,
            "escape_window_ms": escape_window_ms,
        },
        lc4_spike_count=sim_result.spike_count_for(lc4_indices),
        lplc2_spike_count=sim_result.spike_count_for(lplc2_indices),
        dnp01_spike_count=escape_obs.dnp01_spike_count,
        dnp01_peak_firing_rate_hz=escape_obs.dnp01_peak_firing_rate_hz,
        n_active_neurons=sim_result.n_active_neurons(),
        simulation_duration_ms=stimulus_params.simulation_duration_ms,
        wall_clock_runtime_s=wall_clock_s,
        escape_triggered=escape_obs.escape_triggered,
        silenced_populations=tuple(silenced_populations),
        time_series=time_series,
        first_sensory_spike_time_ms=first_sensory_spike_time_ms,
        first_dnp01_spike_time_ms=escape_obs.first_dnp01_spike_time_ms,
        escape_trigger_time_ms=escape_obs.escape_trigger_time_ms,
        lateralized=lateralized,
    )
