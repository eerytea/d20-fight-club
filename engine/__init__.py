# engine/__init__.py
"""
Public API for the engine package.

Tests expect these names to be importable from `engine`:
- TBCombat
- Team, Fighter, Weapon, fighter_from_dict
- layout_teams_tiles
"""

from __future__ import annotations

# Explicit, eager re-exports (simple and robust)
from .tbcombat import TBCombat
from .model import Team, Fighter, Weapon, fighter_from_dict
from .grid import layout_teams_tiles

__all__ = [
    "TBCombat",
    "Team",
    "Fighter",
    "Weapon",
    "fighter_from_dict",
    "layout_teams_tiles",
]
