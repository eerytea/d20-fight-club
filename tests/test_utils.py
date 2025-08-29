# tests/utils.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from engine.tbcombat import TBCombat, Team
from engine.constants import GRID_COLS, GRID_ROWS

@dataclass
class Fighter:
    pid: int
    team_id: int
    name: str = "Fighter"
    hp: int = 20
    max_hp: int = 20
    ac: int = 12
    STR: int = 12
    DEX: int = 12
    CON: int = 12
    INT: int = 10
    WIS: int = 10
    CHA: int = 10
    speed: int = 4
    weapon: Any = None
    tx: int = 0
    ty: int = 0
    alive: bool = True

def make_melee(pid: int, tid: int, x: int, y: int, dice="1d6", reach=1, STR=14, DEX=10, ac=12, hp=20) -> Fighter:
    f = Fighter(pid=pid, team_id=tid, name=f"P{pid}", hp=hp, max_hp=hp, ac=ac, STR=STR, DEX=DEX, tx=x, ty=y)
    f.weapon = {"dice": dice, "reach": reach, "ability": "STR"}
    return f

def make_ranged(pid: int, tid: int, x: int, y: int, dice="1d6", normal=8, long=16, DEX=14, ac=12, hp=18) -> Fighter:
    f = Fighter(pid=pid, team_id=tid, name=f"P{pid}", hp=hp, max_hp=hp, ac=ac, DEX=DEX, tx=x, ty=y)
    f.weapon = {"dice": dice, "ranged": True, "range": (normal, long), "ability": "DEX"}
    return f

class ScriptedController:
    """
    Map pid -> list of intents. Once returned for an actor, the list is consumed.
    If no entries for pid, returns [] (engine falls back to baseline if needed).
    """
    def __init__(self, by_pid: Dict[int, List[Dict[str, Any]]]):
        self.by_pid = {k: list(v) for k, v in by_pid.items()}

    def decide(self, world: TBCombat, actor) -> List[Dict[str, Any]]:
        pid = getattr(actor, "pid", getattr(actor, "id", None))
        if pid is None:
            return []
        seq = self.by_pid.get(pid, [])
        self.by_pid[pid] = []
        return seq

def build_combat(fighters: List[Fighter], seed: int = 123) -> TBCombat:
    t0 = Team(0, "Home", (60, 160, 230))
    t1 = Team(1, "Away", (220, 80, 80))
    return TBCombat(t0, t1, fighters, GRID_COLS, GRID_ROWS, seed=seed)

def set_initiative_order(combat: TBCombat, pids_in_order: List[int]) -> None:
    # reorder initiative deterministically by pid order
    idx_map = []
    for pid in pids_in_order:
        for i, f in enumerate(combat.fighters):
            fp = getattr(f, "pid", getattr(f, "id", None))
            if fp == pid:
                idx_map.append(i)
                break
    if len(idx_map) == len(combat.fighters):
        combat._initiative = idx_map
        combat.turn_idx = 0

def last_events_of_type(combat: TBCombat, typ: str) -> List[Dict[str, Any]]:
    return [e for e in combat.events if e.get("type") == typ]
