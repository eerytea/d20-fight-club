# core/tactics.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

# -------- Public role/archetype enums (free-form strings allowed, but these help the UI) --------
ROLES = {"Support", "DPS", "Tank"}
ARCHETYPES = {
    # Support
    "Healer", "Buffer", "Debuffer",
    # DPS
    "Sniper", "Bombarder", "Rush", "Assassin",
    # Tank
    "True Tank", "Taunter", "Hero",
}

# -------- Team-level tactics (editable by the human player on a team tactics screen) --------
DEFAULT_TEAM_TACTICS = {
    "target_priority": ["lowest_hp", "closest", "highest_dps"],  # ordered fallbacks
    "heal_threshold": 0.40,  # used by Healer/Hero
    "bombarder_min_enemies_hit": 2,
}

def get_team_tactics(env, team_id: int) -> Dict[str, Any]:
    t = getattr(env, "team_tactics", None) or {}
    base = DEFAULT_TEAM_TACTICS.copy()
    base.update(t.get(int(team_id), {}))
    return base

# -------- Player-level setup (role/archetype are player-editable; no auto-assign) --------
def set_role(player: Dict[str, Any], role: Optional[str], archetype: Optional[str]) -> None:
    if role is None:
        player.pop("role", None)
    else:
        player["role"] = str(role)
    if archetype is None:
        player.pop("archetype", None)
    else:
        player["archetype"] = str(archetype)

# -------- Helpers used by the router --------
def _mod(v: int) -> int: return (int(v) - 10) // 2

def _alive(p) -> bool:
    return bool(getattr(p, "alive", True)) and int(getattr(p, "hp", 1)) > 0

def _dist(a, b) -> int:
    return abs(getattr(a, "tx", 0) - getattr(b, "tx", 0)) + abs(getattr(a, "ty", 0) - getattr(b, "ty", 0))

def _pick_target_by_priority(env, me, priority: List[str]) -> Optional[Any]:
    enemies = [e for e in env.actors if _alive(e) and getattr(e, "team_id", -1) != getattr(me, "team_id", -2)]
    if not enemies:
        return None

    # derive helper metrics lazily
    def highest_dps_key(p):
        # cheap proxy: OVR + STR/DEX/INT mods
        ovr = int(getattr(p, "OVR", 50))
        strm = _mod(getattr(p, "STR", getattr(p, "str", 10)))
        dexm = _mod(getattr(p, "DEX", getattr(p, "dex", 10)))
        intm = _mod(getattr(p, "INT", getattr(p, "int", 10)))
        return -(ovr + max(strm, dexm, intm)*3)

    for rule in priority:
        if rule == "lowest_hp":
            cand = min(enemies, key=lambda e: (int(getattr(e, "hp", 1)) / max(1, int(getattr(e, "max_hp", 1)))), default=None)
        elif rule == "highest_dps":
            cand = min(enemies, key=highest_dps_key, default=None)
        elif rule == "closest":
            cand = min(enemies, key=lambda e: _dist(me, e), default=None)
        elif rule == "highest_ovr":
            cand = max(enemies, key=lambda e: int(getattr(e, "OVR", 50)), default=None)
        else:
            cand = None
        if cand is not None:
            return cand
    return enemies[0]

def _has_bonus_hide(me) -> bool:
    cls = str(getattr(me, "class", "")).capitalize()
    lvl = int(getattr(me, "level", 1))
    if cls == "Stalker" and lvl >= 10:  # Hide as bonus action
        return True
    if cls == "Rogue":                  # Rogue Cunning Action (our design intent)
        return True
    return False

def _two_handed_in_use(env, me) -> bool:
    main = env._equipped_main(me)
    if not main: return False
    if main.get("two_handed"): return True
    return bool(main.get("versatile")) and not env._has_shield_equipped(me) and env._equipped_off(me) is None

