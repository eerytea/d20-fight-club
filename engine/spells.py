# engine/spells.py
from __future__ import annotations
from typing import Iterable, List, Tuple

# Cardinal line (no diagonals), from (sx,sy) stepping toward (tx,ty), up to length tiles.
# If dx and dy are both non-zero, we choose the dominant axis (whichever delta is larger).
def line_aoe_cells(sx: int, sy: int, tx: int, ty: int, length: int, cols: int, rows: int) -> List[Tuple[int,int]]:
    length = max(1, int(length))
    dx = tx - sx
    dy = ty - sy
    # choose cardinal axis by dominant delta; break ties preferring X
    if abs(dx) >= abs(dy):
        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 0
    else:
        step_x = 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0
    out: List[Tuple[int,int]] = []
    cx, cy = sx, sy
    for _ in range(length):
        cx += step_x; cy += step_y
        if 0 <= cx < cols and 0 <= cy < rows:
            out.append((cx, cy))
        else:
            break
    return out
