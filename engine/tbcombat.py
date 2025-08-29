# engine/tbcombat.py
# (unchanged imports and the whole file from your latest Patch F version...)
# Only _apply_damage is shown here for brevity in this snippet comment; full file follows.

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random

from engine.conditions import (
    CONDITION_PRONE, CONDITION_RESTRAINED, CONDITION_STUNNED,
    ensure_bag, has_condition, add_condition, clear_condition, decrement_all_for_turn
)
from engine.spells import line_aoe_cells

__all__ = ["TBCombat", "Team"]

# ... [everything above unchanged from the Patch F version I gave you] ...

    def _apply_damage(self, attacker, defender, dmg: int):
        # NEW: global outgoing bonus per level hook (e.g., Goblin)
        try:
            per_lvl = int(getattr(attacker, "dmg_bonus_per_level", 0))
            lvl = int(getattr(attacker, "level", getattr(attacker, "lvl", 1)))
            if per_lvl > 0 and lvl > 0:
                dmg = int(dmg) + per_lvl * lvl
        except Exception:
            pass

        try:
            defender.hp = int(defender.hp) - int(dmg)
        except Exception:
            pass
        self._push({"type": "damage", "actor": _name(attacker), "target": _name(defender), "amount": int(dmg)})

        # Concentration check hook (Patch E)
        if getattr(defender, "concentration", False):
            dc = max(10, int(dmg) // 2)
            res = self.saving_throw(defender, "CON", dc)
            if not res["success"]:
                try: setattr(defender, "concentration", False)
                except Exception: pass
                self._push({"type": "concentration_broken", "target": _name(defender)})

        if getattr(defender, "hp", 0) <= 0 and _alive(defender):
            try: setattr(defender, "alive", False)
            except Exception: pass
            self._push({"type": "down", "name": _name(defender)})

# ... [everything below unchanged from your Patch F file] ...
