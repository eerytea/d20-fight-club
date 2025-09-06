# tools/batch_balance.py
from __future__ import annotations
import argparse, random, statistics
from typing import Dict, Any, List, Tuple
from engine.tbcombat import TBCombat
from engine.model import Fighter, Team
from core.creator import ensure_class_features, grant_starting_kit

# --- knobs ---
GRID_W = 16; GRID_H = 16

CLASSES = ["Fighter","Ranger","Paladin","Wizard","Druid","Rogue","Barbarian","Cleric","Bard","Monk","Warlock","Sorcerer"]  # trim to your current set
TEAM_SIZE = 5

def _mk_fighter(pid: int, team_id: int, klass: str, seed: int) -> Fighter:
    rng = random.Random(seed + pid*997 + team_id*131)
    base = {
        "name": f"{klass[:3]}-{team_id}-{pid}",
        "level": 1,
        "hp": 10 + rng.randint(0, 8),
        "STR": 10 + rng.randint(0, 6),
        "DEX": 10 + rng.randint(0, 6),
        "CON": 10 + rng.randint(0, 6),
        "INT": 10 + rng.randint(0, 6),
        "WIS": 10 + rng.randint(0, 6),
        "CHA": 10 + rng.randint(0, 6),
        "team_id": team_id,
        "class": klass,
    }
    f = Fighter(**base)
    # apply class features & starting kit so this aligns with game rules:
    ensure_class_features(f.__dict__)
    grant_starting_kit(f.__dict__)
    # snapshot
    return f

def _mk_team(tid: int, klasses: List[str], seed: int) -> Team:
    fighters = []
    # evenly cycle through provided classes
    for i in range(TEAM_SIZE):
        k = klasses[i % len(klasses)]
        fighters.append(_mk_fighter(i, tid, k, seed))
    color = (200,50,50) if tid==0 else (50,50,200)
    return Team(id=tid, name=f"T{tid}", color=color, fighters=fighters)

def run_match(seed: int, klasses_home: List[str], klasses_away: List[str]) -> Dict[str, Any]:
    t1 = _mk_team(0, klasses_home, seed)
    t2 = _mk_team(1, klasses_away, seed)
    actors = t1.fighters + t2.fighters
    cmb = TBCombat(t1, t2, actors, width=GRID_W, height=GRID_H, seed=seed)
    turns = 0
    while not cmb.finished and turns < 200:
        cmb.take_turn()
        turns += 1
    # summarize
    k_home = sum(1 for f in t2.fighters if not f.alive or getattr(f, "hp", 1) <= 0)
    k_away = sum(1 for f in t1.fighters if not f.alive or getattr(f, "hp", 1) <= 0)
    winner = 0 if k_home > k_away else (1 if k_away > k_home else -1)
    return {"seed": seed, "k_home": k_home, "k_away": k_away, "turns": turns, "winner": winner}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.seeds = min(args.seeds, 20)

    # Example: mirror comp (same class set vs itself)
    comp = ["Fighter","Ranger","Wizard","Cleric","Rogue"]  # tweak comp here per pass
    results: List[Dict[str,Any]] = []
    for s in range(args.seeds):
        results.append(run_match(10_000 + s, comp, comp))

    # aggregate
    wins = sum(1 for r in results if r["winner"] == 0)
    losses = sum(1 for r in results if r["winner"] == 1)
    draws = len(results) - wins - losses
    avg_k = statistics.mean((r["k_home"] + r["k_away"]) / 2 for r in results)
    avg_turns = statistics.mean(r["turns"] for r in results)

    print(f"[batch] seeds={args.seeds}  W/L/D={wins}/{losses}/{draws}  avg_kills={avg_k:.2f}  avg_turns={avg_turns:.1f}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
