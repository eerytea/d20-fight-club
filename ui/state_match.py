# ui/state_match.py
from __future__ import annotations

import pygame
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, Any, List

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel

# --- Import TBCombat & helpers, but be resilient if some symbols are missing ---
from engine.tbcombat import TBCombat  # core class should exist

# Optional imports with fallbacks (to tolerate API differences across branches)
try:
    from engine.tbcombat import Team as TBTeam  # preferred
except Exception:
    @dataclass
    class TBTeam:  # minimal compatibility shim
        tid: int
        name: str
        color: tuple[int, int, int]

# fighter_from_dict may not exist on your local branch — provide a robust fallback
try:
    from engine.tbcombat import fighter_from_dict as _fighter_from_dict
except Exception:
    def _fighter_from_dict(fd: Dict[str, Any]):
        """
        Convert a plain fighter dict into a SimpleNamespace that looks like
        what TBCombat expects (attributes instead of dict keys).
        We keep the original dict fields and add safe defaults.
        """
        d = dict(fd)

        # IDs & names
        pid = d.get("pid") or d.get("id") or d.get("name") or "F"
        d.setdefault("pid", str(pid))
        d.setdefault("name", f"{d['pid']}")

        # Team & class info
        d.setdefault("team_id", d.get("team") or 0)
        d.setdefault("class", d.get("cls") or d.get("class_", "Fighter"))
        d.setdefault("level", d.get("level", d.get("lvl", 1)))

        # Core combat stats (very conservative defaults)
        d.setdefault("hp", d.get("hp", 12))
        d.setdefault("max_hp", d.get("max_hp", d["hp"]))
        d.setdefault("ac", d.get("ac", 10))
        d.setdefault("atk", d.get("atk", 2))
        d.setdefault("alive", d.get("alive", True))
        d.setdefault("xp", d.get("xp", 0))

        # Position
        d.setdefault("x", d.get("x", 0))
        d.setdefault("y", d.get("y", 0))

        return SimpleNamespace(**d)

# Optional layout helper
try:
    from engine.tbcombat import layout_teams_tiles as _layout_teams_tiles
except Exception:
    _layout_teams_tiles = None

# Grid size (fallback if not exported)
try:
    from engine.tbcombat import GRID_W as _GRID_W, GRID_H as _GRID_H
except Exception:
    _GRID_W, _GRID_H = 15, 9  # safe defaults


class MatchState(BaseState):
    """
    Minimal match viewer:
      - Builds TBCombat from team dicts
      - Step / Auto buttons
      - Shows a rolling text log
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
        th = TBTeam(self.home_d["tid"], self.home_d.get("name", "Home"),
                    tuple(self.home_d.get("color", (180, 180, 220))))
        ta = TBTeam(self.away_d["tid"], self.away_d.get("name", "Away"),
                    tuple(self.away_d.get("color", (220, 180, 180))))

        # Build fighter list (ensure team_id is attached)
        h_roster = self.home_d.get("fighters") or self.home_d.get("roster") or []
        a_roster = self.away_d.get("fighters") or self.away_d.get("roster") or []
        fighters = [_fighter_from_dict({**fd, "team_id": th.tid}) for fd in h_roster]
        fighters += [_fighter_from_dict({**fd, "team_id": ta.tid}) for fd in a_roster]

        # Place fighters on grid
        if _layout_teams_tiles:
            _layout_teams_tiles(fighters, _GRID_W, _GRID_H)
        else:
            # crude fallback: left/right columns with spacing
            y = 1
            for f in fighters:
                if getattr(f, "team_id", th.tid) == th.tid:
                    f.x, f.y = 1, y
                else:
                    f.x, f.y = _GRID_W - 2, y
                y = 1 if y >= _GRID_H - 2 else y + 2

        # start combat
        self.combat = TBCombat(th, ta, fighters, _GRID_W, _GRID_H, seed=42)
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
        if self.combat and self.combat.winner is None:
            self._tick_once()

    def _toggle_auto(self):
        self.auto = not self.auto
        if self.btn_auto:
            self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"

    def _back(self):
        self.app.pop_state()

    def _tick_once(self):
        assert self.combat is not None
        self.combat.take_turn()

        # Prefer typed events if available; else legacy strings
        evs = getattr(self.combat, "events_typed", None)
        if evs:
            try:
                from engine.events import format_event
                new_lines = [format_event(e) for e in evs[-4:]]
            except Exception:
                new_lines = [str(e) for e in evs[-4:]]
        else:
            new_lines = [str(s) for s in getattr(self.combat, "events", [])[-4:]]

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
            wtxt = {
                "home": self.home_d.get("name", "Home"),
                "away": self.away_d.get("name", "Away"),
                "draw": "Draw",
                0: self.home_d.get("name", "Home"),
                1: self.away_d.get("name", "Away"),
            }.get(self.combat.winner, str(self.combat.winner))
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
