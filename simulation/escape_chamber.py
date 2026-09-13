"""A bounded escape experiment built around the persistent connectome loop.

The connectome still owns looming detection, escape initiation and DNa02
steering.  Geometry sensing, collision response and exit guidance are explicit
engineering layers because the current dataset does not model eyes beyond the
selected looming populations, the ventral nerve cord, muscles or aerodynamics.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np

from simulation.closed_loop import ClosedLoopSession


def _wrap_radians(value: float) -> float:
    return (value + math.pi) % (2.0 * math.pi) - math.pi


@dataclass(frozen=True)
class ChamberObstacle:
    x_cm: float
    z_cm: float
    radius_cm: float
    kind: str = "column"


@dataclass(frozen=True)
class ChamberGeometry:
    half_width_cm: float = 14.0
    north_z_cm: float = -16.0
    south_z_cm: float = 12.0
    exit_x_cm: float = -10.0
    exit_half_width_cm: float = 2.4
    body_radius_cm: float = 0.72
    sensor_range_cm: float = 7.5
    obstacles: tuple[ChamberObstacle, ...] = (
        ChamberObstacle(0.0, -1.8, 2.15, "column"),
        ChamberObstacle(-7.4, -7.4, 1.65, "column"),
        ChamberObstacle(5.8, -9.2, 2.0, "column"),
        ChamberObstacle(7.0, 3.7, 1.45, "equipment"),
    )


@dataclass
class EscapeChamberSession(ClosedLoopSession):
    """Closed-loop trial where the fly must reach one physical exit."""

    chamber: ChamberGeometry = field(default_factory=ChamberGeometry)
    collision_count: int = 0
    path_length_cm: float = 0.0
    captured: bool = False
    outcome: str = "running"
    navigation_assist: bool = True
    neural_turn_rad_s: float = 0.0
    reflex_turn_rad_s: float = 0.0
    exit_turn_rad_s: float = 0.0
    forward_clearance_cm: float = 0.0
    left_clearance_cm: float = 0.0
    right_clearance_cm: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        self._start_x = self.body.x_cm
        self._start_z = self.body.z_cm
        self._last_collision_ms = -1000.0
        self.forward_clearance_cm = self._ray_clearance(self.body.heading_rad)
        self.left_clearance_cm = self._ray_clearance(self.body.heading_rad + math.pi / 3.0)
        self.right_clearance_cm = self._ray_clearance(self.body.heading_rad - math.pi / 3.0)

    def _blocked(self, x: float, z: float) -> bool:
        c = self.chamber
        if x < -c.half_width_cm or x > c.half_width_cm or z > c.south_z_cm:
            return True
        if z < c.north_z_cm:
            return abs(x - c.exit_x_cm) > c.exit_half_width_cm
        return any(
            math.hypot(x - obstacle.x_cm, z - obstacle.z_cm)
            < obstacle.radius_cm + c.body_radius_cm
            for obstacle in c.obstacles
        )

    def _ray_clearance(self, heading: float) -> float:
        c = self.chamber
        for distance in np.linspace(0.3, c.sensor_range_cm, 30):
            x = self.body.x_cm - math.sin(heading) * float(distance)
            z = self.body.z_cm - math.cos(heading) * float(distance)
            if self._blocked(x, z):
                return float(distance)
        return c.sensor_range_cm

    def _resolve_position(self, old_x: float, old_z: float, x: float, z: float) -> tuple[float, float, bool]:
        c = self.chamber
        # Crossing the north wall is legal only through the illuminated exit.
        through_exit = (
            z < c.north_z_cm + c.body_radius_cm
            and abs(x - c.exit_x_cm) <= c.exit_half_width_cm
        )
        if through_exit:
            return x, z, False

        collided = False
        x = float(np.clip(x, -c.half_width_cm + c.body_radius_cm, c.half_width_cm - c.body_radius_cm))
        z = min(z, c.south_z_cm - c.body_radius_cm)
        if z < c.north_z_cm + c.body_radius_cm:
            z = c.north_z_cm + c.body_radius_cm
            collided = True
        if x != old_x and abs(x) >= c.half_width_cm - c.body_radius_cm - 1e-6:
            collided = True
        if z >= c.south_z_cm - c.body_radius_cm - 1e-6 and z != old_z:
            collided = True

        for obstacle in c.obstacles:
            dx, dz = x - obstacle.x_cm, z - obstacle.z_cm
            distance = math.hypot(dx, dz)
            minimum = obstacle.radius_cm + c.body_radius_cm
            if distance < minimum:
                collided = True
                if distance < 1e-6:
                    dx, dz, distance = 1.0, 0.0, 1.0
                x = obstacle.x_cm + dx / distance * minimum
                z = obstacle.z_cm + dz / distance * minimum
        return x, z, collided

    def _navigation_turn(self) -> tuple[float, float]:
        self.forward_clearance_cm = self._ray_clearance(self.body.heading_rad)
        self.left_clearance_cm = self._ray_clearance(self.body.heading_rad + math.pi / 3.0)
        self.right_clearance_cm = self._ray_clearance(self.body.heading_rad - math.pi / 3.0)

        reflex = 0.0
        if self.forward_clearance_cm < 3.4:
            # Positive heading turns the body toward -x in this coordinate system.
            reflex = 1.5 if self.left_clearance_cm >= self.right_clearance_cm else -1.5
        elif min(self.left_clearance_cm, self.right_clearance_cm) < 1.1:
            reflex = 0.6 if self.left_clearance_cm > self.right_clearance_cm else -0.6

        exit_turn = 0.0
        if self.navigation_assist and self.escape_latched:
            dx = self.chamber.exit_x_cm - self.body.x_cm
            dz = self.chamber.north_z_cm - 1.5 - self.body.z_cm
            desired = math.atan2(-dx, -dz)
            exit_turn = float(np.clip(_wrap_radians(desired - self.body.heading_rad) * 0.55, -0.75, 0.75))
            # Obstacle reflex has authority at close range; the exit beacon is weak.
            if self.forward_clearance_cm < 3.4:
                exit_turn *= 0.25
        return reflex, exit_turn

    def _move(self, steering_hz: float, escape_now: bool, dt_s: float) -> None:
        self.escape_latched = self.escape_latched or escape_now
        self.neural_turn_rad_s = float(np.clip(
            steering_hz * self.decoder.turn_gain_rad_s_per_hz,
            -self.decoder.maximum_turn_rad_s,
            self.decoder.maximum_turn_rad_s,
        ))
        self.reflex_turn_rad_s, self.exit_turn_rad_s = self._navigation_turn()
        total_turn = float(np.clip(
            self.neural_turn_rad_s + self.reflex_turn_rad_s + self.exit_turn_rad_s,
            -self.decoder.maximum_turn_rad_s,
            self.decoder.maximum_turn_rad_s,
        ))
        self.body.angular_velocity_rad_s = total_turn
        self.body.heading_rad = _wrap_radians(self.body.heading_rad + total_turn * dt_s)

        if self.escape_latched:
            self.body.speed_cm_s = min(self.decoder.escape_speed_cm_s, 9.5)
            since_escape_s = max(0.0, (self.elapsed_ms - 100.0) / 1000.0)
            lift = min(1.0, since_escape_s / 0.55)
            self.body.y_cm = self.decoder.takeoff_height_cm * (lift * lift * (3.0 - 2.0 * lift))
            self.body.behaviour = "takeoff" if lift < 1.0 else "navigating_escape"
        elif abs(steering_hz) > 0.1:
            self.body.speed_cm_s = self.decoder.orient_speed_cm_s
            self.body.behaviour = "orienting_left" if steering_hz > 0 else "orienting_right"
        else:
            self.body.speed_cm_s = 0.0
            self.body.behaviour = "tracking_threat"

        old_x, old_z = self.body.x_cm, self.body.z_cm
        proposed_x = old_x - math.sin(self.body.heading_rad) * self.body.speed_cm_s * dt_s
        proposed_z = old_z - math.cos(self.body.heading_rad) * self.body.speed_cm_s * dt_s
        new_x, new_z, collided = self._resolve_position(old_x, old_z, proposed_x, proposed_z)
        self.body.x_cm, self.body.z_cm = new_x, new_z
        self.path_length_cm += math.hypot(new_x - old_x, new_z - old_z)
        if collided and self.elapsed_ms - self._last_collision_ms > 160.0:
            self.collision_count += 1
            self._last_collision_ms = self.elapsed_ms
            self.body.behaviour = "collision_recovery"

        c = self.chamber
        self.escaped = new_z < c.north_z_cm - 0.8 and abs(new_x - c.exit_x_cm) <= c.exit_half_width_cm
        if self.escaped:
            self.outcome = "escaped"
            self.body.behaviour = "escaped"

    def _advance_threat(self, dt_s: float) -> None:
        # A pursuit controller keeps pressure on the fly; this is world dynamics,
        # not neural activity. Velocity changes are deliberately rate-limited.
        dx = self.body.x_cm - self.threat.x_cm
        dz = self.body.z_cm - self.threat.z_cm
        distance = max(0.001, math.hypot(dx, dz))
        speed = max(0.0, math.hypot(self.threat.vx_cm_s, self.threat.vz_cm_s))
        target_vx, target_vz = dx / distance * speed, dz / distance * speed
        blend = min(1.0, dt_s * 1.8)
        self.threat.vx_cm_s += (target_vx - self.threat.vx_cm_s) * blend
        self.threat.vz_cm_s += (target_vz - self.threat.vz_cm_s) * blend
        self.threat.x_cm += self.threat.vx_cm_s * dt_s
        self.threat.z_cm += self.threat.vz_cm_s * dt_s
        if math.hypot(dx, dz) <= self.threat.radius_cm + self.chamber.body_radius_cm:
            self.captured = True
            self.outcome = "captured"
            self.body.behaviour = "captured"

    @property
    def done(self) -> bool:
        timed_out = self.elapsed_ms >= self.maximum_duration_ms
        if timed_out and self.outcome == "running":
            self.outcome = "timeout"
        return self.escaped or self.captured or timed_out

    def _metrics(self) -> dict:
        c = self.chamber
        optimal = math.hypot(c.exit_x_cm - self._start_x, c.north_z_cm - self._start_z)
        efficiency = 0.0 if self.path_length_cm <= 0.0 else min(1.0, optimal / self.path_length_cm)
        threat_distance = math.hypot(self.threat.x_cm - self.body.x_cm, self.threat.z_cm - self.body.z_cm)
        return {
            "outcome": self.outcome,
            "elapsed_s": self.elapsed_ms / 1000.0,
            "path_length_cm": self.path_length_cm,
            "optimal_path_cm": optimal,
            "route_efficiency": efficiency,
            "collision_count": self.collision_count,
            "threat_distance_cm": threat_distance,
        }

    def _chamber_payload(self) -> dict:
        c = self.chamber
        return {
            "half_width_cm": c.half_width_cm,
            "north_z_cm": c.north_z_cm,
            "south_z_cm": c.south_z_cm,
            "exit_x_cm": c.exit_x_cm,
            "exit_half_width_cm": c.exit_half_width_cm,
            "obstacles": [asdict(obstacle) for obstacle in c.obstacles],
        }

    def snapshot(self) -> dict:
        payload = super().snapshot()
        payload.update({
            "captured": self.captured,
            "outcome": self.outcome,
            "chamber": self._chamber_payload(),
            "navigation": {
                "neural_turn_rad_s": self.neural_turn_rad_s,
                "reflex_turn_rad_s": self.reflex_turn_rad_s,
                "exit_turn_rad_s": self.exit_turn_rad_s,
                "forward_clearance_cm": self.forward_clearance_cm,
                "left_clearance_cm": self.left_clearance_cm,
                "right_clearance_cm": self.right_clearance_cm,
                "assist_enabled": self.navigation_assist,
            },
            "metrics": self._metrics(),
        })
        return payload

    def step(self) -> dict:
        payload = super().step()
        payload.update({
            "captured": self.captured,
            "outcome": self.outcome,
            "chamber": self._chamber_payload(),
            "navigation": {
                "neural_turn_rad_s": self.neural_turn_rad_s,
                "reflex_turn_rad_s": self.reflex_turn_rad_s,
                "exit_turn_rad_s": self.exit_turn_rad_s,
                "forward_clearance_cm": self.forward_clearance_cm,
                "left_clearance_cm": self.left_clearance_cm,
                "right_clearance_cm": self.right_clearance_cm,
                "assist_enabled": self.navigation_assist,
            },
            "metrics": self._metrics(),
        })
        return payload
