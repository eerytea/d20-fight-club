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
        self.rect_log = pygame.Rect(self.rect_panel.x + split, self.rect_panel.y + 12, self.rect_panel.w - split - 12, self.rect_panel.h
