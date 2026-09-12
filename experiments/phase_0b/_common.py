"""Shared helpers for the Phase 0B script sequence. Not a runnable step itself."""

from __future__ import annotations

import argparse
import sys

import scipy.sparse as sp

import config
from brain.neurons import registry as registry_module


def change_reason_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--change-reason",
        default=None,
        help=(
            "Required only if this run's locked parameters differ from the previous "
            "recorded run of this experiment (simulation.run_ledger enforces this). "
            "Explain what changed and why."
        ),
    )
    return parser


def load_registry_and_connectome():
    """Load the already-built connectome + registry, or exit(1) with a clear message."""
    try:
        registry = registry_module.load()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    connectome = sp.load_npz(config.CONNECTOME_NPZ)
    return registry, connectome


def print_header(title: str) -> None:
    print("=" * 88)
    print(title)
    print("=" * 88)


def print_time_series_table(time_series: list[dict], columns: tuple[str, ...]) -> None:
    header = f"{'t_ms':>8s} " + " ".join(f"{c:>14s}" for c in columns)
    print(header)
    for row in time_series:
        line = f"{row['t_ms']:8.1f} " + " ".join(f"{c}={row.get(c, 0):<10d}" for c in columns)
        print(line)
