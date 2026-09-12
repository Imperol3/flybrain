"""Live local backend for the connectome UI.

Wraps the exact same simulation.session.run_looming_session used by every
CLI experiment behind an HTTP API, so the browser UI can trigger a REAL
simulation on demand instead of only replaying baked-in JSON.

Run with:
    uvicorn api.main:app --port 8000
(or via the Browser pane's dev-server preview, see .claude/launch.json)

Deliberately NOT gated by simulation.run_ledger's "no silent tuning"
refusal: the run ledger protects the FORMAL, canonical experiment record
(experiments/phase_0b/*, experiments/phase0c_*) from silent parameter
drift between reported results. This API exists for interactive
exploration/play — every call is still logged (data/metadata/ui_session_log.jsonl)
for provenance, but is not blocked on providing a change reason, since
requiring that for every UI slider tweak would defeat the point of
exploring interactively. Formal conclusions still come from the
run-ledger-protected scripts, not from this API.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

import numpy as np
import scipy.sparse as sp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from brain import provenance
from brain.connectivity import loaders
from brain.neurons import registry as registry_module
from brain.sensory import looming
from simulation import reporting, session

app = FastAPI(title="Fly Brain Lab — Live API")

STATIC_DIR = Path(__file__).resolve().parent / "static"
UI_SESSION_LOG = config.METADATA_DIR / "ui_session_log.jsonl"

_state: dict = {"registry": None, "connectome": None, "positions": None}


def _load_backend():
    """Load the already-built connectome/registry (must exist on disk —
    this API never builds one itself, matching the "fail clearly, no
    silent substitution" rule used everywhere else in this project).
    """
    try:
        registry = registry_module.load()
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"{exc} Run `python -m brain.connectivity.build_connectome` before starting this API."
        ) from exc
    connectome = sp.load_npz(config.CONNECTOME_NPZ)
    return registry, connectome


def _extract_positions(flywire_dir: Path, registry) -> dict:
    """Real neuron positions for the populations we care about, plus a
    background sample for anatomical shape — same approach used to build
    the earlier static Connectome Viewer artifact, computed live here
    instead of baked into a file.
    """
    coords = loaders.load_coordinates(flywire_dir)

    def parse_pos(s):
        nums = re.findall(r"-?\d+", s)
        return float(nums[0]), float(nums[1]), float(nums[2])

    parsed = coords["position"].apply(parse_pos)
    coords = coords.assign(
        x=parsed.apply(lambda t: t[0]),
        y=parsed.apply(lambda t: t[1]),
        z=parsed.apply(lambda t: t[2]),
    )
    centroid = coords.groupby("root_id")[["x", "y", "z"]].mean().reset_index()

    pop_root_ids = {name: set(registry.population_root_ids(name)) for name in ("LC4", "LPLC2", "DNp01")}
    all_named = set().union(*pop_root_ids.values())

    populations = {}
    for name, ids in pop_root_ids.items():
        sub = centroid[centroid["root_id"].isin(ids)]
        populations[name] = sub[["x", "y", "z"]].to_dict(orient="records")

    other = centroid[~centroid["root_id"].isin(all_named)]
    rng = np.random.default_rng(0)
    sample_n = min(7000, len(other))
    sample_idx = rng.choice(len(other), size=sample_n, replace=False)
    background = other.iloc[sample_idx][["x", "y", "z"]].to_dict(orient="records")

    all_x, all_y, all_z = centroid["x"].to_numpy(), centroid["y"].to_numpy(), centroid["z"].to_numpy()
    bounds = {
        "x": [float(all_x.min()), float(all_x.max())],
        "y": [float(all_y.min()), float(all_y.max())],
        "z": [float(all_z.min()), float(all_z.max())],
    }
    return {"bounds": bounds, "populations": populations, "background": background}


@app.on_event("startup")
def startup():
    print("Loading connectome/registry...")
    registry, connectome = _load_backend()
    _state["registry"] = registry
    _state["connectome"] = connectome
    print(f"Loaded {registry.dataset_version}: {registry.n_neurons:,} neurons")

    try:
        flywire_dir = config.get_flywire_dir()
    except config.DatasetConfigError:
        flywire_dir = config.PROJECT_ROOT / "data" / "source"
        print(f"FLYWIRE_V783_DIR not set; defaulting to {flywire_dir} for neuron positions")

    if flywire_dir.is_dir():
        print("Extracting neuron positions (real coordinates.csv, one-time at startup)...")
        _state["positions"] = _extract_positions(flywire_dir, registry)
        print("Positions ready.")
    else:
        print(f"WARNING: {flywire_dir} not found — /api/positions will be unavailable.")


class SimulateRequest(BaseModel):
    condition: Literal["looming", "receding", "static"] = "looming"
    approach_velocity_cm_s: float | None = Field(
        default=None, description="Overrides the condition's default velocity if given."
    )
    object_radius_cm: float = 1.0
    initial_distance_cm: float = 20.0
    azimuth_deg: float = 0.0
    stimulus_duration_ms: float = 200.0
    simulation_duration_ms: float = 300.0
    seed: int = 12345
    silenced_populations: list[str] = Field(default_factory=list)
    gain_mV_per_unit: float = 16.0


def _log_ui_run(payload: dict, result_summary: dict) -> None:
    UI_SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp_utc": provenance.utc_now_iso(),
        "request": payload,
        "result_summary": result_summary,
        "git_commit": provenance.get_git_commit(),
    }
    with open(UI_SESSION_LOG, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


@app.get("/api/health")
def health():
    registry = _state["registry"]
    if registry is None:
        raise HTTPException(503, "Backend not loaded")
    return {
        "status": "ok",
        "dataset_version": registry.dataset_version,
        "n_neurons": registry.n_neurons,
        "populations": {name: len(registry.population_root_ids(name)) for name in ("LC4", "LPLC2", "DNp01")},
        "positions_available": _state["positions"] is not None,
    }


@app.get("/api/positions")
def positions():
    if _state["positions"] is None:
        raise HTTPException(503, "Neuron positions unavailable (FLYWIRE_V783_DIR not found at startup)")
    return _state["positions"]


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    registry, connectome = _state["registry"], _state["connectome"]
    if registry is None:
        raise HTTPException(503, "Backend not loaded")

    factory = {"looming": looming.looming, "receding": looming.receding, "static": looming.static}[req.condition]
    kwargs = dict(
        object_radius_cm=req.object_radius_cm,
        initial_distance_cm=req.initial_distance_cm,
        azimuth_deg=req.azimuth_deg,
        stimulus_duration_ms=req.stimulus_duration_ms,
        simulation_duration_ms=req.simulation_duration_ms,
        seed=req.seed,
    )
    if req.approach_velocity_cm_s is not None:
        kwargs["approach_velocity_cm_s"] = req.approach_velocity_cm_s
    stimulus_params = factory(**kwargs)

    try:
        result = session.run_looming_session(
            registry,
            connectome,
            stimulus_params,
            condition_name=req.condition,
            silenced_populations=tuple(req.silenced_populations),
            gain_mV_per_unit=req.gain_mV_per_unit,
        )
    except Exception as exc:  # noqa: BLE001 — surface to the UI as a clear error, not a 500 stack trace
        raise HTTPException(400, f"Simulation failed: {exc}") from exc

    condition_dict = reporting.session_result_to_condition_dict(result)
    _log_ui_run(
        req.model_dump(),
        {
            "lc4": condition_dict["lc4_spike_count"],
            "lplc2": condition_dict["lplc2_spike_count"],
            "dnp01": condition_dict["dnp01_spike_count"],
            "escape_triggered": condition_dict["escape_triggered"],
        },
    )
    return condition_dict


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
