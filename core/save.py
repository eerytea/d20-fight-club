# core/save.py
from __future__ import annotations
from pathlib import Path
from .types import Career

def save_career(career: Career, path: str | Path) -> None:
    path = Path(path)
    path.write_text(career.to_json(), encoding="utf-8")

def load_career(path: str | Path) -> Career:
    path = Path(path)
    return Career.from_json(path.read_text(encoding="utf-8"))

from core.save import save_career, load_career

# write main save
save_career(career, "saves/career.json")

# read it later
career = load_career("saves/career.json")

from core.save import save_career
save_career(career, "saves/autosave.json")

from datetime import datetime, timezone
from pathlib import Path
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
Path("saves/backups").mkdir(parents=True, exist_ok=True)
save_career(career, f"saves/backups/career_{ts}.json")
