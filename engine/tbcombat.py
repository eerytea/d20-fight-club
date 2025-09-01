# engine/tbcombat.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import random

from core.xp import xp_for_kill, grant_xp
from core.tactics import choose_intent, get_team_tactics  # NEW: tactics integration

def _mod(val: int) -> int: return (int(val) - 10) // 2
def _alive(f) -> bool: return bool(getattr(f, "alive", True)) and int(getattr(f, "hp", 1)) > 0
def _pname(f) -> str: return getattr(f, "name", getattr(f, "id", "player"))
def _pid(f) -> str: return str(getattr(f, "pid", getattr(f, "id", getattr(f, "name", id(f)))))
def _prof_for_level(level: int) -> int:
    L = max(1, int(level)); return min(6, 2 + (L - 1) // 4)

def _roll_d20(rng: random.Random, adv_ctx: int = 0) -> Tuple[Tuple[int,int,int], int]:
    a = rng.randint(1, 20); b = rng.randint(1, 20)
    if   adv_ctx > 0: return (a, b, max(a, b)), max(a, b)
    elif adv_ctx < 0: return (a, b, min(a, b)), min(a, b)
    else:             return (a, b, a), a

class TBCombat:
    """
    Turn-based combat with:
    - INT-only detection/saves, Stalker/Crusader/Wizard features
    - Proportional XP on death (killer = top damager)
    - NEW: Tactics router fallback + Taunt action and forced targeting for 1 round
    """
    def __init__(self, team_a, team_b, actors: List[Any], width: int, height: int, *, seed: int = 1):
        self.team_a = team_a; self.team_b = team_b
        self.actors = actors[:]
        self.width = int(width); self.height = int(height)
        self.rng = random.Random(seed)
        self.turn_idx = 0
        self.winner: Optional[int] = None
        self.events: List[Dict[str, Any]] = []
        self.controllers: Dict[int, Any] = {}
        # Team tactics store (UI can set this on the env)
        self.team_tactics: Dict[int, Dict[str, Any]] = {}

    # ---- Equipment helpers ----
    def _equipped(self, f) -> Dict[str, Any]: return getattr(f, "equipped", {}) or {}
    def _inventory(self, f) -> Dict[str, Any]: return getattr(f, "inventory", {}) or {}
    def _equipped_main(self, f) -> Optional[Dict[str, Any]]:
        inv = self._inventory(f); weapons = inv.get("weapons", [])
        mid = self._equipped(f).get("main_hand_id")
        for w in weapons:
            if w.get("id") == mid: return w
        w = getattr(f, "weapon", None)
        return w if isinstance(w, dict) else None
    def _equipped_off(self, f) -> Optional[Dict[str, Any]]:
        inv = self._inventory(f); weapons = inv.get("weapons", [])
        oid = self._equipped(f).get("off_hand_id")
        for w in weapons:
            if w.get("id") == oid: return w
        return None
    def _has_shield_equipped(self, f) -> bool: return bool(self._equipped(f).get("shield_id"))
    def _weapon_profile_from_item(self, item: Optional[Dict[str, Any]]) -> Tuple[str, str, bool, int, bool, bool, str]:
        if not item: return ("1d4", "STR", False, 1, False, False, "")
        dice = str(item.get("dice", "1d4"))
        ability = str(item.get("ability", "STR")).upper()
        is_ranged = bool(item.get("ranged", False))
        reach = int(item.get("reach", 1))
        finesse = bool(item.get("finesse", False))
        versatile = bool(item.get("versatile", False))
        two_handed_dice = str(item.get("two_handed_dice", ""))
        return (dice, ability, is_ranged, reach, finesse, versatile, two_handed_dice)

    # ---- Distances, ranges ----
    def _dist(self, a, b) -> int:
        return abs(getattr(a, "tx", 0) - getattr(b, "tx", 0)) + abs(getattr(a, "ty", 0) - getattr(b, "ty", 0))
    def _dist_to_xy(self, a, xy: Tuple[int,int]) -> int:
        x, y = xy; return abs(getattr(a, "tx", 0) - x) + abs(getattr(a, "ty", 0) - y)
    def reach(self, f) -> int:
        main = self._equipped_main(f)
        dice, ability, is_ranged, reach, finesse, versatile, two_handed_dice = self._weapon_profile_from_item(main)
        r = reach
        off = self._equipped_off(f)
        if off:
            _, _, _, r2, *_ = self._weapon_profile_from_item(off)
            r = max(r, r2)
        cls = str(getattr(f, "class", "")).capitalize(); lvl = int(getattr(f, "level", 1))
        if cls == "Stalker" and lvl >= 18 and not (main and main.get("ranged")):
            r += 1
        return r
    def ranged_limits(self, f, item) -> Tuple[int, int]:
        if not item or not item.get("ranged"): return (1, 1)
        base = item.get("range", (8, 16))
        cls = str(getattr(f, "class", "")).capitalize(); lvl = int(getattr(f, "level", 1))
        if cls == "Stalker" and lvl >= 18: return (10**9, 10**9)
        return (int(base[0]), int(base[1]))

    # ---- Stealth / detection ----
    def _highest_enemy_passive_perception(self, f) -> int:
        enemies = [e for e in self.actors if _alive(e) and getattr(e, "team_id", -1) != getattr(f, "team_id", -2)]
        if not enemies: return 10
        return max(10 + _mod(getattr(e, "INT", getattr(e, "int", 10))) for e in enemies)
    def _attempt_hide(self, player) -> Dict[str, Any]:
        raw, eff = _roll_d20(self.rng, 0)
        dex_mod = _mod(getattr(player, "DEX", 10))
        bonus10 = 10 if (str(getattr(player, "class","")).capitalize() == "Stalker" and int(getattr(player, "level",1)) >= 10) else 0
        stealth_total = eff + dex_mod + bonus10
        dc = self._highest_enemy_passive_perception(player)
        success = stealth_total >= dc
        setattr(player, "hidden", bool(success)); setattr(player, "_hide_roll", int(stealth_total if success else 0))
        return {"type": "hide_attempt", "player": _pname(player), "d20": eff, "dex_mod": dex_mod, "bonus10": bonus10, "stealth": stealth_total, "dc": dc, "success": success}
    def _start_of_turn_detect_hidden(self, detector):
        out = []
        for e in self.actors:
            if not _alive(e) or getattr(e, "team_id", -1) == getattr(detector, "team_id", -2) or not bool(getattr(e, "hidden", False)):
                continue
            raw, eff = _roll_d20(self.rng, 0)
            total = eff + _mod(getattr(detector, "INT", 10))
            thr = int(getattr(e, "_hide_roll", 0) or 0)
            success = (thr > 0) and (total >= thr)
            out.append({"type": "detect_hidden", "detector": _pname(detector), "target": _pname(e), "d20": eff, "int_mod": _mod(getattr(detector, "INT", 10)), "total": total, "threshold": thr, "success": success})
            if success:
                setattr(e, "hidden", False); setattr(e, "_hide_roll", 0)
        return out

    # ---- Crusader aura / saves ----
    def _crusader_int_aura_bonus(self, target) -> int:
        tid = getattr(target, "team_id", -1); best = 0
        for p in self.actors:
            if not _alive(p) or str(getattr(p, "class","")).capitalize() != "Crusader" or getattr(p, "team_id", -2) != tid: continue
            radius = int(getattr(p, "cru_aura_radius", 0))
            if radius and self._dist(p, target) <= radius:
                best = max(best, int(getattr(p, "cru_aura_int_bonus", 0)))
        return best
    def _crusader_no_fear_active(self, target) -> bool:
        tid = getattr(target, "team_id", -1)
        for p in self.actors:
            if not _alive(p) or str(getattr(p, "class","")).capitalize() != "Crusader" or getattr(p, "team_id", -2) != tid: continue
            if bool(getattr(p, "cru_aura_no_fear", False)) and self._dist(p, target) <= int(getattr(p, "cru_aura_radius", 0)):
                return True
        return False
    def _saving_throw(self, target, ability: str, dc: int, *, vs_condition: Optional[str] = None) -> bool:
        if vs_condition == "frightened" and self._crusader_no_fear_active(target):
            self.events.append({"type":"saving_throw","target":_pname(target),"ability":ability,"dc":dc,"auto":"crusader_no_fear"}); return True
        adv = 0
        if vs_condition in ("blinded", "deafened") and bool(getattr(target, "wiz_adv_vs_blind_deaf", False)):
            adv = 1
        _, eff = _roll_d20(self.rng, adv)
        total = eff + _mod(getattr(target, ability.upper(), 10))
        if ability.upper() == "INT":
            total += self._crusader_int_aura_bonus(target)
        self.events.append({"type":"saving_throw","target":_pname(target),"ability":ability,"d20":eff,"total":total,"dc":dc,"success":(total>=dc)})
        return total >= dc

    # ---- Damage, contributions, XP ----
    def _record_contribution(self, target, attacker, amount: int) -> None:
        if not attacker or amount <= 0: return
        m = getattr(target, "_dmg_from", None)
        if m is None: m = {}; setattr(target, "_dmg_from", m)
        k = _pid(attacker); m[k] = int(m.get(k, 0)) + int(amount)
    def _distribute_xp_for_death(self, target) -> None:
        contribs: Dict[str, int] = getattr(target, "_dmg_from", {}) or {}
        if not contribs: return
        total = sum(max(0, v) for v in contribs.values())
        if total <= 0: return
        by_id = {_pid(a): a for a in self.actors}
        killer_id = max(contribs.items(), key=lambda kv: kv[1])[0]
        victim_level = int(getattr(target, "level", 1))
        base_xp = xp_for_kill(victim_level)
        awarded_sum = 0; shares: Dict[str, int] = {}
        for cid, dmg in contribs.items():
            share = int(round(base_xp * (max(0, dmg) / float(total))))
            shares[cid] = share; awarded_sum += share
        if awarded_sum != base_xp:
            shares[killer_id] = shares.get(killer_id, 0) + (base_xp - awarded_sum)
        for cid, amt in shares.items():
            actor = by_id.get(cid); 
            if not actor: continue
            grant_xp(actor, amt, reason="kill", queue_levelups=True)
            if cid == killer_id: actor["kills"] = int(actor.get("kills", 0)) + 1
            else: actor["assists"] = int(actor.get("assists", 0)) + 1
        if hasattr(target, "_dmg_from"): delattr(target, "_dmg_from")
    def _apply_damage(self, target, amount: int, *, dtype: str = "physical", attacker=None) -> int:
        if dtype == "poison" and bool(getattr(target, "poison_immune", False)):
            self.events.append({"type":"damage_ignored","target":_pname(target),"dtype":"poison","amount":int(amount)}); return 0
        prev = int(getattr(target, "hp", 0)); new_hp = max(0, prev - int(amount))
        target.hp = new_hp; dealt = max(0, prev - new_hp)
        if dealt > 0 and attacker is not None: self._record_contribution(target, attacker, dealt)
        if prev > 0 and new_hp == 0:
            setattr(target, "alive", False); self._distribute_xp_for_death(target)
        return dealt

    # ---- Rolls and damage ----
    def _attack_roll(self, attacker, defender, *, item: Optional[Dict[str, Any]] = None,
                     adv_ctx: int = 0, is_ranged: bool = False, offhand: bool = False) -> Tuple[bool, bool, int]:
        raw, eff = _roll_d20(self.rng, max(-1, min(1, adv_ctx)))
        finesse = bool(item.get("finesse")) if item else False
        ability = "DEX" if (is_ranged or finesse) else (item.get("ability", "STR") if item else "STR")
        atk_mod = _mod(getattr(attacker, ability, 10))
        prof = _prof_for_level(getattr(attacker, "level", 1))
        prof_to_hit = prof
        if offhand:
            prof_to_hit = 0
            if getattr(attacker, "fighter_duelist_offhand_prof", False): prof_to_hit = prof
            if str(getattr(attacker, "class","")).capitalize() == "Stalker" and int(getattr(attacker, "level", 1)) >= 2: prof_to_hit = prof
        style_bonus = 0
        if is_ranged and int(getattr(attacker, "fighter_archery_bonus", 0)) > 0: style_bonus += 2
        if is_ranged and str(getattr(attacker, "class","")).capitalize() == "Stalker" and int(getattr(attacker, "level", 1)) >= 2: style_bonus += 2
        if str(getattr(attacker, "class","")).capitalize() == "Stalker" and int(getattr(attacker, "level", 1)) >= 20:
            style_bonus += _mod(getattr(attacker, "INT", 10))
        total = eff + atk_mod + prof_to_hit + style_bonus
        ac = int(getattr(defender, "ac", getattr(defender, "AC", 10)))
        hit = (total >= ac); crit = (eff == 20)
        self.events.append({"type": "attack_roll","attacker": _pname(attacker), "defender": _pname(defender),
                            "d20": eff, "ability_mod": atk_mod, "prof_to_hit": prof_to_hit, "style_bonus": style_bonus,
                            "total": total, "ac": ac, "hit": hit, "crit": crit})
        return hit, crit, eff
    def _is_two_handed_in_use(self, attacker, item: Dict[str, Any]) -> bool:
        if not item: return False
        if item.get("two_handed", False): return True
        if item.get("versatile", False) and (not self._has_shield_equipped(attacker)) and (self._equipped_off(attacker) is None):
            return True
        return False
    def _roll_damage_once(self, attacker, item: Dict[str, Any], *, is_ranged: bool, crit: bool, versatile_two_handed: bool) -> int:
        dice = str(item.get("dice", "1d6"))
        two_handed_dice = str(item.get("two_handed_dice", "")) if versatile_two_handed else ""
        if two_handed_dice: dice = two_handed_dice
        n, s = map(int, str(dice).lower().split("d"))
        dmg = sum(self.rng.randint(1, s) for _ in range(n))
        if crit: dmg += sum(self.rng.randint(1, s) for _ in range(n))
        finesse = bool(item.get("finesse")); ability = "DEX" if (is_ranged or finesse) else item.get("ability", "STR")
        dmg += _mod(getattr(attacker, ability, 10))
        dmg += _prof_for_level(getattr(attacker, "level", 1))
        return max(0, dmg)
    def _weapon_damage_roll(self, attacker, item: Dict[str, Any], *, is_ranged: bool, crit: bool) -> int:
        versatile_two_handed = self._is_two_handed_in_use(attacker, item)
        if str(getattr(attacker, "class","")).capitalize() == "Crusader" and int(getattr(attacker, "level", 1)) >= 2 and versatile_two_handed and not is_ranged:
            d1 = self._roll_damage_once(attacker, item, is_ranged=is_ranged, crit=crit, versatile_two_handed=True)
            d2 = self._roll_damage_once(attacker, item, is_ranged=is_ranged, crit=crit, versatile_two_handed=True)
            return max(d1, d2)
        return self._roll_damage_once(attacker, item, is_ranged=is_ranged, crit=crit, versatile_two_handed=versatile_two_handed)

    # ---- AOE ally exemptions (Wizard) ----
    def _apply_aoe_ally_exemptions(self, caster, candidates: List[Any], center_xy: Tuple[int,int]) -> List[Any]:
        L = int(getattr(caster, "level", 1))
        n_exempt = 1 if L >= 3 else 0
        if L >= 10: n_exempt = 2
        if L >= 17: n_exempt = 3
        allies = [a for a in candidates if getattr(a, "team_id", -1) == getattr(caster, "team_id", -2)]
        allies = sorted(allies, key=lambda a: self._dist_to_xy(a, center_xy))[:n_exempt]
        return [c for c in candidates if c not in allies]

    # ---- Taunt (new) ----
    def _attempt_taunt(self, taunter, target) -> Dict[str, Any]:
        # Contested roll: (d20 + CHA mod + prof) vs (d20 + INT mod (+ Crusader INT aura))
        (_, aroll), a_mod = _roll_d20(self.rng, 0)
        (_, droll), d_mod = _roll_d20(self.rng, 0)
        atk_total = a_mod + _mod(getattr(taunter, "CHA", 10)) + _prof_for_level(getattr(taunter, "level", 1))
        def_total = d_mod + _mod(getattr(target, "INT", 10)) + self._crusader_int_aura_bonus(target)
        success = (atk_total >= def_total)
        if success:
            target._taunted_by = _pid(taunter)
            target._taunt_rounds = 1  # lasts through their upcoming turn
        ev = {"type":"taunt", "taunter": _pname(taunter), "target": _pname(target),
              "atk_d20": a_mod, "def_d20": d_mod, "atk_total": atk_total, "def_total": def_total, "success": success}
        return ev

    # ---- Turn loop ----
    def _enemies_of(self, f): 
        tid = getattr(f, "team_id", -1); return [e for e in self.actors if getattr(e, "team_id", -2) != tid]

    def take_turn(self) -> None:
        if self.winner is not None: return
        if self.turn_idx >= len(self.actors): self.turn_idx = 0
        player = self.actors[self.turn_idx]
        if not _alive(player):
            self.turn_idx += 1; return

        # Forced targeting due to Taunt: mark the preferred target id if active
        forced_target_id = getattr(player, "_taunted_by", None)
        if forced_target_id is not None:
            # will be consumed this turn; decrement duration
            rounds = int(getattr(player, "_taunt_rounds", 0))
            if rounds <= 0:
                player._taunted_by = None
            else:
                player._taunt_rounds = rounds - 1

        # Detection step
        self.events.extend(self._start_of_turn_detect_hidden(player))

        intents: List[Dict[str, Any]] = []
        ctrl = self.controllers.get(getattr(player, "team_id", 0))
        if ctrl and hasattr(ctrl, "decide"):
            try:
                intents = ctrl.decide(self, player) or []
            except Exception:
                intents = []

        # If controller didn’t provide, ask tactics router
        if not intents:
            intents = choose_intent(self, player) or [{"type": "wait"}]

        # If taunted: rewrite any attack with missing/other target to the taunter when possible
        if forced_target_id is not None:
            taunter = next((a for a in self.actors if _pid(a) == forced_target_id and _alive(a)), None)
            if taunter:
                for it in intents:
                    if it.get("type") in ("attack", "cast") and "target" not in it:
                        it["target"] = taunter

        # Execute intents (subset supported)
        for intent in intents:
            itype = intent.get("type")

            if itype == "hide":
                self.events.append(self._attempt_hide(player))

            elif itype == "lay_on_hands" and str(getattr(player, "class","")).capitalize() == "Crusader":
                target = intent.get("target", player)
                amount = max(0, int(intent.get("amount", 0)))
                pool = int(getattr(player, "cru_lay_on_hands_current", 0))
                if amount <= 0 or pool <= 0:
                    self.events.append({"type":"loh","player":_pname(player),"target":_pname(target),"healed":0,"reason":"no_pool_or_zero_amount"})
                else:
                    heal = min(amount, pool)
                    target.hp = min(int(getattr(target, "max_hp", getattr(target, "hp", 1))), int(getattr(target, "hp", 0)) + heal)
                    player.cru_lay_on_hands_current = pool - heal
                    self.events.append({"type":"loh","player":_pname(player),"target":_pname(target),"healed":int(heal),"pool_left":int(player.cru_lay_on_hands_current)})

            elif itype == "taunt":
                target = intent.get("target")
                if target and _alive(target):
                    self.events.append(self._attempt_taunt(player, target))

            elif itype == "attack":
                target = intent.get("target")
                if forced_target_id is not None:
                    # Force target to taunter if available
                    t2 = next((a for a in self.actors if _pid(a) == forced_target_id and _alive(a)), None)
                    if t2: target = t2
                if not target or not _alive(target): continue
                main = self._equipped_main(player)
                dice, ability, is_ranged, reach, finesse, versatile, two_handed_dice = self._weapon_profile_from_item(main)
                hit, crit, _ = self._attack_roll(player, target, item=main, adv_ctx=0, is_ranged=is_ranged, offhand=False)
                if hit:
                    dmg = self._weapon_damage_roll(player, main or {}, is_ranged=is_ranged, crit=crit)
                    if not is_ranged and str(getattr(player, "class","")).capitalize() == "Crusader":
                        chance = float(getattr(player, "cru_smite_chance", 0.0)); nd6 = int(getattr(player, "cru_smite_nd6", 0))
                        if nd6 > 0 and self.rng.random() < chance:
                            extra = sum(self.rng.randint(1, 6) for _ in range(nd6))
                            dmg += extra; self.events.append({"type":"cru_smite","attacker":_pname(player),"defender":_pname(target),"nd6":nd6,"extra":int(extra),"chance":chance})
                    dealt = self._apply_damage(target, dmg, dtype="physical", attacker=player)
                    self.events.append({"type":"damage","attacker":_pname(player),"defender":_pname(target),"amount":int(dealt),"crit":bool(crit)})
                    # Crusader extra attack @5
                    if str(getattr(player, "class","")).capitalize() == "Crusader" and int(getattr(player, "level", 1)) >= 5 and _alive(target):
                        hit2, crit2, _ = self._attack_roll(player, target, item=main, adv_ctx=0, is_ranged=is_ranged, offhand=False)
                        if hit2:
                            dmg2 = self._weapon_damage_roll(player, main or {}, is_ranged=is_ranged, crit=crit2)
                            if not is_ranged:
                                chance = float(getattr(player, "cru_smite_chance", 0.0)); nd6 = int(getattr(player, "cru_smite_nd6", 0))
                                if nd6 > 0 and self.rng.random() < chance:
                                    extra2 = sum(self.rng.randint(1, 6) for _ in range(nd6))
                                    dmg2 += extra2; self.events.append({"type":"cru_smite","attacker":_pname(player),"defender":_pname(target),"nd6":nd6,"extra":int(extra2),"chance":chance})
                            dealt2 = self._apply_damage(target, dmg2, dtype="physical", attacker=player)
                            self.events.append({"type":"damage","attacker":_pname(player),"defender":_pname(target),"amount":int(dealt2),"crit":bool(crit2),"extra_attack":True})

            elif itype == "cast":
                spell = intent.get("spell", {}); target = intent.get("target")
                name = spell.get("name", "Spell"); level = int(spell.get("level", 0))
                # spend slot if any
                if level >= 1:
                    slots = getattr(player, "spell_slots_current", None)
                    if slots is not None and len(slots) > level and slots[level] > 0:
                        slots[level] -= 1
                if spell.get("attack_roll", False) and target:
                    hit, crit, _ = self._attack_roll(player, target, item=None, adv_ctx=0, is_ranged=True, offhand=False)
                    if hit and _alive(target):
                        tier = int(getattr(player, "wiz_cantrip_tier", 1))
                        dmg = self.rng.randint(1, 10) * tier
                        dealt = self._apply_damage(target, dmg, dtype=spell.get("dtype", "fire"), attacker=player)
                        self.events.append({"type":"spell_hit","name":name,"attacker":_pname(player),"defender":_pname(target),"dmg":int(dealt),"tier":tier})
                elif spell.get("center"):
                    cx, cy = spell["center"]; candidates = [t for t in self.actors if _alive(t)]
                    targets = self._apply_aoe_ally_exemptions(player, candidates, (cx, cy))
                    dc = int(spell.get("dc_override", getattr(player, "spell_save_dc", 10)))
                    for t in targets:
                        if getattr(t, "team_id", -1) == getattr(player, "team_id", -2): continue
                        saved = self._saving_throw(t, "DEX", dc, vs_condition=None)
                        dmg = self.rng.randint(1, 6) * (2 if level >= 3 else 1)
                        if saved: dmg //= 2
                        dealt = self._apply_damage(t, dmg, dtype=spell.get("dtype", "fire"), attacker=player)
                        self.events.append({"type":"spell_aoe","name":name,"attacker":_pname(player),"defender":_pname(t),"dmg":int(dealt),"saved":bool(saved)})
                else:
                    if target:
                        dc = int(spell.get("dc_override", getattr(player, "spell_save_dc", 10)))
                        saved = self._saving_throw(target, "INT", dc, vs_condition=spell.get("vs_condition"))
                        if not saved:
                            setattr(target, "_controlled", True)
                            self.events.append({"type":"spell_control","name":name,"attacker":_pname(player),"defender":_pname(target),"applied":True})
            else:
                pass

        self.turn_idx = (self.turn_idx + 1) % len(self.actors)
