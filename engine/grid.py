from __future__ import annotations
from typing import List

from .model import Fighter

def layout_teams_tiles(fighters: List[Fighter], grid_w: int, grid_h: int) -> None:
    """
    Simple deterministic placement:
      - team 0 starts on the left columns (x=1..2)
      - team 1 starts on the right columns (x=grid_w-2..grid_w-1)
      - y spreads from top downward without overlap
    Mutates fighters' (tx, ty) in place.
    """
    left_cols = [1, 2]
    right_cols = [max(grid_w - 2, 0), max(grid_w - 1, 0)]

    t0 = [f for f in fighters if f.team_id == 0]
    t1 = [f for f in fighters if f.team_id == 1]

    def place(lineup: List[Fighter], cols: List[int]) -> None:
        y = 1
        col_i = 0
        for f in lineup:
            f.tx = cols[col_i % len(cols)]
            f.ty = y
            y += 2
            if y >= grid_h - 1:
                y = 1
                col_i += 1

    place(t0, left_cols)
    place(t1, right_cols)
