"""Phase 0B, step 2: looming stimulus only, locked parameters, no tuning.

Runs exactly one condition — looming, with every parameter carried over
unmodified from Phase 0A (see locked_parameters.py) — and reports what
happens. If DNp01 does not respond, that is itself the useful result: it
means the locked stimulus gain (tuned only against the tiny synthetic
fixture) does not transfer to real scale, which is expected and fine to
learn here. This script does NOT retune anything and does NOT fail/exit
non-zero just because escape wasn't triggered — Phase 0A already proved the
architecture can produce escape; Phase 0B is about observing the real
network, not reproducing that result on demand.

Requires a connectome already built via:
    python -m brain.connectivity.build_connectome

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.phase_0b.step2_looming_only
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

EXPERIMENT_NAME = "phase0b_looming_only"


def main() -> int:
    args = change_reason_arg_parser(__doc__).parse_args()
    registry, connectome = load_registry_and_connectome()

    run_record = run_ledger.record_run(
        EXPERIMENT_NAME, registry.dataset_version, P.ledger_parameters(), change_reason=args.change_reason
    )

    stimulus_params = looming.looming(**P.locked_stimulus_kwargs())
    result = session.run_looming_session(
        registry, connectome, stimulus_params, condition_name="looming", **P.locked_session_kwargs()
    )

    print_header(f"PHASE 0B STEP 2 — Looming only, locked parameters ({run_record.run_id})")
    print(f"dataset:            {registry.dataset_version}")
    print(f"n_neurons:          {registry.n_neurons:,}")
    print(f"gain_mV_per_unit:   {P.GAIN_MV_PER_UNIT} (unmodified from Phase 0A — see locked_parameters.py)")
    print(f"LC4 spikes:         {result.lc4_spike_count}")
    print(f"LPLC2 spikes:       {result.lplc2_spike_count}")
    print(f"DNp01 spikes:       {result.dnp01_spike_count}")
    print(f"DNp01 peak rate:    {result.dnp01_peak_firing_rate_hz:.1f} Hz")
    print(f"active neurons:     {result.n_active_neurons}")
    print(f"DNp01 reached configured escape threshold ({P.ESCAPE_THRESHOLD_RATE_HZ} Hz): {result.escape_triggered}")
    print(f"wall-clock runtime: {result.wall_clock_runtime_s:.3f}s")
    print()
    print_time_series_table(
        list(result.time_series), columns=("LC4", "LPLC2", "DNp01")
    )
    print()
    if result.dnp01_spike_count == 0:
        print(
            "OBSERVATION: DNp01 did not respond under these unmodified parameters. "
            "This is a valid, informative result — it likely means the encoder gain "
            "and/or LIF constants need re-examination at real scale, not that anything "
            "is broken. Do not retune without recording a --change-reason."
        )
    else:
        print(
            "OBSERVATION: DNp01 produced spikes under the unmodified looming condition. "
            "Proceed to step3 (receding/static) and step4 (silencing comparison) before "
            "drawing any causal conclusion."
        )

    out_path = reporting.write_experiment_output(
        experiment_name="phase0b_looming_only",
        dataset_version=registry.dataset_version,
        seed=stimulus_params.seed,
        conditions=[reporting.session_result_to_condition_dict(result)],
        parameters=result.parameters,
        runtime={"total_wall_clock_s": result.wall_clock_runtime_s, "run_id": run_record.run_id},
    )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
