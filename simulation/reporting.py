"""Structured (JSON) + human-readable experiment output, per the brief's schema (section 12)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import config
from brain import provenance


def session_result_to_condition_dict(result) -> dict:
    return {
        "condition": result.condition_name,
        "seed": result.seed,
        "silenced_populations": list(result.silenced_populations),
        "lc4_spike_count": result.lc4_spike_count,
        "lplc2_spike_count": result.lplc2_spike_count,
        "dnp01_spike_count": result.dnp01_spike_count,
        "dnp01_peak_firing_rate_hz": result.dnp01_peak_firing_rate_hz,
        "n_active_neurons": result.n_active_neurons,
        "first_sensory_spike_time_ms": result.first_sensory_spike_time_ms,
        "first_dnp01_spike_time_ms": result.first_dnp01_spike_time_ms,
        "escape_triggered": result.escape_triggered,
        "escape_trigger_time_ms": result.escape_trigger_time_ms,
        "lateralized": result.lateralized,
        "simulation_duration_ms": result.simulation_duration_ms,
        "wall_clock_runtime_s": result.wall_clock_runtime_s,
        "parameters": result.parameters,
        "time_series": list(result.time_series),
    }


def write_experiment_output(
    experiment_name: str,
    dataset_version: str,
    seed: int,
    conditions: list[dict],
    parameters: dict,
    runtime: dict,
) -> Path:
    payload = {
        "experiment": experiment_name,
        "dataset": dataset_version,
        "seed": seed,
        "conditions": conditions,
        "parameters": parameters,
        "runtime": runtime,
        "git_commit": provenance.get_git_commit(),
    }
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = config.OUTPUTS_DIR / f"{experiment_name}_{timestamp}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path
