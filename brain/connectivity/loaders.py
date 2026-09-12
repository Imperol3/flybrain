"""Typed readers for the raw FlyWire FAFB v783 source files.

Each function reads exactly one logical source file into a pandas DataFrame
with an explicit dtype contract and an explicit required-column check.
Nothing here guesses at a schema — a missing/renamed column is a hard
error, not a silently-dropped feature, per the "fail clearly" requirement
in the brief.

Real-world exports are not perfectly consistent about filenames or gzip
compression (see config.SOURCE_FILE_ALIASES / config.COLUMN_ALIASES and
docs/DATA_PROVENANCE.md). `resolve_source_file` and the loaders below try a
documented list of alternates before giving up — but if none of them exist,
this still fails clearly rather than silently substituting anything.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config
from config import DatasetValidationError


def resolve_source_file(flywire_dir: Path, canonical_name: str) -> Path:
    """Return the path to `canonical_name`, or one of its documented aliases.

    Raises DatasetValidationError listing every candidate tried if none exist.
    """
    candidates = [canonical_name, *config.SOURCE_FILE_ALIASES.get(canonical_name, ())]
    for name in candidates:
        path = flywire_dir / name
        if path.exists():
            return path
    raise DatasetValidationError(
        f"Required source file missing: none of {candidates} found in {flywire_dir}"
    )


def _read_required_columns(
    flywire_dir: Path, canonical_name: str, required_columns: tuple[str, ...], dtypes: dict
) -> pd.DataFrame:
    path = resolve_source_file(flywire_dir, canonical_name)
    df = pd.read_csv(path, compression="infer")

    column_aliases = config.COLUMN_ALIASES.get(canonical_name, {})
    present_aliases = {raw: canonical for raw, canonical in column_aliases.items() if raw in df.columns}
    if present_aliases:
        df = df.rename(columns=present_aliases)

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise DatasetValidationError(
            f"{path.name} is missing required column(s) {missing}; found columns {list(df.columns)}"
        )

    for column, dtype in dtypes.items():
        if column in df.columns:
            df[column] = df[column].astype(dtype)

    return df


def load_neurons(flywire_dir: Path) -> pd.DataFrame:
    """neurons.csv[.gz]: one row per neuron root_id with predicted neurotransmitter."""
    return _read_required_columns(
        flywire_dir,
        "neurons.csv.gz",
        required_columns=("root_id", "nt_type"),
        dtypes={"root_id": "int64", "nt_type": "string"},
    )


def load_classification(flywire_dir: Path) -> pd.DataFrame:
    """classification.csv[.gz]: super-class / class / side / nerve annotations."""
    return _read_required_columns(
        flywire_dir,
        "classification.csv.gz",
        required_columns=("root_id", "super_class", "class", "side"),
        dtypes={"root_id": "int64"},
    )


def load_consolidated_cell_types(flywire_dir: Path) -> pd.DataFrame:
    """consolidated_cell_types.csv[.gz]: root_id -> named cell type (e.g. LC4, LPLC2, DNp01)."""
    return _read_required_columns(
        flywire_dir,
        "consolidated_cell_types.csv.gz",
        required_columns=("root_id", "primary_type"),
        dtypes={"root_id": "int64", "primary_type": "string"},
    )


def load_connections(flywire_dir: Path) -> pd.DataFrame:
    """connections_princeton.csv[.gz] (or the documented alias): pre/post root_id pairs with synapse counts."""
    return _read_required_columns(
        flywire_dir,
        "connections_princeton.csv.gz",
        required_columns=("pre_root_id", "post_root_id", "syn_count", "nt_type"),
        dtypes={"pre_root_id": "int64", "post_root_id": "int64", "syn_count": "int64", "nt_type": "string"},
    )


def load_coordinates(flywire_dir: Path) -> pd.DataFrame:
    """coordinates.csv[.gz]: neuron soma/skeleton position, nanometres. Not consumed by V0 compute."""
    return _read_required_columns(
        flywire_dir,
        "coordinates.csv.gz",
        required_columns=("root_id",),
        dtypes={"root_id": "int64"},
    )


def load_column_assignment(flywire_dir: Path) -> pd.DataFrame:
    """column_assignment.csv[.gz]: optic-lobe column assignment. Not consumed by V0 compute."""
    return _read_required_columns(
        flywire_dir,
        "column_assignment.csv.gz",
        required_columns=("root_id",),
        dtypes={"root_id": "int64"},
    )


def load_labels(flywire_dir: Path) -> pd.DataFrame:
    """labels.csv[.gz]: free-text annotations. Not consumed by V0 compute."""
    return _read_required_columns(
        flywire_dir,
        "labels.csv.gz",
        required_columns=("root_id",),
        dtypes={"root_id": "int64"},
    )


def load_visual_neuron_types(flywire_dir: Path) -> pd.DataFrame:
    """visual_neuron_types.csv[.gz]: visual-system cell type labels. Not consumed by V0 compute."""
    return _read_required_columns(
        flywire_dir,
        "visual_neuron_types.csv.gz",
        required_columns=("root_id",),
        dtypes={"root_id": "int64"},
    )
