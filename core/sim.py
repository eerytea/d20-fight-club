# core/sim.py
from __future__ import annotations
from typing import List
from .career import Career, Fixture
from .rng import mix

# Deterministic per-fixture result so tests are stable and fast.
def _deterministic_kills(seed: int, fx: Fixture) -> tuple[int, int]:
    # Mix career seed with fixture identity for reproducibility
    ident = f"W{fx.week}:{fx.home_id}-{fx.away_id}"
    r = mix(seed, ident)
    # Small-ish spread with some ties allowed
    k_home = (r >> 5) % 6 + ((r >> 13) & 1)  # 0..7
    k_away = (r >> 9) % 6 + ((r >> 17) & 1)  # 0..7
    return int(k_home), int(k_away)

def _play_fixture(car: Career, fx: Fixture) -> None:
    if fx.played:
        return
    kH, kA = _deterministic_kills(car.seed, fx)
    car.record_result(fx.id, kH, kA)

def simulate_week_ai(car: Career) -> None:
    """Simulate *all* fixtures in the current week, then advance the week."""
    # Play everything scheduled for this week
    for fx in list(car.fixtures_in_week()):
        _play_fixture(car, fx)
    # Move to next week once all current-week fixtures are played
    car.advance_week_if_done()

# Back-compat helpers (same behavior for now)
def simulate_week_full(car: Career) -> None:
    simulate_week_ai(car)

def simulate_week_full_except(car: Career, except_team_id: int | None = None) -> None:
    # If an except team is provided, skip their fixture in the week
    for fx in list(car.fixtures_in_week()):
        if except_team_id is not None and (fx.home_id == except_team_id or fx.away_id == except_team_id):
            continue
        _play_fixture(car, fx)
    car.advance_week_if_done()
