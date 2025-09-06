# core/config.py
from __future__ import annotations

# -------- League / Season --------
LEAGUE_TEAMS: int = 20               # <-- 20 teams in the league
TEAM_SIZE: int = 5                   # 5 players per team
ROUNDS_DOUBLE_ROUND_ROBIN: int = 2   # each opponent twice (home/away) → 38 rounds

# Points (W-D-L = 3-1-0)
POINTS_WIN: int = 3
POINTS_DRAW: int = 1
POINTS_LOSS: int = 0

# Tiebreakers (in order):
# 1) Kill Difference (PF - PA), 2) Head-to-Head (mini-table over tied teams)
TIEBREAKERS = ("KILL_DIFF", "HEAD_TO_HEAD")

# -------- Match / Grid --------
TURN_LIMIT: int = 100

# -------- RNG / Seeds --------
DEFAULT_SEED: int = 1337

# -------- UI / Misc --------
SAVE_DIR = "saves"
