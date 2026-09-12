"""Phase 0B, step 4: the first real causal experiment — looming vs. looming + LC4/LPLC2 silenced.

Same locked parameters as steps 2-3. This reports what was observed; it
does not assert a PASS/FAIL verdict the way experiments/02_escape_controls.py
does for the synthetic fixture, because on real data we do not yet know
what the correct answer is — that is the entire point of Phase 0B.

Requires a connectome already built via:
    python -m brain.connectivity.build_connectome

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.phase_0b.step4_looming_vs_silenced
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

EXPERIMENT_NAME = "phase0b_looming_vs_silenced"


def main() -> int:
    args = change_reason_arg_parser(__doc__).parse_args()
    registry, connectome = load_registry_and_connectome()

    run_record = run_ledger.record_run(
        EXPERIMENT_NAME,
        registry.dataset_version,
        P.ledger_parameters(silenced_populations=["LC4", "LPLC2"]),
        change_reason=args.change_reason,
    )

    print_header(f"PHASE 0B STEP 4 — Looming vs. looming + LC4/LPLC2 silenced ({run_record.run_id})")

    condition_dicts = []
    results = {}
    for name, silenced in (("looming", ()), ("looming_LC4_LPLC2_silenced", ("LC4", "LPLC2"))):
        stimulus_params = looming.looming(**P.locked_stimulus_kwargs())
        result = session.run_looming_session(
            registry,
            connectome,
            stimulus_params,
            condition_name=name,
            silenced_populations=silenced,
            **P.locked_session_kwargs(),
        )
        results[name] = result
        condition_dicts.append(reporting.session_result_to_condition_dict(result))
        print(f"--- {name} (silenced={silenced}) ---")
        print(f"  LC4={result.lc4_spike_count} LPLC2={result.lplc2_spike_count} DNp01={result.dnp01_spike_count} "
              f"active={result.n_active_neurons} escape={result.escape_triggered}")
        print_time_series_table(list(result.time_series), columns=("LC4", "LPLC2", "DNp01"))
        print()

    looming_dnp01 = results["looming"].dnp01_spike_count
    silenced_dnp01 = results["looming_LC4_LPLC2_silenced"].dnp01_spike_count
    print("OBSERVED (not asserted):")
    print(f"  looming DNp01 spikes:                    {looming_dnp01}")
    print(f"  looming + LC4/LPLC2 silenced DNp01 spikes: {silenced_dnp01}")
    if looming_dnp01 > 0 and silenced_dnp01 == 0:
        print("  This matches the pattern demonstrated on the synthetic fixture in Phase 0A.")
    elif looming_dnp01 == 0:
        print("  DNp01 did not respond to looming at all under these unmodified parameters — "
              "see step2's observation before interpreting this comparison.")
    else:
        print("  DNp01 responded to looming but silencing LC4/LPLC2 did not fully collapse it — "
              "worth investigating (e.g. other unsilenced pathways to DNp01 in the real connectome).")

    out_path = reporting.write_experiment_output(
        experiment_name="phase0b_looming_vs_silenced",
        dataset_version=registry.dataset_version,
        seed=P.SEED,
        conditions=condition_dicts,
        parameters=P.ledger_parameters(silenced_populations=["LC4", "LPLC2"]),
        runtime={"run_id": run_record.run_id},
    )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
