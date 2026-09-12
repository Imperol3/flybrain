"""Phase 0B, step 3: receding and static stimulus controls, locked parameters, no tuning.

Same locked parameters as step2 (see locked_parameters.py). This is purely
informational, run before drawing any causal conclusion — it does not
assert or require any particular outcome.

Requires a connectome already built via:
    python -m brain.connectivity.build_connectome

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.phase_0b.step3_receding_static
"""

from __future__ import annotations

from brain.sensory import looming
from experiments.phase_0b import locked_parameters as P
from experiments.phase_0b._common import (
    change_reason_arg_parser,
    load_registry_and_connectome,
    print_header,
    print_time_series_table,
)
from simulation import reporting, run_ledger, session

EXPERIMENT_NAME = "phase0b_receding_static"


def main() -> int:
    args = change_reason_arg_parser(__doc__).parse_args()
    registry, connectome = load_registry_and_connectome()

    run_record = run_ledger.record_run(
        EXPERIMENT_NAME, registry.dataset_version, P.ledger_parameters(), change_reason=args.change_reason
    )

    print_header(f"PHASE 0B STEP 3 — Receding & static controls, locked parameters ({run_record.run_id})")

    condition_dicts = []
    for name, factory in (("receding", looming.receding), ("static", looming.static)):
        stimulus_params = factory(**P.locked_stimulus_kwargs())
        result = session.run_looming_session(
            registry, connectome, stimulus_params, condition_name=name, **P.locked_session_kwargs()
        )
        condition_dicts.append(reporting.session_result_to_condition_dict(result))
        print(f"--- {name} ---")
        print(f"  LC4={result.lc4_spike_count} LPLC2={result.lplc2_spike_count} DNp01={result.dnp01_spike_count} "
              f"active={result.n_active_neurons} escape={result.escape_triggered}")
        print_time_series_table(list(result.time_series), columns=("LC4", "LPLC2", "DNp01"))
        print()

    out_path = reporting.write_experiment_output(
        experiment_name="phase0b_receding_static",
        dataset_version=registry.dataset_version,
        seed=P.SEED,
        conditions=condition_dicts,
        parameters=P.ledger_parameters(),
        runtime={"run_id": run_record.run_id},
    )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
