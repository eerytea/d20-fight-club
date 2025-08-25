# engine/grid.py
from __future__ import annotations
from typing import List, Any


def layout_teams_tiles(fighters: List[Any], grid_w: int, grid_h: int) -> None:
    """
    Assign tile coords (tx, ty) in-bounds and separated by team.
    Assumes fighters have a .team_id attribute (0 for home, 1 for away).
    This function mutates fighters: sets f.tx and f.ty.
    """
    # Split by team id
    team0 = [f for f in fighters if getattr(f, "team_id", 0) == 0]
    team1 = [f for f in fighters if getattr(f, "team_id", 0) == 1]

    # Left and right bands (leave a column of padding)
    left_min_x = 1
    left_max_x = max(left_min_x, grid_w // 3)
    right_min_x = max(grid_w - (grid_w // 3) - 1, 0)
    right_max_x = max(grid_w - 2, right_min_x)

    def place_line(fs: List[Any], x_band_min: int, x_band_max: int) -> None:
        if not fs:
            return
        # Use up to two columns within the band for spacing
        cols = [max(x_band_min, 0), min(x_band_max, grid_w - 1)]
        y = 1
        col_idx = 0
        for f in fs:
            x = cols[col_idx % len(cols)]
            # Clamp y
            if y >= grid_h - 1:
                y = 1
                col_idx += 1
                x = cols[col_idx % len(cols)]
            # Set attributes (be robust if Fighter doesn't define tx/ty)
            setattr(f, "tx", int(max(0, min(grid_w - 1, x))))
            setattr(f, "ty", int(max(0, min(grid_h - 1, y))))
            y += 2  # vertical spacing

    place_line(team0, left_min_x, left_max_x)
    place_line(team1, right_min_x, right_max_x)
