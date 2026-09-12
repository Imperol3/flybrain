"""Dataset validation: required files, checksums, schema, and scale counts.

Per the brief: the application must fail clearly (not silently substitute
fake data) when the environment variable is missing, required files are
missing, the dataset version is wrong, or validation fails.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import config
from config import DatasetValidationError
from brain.connectivity import loaders


@dataclass(frozen=True)
class ValidationReport:
    dataset_version: str
    flywire_dir: str
    checksums: dict[str, str]
    neuron_count: int
    neuron_pair_count: int
    synapse_count: int
    population_counts: dict[str, int]
    unknown_nt_neuron_count: int = 0
    unknown_nt_connection_count: int = 0


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_required_files_present(flywire_dir: Path) -> None:
    """Every canonical required file must resolve (canonical name or a
    documented alias — config.SOURCE_FILE_ALIASES) to an existing path.
    """
    missing = []
    for name in config.REQUIRED_SOURCE_FILES:
        try:
            loaders.resolve_source_file(flywire_dir, name)
        except DatasetValidationError:
            missing.append(name)
    if missing:
        raise DatasetValidationError(
            f"Missing required FlyWire source file(s) in {flywire_dir}: {missing} "
            f"(canonical name or a documented alias — see config.SOURCE_FILE_ALIASES). "
            "See README.md for how to obtain and place the FAFB v783 download."
        )


def compute_checksums(flywire_dir: Path) -> dict[str, str]:
    """Checksums keyed by each file's CANONICAL name, even when the file on
    disk was found under a documented alias — the manifest should be
    comparable across differently-named exports of the same dataset.
    """
    return {name: _sha256_of(loaders.resolve_source_file(flywire_dir, name)) for name in config.REQUIRED_SOURCE_FILES}


def _check_neuron_ids_exist(neuron_ids: set[int], connections) -> None:
    referenced = set(connections["pre_root_id"]).union(connections["post_root_id"])
    unknown = referenced - neuron_ids
    if unknown:
        sample = sorted(unknown)[:10]
        raise DatasetValidationError(
            f"connections_princeton.csv.gz references {len(unknown)} root_id(s) not present in "
            f"neurons.csv.gz (e.g. {sample}). Refusing to build a connectome with fabricated/unknown neuron IDs."
        )


def _check_neurotransmitter_signs_known(nt_types) -> None:
    """Any nt_type value we don't have a documented sign for is a hard
    failure — EXCEPT a missing/NaN value, which is a real, expected, and
    documented condition in FlyWire's own predictions (not every neuron has
    a confident neurotransmitter call). Missing values are handled as a
    distinct "unknown" case (zero signed weight, never guessed) — see
    docs/BIOLOGICAL_ASSUMPTIONS.md section on missing neurotransmitter
    predictions. This still fails hard on any OTHER unrecognized non-null
    string (e.g. a typo, or a genuinely new NT category not yet mapped).
    """
    known = config.EXCITATORY_NEUROTRANSMITTERS | config.INHIBITORY_NEUROTRANSMITTERS
    series = pd.Series(nt_types)
    non_null_values = set(series.dropna().unique())
    unknown = non_null_values - known
    if unknown:
        raise DatasetValidationError(
            f"Unknown neurotransmitter type(s) {sorted(unknown)} with no documented excitatory/inhibitory "
            "sign in config.py. Refusing to silently assume a sign — add the mapping and document why."
        )


def _count_missing_nt(nt_types) -> int:
    return int(pd.Series(nt_types).isna().sum())


def apply_synapse_threshold(connections: pd.DataFrame, dataset_version: str) -> pd.DataFrame:
    """Aggregate multi-neuropil rows for the same (pre,post) pair and drop
    pairs whose total synapse count is below
    config.CONNECTION_MIN_SYNAPSES_PER_PAIR for this dataset version
    (default 1 = no filtering).

    Idempotent: filtering an already-filtered frame with the same threshold
    is a no-op, so this is safe to call from both validate_dataset() (which
    may receive already-filtered connections from build_connectome.build())
    and independently inside build_connectome.build() itself.
    """
    min_synapses = config.CONNECTION_MIN_SYNAPSES_PER_PAIR.get(dataset_version, 1)
    if min_synapses <= 1:
        return connections
    pair_totals = connections.groupby(["pre_root_id", "post_root_id"])["syn_count"].transform("sum")
    return connections.loc[pair_totals >= min_synapses].reset_index(drop=True)


def _check_counts(dataset_version: str, neuron_count: int, neuron_pair_count: int, synapse_count: int) -> None:
    expected = config.EXPECTED_COUNTS.get(dataset_version)
    if expected is None:
        raise DatasetValidationError(
            f"Unknown dataset version {dataset_version!r}; no expected counts declared in config.py. "
            f"Set {config.FLYWIRE_DATASET_VERSION_ENV} to one of {sorted(config.EXPECTED_COUNTS)}."
        )
    actual = {"neurons": neuron_count, "neuron_pairs": neuron_pair_count, "synapses": synapse_count}
    mismatches = {k: (expected[k], actual[k]) for k in expected if expected[k] != actual[k]}
    if mismatches:
        details = ", ".join(f"{k}: expected {exp:,} got {act:,}" for k, (exp, act) in mismatches.items())
        raise DatasetValidationError(
            f"Dataset scale mismatch for version {dataset_version!r}: {details}. "
            "Stopping rather than continuing with a dataset that does not match the declared version."
        )


def _check_population_counts(dataset_version: str, population_counts: dict[str, int]) -> None:
    expected = config.EXPECTED_POPULATION_COUNTS.get(dataset_version, {})
    mismatches = {
        name: (exp, population_counts.get(name, 0))
        for name, exp in expected.items()
        if population_counts.get(name, 0) != exp
    }
    if mismatches:
        details = ", ".join(f"{k}: expected {exp} got {act}" for k, (exp, act) in mismatches.items())
        raise DatasetValidationError(f"Cell population count mismatch for {dataset_version!r}: {details}")


def validate_dataset(
    flywire_dir: Path,
    dataset_version: str | None = None,
    *,
    neurons=None,
    connections=None,
    cell_types=None,
) -> ValidationReport:
    """Run the full V0 validation pipeline and return a report, or raise DatasetValidationError.

    `neurons`/`connections`/`cell_types` may be passed in already-loaded (as
    used by build_connectome.py) to avoid reading the large connections file
    twice; otherwise they are loaded here.
    """
    dataset_version = dataset_version or config.get_dataset_version()

    check_required_files_present(flywire_dir)
    checksums = compute_checksums(flywire_dir)

    neurons = loaders.load_neurons(flywire_dir) if neurons is None else neurons
    connections = loaders.load_connections(flywire_dir) if connections is None else connections
    cell_types = loaders.load_consolidated_cell_types(flywire_dir) if cell_types is None else cell_types

    # Files validated for schema/presence only in V0 (not consumed by compute).
    loaders.load_classification(flywire_dir)
    loaders.load_coordinates(flywire_dir)
    loaders.load_column_assignment(flywire_dir)
    loaders.load_labels(flywire_dir)
    loaders.load_visual_neuron_types(flywire_dir)

    neuron_ids = set(neurons["root_id"])
    # Fabricated/unknown-ID check runs on the RAW connections, before any
    # synapse-count threshold filtering, so a low-synapse fabricated edge
    # can't slip through by being filtered out first.
    _check_neuron_ids_exist(neuron_ids, connections)

    connections = apply_synapse_threshold(connections, dataset_version)

    _check_neurotransmitter_signs_known(neurons["nt_type"])
    _check_neurotransmitter_signs_known(connections["nt_type"])

    neuron_count = len(neuron_ids)
    neuron_pair_count = connections[["pre_root_id", "post_root_id"]].drop_duplicates().shape[0]
    synapse_count = int(connections["syn_count"].sum())
    unknown_nt_neuron_count = _count_missing_nt(neurons["nt_type"])
    unknown_nt_connection_count = _count_missing_nt(connections["nt_type"])

    population_counts = {
        name: int((cell_types["primary_type"] == name).sum())
        for name in set(config.EXPECTED_POPULATION_COUNTS.get(dataset_version, {})) | {config.DESCENDING_OUTPUT_POPULATION}
    }

    _check_counts(dataset_version, neuron_count, neuron_pair_count, synapse_count)
    _check_population_counts(dataset_version, population_counts)

    return ValidationReport(
        dataset_version=dataset_version,
        flywire_dir=str(flywire_dir),
        checksums=checksums,
        neuron_count=neuron_count,
        neuron_pair_count=neuron_pair_count,
        synapse_count=synapse_count,
        population_counts=population_counts,
        unknown_nt_neuron_count=unknown_nt_neuron_count,
        unknown_nt_connection_count=unknown_nt_connection_count,
    )


def validate_with_checklist(flywire_dir: Path, dataset_version: str | None = None):
    """Step-by-step version of validate_dataset() that yields (label, passed,
    detail) after each stage instead of only raising/returning at the end.

    Used by experiments/phase_0b/step0_validate_dataset.py to print exactly
    the checklist requested for real-data validation:

        Dataset loads -> neuron count confirmed -> connection count confirmed
        -> synapse count confirmed -> LC4 found -> LPLC2 found -> DNp01 identified

    Stops (does not yield further stages) after the first failure — this
    function performs NO simulation, only the checks above.
    """
    dataset_version = dataset_version or config.get_dataset_version()

    try:
        check_required_files_present(flywire_dir)
    except DatasetValidationError as exc:
        yield ("Dataset files present", False, str(exc))
        return
    yield ("Dataset files present", True, f"{len(config.REQUIRED_SOURCE_FILES)} required files found")

    try:
        neurons = loaders.load_neurons(flywire_dir)
        connections = loaders.load_connections(flywire_dir)
        cell_types = loaders.load_consolidated_cell_types(flywire_dir)
    except DatasetValidationError as exc:
        yield ("Dataset loads", False, str(exc))
        return
    yield ("Dataset loads", True, f"{len(neurons)} neuron rows, {len(connections)} connection rows")

    try:
        neuron_ids = set(neurons["root_id"])
        _check_neuron_ids_exist(neuron_ids, connections)
    except DatasetValidationError as exc:
        yield ("Neuron IDs and neurotransmitter signs valid", False, str(exc))
        return

    min_synapses = config.CONNECTION_MIN_SYNAPSES_PER_PAIR.get(dataset_version, 1)
    connections = apply_synapse_threshold(connections, dataset_version)
    if min_synapses > 1:
        yield (
            "Synapse-count-per-pair threshold applied",
            True,
            f">= {min_synapses} synapses/pair, {len(connections):,} rows remain",
        )

    try:
        _check_neurotransmitter_signs_known(neurons["nt_type"])
        _check_neurotransmitter_signs_known(connections["nt_type"])
    except DatasetValidationError as exc:
        yield ("Neuron IDs and neurotransmitter signs valid", False, str(exc))
        return
    yield (
        "Neuron IDs and neurotransmitter signs valid",
        True,
        "no fabricated IDs and no unrecognized (non-missing) NT types",
    )

    unknown_nt_neurons = _count_missing_nt(neurons["nt_type"])
    unknown_nt_connections = _count_missing_nt(connections["nt_type"])
    if unknown_nt_neurons or unknown_nt_connections:
        yield (
            "Missing (NaN) NT predictions noted",
            True,
            f"{unknown_nt_neurons} neurons, {unknown_nt_connections} connections — "
            "excluded from signed weight, not from structural counts",
        )

    expected = config.EXPECTED_COUNTS.get(dataset_version)
    if expected is None:
        yield (
            "Dataset version known",
            False,
            f"no expected counts declared for {dataset_version!r} in config.EXPECTED_COUNTS",
        )
        return
    yield ("Dataset version known", True, dataset_version)

    neuron_count = len(neuron_ids)
    neuron_pair_count = connections[["pre_root_id", "post_root_id"]].drop_duplicates().shape[0]
    synapse_count = int(connections["syn_count"].sum())
    actual_by_key = {"neurons": neuron_count, "neuron_pairs": neuron_pair_count, "synapses": synapse_count}
    label_by_key = {"neurons": "neurons", "neuron_pairs": "pairwise connections", "synapses": "synapses"}

    for key in ("neurons", "neuron_pairs", "synapses"):
        exp, act = expected[key], actual_by_key[key]
        ok = exp == act
        yield (f"{exp:,} {label_by_key[key]} confirmed", ok, f"got {act:,}")
        if not ok:
            return

    for name in ("LC4", "LPLC2"):
        count = int((cell_types["primary_type"] == name).sum())
        ok = count > 0
        yield (f"{name} population found", ok, f"{count} neurons")
        if not ok:
            return

    dnp01_count = int((cell_types["primary_type"] == config.DESCENDING_OUTPUT_POPULATION).sum())
    ok = dnp01_count > 0
    yield (f"{config.DESCENDING_OUTPUT_POPULATION} / Giant Fibre identified", ok, f"{dnp01_count} neurons")
