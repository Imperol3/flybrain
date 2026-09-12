"""Canonical demonstration: LOOMING -> LC4/LPLC2 -> whole-connectome propagation -> DNp01/Giant Fibre.

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.01_looming_escape

Requires a connectome already built via:
    python -m brain.connectivity.build_connectome
"""

from __future__ import annotations

import sys
import time

import scipy.sparse as sp

import config
from brain.neurons import registry as registry_module
from brain.sensory import looming
from simulation import reporting, session


def main() -> int:
    try:
        registry = registry_module.load()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    connectome = sp.load_npz(config.CONNECTOME_NPZ)

    seed = 12345
    stimulus_params = looming.looming(
        simulation_duration_ms=config.DEFAULT_SIMULATION_DURATION_MS,
        seed=seed,
    )

    start = time.perf_counter()
    result = session.run_looming_session(
        registry, connectome, stimulus_params, condition_name="looming", dt_ms=config.DEFAULT_TIMESTEP_MS
    )
    total_runtime_s = time.perf_counter() - start

    print("=" * 72)
    print("LOOMING -> LC4/LPLC2 -> connectome propagation -> DNp01/Giant Fibre")
    print("=" * 72)
    print(f"dataset:            {registry.dataset_version}")
    print(f"n_neurons:          {registry.n_neurons:,}")
    print(f"seed:               {seed}")
    print(f"LC4 spikes:         {result.lc4_spike_count}")
    print(f"LPLC2 spikes:       {result.lplc2_spike_count}")
    print(f"DNp01 spikes:       {result.dnp01_spike_count}")
    print(f"DNp01 peak rate:    {result.dnp01_peak_firing_rate_hz:.1f} Hz")
    print(f"active neurons:     {result.n_active_neurons}")
    print(f"escape triggered:   {result.escape_triggered}")
    print(f"wall-clock runtime: {result.wall_clock_runtime_s:.3f}s")

    out_path = reporting.write_experiment_output(
        experiment_name="looming_escape",
        dataset_version=registry.dataset_version,
        seed=seed,
        conditions=[reporting.session_result_to_condition_dict(result)],
        parameters=result.parameters,
        runtime={"total_wall_clock_s": total_runtime_s},
    )
    print(f"wrote {out_path}")

    if not result.escape_triggered:
        print(
            "WARNING: expected DNp01 escape response to a looming stimulus did not occur. "
            "Investigate rather than treat this run as passing.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
