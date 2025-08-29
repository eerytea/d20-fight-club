# engine/tbcombat.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random
import math

# Public surface used by UI/other modules
__all__ = ["TBCombat", "Team"]

# --- Simple Team container (kept minimal; UI imports it from engine) ---
@dataclass
class Team:
    tid: int
    name: str
    color: Tuple[int, int, int] = (200, 200, 200)

# --- Utility: ability modifier ---
def _mod(score: int) -> int:
    try:
        return (int(score) - 10) // 2
    except Exception:
        return 0

# --- Dice helpers ---
def _parse_dice(spec: Any) -> Tuple[int, int]:
    """
    Accepts:
      - tuple/list like (num, sides)
      - string "XdY"
      - int -> treated as 1d<int>
      - None -> default 1d4
    """
    if isinstance(spec, (tuple, list)) and len(spec) == 2:
        return max(1, int(spec[0])), max(1, int(spec[1]))
    if isinstance(spec, str):
        s = spec.lower().strip()
        if "d" in s:
            a, b = s.split("d", 1)
            a = a.strip() or "1"
            try:
                return max(1, int(a)), max(1, int(b))
            except Exception:
                return 1, 4
        try:
            v = int(spec)
            return 1, max(1, v)
        except Exception:
            return 1, 4
    if isinstance(spec, int):
        return 1, max(1, spec)
    return 1, 4

def _roll_dice(rng: random.Random, num: int, sides: int) -> int:
    return sum(rng.randint(1, sides) for _ in range(max(1, num)))

def _roll_d20(rng: random.Random, adv: int = 0) -> Tuple[int, int]:
    """
    Returns (natural, effective). adv=+1 advantage, -1 disadvantage, 0 normal.
    We cap |adv| at 1 for now.
    """
    adv = 1 if adv > 0 else -1 if adv < 0 else 0
    if adv == 0:
        n = rng.randint(1, 20)
        return n, n
    a = rng.randint(1, 20)
    b = rng.randint(1, 20)
    return (a, max(a, b)) if adv > 0 else (a, min(a, b))

