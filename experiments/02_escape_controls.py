"""Escape/lesion control battery (brief section 11).

Runs six conditions with identical simulation settings (same seed, timestep,
duration, LIF/encoder parameters) and records the required metrics for each:

    looming
    receding
    static
    looming + LC4 silenced
    looming + LPLC2 silenced
    looming + LC4 and LPLC2 silenced

The crucial causal test: DNp01 responds to plain looming, and that response
should collapse when LC4+LPLC2's outbound effect is silenced (sensory drive
still occurs; only the outbound synaptic effect is removed). This script
reports whatever actually happens rather than asserting/forcing the expected
result.

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.02_escape_controls

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

SEED = 12345
DURATION_MS = config.DEFAULT_SIMULATION_DURATION_MS


def _stimulus(**overrides) -> looming.LoomingStimulusParams:
    overrides.setdefault("simulation_duration_ms", DURATION_MS)
    overrides.setdefault("seed", SEED)
    return overrides


CONDITIONS = [
    ("looming", looming.looming, {}, ()),
    ("receding", looming.receding, {}, ()),
    ("static", looming.static, {}, ()),
    ("looming_LC4_silenced", looming.looming, {}, ("LC4",)),
    ("looming_LPLC2_silenced", looming.looming, {}, ("LPLC2",)),
    ("looming_LC4_LPLC2_silenced", looming.looming, {}, ("LC4", "LPLC2")),
]


def main() -> int:
    try:
        registry = registry_module.load()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    connectome = sp.load_npz(config.CONNECTOME_NPZ)

    results = {}
    condition_dicts = []
    overall_start = time.perf_counter()

    print("=" * 88)
    print(f"{'condition':30s} {'LC4':>6} {'LPLC2':>6} {'DNp01':>6} {'peakHz':>8} {'active':>7} {'escape':>7}")
    print("-" * 88)

    for name, factory, overrides, silenced in CONDITIONS:
        stimulus_params = factory(**_stimulus(**overrides))
        result = session.run_looming_session(
            registry,
            connectome,
            stimulus_params,
            condition_name=name,
            dt_ms=config.DEFAULT_TIMESTEP_MS,
            silenced_populations=silenced,
        )
        results[name] = result
        condition_dicts.append(reporting.session_result_to_condition_dict(result))
        print(
            f"{name:30s} {result.lc4_spike_count:6d} {result.lplc2_spike_count:6d} "
            f"{result.dnp01_spike_count:6d} {result.dnp01_peak_firing_rate_hz:8.1f} "
            f"{result.n_active_neurons:7d} {str(result.escape_triggered):>7s}"
        )

    total_runtime_s = time.perf_counter() - overall_start
    print("-" * 88)

    looming_dnp01 = results["looming"].dnp01_spike_count
    both_silenced_dnp01 = results["looming_LC4_LPLC2_silenced"].dnp01_spike_count
    causal_test_passed = looming_dnp01 > 0 and both_silenced_dnp01 == 0

    print()
    print("Causal test: looming drives DNp01, and LC4+LPLC2 output-silencing collapses it.")
    print(f"  looming DNp01 spikes:                 {looming_dnp01}")
    print(f"  looming+LC4+LPLC2-silenced DNp01 spikes: {both_silenced_dnp01}")
    print(f"  RESULT: {'PASS' if causal_test_passed else 'FAIL - investigate, do not treat as passing'}")

    out_path = reporting.write_experiment_output(
        experiment_name="escape_controls",
        dataset_version=registry.dataset_version,
        seed=SEED,
        conditions=condition_dicts,
        parameters={"dt_ms": config.DEFAULT_TIMESTEP_MS, "simulation_duration_ms": DURATION_MS, "seed": SEED},
        runtime={"total_wall_clock_s": total_runtime_s},
    )
    print(f"wrote {out_path}")

    return 0 if causal_test_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
