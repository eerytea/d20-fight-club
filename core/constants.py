# core/constants.py
from __future__ import annotations
from typing import Dict

# Canonical race codes (snake_case). UI pretty-prints via .replace('_',' ').title()
RACES = [
    "human","dwarf","goblin","orc","high_elf","sea_elf","dark_elf","wood_elf",
    "golem","dark_dwarf","dark_gnome","gnome","birdkin","lizardkin","catkin","bullkin",
]

RACE_DISPLAY: Dict[str, str] = {code: code.replace('_',' ').title() for code in RACES}

# Your exact racial ability bonuses
RACE_TRAITS: Dict[str, Dict[str, int]] = {
    "human":       {"STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": 1},
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

# New: canonical base speed per race (tiles/turn)
RACE_SPEED: Dict[str, int] = {
    "birdkin": 5,
    "dwarf": 5,
    "dark_dwarf": 5,
    "human": 6,
    "high_elf": 6,
    "sea_elf": 6,
    "dark_elf": 6,
    "wood_elf": 7,
    "dark_gnome": 5,
    "gnome": 5,
    "golem": 6,
    "lizardkin": 6,
    "catkin": 6,
    "bullkin": 6,
    "goblin": 5,
    "orc": 6,
}

DEV_TRAITS: Dict[str, float] = {
    "bad": 0.75,
    "normal": 1.00,
    "star": 1.25,
    "superstar": 1.50,
}

# default per-team race weights (equal). A team can override by setting team["race_weights"].
DEFAULT_RACE_WEIGHTS: Dict[str, float] = {race: 1.0 for race in RACES}
