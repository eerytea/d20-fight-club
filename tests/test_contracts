from __future__ import annotations
from typing import Dict, Any, List

from core.adapters import as_fighter_dict, as_fixture_dict, as_result_dict
from core.contracts import (
    FIGHTER_KEYS_REQ, FIXTURE_KEYS_REQ, RESULT_KEYS_REQ,
)

def test_fighter_adapter_minimal():
    raw = {"id": 7, "name": "Unit", "HP": 9, "HP_max": 9, "AC": 11}
    f = as_fighter_dict(raw, default_team_id=1, default_pid=7)
    for k in FIGHTER_KEYS_REQ:
        assert k in f
    assert f["pid"] == 7
    assert f["team_id"] == 1
    assert f["hp"] == 9
    assert f["max_hp"] == 9
    assert f["ac"] == 11
    assert f["alive"] is True

def test_fixture_adapter_minimal():
    raw = {"week": 3, "home_tid": 2, "away_tid": 5}
    fx = as_fixture_dict(raw)
    for k in FIXTURE_KEYS_REQ:
        assert k in fx
    assert fx["week"] == 3
    assert fx["home_id"] == 2
    assert fx["away_id"] == 5
    assert fx["played"] is False
    assert fx["comp_kind"] == "league"

def test_result_adapter_minimal():
    raw = {"A": 1, "B": 9, "k_home": 2, "k_away": 2, "winner": None}
    r = as_result_dict(raw)
    for k in RESULT_KEYS_REQ:
        assert k in r
    assert r["home_id"] == 1
    assert r["away_id"] == 9
    assert r["k_home"] == 2
    assert r["k_away"] == 2
    assert r["winner"] is None
