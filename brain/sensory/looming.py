"""Looming (expanding-object) visual stimulus generator.

Models the classic approaching-object geometry: an object of fixed physical
radius approaches (or recedes) the eye at a constant velocity, producing a
time-varying angular half-size theta(t) = atan(radius / distance(t)).
LC4/LPLC2 are looming-selective loom detectors tuned to *expansion rate*
(d(theta)/dt), not raw angular size, so the drive signal handed to
brain.sensory.encoders is the (rectified) expansion rate, not theta itself.
This is an explicit, documented interface-layer modeling choice (brief
section 15/16), not an asserted biological constant — every parameter below
is exposed rather than buried in code.

All three required stimulus conditions (looming / receding / static) are the
*same* generator, distinguished only by the sign/magnitude of
`approach_velocity_cm_s` — never a separate `if looming: escape()` branch.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LoomingStimulusParams:
    object_radius_cm: float = 1.0
    initial_distance_cm: float = 20.0
    approach_velocity_cm_s: float = 40.0   # positive = approaching, negative = receding, 0 = static
    azimuth_deg: float = 0.0               # exposed for future spatially-tuned encoders; unused in V0 drive calc
    min_distance_cm: float = 0.5           # clamp so distance never reaches/crosses zero
    stimulus_onset_ms: float = 0.0
    stimulus_duration_ms: float = 200.0
    simulation_duration_ms: float = 300.0
    seed: int = 0


def looming(**overrides) -> LoomingStimulusParams:
    return LoomingStimulusParams(**overrides)


def receding(**overrides) -> LoomingStimulusParams:
    overrides.setdefault("approach_velocity_cm_s", -40.0)
    return LoomingStimulusParams(**overrides)


def static(**overrides) -> LoomingStimulusParams:
    overrides.setdefault("approach_velocity_cm_s", 0.0)
    return LoomingStimulusParams(**overrides)


def _distance_cm(t_ms: np.ndarray, params: LoomingStimulusParams) -> np.ndarray:
    elapsed_s = np.clip(t_ms - params.stimulus_onset_ms, 0.0, None) / 1000.0
    active = (t_ms >= params.stimulus_onset_ms) & (
        t_ms < params.stimulus_onset_ms + params.stimulus_duration_ms
    )
    distance = params.initial_distance_cm - params.approach_velocity_cm_s * elapsed_s
    distance = np.clip(distance, params.min_distance_cm, None)
    # Before onset and after the stimulus window, distance holds at its
    # initial value (object is not present / not moving).
    held_distance = np.where(t_ms < params.stimulus_onset_ms, params.initial_distance_cm, distance)
    end_elapsed_s = params.stimulus_duration_ms / 1000.0
    end_distance = max(
        params.min_distance_cm,
        params.initial_distance_cm - params.approach_velocity_cm_s * end_elapsed_s,
    )
    held_distance = np.where(
        t_ms >= params.stimulus_onset_ms + params.stimulus_duration_ms, end_distance, held_distance
    )
    return np.where(active, distance, held_distance)


def angular_half_size_deg(t_ms: np.ndarray, params: LoomingStimulusParams) -> np.ndarray:
    distance = _distance_cm(t_ms, params)
    return np.degrees(np.arctan(params.object_radius_cm / distance))


def expansion_rate_deg_per_ms(t_ms: np.ndarray, params: LoomingStimulusParams) -> np.ndarray:
    """d(theta)/dt via central differences on the sampled timebase."""
    theta = angular_half_size_deg(t_ms, params)
    rate = np.gradient(theta, t_ms) if len(t_ms) > 1 else np.zeros_like(theta)
    return rate


def generate_drive_signal(dt_ms: float, params: LoomingStimulusParams) -> np.ndarray:
    """Rectified, non-negative expansion-rate drive signal, one sample per simulation step.

    Only positive expansion (object growing larger / approaching) drives the
    loom-detector populations, matching LC4/LPLC2's known selectivity for
    approaching over receding motion. A static object produces a ~zero
    signal since its angular size does not change.
    """
    n_steps = int(round(params.simulation_duration_ms / dt_ms))
    t_ms = np.arange(n_steps) * dt_ms
    rate = expansion_rate_deg_per_ms(t_ms, params)
    return np.clip(rate, 0.0, None)