# --- Grid helpers ---
def _chebyshev(a: Tuple[int,int], b: Tuple[int,int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def _manhattan(a: Tuple[int,int], b: Tuple[int,int]) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

# --- Fighter helpers ---
def _alive(f) -> bool:
    return bool(getattr(f, "alive", True)) and getattr(f, "hp", 1) > 0

def _ensure_xy(f):
    # normalize {x,y} and {tx,ty} so the UI sees consistent coords
    for attr in ("x", "tx"):
        if not hasattr(f, attr):
            try: setattr(f, attr, 0)
            except Exception: pass
    for attr in ("y", "ty"):
        if not hasattr(f, attr):
            try: setattr(f, attr, 0)
            except Exception: pass

def _name(f) -> str:
    n = getattr(f, "name", None)
    if n: return str(n)
    first = getattr(f, "first", getattr(f, "first_name", "")) or ""
    last  = getattr(f, "last", getattr(f, "last_name", "")) or ""
    s = (first + " " + last).strip()
    return s if s else f"F{getattr(f, 'pid', getattr(f, 'id', '?'))}"

def _team_id(f) -> int:
    return int(getattr(f, "team_id", getattr(f, "tid", 0)))

def _dex_mod(f) -> int:
    return _mod(getattr(f, "dex", getattr(f, "DEX", 10)))

def _str_mod(f) -> int:
    return _mod(getattr(f, "str", getattr(f, "STR", 10)))

def _ac(f) -> int:
    # Respect explicit AC if set; otherwise fallback to DEX-based baseline
    if hasattr(f, "ac"):
        try: return int(getattr(f, "ac"))
        except Exception: pass
    dex = getattr(f, "dex", getattr(f, "DEX", 10))
    armor_bonus = getattr(f, "armor_bonus", 0)
    return 10 + _mod(dex) + int(armor_bonus)

def _weapon_profile(f) -> Tuple[int, int, str, int]:
    """
    Returns (num_dice, die_sides, ability_used, reach)
    ability_used is "STR" or "DEX" for mod selection
    """
    w = getattr(f, "weapon", None)
    if w is None:
        return (1, 4, "STR", 1)
    # Dict style
    if isinstance(w, dict):
        num, sides = _parse_dice(w.get("dice", w.get("formula", "1d4")))
        reach = int(w.get("reach", 1))
        ability = str(w.get("ability", w.get("mod", "STR"))).upper()
        if ability not in ("STR", "DEX"):
            ability = "STR"
        return (num, sides, ability, max(1, reach))
    # String style "1d6", optional suffix " reach=2" (loose parsing)
    if isinstance(w, str):
        # crude parse for "... reach=2" or "(reach 2)"
        base = w
        reach = 1
        if "reach" in w:
            try:
                part = w.split("reach", 1)[1]
                digits = "".join(ch for ch in part if ch.isdigit())
                if digits:
                    reach = int(digits)
            except Exception:
                pass
            base = w.split("reach", 1)[0]
        num, sides = _parse_dice(base.strip())
        # finesse guess: daggers/rapiers use DEX
        ability = "DEX" if any(k in w.lower() for k in ("dagger", "rapier", "finesse")) else "STR"
        return (num, sides, ability, max(1, reach))
    # Int -> 1dX
    if isinstance(w, int):
        num, sides = _parse_dice(w)
        return (num, sides, "STR", 1)
    # fallback
    return (1, 4, "STR", 1)

def _ability_mod(f, ability: str) -> int:
    return _dex_mod(f) if ability == "DEX" else _str_mod(f)

# --- TBCombat core ---
class TBCombat:
    """
    Turn-based combat on a rectangular grid.

    Features:
      - Initiative once at start (d20 + DEX mod), fixed across rounds.
      - Per-turn speed (default 4); multi-step movement until in reach.
      - Melee attacks with weapon profiles (XdY + mod), reach, crits on nat 20.
      - Advantage/disadvantage supported at roll site (flags on fighters).
      - Opportunity Attacks (OA): leaving an enemy's reach provokes one reaction per enemy each round.
      - Event stream: 'round_start', 'turn_start', 'move_step', 'attack', 'damage', 'down', 'end'.
    """

    def __init__(self, teamA: Team, teamB: Team, fighters: List[Any], cols: int, rows: int, seed: Optional[int] = None):
        self.teams = [teamA, teamB]
        self.cols = int(cols)
        self.rows = int(rows)
        self.rng = random.Random(seed if seed is not None else random.randint(0, 10_000_000))

        self.fighters: List[Any] = list(fighters)
        for f in self.fighters:
            _ensure_xy(f)
            if not hasattr(f, "alive"):
                try: setattr(f, "alive", True)
                except Exception: pass
            if not hasattr(f, "hp"):
                try: setattr(f, "hp", getattr(f, "max_hp", 10))
                except Exception: pass
            if not hasattr(f, "speed"):
                try: setattr(f, "speed", 4)  # default movement speed
                except Exception: pass

        # battle state
        self.events: List[Any] = []
        self.round: int = 1
        self.turn_idx: int = 0  # index in initiative list
        self.winner: Optional[int] = None

        # initiative & per-round reactions
        self._initiative: List[int] = []  # list of indices into self.fighters
        self._roll_initiative()

        self._push({"type": "round_start", "round": self.round})
        self._reset_reactions_for_round()

    # --- Public API ---
    def take_turn(self):
        """Advance the battle by exactly one actor's turn."""
        if self.winner is not None:
            return

        # Find next living actor
        f_idx = self._next_living_index()
        if f_idx is None:
            # All dead? End battle.
            self._end_if_finished()
            return

        self.turn_idx = f_idx
        actor = self.fighters[self._initiative[self.turn_idx]]
        if not _alive(actor):
            # skip just in case
            self._advance_turn_pointer()
            self._end_if_finished()
            return

        self._push({"type": "turn_start", "actor": _name(actor), "actor_id": getattr(actor, "pid", None)})

        # Take an AI turn: move towards nearest enemy until in reach, then attack once.
        enemy = self._choose_target(actor)
        if enemy is None:
            # no enemies; end
            self._end_if_finished()
            self._advance_turn_pointer()
            return

        # Try to attack if already in reach
        reach = self._reach(actor)
        if self._in_reach(actor, enemy, reach):
            self._attack(actor, enemy)
        else:
            # Move up to speed steps toward enemy; stop if in reach mid-way
            steps = max(0, int(getattr(actor, "speed", 4)))
            for _ in range(steps):
                if self._in_reach(actor, enemy, reach):
                    break
                moved = self._step_towards(actor, enemy)
                if not moved:
                    break  # blocked
                if not _alive(enemy):
                    break
            # After movement, attack if now in reach
            if _alive(actor) and _alive(enemy) and self._in_reach(actor, enemy, reach):
                self._attack(actor, enemy)

        self._advance_turn_pointer()
        self._end_if_finished()

    # --- Initiative & Round ---
    def _roll_initiative(self):
        # List of fighter indices
        order = list(range(len(self.fighters)))
        # Compute scores
        init_scores = []
        for i in order:
            f = self.fighters[i]
            n, eff = _roll_d20(self.rng)  # no adv on init for now
            score = eff + _dex_mod(f)
            init_scores.append((i, score, _dex_mod(f), self.rng.random()))
        # Sort by score desc, then dex mod desc, then random tie-breaker
        init_scores.sort(key=lambda t: (t[1], t[2], t[3]), reverse=True)
        self._initiative = [i for (i, _, __, ___) in init_scores]
        # Reset per-round reaction availability
        self._reset_reactions_for_round()

    def _reset_reactions_for_round(self):
        for f in self.fighters:
            try: setattr(f, "reaction_ready", True)
            except Exception: pass

    def _advance_turn_pointer(self):
        # Move pointer; if we wrapped, new round
        if len(self._initiative) == 0:
            return
        self.turn_idx = (self.turn_idx + 1) % len(self._initiative)
        if self.turn_idx == 0:
            # New round
            self.round += 1
            self._push({"type": "round_start", "round": self.round})
            self._reset_reactions_for_round()

    def _next_living_index(self) -> Optional[int]:
        if not self._initiative:
            return None
        n = len(self._initiative)
        for off in range(n):
            idx = (self.turn_idx + off) % n
            f = self.fighters[self._initiative[idx]]
            if _alive(f):
                return idx
        return None

    # --- Grid & Occupancy ---
    def _pos(self, f) -> Tuple[int,int]:
        return int(getattr(f, "x", getattr(f, "tx", 0))), int(getattr(f, "y", getattr(f, "ty", 0)))

    def _set_pos(self, f, x: int, y: int):
        try: setattr(f, "x", int(x)); setattr(f, "y", int(y))
        except Exception: pass
        try: setattr(f, "tx", int(x)); setattr(f, "ty", int(y))
        except Exception: pass

    def _occupied(self, x: int, y: int) -> Optional[Any]:
        for g in self.fighters:
            if not _alive(g): continue
            gx, gy = self._pos(g)
            if gx == x and gy == y:
                return g
        return None

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    # --- Targeting & AI ---
    def _choose_target(self, actor) -> Optional[Any]:
        # Nearest living enemy by Chebyshev distance, tie-breaker: lowest HP then team order.
        best = None
        best_d = 10**9
        ax, ay = self._pos(actor)
        a_team = _team_id(actor)
        for g in self.fighters:
            if not _alive(g): continue
            if _team_id(g) == a_team: continue
            d = _chebyshev((ax, ay), self._pos(g))
            if d < best_d:
                best = g; best_d = d
            elif d == best_d:
                # tie-breaker: lower HP
                if getattr(g, "hp", 1) < getattr(best, "hp", 1):
                    best = g
        return best

    def _reach(self, f) -> int:
        _, _, ability, reach = _weapon_profile(f)
        return max(1, int(reach))

    def _in_reach(self, a, b, reach: Optional[int] = None) -> bool:
        if reach is None:
            reach = self._reach(a)
        ax, ay = self._pos(a)
        bx, by = self._pos(b)
        return _chebyshev((ax, ay), (bx, by)) <= int(reach)

    def _neighbors4(self, x: int, y: int) -> List[Tuple[int,int]]:
        return [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]

    def _step_towards(self, actor, target) -> bool:
        """
        Greedy 4-dir step toward the target with occupancy/bounds checks.
        Triggers Opportunity Attacks if leaving enemy reach.
        """
        ax, ay = self._pos(actor)
        tx, ty = self._pos(target)

        # Try axis that reduces Manhattan distance most, then alternate options
        options: List[Tuple[int,int]] = []
        dx = tx - ax; dy = ty - ay
        primary = []
        if abs(dx) >= abs(dy):
            primary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
            secondary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
        else:
            primary = [(0, 1 if dy > 0 else -1)] if dy != 0 else []
            secondary = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
        options = primary + secondary

        # Add side options (try to slide around obstacles)
        options += [(1,0), (-1,0), (0,1), (0,-1)]

        # Evaluate unique next cells
        tried = set()
        for vx, vy in options:
            nx, ny = ax + vx, ay + vy
            if (nx,ny) in tried: continue
            tried.add((nx,ny))
            if not self._in_bounds(nx, ny): continue
            if self._occupied(nx, ny): continue

            # OA check: leaving reach of any enemy with reaction ready
            threatened_by = self._enemies_in_reach_of(actor, (ax,ay))
            threatened_after = self._enemies_in_reach_of(actor, (nx,ny))
            provokers = [e for e in threatened_by if e not in threatened_after and getattr(e, "reaction_ready", True) and _alive(e)]

            # Resolve OAs (each enemy at most once per round)
            for e in list(provokers):
                self._opportunity_attack(e, actor)
                # mark reaction spent
                try: setattr(e, "reaction_ready", False)
                except Exception: pass
                if not _alive(actor):
                    # actor dropped before stepping out
                    return False

            # Perform the step
            self._set_pos(actor, nx, ny)
            self._push({"type": "move_step", "actor": _name(actor), "to": (nx, ny)})
            return True

        # Blocked
        self._push({"type": "blocked", "actor": _name(actor), "at": (ax, ay)})
        return False

    def _enemies_in_reach_of(self, actor, pos: Tuple[int,int]) -> List[Any]:
        a_team = _team_id(actor)
        in_reach = []
        for e in self.fighters:
            if not _alive(e): continue
            if _team_id(e) == a_team: continue
            ex, ey = self._pos(e)
            if _chebyshev((ex, ey), pos) <= self._reach(e):
                in_reach.append(e)
        return in_reach

    # --- Attacking ---
    def _attack(self, attacker, defender, *, is_reaction: bool = False):
        if not (_alive(attacker) and _alive(defender)):
            return
        # Advantage/disadvantage flags (optional on fighter)
        adv = 0
        if getattr(attacker, "advantage", False): adv += 1
        if getattr(attacker, "disadvantage", False): adv -= 1
        # roll to hit
        nat, eff = _roll_d20(self.rng, adv=adv)
        num, sides, ability, reach = _weapon_profile(attacker)
        atk_mod = _ability_mod(attacker, ability)
        ac = _ac(defender)
        crit = (nat == 20)
        hit = (eff + atk_mod >= ac) or crit

        self._push({
            "type": "attack",
            "actor": _name(attacker),
            "target": _name(defender),
            "roll": nat,
            "effective": eff,
            "mod": atk_mod,
            "target_ac": ac,
            "hit": hit,
            "critical": crit,
            "opportunity": bool(is_reaction),
        })

        if hit:
            dice_num = num * (2 if crit else 1)
            dmg = _roll_dice(self.rng, dice_num, sides) + atk_mod
            if dmg < 1: dmg = 1
            self._apply_damage(attacker, defender, dmg)

    def _opportunity_attack(self, attacker, mover):
        self._attack(attacker, mover, is_reaction=True)

    def _apply_damage(self, attacker, defender, dmg: int):
        try:
            defender.hp = int(defender.hp) - int(dmg)
        except Exception:
            pass
        self._push({"type": "damage", "actor": _name(attacker), "target": _name(defender), "amount": int(dmg)})

        if getattr(defender, "hp", 0) <= 0 and _alive(defender):
            try: setattr(defender, "alive", False)
            except Exception: pass
            self._push({"type": "down", "name": _name(defender)})

    # --- End conditions ---
    def _end_if_finished(self):
        alive0 = any(_alive(f) and _team_id(f) == 0 for f in self.fighters)
        alive1 = any(_alive(f) and _team_id(f) == 1 for f in self.fighters)
        if alive0 and alive1:
            return
        if alive0 and not alive1:
            self.winner = 0
        elif alive1 and not alive0:
            self.winner = 1
        else:
            self.winner = None  # double KO
        self._push({"type": "end", "winner": self.winner})

    # --- Events ---
    def _push(self, e: Any):
        self.events.append(e)
