# engine/__init__.py
# engine package marker
"""
Public API for the engine package.

We lazily expose:
- TBCombat                (from engine.tbcombat)
- Team, Fighter, Weapon,
  fighter_from_dict       (from engine.model)
- layout_teams_tiles      (from engine.grid)

Using lazy exports avoids circular import issues during package import.
"""

__all__ = [
    "TBCombat",
    "Team",
    "Fighter",
    "Weapon",
    "fighter_from_dict",
    "layout_teams_tiles",
]

def __getattr__(name: str):
    if name == "TBCombat":
        from . import tbcombat as _tb
        return _tb.TBCombat

    if name in ("Team", "Fighter", "Weapon", "fighter_from_dict"):
        from . import model as _model
        return getattr(_model, name)

    if name == "layout_teams_tiles":
        from . import grid as _grid
        return _grid.layout_teams_tiles

    raise AttributeError(f"module 'engine' has no attribute {name!r}")

def __dir__():
    return sorted(__all__)
