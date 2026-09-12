"""Append-only run ledger: makes silent parameter drift between runs impossible.

Every Phase 0B script calls record_run(...) with the exact parameters it
used. If those parameters differ from the previous recorded run of the same
experiment and no `change_reason` is given, recording refuses (raises)
rather than silently logging a changed value — this is what prevents
someone (human or agent) from quietly re-tuning e.g. stimulus gain across
runs until the network "gives the expected answer".

Ledger entries are appended as one JSON object per line to
config.RUN_LEDGER_PATH, giving a permanent RUN 001 / RUN 002 / ... history
per experiment name.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import config
from brain import provenance


class SilentParameterChangeError(RuntimeError):
    """Raised when a run's parameters differ from the previous run of the
    same experiment but no change_reason was supplied."""


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    run_number: int
    timestamp_utc: str
    experiment: str
    dataset_version: str
    parameters_hash: str
    parameters: dict
    changed_from_previous: bool
    change_reason: str | None
    git_commit: str

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "run_number": self.run_number,
            "timestamp_utc": self.timestamp_utc,
            "experiment": self.experiment,
            "dataset_version": self.dataset_version,
            "parameters_hash": self.parameters_hash,
            "parameters": self.parameters,
            "changed_from_previous": self.changed_from_previous,
            "change_reason": self.change_reason,
            "git_commit": self.git_commit,
        }


def _hash_parameters(parameters: dict) -> str:
    canonical = json.dumps(parameters, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read_ledger() -> list[dict]:
    if not config.RUN_LEDGER_PATH.exists():
        return []
    entries = []
    for line in config.RUN_LEDGER_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def get_last_run(experiment: str) -> dict | None:
    matching = [e for e in _read_ledger() if e["experiment"] == experiment]
    return matching[-1] if matching else None


def get_run_history(experiment: str) -> list[dict]:
    return [e for e in _read_ledger() if e["experiment"] == experiment]


def record_run(
    experiment: str,
    dataset_version: str,
    parameters: dict,
    change_reason: str | None = None,
) -> RunRecord:
    """Append one entry to the run ledger.

    Raises SilentParameterChangeError if `parameters` differs from the
    previous recorded run of this experiment and `change_reason` is None.
    The very first run of an experiment always succeeds and establishes the
    baseline.
    """
    last = get_last_run(experiment)
    param_hash = _hash_parameters(parameters)

    if last is None:
        run_number = 1
        changed = False
    else:
        run_number = last["run_number"] + 1
        changed = param_hash != last["parameters_hash"]
        if changed and not change_reason:
            raise SilentParameterChangeError(
                f"Refusing to record {experiment!r} RUN {run_number:03d}: its parameters differ "
                f"from the previous recorded run (RUN {last['run_number']:03d}, "
                f"hash {last['parameters_hash'][:12]}...) but no change_reason was given. "
                "Pass an explicit change_reason describing what changed and why — silent "
                "parameter drift (e.g. re-tuning stimulus gain) between runs is not permitted. "
                f"See {config.RUN_LEDGER_PATH} for the full run history."
            )

    record = RunRecord(
        run_id=f"RUN {run_number:03d}",
        run_number=run_number,
        timestamp_utc=provenance.utc_now_iso(),
        experiment=experiment,
        dataset_version=dataset_version,
        parameters_hash=param_hash,
        parameters=parameters,
        changed_from_previous=changed,
        change_reason=change_reason,
        git_commit=provenance.get_git_commit(),
    )

    config.RUN_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.RUN_LEDGER_PATH, "a") as fh:
        fh.write(json.dumps(record.to_dict()) + "\n")

    return record
