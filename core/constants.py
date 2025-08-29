# core/constants.py
RACES = [
    "human","dwarf","goblin","orc","high_elf","sea_elf","dark_elf","wood_elf",
    "golem","dark_dwarf","dark_gnome","gnome","birdkin","lizardkin","catkin","bullkin",
]

# place-holder for race-specific adjustments (kept empty for now)
RACE_TRAITS = {
    # "human": {"str_mod": 0, "dex_mod": 0, ...}
}

DEV_TRAITS = {
    "bad": 0.75,
    "normal": 1.00,
    "star": 1.25,
    "superstar": 1.50,
}

# default per-team race weights (equal). A team can override by setting team["race_weights"].
DEFAULT_RACE_WEIGHTS = {race: 1.0 for race in RACES}
