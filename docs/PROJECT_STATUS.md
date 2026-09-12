# Project Status

## PHASE 0A — ENGINEERING BASELINE ✅ complete

```
Synthetic connectome
       |
   stimulus
       |
  LC4/LPLC2
       |
   network
       |
    DNp01
       |
 lesion test

PASS
```

What this proves: the **architecture** works. Dataset loading and
validation, the sparse connectome build, the whole-network LIF engine, the
looming stimulus interface, the DNp01 interpretation layer, the
lesion/silencing mechanism, the experiment runner, the test suite (49
tests), and the structured JSON output all function correctly and compose
correctly, end to end, deterministically. Verified against a small
synthetic fixture connectome (`tests/fixtures/`, 24 neurons) — **not** real
fly biology.

What this does NOT prove: anything about the real fly brain. The causal
result (`looming -> DNp01`, collapsing when LC4/LPLC2 are silenced) came
from a hand-built toy circuit, not a reconstructed connectome. It is proof
the software works, not proof of a biological finding.

## PHASE 0B — REAL CONNECTOME VALIDATION 🟡 run once, against a real-data mirror — not the fully authoritative dataset yet

**Run against:** a third-party Kaggle mirror of FAFB v783
(`leonidblokhinrs/flywire-brain-dataset-fafb-v783`, CC BY-NC-SA 4.0,
unofficial/unaffiliated — not an authenticated FlyWire account download).
Declared as its own dataset version, `FAFB_v783_kaggle_mirror`, with its
own empirically-observed counts — see `docs/DATA_PROVENANCE.md` for exactly
how those were derived (a >=5-synapse-per-pair threshold, discovered by
sweeping against the documented target, gets within ~0.4-1.1% of it; the
residual gap is presumed to be a different proofreading snapshot date).
**This is real reconstructed-brain data, but its provenance relative to the
canonical Princeton release is not independently verified** — treat these
results as a strong real-data rehearsal, not the final word. Re-running
this exact sequence against an authenticated Codex download once available
is still worth doing.

### Results (first and only run so far)

```
Dataset loads
   |
139,255 neurons confirmed              <- exact match to documented FAFB_v783
   |
3,718,216 pairwise connections         <- this mirror's own count (see DATA_PROVENANCE.md)
   |
50,106,939 synapses                    <- this mirror's own count
   |
LC4 population found (104)             <- exact match to documented FAFB_v783
   |
LPLC2 population found (210)           <- exact match to documented FAFB_v783
   |
DNp01 / Giant Fibre identified (2)
```

- **Step 1 (zero-stimulus baseline):** fully quiescent, no spontaneous
  activity. Ran in 1.5s for the full 139,255-neuron network.
- **Step 2 (looming only, unmodified Phase 0A parameters):** LC4=267
  spikes, LPLC2=334 spikes, **DNp01=25 spikes** (peak 400 Hz), 5,035/139,255
  neurons active (~3.6%). Escape threshold reached. Ran in 1.5s.
- **Step 3 (receding / static, unmodified parameters):** zero spikes in
  every population for both conditions, exactly as in Phase 0A.
- **Step 4 (looming vs. looming + LC4/LPLC2 silenced):** looming DNp01 = 25
  spikes; silenced DNp01 = **0** spikes. **Matches the Phase 0A causal
  pattern.**

A real, uninvented bug was caught and fixed mid-run: the first attempt at
step 3 showed receding/static producing results **identical** to looming —
immediately suspicious (this never happened on the fixture) and correctly
not reported as a finding. Root cause: `locked_parameters.locked_stimulus_kwargs()`
baked `approach_velocity_cm_s=40.0` directly into the shared kwargs dict,
which defeated `looming.receding()`/`looming.static()`'s own `setdefault()`
calls (the key was already present, so their -40/0 defaults never fired) —
silently turning every "condition" into looming. Fixed by excluding
velocity from the shared kwargs (it's the one parameter that must vary by
condition); a regression test (`tests/test_phase_0b_locked_parameters.py`)
now asserts looming/receding/static always produce distinct velocities and
drive signals. This is exactly why step 3 exists as a separate, inspected
step rather than skipping straight to step 4.

