# tests/test_grid_layout.py
from engine import layout_teams_tiles, fighter_from_dict, Team
from engine.model import Fighter

def test_layout_in_bounds_and_separated():
    GRID_W, GRID_H = 10, 8
    # minimal 2 fighters per side
    roster = []
    for tid in (0, 1):
        for i in range(2):
            roster.append(fighter_from_dict({
                "fighter_id": tid*100+i, "team_id": tid, "name": f"T{tid}-{i}",
                "hp": 8, "max_hp": 8, "ac": 12, "str": 12, "dex": 12, "con": 12,
                "weapon": {"name": "Dagger", "damage": "1d4", "reach": 1}
            }))
    layout_teams_tiles(roster, GRID_W, GRID_H)
    for f in roster:
        assert 0 <= f.tx < GRID_W and 0 <= f.ty < GRID_H
    # check teams on different halves (roughly)
    left_half = all(f.tx <= GRID_W//2 for f in roster if f.team_id == 0)
    right_half = all(f.tx >= GRID_W//2 for f in roster if f.team_id == 1)
    assert left_half and right_half
