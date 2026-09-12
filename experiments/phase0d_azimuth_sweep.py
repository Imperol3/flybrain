"""Phase 0D: steering validation — azimuth sweep.

Question: does a left/right visual stimulus naturally produce asymmetric
DNa02 (steering descending neuron) activity through the real connectome?
Everything is held at the Phase 0A/0B/0C locked baseline (velocity fixed at
40 cm/s, the existing reference) except azimuth_deg, swept across:

    -45, -30, 0, +30, +45 degrees

This is a PREREQUISITE for any future steering/embodiment work: azimuth_deg
was previously stored on every stimulus but never used anywhere in the
sensory encoding (every looming stimulus drove LC4/LPLC2 bilaterally,
regardless of the angle it claimed to come from). simulation.session now
routes stimulation to only the LC4_L/LPLC2_L (or _R) neurons based on
azimuth sign — a documented, deliberate hemifield simplification, not a
retinotopic model (see docs/BIOLOGICAL_ASSUMPTIONS.md).

Records, per azimuth: DNa02_L / DNa02_R spike counts and firing rates, the
steering_signal_hz difference (positive = leftward, negative = rightward),
plus the existing LC4/LPLC2/DNp01 metrics and full time series.

Requires a connectome already built via:
    python -m brain.connectivity.build_connectome
(the build must be recent enough to include side-qualified populations —
rebuild if DNa02_L/DNa02_R are missing from data/derived/connectome_index.json)

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.phase0d_azimuth_sweep
"""

from __future__ import annotations

import sys
import time

from brain.sensory import looming
from experiments.phase_0b import locked_parameters as P
from experiments.phase_0b._common import (
    change_reason_arg_parser,
    load_registry_and_connectome,
    print_header,
)
from simulation import reporting, run_ledger, session

EXPERIMENT_NAME = "phase0d_azimuth_sweep"
AZIMUTHS_DEG = (-45.0, -30.0, 0.0, 30.0, 45.0)
FIXED_VELOCITY_CM_S = 40.0  # the existing Phase 0A/0B/0C reference — held constant here


def _ledger_parameters() -> dict:
    return P.ledger_parameters(azimuths_deg=list(AZIMUTHS_DEG), fixed_velocity_cm_s=FIXED_VELOCITY_CM_S)