# -------- Public router: returns a list of intents the engine can execute --------
def choose_intent(env, me) -> List[Dict[str, Any]]:
    if not _alive(me):
        return [{"type": "wait"}]

    role = str(getattr(me, "role", "")).strip()
    arche = str(getattr(me, "archetype", "")).strip()
    team_cfg = get_team_tactics(env, getattr(me, "team_id", 0))
    prio = list(team_cfg.get("target_priority", DEFAULT_TEAM_TACTICS["target_priority"]))

    # Helpers
    target = _pick_target_by_priority(env, me, prio)

    # ------------- SUPPORT -------------
    if role == "Support":
        if arche == "Healer":
            # Heal nearest ally < threshold; else attack target
            thr = float(team_cfg.get("heal_threshold", 0.40))
            allies = [a for a in env.actors if _alive(a) and getattr(a, "team_id", -1) == getattr(me, "team_id", -2)]
            low = [a for a in allies if int(getattr(a, "hp", 0)) / max(1, int(getattr(a, "max_hp", 1))) < thr]
            if low:
                ally = min(low, key=lambda a: _dist(me, a))
                return [{"type": "lay_on_hands", "target": ally, "amount": int(getattr(me, "cru_lay_on_hands_current", 0)) // 2 or 1}]
            if target:
                return [{"type": "attack", "target": target}]
            return [{"type": "wait"}]

        if arche == "Buffer":
            # Prefer buff intent if available, else attack
            if target:
                return [{"type": "attack", "target": target}]
            return [{"type": "wait"}]

        if arche == "Debuffer":
            if target:
                return [{"type": "cast", "spell": {"name": "Debuff", "level": 1, "vs_condition": "blinded"}, "target": target}]
            return [{"type": "wait"}]

    # ------------- DPS -------------
    if role == "DPS":
        if arche == "Sniper":
            if target:
                return [{"type": "attack", "target": target}]
            return [{"type": "wait"}]

        if arche == "Bombarder":
            # Try an AOE centered near enemies (engine will resolve ally exemptions if Wizard)
            min_hits = int(team_cfg.get("bombarder_min_enemies_hit", 2))
            enemies = [e for e in env.actors if _alive(e) and getattr(e, "team_id", -1) != getattr(me, "team_id", -2)]
            if enemies:
                # crude: center on the closest enemy
                center = (getattr(enemies[0], "tx", 0), getattr(enemies[0], "ty", 0))
                # ask engine to resolve AOE; if few enemies on board, still attempt if >=1
                return [{"type": "cast", "spell": {"name": "Bombard", "level": 3, "center": center, "dtype": "fire"}}]
            if target:
                return [{"type": "attack", "target": target}]
            return [{"type": "wait"}]

        if arche == "Rush":
            if target:
                return [{"type": "attack", "target": target}]
            return [{"type": "wait"}]

        if arche == "Assassin":
            # If bonus-action Hide available: try every turn; else alternate hide -> strike
            if _has_bonus_hide(me):
                # Try to hide; engine will auto-detect next turn
                if not getattr(me, "hidden", False):
                    return [{"type": "hide"}]
                if target:
                    return [{"type": "attack", "target": target}]
                return [{"type": "wait"}]
            else:
                prev = getattr(me, "_tac_last_action", "")
                if prev != "hide":
                    me._tac_last_action = "hide"
                    return [{"type": "hide"}]
                me._tac_last_action = "attack"
                if target:
                    return [{"type": "attack", "target": target}]
                return [{"type": "wait"}]

    # ------------- TANK -------------
    if role == "Tank":
        if arche == "True Tank":
            if target:
                return [{"type": "attack", "target": target}]
            return [{"type": "wait"}]

        if arche == "Taunter":
            # Prefer taunt first if a target exists, else attack
            if target:
                return [{"type": "taunt", "target": target}]
            return [{"type": "wait"}]

        if arche == "Hero":
            # Find endangered ally; move adjacent (abstracted) & buff/heal them; then engage their target
            thr = float(team_cfg.get("heal_threshold", 0.40))
            allies = [a for a in env.actors if _alive(a) and getattr(a, "team_id", -1) == getattr(me, "team_id", -2) and a is not me]
            low = [a for a in allies if int(getattr(a, "hp", 0)) / max(1, int(getattr(a, "max_hp", 1))) < thr]
            if low:
                ally = min(low, key=lambda a: _dist(me, a))
                # heal or buff self/adjacent ally
                if int(getattr(me, "cru_lay_on_hands_current", 0)) > 0:
                    amt = max(1, int(getattr(me, "cru_lay_on_hands_current", 0)) // 2)
                    # then attack the same target that threatens the ally (fallback to selected target)
                    tgt = _pick_target_by_priority(env, ally, prio) or _pick_target_by_priority(env, me, prio)
                    intents = [{"type": "lay_on_hands", "target": ally, "amount": amt}]
                    if tgt: intents.append({"type": "attack", "target": tgt})
                    return intents
            if target:
                return [{"type": "attack", "target": target}]
            return [{"type": "wait"}]

    # Fallbacks
    if target:
        return [{"type": "attack", "target": target}]
    return [{"type": "wait"}]
