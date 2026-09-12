"""The single, shared, LOCKED parameter set for every Phase 0B script.

Phase 0B's purpose is to find out what the real FlyWire connectome actually
does under the parameters carried over unmodified from Phase 0A (the
synthetic-fixture engineering baseline) — not to find parameters that make
it produce an expected answer. Every Phase 0B script imports its parameters
from here, and every run is recorded via simulation.run_ledger, which
refuses to log a changed value without an explicit reason.

If you need to change something (e.g. `GAIN_MV_PER_UNIT` turns out to be
off by orders of magnitude on the real connectome, exactly as anticipated),
do it by editing this file AND passing a `--change-reason` to whichever
script's CLI first uses the new value — never edit this file silently.
"""

from __future__ import annotations

import config
from brain.motor import descending

# Carried over UNCHANGED from Phase 0A fixture tuning. This value has NO
# claim to correctness at real FAFB_v783 scale — Phase 0B step 2
# (looming-only) exists specifically to find out what it actually produces,
# unmodified. See docs/BIOLOGICAL_ASSUMPTIONS.md section 4.
GAIN_MV_PER_UNIT = 16.0

DT_MS = config.DEFAULT_TIMESTEP_MS
SIMULATION_DURATION_MS = config.DEFAULT_SIMULATION_DURATION_MS
TIME_SERIES_BIN_MS = config.DEFAULT_TIME_SERIES_BIN_MS
SEED = 12345

ESCAPE_THRESHOLD_RATE_HZ = descending.DEFAULT_ESCAPE_RATE_THRESHOLD_HZ
ESCAPE_WINDOW_MS = descending.DEFAULT_ESCAPE_WINDOW_MS

# Looming stimulus shape, also carried over unchanged from Phase 0A.
LOOMING_OBJECT_RADIUS_CM = 1.0
LOOMING_INITIAL_DISTANCE_CM = 20.0
LOOMING_APPROACH_VELOCITY_CM_S = 40.0
LOOMING_AZIMUTH_DEG = 0.0
LOOMING_STIMULUS_DURATION_MS = 200.0


def locked_stimulus_kwargs() -> dict:
    """Shared stimulus-shape parameters, EXCLUDING approach_velocity_cm_s.

    Velocity is deliberately left out here because it's the one parameter
    that distinguishes looming/receding/static — looming.looming() defaults
    to +40 cm/s, looming.receding() defaults to -40 cm/s, and looming.static()
    defaults to 0, each via their own setdefault(). Baking a fixed velocity
    into this shared dict would make those defaults never fire (the key
    would already be present), silently turning every condition into
    looming — exactly the bug this comment is here to prevent regressing.
    """
    return dict(
        object_radius_cm=LOOMING_OBJECT_RADIUS_CM,
        initial_distance_cm=LOOMING_INITIAL_DISTANCE_CM,
        azimuth_deg=LOOMING_AZIMUTH_DEG,
        stimulus_duration_ms=LOOMING_STIMULUS_DURATION_MS,
        simulation_duration_ms=SIMULATION_DURATION_MS,
        seed=SEED,
    )


def locked_session_kwargs() -> dict:
    return dict(
        dt_ms=DT_MS,
        gain_mV_per_unit=GAIN_MV_PER_UNIT,
        lif_params=dict(config.LIF_PARAMS),
        escape_threshold_rate_hz=ESCAPE_THRESHOLD_RATE_HZ,
        escape_window_ms=ESCAPE_WINDOW_MS,
        time_series_bin_ms=TIME_SERIES_BIN_MS,
    )


def ledger_parameters(**extra) -> dict:
    """The full locked parameter set, for hashing/logging in the run ledger.
    `extra` lets a script add condition-specific values (e.g. which
    populations are silenced) that are also part of "what changed".
    """
    params = {
        "dt_ms": DT_MS,
        "simulation_duration_ms": SIMULATION_DURATION_MS,
        "time_series_bin_ms": TIME_SERIES_BIN_MS,
        "seed": SEED,
        "gain_mV_per_unit": GAIN_MV_PER_UNIT,
        "lif_params": dict(config.LIF_PARAMS),
        "escape_threshold_rate_hz": ESCAPE_THRESHOLD_RATE_HZ,
        "escape_window_ms": ESCAPE_WINDOW_MS,
        "looming_stimulus": {
            **locked_stimulus_kwargs(),
            "approach_velocity_cm_s": LOOMING_APPROACH_VELOCITY_CM_S,
        },
    }
    params.update(extra)
    return params