def main() -> int:
    args = change_reason_arg_parser(__doc__).parse_args()
    registry, connectome = load_registry_and_connectome()

    if "DNa02_L" not in registry.populations or "DNa02_R" not in registry.populations:
        print(
            "ERROR: DNa02_L/DNa02_R not found in this connectome build. "
            "Rebuild with `python -m brain.connectivity.build_connectome` "
            "(requires a build_connectome.py new enough to emit side-qualified "
            "populations from classification.csv's side column).",
            file=sys.stderr,
        )
        return 1

    run_record = run_ledger.record_run(
        EXPERIMENT_NAME, registry.dataset_version, _ledger_parameters(), change_reason=args.change_reason
    )

    print_header(f"PHASE 0D — Azimuth sweep, locked parameters ({run_record.run_id})")
    print(f"dataset:  {registry.dataset_version}")
    print(f"n_neurons: {registry.n_neurons:,}")
    print(f"azimuths: {AZIMUTHS_DEG} deg, velocity fixed at {FIXED_VELOCITY_CM_S} cm/s")
    print("-" * 110)
    print(
        f"{'azimuth':>9s} {'LC4_L':>6s} {'LC4_R':>6s} {'LPLC2_L':>8s} {'LPLC2_R':>8s} "
        f"{'DNa02_L_Hz':>11s} {'DNa02_R_Hz':>11s} {'steering_Hz':>12s} {'DNp01':>6s} {'s':>5s}"
    )
    print("-" * 110)

    overall_start = time.perf_counter()
    condition_dicts = []
    stimulus_kwargs = dict(P.locked_stimulus_kwargs())
    stimulus_kwargs["approach_velocity_cm_s"] = FIXED_VELOCITY_CM_S
    stimulus_kwargs.pop("azimuth_deg", None)  # this sweep is the one thing that varies it

    for azimuth in AZIMUTHS_DEG:
        stimulus_params = looming.looming(azimuth_deg=azimuth, **stimulus_kwargs)
        result = session.run_looming_session(
            registry,
            connectome,
            stimulus_params,
            condition_name=f"azimuth_{azimuth:g}",
            **P.locked_session_kwargs(),
        )
        cond = reporting.session_result_to_condition_dict(result)
        cond["azimuth_deg"] = azimuth
        condition_dicts.append(cond)

        lat = result.lateralized
        print(
            f"{azimuth:>7.0f}deg "
            f"{lat.get('lc4_left_spike_count', '-'):>6} {lat.get('lc4_right_spike_count', '-'):>6} "
            f"{lat.get('lplc2_left_spike_count', '-'):>8} {lat.get('lplc2_right_spike_count', '-'):>8} "
            f"{lat.get('dna02_left_firing_rate_hz', 0):>11.1f} {lat.get('dna02_right_firing_rate_hz', 0):>11.1f} "
            f"{lat.get('steering_signal_hz', 0):>12.1f} {result.dnp01_spike_count:>6d} "
            f"{result.wall_clock_runtime_s:>5.2f}"
        )

    total_runtime_s = time.perf_counter() - overall_start
    print("-" * 110)

    steering_by_az = {c["azimuth_deg"]: c["lateralized"].get("steering_signal_hz", 0.0) for c in condition_dicts}
    signal_reverses = (steering_by_az[-45.0] * steering_by_az[45.0]) < 0
    print()
    print("Lateralization check — reporting what was observed, not asserting a presumed-correct sign:")
    print(f"  steering_signal_hz at azimuth=-45 (threat on left):  {steering_by_az[-45.0]:+.1f}")
    print(f"  steering_signal_hz at azimuth=0   (centered):        {steering_by_az[0.0]:+.1f}")
    print(f"  steering_signal_hz at azimuth=+45 (threat on right): {steering_by_az[45.0]:+.1f}")
    if signal_reverses:
        pattern = "CONTRALATERAL (turn AWAY from the threat)" if steering_by_az[-45.0] < 0 else "IPSILATERAL (turn TOWARD the threat)"
        print("  The steering signal DOES reverse sign with azimuth — the circuit is azimuth-sensitive.")
        print(f"  Observed pattern: {pattern}. This is reported as an observation, not assumed correct —")
        print("  do not treat either direction as validated without checking against the literature on")
        print("  LC4/LPLC2 -> DNa02 connectivity specifically (an escape/avoidance circuit turning away")
        print("  from threat is at least as biologically plausible as an orienting-toward pattern).")
    else:
        print("  The steering signal does NOT reverse sign between the two extremes — investigate before")
        print("  building a motor decoder on top of it.")
    if abs(steering_by_az[0.0]) > 0.1 * max(abs(steering_by_az[-45.0]), abs(steering_by_az[45.0]), 1.0):
        print(
            f"  CAVEAT: azimuth=0 (nominally symmetric) is NOT near zero ({steering_by_az[0.0]:+.1f} Hz) — "
            "the real connectome is not perfectly left/right symmetric (it is one real, individual fly, "
            "not an idealized bilateral model), or the coarse hemifield routing itself introduces bias. "
            "Worth investigating before relying on the zero-point as a 'go straight' baseline."
        )

    out_path = reporting.write_experiment_output(
        experiment_name=EXPERIMENT_NAME,
        dataset_version=registry.dataset_version,
        seed=P.SEED,
        conditions=condition_dicts,
        parameters=_ledger_parameters(),
        runtime={"total_wall_clock_s": total_runtime_s, "run_id": run_record.run_id},
    )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
