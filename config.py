"""Central configuration: paths, dataset expectations, and documented model constants.

Nothing in this file is a "magic number" buried in application code — every
constant here is either read from the environment or has a citation in
docs/BIOLOGICAL_ASSUMPTIONS.md or docs/DATA_PROVENANCE.md.
"""

from __future__ import annotations

import os
from pathlib import Path


class DatasetConfigError(RuntimeError):
    """Raised when the FlyWire dataset location or version is not configured."""


class DatasetValidationError(RuntimeError):
    """Raised when the dataset on disk does not match the declared/expected schema or counts."""


# ---------------------------------------------------------------------------
# Dataset location
# ---------------------------------------------------------------------------

FLYWIRE_V783_DIR_ENV = "FLYWIRE_V783_DIR"

# Which named dataset version's expected counts to validate against. Real
# production runs use the default "FAFB_v783". Automated tests point this at
# "test_fixture_v0" so the exact-same validation code path runs against the
# small synthetic fixtures in tests/fixtures/ without needing licensed data.
# This indirection is documented in docs/DATA_PROVENANCE.md as a deliberate
# V0 testability decision, not a relaxation of the real-data requirement.
FLYWIRE_DATASET_VERSION_ENV = "FLYWIRE_DATASET_VERSION"
DEFAULT_DATASET_VERSION = "FAFB_v783"


def get_flywire_dir() -> Path:
    """Return the configured FlyWire source directory, or raise DatasetConfigError."""
    raw = os.environ.get(FLYWIRE_V783_DIR_ENV)
    if not raw:
        raise DatasetConfigError(
            f"{FLYWIRE_V783_DIR_ENV} is not set. Point it at the directory containing "
            "the downloaded FlyWire FAFB v783 files (see README.md for how to obtain them)."
        )
    path = Path(raw).expanduser()
    if not path.is_dir():
        raise DatasetConfigError(f"{FLYWIRE_V783_DIR_ENV}={raw!r} is not a directory.")
    return path


def get_dataset_version() -> str:
    return os.environ.get(FLYWIRE_DATASET_VERSION_ENV, DEFAULT_DATASET_VERSION)


# ---------------------------------------------------------------------------
# Required source files
# ---------------------------------------------------------------------------

# Per the V0 brief. If a real FlyWire download turns out to need additional
# files, add them here and note the addition in docs/DATA_PROVENANCE.md.
REQUIRED_SOURCE_FILES = (
    "neurons.csv.gz",
    "classification.csv.gz",
    "consolidated_cell_types.csv.gz",
    "connections_princeton.csv.gz",
    "coordinates.csv.gz",
    "column_assignment.csv.gz",
    "labels.csv.gz",
    "visual_neuron_types.csv.gz",
)

# Files actually consumed by the V0 connectome build and simulation.
# The remainder are validated for presence/schema only (kept for future
# layers, e.g. spatial visualization) and are documented as such.
CONSUMED_SOURCE_FILES = (
    "neurons.csv.gz",
    "classification.csv.gz",       # side ("left"/"right") drives side-qualified populations, e.g. "DNa02_L"
    "consolidated_cell_types.csv.gz",
    "connections_princeton.csv.gz",
)

# ---------------------------------------------------------------------------
# Real-world filename/column variance
# ---------------------------------------------------------------------------
# Not every real FlyWire export uses the exact filenames/columns above.
# Confirmed while evaluating a third-party FAFB v783 mirror (see
# docs/DATA_PROVENANCE.md, "File naming and compression variance"): files may
# be plain .csv rather than .csv.gz, and the connections file may be named
# "connections_princeton_no_threshold.csv" with "pre_pt_root_id"/
# "post_pt_root_id" instead of "pre_root_id"/"post_root_id". These aliases
# are tried, in order, after the canonical name whenever a required file or
# column isn't found under its canonical name — never a silent guess: if
# NONE of a file's candidates exist, validation still fails clearly.
SOURCE_FILE_ALIASES: dict[str, tuple[str, ...]] = {
    "connections_princeton.csv.gz": (
        "connections_princeton.csv",
        "connections_princeton_no_threshold.csv.gz",
        "connections_princeton_no_threshold.csv",
    ),
    "neurons.csv.gz": ("neurons.csv",),
    "classification.csv.gz": ("classification.csv",),
    "consolidated_cell_types.csv.gz": ("consolidated_cell_types.csv",),
    "coordinates.csv.gz": ("coordinates.csv",),
    "column_assignment.csv.gz": ("column_assignment.csv",),
    "labels.csv.gz": ("labels.csv",),
    "visual_neuron_types.csv.gz": ("visual_neuron_types.csv",),
}

# Column renames applied (only for columns actually present) after loading a
# file, keyed by the file's canonical name. Lets the rest of the codebase
# keep using one column-naming convention regardless of which real-world
# export produced the file.
COLUMN_ALIASES: dict[str, dict[str, str]] = {
    "connections_princeton.csv.gz": {
        "pre_pt_root_id": "pre_root_id",
        "post_pt_root_id": "post_root_id",
    },
}

# ---------------------------------------------------------------------------
# Expected dataset-scale counts, keyed by dataset version.
# ---------------------------------------------------------------------------

