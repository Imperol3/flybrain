"""Generates the small synthetic FlyWire-schema fixture files used by the test suite.

These are NOT real FlyWire data and make NO biological claims — they exist
only to exercise the loading/validation/connectome-build/simulation code
paths deterministically without requiring a licensed FlyWire download. See
tests/fixtures/README.md.

Run with: python tests/fixtures/generate_fixtures.py
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pandas as pd

FIXTURES_DIR = Path(__file__).resolve().parent
GOOD_DIR = FIXTURES_DIR
INVALID_DIR = FIXTURES_DIR / "invalid_neuron_ref"

# Synthetic root IDs live in the same numeric range as real FlyWire root IDs
# (720575940xxxxxxxx) purely so downstream int64 handling is exercised
# realistically; the values themselves are arbitrary.
BASE_ID = 720_575_940_000_000_000

# id offset -> (population/type label, neurotransmitter, side)
# side values ("left"/"right") match the REAL FlyWire classification.csv
# convention exactly (confirmed against the real download) — not the "L"/"R"
# abbreviation an earlier version of this fixture guessed at.
NEURONS = {
    1: ("LC4", "ACH", "left"),
    2: ("LC4", "ACH", "left"),
    3: ("LC4", "ACH", "right"),
    4: ("LC4", "ACH", "right"),
    5: ("LPLC2", "ACH", "left"),
    6: ("LPLC2", "ACH", "left"),
    7: ("LPLC2", "ACH", "right"),
    8: ("LPLC2", "ACH", "right"),
    9: ("relay_L", "ACH", "left"),
    10: ("relay_L", "ACH", "right"),
    11: ("relay_P", "ACH", "left"),
    12: ("relay_P", "ACH", "right"),
    13: ("convergence", "ACH", "left"),
    14: ("convergence", "ACH", "right"),
    15: ("DNp01", "ACH", "left"),
    16: ("DNp01", "ACH", "right"),
    17: ("inhibitory_control", "GABA", "left"),
    18: ("inhibitory_control", "GABA", "right"),
    19: ("isolated_decoy", "ACH", "left"),
    20: ("isolated_decoy", "ACH", "right"),
    21: ("isolated_decoy", "ACH", "left"),
    22: ("unrelated_chain", "ACH", "left"),
    23: ("unrelated_chain", "ACH", "right"),
    24: ("unrelated_chain", "ACH", "left"),
    # Steering descending neurons (Phase 0D). Real FlyWire has exactly 2 of
    # each (one per side) — mirrored here so the lateralized-stimulus
    # routing and DNa02_L/DNa02_R readout logic can be exercised on the
    # fixture without real data.
    25: ("DNa02", "ACH", "left"),
    26: ("DNa02", "ACH", "right"),
}

# (pre_offset, post_offset, syn_count)
CONNECTIONS = []


def _fan_out(pre_offsets, post_offsets, syn_count):
    for pre in pre_offsets:
        for post in post_offsets:
            CONNECTIONS.append((pre, post, syn_count))


_fan_out([1, 2, 3, 4], [9, 10], 40)       # LC4 -> relay_L
_fan_out([5, 6, 7, 8], [11, 12], 40)      # LPLC2 -> relay_P
_fan_out([9, 10], [13, 14], 60)           # relay_L -> convergence
_fan_out([11, 12], [13, 14], 60)          # relay_P -> convergence
_fan_out([13, 14], [15, 16], 80)          # convergence -> DNp01
_fan_out([1, 2], [17, 18], 20)            # LC4 -> inhibitory_control
_fan_out([17, 18], [13, 14], 5)           # inhibitory_control -| convergence (weak)
_fan_out([22], [23], 30)                  # unrelated chain
_fan_out([23], [24], 30)
_fan_out([1, 2, 5, 6], [25], 50)          # left LC4/LPLC2 -> DNa02 (left)
_fan_out([3, 4, 7, 8], [26], 50)          # right LC4/LPLC2 -> DNa02 (right)


def root_id(offset: int) -> int:
    return BASE_ID + offset


def _write_gz_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        df.to_csv(fh, index=False)


def build_neurons_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "root_id": [root_id(o) for o in NEURONS],
            "nt_type": [nt for _, nt, _side in NEURONS.values()],
            "nt_type_score": [0.95 for _ in NEURONS],
        }
    )


def build_classification_df() -> pd.DataFrame:
    rows = []
    for offset, (label, _nt, side) in NEURONS.items():
        rows.append(
            {
                "root_id": root_id(offset),
                "super_class": "visual" if "LC4" in label or "LPLC2" in label else "central",
                "class": label,
                "sub_class": "",
                "side": side,
                "nerve": "",
            }
        )
    return pd.DataFrame(rows)


def build_consolidated_cell_types_df() -> pd.DataFrame:
    named_types = ("LC4", "LPLC2", "DNp01", "DNa02")
    rows = []
    for offset, (label, _nt, _side) in NEURONS.items():
        primary_type = label if label in named_types else "unclassified"
        rows.append({"root_id": root_id(offset), "primary_type": primary_type})
    return pd.DataFrame(rows)


def build_connections_df(connections=None) -> pd.DataFrame:
    connections = CONNECTIONS if connections is None else connections
    return pd.DataFrame(
        {
            "pre_root_id": [root_id(pre) for pre, _post, _n in connections],
            "post_root_id": [root_id(post) for _pre, post, _n in connections],
            "neuropil": ["TEST_NEUROPIL" for _ in connections],
            "syn_count": [n for _pre, _post, n in connections],
            "nt_type": [NEURONS[pre][1] for pre, _post, _n in connections],
        }
    )


def build_coordinates_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "root_id": [root_id(o) for o in NEURONS],
            "pos_x_nm": [float(o * 1000) for o in NEURONS],
            "pos_y_nm": [float(o * 2000) for o in NEURONS],
            "pos_z_nm": [float(o * 3000) for o in NEURONS],
        }
    )


def build_column_assignment_df() -> pd.DataFrame:
    visual_offsets = [o for o, (label, _nt, _side) in NEURONS.items() if label in ("LC4", "LPLC2")]
    return pd.DataFrame(
        {
            "root_id": [root_id(o) for o in visual_offsets],
            "column_id": [o % 8 for o in visual_offsets],
        }
    )


def build_labels_df() -> pd.DataFrame:
    annotated = [1, 5, 15]
    return pd.DataFrame(
        {
            "root_id": [root_id(o) for o in annotated],
            "label": [f"synthetic fixture neuron {o}" for o in annotated],
        }
    )


def build_visual_neuron_types_df() -> pd.DataFrame:
    visual_offsets = [o for o, (label, _nt, _side) in NEURONS.items() if label in ("LC4", "LPLC2")]
    return pd.DataFrame(
        {
            "root_id": [root_id(o) for o in visual_offsets],
            "type": [NEURONS[o][0] for o in visual_offsets],
        }
    )


def write_fixture_set(target_dir: Path, connections=None) -> None:
    _write_gz_csv(build_neurons_df(), target_dir / "neurons.csv.gz")
    _write_gz_csv(build_classification_df(), target_dir / "classification.csv.gz")
    _write_gz_csv(build_consolidated_cell_types_df(), target_dir / "consolidated_cell_types.csv.gz")
    _write_gz_csv(build_connections_df(connections), target_dir / "connections_princeton.csv.gz")
    _write_gz_csv(build_coordinates_df(), target_dir / "coordinates.csv.gz")
    _write_gz_csv(build_column_assignment_df(), target_dir / "column_assignment.csv.gz")
    _write_gz_csv(build_labels_df(), target_dir / "labels.csv.gz")
    _write_gz_csv(build_visual_neuron_types_df(), target_dir / "visual_neuron_types.csv.gz")


def main() -> None:
    write_fixture_set(GOOD_DIR)

    # A second fixture set whose connections file references a root_id that
    # does not exist in neurons.csv.gz, for the "invalid/fabricated neuron
    # IDs rejected" test (brief section 13).
    bad_connections = list(CONNECTIONS) + [(1, 9999, 10)]  # 9999 has no matching neuron row
    write_fixture_set(INVALID_DIR, connections=bad_connections)

    n_neurons = len(NEURONS)
    n_edges = len(CONNECTIONS)
    n_synapses = sum(n for *_, n in CONNECTIONS)
    print(f"Wrote fixtures to {GOOD_DIR}")
    print(f"  neurons={n_neurons} neuron_pairs={n_edges} synapses={n_synapses}")
    print(f"Wrote invalid-reference fixtures to {INVALID_DIR}")


if __name__ == "__main__":
    main()
