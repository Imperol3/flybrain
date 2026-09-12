"""Geometry checks for the embodied closed loop."""

import math

import pytest

from simulation.closed_loop import BodyState, _wrap_degrees, threat_from_azimuth


@pytest.mark.parametrize("value, expected", [(181, -179), (-181, 179), (360, 0), (-360, 0)])
def test_wrap_degrees(value, expected):
    assert _wrap_degrees(value) == expected


def test_right_hand_threat_starts_right_and_moves_toward_fly():
    body = BodyState()
    threat = threat_from_azimuth(
        body,
        azimuth_deg=45,
        distance_cm=20,
        radius_cm=1,
        approach_velocity_cm_s=40,
    )
    assert threat.x_cm > body.x_cm
    assert threat.z_cm < body.z_cm
    before = math.hypot(threat.x_cm - body.x_cm, threat.z_cm - body.z_cm)
    threat.x_cm += threat.vx_cm_s * 0.1
    threat.z_cm += threat.vz_cm_s * 0.1
    after = math.hypot(threat.x_cm - body.x_cm, threat.z_cm - body.z_cm)
    assert after < before


def test_centered_threat_has_no_lateral_offset():
    body = BodyState()
    threat = threat_from_azimuth(
        body,
        azimuth_deg=0,
        distance_cm=20,
        radius_cm=1,
        approach_velocity_cm_s=40,
    )
    assert threat.x_cm == pytest.approx(body.x_cm)
    assert threat.z_cm < body.z_cm
