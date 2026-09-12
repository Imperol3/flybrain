"""Phase 0C: stimulus-response velocity sweep.

Question: does the fly brain respond differently depending on how
threatening the approaching object is? Everything is held identical to the
Phase 0A/0B locked baseline (experiments/phase_0b/locked_parameters.py)
except approach_velocity_cm_s, which is swept across:

    10, 20, 40, 80 cm/s   (40 cm/s is the existing Phase 0A/0B reference)

This is deliberately NOT assuming faster approach must produce more spikes
or an earlier/stronger escape — the point is to observe what the network
actually does, using the same "no silent tuning" run-ledger discipline as
Phase 0B.

Requires a connectome already built via:
    python -m brain.connectivity.build_connectome

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.phase0c_velocity_sweep
"""

from __future__ import annotations

import time

from brain.sensory import looming
from experiments.phase_0b import locked_parameters as P
from experiments.phase_0b._common import (
    change_reason_arg_parser,
    load_registry_and_connectome,
    print_header,
)
from simulation import reporting, run_ledger, session

EXPERIMENT_NAME = "phase0c_velocity_sweep"
VELOCITIES_CM_S = (10.0, 20.0, 40.0, 80.0)


def _ledger_parameters() -> dict:
    return P.ledger_parameters(velocities_cm_s=list(VELOCITIES_CM_S))


def main() -> int:
    args = change_reason_arg_parser(__doc__).parse_args()
    registry, connectome = load_registry_and_connectome()

    run_record = run_ledger.record_run(
        EXPERIMENT_NAME, registry.dataset_version, _ledger_parameters(), change_reason=args.change_reason
    )

    print_header(f"PHASE 0C — Velocity sweep, locked parameters ({run_record.run_id})")
    print(f"dataset:  {registry.dataset_version}")
    print(f"n_neurons: {registry.n_neurons:,}")
    print(f"velocities: {VELOCITIES_CM_S} cm/s (40 cm/s = existing Phase 0A/0B reference)")
    print("-" * 100)
    header = (
        f"{'velocity':>10s} {'LC4':>5s} {'LPLC2':>6s} {'DNp01':>6s} {'peakHz':>8s} "
        f"{'active':>7s} {'1st_sens_ms':>12s} {'1st_dn_ms':>10s} {'escape':>7s} {'trig_ms':>9s} {'s':>6s}"
    )
    print(header)
    print("-" * 100)

    overall_start = time.perf_counter()
    condition_dicts = []

    stimulus_kwargs = dict(P.locked_stimulus_kwargs())

    for velocity in VELOCITIES_CM_S:
        stimulus_params = looming.looming(approach_velocity_cm_s=velocity, **stimulus_kwargs)
        result = session.run_looming_session(
            registry,
            connectome,
            stimulus_params,
            condition_name=f"looming_v{velocity:g}",
            **P.locked_session_kwargs(),
        )
        cond = reporting.session_result_to_condition_dict(result)
        cond["approach_velocity_cm_s"] = velocity
        condition_dicts.append(cond)

        def fmt_ms(v):
            return f"{v:.1f}" if v is not None else "-"

        print(
            f"{velocity:>8.0f}cm/s {result.lc4_spike_count:5d} {result.lplc2_spike_count:6d} "
            f"{result.dnp01_spike_count:6d} {result.dnp01_peak_firing_rate_hz:8.1f} "
            f"{result.n_active_neurons:7d} {fmt_ms(result.first_sensory_spike_time_ms):>12s} "
            f"{fmt_ms(result.first_dnp01_spike_time_ms):>10s} {str(result.escape_triggered):>7s} "
            f"{fmt_ms(result.escape_trigger_time_ms):>9s} {result.wall_clock_runtime_s:6.2f}"
        )

    total_runtime_s = time.perf_counter() - overall_start
    print("-" * 100)

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
