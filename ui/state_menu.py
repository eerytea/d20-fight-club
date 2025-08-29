# ui/state_menu.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Callable, List, Optional

def _import_opt(fullname: str):
    try:
        module_name, class_name = fullname.rsplit(".", 1)
        mod = __import__(module_name, fromlist=[class_name])
        return getattr(mod, class_name)
    except Exception:
        return None

@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: Callable[[], None]
    disabled: bool = False
    hover: bool = False

    def draw(self, screen):
        if pygame is None: return
        bg = (60, 60, 72)
        if self.hover and not self.disabled:
            bg = (80, 80, 95)
        if self.disabled:
            bg = (40, 40, 48)
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, (24, 24, 28), self.rect, 2, border_radius=8)
        font = pygame.font.SysFont(None, 24)
        color = (235, 235, 240) if not self.disabled else (160, 160, 165)
        txt = font.render(self.label, True, color)
        screen.blit(txt, (self.rect.x + 14, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle(self, ev):
        if pygame is None or self.disabled: return
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.action()

class MenuState:
    def __init__(self, app):
        self.app = app
        self.font = pygame.font.SysFont(None, 28)
        self.h1 = pygame.font.SysFont(None, 40)

        w, h = self.app.screen.get_size()
        self.margin = 24
        self.panel = pygame.Rect(self.margin, 100, max(420, int(w*0.35)), h - 2*self.margin - 100)

        btn_w, btn_h, gap = 320, 52, 18
        x = self.panel.x + 36
        y = self.panel.y + 36
        self.buttons: List[Button] = []

        def add_button(label: str, cb, disabled: bool=False):
            nonlocal y
            b = Button(pygame.Rect(x, y, btn_w, btn_h), label, cb, disabled=disabled)
            self.buttons.append(b)
            y += btn_h + gap

        add_button("New Season", self.on_new_season)
        add_button("Exhibition", self.on_exhibition)
        add_button("Load", self.on_load)
        add_button("Settings", self.on_settings)
        add_button("Quit", self.on_quit)

        self._toast_text: Optional[str] = None
        self._toast_t: float = 0.0

    # ---------------- actions ----------------
    def _toast(self, msg: str):
        self._toast_text = msg; self._toast_t = 2.2

    def on_new_season(self):
        TeamSelectState = _import_opt("ui.state_team_select.TeamSelectState")
        if TeamSelectState is None:
            self._toast("Team Select screen missing.")
            return
        self.app.push_state(TeamSelectState(self.app))

    def on_exhibition(self):
        MatchState = _import_opt("ui.state_match.MatchState")
        if MatchState is None:
            self._toast("Match screen not implemented.")
            return
        # Wrap two quick teams in a tiny Career-like object so MatchState gets what it expects.
        def _mk(name, tid, size=4):
            return {"tid": tid, "name": name,
                    "fighters": [{"pid": i, "name": f"{name[:1]}{i}", "team_id": tid,
                                  "hp": 8, "max_hp": 8, "ac": 9, "alive": True,
                                  "STR": 11 + (i % 2), "DEX": 10 + ((i + 1) % 2),
                                  "CON": 10, "INT": 8, "WIS": 8, "CHA": 8} for i in range(size)]}
        home = _mk("Home", 0); away = _mk("Away", 1)

        mini = type("MiniCareer", (), {})()
        mini.teams = [home, away]; mini.week = 1; mini.user_tid = None; mini.seed = 1337
        def _tn(tid):
            for t in mini.teams:
                if int(t.get("tid", -1)) == int(tid): return t.get("name", f"Team {tid}")
            return f"Team {tid}"
        mini.team_name = _tn

        fixture = {"home_id": 0, "away_id": 1, "played": False}
        st = MatchState(self.app, mini, fixture)
        self.app.push_state(st)

    def on_load(self):
        SaveLoadState = _import_opt("ui.state_save_load.SaveLoadState")
        if SaveLoadState is None:
            self._toast("Load screen coming soon.")
            return
        self.app.push_state(SaveLoadState(self.app))

    def on_settings(self):
        SettingsState = _import_opt("ui.state_settings.SettingsState")
        if SettingsState is None:
            self._toast("Settings screen missing.")
            return
        self.app.push_state(SettingsState(self.app))

    def on_quit(self):
        self.app.running = False

    # --------------- event/update/draw ---------------
    def handle(self, ev):
        if pygame is None: return
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
            self.on_quit(); return
        for b in self.buttons:
            b.handle(ev)

    def update(self, dt):
        if self._toast_t > 0:
            self._toast_t -= dt
            if self._toast_t <= 0:
                self._toast_text = None

    def draw(self, screen: pygame.Surface):
        w, h = screen.get_size()
        screen.fill((18, 18, 22))

        head = pygame.Rect(16, 18, w - 32, 64)
        pygame.draw.rect(screen, (42, 44, 52), head, border_radius=12)
        pygame.draw.rect(screen, (24, 24, 28), head, 2, border_radius=12)
        title = self.h1.render("D20 Fight Club", True, (235, 235, 240))
        screen.blit(title, (head.x + 24, head.y + (head.h - title.get_height()) // 2))

        pygame.draw.rect(screen, (42, 44, 52), self.panel, border_radius=12)
        pygame.draw.rect(screen, (24, 24, 28), self.panel, 2, border_radius=12)

        for b in self.buttons:
            b.draw(screen)

        if self._toast_text:
            toast = self.font.render(self._toast_text, True, (255, 210, 120))
            screen.blit(toast, (self.panel.x, self.panel.bottom + 8))
