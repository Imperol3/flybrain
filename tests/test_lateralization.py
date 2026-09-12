"""Azimuth-based hemifield stimulus routing and DNa02-L/R steering readout (Phase 0D).

Prerequisite gap this closes: azimuth_deg was previously stored on
LoomingStimulusParams but never used anywhere in the sensory encoding —
every stimulus drove LC4/LPLC2 bilaterally regardless of the angle it
claimed to come from. That made any steering/lateralization experiment
meaningless before this was fixed.
"""

from __future__ import annotations

from brain.sensory import looming
from simulation import session


def test_negative_azimuth_drives_left_side_only(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    params = looming.looming(azimuth_deg=-45.0, simulation_duration_ms=300.0)
    result = session.run_looming_session(registry, connectome, params, condition_name="left")

    lat = result.lateralized
    assert lat["lc4_left_spike_count"] > 0
    assert lat["lc4_right_spike_count"] == 0
    assert lat["lplc2_left_spike_count"] > 0
    assert lat["lplc2_right_spike_count"] == 0


def test_positive_azimuth_drives_right_side_only(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    params = looming.looming(azimuth_deg=45.0, simulation_duration_ms=300.0)
    result = session.run_looming_session(registry, connectome, params, condition_name="right")

    lat = result.lateralized
    assert lat["lc4_right_spike_count"] > 0
    assert lat["lc4_left_spike_count"] == 0
    assert lat["lplc2_right_spike_count"] > 0
    assert lat["lplc2_left_spike_count"] == 0


def test_zero_azimuth_drives_both_sides_symmetrically(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    params = looming.looming(azimuth_deg=0.0, simulation_duration_ms=300.0)
    result = session.run_looming_session(registry, connectome, params, condition_name="center")

    lat = result.lateralized
    assert lat["lc4_left_spike_count"] == lat["lc4_right_spike_count"] > 0
    assert lat["steering_signal_hz"] == 0.0


def test_bilateral_reported_count_reflects_full_population_not_just_driven_side(built_fixture_connectome):
    """The top-level lc4_spike_count must keep ONE stable meaning (spikes
    across the FULL bilateral population) regardless of azimuth — it must
    equal the sum of the lateralized left+right breakdown for that SAME
    run (not be silently narrowed to only the driven side), even though a
    unilateral run's total naturally differs from a bilateral run's total
    (recurrent network dynamics are not simply additive across sides).
    """
    registry, connectome, _manifest = built_fixture_connectome
    left = session.run_looming_session(
        registry, connectome, looming.looming(azimuth_deg=-45.0, simulation_duration_ms=300.0), condition_name="l"
    )
    assert left.lc4_spike_count == left.lateralized["lc4_left_spike_count"] + left.lateralized["lc4_right_spike_count"]


def test_steering_signal_sign_convention(built_fixture_connectome):
    """Positive steering_signal_hz = left DNa02 more active = leftward steering;
    negative = right DNa02 more active = rightward steering."""
    registry, connectome, _manifest = built_fixture_connectome
    left_stim = session.run_looming_session(
        registry, connectome, looming.looming(azimuth_deg=-45.0, simulation_duration_ms=300.0), condition_name="l"
    )
    right_stim = session.run_looming_session(
        registry, connectome, looming.looming(azimuth_deg=45.0, simulation_duration_ms=300.0), condition_name="r"
    )
    assert left_stim.lateralized["steering_signal_hz"] > 0
    assert right_stim.lateralized["steering_signal_hz"] < 0
    assert left_stim.lateralized["dna02_right_spike_count"] == 0
    assert right_stim.lateralized["dna02_left_spike_count"] == 0


def test_lateralized_empty_when_dna02_population_missing():
    """If a connectome build has no DNa02_L/DNa02_R (e.g. no side data),
    the steering readout is omitted rather than raising or guessing.
    """
    from simulation.session import _steering_readout
    from brain.neurons.registry import NeuronRegistry

    class FakeSimResult:
        def spike_count_for(self, indices):
            return 0

    registry = NeuronRegistry(root_ids=(1, 2), populations={"LC4": (1, 2)}, dataset_version="test")
    assert _steering_readout(registry, FakeSimResult(), duration_ms=300.0) == {}
