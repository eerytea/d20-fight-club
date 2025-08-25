# core/career.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
import itertools

from .config import (
    TEAM_SIZE,
    LEAGUE_TEAMS,
    ROUNDS_DOUBLE_ROUND_ROBIN,
    DEFAULT_SEED,
)
from .schedule import build_double_round_robin
from .standings import new_table, Table, H2HMap, sort_table


# --- Creation helpers ---------------------------------------------------------

def _default_team_name(i: int) -> str:
    # Simple deterministic names; replace with your namebank if desired.
    animals = [
        "Dragons", "Wolves", "Griffins", "Titans",
        "Phantoms", "Knights", "Rangers", "Serpents",
        "Ravens", "Golems", "Magi", "Stalkers",
    ]
    return f"{animals[i % len(animals)]} {100 + i}"

def _generate_teams(
    n: int,
    team_size: int,
    seed: int,
    provided_names: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Uses core.creator.generate_team if available; otherwise falls back to a stub generator.
    Returns a list of team dicts, each with:
      tid, name, color, budget, wage_bill, roster: [fighter dicts ...]
    """
    teams: List[Dict[str, Any]] = []

    try:
        from . import creator  # your v1/v2 fighter+team generator
        have_creator = hasattr(creator, "generate_team")
    except Exception:
        creator = None
        have_creator = False

    for tid in range(n):
        name = (provided_na_
