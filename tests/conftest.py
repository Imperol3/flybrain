from __future__ import annotations

from pathlib import Path

import pytest
import scipy.sparse as sp

import config
from brain.connectivity import build_connectome
from brain.neurons import registry as registry_module

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
INVALID_FIXTURES_DIR = FIXTURES_DIR / "invalid_neuron_ref"
FIXTURE_DATASET_VERSION = "test_fixture_v0"


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def invalid_fixture_dir() -> Path:
    return INVALID_FIXTURES_DIR


@pytest.fixture
def isolated_derived_paths(tmp_path, monkeypatch):
    """Redirect config's derived/metadata/output paths into a per-test tmp dir
    so tests never touch (or depend on) data/derived in the real project tree.
    """
    derived = tmp_path / "derived"
    metadata = tmp_path / "metadata"
    outputs = tmp_path / "outputs"
    monkeypatch.setattr(config, "DERIVED_DIR", derived)
    monkeypatch.setattr(config, "METADATA_DIR", metadata)
    monkeypatch.setattr(config, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config, "CONNECTOME_NPZ", derived / "connectome.npz")
    monkeypatch.setattr(config, "CONNECTOME_INDEX", derived / "connectome_index.json")
    monkeypatch.setattr(config, "BUILD_MANIFEST", metadata / "build_manifest.json")
    monkeypatch.setattr(config, "RUN_LEDGER_PATH", metadata / "run_ledger.jsonl")
    return {"derived": derived, "metadata": metadata, "outputs": outputs}


@pytest.fixture
def built_fixture_connectome(fixture_dir, isolated_derived_paths):
    """Build the connectome from the synthetic fixtures into an isolated tmp dir
    and return (registry, connectome, manifest).
    """
    manifest = build_connectome.build(flywire_dir=fixture_dir, dataset_version=FIXTURE_DATASET_VERSION)
    registry = registry_module.load(isolated_derived_paths["derived"] / "connectome_index.json")
    connectome = sp.load_npz(isolated_derived_paths["derived"] / "connectome.npz")
    return registry, connectome, manifest
