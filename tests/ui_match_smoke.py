# tests/test_ui_match_smoke.py
from __future__ import annotations
import pygame, pytest

MatchState = pytest.importorskip("ui.state_match").MatchState
Career = pytest.importorskip("core.career").Career

def _init_pygame_headless():
    pygame.init(); pygame.display.init(); pygame.font.init()

class _AppStub:
    def __init__(self, screen, career):
        self.screen = screen
        self.career = career
        self.stack = []
    def push_state(self, s): self.stack.append(s)
    def pop_state(self): 
        if self.stack: self.stack.pop()

def _run_state_frames(state, screen, frames=2):
    for _ in range(frames):
        state.update(0.016)
        state.draw(screen)

def test_match_state_finishes_and_saves_result():
    _init_pygame_headless()
    try:
        screen = pygame.display.set_mode((900, 620))
        car = Career.new(seed=5, n_teams=4, team_size=3, user_team_id=0)
        app = _AppStub(screen, car)

        # Grab user's fixture for week 1
        fx = None
        for f in car.fixtures_for_week(1):
            if str(f["home_id"]) == str(car.user_tid) or str(f["away_id"]) == str(car.user_tid):
                fx = f; break
        assert fx is not None, "No user fixture in week 1?"

        # Start match and then finish immediately
        m = MatchState(app, car, fixture=fx, grid_w=9, grid_h=9)
        _run_state_frames(m, screen, frames=2)
        # Call the Finish action directly
        m._finish()

        # Fixture should now be marked played
        fx2 = [f for f in car.fixtures_for_week(1) if f["home_id"]==fx["home_id"] and f["away_id"]==fx["away_id"]][0]
        assert fx2.get("played") is True
    finally:
        pygame.quit()
