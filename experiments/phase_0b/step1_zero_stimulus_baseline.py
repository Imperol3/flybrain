"""Phase 0B, step 1: zero-stimulus baseline. Is the network stable before we add anything?

No external drive is injected anywhere. This just runs the raw connectome
under the locked LIF parameters and reports what spontaneous activity (if
any) results — runaway activity here would mean something is wrong before
we ever add a stimulus, so this must be checked first.

Requires a connectome already built via:
    python -m brain.connectivity.build_connectome

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.phase_0b.step1_zero_stimulus_baseline
"""

from __future__ import annotations

import time

import numpy as np

import config
from experiments.phase_0b import locked_parameters as P
from experiments.phase_0b._common import (
    change_reason_arg_parser,
    load_registry_and_connectome,
    print_header,
    print_time_series_table,
)
from simulation import reporting, run_ledger
from simulation.engine import lif_engine

EXPERIMENT_NAME = "phase0b_zero_stimulus_baseline"


def main() -> int:
    args = change_reason_arg_parser(__doc__).parse_args()
    registry, connectome = load_registry_and_connectome()

    ledger_params = {
        "dt_ms": P.DT_MS,
        "simulation_duration_ms": P.SIMULATION_DURATION_MS,
        "time_series_bin_ms": P.TIME_SERIES_BIN_MS,
        "seed": P.SEED,
        "lif_params": dict(config.LIF_PARAMS),
        "external_input": None,
    }
    run_record = run_ledger.record_run(
        EXPERIMENT_NAME, registry.dataset_version, ledger_params, change_reason=args.change_reason
    )

    start = time.perf_counter()
    sim_result = lif_engine.run(
        connectome=connectome,
        n_neurons=registry.n_neurons,
        dataset_version=registry.dataset_version,
        dt_ms=P.DT_MS,
        duration_ms=P.SIMULATION_DURATION_MS,
        seed=P.SEED,
        external_input_fn=None,
        silenced_indices=(),
        params=config.LIF_PARAMS,
    )
    wall_clock_s = time.perf_counter() - start

    populations = {
        name: registry.population_indices(name)
        for name in ("LC4", "LPLC2", config.DESCENDING_OUTPUT_POPULATION)
    }
    time_series = sim_result.time_series(populations, bin_ms=P.TIME_SERIES_BIN_MS)

    print_header(f"PHASE 0B STEP 1 — Zero-stimulus baseline ({run_record.run_id})")
    print(f"dataset:            {registry.dataset_version}")
    print(f"n_neurons:          {registry.n_neurons:,}")
    print(f"total spikes:       {sim_result.spike_neuron_indices.size:,}")
    print(f"active neurons:     {sim_result.n_active_neurons():,}")
    print(f"wall-clock runtime: {wall_clock_s:.3f}s")
    print()
    print_time_series_table(time_series, columns=("LC4", "LPLC2", config.DESCENDING_OUTPUT_POPULATION))

    # Naive stability observation only — not a pass/fail judgment. A network
    # that is exploding will show a clearly growing spike count in the
    # second half of the run relative to the first; one that is quiescent
    # or settling will not.
    n_spikes = sim_result.spike_times_ms.size
    if n_spikes == 0:
        observation = "No spontaneous activity at all (fully quiescent)."
    else:
        first_half = int(np.sum(sim_result.spike_times_ms < P.SIMULATION_DURATION_MS / 2))
        second_half = n_spikes - first_half
        observation = (
            f"{first_half} spikes in first half, {second_half} in second half of the run "
            f"({'appears to be growing — investigate before adding stimulus' if second_half > first_half * 2 else 'does not appear to be runaway'})."
        )
    print()
    print(f"Observation: {observation}")

    out_path = reporting.write_experiment_output(
        experiment_name="phase0b_zero_stimulus_baseline",
        dataset_version=registry.dataset_version,
        seed=P.SEED,
        conditions=[
            {
                "condition": "zero_stimulus",
                "run_id": run_record.run_id,
                "total_spikes": int(n_spikes),
                "n_active_neurons": sim_result.n_active_neurons(),
                "observation": observation,
                "time_series": time_series,
            }
        ],
        parameters=ledger_params,
        runtime={"total_wall_clock_s": wall_clock_s},
    )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
