"""Fabricated/invalid neuron IDs and dataset mismatches must be rejected, never silently accepted."""

import pytest

from brain.connectivity.build_connectome import build
from brain.connectivity.validation import validate_dataset
from config import DatasetValidationError


def test_connections_referencing_unknown_root_id_rejected(invalid_fixture_dir):
    with pytest.raises(DatasetValidationError, match="not present in neurons.csv.gz"):
        validate_dataset(invalid_fixture_dir, dataset_version="test_fixture_v0")


def test_build_refuses_fabricated_neuron_ids(invalid_fixture_dir, isolated_derived_paths):
    with pytest.raises(DatasetValidationError):
        build(flywire_dir=invalid_fixture_dir, dataset_version="test_fixture_v0")


def test_build_refuses_wrong_dataset_version(fixture_dir, isolated_derived_paths):
    """The fixture is deliberately far smaller than real FAFB_v783; validating
    it against the real dataset's expected counts must fail loudly rather
    than silently accepting a mismatched dataset.
    """
    with pytest.raises(DatasetValidationError):
        build(flywire_dir=fixture_dir, dataset_version="FAFB_v783")


def test_missing_required_file_rejected(fixture_dir, tmp_path):
    import shutil

    partial_dir = tmp_path / "partial"
    shutil.copytree(fixture_dir, partial_dir, ignore=shutil.ignore_patterns("*.py", "*.md", "invalid_neuron_ref"))
    (partial_dir / "connections_princeton.csv.gz").unlink()

    with pytest.raises(DatasetValidationError, match="Missing required"):
        validate_dataset(partial_dir, dataset_version="test_fixture_v0")
