# engine/__init__.py
from .tbcombat import TBCombat  # adjust if your class/module is named differently
from .model import Fighter, Weapon, Team
from .grid import layout_teams_tiles
from .tbcombat import TBCombat
from .model import Fighter, Weapon, Team, fighter_from_dict
from .grid import layout_teams_tiles

__all__ = [
    "TBCombat", "Fighter", "Weapon", "Team",
    "layout_teams_tiles", "fighter_from_dict",
]
# expose fighter_from_dict wherever it lives
try:
    from .model import fighter_from_dict  # preferred
except Exception:
    try:
        from core.creator import fighter_from_dict  # fallback if you keep it in core
    except Exception:
        def fighter_from_dict(*args, **kwargs):
            raise ImportError(
                "Define fighter_from_dict in engine/model.py or core/creator.py and re-export in engine/__init__.py"
            )

__all__ = [
    "TBCombat", "Fighter", "Weapon", "Team",
    "layout_teams_tiles", "fighter_from_dict"
]
from .tbcombat import TBCombat
from .model import Fighter, Weapon, Team, fighter_from_dict
from .grid import layout_teams_tiles

__all__ = [
    "TBCombat", "Fighter", "Weapon", "Team",
    "layout_teams_tiles", "fighter_from_dict",
]
