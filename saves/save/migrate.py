from __future__ import annotations
from typing import Any, Dict

def migrate_save(data: Dict[str, Any]) -> Dict[str, Any]:
    """No-op for now. Bump SCHEMA_VERSION and add steps here when structure changes."""
    return data
