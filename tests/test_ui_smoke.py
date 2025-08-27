# tests/test_ui_smoke.py
from __future__ import annotations
import pygame, pytest

MenuState = pytest.importorskip("ui.state_menu").MenuState
SeasonHubState = pytest.importorskip("ui.state_season_hub").SeasonHubState
TableState = pytest.importorskip("ui.state_table").TableState
RosterState = pytest.importorskip("ui.state_roster").RosterState
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
    def set_toast(self, *a, **k): pass

def _run_state_frames(state, screen, frames=2):
    for _ in range(frames):
        state.update(0.016)
        state.draw(screen)

def test_ui_menu_hub_table_roster_smoke():
    _init_pygame_headless()
    try:
        screen = pygame.display.set_mode((900, 620))
        career = Career.new(seed=1, n_teams=6, team_size=3, user_team_id=0)
        app = _AppStub(screen, career)

        menu = MenuState(app); app.push_state(menu); _run_state_frames(menu, screen)
        hub = SeasonHubState(app, career); app.push_state(hub); _run_state_frames(hub, screen)
        table = TableState(app, career); app.push_state(table); _run_state_frames(table, screen)
        app.pop_state()
        roster = RosterState(app, career, tid=getattr(career, "user_tid", 0))
        app.push_state(roster); _run_state_frames(roster, screen)
        assert True
    finally:
        pygame.quit()
