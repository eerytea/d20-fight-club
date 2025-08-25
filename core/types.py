# core/types.py
from __future__ import annotations

# Re-export the dataclasses and aliases used across the codebase/tests.
from .career import Career, Fixture
from .standings import TableRow  # Dict[str, int]

__all__ = ["Career", "Fixture", "TableRow"]
