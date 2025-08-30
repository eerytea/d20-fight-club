# engine/tbcombat.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import math
import random

# --------------------------------------------------------------------------------------
# Utility helpers
# --------------------------------------------------------------------------------------

def _mod(val: int) -> int:
    return (int(val) - 10) // 2

def _get(obj, key, default=None):
    return getattr(obj, key, getattr(obj, key.lower(), default)) if hasattr(obj, key) else getattr(obj, key.lower(), default) if hasattr(obj, key.lower()) else obj.get(key, default)

def _prof_for_level(level: int) -> int:
    L = max(1, int(level))
    return min(6, 2 + (L - 1) // 4)

def _alive(f) -> bool:
    return bool(getattr(f, "alive", True)) and int(getattr(f, "hp", 1)) > 0

def _name(f) -> str:
    return getattr(f, "name", getattr(f, "id", "??"))

def _roll_d20(rng: random.Random, adv_ctx: int = 0) -> Tuple[Tuple[int,int,int], int]:
    """
    adv_ctx: -1 = disadvantage, 0 = normal, +1 = advantage
    returns ((a,b,chosen), chosen)
    """
    a = rng.randint(1, 20)
    b = rng.randint(1, 20)
    if adv_ctx > 0:
        return (a, b, max(a, b)), max(a, b)
    if adv_ctx < 0:
        return (a, b, min(a, b)), min(a, b)
    return (a, b, a), a

# --------------------------------------------------------------------------------------
# TBCombat
# --------------------------------------------------------------------------------------

class TBCombat:
    def __init__(self, team_a, team_b, actors: List[Any], width: int, height: int, *, seed: int = 1):
        self.team_a = team_a
        self.team_b = team_b
        self.actors = actors[:]  # initiative list built elsewhere or here
        self.width = int(width); self.height = int(height)
        self.rng = random.Random(seed)
        self.turn_idx = 0
        self.winner: Optional[int] = None
        self.events: List[Dict[str, Any]] = []
        # You may have a different controller wiring—leaving that intact.
        self.controllers: Dict[int, Any] = {}

    # ---------------------- Identity helpers ----------------------
    def _is_class(self, f, cls_name: str) -> bool:
        return str(getattr(f, "class", getattr(f, "Class", ""))).capitalize() == cls_name

    def _is_ranger(self, f) -> bool: return self._is_class(f, "Ranger")
    def _is_rogue(self, f) -> bool:  return self._is_class(f, "Rogue")
    def _is_monk(self, f) -> bool:   return self._is_class(f, "Monk")
    def _is_wizard(self, f) -> bool: return self._is_class(f, "Wizard")

    # ---------------------- Equipment helpers (stubbed, keep your originals if you have them) ----------------------
    def _equipped_main(self, f) -> Optional[Dict[str, Any]]:
        inv = getattr(f, "inventory", {})
        weapons = inv.get("weapons", [])
        eq = getattr(f, "equipped", {})
        mid = eq.get("main_hand_id")
        for w in weapons:
            if w.get("id") == mid: return w
        # fallback to current f.weapon mirror
        w = getattr(f, "weapon", None)
        return w if isinstance(w, dict) else None

    def _equipped_off(self, f) -> Optional[Dict[str, Any]]:
        inv = getattr(f, "inventory", {})
        weapons = inv.get("weapons", [])
        eq = getattr(f, "equipped", {})
        oid = eq.get("off_hand_id")
        for w in weapons:
            if w.get("id") == oid: return w
        return None

    def _weapon_profile_from_item(self, f, item: Optional[Dict[str, Any]]) -> Tuple[str, str, bool, int, bool]:
        """
        returns: (dice, ability_stat, is_ranged, reach, finesse_flag)
        """
        if not item:
            return ("1d4", "STR", False, 1, False)
        dice = str(item.get("dice", "1d4"))
        ability = str(item.get("ability", "STR")).upper()
        is_ranged = bool(item.get("ranged", False))
        reach = int(item.get("reach", 1))
        finesse = bool(item.get("finesse", False))
        return (dice, ability, is_ranged, reach, finesse)

    def _parse_dice(self, dice: str) -> Tuple[int, int]:
        n, s = str(dice).lower().split("d")
        return int(n), int(s)

    # ---------------------- Range / reach ----------------------
    def reach(self, f) -> int:
        main = self._equipped_main(f)
        dice, ability, is_ranged, reach, finesse = self._weapon_profile_from_item(f, main)
        r = reach
        # consider off-hand reach, take max
        off = self._equipped_off(f)
        if off:
            _, _, _, r2, _ = self._weapon_profile_from_item(f, off)
            r = max(r, r2)
        # Ranger L18: +1 melee reach
        if self._is_ranger(f) and int(getattr(f, "level", 1)) >= 18:
            # Only applies to melee swings; leave ranged unchanged
            if not is_ranged:
                r += 1
        return r

    def ranged_limits(self, f, item) -> Tuple[int, int]:
        """
        Returns (normal_range, long_range) in tiles.
        Long-range disadvantage is not modeled here; but we still pass values.
        """
        if not item or not item.get("ranged"):
            return (1, 1)
        base = item.get("range", (8, 16))
        if self._is_ranger(f) and int(getattr(f, "level", 1)) >= 18:
            return (10**9, 10**9)  # Unlimited range
        return (int(base[0]), int(base[1]))

    # ---------------------- Hide & detection ----------------------
    def _highest_enemy_passive_perception(self, f) -> int:
        enemies = [e for e in self.actors if _alive(e) and getattr(e, "team_id", -1) != getattr(f, "team_id", -2)]
        if not enemies: return 10
        return max(10 + _mod(getattr(e, "WIS", 10)) for e in enemies)

    def _attempt_hide(self, actor) -> Dict[str, Any]:
        raw, eff = _roll_d20(self.rng, 0)
        dex_mod = _mod(getattr(actor, "DEX", 10))
        bonus10 = 10 if (self._is_ranger(actor) and int(getattr(actor, "level", 1)) >= 10) else 0
        stealth_total = eff + dex_mod + bonus10
        dc = self._highest_enemy_passive_perception(actor)
        success = stealth_total >= dc
        setattr(actor, "hidden", bool(success))
        setattr(actor, "_hide_roll", int(stealth_total if success else 0))
        return {"type": "hide_attempt", "actor": _name(actor), "d20": eff, "dex_mod": dex_mod,
                "bonus10": bonus10, "stealth": stealth_total, "dc": dc, "success": success}

    def _start_of_turn_detect_hidden(self, detector):
        out = []
        for e in self.actors:
            if not _alive(e): continue
            if getattr(e, "team_id", -1) == getattr(detector, "team_id", -2): continue
            if not bool(getattr(e, "hidden", False)): continue
            raw, eff = _roll_d20(self.rng, 0)
            total = eff + _mod(getattr(detector, "WIS", 10))
            thr = int(getattr(e, "_hide_roll", 0) or 0)
            success = (thr > 0) and (total >= thr)
            ev = {"type": "detect_hidden", "detector": _name(detector), "target": _name(e),
                  "d20": eff, "wis_mod": _mod(getattr(detector, "WIS", 10)),
                  "total": total, "threshold": thr, "success": success}
            out.append(ev)
            if success:
                setattr(e, "hidden", False)
                setattr(e, "_hide_roll", 0)
        return out

    # ---------------------- Core attack resolution ----------------------
    def _attack_roll(self, attacker, defender, *, item: Optional[Dict[str, Any]] = None,
                     adv_ctx: int = 0, is_ranged: bool = False, offhand: bool = False) -> Tuple[bool, bool, int]:
        # Rogue 18 could remove advantage against them—honor that if you model it; we cap within [-1, +1]
        raw, eff = _roll_d20(self.rng, max(-1, min(1, adv_ctx)))
        # ability mod: DEX for ranged or finesse; STR otherwise
        ability = "DEX" if (is_ranged or (item and item.get("finesse"))) else (item.get("ability", "STR") if item else "STR")
        atk_mod = _mod(getattr(attacker, ability, 10))
        # proficiency: offhand normally 0; some classes add it back (Duelist/Ranger L2)
        prof = _prof_for_level(getattr(attacker, "level", 1))
        prof_to_hit = prof
        if offhand:
            prof_to_hit = 0
            # Fighter Duelist or Ranger (L2+) adds prof back to off-hand to-hit
            if getattr(attacker, "fighter_duelist_offhand_prof", False):
                prof_to_hit = prof
            if self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 2:
                prof_to_hit = prof
        # styles & class bonuses
        style_bonus = 0
        if is_ranged and int(getattr(attacker, "fighter_archery_bonus", 0)) > 0:
            style_bonus += 2
        if is_ranged and self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 2:
            style_bonus += 2  # Ranger +2 ranged to-hit
        if self._is_ranger(attacker) and int(getattr(attacker, "level", 1)) >= 20:
            style_bonus += _mod(getattr(attacker, "WIS", 10))  # add WIS to attack rolls

        total = eff + atk_mod + prof_to_hit + style_bonus
        ac = int(getattr(defender, "ac", getattr(defender, "AC", 10)))
        hit = (total >= ac)
        crit = (eff == 20)
        self.events.append({
            "type": "attack_roll",
            "attacker": _name(attacker),
            "defender": _name(defender),
            "d20": eff,
            "ability_mod": atk_mod,
            "prof_to_hit": prof_to_hit,
            "style_bonus": style_bonus,
            "total": total,
            "ac": ac,
            "hit": hit,
            "crit": crit,
        })
        return hit, crit, eff

    def _weapon_damage_roll(self, attacker, item: Dict[str, Any], *, is_ranged: bool, crit: bool) -> int:
        dice = str(item.get("dice", "1d6"))
        n, s = self._parse_dice(dice)
        dmg = 0
        for _ in range(n):
            dmg += self.rng.randint(1, s)
        # crit doubles dice (simple add another set)
        if crit:
            for _ in range(n):
                dmg += self.rng.randint(1, s)
        # add ability mod (DEX for ranged/finesse; STR otherwise)
        ability = "DEX" if (is_ranged or item.get("finesse")) else item.get("ability", "STR")
        dmg += _mod(getattr(attacker, ability, 10))
        # Global retrofit: proficiency bonus to damage
        dmg += _prof_for_level(getattr(attacker, "level", 1))
        return max(0, dmg)

    # ---------------------- AOE ally exemptions (Wizard) ----------------------
    def _apply_aoe_ally_exemptions(self, caster, targets: List[Any], center_xy: Tuple[int,int]) -> List[Any]:
        """
        Remove up to wiz_aoe_ally_exempt allies (closest first) from AOE if the caster is a Wizard.
        This assumes `targets` already include friendlies; we prune them.
        """
        if not self._is_wizard(caster): return targets
        n = int(getattr(caster, "wiz_aoe_ally_exempt", 0))
        if n <= 0: return targets
        cx, cy = center_xy
        allies = [t for t in targets if getattr(t, "team_id", -1) == getattr(caster, "team_id", -2)]
        if not allies: return targets
        # sort allies by manhattan distance to center
        allies_sorted = sorted(allies, key=lambda a: abs(getattr(a, "tx", 0) - cx) + abs(getattr(a, "ty", 0) - cy))
        exempt = set(allies_sorted[:n])
        return [t for t in targets if t not in exempt]

    # ---------------------- Saving throws (advantage hooks) ----------------------
    def _saving_throw(self, target, ability: str, dc: int, *, vs_condition: Optional[str] = None) -> bool:
        """
        Returns True if save succeeds (i.e., avoids or halves effect)
        vs_condition: allow L7 Wizard advantage on blinded/deafened
        """
        adv = 0
        if vs_condition in ("blinded", "deafened") and bool(getattr(target, "wiz_adv_vs_blind_deaf", False)):
            adv = 1
        _, eff = _roll_d20(self.rng, adv)
        total = eff + _mod(getattr(target, ability.upper(), 10))
        self.events.append({"type":"saving_throw","target":_name(target),"ability":ability,"d20":eff,"total":total,"dc":dc,"success":(total>=dc)})
        return total >= dc

    # ---------------------- Turn loop (skeleton) ----------------------
    def _enemies_of(self, f):
        tid = getattr(f, "team_id", -1)
        return [e for e in self.actors if getattr(e, "team_id", -2) != tid]

    def take_turn(self) -> None:
        if self.winner is not None: return
        if self.turn_idx >= len(self.actors): self.turn_idx = 0
        actor = self.actors[self.turn_idx]
        if not _alive(actor):
            self.turn_idx += 1
            return

        # Start-of-turn detection of hidden enemies
        self.events.extend(self._start_of_turn_detect_hidden(actor))

        # Controller decides intents; if you have your own controller system, keep it.
        intents = []
        ctrl = self.controllers.get(getattr(actor, "team_id", 0))
        if ctrl and hasattr(ctrl, "decide"):
            try:
                intents = ctrl.decide(self, actor) or []
            except Exception:
                intents = []
        # Fallback: do nothing
        if not intents:
            intents = [{"type": "wait"}]

        # Execute intents (subset implemented; keep your original branches)
        for intent in intents:
            itype = intent.get("type")
            if itype == "hide":
                self.events.append(self._attempt_hide(actor))
            elif itype == "attack":
                target = intent.get("target")
                if not target or not _alive(target): continue
                main = self._equipped_main(actor)
                dice, ability, is_ranged, reach, finesse = self._weapon_profile_from_item(actor, main)
                # range check for ranged attacks
                if is_ranged:
                    nr, lr = self.ranged_limits(actor, main)
                    dist = abs(getattr(actor, "tx", 0) - getattr(target, "tx", 0)) + abs(getattr(actor, "ty", 0) - getattr(target, "ty", 0))
                    if dist > nr:
                        # in this simplified model we treat >normal as still allowed (no disadvantage model);
                        # but if you want a hard cap, uncomment:
                        # if dist > lr: self.events.append({"type":"attack","reason":"out_of_range"}); continue
                        pass
                hit, crit, eff = self._attack_roll(actor, target, item=main, adv_ctx=0, is_ranged=is_ranged, offhand=False)
                if hit:
                    dmg = self._weapon_damage_roll(actor, main or {}, is_ranged=is_ranged, crit=crit)
                    target.hp = max(0, int(getattr(target, "hp", 0)) - int(dmg))
                    if target.hp == 0: setattr(target, "alive", False)
                    self.events.append({"type":"damage","attacker":_name(actor),"defender":_name(target),"amount":int(dmg),"crit":crit})
            elif itype == "cast":
                # Minimal spell resolution hook (you can expand to your full spell system)
                # expects: {"type":"cast","target":obj,"spell":{"name":...,"level":L,"tag":"attack|aoe|control","dc_override":optional,"attack_roll":bool,"center":(x,y)}}
                spell = intent.get("spell", {})
                target = intent.get("target")
                tag = spell.get("tag", "attack")
                name = spell.get("name", "Spell")
                level = int(spell.get("level", 1))
                # Spend a slot if it's 1..9 (not a cantrip)
                if level >= 1:
                    slots = getattr(actor, "spell_slots_current", None)
                    if slots is not None and len(slots) > level and slots[level] > 0:
                        slots[level] -= 1
                # Attack-roll spells
                if spell.get("attack_roll", False) and target:
                    adv = 0
                    hit, crit, eff = self._attack_roll(actor, target, item=None, adv_ctx=adv, is_ranged=True, offhand=False)
                    if hit:
                        # placeholder damage: cantrip scale via tier
                        tier = int(getattr(actor, "wiz_cantrip_tier", 1))
                        dmg = self.rng.randint(1, 10) * tier  # e.g., Fire Bolt-like
                        target.hp = max(0, int(getattr(target, "hp", 0)) - int(dmg))
                        if target.hp == 0: setattr(target, "alive", False)
                        self.events.append({"type":"spell_hit","name":name,"attacker":_name(actor),"defender":_name(target),"dmg":int(dmg),"tier":tier})
                # Save-based spells (AOE or control)
                elif target or spell.get("center"):
                    dc = int(spell.get("dc_override", getattr(actor, "spell_save_dc", 10)))
                    if spell.get("center"):
                        cx, cy = spell["center"]
                        # Example: collect everyone in a small radius (3x3 diamond); replace with your area finder
                        candidates = [t for t in self.actors if _alive(t)]
                        # Auto-exempt allies up to N for Wizards
                        targets = self._apply_aoe_ally_exemptions(actor, candidates, (cx, cy))
                        for t in targets:
                            if getattr(t, "team_id", -1) == getattr(actor, "team_id", -2):  # skip allies after exemption
                                continue
                            saved = self._saving_throw(t, "DEX", dc, vs_condition=None)
                            dmg = self.rng.randint(1, 6) * (2 if level >= 3 else 1)
                            if saved: dmg //= 2
                            t.hp = max(0, int(getattr(t, "hp", 0)) - int(dmg))
                            if t.hp == 0: setattr(t, "alive", False)
                            self.events.append({"type":"spell_aoe","name":name,"attacker":_name(actor),"defender":_name(t),"dmg":int(dmg),"saved":bool(saved)})
                    elif target:
                        # single-target save
                        saved = self._saving_throw(target, "WIS", dc, vs_condition=None)
                        if not saved:
                            # simple control marker
                            setattr(target, "_controlled", True)
                            self.events.append({"type":"spell_control","name":name,"attacker":_name(actor),"defender":_name(target),"applied":True})
            else:
                # wait / move / other intents handled by your existing logic
                pass

        # Advance turn pointer
        self.turn_idx = (self.turn_idx + 1) % len(self.actors)
