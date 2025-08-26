# ui/state_match.py
from __future__ import annotations

import pygame
from typing import Dict, Any, List

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel

from engine.tbcombat import (
    Team, TBCombat, fighter_from_dict, layout_teams_tiles,
    GRID_W, GRID_H
)


class MatchState(BaseState):
    """
    Minimal match viewer:
      - Builds TBCombat from team dicts
      - Step / Auto buttons
      - Shows last ~12 events as text
    """
    def __init__(self, app, home_team: Dict[str, Any], away_team: Dict[str, Any]):
        self.app = app
        self.theme = Theme()

        self.home_d = home_team
        self.away_d = away_team

        self.combat: TBCombat | None = None
        self.auto = False
        self._built = False

        self.btn_step: Button | None = None
        self.btn_auto: Button | None = None
        self.btn_back: Button | None = None

        self.events: List[str] = []

    def enter(self) -> None:
        self._build_match()
        self._build_ui()

    # --- setup ---------------------------------------------------------------
    def _build_match(self):
        # Build Team objects
        th = Team(self.home_d["tid"], self.home_d["name"], tuple(self.home_d.get("color", (180,180,220))))
        ta = Team(self.away_d["tid"], self.away_d["name"], tuple(self.away_d.get("color", (220,180,180))))

        # Build fighter list (mix both teams)
        fighters = [fighter_from_dict({**fd, "team_id": th.tid}) for fd in self.home_d.get("fighters") or self.home_d.get("roster", [])]
        fighters += [fighter_from_dict({**fd, "team_id": ta.tid}) for fd in self.away_d.get("fighters") or self.away_d.get("roster", [])]

        layout_teams_tiles(fighters, GRID_W, GRID_H)
        self.combat = TBCombat(th, ta, fighters, GRID_W, GRID_H, seed=42)
        self.events = []

    def _build_ui(self):
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)

        btn_w, btn_h, gap = 140, 42, 10
        y = self.rect_panel.bottom - (btn_h + 10)
        self.btn_step = Button(pygame.Rect(self.rect_panel.x + 12, y, btn_w, btn_h), "Step", self._step)
        self.btn_auto = Button(pygame.Rect(self.rect_panel.x + 12 + btn_w + gap, y, btn_w, btn_h), "Auto: OFF", self._toggle_auto)
        self.btn_back = Button(pygame.Rect(self.rect_panel.right - (btn_w + 12), y, btn_w, btn_h), "Back", self._back)
        self._built = True

    # --- actions -------------------------------------------------------------
    def _step(self):
        if not self.combat:
            return
        if self.combat.winner is None:
            self._tick_once()

    def _toggle_auto(self):
        self.auto = not self.auto
        if self.btn_auto:
            self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"

    def _back(self):
        self.app.pop_state()

    def _tick_once(self):
        # advance one micro-turn; TBCombat appends to events (strings or typed)
        self.combat.take_turn()
        # Prefer typed if present; else legacy strings
        evs = getattr(self.combat, "events_typed", None)
        if evs:
            # best-effort use of formatter (works with our minimal engine/events)
            try:
                from engine.events import format_event
                new_lines = [format_event(e) for e in evs[-4:]]  # just tail
            except Exception:
                new_lines = [str(e) for e in evs[-4:]]
        else:
            new_lines = [str(s) for s in self.combat.events[-4:]]

        # keep last ~12 lines
        self.events.extend(new_lines)
        if len(self.events) > 40:
            self.events = self.events[-40:]

    # --- state iface ---------------------------------------------------------
    def handle(self, event) -> None:
        if not self._built:
            return
        self.btn_step.handle(event)
        self.btn_auto.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        if not self._built:
            self.enter(); return
        mx, my = pygame.mouse.get_pos()
        self.btn_step.update((mx, my))
        self.btn_auto.update((mx, my))
        self.btn_back.update((mx, my))

        if self.auto and self.combat and self.combat.winner is None:
            # advance several steps per frame so matches complete
            for _ in range(8):
                if self.combat.winner is not None:
                    break
                self._tick_once()

    def draw(self, surf) -> None:
        if not self._built:
            self.enter()
        th = self.theme
        surf.fill(th.bg)

        title = f"{self.home_d.get('name','Home')} vs {self.away_d.get('name','Away')}"
        draw_text(surf, title, (surf.get_width() // 2, 16), 30, th.text, align="center")

        draw_panel(surf, self.rect_panel, th)

        # Winner/status line
        status_y = self.rect_panel.y + 10
        if self.combat and self.combat.winner is not None:
            wtxt = {"home": self.home_d.get("name","Home"), "away": self.away_d.get("name","Away"), "draw": "Draw"}.get(self.combat.winner, str(self.combat.winner))
            draw_text(surf, f"Winner: {wtxt}", (self.rect_panel.x + 12, status_y), 22, th.text)
        else:
            draw_text(surf, "Running…", (self.rect_panel.x + 12, status_y), 22, th.subt)

        # Event log (tail)
        y = status_y + 30
        for line in self.events[-18:]:
            draw_text(surf, line, (self.rect_panel.x + 12, y), 18, th.text)
            y += 20

        self.btn_step.draw(surf, th)
        self.btn_auto.draw(surf, th)
        self.btn_back.draw(surf, th)
