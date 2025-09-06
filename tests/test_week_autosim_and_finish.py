# tests/test_week_autosim_and_finish.py
import pygame
from ui.app import App
from ui.state_match import MatchState
from core.creator import create_new_career   # if your API is different, tell me the constructor you use
from core.config import SAVE_DIR

def _blit_frames(state, screen, frames=2):
    # minimal advance frames like your other tests
    for _ in range(frames):
        state.update(0.016)
        state.draw(screen)
        pygame.display.flip()

def test_non_user_autosim_and_finish(tmp_path, monkeypatch):
    pygame.init()
    try:
        # Build a mini career with user team 0 (adjust if your factory differs)
        car = create_new_career(num_teams=6, seed=42, user_tid=0)
        app = App(width=640, height=360, title="test")
        screen = app.screen

        # Week 1 user fixture present?
        fixtures = car.fixtures_for_week(1)
        fx = next((f for f in fixtures if f["home_id"] == car.user_tid or f["away_id"] == car.user_tid), None)
        assert fx is not None, "Expected a user fixture in week 1"

        # Enter match state, tick a couple frames, then finish immediately
        m = MatchState(app, car, fixture=fx, grid_w=16, grid_h=16)
        _blit_frames(m, screen, frames=2)
        m._finish()

        # Fixture should be marked played
        fx2 = [f for f in car.fixtures_for_week(1)
               if f["home_id"]==fx["home_id"] and f["away_id"]==fx["away_id"]][0]
        assert fx2.get("played") is True
    finally:
        pygame.quit()
