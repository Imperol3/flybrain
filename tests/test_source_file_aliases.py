"""Real-world exports don't always match our canonical filenames/columns exactly.

Confirmed while evaluating a third-party FAFB v783 mirror on Kaggle: files
may be plain .csv (not .csv.gz), and the connections file may be named
"connections_princeton_no_threshold.csv" with "pre_pt_root_id"/
"post_pt_root_id" instead of "pre_root_id"/"post_root_id". These tests
build a fixture directory shaped exactly like that and confirm the pipeline
still works via config.SOURCE_FILE_ALIASES / config.COLUMN_ALIASES — while
still failing clearly if NEITHER the canonical name nor any alias exists.
"""

from __future__ import annotations

import gzip
import shutil

import pandas as pd
import pytest

import config
from brain.connectivity.build_connectome import build
from brain.connectivity.loaders import load_connections, resolve_source_file
from brain.connectivity.validation import validate_dataset
from config import DatasetValidationError
from tests.fixtures.generate_fixtures import CONNECTIONS, NEURONS, root_id


def _write_kaggle_style_dir(fixture_dir, tmp_path):
    """Copy the canonical fixture, but replace the connections file with a
    plain-.csv, pre_pt_root_id/post_pt_root_id-named alias, matching the
    real-world layout found on Kaggle.
    """
    kaggle_dir = tmp_path / "kaggle_style"
    kaggle_dir.mkdir()
    for name in config.REQUIRED_SOURCE_FILES:
        if name == "connections_princeton.csv.gz":
            continue
        shutil.copy(fixture_dir / name, kaggle_dir / name)

    connections_df = pd.DataFrame(
        {
            "pre_pt_root_id": [root_id(pre) for pre, _post, _n in CONNECTIONS],
            "post_pt_root_id": [root_id(post) for _pre, post, _n in CONNECTIONS],
            "neuropil": ["TEST_NEUROPIL" for _ in CONNECTIONS],
            "syn_count": [n for _pre, _post, n in CONNECTIONS],
            "nt_type": [NEURONS[pre][1] for pre, _post, _n in CONNECTIONS],
        }
    )
    connections_df.to_csv(kaggle_dir / "connections_princeton_no_threshold.csv", index=False)
    return kaggle_dir


def test_resolve_source_file_finds_alias(fixture_dir, tmp_path):
    kaggle_dir = _write_kaggle_style_dir(fixture_dir, tmp_path)
    resolved = resolve_source_file(kaggle_dir, "connections_princeton.csv.gz")
    assert resolved.name == "connections_princeton_no_threshold.csv"


def test_resolve_source_file_raises_when_nothing_matches(tmp_path):
    with pytest.raises(DatasetValidationError):
        resolve_source_file(tmp_path, "connections_princeton.csv.gz")


def test_load_connections_normalizes_pt_root_id_columns(fixture_dir, tmp_path):
    kaggle_dir = _write_kaggle_style_dir(fixture_dir, tmp_path)
    df = load_connections(kaggle_dir)
    assert "pre_root_id" in df.columns
    assert "post_root_id" in df.columns
    assert "pre_pt_root_id" not in df.columns
    assert df["pre_root_id"].dtype == "int64"


def test_validate_dataset_succeeds_against_kaggle_style_layout(fixture_dir, tmp_path):
    kaggle_dir = _write_kaggle_style_dir(fixture_dir, tmp_path)
    report = validate_dataset(kaggle_dir, dataset_version="test_fixture_v0")
    assert report.neuron_count == 26
    assert report.neuron_pair_count == 46
    assert report.synapse_count == 2_000


def test_build_succeeds_against_kaggle_style_layout(fixture_dir, tmp_path, isolated_derived_paths):
    kaggle_dir = _write_kaggle_style_dir(fixture_dir, tmp_path)
    manifest = build(flywire_dir=kaggle_dir, dataset_version="test_fixture_v0")
    assert manifest["neuron_count"] == 26
    assert manifest["synapse_count"] == 2_000
    # Checksum keys stay canonical regardless of which alias was found on disk.
    assert "connections_princeton.csv.gz" in manifest["source_checksums_sha256"]


def test_plain_csv_extension_is_accepted_without_gzip(fixture_dir, tmp_path):
    """Even without any name alias, a plain .csv (no gzip) must load fine —
    real exports aren't always compressed.
    """
    plain_dir = tmp_path / "plain_csv"
    plain_dir.mkdir()
    for name in config.REQUIRED_SOURCE_FILES:
        src = fixture_dir / name
        dest_name = name.removesuffix(".gz")
        with gzip.open(src, "rt") as fh:
            content = fh.read()
        (plain_dir / dest_name).write_text(content)

    report = validate_dataset(plain_dir, dataset_version="test_fixture_v0")
    assert report.neuron_count == 26
