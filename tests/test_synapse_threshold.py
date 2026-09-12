"""Per-pair synapse-count threshold: discovered (not invented) to reproduce
the documented FAFB_v783 reference counts from a real-world mirror whose raw
connections file has no such threshold applied. See config.py
CONNECTION_MIN_SYNAPSES_PER_PAIR and docs/DATA_PROVENANCE.md.
"""

from __future__ import annotations

import pandas as pd

import config
from brain.connectivity.validation import apply_synapse_threshold


def _connections_df():
    # Pair (1,2): two neuropil rows summing to 4 synapses (below a threshold of 5).
    # Pair (1,3): one row with 10 synapses (above threshold).
    # Pair (2,3): two rows summing to exactly 5 (at threshold).
    return pd.DataFrame(
        {
            "pre_root_id": [1, 1, 1, 2, 2],
            "post_root_id": [2, 2, 3, 3, 3],
            "neuropil": ["A", "B", "A", "A", "B"],
            "syn_count": [3, 1, 10, 2, 3],
            "nt_type": ["ACH", "ACH", "ACH", "ACH", "ACH"],
        }
    )


def test_no_filtering_when_threshold_is_one_or_unset():
    df = _connections_df()
    result = apply_synapse_threshold(df, dataset_version="FAFB_v783")
    assert len(result) == len(df)


def test_threshold_drops_pairs_below_cutoff(monkeypatch):
    monkeypatch.setitem(config.CONNECTION_MIN_SYNAPSES_PER_PAIR, "unit_test_version", 5)
    df = _connections_df()
    result = apply_synapse_threshold(df, dataset_version="unit_test_version")

    remaining_pairs = set(zip(result["pre_root_id"], result["post_root_id"]))
    assert (1, 2) not in remaining_pairs  # total 4 < 5, dropped
    assert (1, 3) in remaining_pairs      # total 10 >= 5, kept
    assert (2, 3) in remaining_pairs      # total 5 >= 5, kept (boundary inclusive)


def test_threshold_is_idempotent(monkeypatch):
    monkeypatch.setitem(config.CONNECTION_MIN_SYNAPSES_PER_PAIR, "unit_test_version", 5)
    df = _connections_df()
    once = apply_synapse_threshold(df, dataset_version="unit_test_version")
    twice = apply_synapse_threshold(once, dataset_version="unit_test_version")
    assert len(once) == len(twice)
    assert set(zip(once["pre_root_id"], once["post_root_id"])) == set(
        zip(twice["pre_root_id"], twice["post_root_id"])
    )


def test_kaggle_mirror_dataset_version_declared_with_discovered_counts():
    expected = config.EXPECTED_COUNTS["FAFB_v783_kaggle_mirror"]
    assert expected["neurons"] == 139_255
    assert config.CONNECTION_MIN_SYNAPSES_PER_PAIR["FAFB_v783_kaggle_mirror"] == 5
    # Deliberately NOT equal to the official FAFB_v783 numbers — this dataset
    # version documents an empirically observed, distinct snapshot.
    assert expected["neuron_pairs"] != config.EXPECTED_COUNTS["FAFB_v783"]["neuron_pairs"]
