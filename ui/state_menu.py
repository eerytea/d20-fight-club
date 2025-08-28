# ui/state_menu.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Callable, List, Optional, Any

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
    text: str
    action: Callable[[], None]
    hover: bool = False
    disabled: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        bg = (58, 60, 70) if not self.hover else (76, 78, 90)
        if self.disabled:
            bg = (48, 48, 54)
        pygame.draw.rect(surface, bg, self.rect, border_radius=10)
        pygame.draw.rect(surface, (24, 24, 28), self.rect, width=2, border_radius=10)
        txt = font.render(self.text, True, (230, 230, 235) if not self.disabled else (150, 150, 155))
        surface.blit(txt, (self.rect.x + 16, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle(self, event: pygame.event.Event):
        if self.disabled:
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
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
        def _mk(name, tid, size=4):
            return {"tid": tid, "name": name,
                    "fighters": [{"pid": i, "name": f"{name[:1]}{i}", "team_id": tid,
                                  "hp": 8, "max_hp": 8, "ac": 9, "alive": True,
                                  "STR": 11 + (i % 2), "DEX": 10 + ((i + 1) % 2),
                                  "CON": 10, "INT": 8, "WIS": 8, "CHA": 8} for i in range(size)]}
        home = _mk("Home", 0); away = _mk("Away", 1)
        try:
            st = MatchState(self.app, home, away)
        except TypeError:
            mini = type("MiniCareer", (), {})()
            mini.teams = [home, away]; mini.week = 1; mini.user_tid = None; mini.seed = 1337
            def _tn(tid):
                for t in mini.teams:
                    if int(t.get("tid", -1)) == int(tid): return t.get("name", f"Team {tid}")
                return f"Team {tid}"
            mini.team_name = _tn
            st = MatchState(self.app, mini, {"home_id": 0, "away_id": 1, "played": False})
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

    def handle(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.on_quit(); return
        for b in self.buttons:
            b.handle(event)

    def update(self, dt: float):
        if self._toast_text:
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

        pygame.draw.rect(screen, (38, 40, 48), self.panel, border_radius=16)
        pygame.draw.rect(screen, (24, 24, 28), self.panel, 2, border_radius=16)

        for b in self.buttons:
            b.draw(screen, self.font)

        if self._toast_text:
            self._draw_toast(screen, self._toast_text)

    def _toast(self, text: str, seconds: float = 2.0):
        self._toast_text = text
        self._toast_t = seconds

    def _draw_toast(self, screen: pygame.Surface, text: str):
        w, h = screen.get_size()
        font = pygame.font.SysFont(None, 24)
        surf = font.render(text, True, (240, 240, 245))
        pad = 12
        rect = pygame.Rect(0, 0, surf.get_width() + pad*2, surf.get_height() + pad*2)
        rect.centerx = w // 2
        rect.y = h - rect.height - 24
        pygame.draw.rect(screen, (56, 58, 66), rect, border_radius=10)
        pygame.draw.rect(screen, (24, 24, 28), rect, 2, border_radius=10)
        screen.blit(surf, (rect.x + pad, rect.y + pad))
