# core/save.py
from __future__ import annotations
from pathlib import Path
from .types import Career

def save_career(career: Career, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(career.to_json(), encoding="utf-8")

def load_career(path: str | Path) -> Career:
    path = Path(path)
    return Career.from_json(path.read_text(encoding="utf-8"))
