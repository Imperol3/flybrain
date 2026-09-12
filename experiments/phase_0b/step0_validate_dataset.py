"""Phase 0B, step 0: validate the real FlyWire dataset. NO simulation runs here.

Per the controlled Phase 0B sequence: "First we get the real FlyWire v783
dataset and do nothing else until this passes." This script only checks
that the dataset loads, the documented counts match, and LC4/LPLC2/DNp01
are identifiable — it does not build a connectome or run any simulation.

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m experiments.phase_0b.step0_validate_dataset

Exits 0 only if every check passes.
"""

from __future__ import annotations

import sys

import config
from brain.connectivity.validation import validate_with_checklist


def main() -> int:
    try:
        flywire_dir = config.get_flywire_dir()
    except config.DatasetConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    dataset_version = config.get_dataset_version()

    print(f"Validating {flywire_dir} as dataset version {dataset_version!r}")
    print("-" * 88)

    all_passed = True
    for label, passed, detail in validate_with_checklist(flywire_dir, dataset_version):
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {label:55s} ({detail})")
        if not passed:
            all_passed = False

    print("-" * 88)
    if all_passed:
        print("Dataset validation: ALL CHECKS PASSED.")
        print("Safe to proceed to: python -m brain.connectivity.build_connectome")
        return 0

    print(
        "Dataset validation FAILED. Stop here — do not build the connectome or run any "
        "simulation against this data until every check above passes.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
