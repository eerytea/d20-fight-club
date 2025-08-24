# engine/grid.py
from __future__ import annotations

from typing import Dict, List, Tuple, Iterable

from .model import Team, Fighter


DEFAULT_WIDTH = 10
DEFAULT_HEIGHT = 8
LEFT_X = 1
RIGHT_X_OFFSET = 2  # right team starts at width - RIGHT_X_OFFSET


def _spread_rows(n: int, height: int) -> List[int]:
    """
    Returns a list of 'n' distinct row indices (0..height-1) spread as evenly as possible,
    centered around the middle rows. Deterministic for test stability.
    """
    if n <= 0:
        return []
    rows = list(range(height))
    mid = height // 2
    order: List[int] = []
    i = 0
    while len(order) < height:
        a = mid - i
        b = mid + i
        if 0 <= a < height:
            order.append(a)
        if b != a and 0 <= b < height:
            order.append(b)
        i += 1
    return order[:n]


def _flatten_fighters(objs: Iterable) -> List[Fighter]:
    """
    Accept either:
      - a flat iterable of Fighters, or
      - two Teams (Team, Team), or
      - any iterable containing Fighters and/or Teams.
    Returns a flat fighter list.
    """
    fighters: List[Fighter] = []
    items = list(objs)
    if len(items) == 2 and all(isinstance(x, Team) for x in items):
        for t in items:  # type: ignore[assignment]
            fighters.extend(t.fighters)
        return fighters
    for x in items:
        if isinstance(x, Fighter):
            fighters.append(x)
        elif isinstance(x, Team):
            fighters.extend(x.fighters)
        elif isinstance(x, (list, tuple)):
            fighters.extend(_flatten_fighters(x))
    return fighters


def layout_teams_tiles(
    objs,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> Dict[int, Tuple[int, int]]:
    """
    Flexible layout to match tests:
      - If given a FLAT LIST of fighters (each with .team_id in {0,1}),
        set f.tx/f.ty and return {fighter_id: (x, y)} with team 0 on the left
        and team 1 on the right.
      - If given (TeamA, TeamB), also supported.
    Deterministic and stateless for easy testing.
    """
    if width < 3:
        raise ValueError("Grid width too small to layout two teams.")
    if height < 1:
        raise ValueError("Grid height must be >= 1.")

    fighters = _flatten_fighters(objs)
    team0 = [f for f in fighters if getattr(f, "team_id", 0) == 0]
    team1 = [f for f in fighters if getattr(f, "team_id", 0) == 1]

    xa = LEFT_X
    xb = max(0, width - RIGHT_X_OFFSET)

    ra = _spread_rows(len(team0), height)
    rb = _spread_rows(len(team1), height)

    pos: Dict[int, Tuple[int, int]] = {}

    for f, y in zip(team0, ra):
        f.tx, f.ty = xa, y  # <-- tests rely on these attributes
        pos[f.id] = (f.tx, f.ty)
    for f, y in zip(team1, rb):
        f.tx, f.ty = xb, y
        pos[f.id] = (f.tx, f.ty)

    return pos
