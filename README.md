# Fly Brain Lab — V0

## Status

**Phase 0A (engineering baseline): ✅ complete.** **Phase 0B (real
connectome validation): 🟡 run once, against a real-data mirror** (a
third-party Kaggle re-export of FAFB v783, not yet the authenticated
FlyWire account download) — looming produced DNp01 spikes on the real
~139,255-neuron connectome, and silencing LC4+LPLC2 collapsed that response
to zero, matching the Phase 0A pattern. See `docs/PROJECT_STATUS.md` for
the full results, the dataset provenance caveat, and a real bug that was
caught and fixed mid-run. This is a strong real-data rehearsal, not yet
confirmed against the authoritative Princeton release.

**Phase 0C (velocity sweep): ✅ run once**, same real-data mirror — varying
only approach speed (10/20/40/80 cm/s) revealed a threshold effect (10/20
cm/s produce zero response) and, above it, both stronger and faster escape
responses at higher speed (80 cm/s escapes ~90ms sooner than 40 cm/s). See
`docs/PROJECT_STATUS.md` for the full table and what it does/doesn't establish.

**Phase 0D (steering validation / azimuth sweep): ✅ run once** — closed a
real prerequisite gap first (`azimuth_deg` was stored on every stimulus
since Phase 0A but never used in the sensory encoding), identified DNa02-L/
DNa02-R (steering descending neurons) in the real data, and added
azimuth-based left/right stimulus routing. Result: the DNa02 differential
steering signal DOES reverse sign with azimuth (the circuit is
azimuth-sensitive end to end), in a contralateral/turn-away-from-threat
pattern — reported as an observation, not validated against the
literature. A real, unresolved caveat: the nominally-symmetric azimuth=0
condition is not near-zero, which should be understood before any motor
decoder is built on this signal. See `docs/PROJECT_STATUS.md`.

**Live interactive UI**: a local FastAPI backend (`api/main.py`) + browser
frontend (`api/static/index.html`) that runs the real simulation on demand
(not pre-baked) — pick a condition/velocity, hit run, watch the actual
LIF simulation compute and animate on the real connectome, including a
"what the fly sees" panel showing the true expanding-disc stimulus. Start
with `uvicorn api.main:app --port 8010` (or via the Browser pane's
dev-server preview, see `.claude/launch.json` at the repo root).

## Viewer V2 — embodied closed loop

Open `http://localhost:8010/fly` after starting the API. Viewer V2 keeps
membrane voltage, synaptic state, and the transmission-delay buffer alive
between 25 ms simulation windows. After every window it:

1. recomputes the threat's distance and bearing relative to the fly,
2. generates the new visual expansion drive,
3. advances the real whole-connectome LIF state,
4. reads DNa02-L/R and DNp01,
5. updates body position, height, and heading, and
6. feeds the changed world geometry into the next neural window.

The viewer is split into reusable modules under `api/static/viewer-v2/`.
It renders the real connectome coordinates inside the fly's head, animates
an articulated full-body avatar, streams telemetry over WebSocket, and
provides orbit, chase, overhead, and fly-eye cameras. The original
single-run playback remains available at `/fly-v1`.

The body decoder is still an explicit engineering stand-in for the missing
ventral nerve cord, muscles, and biomechanics; see
`docs/BIOLOGICAL_ASSUMPTIONS.md` section 4d.

## What this is

An engineering baseline that runs a real FlyWire FAFB v783 connectome
through a whole-brain leaky integrate-and-fire (LIF) simulation to
demonstrate one causal chain:

```
looming visual stimulus
        |
LC4 / LPLC2 sensory neurons
        |
whole-brain connectome propagation
        |
DNp01 / Giant Fibre activity
        |
escape output (behavioural interpretation)
```

...and then repeats the same experiment with LC4+LPLC2's outbound synaptic
effect silenced, to show the DNp01 response collapses. This is the
scientific and engineering substrate for later work — it is **not** that
later work.

## What this does NOT claim

- This is **connectome + mathematical neuron model + engineered sensory
  interface** — not a complete biological reproduction of a living fly.
- No claim of consciousness, subjective experience, or full biological
  fidelity is made anywhere in this codebase or its outputs.
- No learning, synaptic plasticity, dopamine/reward circuitry,
  hunger/arousal state, multiple flies, GPU execution, biomechanical body
  physics, game/robot control, or AI/LLM-based interpretation is
  implemented. See `docs/BIOLOGICAL_ASSUMPTIONS.md` for the full list and
  for every place a specific numeric constant is a documented, sourced
  value rather than an invented one.
- The sensory-encoding gain and the escape-detection threshold are
  engineering interface choices, not measured biological constants (see
  `docs/BIOLOGICAL_ASSUMPTIONS.md` section 4).

