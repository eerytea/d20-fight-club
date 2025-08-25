# core/ratings_consts.py
from __future__ import annotations
from typing import Dict

# Canonical class data used by creator and ratings.

CLASS_PROFILES: Dict[str, Dict] = {
    "Fighter": {
        "weights": (0.45, 0.40, 0.15),
        "primaries": ["str", "con"],
        "secondaries": ["dex"],
        "attack_stat_priority": ["str", "dex"],
        "melee_damage_stat": "str",
        "weapon": {"name": "Longsword", "damage": "1d8"},
        "armor_ac": 16,
    },
    "Rogue": {
        "weights": (0.50, 0.25, 0.25),
        "primaries": ["dex"],
        "secondaries": ["int", "cha"],
        "attack_stat_priority": ["dex"],
        "melee_damage_stat": "dex",
        "weapon": {"name": "Shortsword", "damage": "1d6"},
        "armor_ac": 14,
    },
    "Barbarian": {
        "weights": (0.55, 0.35, 0.10),
        "primaries": ["str", "con"],
        "secondaries": ["dex"],
        "attack_stat_priority": ["str"],
        "melee_damage_stat": "str",
        "weapon": {"name": "Greataxe", "damage": "1d12"},
        "armor_ac": 14,
    },
    "Sorcerer": {
        "weights": (0.55, 0.25, 0.20),
        "primaries": ["cha"],
        "secondaries": ["con"],
        "attack_stat_priority": ["cha"],
        "spell_damage_stat": "cha",
        "weapon": {"name": "Wand", "damage": "1d6"},
        "armor_ac": 12,
    },
    # Minimal profiles so class selection never KeyErrors
    "Wizard": {
        "weights": (0.50, 0.25, 0.25),
        "primaries": ["int"],
        "secondaries": ["con", "dex"],
        "attack_stat_priority": ["int"],
        "spell_damage_stat": "int",
        "weapon": {"name": "Staff", "damage": "1d6"},
        "armor_ac": 12,
    },
    "Cleric": {
        "weights": (0.40, 0.40, 0.20),
        "primaries": ["wis", "con"],
        "secondaries": ["str"],
        "attack_stat_priority": ["wis", "str"],
        "melee_damage_stat": "str",
        "weapon": {"name": "Mace", "damage": "1d6"},
        "armor_ac": 16,
    },
}

CLASS_WEIGHTS: Dict[str, Dict[str, int]] = {
    "Fighter":   {"str": 3, "dex": 1, "con": 2, "int": 0, "wis": 0, "cha": 0},
    "Barbarian": {"str": 3, "dex": 0, "con": 3, "int": 0, "wis": 0, "cha": 0},
    "Rogue":     {"str": 0, "dex": 3, "con": 1, "int": 1, "wis": 0, "cha": 1},
    "Wizard":    {"str": 0, "dex": 1, "con": 1, "int": 3, "wis": 0, "cha": 0},
    "Cleric":    {"str": 0, "dex": 0, "con": 2, "int": 0, "wis": 3, "cha": 0},
    "Sorcerer":  {"str": 0, "dex": 1, "con": 1, "int": 0, "wis": 0, "cha": 3},
}
ALL_CLASSES = list(CLASS_WEIGHTS.keys())
