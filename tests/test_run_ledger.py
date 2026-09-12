"""Run ledger: the "no silent parameter tuning" mechanism for Phase 0B."""

import pytest

from simulation import run_ledger


def test_first_run_establishes_baseline(isolated_derived_paths):
    record = run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    assert record.run_id == "RUN 001"
    assert record.run_number == 1
    assert record.changed_from_previous is False
    assert record.change_reason is None


def test_identical_params_do_not_require_a_reason(isolated_derived_paths):
    run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    second = run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    assert second.run_id == "RUN 002"
    assert second.changed_from_previous is False


def test_changed_params_without_reason_is_refused(isolated_derived_paths):
    run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    with pytest.raises(run_ledger.SilentParameterChangeError):
        run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 32.0})


def test_changed_params_with_reason_is_recorded(isolated_derived_paths):
    run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    third = run_ledger.record_run(
        "exp_a", "test_fixture_v0", {"gain": 32.0}, change_reason="doubling gain to test real-scale drive"
    )
    assert third.run_id == "RUN 002"
    assert third.changed_from_previous is True
    assert third.change_reason == "doubling gain to test real-scale drive"


def test_experiments_have_independent_run_numbering(isolated_derived_paths):
    a1 = run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    b1 = run_ledger.record_run("exp_b", "test_fixture_v0", {"gain": 1.0})
    assert a1.run_id == "RUN 001"
    assert b1.run_id == "RUN 001"


def test_get_run_history_returns_all_runs_in_order(isolated_derived_paths):
    run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    history = run_ledger.get_run_history("exp_a")
    assert [h["run_number"] for h in history] == [1, 2]


def test_ledger_persists_across_calls_via_file(isolated_derived_paths):
    run_ledger.record_run("exp_a", "test_fixture_v0", {"gain": 16.0})
    last = run_ledger.get_last_run("exp_a")
    assert last is not None
    assert last["run_id"] == "RUN 001"
