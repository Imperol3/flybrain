"""Escape-trigger-time: when did the interpreted 'escape' condition first become true,
using the SAME window/threshold logic as the escape_triggered boolean itself."""

from __future__ import annotations

import numpy as np

from brain.motor import descending
from simulation.engine.lif_engine import SimulationResult


def _result(spike_times, spike_indices, duration_ms=50.0):
    return SimulationResult(
        dataset_version="test",
        n_neurons=4,
        dt_ms=0.1,
        duration_ms=duration_ms,
        seed=0,
        spike_times_ms=np.array(spike_times, dtype=np.float64),
        spike_neuron_indices=np.array(spike_indices, dtype=np.int64),
    )


def test_no_spikes_no_trigger_time():
    result = _result([], [])
    obs = descending.interpret_descending_activity(result, dnp01_indices=[0, 1])
    assert obs.escape_triggered is False
    assert obs.escape_trigger_time_ms is None
    assert obs.first_dnp01_spike_time_ms is None


def test_first_spike_recorded_even_when_not_escape():
    # A single isolated spike: recorded as "first spike" but too sparse to
    # reach the rate threshold, so no escape trigger time.
    result = _result([10.0], [0], duration_ms=50.0)
    obs = descending.interpret_descending_activity(
        result, dnp01_indices=[0, 1], threshold_rate_hz=1000.0, window_ms=5.0
    )
    assert obs.first_dnp01_spike_time_ms == 10.0
    assert obs.escape_triggered is False
    assert obs.escape_trigger_time_ms is None


def test_escape_trigger_time_is_first_qualifying_window_not_first_spike():
    # Two DNp01 neurons. A lone early spike at t=2 doesn't reach a
    # threshold requiring both neurons active in one 5ms window; a real
    # burst starting at t=20 (two spikes within one window) does.
    result = _result([2.0, 20.0, 21.0], [0, 0, 1], duration_ms=50.0)
    obs = descending.interpret_descending_activity(
        result, dnp01_indices=[0, 1], threshold_rate_hz=200.0, window_ms=5.0
    )
    assert obs.first_dnp01_spike_time_ms == 2.0  # earliest spike overall
    assert obs.escape_triggered is True
    assert obs.escape_trigger_time_ms == 20.0  # first spike of the qualifying window, not t=2


def test_faster_stronger_drive_triggers_earlier():
    """Sanity-check the shape of comparison the Phase 0C velocity sweep relies on:
    a burst that starts earlier and is denser triggers escape earlier."""
    slow = _result([50.0, 51.0, 52.0], [0, 1, 0], duration_ms=100.0)
    fast = _result([10.0, 10.5, 11.0], [0, 1, 0], duration_ms=100.0)

    obs_slow = descending.interpret_descending_activity(slow, dnp01_indices=[0, 1], threshold_rate_hz=100.0, window_ms=5.0)
    obs_fast = descending.interpret_descending_activity(fast, dnp01_indices=[0, 1], threshold_rate_hz=100.0, window_ms=5.0)

    assert obs_slow.escape_triggered and obs_fast.escape_triggered
    assert obs_fast.escape_trigger_time_ms < obs_slow.escape_trigger_time_ms
