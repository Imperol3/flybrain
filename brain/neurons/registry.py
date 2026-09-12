"""Neuron identity registry: root_id <-> connectome matrix index, and named populations.

This is the only place that knows how a raw FlyWire root_id maps to a row/
column in the sparse connectome matrix built by
brain.connectivity.build_connectome. The simulation layer works purely in
matrix-index space and asks this registry to resolve named populations
(LC4, LPLC2, DNp01, ...) — it never re-derives population membership from
raw CSVs itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import config


class UnknownPopulationError(KeyError):
    pass


class UnknownNeuronIdError(KeyError):
    pass


@dataclass(frozen=True)
class NeuronRegistry:
    root_ids: tuple[int, ...]            # matrix-index-ordered
    populations: dict[str, tuple[int, ...]]  # population name -> root_ids
    dataset_version: str

    @property
    def n_neurons(self) -> int:
        return len(self.root_ids)

    def _id_to_index(self) -> dict[int, int]:
        # Not cached on the frozen dataclass to keep it a plain, picklable
        # data holder; callers doing many lookups should build this once
        # via index_map().
        return {rid: i for i, rid in enumerate(self.root_ids)}

    def index_map(self) -> dict[int, int]:
        return self._id_to_index()

    def index_of(self, root_id: int) -> int:
        idx = self._id_to_index().get(root_id)
        if idx is None:
            raise UnknownNeuronIdError(f"root_id {root_id} is not present in this connectome build")
        return idx

    def population_root_ids(self, name: str) -> tuple[int, ...]:
        try:
            return self.populations[name]
        except KeyError as exc:
            raise UnknownPopulationError(
                f"No population named {name!r} in this connectome build; known populations: "
                f"{sorted(self.populations)}"
            ) from exc

    def population_indices(self, name: str) -> np.ndarray:
        id_to_index = self._id_to_index()
        return np.array([id_to_index[rid] for rid in self.population_root_ids(name)], dtype=np.int64)


def save(registry: NeuronRegistry, path: Path | None = None) -> None:
    path = path or config.CONNECTOME_INDEX
    payload = {
        "dataset_version": registry.dataset_version,
        "root_ids": list(registry.root_ids),
        "populations": {name: list(ids) for name, ids in registry.populations.items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load(path: Path | None = None) -> NeuronRegistry:
    path = path or config.CONNECTOME_INDEX
    if not path.exists():
        raise FileNotFoundError(
            f"No connectome index at {path}. Run `python -m brain.connectivity.build_connectome` first."
        )
    payload = json.loads(path.read_text())
    return NeuronRegistry(
        root_ids=tuple(payload["root_ids"]),
        populations={name: tuple(ids) for name, ids in payload["populations"].items()},
        dataset_version=payload["dataset_version"],
    )