**What this does NOT yet prove:** that this exact result holds on the
authoritative, authenticated FlyWire release — only on this specific
third-party mirror snapshot. It also does not validate `GAIN_MV_PER_UNIT`
or the LIF constants against independent literature values (still flagged
in `docs/BIOLOGICAL_ASSUMPTIONS.md`). It DOES prove the full pipeline —
validation, connectome build, whole-brain simulation, lesion mechanism, run
ledger, time series — works correctly end-to-end on a real ~139k-neuron,
~50M-synapse reconstructed connectome, not just a 24-neuron toy.

## PHASE 0C — VELOCITY SWEEP 🟢 run once, against the same real-data mirror

```
                 APPROACH VELOCITY (locked baseline otherwise)

   10 cm/s        20 cm/s        40 cm/s        80 cm/s
      |              |              |              |
      v              v              v              v
  no response    no response    LC4=267        LC4=2671
                                 LPLC2=334      LPLC2=3382
                                 DNp01=25       DNp01=123
                                 escape @120ms  escape @30ms
```

`python -m experiments.phase0c_velocity_sweep` — everything held identical
to the Phase 0A/0B locked baseline except `approach_velocity_cm_s`, per
`experiments/phase_0b/locked_parameters.py` (reused directly, not
duplicated, so Phase 0C can never silently drift from the Phase 0B
baseline). Same run-ledger discipline as Phase 0B.

### Result (first and only run, real ~139k-neuron connectome, ~1.5s/condition)

| velocity | LC4 | LPLC2 | DNp01 | active neurons | 1st sensory spike | escape trigger time |
|---|---|---|---|---|---|---|
| 10 cm/s | 0 | 0 | 0 | 0 | never | never |
| 20 cm/s | 0 | 0 | 0 | 0 | never | never |
| 40 cm/s (reference) | 267 | 334 | 25 | 5,035 | 118.1 ms | 120.1 ms |
| 80 cm/s | 2,671 | 3,382 | 123 | 7,528 | 27.9 ms | 29.9 ms |

Two things worth naming explicitly, neither of which was assumed going in:

1. **A threshold effect, not a smooth gradient.** 10 and 20 cm/s produce
   exactly zero spikes anywhere — not weak, absent. Whatever the true
   biological threshold is, our current stimulus gain (`GAIN_MV_PER_UNIT`,
   still untuned against real scale — see `docs/BIOLOGICAL_ASSUMPTIONS.md`)
   puts it somewhere between 20 and 40 cm/s in this model. This could be a
   genuine network property or an artifact of the untuned gain — Phase 0C
   cannot distinguish those on its own; it only establishes that the
   threshold exists and roughly where it falls.
2. **Faster approach triggers escape both harder and sooner.** 80 cm/s
   produces ~10x the LC4/LPLC2 spikes of 40 cm/s AND crosses the escape
   threshold ~90ms earlier (29.9ms vs 120.1ms). This qualitative pattern —
   response magnitude and latency both scaling with expansion rate — is
   consistent with how real looming-detector circuits are described in the
   literature, but this run does not independently verify that; it is
   flagged as an interesting, not-yet-cross-checked, correspondence.

**What this does NOT yet establish:** exactly where the response threshold
sits in real units, or whether it would move under a properly-calibrated
stimulus gain. That question is exactly what Phase 0D/0E (direction,
object size) and a genuine gain calibration pass should help answer next.

## PHASE 0D — STEERING VALIDATION (AZIMUTH SWEEP) 🟢 run once, against the same real-data mirror

```
          OBJECT

-45deg  -30deg   0deg  +30deg  +45deg    (velocity fixed at 40 cm/s reference)
   \      \       |      /      /
    \      \      |     /      /
              🪰
```

`python -m experiments.phase0d_azimuth_sweep` — a real prerequisite gap
closed first: `azimuth_deg` existed on every stimulus since Phase 0A but
was never used anywhere in the sensory encoding (every looming stimulus
drove LC4/LPLC2 bilaterally regardless of angle). `simulation.session` now
routes stimulation to only that side's LC4_L/LPLC2_L (or _R) neurons based
on azimuth sign — a documented hemifield simplification, not a retinotopic
model (see `docs/BIOLOGICAL_ASSUMPTIONS.md` section 4c). DNa02-L/DNa02-R
(the steering descending neurons — Rayshubskiy et al. 2025, eLife
2025;13:RP102230) were confirmed present in the real dataset (2 neurons,
one per side, same pattern as DNp01) and added as recorded populations.

