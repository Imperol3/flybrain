"""Interactive WORLD -> SENSE -> BRAIN -> ACT closed-loop session.

Body kinematics and motor gains are explicit engineering translation
layers. They are not claims that the FAFB brain connectome contains the
ventral nerve cord, muscles or biomechanics of a living fly.
"""

from __future__ import annotations

import math
import threading
from dataclasses import asdict, dataclass, field

import numpy as np
import scipy.sparse as sp

import config
from brain.motor import descending
from brain.neurons.registry import NeuronRegistry
from brain.sensory import encoders
from simulation.engine import incremental_lif


def _wrap_degrees(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


@dataclass
class BodyState:
    x_cm: float = 0.0
    y_cm: float = 0.0
    z_cm: float = 4.0
    heading_rad: float = 0.0
    speed_cm_s: float = 0.0
    angular_velocity_rad_s: float = 0.0
    behaviour: str = "idle"


@dataclass
class ThreatState:
    x_cm: float
    y_cm: float = 1.0
    z_cm: float = -16.0
    radius_cm: float = 1.0
    vx_cm_s: float = 0.0
    vz_cm_s: float = 40.0


@dataclass(frozen=True)
class MotorDecoderConfig:
    turn_gain_rad_s_per_hz: float = 0.012
    maximum_turn_rad_s: float = 2.4
    orient_speed_cm_s: float = 1.5
    escape_speed_cm_s: float = 12.0
    takeoff_height_cm: float = 2.2


@dataclass
class ClosedLoopSession:
    registry: NeuronRegistry
    connectome: sp.csr_matrix
    body: BodyState
    threat: ThreatState
    step_ms: float = 25.0
    maximum_duration_ms: float = 3000.0
    gain_mV_per_unit: float = 16.0
    silenced_populations: tuple[str, ...] = ()
    decoder: MotorDecoderConfig = field(default_factory=MotorDecoderConfig)
    seed: int = 12345
    elapsed_ms: float = 0.0
    escaped: bool = False
    escape_latched: bool = False
    previous_half_angle_deg: float | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        self._sensory = self._population_indices(("LC4", "LPLC2"), azimuth_deg=0.0)
        self._dnp01 = self.registry.population_indices(config.DESCENDING_OUTPUT_POPULATION)
        self._dna_left = self._optional_population("DNa02_L")
        self._dna_right = self._optional_population("DNa02_R")
        silenced = tuple(
            int(index)
            for name in self.silenced_populations
            for index in self.registry.population_indices(name)
        )
        self._connectome = incremental_lif.mask_outbound(
            self.connectome, self.registry.n_neurons, silenced
        )
        self._engine_state = incremental_lif.initialize(
            self.registry.n_neurons, config.DEFAULT_TIMESTEP_MS, config.LIF_PARAMS
        )

    def _optional_population(self, name: str) -> np.ndarray:
        if name not in self.registry.populations:
            return np.array([], dtype=np.int64)
        return self.registry.population_indices(name)

    def _population_indices(self, names: tuple[str, ...], azimuth_deg: float) -> dict[str, np.ndarray]:
        result = {}
        for name in names:
            suffix = "_L" if azimuth_deg < 0 else "_R" if azimuth_deg > 0 else ""
            qualified = f"{name}{suffix}"
            result[name] = self.registry.population_indices(
                qualified if suffix and qualified in self.registry.populations else name
            )
        return result

    def _observation(self) -> dict:
        dx = self.threat.x_cm - self.body.x_cm
        dz = self.threat.z_cm - self.body.z_cm
        distance = max(0.05, math.hypot(dx, dz))
        target_heading = math.atan2(-dx, -dz)
        azimuth = _wrap_degrees(-math.degrees(target_heading - self.body.heading_rad))
        half_angle = math.degrees(math.atan(self.threat.radius_cm / distance))
        return {"distance_cm": distance, "azimuth_deg": azimuth, "half_angle_deg": half_angle}

    def _advance_threat(self, dt_s: float) -> None:
        self.threat.x_cm += self.threat.vx_cm_s * dt_s
        self.threat.z_cm += self.threat.vz_cm_s * dt_s

    def _drive(self, observation: dict) -> np.ndarray:
        half_angle = observation["half_angle_deg"]
        previous = half_angle if self.previous_half_angle_deg is None else self.previous_half_angle_deg
        rate_deg_per_ms = max(0.0, (half_angle - previous) / self.step_ms)
        self.previous_half_angle_deg = half_angle
        n_steps = int(round(self.step_ms / config.DEFAULT_TIMESTEP_MS))
        return np.full(n_steps, rate_deg_per_ms, dtype=np.float64)

    @staticmethod
    def _rate(result, indices: np.ndarray) -> float:
        if indices.size == 0:
            return 0.0
        return result.spike_count_for(indices) / len(indices) / (result.duration_ms / 1000.0)

    def _move(self, steering_hz: float, escape_now: bool, dt_s: float) -> None:
        self.escape_latched = self.escape_latched or escape_now
        turn = float(np.clip(
            steering_hz * self.decoder.turn_gain_rad_s_per_hz,
            -self.decoder.maximum_turn_rad_s,
            self.decoder.maximum_turn_rad_s,
        ))
        self.body.angular_velocity_rad_s = turn
        self.body.heading_rad += turn * dt_s
        if self.escape_latched:
            self.body.speed_cm_s = self.decoder.escape_speed_cm_s
            self.body.behaviour = "takeoff" if self.elapsed_ms < 450 else "escaping"
            flight_phase = min(1.0, max(0.0, (self.elapsed_ms - 100.0) / 650.0))
            self.body.y_cm = math.sin(flight_phase * math.pi) * self.decoder.takeoff_height_cm
        elif abs(steering_hz) > 0.1:
            self.body.speed_cm_s = self.decoder.orient_speed_cm_s
            self.body.behaviour = "orienting_left" if steering_hz > 0 else "orienting_right"
        else:
            self.body.speed_cm_s = 0.0
            self.body.behaviour = "alert" if self.previous_half_angle_deg else "idle"
        self.body.x_cm -= math.sin(self.body.heading_rad) * self.body.speed_cm_s * dt_s
        self.body.z_cm -= math.cos(self.body.heading_rad) * self.body.speed_cm_s * dt_s
        self.escaped = self.body.z_cm < -12.5 or abs(self.body.x_cm) > 12.5
        if self.escaped:
            self.body.behaviour = "escaped"

    @property
    def done(self) -> bool:
        return self.escaped or self.elapsed_ms >= self.maximum_duration_ms

    def snapshot(self) -> dict:
        return {
            "elapsed_ms": self.elapsed_ms,
            "body": asdict(self.body),
            "threat": asdict(self.threat),
            "observation": self._observation(),
            "escaped": self.escaped,
            "done": self.done,
        }

    def step(self) -> dict:
        with self.lock:
            if self.done:
                return self.snapshot()
            before = self._observation()
            drive_signal = self._drive(before)
            sensory = self._population_indices(("LC4", "LPLC2"), before["azimuth_deg"])
            external_input = encoders.make_external_input_fn(
                drive_signal, sensory, self.registry.n_neurons, self.gain_mV_per_unit
            )
            result, self._engine_state = incremental_lif.run_segment(
                connectome=self._connectome,
                n_neurons=self.registry.n_neurons,
                dataset_version=self.registry.dataset_version,
                state=self._engine_state,
                duration_ms=self.step_ms,
                external_input_fn=external_input,
                seed=self.seed,
            )
            left_hz = self._rate(result, self._dna_left)
            right_hz = self._rate(result, self._dna_right)
            steering_hz = left_hz - right_hz
            escape = descending.interpret_descending_activity(result, self._dnp01)
            dt_s = self.step_ms / 1000.0
            self.elapsed_ms += self.step_ms
            self._move(steering_hz, escape.escape_triggered, dt_s)
            self._advance_threat(dt_s)
            after = self._observation()
            return {
                "elapsed_ms": self.elapsed_ms,
                "body": asdict(self.body),
                "threat": asdict(self.threat),
                "observation": after,
                "neural": {
                    "lc4_spikes": result.spike_count_for(self.registry.population_indices("LC4")),
                    "lplc2_spikes": result.spike_count_for(self.registry.population_indices("LPLC2")),
                    "dnp01_spikes": escape.dnp01_spike_count,
                    "dna02_left_hz": left_hz,
                    "dna02_right_hz": right_hz,
                    "steering_hz": steering_hz,
                    "active_neurons": result.n_active_neurons(),
                    "escape_triggered": escape.escape_triggered,
                    "escape_latched": self.escape_latched,
                },
                "escaped": self.escaped,
                "done": self.done,
            }


def threat_from_azimuth(
    body: BodyState, *, azimuth_deg: float, distance_cm: float, radius_cm: float, approach_velocity_cm_s: float
) -> ThreatState:
    angle = math.radians(azimuth_deg)
    dx, dz = math.sin(angle) * distance_cm, -math.cos(angle) * distance_cm
    length = max(0.001, math.hypot(dx, dz))
    return ThreatState(
        x_cm=body.x_cm + dx,
        z_cm=body.z_cm + dz,
        radius_cm=radius_cm,
        vx_cm_s=-dx / length * approach_velocity_cm_s,
        vz_cm_s=-dz / length * approach_velocity_cm_s,
    )
