# core/config.py
from __future__ import annotations

# -------- League / Season --------
LEAGUE_TEAMS: int = 8            # total teams in the league (adjust as you like)
TEAM_SIZE: int = 5               # roster size per team
ROUNDS_DOUBLE_ROUND_ROBIN: int = 2  # each opponent twice (home/away)

# Points (W-D-L = 3-1-0)
POINTS_WIN: int = 3
POINTS_DRAW: int = 1
POINTS_LOSS: int = 0

# Tiebreakers (in order):
# 1) Kill Difference (PF - PA), 2) Head-to-Head (mini-table over tied teams)
TIEBREAKERS = ("KILL_DIFF", "HEAD_TO_HEAD")

# -------- Match / Grid --------
GRID_W: int = 11
GRID_H: int = 11
TURN_LIMIT: int = 100  # allow draws if we hit this

# -------- RNG / Seeds --------
DEFAULT_SEED: int = 1337

# -------- UI / Misc --------
SAVE_DIR = "saves"