### Result (first run)

| azimuth | LC4_L | LC4_R | DNa02_L (Hz) | DNa02_R (Hz) | steering (Hz) |
|---|---|---|---|---|---|
| -45° (threat left) | 160 | 0 | 50.0 | 103.3 | -53.3 |
| -30° | 160 | 0 | 50.0 | 103.3 | -53.3 |
| 0° (centered) | 150 | 117 | 43.3 | 0.0 | +43.3 |
| +30° | 0 | 159 | 130.0 | 0.0 | +130.0 |
| +45° (threat right) | 0 | 159 | 130.0 | 0.0 | +130.0 |

**The steering signal DOES reverse sign with azimuth — the circuit is
azimuth-sensitive end to end**, from stimulus routing through the real
139k-neuron connectome to a differential DNa02 readout. Two things worth
naming precisely, neither assumed going in:

1. **The pattern is contralateral (turn away from the threat), not
   ipsilateral (turn toward it)** — a threat on the right produces MORE
   left-DNa02 activity. This is reported as an observation, not validated
   against the literature on LC4/LPLC2→DNa02 connectivity specifically. An
   escape circuit turning away from threat is at least as biologically
   plausible as one orienting toward it; this project does not assert
   which is "correct" — that would be inventing a biological claim.
2. **Azimuth=0 (nominally symmetric) did not produce a near-zero steering
   signal** (+43.3 Hz observed, not ~0). The real FlyWire connectome is one
   individually reconstructed fly, not an idealized bilaterally-symmetric
   model — some baseline asymmetry is plausible — but this is flagged for
   follow-up, not silently treated as noise. Before building a motor
   decoder on top of this signal (Phase 1A), this asymmetry should be
   understood: is it real anatomical asymmetry, an artifact of the coarse
   hemifield routing, or something else?

**What this does prove:** the full pipeline — lateralized sensory routing,
whole-brain propagation, and a differential motor-neuron readout — works
mechanically end to end on the real connectome. **What it does NOT yet
prove:** that either the contralateral pattern or the azimuth=0 offset
reflects real fly biology rather than an artifact of this project's still-
unverified LIF constants, untuned stimulus gain, or the coarse hemifield
simplification. Phase 1A's motor decoder should not be built on this
signal until at least the azimuth=0 asymmetry is understood.

### The controlled sequence (for re-runs, e.g. against an authoritative download)

```
REAL FLYWIRE DATA
        |
     VALIDATE                  <- experiments/phase_0b/step0_validate_dataset.py
        |
RUN UNMODIFIED BASELINE        <- experiments/phase_0b/step1_zero_stimulus_baseline.py
        |
     RUN LOOMING                <- experiments/phase_0b/step2_looming_only.py
        |
    RUN CONTROLS                <- experiments/phase_0b/step3_receding_static.py
        |
   RUN SILENCING                <- experiments/phase_0b/step4_looming_vs_silenced.py
        |
     COMPARE
```

### Step 0 — Validate (no simulation)

```
Dataset loads
   |
139,255 neurons confirmed
   |
3,732,460 pairwise connections confirmed
   |
50,666,648 synapses confirmed
   |
LC4 population found
   |
LPLC2 population found
   |
DNp01 / Giant Fibre identified
```

`python -m experiments.phase_0b.step0_validate_dataset` prints exactly this
checklist and stops at the first failure. Do nothing else until every line
passes on the real dataset.

### Step 1 — Zero-stimulus baseline

No stimulus at all. The question is whether the real network is stable
before anything is added — runaway or pathological spontaneous activity
here would need investigating before step 2 means anything.

### Step 2 — Looming only

The exact same locked parameters carried over unmodified from Phase 0A
(`experiments/phase_0b/locked_parameters.py`) — including the stimulus gain
that was only ever tuned against the tiny synthetic fixture. **If DNp01
does not respond, that is a valid and expected possible outcome**, not a
bug to be silently fixed by retuning. Full time series (LC4/LPLC2/DNp01
spike counts per 5ms bin, not just totals) are recorded.

