"""Phase 0D azimuth sweep: parameter wiring and end-to-end sanity on the fixture."""

from __future__ import annotations

from brain.sensory import looming
from experiments import phase0d_azimuth_sweep as sweep
from experiments.phase_0b import locked_parameters as P
from simulation import session


def test_azimuths_match_spec():
    assert sweep.AZIMUTHS_DEG == (-45.0, -30.0, 0.0, 30.0, 45.0)


def test_velocity_held_fixed_at_reference():
    assert sweep.FIXED_VELOCITY_CM_S == 40.0


def test_each_azimuth_produces_a_distinct_stimulus():
    stimulus_kwargs = dict(P.locked_stimulus_kwargs())
    stimulus_kwargs["approach_velocity_cm_s"] = sweep.FIXED_VELOCITY_CM_S
    stimulus_kwargs.pop("azimuth_deg", None)
    params = [looming.looming(azimuth_deg=az, **stimulus_kwargs) for az in sweep.AZIMUTHS_DEG]
    azimuths = [p.azimuth_deg for p in params]
    assert azimuths == [-45.0, -30.0, 0.0, 30.0, 45.0]
    for p in params:
        assert p.approach_velocity_cm_s == 40.0  # velocity held fixed, only azimuth varies


def test_ledger_parameters_include_azimuth_list():
    params = sweep._ledger_parameters()
    assert params["azimuths_deg"] == [-45.0, -30.0, 0.0, 30.0, 45.0]
    assert params["fixed_velocity_cm_s"] == 40.0


def test_sweep_produces_sign_correct_steering_on_fixture(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    stimulus_kwargs = dict(P.locked_stimulus_kwargs())
    stimulus_kwargs["approach_velocity_cm_s"] = sweep.FIXED_VELOCITY_CM_S
    stimulus_kwargs.pop("azimuth_deg", None)

    results = {}
    for az in sweep.AZIMUTHS_DEG:
        params = looming.looming(azimuth_deg=az, **stimulus_kwargs)
        results[az] = session.run_looming_session(registry, connectome, params, condition_name=f"az{az:g}")

    assert results[-45.0].lateralized["steering_signal_hz"] > 0
    assert results[45.0].lateralized["steering_signal_hz"] < 0
    assert results[0.0].lateralized["steering_signal_hz"] == 0.0
