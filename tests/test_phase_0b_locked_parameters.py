"""Regression test for a real bug caught during the first real-data Phase 0B
run: locked_stimulus_kwargs() used to bake approach_velocity_cm_s=40.0
directly into the shared kwargs dict, which defeated looming.receding()'s
and looming.static()'s own setdefault() calls (the key was already present,
so their defaults never fired) — silently turning every "condition" into
looming. Caught because receding/static produced IDENTICAL spike counts to
looming on the real connectome, which should never happen.
"""

from __future__ import annotations

from brain.sensory import looming
from experiments.phase_0b import locked_parameters as P


def test_locked_stimulus_kwargs_excludes_velocity():
    kwargs = P.locked_stimulus_kwargs()
    assert "approach_velocity_cm_s" not in kwargs


def test_looming_receding_static_have_different_velocities_under_locked_kwargs():
    looming_params = looming.looming(**P.locked_stimulus_kwargs())
    receding_params = looming.receding(**P.locked_stimulus_kwargs())
    static_params = looming.static(**P.locked_stimulus_kwargs())

    assert looming_params.approach_velocity_cm_s > 0
    assert receding_params.approach_velocity_cm_s < 0
    assert static_params.approach_velocity_cm_s == 0
    assert len({looming_params.approach_velocity_cm_s, receding_params.approach_velocity_cm_s, static_params.approach_velocity_cm_s}) == 3


def test_looming_receding_static_produce_different_drive_signals():
    dt_ms = 0.5
    looming_drive = looming.generate_drive_signal(dt_ms, looming.looming(**P.locked_stimulus_kwargs()))
    receding_drive = looming.generate_drive_signal(dt_ms, looming.receding(**P.locked_stimulus_kwargs()))
    static_drive = looming.generate_drive_signal(dt_ms, looming.static(**P.locked_stimulus_kwargs()))

    assert looming_drive.sum() > 0
    assert receding_drive.sum() == 0
    assert static_drive.sum() == 0