## Hardware requirements

- CPU: modern x86-64 or Apple Silicon
- RAM: 4 GB minimum, 8 GB+ preferred
- GPU: not required (none is used)
- Disk: reserve at least 5 GB (FlyWire FAFB v783 download + derived artifacts)
- Python: 3.11+

## Python setup

```bash
cd fly-brain-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/requirements.txt -r requirements/requirements-dev.txt
```

Brian2 is an **optional** reference/cross-check dependency (see
`requirements/requirements-dev.txt`) — not required for the tests,
connectome build, or experiments below.

## Acquiring the FlyWire data

1. Create/sign in to a FlyWire account and go to https://codex.flywire.ai
2. Download the FAFB v783 release files listed below.
3. Place them all in one directory (any location you like).
4. Point the environment variable at that directory:

```bash
export FLYWIRE_V783_DIR=/path/to/your/flywire_fafb_v783
```

Required files (see `docs/DATA_PROVENANCE.md` for what each contains and
which ones V0 actually computes with):

```
neurons.csv.gz
classification.csv.gz
consolidated_cell_types.csv.gz
connections_princeton.csv.gz
coordinates.csv.gz
column_assignment.csv.gz
labels.csv.gz
visual_neuron_types.csv.gz
```

FlyWire data is licensed CC BY-NC-SA 4.0 (non-commercial, attribution
required) — see `docs/DATA_PROVENANCE.md` for the required citations. This
repository never downloads, mirrors, or commits FlyWire data itself.

**Alternate source / naming variance:** third-party mirrors (e.g. on
Kaggle) may package the same data under different filenames or without
gzip compression — for example `connections_princeton_no_threshold.csv`
with `pre_pt_root_id`/`post_pt_root_id` columns instead of
`connections_princeton.csv.gz` with `pre_root_id`/`post_root_id`. The
loader accepts these documented alternates automatically (see
`config.SOURCE_FILE_ALIASES`, `config.COLUMN_ALIASES`, and
`docs/DATA_PROVENANCE.md` "File naming and compression variance") — you do
not need to rename anything yourself. If you use a mirror rather than an
authenticated FlyWire account download, note that its provenance/integrity
relative to the official Princeton release is not independently verified
by this project; the count/schema validation below is your main check.

## Validating the data

Validation runs automatically as part of the connectome build (next
section) and will **fail loudly** — never silently substitute fake data —
if `FLYWIRE_V783_DIR` is unset, a required file is missing, or the
neuron/connection/synapse counts don't match the declared dataset version.
To validate without building:

```python
from pathlib import Path
from brain.connectivity.validation import validate_dataset
report = validate_dataset(Path("/path/to/your/flywire_fafb_v783"))
print(report)
```

## Building the connectome

```bash
python -m brain.connectivity.build_connectome
```

Writes:

- `data/derived/connectome.npz` — sparse (CSR) signed-synapse-count matrix; a
  dense `139255 x 139255` matrix is never allocated.
- `data/derived/connectome_index.json` — root_id <-> matrix-index mapping and
  named cell-type populations (LC4, LPLC2, DNp01, ...).
- `data/metadata/build_manifest.json` — dataset version, source file SHA256
  checksums, counts, build timestamp, git commit, Python version, platform.

## Running the tests

```bash
python -m pytest tests/ -q
```

Tests run entirely against small synthetic fixtures
(`tests/fixtures/generate_fixtures.py`, **not** real biological data — see
`tests/fixtures/README.md`) so they need no FlyWire download. They cover
dataset provenance/validation, connectome build (counts, sparsity, signed
weights, population identification), the LIF model (state-update math, an
independent scalar cross-check, quiescence, determinism), the looming
stimulus and sensory encoders, the DNp01 interpretation layer, the
LC4/LPLC2 lesion causal test, and rejection of fabricated/invalid neuron
IDs and mismatched dataset versions.

## Running the Phase 0A escape experiments (synthetic fixture, done)

```bash
python -m experiments.01_looming_escape
python -m experiments.02_escape_controls
```

Both require a connectome already built (previous section) and print a
human-readable summary plus write a structured JSON file to
`simulation/outputs/` (see "Expected experiment structure" below).

### Against the synthetic fixture (no FlyWire account needed)

```bash
export FLYWIRE_V783_DIR=tests/fixtures
export FLYWIRE_DATASET_VERSION=test_fixture_v0
python -m brain.connectivity.build_connectome
python -m experiments.01_looming_escape
python -m experiments.02_escape_controls
```

These two scripts (`01_looming_escape.py`, `02_escape_controls.py`) are the
Phase 0A demonstration and are intentionally allowed to run against
whichever dataset is configured — including the real one, if you want to
sanity-check the pipeline end to end. **They are not the controlled Phase
0B validation** described next; running them against real data is not a
substitute for step0-step4 below.

