# core/ids.py
from __future__ import annotations
import uuid

def new_id(prefix: str) -> str:
    """
    Create a short, readable ID like 'TID_3f2b8a1c'.
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"