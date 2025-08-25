# core package marker
# core/__init__.py
from .career import new_career
from .sim import simulate_week_ai
from .save import save_career, load_career
from .types import Career, Fixture, TableRow
from .ratings import ovr_from_stats, age_xp_mult, dev_trait_mult, project_potential_l20

__all__ = [
    "new_career",
    "simulate_week_ai",
    "save_career", "load_career",
    "Career", "Fixture", "TableRow",
    "ovr_from_stats", "age_xp_mult", "dev_trait_mult", "project_potential_l20",
]

