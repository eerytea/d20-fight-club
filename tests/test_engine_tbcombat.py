# tests/test_engine_tbcombat.py
from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles

GRID_W, GRID_H = 10, 8

def make_team_dict(name: str, team_id: int):
    # Minimal helper used only by this test; weapon has reach to exercise movement/attack
    color = (100 + team_id*10, 120, 160)
    fighters = []
    base_stats = [
        {"name": f"{name} A", "str": 14, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 10},
        {"name": f"{name} B", "str": 12, "dex": 14, "con": 12, "int": 10, "wis": 10, "cha": 10},
        {"name": f"{name} C", "str": 13, "dex": 13, "con": 12, "int": 10, "wis": 10, "cha": 10},
        {"name": f"{name} D", "str": 12, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 10},
    ]
    for i, st in enumerate(base_stats, start=1):
        f = {
            "fighter_id": team_id*100 + i,
            "team_id": team_id,
            "level": 1,
            "ac": 12,
            "hp": 10,
            "max_hp": 10,
            **st,
            "weapon": {"name": "Spear", "damage": "1d6", "to_hit_bonus": 1, "reach": 2},
        }
        fighters.append(f)
    return {"name": name, "color": color, "fighters": fighters}

def test_tbcombat_completes_and_awards_xp():
    tH = make_team_dict("Alpha", 0)
    tA = make_team_dict("Bravo", 1)

    teamA = Team(0, tH["name"], tuple(tH["color"]))
    teamB = Team(1, tA["name"], tuple(tA["color"]))

    fighters = [fighter_from_dict({**fd, "team_id": 0}) for fd in tH["fighters"]] + \
               [fighter_from_dict({**fd, "team_id": 1}) for fd in tA["fighters"]]

    layout_teams_tiles(fighters, GRID_W, GRID_H)
    combat = TBCombat(teamA, teamB, fighters, GRID_W, GRID_H, seed=999)

    # run up to a cap so it must finish
    for _ in range(2000):
        if combat.winner is not None:
            break
        combat.take_turn()

    assert combat.winner in (0, 1), "Match should end with a winner"
    # someone should have gained XP by downing an enemy
    assert any(f.xp > 0 for f in fighters), "No XP was awarded on downs"
