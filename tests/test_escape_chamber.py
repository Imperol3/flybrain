"""Geometry and navigation checks for the bounded escape chamber."""

import scipy.sparse as sp

from brain.neurons.registry import NeuronRegistry
from simulation.closed_loop import BodyState, ThreatState
from simulation.escape_chamber import EscapeChamberSession


def _trial() -> EscapeChamberSession:
    registry = NeuronRegistry(
        root_ids=(1, 2, 3, 4, 5),
        populations={
            "LC4": (1,),
            "LPLC2": (2,),
            "DNp01": (3,),
            "DNa02_L": (4,),
            "DNa02_R": (5,),
        },
        dataset_version="test",
    )
    return EscapeChamberSession(
        registry=registry,
        connectome=sp.csr_matrix((5, 5)),
        body=BodyState(),
        threat=ThreatState(x_cm=0.0, z_cm=20.0, vz_cm_s=-6.0),
        maximum_duration_ms=12000.0,
    )


def test_north_wall_only_allows_exit_opening():
    trial = _trial()
    _, blocked_z, collided = trial._resolve_position(0.0, -15.0, 0.0, -16.2)
    assert collided
    assert blocked_z > trial.chamber.north_z_cm

    exit_x = trial.chamber.exit_x_cm
    allowed_x, allowed_z, collided = trial._resolve_position(exit_x, -15.0, exit_x, -16.2)
    assert not collided
    assert allowed_x == exit_x
    assert allowed_z == -16.2


def test_navigation_layer_can_route_an_activated_escape_to_the_exit():
    trial = _trial()
    trial.escape_latched = True
    for _ in range(500):
        trial.elapsed_ms += 25.0
        trial._move(steering_hz=0.0, escape_now=False, dt_s=0.025)
        if trial.escaped:
            break

    assert trial.escaped
    assert trial.collision_count >= 0
    assert trial.path_length_cm > trial._metrics()["optimal_path_cm"]
    assert 0.0 < trial._metrics()["route_efficiency"] <= 1.0
    assert trial.body.y_cm == trial.decoder.takeoff_height_cm
