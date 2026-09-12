# Data Provenance

## Source dataset

**FlyWire FAFB v783** — the adult female *Drosophila melanogaster* whole-brain
connectome, version 783 (published 2024-06-02, Zenodo record 10676866),
hosted via the Codex portal (https://codex.flywire.ai) by the Princeton
Neuroscience Institute.

Reference documented counts (from the V0 build brief):

| quantity | count |
|---|---|
| neurons | 139,255 |
| neuron-pair connections | 3,732,460 |
| synapses | 50,666,648 |

These are enforced by `brain.connectivity.validation.validate_dataset` — a
build against real FAFB v783 data that does not match these counts fails
loudly rather than proceeding.

## Required citations

Per FlyWire's data usage terms, any use of this dataset (including this
project) must cite:

- Dorkenwald, S. et al. (2024). *Neuronal wiring diagram of an adult brain.*
  (Connectome reconstruction and annotations.)
- Schlegel, P. et al. (2024). *Whole-brain annotation and multi-connectome
  cell typing quantifies circuit stereotypy in Drosophila.* (Cell-type
  annotation.)
- Shiu, P. K. et al. (2024). *A leaky integrate-and-fire computational model
  based on the connectome of the entire adult Drosophila brain reveals
  insights into sensorimotor processing.* Nature.
  DOI: 10.1038/s41586-024-07763-9. (The LIF model this project implements —
  see `docs/BIOLOGICAL_ASSUMPTIONS.md` for the provenance of the specific
  constants used.)

## License

FlyWire data is released under **CC BY-NC-SA 4.0** (Attribution,
NonCommercial, ShareAlike). This project's use of FlyWire data is
non-commercial and research/educational; the raw data files themselves are
never committed to this repository (see `.gitignore`, `data/source/`) —
users must download them directly from an authorized FlyWire account.

## How the data enters this project

The user downloads the FAFB v783 files themselves (a FlyWire account is
required) and points the `FLYWIRE_V783_DIR` environment variable at the
directory containing them. Nothing in this codebase fetches, mirrors, or
redistributes FlyWire data.

Required files (see `config.REQUIRED_SOURCE_FILES`):

- `neurons.csv.gz` — root_id, predicted neurotransmitter type
- `classification.csv.gz` — super_class / class / side / nerve annotations
- `consolidated_cell_types.csv.gz` — root_id -> named cell type (LC4, LPLC2, DNp01, ...)
- `connections_princeton.csv.gz` — pre/post root_id pairs, synapse counts, neuropil, nt_type
- `coordinates.csv.gz` — soma/skeleton position (nanometres)
- `column_assignment.csv.gz` — optic-lobe column assignment
- `labels.csv.gz` — free-text annotations
- `visual_neuron_types.csv.gz` — visual-system cell type labels

Of these, V0 *computes* with `neurons.csv.gz`, `classification.csv.gz`,
`consolidated_cell_types.csv.gz`, and `connections_princeton.csv.gz`
(`config.CONSUMED_SOURCE_FILES`). The remaining four are validated for
presence and schema only — they are reserved for future layers (e.g.
spatial visualization) and are not silently dropped from validation, per
the brief's "if additional required files are discovered, document them"
requirement. If a real FlyWire download is found to need files beyond this
list, add them to `config.REQUIRED_SOURCE_FILES` and note the addition
here with a date and reason.

## File naming and compression variance

