# core/config.py
from __future__ import annotations

# ---- Grid / Match ----
GRID_W: int = 10
GRID_H: int = 8
TURN_LIMIT: int = 3000           # global safety cap for any full-combat sim
TEAM_SIZE: int = 4               # fighters per side that start a match

# ---- League / Table ----
LEAGUE_TEAMS: int = 20
POINTS_WIN: int = 3
POINTS_DRAW: int = 1
POINTS_LOSS: int = 0

# ---- Combat ----
CRIT_NAT: int = 20               # natural d20 that is a critical hit
CRIT_MULTIPLIER: int = 2         # simple crit model (x2 damage)

# ---- Progression (design levers; used where applicable) ----
AGE_BRACKETS = {                 # inclusive ranges
    "young": (18, 23),
    "prime": (24, 28),
    "veteran": (29, 60),
}
AGE_XP_MULT = {
    "young": 1.25,
    "prime": 1.00,
    "veteran": 0.75,
}
DEV_TRAIT_MULT = {
    "bad": 0.85,
    "normal": 1.00,
    "star": 1.15,
    "superstar": 1.30,
}
POTENTIAL_LEVEL: int = 20
