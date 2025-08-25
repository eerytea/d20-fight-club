# core/save.py
from __future__ import annotations

import json, os
from typing import Dict, Any
from .career import Career
from .migrate import migrate_save, CURRENT_SCHEMA_VERSION

def save_career(path: str, career: Career) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    blob: Dict[str, Any] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "career": career.to_dict(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2)

def load_career(path: str) -> Career:
    with open(path, "r", encoding="utf-8") as f:
        blob = json.load(f)

    version = int(blob.get("schema_version", 0))
    data = migrate_save(blob, version)
    return Career.from_dict(data["career"])
