"""Dataset configuration and provenance: env var handling, declared expected counts."""

import pytest

import config


def test_get_flywire_dir_raises_when_env_unset(monkeypatch):
    monkeypatch.delenv(config.FLYWIRE_V783_DIR_ENV, raising=False)
    with pytest.raises(config.DatasetConfigError):
        config.get_flywire_dir()


def test_get_flywire_dir_raises_when_dir_missing(monkeypatch, tmp_path):
    monkeypatch.setenv(config.FLYWIRE_V783_DIR_ENV, str(tmp_path / "does_not_exist"))
    with pytest.raises(config.DatasetConfigError):
        config.get_flywire_dir()


def test_get_flywire_dir_returns_path_when_valid(monkeypatch, fixture_dir):
    monkeypatch.setenv(config.FLYWIRE_V783_DIR_ENV, str(fixture_dir))
    assert config.get_flywire_dir() == fixture_dir


def test_dataset_version_defaults_to_fafb_v783(monkeypatch):
    monkeypatch.delenv(config.FLYWIRE_DATASET_VERSION_ENV, raising=False)
    assert config.get_dataset_version() == "FAFB_v783"


def test_dataset_version_reads_env_override(monkeypatch):
    monkeypatch.setenv(config.FLYWIRE_DATASET_VERSION_ENV, "test_fixture_v0")
    assert config.get_dataset_version() == "test_fixture_v0"


def test_required_source_files_match_brief():
    expected = {
        "neurons.csv.gz",
        "classification.csv.gz",
        "consolidated_cell_types.csv.gz",
        "connections_princeton.csv.gz",
        "coordinates.csv.gz",
        "column_assignment.csv.gz",
        "labels.csv.gz",
        "visual_neuron_types.csv.gz",
    }
    assert set(config.REQUIRED_SOURCE_FILES) == expected


def test_fafb_v783_expected_counts_match_reference_brief():
    expected = config.EXPECTED_COUNTS["FAFB_v783"]
    assert expected["neurons"] == 139_255
    assert expected["neuron_pairs"] == 3_732_460
    assert expected["synapses"] == 50_666_648


def test_fafb_v783_expected_population_counts_match_reference_brief():
    expected = config.EXPECTED_POPULATION_COUNTS["FAFB_v783"]
    assert expected["LC4"] == 104
    assert expected["LPLC2"] == 210
