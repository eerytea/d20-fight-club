# ui/state_match.py
from __future__ import annotations

import pygame
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, Any, List, Tuple

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel

# Core combat class (should exist)
from engine.tbcombat import TBCombat

# --- Optional engine symbols (tolerant to branch/API differences) -----------
try:
    from engine.tbcombat import Team as TBTeam  # ideal
except Exception:
    @dataclass
    class TBTeam:  # minimal compatibility shim
        tid: int
        name: str
        color: Tuple[int, int, int]

try:
    from engine.tbcombat import fighter_from_dict as _fighter_from_dict
except Exception:
    def _fighter_from_dict(fd: Dict[str, Any]):
        """Fallback: turn a dict into a fighter-like object."""
        d = dict(fd)
        d.setdefault("pid", str(d.get("pid") or d.get("id") or d.get("name") or "F"))
        d.setdefault("name", str(d.get("name") or d["pid"]))
        d.setdefault("team_id", d.get("team_id", d.get("team", 0)))
        d.setdefault("class", d.get("class", d.get("cls", "Fighter")))
        d.setdefault("level", int(d.get("level", d.get("lvl", 1))))
        d.setdefault("hp", int(d.get("hp", 12)))
        d.setdefault("max_hp", int(d.get("max_hp", d["hp"])))
        d.setdefault("ac", int(d.get("ac", 10)))
        d.setdefault("atk", int(d.get("atk", 2)))
        d.setdefault("alive", bool(d.get("alive", True)))
        d.setdefault("xp", int(d.get("xp", 0)))
        d.setdefault("x", int(d.get("x", 0)))
        d.setdefault("y", int(d.get("y", 0)))
        return SimpleNamespace(**d)

try:
    from engine.tbcombat import layout_teams_tiles as _layout_teams_tiles
except Exception:
    _layout_teams_tiles = None

try:
    from engine.tbcombat import GRID_W as _GRID_W, GRID_H as _GRID_H
except Exception:
    _GRID_W, _GRID_H = 15, 9  # sane defaults

# Optional typed events
try:
    from engine.events import format_event
except Exception:
    def format_event(e):  # noqa: N802
        return str(e)


