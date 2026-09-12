"""Phase 0C velocity sweep: parameter wiring and end-to-end sanity on the fixture."""

from __future__ import annotations

from brain.sensory import looming
from experiments import phase0c_velocity_sweep as sweep
from experiments.phase_0b import locked_parameters as P
from simulation import session


def test_velocities_match_spec():
    assert sweep.VELOCITIES_CM_S == (10.0, 20.0, 40.0, 80.0)


def test_each_velocity_produces_a_distinct_stimulus():
    stimulus_kwargs = dict(P.locked_stimulus_kwargs())
    params = [looming.looming(approach_velocity_cm_s=v, **stimulus_kwargs) for v in sweep.VELOCITIES_CM_S]
    velocities = [p.approach_velocity_cm_s for p in params]
    assert velocities == [10.0, 20.0, 40.0, 80.0]
    # every other field stays identical across conditions -- only velocity varies
    for p in params[1:]:
        assert p.object_radius_cm == params[0].object_radius_cm
        assert p.initial_distance_cm == params[0].initial_distance_cm
        assert p.stimulus_duration_ms == params[0].stimulus_duration_ms


def test_ledger_parameters_include_velocity_list():
    params = sweep._ledger_parameters()
    assert params["velocities_cm_s"] == [10.0, 20.0, 40.0, 80.0]


def test_sweep_conditions_carry_latency_fields_on_fixture(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    stimulus_kwargs = dict(P.locked_stimulus_kwargs())

    results = []
    for velocity in sweep.VELOCITIES_CM_S:
        stimulus_params = looming.looming(approach_velocity_cm_s=velocity, **stimulus_kwargs)
        result = session.run_looming_session(
            registry, connectome, stimulus_params, condition_name=f"looming_v{velocity:g}",
            **P.locked_session_kwargs(),
        )
        results.append(result)

    # Higher velocity must not respond LESS than a lower velocity that already
    # crossed the threshold, and a response that exists must have a real
    # (non-None) first-spike/trigger time.
    by_velocity = dict(zip(sweep.VELOCITIES_CM_S, results))
    r40, r80 = by_velocity[40.0], by_velocity[80.0]
    assert r40.escape_triggered and r80.escape_triggered
    assert r80.dnp01_spike_count >= r40.dnp01_spike_count
    assert r80.escape_trigger_time_ms < r40.escape_trigger_time_ms
    assert r40.first_sensory_spike_time_ms is not None
    assert r80.first_sensory_spike_time_ms < r40.first_sensory_spike_time_ms
