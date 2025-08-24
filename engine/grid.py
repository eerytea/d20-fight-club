from typing import List
from .model import Fighter

def layout_teams_tiles(fighters: List[Fighter], W: int, H: int):
    """Place team 0 on left, team 1 on right."""
    left_y = 1
    right_y = 1
    for f in fighters:
        if f.team_id == 0:
            f.tx, f.ty = 2, left_y
            left_y = min(H-2, left_y+2)
        else:
            f.tx, f.ty = W-3, right_y
            right_y = min(H-2, right_y+2)
