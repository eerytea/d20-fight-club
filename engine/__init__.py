# engine/__init__.py
"""
Public API for the engine package.

We lazily expose:
- TBCombat                (from engine.tbcombat)
- Team, Fighter, Weapon,
  fighter_from_dict       (from engine.model)
- layout_teams_tiles      (from engine.grid)

The lazy loader avoids circular imports and lets us attach small shims (e.g. take_turn alias).
"""

__all__ = [
    "TBCombat",
    "Team",
    "Fighter",
    "Weapon",
    "fighter_from_dict",
    "layout_teams_tiles",
]

# PEP 562: module-level __getattr__ for lazy exports
def __getattr__(name: str):
    if name == "TBCombat":
        # Import TBCombat from the real engine
        from . import tbcombat as _tb
        cls = _tb.TBCombat
        # Back-compat: some tests call TBCombat.take_turn(), alias to step_action()
        if not hasattr(cls, "take_turn"):
            def _take_turn(self):
                return self.step_action()
            setattr(cls, "take_turn", _take_turn)
        return cls

    if name in ("Team", "Fighter", "Weapon", "fighter_from_dict"):
        from . import model as _model
        return getattr(_model, name)

    if name == "layout_teams_tiles":
        from . import grid as _grid
        return _grid.layout_teams_tiles

    raise AttributeError(f"module 'engine' has no attribute {name!r}")

def __dir__():
    return sorted(__all__)
