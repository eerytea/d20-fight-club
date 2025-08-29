# engine/team_tactics.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, List

# -----------------------------
#   Data models (plain knobs)
# -----------------------------
@dataclass
class RoleSpec:
    # Display / tag
    name: str = "fighter"                 # e.g. tank, skirmisher, sniper, healer

    # Behavior
    stance: str = "balanced"              # aggressive | balanced | defensive | hold
    desired_range: int = 1                # 1=melee, >=2 for reach/ranged
    avoid_oa: bool = True                 # try to route around OA zones
    focus: str = "closest"                # closest | lowest_hp | highest_ovr
    roam: int = 3                         # tiles allowed from anchor
    anchor: Optional[Tuple[int,int]] = None

    # 🎯 Patch B: one-shot attack roll modifiers
    attack_advantage: bool = False
    attack_disadvantage: bool = False

@dataclass
class TeamTactics:
    default: RoleSpec = field(default_factory=RoleSpec)
    roles: Dict[Any, RoleSpec] = field(default_factory=dict)  # pid -> RoleSpec

@dataclass
class MatchTactics:
    by_team: Dict[int, TeamTactics] = field(default_factory=dict)

# -----------------------------------------
# Strategy interface
# -----------------------------------------
class BaseController:
    """Strategy interface. The combat engine will call decide(world, actor)."""
    def decide(self, world, actor) -> List[dict]:
        raise NotImplementedError


class TacticsController(BaseController):
    """
    A simple controller that respects RoleSpec knobs.
    It plans up to `speed` move steps (using world.path_step) and then attacks if in range.
    """
    def __init__(self, tactics: TeamTactics):
        self.tactics = tactics

    # ------- Policy helpers -------
    def _spec_for(self, actor) -> RoleSpec:
        pid = getattr(actor, "pid", None)
        return self.tactics.roles.get(pid, self.tactics.default)

    def _score_target(self, world, actor, enemy, spec: RoleSpec) -> tuple:
        # Lower = better
        d = world.distance(actor, enemy)
        hp = getattr(enemy, "hp", 1)
        ovr = getattr(enemy, "ovr", getattr(enemy, "OVR", 50))
        if spec.focus == "lowest_hp":
            return (hp, d, -ovr)
        if spec.focus == "highest_ovr":
            return (-ovr, d, hp)
        # closest (default)
        return (d, hp, -ovr)

    def _select_target(self, world, actor, spec: RoleSpec):
        best = None; best_score = (10**9, 10**9, 10**9)
        for e in world.fighters:
            if getattr(e, "alive", True) and getattr(e, "hp", 1) > 0 and getattr(e, "team_id", getattr(e, "tid", None)) != getattr(actor, "team_id", getattr(actor, "tid", None)):
                score = self._score_target(world, actor, e, spec)
                if score < best_score:
                    best = e; best_score = score
        return best

    def _enforce_anchor(self, world, actor, spec: RoleSpec) -> Optional[Tuple[int, int]]:
        if not spec.anchor:
            return None
        ax, ay = spec.anchor
        # If too far from anchor, move back toward it.
        if world.distance_xy(actor, (ax, ay)) > spec.roam:
            step = world.path_step_towards(actor, (ax, ay), avoid_oa=spec.avoid_oa)
            return step
        return None

    # ------- Main decision -------
    def decide(self, world, actor) -> List[dict]:
        spec = self._spec_for(actor)

        desired = max(1, int(spec.desired_range))
        desired = max(desired, world.reach(actor))  # don’t desire less than own reach

        # First: respect anchor/roam if too far away
        back_step = self._enforce_anchor(world, actor, spec)
        if back_step is not None:
            return [{"type": "move", "to": back_step}]

        enemy = self._select_target(world, actor, spec)
        if not enemy:
            return [{"type": "end"}]

        dist = world.distance(actor, enemy)
        speed = world.speed(actor)

        intents: List[dict] = []

        # Simple action-economy heuristics:
        # - Defensive stance with low HP → Dodge
        try:
            hp = int(getattr(actor, "hp", 1)); mhp = int(getattr(actor, "max_hp", max(1, hp)))
        except Exception:
            hp, mhp = 1, 1
        if str(getattr(spec, "stance", "balanced")).lower() == "defensive" and hp * 2 <= mhp:
            intents.append({"type": "dodge"})

        # - If playing as ranged (desired >= 2) and threatened in melee, Disengage first
        if int(desired) >= 2:
            try:
                if world._threatened_in_melee(actor):
                    intents.append({"type": "disengage"})
            except Exception:
                pass

        # - If far from desired range, Dash once to close/open distance faster
        if dist > speed and int(desired) >= 2:
            intents.append({"type": "dash"})

        # If already in desired range, attack now (with one-shot roll settings)
        if world.distance(actor, enemy) <= desired:
            if getattr(spec, "attack_advantage", False):
                try: world.grant_advantage(actor, 1)
                except Exception: pass
            if getattr(spec, "attack_disadvantage", False):
                try: world.grant_disadvantage(actor, 1)
                except Exception: pass
            # Ranged stance may choose to hide first, then shoot
            if int(desired) >= 2:
                intents.append({"type": "hide"})
            intents.append({"type": "attack", "target": enemy})
            return intents

        # Otherwise, plan up to speed steps toward target (avoiding OA when possible)
        for _ in range(speed):
            if world.distance(actor, enemy) <= desired:
                break
            step = world.path_step(actor, enemy, avoid_oa=spec.avoid_oa)
            if step is None:
                break
            intents.append({"type": "move", "to": step})

        # If we've reached desired range and are a ranged stance, consider Hiding before attacking
        if world.distance(actor, enemy) <= desired and int(desired) >= 2:
            intents.append({"type": "hide"})

        # After moving, apply one-shot roll modifiers if configured, then attack if in range
        if world.distance(actor, enemy) <= desired:
            if getattr(spec, "attack_advantage", False):
                try: world.grant_advantage(actor, 1)
                except Exception: pass
            if getattr(spec, "attack_disadvantage", False):
                try: world.grant_disadvantage(actor, 1)
                except Exception: pass
            intents.append({"type": "attack", "target": enemy})

        if not intents:
            intents.append({"type": "end"})
        return intents