class MatchState(BaseState):
    """
    Classic viewer:
      - Left: grid with fighters (colored dots), names, HP bars
      - Right: scrolling event log
      - Bottom buttons: Step, Auto, Finish, Back
    """
    def __init__(self, app, home_team: Dict[str, Any], away_team: Dict[str, Any]):
        self.app = app
        self.theme = Theme()

        self.home_d = home_team
        self.away_d = away_team

        self.combat: TBCombat | None = None
        self.fighters: List[Any] = []
        self.teamA: TBTeam | None = None
        self.teamB: TBTeam | None = None

        self.auto = False
        self._built = False

        # UI
        self.btn_step: Button | None = None
        self.btn_auto: Button | None = None
        self.btn_finish: Button | None = None
        self.btn_back: Button | None = None

        self.rect_panel: pygame.Rect | None = None
        self.rect_grid: pygame.Rect | None = None
        self.rect_log: pygame.Rect | None = None

        # Log handling
        self.events: List[str] = []
        self._last_typed_len = 0
        self._last_str_len = 0

        # Auto settings
        self._auto_steps_per_update = 256  # fast enough to finish quickly

    # --- Lifecycle -----------------------------------------------------------
    def enter(self) -> None:
        self._build_match()
        self._build_ui()

    # --- Build match from team dicts ----------------------------------------
    def _build_match(self):
        # Teams
        self.teamA = TBTeam(
            self.home_d["tid"],
            self.home_d.get("name", "Home"),
            tuple(self.home_d.get("color", (180, 180, 220))),
        )
        self.teamB = TBTeam(
            self.away_d["tid"],
            self.away_d.get("name", "Away"),
            tuple(self.away_d.get("color", (220, 180, 180))),
        )

        # Fighters
        h_roster = self.home_d.get("fighters") or self.home_d.get("roster") or []
        a_roster = self.away_d.get("fighters") or self.away_d.get("roster") or []
        self.fighters = [_fighter_from_dict({**fd, "team_id": self.teamA.tid}) for fd in h_roster]
        self.fighters += [_fighter_from_dict({**fd, "team_id": self.teamB.tid}) for fd in a_roster]

        # Place on grid
        if _layout_teams_tiles:
            _layout_teams_tiles(self.fighters, _GRID_W, _GRID_H)
        else:
            # Fallback: left vs right columns
            y = 1
            for f in self.fighters:
                if getattr(f, "team_id", self.teamA.tid) == self.teamA.tid:
                    f.x, f.y = 1, y
                else:
                    f.x, f.y = _GRID_W - 2, y
                y = 1 if y >= _GRID_H - 2 else y + 2

        # Start combat
        self.combat = TBCombat(self.teamA, self.teamB, self.fighters, _GRID_W, _GRID_H, seed=42)
        self.events.clear()
        self._last_typed_len = 0
        self._last_str_len = 0

    # --- UI layout -----------------------------------------------------------
    def _build_ui(self):
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)

        # Split: 62% grid / 38% log
        split = int(self.rect_panel.w * 0.62)
        self.rect_grid = pygame.Rect(self.rect_panel.x + 12, self.rect_panel.y + 12, split - 24, self.rect_panel.h - 84)
        self.rect_log = pygame.Rect(self.rect_panel.x + split, self.rect_panel.y + 12, self.rect_panel.w - split - 12, self.rect_panel.h - 84)

        # Buttons along bottom of panel
        btn_w, btn_h, gap = 140, 42, 10
        y = self.rect_panel.bottom - (btn_h + 10)
        x = self.rect_panel.x + 12
        self.btn_step = Button(pygame.Rect(x, y, btn_w, btn_h), "Step", self._step)
        x += btn_w + gap
        self.btn_auto = Button(pygame.Rect(x, y, btn_w, btn_h), "Auto: OFF", self._toggle_auto)
        x += btn_w + gap
        self.btn_finish = Button(pygame.Rect(x, y, btn_w, btn_h), "Finish", self._finish)
        # Back on far right
        self.btn_back = Button(pygame.Rect(self.rect_panel.right - (btn_w + 12), y, btn_w, btn_h), "Back", self._back)

        self._built = True

    # --- Buttons / actions ---------------------------------------------------
    def _step(self):
        if self.combat and self.combat.winner is None:
            self._tick_once()

    def _toggle_auto(self):
        self.auto = not self.auto
        if self.btn_auto:
            self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"

    def _finish(self):
        """Run to completion with a generous cap to avoid infinite loops."""
        if not self.combat or self.combat.winner is not None:
            return
        for _ in range(20000):
            if self.combat.winner is not None:
                break
            self._tick_once()

    def _back(self):
        self.app.pop_state()

    # --- Advancing and harvesting events ------------------------------------
    def _tick_once(self):
        assert self.combat is not None
        self.combat.take_turn()
        self._harvest_new_events()

    def _harvest_new_events(self):
        """Append only the new events since last harvest."""
        if not self.combat:
            return

        evs_t = getattr(self.combat, "events_typed", None)
        if evs_t is not None:
            fresh = evs_t[self._last_typed_len :]
            if fresh:
                for e in fresh:
                    try:
                        self.events.append(format_event(e))
                    except Exception:
                        self.events.append(str(e))
                self._last_typed_len += len(fresh)

        # Legacy string events (if present)
        evs_s = getattr(self.combat, "events", None)
        if evs_s is not None and isinstance(evs_s, list):
            fresh_s = evs_s[self._last_str_len :]
            if fresh_s:
                self.events.extend([str(s) for s in fresh_s])
                self._last_str_len += len(fresh_s)

        # Trim
        if len(self.events) > 400:
            self.events = self.events[-400:]

    # --- State interface -----------------------------------------------------
    def handle(self, event) -> None:
        if not self._built:
            return
        self.btn_step.handle(event)
        self.btn_auto.handle(event)
        self.btn_finish.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        if not self._built:
            self.enter(); return
        mx, my = pygame.mouse.get_pos()
        self.btn_step.update((mx, my))
        self.btn_auto.update((mx, my))
        self.btn_finish.update((mx, my))
        self.btn_back.update((mx, my))

        if self.auto and self.combat and self.combat.winner is None:
            # Advance a chunk each frame; usually enough to finish quickly
            for _ in range(self._auto_steps_per_update):
                if self.combat.winner is not None:
                    break
                self._tick_once()

    # --- Drawing -------------------------------------------------------------
    def draw(self, surf) -> None:
        if not self._built:
            self.enter()
        th = self.theme
        surf.fill(th.bg)

        # Title
        title = f"{self.home_d.get('name','Home')} vs {self.away_d.get('name','Away')}"
        draw_text(surf, title, (surf.get_width() // 2, 16), 30, th.text, align="center")

        # Panel and sub-panels
        draw_panel(surf, self.rect_panel, th)
        draw_panel(surf, self.rect_grid, th)
        draw_panel(surf, self.rect_log, th)

        # Winner/status
        status_y = self.rect_panel.y + 16
        if self.combat and self.combat.winner is not None:
            wmap = {
                "home": self.home_d.get("name", "Home"),
                "away": self.away_d.get("name", "Away"),
                "draw": "Draw",
                0: self.home_d.get("name", "Home"),
                1: self.away_d.get("name", "Away"),
            }
            wtxt = wmap.get(self.combat.winner, str(self.combat.winner))
            draw_text(surf, f"Winner: {wtxt}", (self.rect_panel.x + 16, status_y), 22, th.text)
        else:
            draw_text(surf, "Status: Running" if self.auto else "Status: Paused", (self.rect_panel.x + 16, status_y), 22, th.subt)

        # Grid
        self._draw_grid(surf)
        # Log
        self._draw_log(surf)

        # Buttons
        self.btn_step.draw(surf, th)
        self.btn_auto.draw(surf, th)
        self.btn_finish.draw(surf, th)
        self.btn_back.draw(surf, th)

    def _draw_grid(self, surf: pygame.Surface) -> None:
        if not (self.rect_grid and self.fighters):
            return

        rg = self.rect_grid
        gw, gh = _GRID_W, _GRID_H

        # cell size
        cell_w = max(12, (rg.w - 12) // gw)
        cell_h = max(12, (rg.h - 12) // gh)
        origin_x = rg.x + (rg.w - cell_w * gw) // 2
        origin_y = rg.y + (rg.h - cell_h * gh) // 2

        # grid lines
        for x in range(gw + 1):
            X = origin_x + x * cell_w
            pygame.draw.line(surf, self.theme.panel_border, (X, origin_y), (X, origin_y + gh * cell_h), 1)
        for y in range(gh + 1):
            Y = origin_y + y * cell_h
            pygame.draw.line(surf, self.theme.panel_border, (origin_x, Y), (origin_x + gw * cell_w, Y), 1)

        # draw fighters
        for f in self.fighters:
            x, y = int(getattr(f, "x", 0)), int(getattr(f, "y", 0))
            cx = origin_x + x * cell_w + cell_w // 2
            cy = origin_y + y * cell_h + cell_h // 2

            # color by team; dim if down
            team_id = getattr(f, "team_id", self.teamA.tid if self.teamA else 0)
            base = (self.teamA.color if self.teamA and team_id == self.teamA.tid
                    else self.teamB.color if self.teamB and team_id == self.teamB.tid
                    else (200, 200, 200))
            alive = bool(getattr(f, "alive", True))
            color = base if alive else (110, 110, 110)

            # dot
            radius = max(6, min(cell_w, cell_h) // 3)
            pygame.draw.circle(surf, color, (cx, cy), radius)
            pygame.draw.circle(surf, self.theme.panel_border, (cx, cy), radius, 1)

            # name
            name = str(getattr(f, "name", getattr(f, "pid", "F")))
            draw_text(surf, name, (cx, cy + radius + 2), 16, self.theme.text, align="center")

            # HP bar
            hp = max(0, int(getattr(f, "hp", 0)))
            mh = max(1, int(getattr(f, "max_hp", max(hp, 1))))
            bar_w = max(24, cell_w - 6)
            bar_h = 6
            bx = cx - bar_w // 2
            by = cy - radius - 10
            pygame.draw.rect(surf, (50, 55, 60), pygame.Rect(bx, by, bar_w, bar_h), border_radius=3)
            if mh > 0:
                fill_w = int(bar_w * (hp / mh))
                pygame.draw.rect(surf, (90, 200, 120), pygame.Rect(bx, by, fill_w, bar_h), border_radius=3)

    def _draw_log(self, surf: pygame.Surface)
