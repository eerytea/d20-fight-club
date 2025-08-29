# core/constants.py
from __future__ import annotations
from typing import Dict

# Canonical race codes (snake_case). UI pretty-prints via .replace('_',' ').title()
RACES = [
    "human","dwarf","goblin","orc","high_elf","sea_elf","dark_elf","wood_elf",
    "golem","dark_dwarf","dark_gnome","gnome","birdkin","lizardkin","catkin","bullkin",
]

# Display names if ever needed outside UI helpers
RACE_DISPLAY: Dict[str, str] = {code: code.replace('_',' ').title() for code in RACES}

# Racial ability bonuses (your exact spec)
# Values are deltas applied to the base ability scores (standard array assignment).
RACE_TRAITS: Dict[str, Dict[str, int]] = {
    "human":       {"STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": 1},  # unchanged
    "dwarf":       {"STR": 2, "CON": 2},
    "high_elf":    {"DEX": 2, "INT": 1},
    "wood_elf":    {"DEX": 2, "WIS": 1},
    "dark_elf":    {"DEX": 2, "CHA": 1},
    "sea_elf":     {"DEX": 2, "CON": 1},
    "orc":         {"STR": 2, "CON": 1},
    "goblin":      {"DEX": 2, "CON": 1},
    "birdkin":     {"DEX": 2, "WIS": 1},
    "catkin":      {"DEX": 2, "CHA": 1},
    "bullkin":     {"STR": 2, "CON": 1},
    "lizardkin":   {"CON": 2, "WIS": 1},
    "dark_gnome":  {"INT": 2, "DEX": 1},
    "gnome":       {"INT": 2, "CON": 1, "DEX": 1},
    "dark_dwarf":  {"CON": 2, "STR": 1},
    "golem":       {"CON": 2, "STR": 2},
}

DEV_TRAITS: Dict[str, float] = {
    "bad": 0.75,
    "normal": 1.00,
    "star": 1.25,
    "superstar": 1.50,
}

# default per-team race weights (equal). A team can override by setting team["race_weights"].
DEFAULT_RACE_WEIGHTS: Dict[str, float] = {race: 1.0 for race in RACES}
