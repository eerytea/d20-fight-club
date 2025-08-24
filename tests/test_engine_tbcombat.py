# tests/test_engine_tbcombat.py
import random
from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles
from core.creator import generate_fighter
from core.ratings import refresh_fighter_ratings

GRID_W, GRID_H = 12, 8

def make_team_dict(name, tid, size=4, seed=1234):
    r = random.Random(seed + tid)
    fighters = [generate_fighter(level=1, rng=r, class_mode="weighted", misfit_prob=0.05) for _ in range(size)]
    for f in fighters:
        refresh_fighter_ratings(f)
    return {"tid": tid, "name": name, "color": [120, 180, 255] if tid==0 else [255, 140, 140], "fighters": fighters}

def test_tbcombat_completes_and_awards_xp():
    tH = make_team_dict("Alpha", 0)
    tA = make_team_dict("Bravo", 1)
    # build engine objects
    teamA = Team(0, tH["name"], tuple(tH["color"]))
    teamB = Team(1, tA["name"], tuple(tA["color"]))
    fighters = [fighter_from_dict({**fd, "team_id":0}) for fd in tH["fighters"]] + \
               [fighter_from_dict({**fd, "team_id":1}) for fd in tA["fighters"]]
    layout_teams_tiles(fighters, GRID_W, GRID_H)
    combat = TBCombat(teamA, teamB, fighters, GRID_W, GRID_H, seed=999)

    # run up to a cap
    for _ in range(2000):
        if combat.winner is not None:
            break
        combat.take_turn()

    assert combat.winner in (0, 1, -1)  # someone won or both down
    # ensure at least some XP was assigned to living fighters
    alive = [f for f in fighters if getattr(f, "alive", False)]
    assert any(getattr(f, "xp", 0) > 0 for f in alive + [fighters[0]])  # allow all dead edge case
