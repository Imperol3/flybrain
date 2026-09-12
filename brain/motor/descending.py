"""Interpretation layer: descending-neuron (DNp01 / Giant Fibre) activity -> behavioural observation.

Deliberately the ONLY place that turns raw neural output into a behavioural
claim ("escape event"). Everything upstream (simulation.engine.lif_engine)
only ever talks about spikes; nothing about "escape" leaks into the neuron
model or connectome layers, so this interpretation can be changed later
without touching the brain simulation (brief section 10/15).

The firing-rate threshold used to call something an "escape event" is a
product/behavioural decision, not a measured biological constant. It is
exposed as a parameter here and flagged as an open, documented interface
decision in docs/BIOLOGICAL_ASSUMPTIONS.md rather than silently hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_ESCAPE_RATE_THRESHOLD_HZ = 50.0
DEFAULT_ESCAPE_WINDOW_MS = 5.0


@dataclass(frozen=True)
class EscapeObservation:
    dnp01_spike_count: int
    dnp01_peak_firing_rate_hz: float
    escape_triggered: bool
    threshold_rate_hz: float
    window_ms: float
    first_dnp01_spike_time_ms: float | None = None
    escape_trigger_time_ms: float | None = None


def _escape_trigger_time_ms(simulation_result, dnp01_indices, threshold_rate_hz: float, window_ms: float) -> float | None:
    """Time (ms) of the first spike inside the first fixed window whose firing
    rate reaches threshold_rate_hz — i.e. when the escape condition first
    becomes true, using exactly the same windowing as peak_firing_rate_hz,
    not a separately-defined notion of "trigger".
    """
    indices = set(int(i) for i in dnp01_indices)
    if not indices or not simulation_result.spike_neuron_indices.size:
        return None
    mask = np.isin(simulation_result.spike_neuron_indices, list(indices))
    times = simulation_result.spike_times_ms[mask]
    if times.size == 0:
        return None

    n_bins = max(1, int(np.ceil(simulation_result.duration_ms / window_ms)))
    bin_edges = np.arange(n_bins + 1) * window_ms
    counts, _ = np.histogram(times, bins=bin_edges)
    n_pop = len(indices)
    rates = counts / n_pop / (window_ms / 1000.0)

    qualifying = np.flatnonzero(rates >= threshold_rate_hz)
    if qualifying.size == 0:
        return None
    first_bin = qualifying[0]
    bin_start, bin_end = bin_edges[first_bin], bin_edges[first_bin + 1]
    in_bin = times[(times >= bin_start) & (times < bin_end)]
    return float(in_bin.min()) if in_bin.size else None


def interpret_descending_activity(
    simulation_result,
    dnp01_indices,
    threshold_rate_hz: float = DEFAULT_ESCAPE_RATE_THRESHOLD_HZ,
    window_ms: float = DEFAULT_ESCAPE_WINDOW_MS,
) -> EscapeObservation:
    spike_count = simulation_result.spike_count_for(dnp01_indices)
    peak_rate = simulation_result.peak_firing_rate_hz(dnp01_indices, window_ms=window_ms)
    escape_triggered = peak_rate >= threshold_rate_hz
    trigger_time = (
        _escape_trigger_time_ms(simulation_result, dnp01_indices, threshold_rate_hz, window_ms)
        if escape_triggered
        else None
    )
    return EscapeObservation(
        dnp01_spike_count=spike_count,
        dnp01_peak_firing_rate_hz=peak_rate,
        escape_triggered=escape_triggered,
        threshold_rate_hz=threshold_rate_hz,
        window_ms=window_ms,
        first_dnp01_spike_time_ms=simulation_result.first_spike_time_for(dnp01_indices),
        escape_trigger_time_ms=trigger_time,
    )