### Step 3 — Receding / static controls

Same locked parameters, no tuning.

### Step 4 — Looming vs. looming + LC4/LPLC2 silenced

The first real causal experiment. Reports what was observed; does not
force or assume the Phase 0A answer.

## The "no silent tuning" rule

Every Phase 0B script records its exact parameters to an append-only run
ledger (`simulation/run_ledger.py`, `data/metadata/run_ledger.jsonl`) before
running. If a script's parameters differ from the previous recorded run of
that same experiment and no `--change-reason "..."` is given on the command
line, the run is **refused** — not logged, not executed. This makes it
structurally impossible to quietly re-tune something (like stimulus gain)
across repeated runs until the network happens to produce the expected
answer. Every intentional change is permanently recorded as
`RUN 00N — <reason>` in the ledger, alongside the full parameter set and
git commit.

## What "done" looks like for Phase 0B

Not "we built software that behaves like our test." It is: **we stimulated
identified neurons (LC4/LPLC2) in the real reconstructed FlyWire connectome
and observed the resulting network response at DNp01**, with the full
observation trail (validation checklist, zero-stimulus baseline, unmodified
looming/receding/static results, silencing comparison, time series, and run
ledger) preserved and inspectable.

## Roadmap

```
DONE     Phase 0B   Basic causal validation (baseline / looming / receding /
                     static / circuit silencing)
DONE     Phase 0C   Velocity sweep (10 / 20 / 40 / 80 cm/s)
DONE     Phase 0D   Steering validation / azimuth sweep (-45/-30/0/+30/+45 deg,
                     velocity fixed at 40 cm/s). DNa02-L/DNa02-R identified
                     and added as recorded populations; azimuth-based
                     hemifield stimulus routing implemented (previously
                     azimuth_deg was stored but never used anywhere).
                     Result: the steering signal DOES reverse sign with
                     azimuth (contralateral/turn-away pattern observed, not
                     yet validated against literature), but azimuth=0 is
                     NOT near-zero — that asymmetry should be understood
                     before Phase 1A builds a motor decoder on this signal.
THEN     Phase 0E   Object-size sweep (0.25 / 0.5 / 1.0 / 2.0 cm radius) —
                     combined with 0C/0D this starts building an actual
                     speed x size x direction response surface, not one
                     scripted scenario.
THEN     Phase 1A   Motor decoder: map the DNa02-L/DNa02-R difference to
                     angular velocity (turn_signal = left_rate - right_rate,
                     angular_velocity = K_TURN * turn_signal — a documented,
                     explicit translation layer, not a claim about the real
                     VNC/muscle pathway), and give the simulated fly a body
                     state (x, y, heading) that actually rotates from it.
THEN     Phase 1B   Close the loop: WORLD -> SENSE -> BRAIN -> ACT ->
                     WORLD CHANGES, looped every 5ms — recompute the
                     object's angle relative to the fly's new heading and
                     re-stimulate, instead of a single predetermined
                     stimulus -> brain -> result pass.
THEN     Phase 1C   Realistic fly viewer showing the closed loop live (this
                     is where the Connectome Viewer / live API grows into
                     the real Demo 1).
THEN     Phase 2    Obstacle / maze environment.
THEN     Phase 3    Learning / dopamine / plasticity.
```

Per the caveat recorded for Phase 1A: the FAFB connectome models the brain,
not the ventral nerve cord, muscles, legs, or biomechanics. Translating a
DNa02 differential directly into body angular velocity is this project's
own motor decoder — a documented stand-in for "this descending command
would, in the real fly, influence leg motor circuits via the VNC" — not a
claim of deeper biomechanical fidelity. That is explicitly out of scope
for Demo 1.

Every experiment parameter, `run_id`, git commit, seed, dataset version,
and simulator parameters live in the saved JSON for every phase from 0B
onward, specifically so a result can be reproduced exactly later — this is
a standing requirement for every new experiment script added from here on,
not just a Phase 0B/0C convention.