# -----------------------------------------
# Fixture parsing helpers (unchanged API)
# -----------------------------------------
def _rolespec_from_dict(d: Dict[str, Any]) -> RoleSpec:
    rs = RoleSpec()
    if not isinstance(d, dict):
        return rs
    rs.name = str(d.get("name", rs.name))
    rs.stance = str(d.get("stance", rs.stance))
    rs.desired_range = int(d.get("desired_range", rs.desired_range))
    rs.avoid_oa = bool(d.get("avoid_oa", rs.avoid_oa))
    rs.focus = str(d.get("focus", rs.focus))
    rs.roam = int(d.get("roam", rs.roam))
    anc = d.get("anchor")
    if isinstance(anc, (tuple, list)) and len(anc) == 2:
        rs.anchor = (int(anc[0]), int(anc[1]))
    elif isinstance(anc, dict) and "x" in anc and "y" in anc:
        rs.anchor = (int(anc["x"]), int(anc["y"]))

    # 🎯 Patch B fields
    rs.attack_advantage = bool(d.get("attack_advantage", rs.attack_advantage))
    rs.attack_disadvantage = bool(d.get("attack_disadvantage", rs.attack_disadvantage))
    return rs

def team_tactics_from_fixture(blob: Dict[str, Any]) -> TeamTactics:
    tt = TeamTactics()
    if not isinstance(blob, dict):
        return tt
    # defaults
    if "default" in blob:
        tt.default = _rolespec_from_dict(blob["default"])
    # roles
    roles = blob.get("roles", {})
    if isinstance(roles, dict):
        for pid, spec in roles.items():
            tt.roles[pid] = _rolespec_from_dict(spec)
    return tt

def load_match_tactics(fixture: Dict[str, Any]) -> MatchTactics:
    """
    UI can embed tactics in fixture like:
      fixture["tactics"] = {
        "home": { "default": {...}, "roles": {pid: {...}} },
        "away": { ... }
      }
    """
    mt = MatchTactics()
    if not isinstance(fixture, dict):
        return mt
    tac = fixture.get("tactics")
    if not isinstance(tac, dict):
        return mt
    if "home" in tac:
        mt.by_team[0] = team_tactics_from_fixture(tac["home"])
    if "away" in tac:
        mt.by_team[1] = team_tactics_from_fixture(tac["away"])
    return mt
