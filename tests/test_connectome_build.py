"""Connectome build: counts, sparse representation, population registry, manifest."""

import json

import numpy as np
import scipy.sparse as sp

import config
from brain.connectivity.validation import validate_dataset, validate_with_checklist


def test_validate_dataset_matches_fixture_counts(fixture_dir):
    report = validate_dataset(fixture_dir, dataset_version="test_fixture_v0")
    assert report.neuron_count == 26
    assert report.neuron_pair_count == 46
    assert report.synapse_count == 2_000


def test_build_produces_expected_counts(built_fixture_connectome):
    _registry, _connectome, manifest = built_fixture_connectome
    assert manifest["neuron_count"] == 26
    assert manifest["neuron_pair_count"] == 46
    assert manifest["synapse_count"] == 2_000


def test_connectome_is_sparse_csr_not_dense(built_fixture_connectome):
    _registry, connectome, _manifest = built_fixture_connectome
    assert isinstance(connectome, sp.csr_matrix)
    assert connectome.shape == (26, 26)
    # nnz should be proportional to the number of distinct edges, not n^2.
    assert connectome.nnz <= 46
    assert connectome.nnz < connectome.shape[0] * connectome.shape[1]


def test_connectome_signed_weights(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome

    # LC4 -> relay_L connections are excitatory (ACh): positive signed weight.
    lc4_idx = registry.population_indices("LC4")[0]
    lc4_row = connectome.getrow(lc4_idx).toarray().ravel()
    assert np.any(lc4_row > 0)
    assert not np.any(lc4_row < 0)

    # The fixture's GABAergic "inhibitory_control" population should produce
    # at least one negative signed weight somewhere in the connectome.
    has_negative_row = any(
        np.any(connectome.getrow(i).toarray().ravel() < 0) for i in range(registry.n_neurons)
    )
    assert has_negative_row, "expected at least one inhibitory (negative-weight) connection in the fixture"


def test_registry_population_counts(built_fixture_connectome):
    registry, _connectome, _manifest = built_fixture_connectome
    assert len(registry.population_root_ids("LC4")) == config.EXPECTED_POPULATION_COUNTS["test_fixture_v0"]["LC4"]
    assert len(registry.population_root_ids("LPLC2")) == config.EXPECTED_POPULATION_COUNTS["test_fixture_v0"]["LPLC2"]


def test_dnp01_population_identified(built_fixture_connectome):
    registry, _connectome, _manifest = built_fixture_connectome
    dnp01_ids = registry.population_root_ids(config.DESCENDING_OUTPUT_POPULATION)
    assert len(dnp01_ids) == 2
    indices = registry.population_indices(config.DESCENDING_OUTPUT_POPULATION)
    assert indices.shape == (2,)


def test_manifest_has_required_provenance_fields(built_fixture_connectome, isolated_derived_paths):
    _registry, _connectome, manifest = built_fixture_connectome
    for key in (
        "dataset_version",
        "source_checksums_sha256",
        "neuron_count",
        "neuron_pair_count",
        "synapse_count",
        "build_timestamp_utc",
        "git_commit",
        "python_version",
        "platform",
    ):
        assert key in manifest

    on_disk = json.loads(config.BUILD_MANIFEST.read_text())
    assert on_disk == manifest


def test_unknown_dataset_version_raises(fixture_dir):
    from config import DatasetValidationError

    try:
        validate_dataset(fixture_dir, dataset_version="not_a_real_version")
        assert False, "expected DatasetValidationError"
    except DatasetValidationError:
        pass


def test_validate_with_checklist_all_stages_pass_for_fixture(fixture_dir):
    stages = list(validate_with_checklist(fixture_dir, dataset_version="test_fixture_v0"))
    assert all(passed for _label, passed, _detail in stages)
    labels = [label for label, _passed, _detail in stages]
    assert "Dataset files present" in labels
    assert "Dataset loads" in labels
    assert any("neurons confirmed" in label for label in labels)
    assert any("pairwise connections confirmed" in label for label in labels)
    assert any("synapses confirmed" in label for label in labels)
    assert "LC4 population found" in labels
    assert "LPLC2 population found" in labels
    assert f"{config.DESCENDING_OUTPUT_POPULATION} / Giant Fibre identified" in labels


def test_validate_with_checklist_stops_at_first_failure(invalid_fixture_dir):
    stages = list(validate_with_checklist(invalid_fixture_dir, dataset_version="test_fixture_v0"))
    assert stages[-1][1] is False  # last yielded stage failed
    assert all(passed for _label, passed, _detail in stages[:-1])  # everything before it passed


def test_validate_with_checklist_wrong_dataset_version_fails_at_counts(fixture_dir):
    stages = list(validate_with_checklist(fixture_dir, dataset_version="FAFB_v783"))
    labels_and_pass = {label: passed for label, passed, _detail in stages}
    assert labels_and_pass["139,255 neurons confirmed"] is False