# FAFB_v783 values are the documented reference counts from the V0 brief
# (FlyWire FAFB v783 adult female Drosophila connectome). Do not change these
# without recording why in docs/DATA_PROVENANCE.md.
EXPECTED_COUNTS = {
    "FAFB_v783": {
        "neurons": 139_255,
        "neuron_pairs": 3_732_460,
        "synapses": 50_666_648,
    },
    # Small synthetic fixture used by the automated test suite
    # (tests/fixtures/generate_fixtures.py). NOT real biological data.
    "test_fixture_v0": {
        "neurons": 26,
        "neuron_pairs": 46,
        "synapses": 2_000,
    },
    # A specific real-data snapshot: the third-party Kaggle mirror
    # "leonidblokhinrs/flywire-brain-dataset-fafb-v783" (CC BY-NC-SA 4.0,
    # unofficial/unaffiliated — see docs/DATA_PROVENANCE.md), with a >=5
    # synapse-per-pair threshold applied (config.CONNECTION_MIN_SYNAPSES_PER_PAIR)
    # to its "connections_princeton_no_threshold.csv". This reproduces the
    # documented FAFB_v783 counts to within ~0.4-1.1%, not exactly — the
    # residual gap is presumed to be a different proofreading snapshot date.
    # These are THIS mirror's own observed, empirically-measured counts, not
    # a claim that they equal the official FAFB_v783 numbers. Never conflate
    # the two: validating against "FAFB_v783" must still require the exact
    # documented numbers above.
    "FAFB_v783_kaggle_mirror": {
        "neurons": 139_255,
        "neuron_pairs": 3_718_216,
        "synapses": 50_106_939,
    },
}

# Synapse-count-per-pair threshold applied (after aggregating multi-neuropil
# rows for the same (pre,post) pair) before counting/building the connectome,
# keyed by dataset version. Default (any version not listed) is 1, i.e. no
# filtering — every real synapse count is >= 1 anyway, so this only has an
# effect for versions that explicitly declare a higher threshold.
#
# The value 5 for "FAFB_v783_kaggle_mirror" was DISCOVERED empirically, not
# invented: sweeping thresholds against that mirror's "no_threshold"
# connections file showed >=5 lands closest (within ~0.4-1.1%) to the
# documented FAFB_v783 reference counts, consistent with FlyWire's common
# convention of treating >=5 synapses as a "significant" connection. See
# docs/DATA_PROVENANCE.md for the full threshold sweep table.
CONNECTION_MIN_SYNAPSES_PER_PAIR: dict[str, int] = {
    "FAFB_v783_kaggle_mirror": 5,
}

# Documented reference cell-population sizes, keyed by dataset version.
EXPECTED_POPULATION_COUNTS = {
    "FAFB_v783": {
        "LC4": 104,
        "LPLC2": 210,
    },
    "test_fixture_v0": {
        "LC4": 4,
        "LPLC2": 4,
    },
    # Confirmed by directly inspecting the Kaggle mirror's
    # consolidated_cell_types.csv — matches the official documented counts
    # exactly, unlike the connection counts above.
    "FAFB_v783_kaggle_mirror": {
        "LC4": 104,
        "LPLC2": 210,
    },
}

DESCENDING_OUTPUT_POPULATION = "DNp01"


# ---------------------------------------------------------------------------
# LIF neuron model constants
# ---------------------------------------------------------------------------
# Attributed to Shiu et al. 2024, "A leaky integrate-and-fire computational
# model based on the connectome of the entire adult Drosophila brain reveals
# insights into sensorimotor processing", Nature (2024),
# DOI: 10.1038/s41586-024-07763-9.
#
# PROVENANCE NOTE (read docs/BIOLOGICAL_ASSUMPTIONS.md for the full table):
# These numeric values were obtained from a third-party open-source
# reimplementation's citation of the paper, not by reading the primary
# paper's Methods/supplement directly (the publisher page returned HTTP 403
# for automated fetching during this build). They are shipped here as the
# documented default and should be cross-checked against the primary source
# before being treated as scientifically final.
LIF_PARAMS = {
    "v_reset_mV": -52.0,       # resting / reset membrane potential
    "v_threshold_mV": -45.0,   # spike threshold
    "tau_membrane_ms": 20.0,   # membrane time constant
    "tau_synapse_ms": 5.0,     # synaptic conductance decay time constant
    "t_refractory_ms": 2.2,    # refractory period
    "t_synaptic_delay_ms": 1.8,  # synaptic transmission delay
    "w_synapse_mV": 0.275,     # per-synapse conductance weight
}

# Neurotransmitter sign convention (Shiu et al. 2024, via the same
# provenance note above). Any nt_type not listed is treated as unknown and
# will raise during connectome build rather than silently defaulting to a
# sign, per the "do not silently substitute" requirement.
EXCITATORY_NEUROTRANSMITTERS = frozenset({"ACH", "DA", "OCT", "SER"})
INHIBITORY_NEUROTRANSMITTERS = frozenset({"GABA", "GLUT"})

DEFAULT_TIMESTEP_MS = 0.1
DEFAULT_SIMULATION_DURATION_MS = 300.0
DEFAULT_TIME_SERIES_BIN_MS = 5.0


# ---------------------------------------------------------------------------
# Derived / metadata output locations
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
DERIVED_DIR = PROJECT_ROOT / "data" / "derived"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
OUTPUTS_DIR = PROJECT_ROOT / "simulation" / "outputs"

CONNECTOME_NPZ = DERIVED_DIR / "connectome.npz"
CONNECTOME_INDEX = DERIVED_DIR / "connectome_index.json"
BUILD_MANIFEST = METADATA_DIR / "build_manifest.json"

# Append-only record of every simulation run's parameters, per experiment
# name (simulation.run_ledger). Used to detect and refuse silent parameter
# drift (e.g. re-tuning stimulus gain) between runs without an explicit,
# logged reason — see docs/BIOLOGICAL_ASSUMPTIONS.md and
# docs/PROJECT_STATUS.md ("no silent tuning" policy).
RUN_LEDGER_PATH = METADATA_DIR / "run_ledger.jsonl"
