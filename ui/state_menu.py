from __future__ import annotations

import pygame
from pygame import Rect

# ---- Optional real UI kit ----
try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=8)
            font = pygame.font.SysFont("arial", 20)
            screen.blit(font.render(self.label, True, (255,255,255) if self.enabled else (170,170,170)),
                        (self.rect.x+14, self.rect.y+8))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=24):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=10)

# ---- Child states ----
try:
    from ui.state_season_hub import SeasonHubState
except Exception:
    SeasonHubState = None
try:
    from ui.state_roster import RosterState
except Exception:
    RosterState = None
try:
    from ui.state_exhibition_picker import ExhibitionPickerState
except Exception:
    ExhibitionPickerState = None
try:
    from ui.state_settings import SettingsState
except Exception:
    SettingsState = None
try:
    from core.usecases.states.state_reputation import ReputationState
except Exception:
    ReputationState = None
try:
    from ui.state_save_load import SaveLoadState
except Exception:
    SaveLoadState = None
try:
    from ui.state_team_select import TeamSelectState
except Exception:
    TeamSelectState = None
try:
    from ui.state_training import TrainingState
except Exception:
    TrainingState = None

# ---- Career (for default/new career) ----
try:
    from core.career import Career
except Exception:
    Career = None


class MenuState:
    """
    Main Menu:
      - Season
      - Exhibition
      - Roster
      - Save / Load
      - Team Select
      - Training
      - Reputation
      - Settings
      - Quit
    """
    def __init__(self, app):
        self.app = app
        self.rc_title = Rect(20, 20, 860, 80)
        self.rc_menu  = Rect(20, 120, 860, 460)

        # Build buttons
        x, y = self.rc_menu.x + 40, self.rc_menu.y + 20
        w, h, gap = 260, 44, 14

        self.btn_season = Button(Rect(x, y, w, h), "Season", self._open_season); y += h + gap
        self.btn_exhib  = Button(Rect(x, y, w, h), "Exhibition", self._open_exhibition); y += h + gap
        self.btn_roster = Button(Rect(x, y, w, h), "Roster", self._open_roster); y += h + gap
        self.btn_savel  = Button(Rect(x, y, w, h), "Save / Load", self._open_saveload); y += h + gap
        self.btn_select = Button(Rect(x, y, w, h), "Team Select", self._open_team_select); y += h + gap
        self.btn_train  = Button(Rect(x, y, w, h), "Training", self._open_training); y += h + gap
        self.btn_rep    = Button(Rect(x, y, w, h), "Reputation", self._open_reputation); y += h + gap
        self.btn_setts  = Button(Rect(x, y, w, h), "Settings", self._open_settings); y += h + gap
        self.btn_quit   = Button(Rect(x, y, w, h), "Quit", self._quit)

        self._buttons = [
            self.btn_season, self.btn_exhib, self.btn_roster, self.btn_savel,
            self.btn_select, self.btn_train, self.btn_rep, self.btn_setts, self.btn_quit
        ]

    # ---------------- events ----------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._quit(); return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_title)
        draw_text(screen, "D20 Fight Club", self.rc_title.x + 20, self.rc_title.y + 22, size=28)

        panel(screen, self.rc_menu, color=(24,24,28))
        for b in self._buttons:
            b.draw(screen)

    # ---------------- actions ----------------
    def _ensure_career(self):
        career = getattr(self.app, "career", None)
        if career is None and Career is not None:
            self.app.career = Career.new(seed=12345, n_teams=20, team_size=5, user_team_id=0)
        return getattr(self.app, "career", None)

    def _open_season(self):
        car = self._ensure_career()
        if SeasonHubState is not None and car is not None:
            self.app.push_state(SeasonHubState(self.app, car))

    def _open_exhibition(self):
        car = self._ensure_career()
        if ExhibitionPickerState is not None and car is not None:
            self.app.push_state(ExhibitionPickerState(self.app, car))

    def _open_roster(self):
        car = self._ensure_career()
        if RosterState is not None and car is not None:
            tid = getattr(car, "user_tid", 0)
            self.app.push_state(RosterState(self.app, car, tid=tid))

    def _open_saveload(self):
        if SaveLoadState is not None:
            self.app.push_state(SaveLoadState(self.app))

    def _open_team_select(self):
        car = self._ensure_career()
        if TeamSelectState is not None and car is not None:
            self.app.push_state(TeamSelectState(self.app, car))

    def _open_training(self):
        car = self._ensure_career()
        if TrainingState is not None and car is not None:
            tid = getattr(car, "user_tid", 0)
            self.app.push_state(TrainingState(self.app, car, tid=tid))

    def _open_reputation(self):
        car = self._ensure_career()
        if ReputationState is not None and car is not None:
            self.app.push_state(ReputationState(self.app, car))

    def _open_settings(self):
        if SettingsState is not None:
            self.app.push_state(SettingsState(self.app))

    def _quit(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))
