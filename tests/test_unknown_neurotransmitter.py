"""Missing (NaN) neurotransmitter predictions are a real, expected condition in
FlyWire's own data (confirmed against the real FAFB v783 download: ~14% of
neurons, ~6.5% of connection rows). These are excluded from signed weight
(never guessed) but still counted in structural validation — see
docs/BIOLOGICAL_ASSUMPTIONS.md. A genuinely unrecognized non-null NT value
must still fail loudly.
"""

from __future__ import annotations

import gzip
import shutil

import pandas as pd
import pytest

import config
from brain.connectivity.build_connectome import build
from brain.connectivity.validation import validate_dataset
from config import DatasetValidationError
from tests.fixtures.generate_fixtures import CONNECTIONS, NEURONS, root_id


def _write_gz_csv(df, path):
    with gzip.open(path, "wt", newline="") as fh:
        df.to_csv(fh, index=False)


def _fixture_dir_with_missing_nt(fixture_dir, tmp_path, *, bad_value=None):
    """Copy the canonical fixture, but null out (or corrupt) one neuron's and
    one connection's nt_type.
    """
    target = tmp_path / "missing_nt"
    target.mkdir()
    for name in config.REQUIRED_SOURCE_FILES:
        shutil.copy(fixture_dir / name, target / name)

    with gzip.open(fixture_dir / "neurons.csv.gz", "rt") as fh:
        neurons_df = pd.read_csv(fh)
    neurons_df.loc[neurons_df["root_id"] == root_id(1), "nt_type"] = bad_value
    _write_gz_csv(neurons_df, target / "neurons.csv.gz")

    connections_df = pd.DataFrame(
        {
            "pre_root_id": [root_id(pre) for pre, _post, _n in CONNECTIONS],
            "post_root_id": [root_id(post) for _pre, post, _n in CONNECTIONS],
            "neuropil": ["TEST_NEUROPIL" for _ in CONNECTIONS],
            "syn_count": [n for _pre, _post, n in CONNECTIONS],
            "nt_type": [NEURONS[pre][1] for pre, _post, _n in CONNECTIONS],
        }
    )
    connections_df.loc[0, "nt_type"] = bad_value
    _write_gz_csv(connections_df, target / "connections_princeton.csv.gz")

    return target


def test_missing_nt_does_not_fail_validation(fixture_dir, tmp_path):
    target = _fixture_dir_with_missing_nt(fixture_dir, tmp_path, bad_value=None)
    report = validate_dataset(target, dataset_version="test_fixture_v0")
    assert report.unknown_nt_neuron_count == 1
    assert report.unknown_nt_connection_count == 1
    # Structural counts are unaffected by the missing NT.
    assert report.neuron_count == 26
    assert report.neuron_pair_count == 46
    assert report.synapse_count == 2_000


def test_unrecognized_non_null_nt_still_fails(fixture_dir, tmp_path):
    target = _fixture_dir_with_missing_nt(fixture_dir, tmp_path, bad_value="TOTALLY_UNKNOWN_NT")
    with pytest.raises(DatasetValidationError, match="Unknown neurotransmitter type"):
        validate_dataset(target, dataset_version="test_fixture_v0")


def test_build_zero_weights_missing_nt_connection(fixture_dir, tmp_path, isolated_derived_paths):
    import scipy.sparse as sp

    target = _fixture_dir_with_missing_nt(fixture_dir, tmp_path, bad_value=None)
    manifest = build(flywire_dir=target, dataset_version="test_fixture_v0")

    assert manifest["unknown_nt_neuron_count"] == 1
    assert manifest["unknown_nt_connection_count"] == 1
    # Still counted structurally even though excluded from signal.
    assert manifest["neuron_pair_count"] == 46
    assert manifest["synapse_count"] == 2_000

    connectome = sp.load_npz(config.CONNECTOME_NPZ)
    # The first CONNECTIONS edge (whose nt_type we nulled) must now carry
    # zero weight rather than a guessed sign.
    pre_offset, post_offset, _syn_count = CONNECTIONS[0]
    root_ids = sorted(root_id(o) for o in NEURONS)
    pre_idx = root_ids.index(root_id(pre_offset))
    post_idx = root_ids.index(root_id(post_offset))
    assert connectome[pre_idx, post_idx] == 0
