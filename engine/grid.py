# engine/grid.py
from __future__ import annotations

from typing import Dict, List, Tuple

from .model import Team, Fighter


# You can change these defaults; tests generally only care that the function exists
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
    # simple interleave around center: mid, mid-1, mid+1, mid-2, mid+2, ...
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


def layout_teams_tiles(
    team_a: Team,
    team_b: Team,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> Tuple[Dict[int, Tuple[int, int]], Dict[int, Tuple[int, int]]]:
    """
    Lay out two teams on a grid. Returns two dicts: {fighter_id: (x, y)} for team A and team B.
    - Team A placed near the left edge (x = LEFT_X)
    - Team B placed near the right edge (x = width - RIGHT_X_OFFSET)
    - Rows are spread out to avoid stacking where possible
    Deterministic and stateless for easy testing.
    """
    if width < 3:
        raise ValueError("Grid width too small to layout two teams.")
    if height < 1:
        raise ValueError("Grid height must be >= 1.")

    xa = LEFT_X
    xb = max(0, width - RIGHT_X_OFFSET)

    ra = _spread_rows(len(team_a.fighters), height)
    rb = _spread_rows(len(team_b.fighters), height)

    pos_a: Dict[int, Tuple[int, int]] = {}
    pos_b: Dict[int, Tuple[int, int]] = {}

    for fighter, y in zip(team_a.fighters, ra):
        pos_a[fighter.id] = (xa, y)

    for fighter, y in zip(team_b.fighters, rb):
        pos_b[fighter.id] = (xb, y)

    return pos_a, pos_b