## Running Phase 0B: real connectome validation (not yet run — needs real data)

See `docs/PROJECT_STATUS.md` for the full rationale. This is a controlled,
ordered sequence — run each step in order and do not tune any parameter
between them without an explicit `--change-reason`:

```bash
export FLYWIRE_V783_DIR=/path/to/your/flywire_fafb_v783
unset FLYWIRE_DATASET_VERSION   # defaults to FAFB_v783

python -m experiments.phase_0b.step0_validate_dataset       # validation only, no simulation
python -m brain.connectivity.build_connectome                # only after step0 passes
python -m experiments.phase_0b.step1_zero_stimulus_baseline  # is the network stable?
python -m experiments.phase_0b.step2_looming_only             # looming only, no tuning
python -m experiments.phase_0b.step3_receding_static          # controls, no tuning
python -m experiments.phase_0b.step4_looming_vs_silenced       # the first real causal test
```

All parameters for these five scripts are locked in
`experiments/phase_0b/locked_parameters.py` and carried over unmodified
from Phase 0A. Every run is recorded to `data/metadata/run_ledger.jsonl`
(`simulation/run_ledger.py`) — if a script's parameters differ from the
previous recorded run of that experiment, it **refuses to run** unless you
pass `--change-reason "..."` explaining what changed and why. This makes
silent re-tuning (e.g. adjusting stimulus gain until DNp01 "responds
correctly") structurally impossible; every deliberate change is permanently
logged as its own numbered run.

Each script also records a full **time series** (not just totals) — LC4,
LPLC2, and DNp01 spike counts per 5 ms bin across the whole run — in both
its console table and its JSON output, since this is the data later demo
work will need for a live visualization.

If DNp01 does not respond in step2, or the silencing comparison in step4
doesn't match the Phase 0A pattern, that is a valid and useful result to
report, not a failure to fix by adjusting parameters on the spot.

## Running Phase 0C: velocity sweep (stimulus-response)

```bash
python -m experiments.phase0c_velocity_sweep
```

Runs the locked baseline stimulus at 10/20/40/80 cm/s approach velocity
(everything else identical, reusing `experiments/phase_0b/locked_parameters.py`
directly rather than a separate copy) and records, per condition: LC4/LPLC2/
DNp01 spike counts, DNp01 peak firing rate, active-neuron count, first
sensory spike time, first DNp01 spike time, escape-triggered flag and
trigger time, wall-clock runtime, and the full time series — same run-ledger
discipline as Phase 0B. See `docs/PROJECT_STATUS.md` for the real result
and what it does/doesn't establish.

## Running Phase 0D: steering validation (azimuth sweep)

```bash
python -m experiments.phase0d_azimuth_sweep
```

Sweeps stimulus azimuth (-45/-30/0/+30/+45 degrees, velocity fixed at the
40 cm/s reference) and records LC4_L/R and LPLC2_L/R spike counts,
DNa02_L/DNa02_R spike counts and firing rates, and the steering signal
(`left_rate - right_rate`) — requires a connectome build recent enough to
include side-qualified populations (`DNa02_L`, `DNa02_R`, etc.; rebuild via
`python -m brain.connectivity.build_connectome` if missing). Same
run-ledger discipline as Phase 0B/0C. See `docs/PROJECT_STATUS.md` for the
real result and its caveats.

## Expected experiment structure

`experiments/02_escape_controls.py` runs six conditions with identical
simulation settings (seed, timestep, duration, LIF/encoder parameters):
`looming`, `receding`, `static`, `looming_LC4_silenced`,
`looming_LPLC2_silenced`, `looming_LC4_LPLC2_silenced`. For each it records
LC4/LPLC2/DNp01 spike counts, DNp01 peak firing rate, active-neuron count,
simulation duration, wall-clock runtime, seed, parameters, and (as of the
Phase 0B work) a per-5ms-bin **time series** of LC4/LPLC2/DNp01 spike
counts and active-neuron count — not just totals — then writes:

```json
{
  "experiment": "escape_controls",
  "dataset": "FAFB_v783",
  "seed": 12345,
  "conditions": [
    {
      "condition": "looming",
      "...": "...",
      "time_series": [
        { "t_ms": 0.0, "LC4": 0, "LPLC2": 0, "DNp01": 0, "active_neurons": 0 },
        { "t_ms": 5.0, "LC4": 4, "LPLC2": 4, "DNp01": 0, "active_neurons": 4 }
      ]
    }
  ],
  "parameters": { "...": "..." },
  "runtime": { "total_wall_clock_s": 0.0 },
  "git_commit": "..."
}
```

The Phase 0B scripts (`experiments/phase_0b/`) write the same
`time_series`-bearing condition structure, plus a `run_id` from the run
ledger.

The crucial causal check the script reports (and exits non-zero if it does
not hold, rather than pretending it did):

- `looming` produces DNp01 spikes and `escape_triggered: true`.
- `looming_LC4_LPLC2_silenced` produces **zero** DNp01 spikes and
  `escape_triggered: false`, even though LC4/LPLC2 themselves still spike in
  response to the stimulus (their outbound effect, not their sensory
  stimulation, is what's silenced).

## Known limitations

- **LIF constants provenance**: the seven Shiu et al. 2024 constants used
  here were sourced via a third-party summary of the paper (the primary
  paper could not be fetched directly during this build) — see
  `docs/BIOLOGICAL_ASSUMPTIONS.md` section 1 for the exact caveat and what
  to verify.
- **Sensory-encoder gain is untuned for real scale**: `GAIN_MV_PER_UNIT=16.0`
  in `experiments/phase_0b/locked_parameters.py` (and the same default in
  `simulation/session.py`) was tuned only against the tiny synthetic test
  fixture. It has no claim to being correct at real FAFB_v783 scale. Phase
  0B step 2 deliberately runs it unmodified to find out what it actually
  does — any change to it must go through the run ledger with an explicit
  `--change-reason` (see `docs/PROJECT_STATUS.md`), never a quiet edit.
- **DNp01 population size is not hard-validated**: unlike LC4 (104) and
  LPLC2 (210), the brief does not give a citable exact DNp01 count, so no
  hard count check is enforced for it (see `docs/BIOLOGICAL_ASSUMPTIONS.md`
  section 3).
- **No visualization, game/robot integration, or learning** — explicitly
  out of scope for V0 (brief section 2).

## Data & model citations

- Dorkenwald, S. et al. (2024). *Neuronal wiring diagram of an adult brain.*
- Schlegel, P. et al. (2024). *Whole-brain annotation and multi-connectome
  cell typing quantifies circuit stereotypy in Drosophila.*
- Shiu, P. K. et al. (2024). *A leaky integrate-and-fire computational model
  based on the connectome of the entire adult Drosophila brain reveals
  insights into sensorimotor processing.* Nature.
  DOI: 10.1038/s41586-024-07763-9.

See `docs/DATA_PROVENANCE.md` and `docs/THIRD_PARTY_NOTICES.md` for full
attribution and license details.

## Repository layout

```
fly-brain-lab/
├── config.py                    # env/config, expected counts, LIF constants (documented)
├── brain/
│   ├── connectivity/            # load, validate, build sparse connectome (biological data layer)
│   ├── neurons/registry.py      # root_id <-> matrix index, named populations
│   ├── neuron_models/lif.py     # LIF state-update math (neuron model layer)
│   ├── sensory/                 # looming stimulus + generic drive-signal encoder (interface layer)
│   └── motor/descending.py      # DNp01 spikes -> escape observation (interpretation layer)
├── simulation/
│   ├── engine/lif_engine.py     # whole-connectome timestep loop, per-bin time series
│   ├── session.py                # composes all four layers for one run
│   ├── reporting.py              # structured JSON experiment output
│   ├── run_ledger.py             # append-only run history; refuses silent parameter drift
│   └── outputs/                  # written experiment results land here
├── experiments/
│   ├── 01_looming_escape.py       # Phase 0A demo (synthetic fixture)
│   ├── 02_escape_controls.py      # Phase 0A demo (synthetic fixture)
│   ├── phase0c_velocity_sweep.py  # Phase 0C: stimulus-response velocity sweep
│   ├── phase0d_azimuth_sweep.py   # Phase 0D: steering validation / azimuth sweep
│   └── phase_0b/                  # Phase 0B: controlled real-data validation sequence
│       ├── locked_parameters.py   # the one shared, ledger-tracked parameter set
│       ├── step0_validate_dataset.py
│       ├── step1_zero_stimulus_baseline.py
│       ├── step2_looming_only.py
│       ├── step3_receding_static.py
│       └── step4_looming_vs_silenced.py
├── api/                           # live local backend + browser UI (real simulation on demand)
│   ├── main.py                    # FastAPI: /api/simulate, /api/positions, /api/health
│   └── static/index.html          # three.js viewer wired to the live API, not baked JSON
├── data/{source,derived,metadata}/   # metadata/run_ledger.jsonl, ui_session_log.jsonl live here
├── tests/                         # runs against synthetic fixtures, no FlyWire account needed
├── requirements/
└── docs/
    ├── PROJECT_STATUS.md          # Phase 0A-0D results, the controlled sequence, no-tuning policy
    ├── DATA_PROVENANCE.md
    ├── BIOLOGICAL_ASSUMPTIONS.md
    └── THIRD_PARTY_NOTICES.md
```