Real-world FlyWire exports are not perfectly consistent about filenames or
gzip compression. Confirmed while evaluating a third-party Kaggle mirror of
FAFB v783 (`leonidblokhinrs/flywire-brain-dataset-fafb-v783`, CC BY-NC-SA
4.0 — an unofficial, unaffiliated re-export, not the authenticated FlyWire
account download; its provenance is not independently verified against
Princeton's own checksums):

| canonical name (this project) | observed alternate | difference |
|---|---|---|
| `connections_princeton.csv.gz` | `connections_princeton_no_threshold.csv` | different filename, plain `.csv`, and columns `pre_pt_root_id`/`post_pt_root_id` instead of `pre_root_id`/`post_root_id` |
| any `*.csv.gz` | same name without `.gz` | plain, uncompressed CSV |

`config.SOURCE_FILE_ALIASES` and `config.COLUMN_ALIASES` document every
accepted alternate; `brain.connectivity.loaders.resolve_source_file` tries
the canonical name first, then each alias in order, and
`pandas.read_csv(..., compression="infer")` handles gzip-vs-plain
automatically. If **none** of a file's candidates exist, or a required
column is missing under any of its aliases, validation still fails clearly
— this is alias resolution, not silent substitution. If a real download
uses yet another naming convention not listed here, add it to these dicts
and record the addition in this table with a date and source.

## Synapse-count-per-pair threshold ("FAFB_v783_kaggle_mirror" dataset version)

The Kaggle mirror's `connections_princeton_no_threshold.csv` has, as its
name says, no synapse-count threshold applied: aggregated across neuropils
it has **20,152,374** distinct (pre, post) pairs — nowhere near the
documented 3,732,460. Sweeping a per-pair synapse-count threshold on that
same aggregated data:

| threshold | pairs | synapses |
|---|---|---|
| >=1 (none) | 20,152,374 | 76,929,804 |
| >=3 | 6,606,540 | 59,865,731 |
| >=4 | 4,812,036 | 54,482,219 |
| **>=5** | **3,718,216** | **50,106,939** |
| >=6 | 2,983,507 | 46,433,394 |
| documented FAFB_v783 | 3,732,460 | 50,666,648 | — |

A threshold of **>=5 synapses per pair** lands within 0.38% (pairs) / 1.1%
(synapses) of the documented reference — far closer than any untresholded
file, and consistent with FlyWire's common convention of treating >=5
synapses as a "significant" connection. This was **discovered by sweeping
against the documented target, not invented to force a match**: parameter
5, reference value (implicit in the official counts) unknown/unpublished,
new value 5 (empirically the closest of the values tried), reason: no
official threshold value is stated in the brief or in this mirror's
metadata, effect: connectome pair/synapse counts shift as tabulated above.

The residual ~0.4-1.1% gap is presumed to be a different proofreading
snapshot date than whichever exact snapshot produced the brief's cited
numbers — connectome proofreading is continuously updated. **This is not
claimed to be the official FAFB_v783 dataset.** It is declared as its own
dataset version, `"FAFB_v783_kaggle_mirror"`
(`config.EXPECTED_COUNTS["FAFB_v783_kaggle_mirror"]`,
`config.CONNECTION_MIN_SYNAPSES_PER_PAIR["FAFB_v783_kaggle_mirror"] = 5`),
with its own observed counts as ITS documented truth. Validating against
`"FAFB_v783"` still requires the exact original documented numbers — the
two are never conflated. LC4 (104), LPLC2 (210), and DNp01 (2) population
counts in this mirror DO match the official documented values exactly.

## Missing (NaN) neurotransmitter predictions

Confirmed against the real download: **19,658 of 139,255 neurons (14.1%)**
and **1,478,338 of 22,697,441 raw connection rows (6.5%, 310,738 of
5,334,638 after the >=5 threshold above)** have no neurotransmitter
prediction at all — a real, expected gap in FlyWire's own predictions, not
a data error. Decision (see `docs/BIOLOGICAL_ASSUMPTIONS.md` for the full
record): these are excluded from signed connectome weight (treated as zero
— never guessed) but still counted in the structural neuron/pair/synapse
validation totals, since those are graph-scale metrics independent of
sign. Any OTHER unrecognized non-null neurotransmitter value still fails
validation loudly, exactly as before.

## Descending steering neurons (DNa02, DNa01, DNp09) — confirmed present (Phase 0D)

Checked directly against the real download's `consolidated_cell_types.csv`
and `classification.csv`: `DNa02`, `DNa01`, and `DNp09` (the steering/
forward-locomotion descending neurons used from Phase 0D onward) each have
**exactly 2 neurons**, one per side, cleanly identifiable via
`classification.csv`'s `side` column ("left"/"right") — same pattern as
`DNp01`. `build_connectome.py` uses this to emit side-qualified populations
(e.g. `DNa02_L`, `DNa02_R`) for every cell type that has side data, not just
these four.

## Testability without licensed data (deliberate V0 decision)

Automated tests cannot depend on a licensed, multi-gigabyte, account-gated
download. `config.py` therefore keys expected dataset-scale counts by a
`dataset_version` string (`FLYWIRE_DATASET_VERSION` env var, default
`FAFB_v783`). The test suite generates and validates against a small
synthetic fixture (`tests/fixtures/generate_fixtures.py`, dataset version
`test_fixture_v0`) that mirrors the real schema exactly but is **not**
biological data and makes **no** biological claims. The exact same
validation/build/simulation code path runs for both; only the declared
expected counts differ. Real production runs default to `FAFB_v783` and
will fail loudly if the real counts don't match — this indirection is a
testability mechanism, not a relaxation of the real-data requirement.

## Reference implementation used for orientation

`vaibhavkedarisetti/fruit-fly-lab` on GitHub was consulted as a technical
reference while designing this project (see
`docs/THIRD_PARTY_NOTICES.md` for what was and was not reused from it).
