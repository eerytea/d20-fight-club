# core/constants.py
from __future__ import annotations
from typing import Dict

RACES = [
    "human","dwarf","goblin","orc","high_elf","sea_elf","dark_elf","wood_elf",
    "golem","dark_dwarf","dark_gnome","gnome","birdkin","lizardkin","catkin","bullkin",
]

RACE_DISPLAY: Dict[str, str] = {code: code.replace('_',' ').title() for code in RACES}

# Ability bonuses (as you specified earlier)
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

# Movement speed (tiles/turn)
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

# NEW: Race perk flags/values (non-ability bonuses)
# Conventions:
# - weekly_heal_mult: out-of-combat weekly refill multiplier (hook for Season systems)
# - adv_vs_*: advantage on saving throws against a tag
# - sleep_immune: cannot be affected by "sleep" effects
# - poison_resist: takes half damage from poison damage types
# - extra_hp_per_level: bonus max HP on each level (applies at L1 too)
# - unarmed_dice: base unarmed dice string ("1d4","1d6") using STR mod
# - cunning_action: may Disengage/Hide as a bonus action (engine already lenient; flag stored)
RACE_PERKS: Dict[str, Dict[str, object]] = {
    "human": {},  # Nothing new

    # Elves
    "high_elf": {"weekly_heal_mult": 1.5, "adv_vs_charm": True, "sleep_immune": True},
    "sea_elf":  {"weekly_heal_mult": 1.5, "adv_vs_charm": True, "sleep_immune": True},
    "dark_elf": {"weekly_heal_mult": 1.5, "adv_vs_charm": True, "sleep_immune": True},
    "wood_elf": {"weekly_heal_mult": 1.5, "adv_vs_charm": True, "sleep_immune": True},

    # Dwarves
    "dwarf":      {"extra_hp_per_level": 1, "adv_vs_poison": True, "poison_resist": True},
    "dark_dwarf": {"adv_vs_charm": True, "adv_vs_paralysis": True},

    # Gnomes
    # Advantage on INT/WIS/CHA saves vs magic (we expose as 'adv_vs_magic_mental')
    "gnome":      {"adv_vs_magic_mental": True},
    "dark_gnome": {"adv_vs_magic_mental": True},

    # Goblin
    "goblin": {"cunning_action": True},  # Disengage/Hide as bonus action

    # Golem
    "golem": {"adv_vs_poison": True, "poison_resist": True, "weekly_heal_mult": 1.25},

    # Lizardkin
    "lizardkin": {"unarmed_dice": "1d6"},

    # Bird/Cat/Bull kin unarmed dice
    "birdkin": {"unarmed_dice": "1d4"},
    "catkin":  {"unarmed_dice": "1d4"},
    "bullkin": {"unarmed_dice": "1d6"},

    # Orc
    "orc": {},
}

DEV_TRAITS: Dict[str, float] = {
    "bad": 0.75,
    "normal": 1.00,
    "star": 1.25,
    "superstar": 1.50,
}

DEFAULT_RACE_WEIGHTS: Dict[str, float] = {race: 1.0 for race in RACES}
