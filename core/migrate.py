# core/migrate.py
from __future__ import annotations
from typing import Dict, Any

CURRENT_SCHEMA_VERSION = 1

def migrate_save(blob: Dict[str, Any], version: int) -> Dict[str, Any]:
    """
    Returns a new blob upgraded to CURRENT_SCHEMA_VERSION.
    For now, only ensures keys exist and converts any old shapes if needed.
    """
    data = dict(blob)
    if version == CURRENT_SCHEMA_VERSION:
        return data

    # v0 -> v1: wrap raw "career" dict if missing; ensure h2h map shape is correct
    if version < 1:
        career = data.get("career", data)
        # normalize missing keys
        career.setdefault("week", 0)
        career.setdefault("teams", career.get("teams", []))
        career.setdefault("fixtures", career.get("fixtures", []))
        career.setdefault("table", career.get("table", {}))
        career.setdefault("h2h", career.get("h2h", {}))
        data = {"schema_version": 1, "career": career}

    data["schema_version"] = CURRENT_SCHEMA_VERSION
    return data
