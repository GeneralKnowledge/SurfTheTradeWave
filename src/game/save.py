"""JSON save/load for simulation state."""

from __future__ import annotations

import json
from pathlib import Path

from src.game.simulation import Simulation

DEFAULT_SAVE_DIR = Path("saves")


def save_game(sim: Simulation, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(sim.to_dict(), fh, indent=2)
    return path


def load_game(path: str | Path) -> Simulation:
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return Simulation.from_dict(data)


def default_save_path(slot: int = 1) -> Path:
    return DEFAULT_SAVE_DIR / f"save_{slot}.json"
