# Biological Assumptions

This document tracks every place this project's numbers or behavior are NOT
a 1:1, independently-verified read of the primary literature, per the V0
brief's requirement to document `parameter / reference value / new value /
reason for change / effect on output` for any such case, and to expose
(rather than silently invent) any ambiguous biological or product decision.

## 1. LIF model constants — provenance caveat

**This is the single most important entry in this document.**

`config.LIF_PARAMS` implements the leaky integrate-and-fire model from:

> Shiu, P. K. et al. (2024). *A leaky integrate-and-fire computational model
> based on the connectome of the entire adult Drosophila brain reveals
> insights into sensorimotor processing.* Nature.
> DOI: 10.1038/s41586-024-07763-9.

| parameter | value used | reference |
|---|---|---|
| v_reset (mV) | -52.0 | Shiu et al. 2024 |
| v_threshold (mV) | -45.0 | Shiu et al. 2024 |
| tau_membrane (ms) | 20.0 | Shiu et al. 2024 |
| tau_synapse (ms) | 5.0 | Shiu et al. 2024 |
| t_refractory (ms) | 2.2 | Shiu et al. 2024 |
| t_synaptic_delay (ms) | 1.8 | Shiu et al. 2024 |
| w_synapse (mV/synapse) | 0.275 | Shiu et al. 2024 |

**Reason these are flagged rather than treated as settled:** during this
build, the primary paper (Nature, and the bioRxiv preprint
10.1101/2023.05.02.539144) could not be fetched directly — the publisher
page returned HTTP 403 to automated retrieval. These numeric values were
instead obtained from a third-party open-source reimplementation's own
citation of the paper (`vaibhavkedarisetti/fruit-fly-lab`, itself unlicensed
— see `THIRD_PARTY_NOTICES.md` — used here only to locate the correct
published numbers, not for any code). **Action requested:** cross-check
these seven values against the primary paper's Methods/supplementary
material before treating them as scientifically final. If any value differs,
update the table above and this row, and re-run
`python -m experiments.02_escape_controls` to confirm the causal result
still holds — `effect on output` if a value is wrong would most likely be a
shift in how much sensory drive is needed to cross threshold (encoder gain,
entry 4 below, would need retuning to compensate).

**Effect on output if wrong:** these constants set the absolute voltage
scale and time constants of every neuron in the simulation. An error here
would not change the qualitative escape/no-escape logic (which depends on
network topology and NT sign, not absolute constants) but would change how
much stimulus drive or connection strength is needed to reach threshold.

## 2. Neurotransmitter sign convention

| nt_type | sign | reference |
|---|---|---|
| ACh, dopamine, octopamine, serotonin | excitatory (+1) | Shiu et al. 2024 (same provenance caveat as above) |
| GABA, glutamate | inhibitory (-1) | Shiu et al. 2024; glutamate is inhibitory in *Drosophila* via the GluClα receptor, not excitatory as in vertebrates |

Any `nt_type` value not in this list raises `DatasetValidationError` rather
than being silently assigned a sign (`brain/connectivity/validation.py`).

## 3. DNp01 (Giant Fibre) left/right neurotransmitter inconsistency — NOT modeled

Community documentation of the FlyWire annotations notes that DNp01's two
copies (left/right) have inconsistent predicted neurotransmitter (one
predicted ACh, the other predicted GABA/glutamate). V0 does not special-case
this: DNp01's *inbound* sign as a postsynaptic target is irrelevant to this
inconsistency (it only affects DNp01's own outbound connections, which V0
does not simulate further downstream — see `brain/motor/descending.py`,
section 15 layer-separation). No assumption is made about DNp01's outbound
targets in V0. Flagged here as an open question for the next phase.

## 4. Interface-layer decisions (explicitly ours to make, per brief section 16)

These are NOT biological facts; they are documented, exposed, and
changeable engineering choices for the sensory interface and interpretation
layers, per the brief's explicit instruction not to silently invent such
decisions but to expose them as configuration.

| decision | where | default | rationale |
|---|---|---|---|
| Looming drive = rectified expansion rate `d(theta)/dt`, not raw angular size | `brain/sensory/looming.py` | — | LC4/LPLC2 are known loom detectors tuned to expansion rate; this is a simplifying interface choice for V0, not a literature-matched receptive-field model |
| Stimulus-to-conductance gain | `brain/sensory/encoders.py`, `gain_mV_per_unit`; locked for Phase 0B in `experiments/phase_0b/locked_parameters.py` | 16.0 mV per (deg/ms) | Tuned only against the synthetic test fixture so the demonstration circuit produces a clear suprathreshold/subthreshold contrast; has no meaning at real FAFB_v783 scale. Phase 0B step 2 runs it unmodified against real data deliberately, to find out what it actually produces. Any change to it after that must go through `simulation/run_ledger.py` with an explicit `--change-reason` — it is never silently retuned (see `docs/PROJECT_STATUS.md`) |
| Escape-event firing-rate threshold | `brain/motor/descending.py`, `DEFAULT_ESCAPE_RATE_THRESHOLD_HZ` | 50.0 Hz over a 5 ms window | A behavioural interpretation threshold, not a measured constant; kept fully separate from the neuron model (layer-separation rule) so it can change without touching the simulation |
| Random seed has no numeric effect | `simulation/engine/lif_engine.py` | — | V0's LIF model has no stochastic term; `seed` is threaded through via `numpy.random.default_rng` for forward compatibility (future noise models) and to satisfy the "deterministic given seed" requirement, but currently the result is identical for any seed value given identical other inputs |

## 4b. Missing (NaN) neurotransmitter predictions — real-data decision, confirmed against the actual download

Discovered on the first real Phase 0B validation run: 19,658/139,255
(14.1%) of neurons and 1,478,338/22,697,441 (6.5%) of raw connection rows
in the real FlyWire data have **no** neurotransmitter prediction at all
(`nt_type` is missing/NaN) — a real, expected gap in FlyWire's own
predictions (not every neuron has a confident NT call), not a data error
or a sign that something is broken.

| parameter | reference value | value used | reason | effect on output |
|---|---|---|---|---|
| Sign of a connection with missing NT | not addressed in brief or by Shiu et al. 2024 | **0** (zero signed weight — excluded from signal propagation) | Guessing excitatory or inhibitory for ~6.5% of real connections would corrupt every downstream causal claim; zero is the only choice that asserts nothing we don't know | These connections structurally exist in the connectome (counted in neuron/pair/synapse totals) but never contribute to LIF signal propagation. User-confirmed decision (see chat record) rather than silently invented. |

Implementation: `brain.connectivity.validation._check_neurotransmitter_signs_known`
treats missing/NaN as the one permitted "unknown" case (any OTHER
unrecognized non-null value still fails validation loudly);
`brain.connectivity.build_connectome._signed_weight` leaves the signed
weight at its zero-initialized default for any value not in the known
excitatory/inhibitory sets. Counts are reported transparently in the build
manifest (`unknown_nt_neuron_count`, `unknown_nt_connection_count`) — never
silently dropped from view.

## 4c. Azimuth-based hemifield stimulus routing (Phase 0D) — a deliberate simplification, not a retinotopic model

`azimuth_deg` existed on `LoomingStimulusParams` since Phase 0A but was
never used anywhere in the sensory encoding — every stimulus drove
LC4/LPLC2 bilaterally regardless of the angle it claimed to come from.
This was a real gap, not a placeholder: it made any left/right
steering/lateralization experiment meaningless until fixed.

| parameter | reference value | value used | reason | effect on output |
|---|---|---|---|---|
| Spatial routing of visual drive by azimuth | none — not addressed by Shiu et al. 2024 or the V0 brief | **Binary hemifield split**: negative azimuth drives only that population's `_L` (left-side) neurons; positive drives only `_R`; azimuth 0 (or no side-split available) drives both, as before | A real retinotopic/receptive-field model of the visual system is a much larger, separate project (see brief section 16 — "do not independently invent new sensory pathways"); a coarse, transparent, binary split is the simplest change that makes azimuth do anything at all, and is fully documented rather than silently invented | LC4/LPLC2 spikes now differ by stimulus side (`simulation.session._lateralized_sensory_indices`), enabling the DNa02_L/DNa02_R steering readout below. It is NOT a claim about how the real fly's optic lobe columns actually map visual angle to neuron identity. |

**DNa02-L/DNa02-R steering readout**: identified via `consolidated_cell_types.csv`'s `primary_type == "DNa02"` (2 neurons in both the real dataset and Phase 0A fixture) crossed with `classification.csv`'s `side` column — confirmed against the real download to contain exactly the documented left/right pair (see `docs/DATA_PROVENANCE.md`). The steering signal is defined as `left_firing_rate_hz - right_firing_rate_hz` per Rayshubskiy et al. 2025 (eLife 2025;13:RP102230) — DNa02 activity difference reported as approximately linearly related to rotational velocity, left DNa02 predicting leftward steering. This project does **not** independently verify that correlation; it only measures whether OUR simulated DNa02-L/R activity is azimuth-sensitive at all.

**Real-data finding (first run, `FAFB_v783_kaggle_mirror`, not yet independently interpreted):** the steering signal DOES reverse sign with azimuth (confirming the circuit is azimuth-sensitive end to end), but in a **contralateral** pattern — a threat on the right produces MORE left-DNa02 activity, i.e. a turn-away-from-threat pattern, not a turn-toward pattern. This is reported as an observation, not validated against the literature on LC4/LPLC2→DNa02 connectivity specifically; an escape circuit turning away from threat is at least as plausible as one orienting toward it, but this project does not assert which is correct. Additionally, the nominally-symmetric azimuth=0 condition did NOT produce a near-zero steering signal (+43.3 Hz observed) — the real FlyWire connectome is one individually reconstructed fly, not an idealized bilaterally-symmetric model, so some baseline left/right asymmetry is expected; the magnitude found is flagged for follow-up, not treated as a bug to silently correct.

## 5. Synthetic test fixture — not biological data

`tests/fixtures/*.csv.gz` (generated by `tests/fixtures/generate_fixtures.py`)
are small synthetic files used only to exercise the code paths without a
licensed download. They declare their own `test_fixture_v0` dataset version
with their own expected counts (24 neurons / 38 pairs / 1600 synapses / 4
LC4 / 4 LPLC2 / 2 DNp01) and make no claim to represent real fly biology.
See `tests/fixtures/README.md`.

## 6. Optional Brian2 cross-check — not run by default

The brief allows Brian2 as an optional reference/cross-check dependency. It
is not installed by default (`requirements/requirements-dev.txt`) and no
Brian2-based test currently runs; `tests/test_lif_model.py` instead
cross-checks the vectorized engine against a scalar Python reimplementation
of the same documented equations, which catches implementation bugs but is
not an independent second implementation. Adding a genuine Brian2
cross-check is left as documented future work, not invented here.

## What is explicitly NOT modeled in V0 (per brief section 2)

Dopamine, learning, synaptic plasticity, hunger/arousal, multiple flies,
GPU/CUDA execution, biomechanical body physics, and any AI/LLM-based
interpretation are all out of scope and not present anywhere in this
codebase.
