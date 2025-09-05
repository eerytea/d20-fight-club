# AUTO-GENERATED from artifacts/spells_normalized.json
from __future__ import annotations
SLOT_CAPS = {
  "Druid": {
    "0": 3,
    "1": 4,
    "2": 5,
    "3": 4,
    "4": 5,
    "5": 4,
    "6": 2,
    "7": 2,
    "8": 3,
    "9": 1
  },
  "Skald": {
    "0": 2,
    "1": 7,
    "2": 6,
    "3": 3,
    "4": 1,
    "5": 4,
    "6": 2,
    "7": 2,
    "8": 1,
    "9": 1
  },
  "War Priest": {
    "0": 2,
    "1": 7,
    "2": 6,
    "3": 5,
    "4": 4,
    "5": 7,
    "6": 2,
    "7": 3,
    "8": 1,
    "9": 1
  },
  "Wizard": {
    "0": 5,
    "1": 4,
    "2": 5,
    "3": 10,
    "4": 8,
    "5": 4,
    "6": 6,
    "7": 4,
    "8": 3,
    "9": 2
  }
}

SPELLS = [
  {
    "spell": "Saving Grace",
    "class": "Druid",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Buff",
    "die": "1d4",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "This gives the target an extra 1d4 for the next 3 attacks",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Saving Grace",
    "class": "War Priest",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Buff",
    "die": "1d4",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "This gives the target an extra 1d4 for the next 3 attacks",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Poison Bolt",
    "class": "Druid",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Ranged",
    "die": "1d12, 5th level (2d12), 11th level (3d12), and 17th level (4d12)",
    "damage_type": "Poison",
    "has_save": true,
    "save_attr": "CON SAVING THROW, ON PASS NO DAMAGE",
    "save_success_multiplier": 0.0,
    "range_tiles": 2.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Flame Trap",
    "class": "Druid",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Ranged",
    "die": "1d8, 5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "RANGED SPELL ATTACK",
    "save_success_multiplier": 0.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Death Bolt",
    "class": "Wizard",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Ranged",
    "die": "1d10, 5th level (2d10), 11th level (3d10), and 17th level (4d10)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "RANGED SPELL ATTACK",
    "save_success_multiplier": 0.0,
    "range_tiles": 24.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Frost Bolt",
    "class": "Wizard",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Ranged",
    "die": "1d8, 5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "RANGED SPELL ATTACK",
    "save_success_multiplier": 0.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Poison Splash",
    "class": "Wizard",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "AOE",
    "die": "1d6, 5th level (2d6), 11th level (3d6), and 17th level (4d6)",
    "damage_type": "Poison",
    "has_save": true,
    "save_attr": "DEX SAVE",
    "save_success_multiplier": 0.0,
    "range_tiles": 12.0,
    "aoe_shape": "Can hit any two",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Accuracy",
    "class": "Wizard",
    "learn_at_level": 4,
    "slot_type": 0,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Gives an ally advantage on next attack roll",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Accuracy",
    "class": "Skald",
    "learn_at_level": 4,
    "slot_type": 0,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Gives an ally advantage on next attack roll",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Shock Hold",
    "class": "Wizard",
    "learn_at_level": 10,
    "slot_type": 0,
    "tags": "Melee",
    "die": "1d8, 5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "MELEE SPELL ATTACK",
    "save_success_multiplier": 0.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Holy Bolt",
    "class": "War Priest",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Ranged",
    "die": "1d8, 5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Holy",
    "has_save": true,
    "save_attr": "RANGED SPELL ATTACK",
    "save_success_multiplier": 0.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Scream",
    "class": "Skald",
    "learn_at_level": 1,
    "slot_type": 0,
    "tags": "Ranged",
    "die": "1d4, 5th level (2d4), 11th level (3d4), and 17th level (4d4)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "RANGED SPELL ATTACK",
    "save_success_multiplier": 0.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Charm",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 1,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT THROW, PASS NOTHING",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Charms opponent for 3 turns, each turn int saves, pass no longer charmed",
    "conditions": [
      "charmed"
    ],
    "training_pairs": [
      {
        "position": "Default",
        "role": "Bard"
      },
      {
        "position": "",
        "role": "Druid"
      },
      {
        "position": "",
        "role": "Wizard"
      }
    ]
  },
  {
    "spell": "Charm",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 1,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT THROW, PASS NOTHING",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Charms opponent for 3 turns, each turn int saves, pass no longer charmed",
    "conditions": [
      "charmed"
    ],
    "training_pairs": [
      {
        "position": "Default",
        "role": "Bard"
      },
      {
        "position": "",
        "role": "Druid"
      },
      {
        "position": "",
        "role": "Wizard"
      }
    ]
  },
  {
    "spell": "Charm",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 1,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT THROW, PASS NOTHING",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Charms opponent for 3 turns, each turn int saves, pass no longer charmed",
    "conditions": [
      "charmed"
    ],
    "training_pairs": [
      {
        "position": "Default",
        "role": "Bard"
      },
      {
        "position": "",
        "role": "Druid"
      },
      {
        "position": "",
        "role": "Wizard"
      }
    ]
  },
  {
    "spell": "Electric Blast",
    "class": "Skald",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "AOE",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "CON SAVING THROW, ON PASS HALF DAMAGE",
    "save_success_multiplier": 0.5,
    "range_tiles": 3.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 3 by 3 square with character in the center",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Bard",
        "role": "DPS: Bombarder"
      },
      {
        "position": "Wizard",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Electric Blast",
    "class": "Druid",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "AOE",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "CON SAVING THROW, ON PASS HALF DAMAGE",
    "save_success_multiplier": 0.5,
    "range_tiles": 3.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 3 by 3 square with character in the center",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Bard",
        "role": "DPS: Bombarder"
      },
      {
        "position": "Wizard",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Electric Blast",
    "class": "Wizard",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "AOE",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "CON SAVING THROW, ON PASS HALF DAMAGE",
    "save_success_multiplier": 0.5,
    "range_tiles": 3.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 3 by 3 square with character in the center",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Bard",
        "role": "DPS: Bombarder"
      },
      {
        "position": "Wizard",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Knock Down",
    "class": "Skald",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT THROW, PASS NOTHING",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Paralyzed each turn int saves, pass no longer Paralyzed",
    "conditions": [
      "paralyzed"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Knock Down",
    "class": "War Priest",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT THROW, PASS NOTHING",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Paralyzed each turn int saves, pass no longer Paralyzed",
    "conditions": [
      "paralyzed"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Inaccurate",
    "class": "Skald",
    "learn_at_level": 3,
    "slot_type": 1,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CHA THROW, PASS NOTHING",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Can attack three creatures in range and cause a negative 1d4 for there next attack rolls",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Healing Bolt",
    "class": "Skald",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Healing",
    "die": "1d4, 5th level (2d4), 11th level (3d4), and 17th level (4d4)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Default",
        "role": "Bard"
      },
      {
        "position": "",
        "role": "Cleric"
      },
      {
        "position": "",
        "role": "Wizard"
      },
      {
        "position": "Support",
        "role": "Healer: Bard"
      }
    ]
  },
  {
    "spell": "Healing Bolt",
    "class": "War Priest",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Healing",
    "die": "1d4, 5th level (2d4), 11th level (3d4), and 17th level (4d4)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Default",
        "role": "Bard"
      },
      {
        "position": "",
        "role": "Cleric"
      },
      {
        "position": "",
        "role": "Wizard"
      },
      {
        "position": "Support",
        "role": "Healer: Bard"
      }
    ]
  },
  {
    "spell": "Healing Bolt",
    "class": "Druid",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Healing",
    "die": "1d4, 5th level (2d4), 11th level (3d4), and 17th level (4d4)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Default",
        "role": "Bard"
      },
      {
        "position": "",
        "role": "Cleric"
      },
      {
        "position": "",
        "role": "Wizard"
      },
      {
        "position": "Support",
        "role": "Healer: Bard"
      }
    ]
  },
  {
    "spell": "Healing Bolt",
    "class": "Wizard",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Healing",
    "die": "1d4, 5th level (2d4), 11th level (3d4), and 17th level (4d4)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Default",
        "role": "Bard"
      },
      {
        "position": "",
        "role": "Cleric"
      },
      {
        "position": "",
        "role": "Wizard"
      },
      {
        "position": "Support",
        "role": "Healer: Bard"
      }
    ]
  },
  {
    "spell": "Healing Touch",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 1,
    "tags": "Healing",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healer"
      },
      {
        "position": "Default",
        "role": "Wizard"
      }
    ]
  },
  {
    "spell": "Healing Touch",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 1,
    "tags": "Healing",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healer"
      },
      {
        "position": "Default",
        "role": "Wizard"
      }
    ]
  },
  {
    "spell": "Healing Touch",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 1,
    "tags": "Healing",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healer"
      },
      {
        "position": "Default",
        "role": "Wizard"
      }
    ]
  },
  {
    "spell": "Healing Touch",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 1,
    "tags": "Healing",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healer"
      },
      {
        "position": "Default",
        "role": "Wizard"
      }
    ]
  },
  {
    "spell": "Bravery",
    "class": "Skald",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Makes an ally immune to frightened for 3 turns",
    "conditions": [
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Holy Blast",
    "class": "War Priest",
    "learn_at_level": 1,
    "slot_type": 1,
    "tags": "Ranged",
    "die": "4d6, 5th level (5d6), 11th level (6d6), and 17th level (5d6)",
    "damage_type": "Holy",
    "has_save": true,
    "save_attr": "RANGED SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "",
        "role": "Default"
      }
    ]
  },
  {
    "spell": "Grace Bolt",
    "class": "War Priest",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Buff",
    "die": "1d4",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "This gives the target an extra 1d4 for the next 3 attacks",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Shield of God",
    "class": "War Priest",
    "learn_at_level": 3,
    "slot_type": 1,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "This gives the target plus 2 AC for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Inflict Wounds",
    "class": "War Priest",
    "learn_at_level": 2,
    "slot_type": 1,
    "tags": "Melee",
    "die": "3d10, 5th level (4d10), 11th level (5d10), and 17th level (6d10)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "SPELL ATTACK TO HIT",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Blind",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CON SAVING THROUGH",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Target is blinded for 3 turns, makes int checks every turn to end early",
    "conditions": [
      "blinded"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Blind",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CON SAVING THROUGH",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Target is blinded for 3 turns, makes int checks every turn to end early",
    "conditions": [
      "blinded"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Blind",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CON SAVING THROUGH",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Target is blinded for 3 turns, makes int checks every turn to end early",
    "conditions": [
      "blinded"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Calm",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Removes charm and frightened",
    "conditions": [
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Calm",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Removes charm and frightened",
    "conditions": [
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Enhance Ability",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Has advantage on saving throws for 1 turn and heals 2d6",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      },
      {
        "position": "",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Enhance Ability",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Has advantage on saving throws for 1 turn and heals 2d6",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      },
      {
        "position": "",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Enhance Ability",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Has advantage on saving throws for 1 turn and heals 2d6",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      },
      {
        "position": "",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Heat",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Melee",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "SPELL ATTACK TO HIT",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Lesser Restoration",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff/Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cures any ailment",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      },
      {
        "position": "",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Lesser Restoration",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff/Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cures any ailment",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      },
      {
        "position": "",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Lesser Restoration",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff/Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cures any ailment",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      },
      {
        "position": "",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Thunder",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "AOE",
    "die": "3d8, 5th level (4d8), 11th level (5d8), and 17th level (6d8)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "CON SAVE THROW, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "2 by 2 square",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Bombarder"
      }
    ]
  },
  {
    "spell": "Thunder",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "AOE",
    "die": "3d8, 5th level (4d8), 11th level (5d8), and 17th level (6d8)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "CON SAVE THROW, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "2 by 2 square",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Bombarder"
      }
    ]
  },
  {
    "spell": "Prayer",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Healing",
    "die": "2d8, 5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Cures 6 allys",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healer"
      }
    ]
  },
  {
    "spell": "Blast",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Ranged",
    "die": "1d8, 5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "RANGED SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Barkskin",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "NA",
    "conditions_text": "Increases AC to 16 (normally 8/10/12 + con make it 16) for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Flame Strike",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Melee",
    "die": "3d6, 5th level (4d6), 11th level (5d6), and 17th level (6d6)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Moonbeam",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Ranged",
    "die": "2d10, 5th level (3d10), 11th level (4d10), and 17th level (5d10)",
    "damage_type": "Holy",
    "has_save": true,
    "save_attr": "SPELL ATTAACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Piercing Poison",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Ranged",
    "die": "4d4, 5th level (5d4), 11th level (6d4), and 17th level (7d4)",
    "damage_type": "Poison",
    "has_save": true,
    "save_attr": "SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 15.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Weakening Ray",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Makes the enemy do half damage for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "debuff"
      }
    ]
  },
  {
    "spell": "Fire Blast",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 2,
    "tags": "Ranged",
    "die": "2d6, 5th level (3d6), 11th level (4d6), and 17th level (5d6)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Curse",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVING",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Disadvantage on all rolls for 3 turns, roll saving throw each turn, if fail turn is skipped",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Curse",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVING",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Disadvantage on all rolls for 3 turns, roll saving throw each turn, if fail turn is skipped",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Curse",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVING",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Disadvantage on all rolls for 3 turns, roll saving throw each turn, if fail turn is skipped",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Fear",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff/AOE",
    "die": "",
    "damage_type": "NA",
    "has_save": true,
    "save_attr": "INT SAVING",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "Cone coming from character",
    "conditions_text": "Fightened for three turns, takes saving throws each turn to lower duration",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      },
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Fear",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff/AOE",
    "die": "",
    "damage_type": "NA",
    "has_save": true,
    "save_attr": "INT SAVING",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "Cone coming from character",
    "conditions_text": "Fightened for three turns, takes saving throws each turn to lower duration",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      },
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Mass Charm",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff/AOE",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Square",
    "conditions_text": "Charmed opponent, Saving throw to lower duration",
    "conditions": [
      "charmed"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      },
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Mass Charm",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff/AOE",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Square",
    "conditions_text": "Charmed opponent, Saving throw to lower duration",
    "conditions": [
      "charmed"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      },
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Hope",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Can target all allys in range, Advantage on Int saves for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Mass Healing Bolt",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Heals all allys in range 1d4 plus spell modifyer",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Spirt Blast",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "AOE",
    "die": "5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Radient",
    "has_save": true,
    "save_attr": "INT SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "Square",
    "conditions_text": "Attacks all people in the 8 squares surrounding the character",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "DPS",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Elamental Protection",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Gives resistance to Poison, Fire, Electric and Cold",
    "conditions": [
      "poisoned"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Elamental Protection",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Gives resistance to Poison, Fire, Electric and Cold",
    "conditions": [
      "poisoned"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Elamental Protection",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Gives resistance to Poison, Fire, Electric and Cold",
    "conditions": [
      "poisoned"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Lightning",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Ranged",
    "die": "5th level (1d10), 11th level (2d10), and 17th level (3d10)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 4 by 3 square of damage",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Lightning",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Ranged",
    "die": "5th level (1d10), 11th level (2d10), and 17th level (3d10)",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 4 by 3 square of damage",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Ice",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "AOE",
    "die": "5th level (1d10), 11th level (2d10), and 17th level (3d10)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 2 by 4",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Ice",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "AOE",
    "die": "5th level (1d10), 11th level (2d10), and 17th level (3d10)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 2 by 4",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Wind",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "AOE",
    "die": "5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Line",
    "conditions_text": "Create a 1 x 10 line that does damage",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Fireball",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "AOE",
    "die": "5th level (8d6), 11th level  (9d6), and 17th level (10d6)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 10.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 2 by 4",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Fast",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Adds 2 AC, moves adds 5 to initive",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Slow",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "DEX SAVE, NONE ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 25.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 4 by 3 square, lowers AC by 2, lowers initive by 5",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Death Touch",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 3,
    "tags": "Melee",
    "die": "5th level (3d6), 11th level (4d6), and 17th level (5d6)",
    "damage_type": "",
    "has_save": true,
    "save_attr": "SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Mass Frighten",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Gives frightened to all enemies in range",
    "conditions": [
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Mass Frighten",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Gives frightened to all enemies in range",
    "conditions": [
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Mass Frighten",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Gives frightened to all enemies in range",
    "conditions": [
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Paralyze",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CHA SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Paralyzed each turn int saves, pass no longer Paralyzed",
    "conditions": [
      "paralyzed"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Paralyze",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CHA SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Paralyzed each turn int saves, pass no longer Paralyzed",
    "conditions": [
      "paralyzed"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Death Ward",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "First time this character gets knocked down to 0, it stays at one instead. Can only been done once per combat",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Water Blast",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Ranged",
    "die": "5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "STRENGTH SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Water Blast",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Ranged",
    "die": "5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "STRENGTH SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Water Blast",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Ranged",
    "die": "5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "STRENGTH SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Guardian",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Buff",
    "die": "",
    "damage_type": "Radient",
    "has_save": true,
    "save_attr": "DEX SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "Cast on character, for three attacks anyone attacking within a distance of 1 away takes 20 damage",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Greater Ice",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "AOE",
    "die": "5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 60.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 4 x 5 Square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Greater Ice",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "AOE",
    "die": "5th level (2d8), 11th level (3d8), and 17th level (4d8)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 60.0,
    "aoe_shape": "Square",
    "conditions_text": "Creates a 4 x 5 Square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Stone Skin",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Target takes half damage for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Stone Skin",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Target takes half damage for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Fire Wall",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "AOE",
    "die": "5th level (5d8), 11th level (6d8), and 17th level (7d8)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Line",
    "conditions_text": "Makes a 1 x 12 line",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Fire Wall",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "AOE",
    "die": "5th level (5d8), 11th level (6d8), and 17th level (7d8)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX SAVE, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Line",
    "conditions_text": "Makes a 1 x 12 line",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Death Blast",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Ranged",
    "die": "5th level (8d8), 11th level  (9d8), and 17th level (10d8)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "CON SAVE THROW, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 6.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Elecmental Shield",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 4,
    "tags": "Buff",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "Immune to fire and cold for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      }
    ]
  },
  {
    "spell": "Burning Love",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff/Ranged",
    "die": "5th level (5d10), 11th level (6d10), and 17th level (7d10)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "INT SAVING THROW",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "If hits also charms",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "debuff DPS: ranged"
      }
    ]
  },
  {
    "spell": "Burning Love",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff/Ranged",
    "die": "5th level (5d10), 11th level (6d10), and 17th level (7d10)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "INT SAVING THROW",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "If hits also charms",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "debuff DPS: ranged"
      }
    ]
  },
  {
    "spell": "Burning Love",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff/Ranged",
    "die": "5th level (5d10), 11th level (6d10), and 17th level (7d10)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "INT SAVING THROW",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "If hits also charms",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "debuff DPS: ranged"
      }
    ]
  },
  {
    "spell": "Burning Love",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff/Ranged",
    "die": "5th level (5d10), 11th level (6d10), and 17th level (7d10)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "INT SAVING THROW",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "If hits also charms",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "debuff DPS: ranged"
      }
    ]
  },
  {
    "spell": "Dominate",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVING THROW",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Charms and paralyzes",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "debuff"
      }
    ]
  },
  {
    "spell": "Restore",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cures any debuff",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "healing"
      }
    ]
  },
  {
    "spell": "Restore",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cures any debuff",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "healing"
      }
    ]
  },
  {
    "spell": "Restore",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cures any debuff",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "healing"
      }
    ]
  },
  {
    "spell": "Healing Blast",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Healing",
    "die": "5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 60.0,
    "aoe_shape": "Square",
    "conditions_text": "Makes a 6 x 10 Square of healing",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healing"
      },
      {
        "position": "Support",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Healing Blast",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Healing",
    "die": "5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 60.0,
    "aoe_shape": "Square",
    "conditions_text": "Makes a 6 x 10 Square of healing",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healing"
      },
      {
        "position": "Support",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Healing Blast",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Healing",
    "die": "5th level (3d8), 11th level (4d8), and 17th level (5d8)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 60.0,
    "aoe_shape": "Square",
    "conditions_text": "Makes a 6 x 10 Square of healing",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healing"
      },
      {
        "position": "Support",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Disease",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CON SAV",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Disadvantage on all rolls for 3 turns, roll saving throw each turn, if fail turn is skipped, also poisons",
    "conditions": [
      "poisoned"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Disease",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CON SAV",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Disadvantage on all rolls for 3 turns, roll saving throw each turn, if fail turn is skipped, also poisons",
    "conditions": [
      "poisoned"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Disease",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CON SAV",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Disadvantage on all rolls for 3 turns, roll saving throw each turn, if fail turn is skipped, also poisons",
    "conditions": [
      "poisoned"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Godstrike",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "AOE",
    "die": "8d6, 11th level 9d6, 17 level 10d6",
    "damage_type": "Radient",
    "has_save": true,
    "save_attr": "DEX SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "Rectangele",
    "conditions_text": "1 x 2 square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Hallow",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "Buff/Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "Rectangale",
    "conditions_text": "6 x 10 square around where touched, Cures frightened, charmed and makes resitant to those conditions for 3 turns",
    "conditions": [
      "charmed",
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Buff"
      },
      {
        "position": "",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Concussive Blast",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "AOE/Ranged",
    "die": "5th level (4d10), 11th level (5d10), and 17th level (6d10)",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "CON SAVE THROW, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 60.0,
    "aoe_shape": "Square",
    "conditions_text": "4 x 5 square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Poison Cloud",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "AOE",
    "die": "5th level (5d8), 11th level (6d8), and 17th level (7d8)",
    "damage_type": "Poison",
    "has_save": true,
    "save_attr": "CON SVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Square",
    "conditions_text": "4 x 5 square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Cold Blast",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 5,
    "tags": "AOE",
    "die": "5th level (8d8), 11th level  (9d8), and 17th level (10d8)",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "CON SAVE THROW, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "Cone coming from character",
    "conditions_text": "12 squares total",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Mass Charm",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Picks any target within range and charms on fail",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Greater Fear",
    "class": "Skald",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "INT SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "One target, makes character frightened and blind",
    "conditions": [
      "frightened"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Harm",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Melee",
    "die": "14d6, 17th level (15d6)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cannot reduce an enemy to zero hitpoints",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Harm",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Melee",
    "die": "14d6, 17th level (15d6)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "Cannot reduce an enemy to zero hitpoints",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Heal",
    "class": "War Priest",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Healing",
    "die": "70 HP",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Pick any ally within range, they are cured of all ailments and healed for 70 HP",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Supper",
        "role": "healing"
      }
    ]
  },
  {
    "spell": "Heal",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Healing",
    "die": "70 HP",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Pick any ally within range, they are cured of all ailments and healed for 70 HP",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Supper",
        "role": "healing"
      }
    ]
  },
  {
    "spell": "Heal",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Healing",
    "die": "70 HP",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Pick any ally within range, they are cured of all ailments and healed for 70 HP",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Supper",
        "role": "healing"
      }
    ]
  },
  {
    "spell": "Radient Beam",
    "class": "Druid",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Ranged",
    "die": "11th level (6d8), and 17th level (7d8)",
    "damage_type": "Radient",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "Line",
    "conditions_text": "From caster goes 12 squares in a line",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Rush"
      },
      {
        "position": "",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Radient Beam",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Ranged",
    "die": "11th level (6d8), and 17th level (7d8)",
    "damage_type": "Radient",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "Line",
    "conditions_text": "From caster goes 12 squares in a line",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Rush"
      },
      {
        "position": "",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Lightning Blast",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Ranged",
    "die": "10d8, 17th level 11d8",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "Can choose 3 people within 6 squares from first target, but not AOE",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      },
      {
        "position": "",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Ice Beam",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Ranged",
    "die": "10d6, 17th level 11d8",
    "damage_type": "Cold",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": 24.0,
    "aoe_shape": "Line",
    "conditions_text": "Shoot beam from caster in a line",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      },
      {
        "position": "",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Destroy",
    "class": "Wizard",
    "learn_at_level": 0,
    "slot_type": 6,
    "tags": "Ranged",
    "die": "10d6 + 40, 17th level 11d8 + 40",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Targets one character",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Cage",
    "class": "Skald",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CHA",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "Paralyzes one target",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Cage",
    "class": "Wizard",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "Debuff",
    "die": "",
    "damage_type": "",
    "has_save": true,
    "save_attr": "CHA",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "Paralyzes one target",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Focused Blast",
    "class": "Skald",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "Ranged",
    "die": "3d10, 17 level 4d10",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "SPELL ATTACK",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Targets one character",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Divine Intervention",
    "class": "War Priest",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "Ranged/ Debuff",
    "die": "",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "CHA",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "If target has less then 20 HP or less it dies, if target has 30 HP or less it is blinded paralyzed, if it has 40 HP or less it is blinded",
    "conditions": [
      "blinded",
      "paralyzed"
    ],
    "training_pairs": [
      {
        "position": "Support",
        "role": "debuff"
      }
    ]
  },
  {
    "spell": "Fire Rain",
    "class": "War Priest",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "AOE",
    "die": "7d10, 17 8d10",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "Create Square 2 x 1",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Fire Rain",
    "class": "Druid",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "AOE",
    "die": "7d10, 17 8d10",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "Create Square 2 x 1",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Regenerate",
    "class": "War Priest",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "Healing",
    "die": "4d8 (+15), 17 5d8 (+15)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Regenerate",
    "class": "Druid",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "Healing",
    "die": "4d8 (+15), 17 5d8 (+15)",
    "damage_type": "Healing",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 1.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Blast",
    "class": "Wizard",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "AOE",
    "die": "12d6, 17th level 13d6",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "Makes square 4 x 5",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Death Burst",
    "class": "Wizard",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "Ranged",
    "die": "7d8 +30, 17th level 8d8 +30",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Fire Cone",
    "class": "Wizard",
    "learn_at_level": 13,
    "slot_type": 7,
    "tags": "AOE",
    "die": "9d8, and 17th level (10d8)",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "CON SAVE THROW, HALF ON SAVE",
    "save_success_multiplier": 0.5,
    "range_tiles": 1.0,
    "aoe_shape": "Cone coming from character",
    "conditions_text": "12 squares total",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      },
      {
        "position": "",
        "role": "Rush"
      }
    ]
  },
  {
    "spell": "Stupify",
    "class": "Skald",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "Debuff",
    "die": "4d6, 17th level (5d6)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "INT",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "Target can only move and perform melee attacks for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Stupify",
    "class": "Druid",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "Debuff",
    "die": "4d6, 17th level (5d6)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "INT",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "Target can only move and perform melee attacks for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Stupify",
    "class": "Wizard",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "Debuff",
    "die": "4d6, 17th level (5d6)",
    "damage_type": "Necrotic",
    "has_save": true,
    "save_attr": "INT",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "Target can only move and perform melee attacks for 3 turns",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Debuff"
      }
    ]
  },
  {
    "spell": "Quake",
    "class": "War Priest",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "AOE, Ranged",
    "die": "5d6, 17th level (6d6)",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "Hits all enemys",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      },
      {
        "position": "",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Quake",
    "class": "Druid",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "AOE, Ranged",
    "die": "5d6, 17th level (6d6)",
    "damage_type": "Treat the same as how we treat melee damage",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "Hits all enemys",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      },
      {
        "position": "",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Radient Burst",
    "class": "Druid",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "AOE",
    "die": "12d6, 17th level 13d6",
    "damage_type": "Radient",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "4 x 5 square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Radient Burst",
    "class": "Wizard",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "AOE",
    "die": "12d6, 17th level 13d6",
    "damage_type": "Radient",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "",
    "conditions_text": "4 x 5 square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Incinderating Blast",
    "class": "Wizard",
    "learn_at_level": 15,
    "slot_type": 8,
    "tags": "AOE",
    "die": "10d8, 17th level 11d8",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": 30.0,
    "aoe_shape": "Square",
    "conditions_text": "4 x 5 square",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Die",
    "class": "Skald",
    "learn_at_level": 17,
    "slot_type": 9,
    "tags": "Ranged",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Kills character under 100 HP",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Die",
    "class": "Wizard",
    "learn_at_level": 17,
    "slot_type": 9,
    "tags": "Ranged",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "Kills character under 100 HP",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "Ranged"
      }
    ]
  },
  {
    "spell": "Mass Heal",
    "class": "War Priest",
    "learn_at_level": 17,
    "slot_type": 9,
    "tags": "Healing",
    "die": "",
    "damage_type": "",
    "has_save": false,
    "save_attr": "",
    "save_success_multiplier": 1.0,
    "range_tiles": 12.0,
    "aoe_shape": "",
    "conditions_text": "From a bank of 700 HP, heals all allies in range",
    "conditions": [],
    "training_pairs": [
      {
        "position": "Support",
        "role": "Healing"
      }
    ]
  },
  {
    "spell": "Storm",
    "class": "Druid",
    "learn_at_level": 17,
    "slot_type": 9,
    "tags": "AOE",
    "die": "6d6",
    "damage_type": "Electric",
    "has_save": true,
    "save_attr": "CON",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "Hits all characters on the field minus self and all allies below 50% health",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  },
  {
    "spell": "Meteor",
    "class": "Wizard",
    "learn_at_level": 17,
    "slot_type": 9,
    "tags": "AOE",
    "die": "40d6",
    "damage_type": "Fire",
    "has_save": true,
    "save_attr": "DEX",
    "save_success_multiplier": 0.5,
    "range_tiles": NaN,
    "aoe_shape": "",
    "conditions_text": "Hits whole field",
    "conditions": [],
    "training_pairs": [
      {
        "position": "DPS",
        "role": "AOE"
      }
    ]
  }
]
