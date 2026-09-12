"""Build the sparse signed connectome from validated FlyWire source data.

Usage:
    FLYWIRE_V783_DIR=/path/to/data python -m brain.connectivity.build_connectome

Writes:
    data/derived/connectome.npz        - scipy.sparse CSR matrix, signed synapse counts
    data/derived/connectome_index.json - root_id <-> matrix index, named populations
    data/metadata/build_manifest.json  - dataset version, checksums, counts, timestamp, git commit

Deliberately never allocates a dense (n_neurons x n_neurons) matrix (brief
section 7): the CSR matrix is built directly from (row, col, data) triplets.

The stored matrix holds *signed synapse counts*, not physiological weights —
converting synapse count to a synaptic effect (the w_synapse_mV scaling) is a
neuron-model concern and is applied in simulation.engine.lif_engine, not
baked into this biological-data layer (brief section 15).

Connections whose predicted neurotransmitter is missing (NaN — a real,
documented gap in FlyWire's own predictions, not a data error) get a signed
weight of exactly zero: they are excluded from signal propagation but are
still counted in the structural validation totals (neuron/pair/synapse
counts are graph-scale metrics, independent of sign). See
docs/BIOLOGICAL_ASSUMPTIONS.md for the full decision record and observed
real-data rates.
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

import config
from brain import provenance
from brain.connectivity import loaders, validation
from brain.neurons.registry import NeuronRegistry
from brain.neurons import registry as registry_module


def _signed_weight(nt_types) -> np.ndarray:
    """Excitatory -> +1, inhibitory -> -1, anything else (including missing/
    NaN, already validated as the only permitted "anything else" — see
    validation._check_neurotransmitter_signs_known) -> 0, i.e. excluded from
    signal propagation without guessing a sign.

    `nt_types` may contain pandas NA (nullable "string" dtype) for missing
    predictions. NA compares as NA (not False) under plain `==`, which makes
    np.isin raise ("boolean value of NA is ambiguous") — so NA is filled
    with a sentinel that cannot match either known set before comparing.
    """
    filled = pd.Series(nt_types).fillna("__UNKNOWN_NT__").to_numpy()
    sign = np.zeros(len(filled), dtype=np.int8)
    excitatory_mask = np.isin(filled, list(config.EXCITATORY_NEUROTRANSMITTERS))
    inhibitory_mask = np.isin(filled, list(config.INHIBITORY_NEUROTRANSMITTERS))
    sign[excitatory_mask] = 1
    sign[inhibitory_mask] = -1
    return sign


def build(flywire_dir=None, dataset_version: str | None = None) -> dict:
    flywire_dir = flywire_dir or config.get_flywire_dir()
    dataset_version = dataset_version or config.get_dataset_version()

    neurons = loaders.load_neurons(flywire_dir)
    connections = loaders.load_connections(flywire_dir)
    cell_types = loaders.load_consolidated_cell_types(flywire_dir)
    classification = loaders.load_classification(flywire_dir)

    report = validation.validate_dataset(
        flywire_dir,
        dataset_version,
        neurons=neurons,
        connections=connections,
        cell_types=cell_types,
    )

    # Same synapse-count-per-pair threshold validate_dataset() applied
    # internally (config.CONNECTION_MIN_SYNAPSES_PER_PAIR) — applied again
    # here to this function's own local `connections`, since validate_dataset
    # filters its own copy without mutating the caller's. Idempotent, so
    # this is safe even though validate_dataset already did it once.
    connections = validation.apply_synapse_threshold(connections, dataset_version)

    root_ids = sorted(neurons["root_id"].tolist())
    id_to_index = {rid: i for i, rid in enumerate(root_ids)}

    rows = connections["pre_root_id"].map(id_to_index).to_numpy()
    cols = connections["post_root_id"].map(id_to_index).to_numpy()
    sign = _signed_weight(connections["nt_type"])
    data = connections["syn_count"].to_numpy() * sign

    n = len(root_ids)
    connectome = sp.coo_matrix((data, (rows, cols)), shape=(n, n)).tocsr()
    # Duplicate (pre, post) pairs across neuropils are summed by coo->csr
    # conversion, which matches "total synapses between this ordered pair".

    side_by_root_id = dict(zip(classification["root_id"], classification["side"]))

    populations: dict[str, tuple[int, ...]] = {}
    for name in sorted(cell_types["primary_type"].dropna().unique()):
        if not name or name == "unclassified":
            continue
        ids = tuple(sorted(cell_types.loc[cell_types["primary_type"] == name, "root_id"].tolist()))
        if not ids:
            continue
        populations[name] = ids

        # Side-qualified variants (e.g. "DNa02_L", "DNa02_R") for any type
        # whose members have a documented left/right side in classification.csv
        # — needed for lateralized stimulus routing and steering readouts
        # (Phase 0D). Not every type splits cleanly (some neurons have no
        # side, e.g. midline cells); those are simply absent from the L/R
        # variant rather than guessed.
        left_ids = tuple(sorted(rid for rid in ids if side_by_root_id.get(rid) == "left"))
        right_ids = tuple(sorted(rid for rid in ids if side_by_root_id.get(rid) == "right"))
        if left_ids:
            populations[f"{name}_L"] = left_ids
        if right_ids:
            populations[f"{name}_R"] = right_ids

    reg = NeuronRegistry(root_ids=tuple(root_ids), populations=populations, dataset_version=dataset_version)

    config.DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    config.METADATA_DIR.mkdir(parents=True, exist_ok=True)
    sp.save_npz(config.CONNECTOME_NPZ, connectome)
    registry_module.save(reg, config.CONNECTOME_INDEX)

    manifest = {
        "dataset_version": report.dataset_version,
        "flywire_dir": report.flywire_dir,
        "source_checksums_sha256": report.checksums,
        "neuron_count": report.neuron_count,
        "neuron_pair_count": report.neuron_pair_count,
        "synapse_count": report.synapse_count,
        "population_counts": report.population_counts,
        "unknown_nt_neuron_count": report.unknown_nt_neuron_count,
        "unknown_nt_connection_count": report.unknown_nt_connection_count,
        "build_timestamp_utc": provenance.utc_now_iso(),
        "git_commit": provenance.get_git_commit(),
        "python_version": provenance.python_version(),
        "platform": provenance.platform_summary(),
    }
    config.BUILD_MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    start = time.monotonic()
    manifest = build()
    elapsed = time.monotonic() - start
    print(f"Connectome build OK ({manifest['dataset_version']}) in {elapsed:.2f}s")
    print(f"  neurons={manifest['neuron_count']:,}")
    print(f"  neuron_pairs={manifest['neuron_pair_count']:,}")
    print(f"  synapses={manifest['synapse_count']:,}")
    print(f"  populations: {manifest['population_counts']}")
    if manifest["unknown_nt_neuron_count"] or manifest["unknown_nt_connection_count"]:
        print(
            f"  unknown NT (excluded from signal, kept in counts): "
            f"{manifest['unknown_nt_neuron_count']:,} neurons, "
            f"{manifest['unknown_nt_connection_count']:,} connections"
        )
    print(f"  wrote {config.CONNECTOME_NPZ}")
    print(f"  wrote {config.CONNECTOME_INDEX}")
    print(f"  wrote {config.BUILD_MANIFEST}")


if __name__ == "__main__":
    main()
