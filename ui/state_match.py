# ui/state_match.py
from __future__ import annotations

from typing import Optional, List, Dict, Tuple

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, Button, draw_panel, draw_text
from .app import App
from core import config
from engine import TBCombat, Team as BattleTeam, fighter_from_dict, layout_teams_tiles
from engine.events import format_event


class MatchState:
    """
    Watchable match viewer using the typed event log.
    Construct one of:
      - MatchState(app, career=<Career>, home_team_id=<int>, away_team_id=<int>, seed=<int|None>)
      - Or for exhibition: provide home_team_id & away_team_id without career, and pass rosters explicitly
    """
    def __init__(
        self,
        app: Optional[App] = None,
        *,
        career=None,
        home_team_id: Optional[int] = None,
        away_team_id: Optional[int] = None,
        seed: Optional[int] = None,
        # Optional direct rosters for exhibition: list[dict] fighter dicts
        home_roster: Optional[List[dict]] = None,
        away_roster: Optional[List[dict]] = None,
        title: str = "Match",
    ) -> None:
        self.app: App | None = app
        self.career = career
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.seed = seed
        self.home_roster_raw = home_roster
        self.away_roster_raw = away_roster
        self.title = title

        self.combat: TBCombat | None = None
        self._buttons: List[Button] = []
        self._auto: bool = False

        self._grid_rect: Optional["pygame.Rect"] = None
        self._log_rect: Optional["pygame.Rect"] = None
        self._hud_rect: Optional["pygame.Rect"] = None

        self._names: Dict[int, str] = {}

    # ---------------- lifecycle ----------------

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return

        # Build teams + fighters
        teamH, teamA, fighters = self._build_teams_and_fighters()
        layout_teams_tiles(fighters, config.GRID_W, config.GRID_H)
        self.combat = TBCombat(teamH, teamA, fighters, config.GRID_W, config.GRID_H, seed=self.seed)

        # cache id->name for logs
        self._names = {f.id: getattr(f, "name", f"F#{f.id}") for f in self.combat.fighters}

        # Layout
        W, H = self.app.width, self.app.height
        pad = 16
        grid_size = min(W - pad * 3 - 320, H - pad * 3)  # square area for grid
        grid_size = max(420, grid_size)
        self._grid_rect = pygame.Rect(pad, pad, grid_size, grid_size)

        right_w = W - self._grid_rect.right - pad * 2
        self._log_rect = pygame.Rect(self._grid_rect.right + pad, pad, right_w, int(grid_size * 0.65))
        self._hud_rect = pygame.Rect(self._grid_rect.right + pad, self._log_rect.bottom + pad, right_w, grid_size - self._log_rect.height - pad)

        # Buttons under the grid
        btn_w, btn_h = 140, 40
        b_step = Button(pygame.Rect(pad, self._grid_rect.bottom + pad, btn_w, btn_h), "Step", on_click=self._step_once)
        b_auto = Button(pygame.Rect(pad + btn_w + 10, self._grid_rect.bottom + pad, btn_w, btn_h), "Auto: Off", on_click=self._toggle_auto)
        b_back = Button(pygame.Rect(pad + (btn_w + 10) * 2, self._grid_rect.bottom + pad, btn_w, btn_h), "Back", on_click=lambda: self.app.pop_state())
        self._buttons = [b_step, b_auto, b_back]

    def exit(self) -> None:
        self._buttons.clear()

    # ---------------- events & update ----------------

    def handle_event(self, event: "pygame.event.Event") -> bool:
        for b in self._buttons:
            if b.handle_event(event):
                # keep the auto label in sync, if toggled
                if "Auto" in b.label:
                    b.label = f"Auto: {'On' if self._auto else 'Off'}"
                return True
        return False

    def update(self, dt: float) -> None:
        if self._auto and self.combat and self.combat.winner is None:
            # run a few steps per frame for smoother viewing
            for _ in range(4):
                if self.combat.winner is not None:
                    break
                self.combat.take_turn()

    # ---------------- drawing ----------------

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        draw_text(surface, self.title, (surface.get_width() // 2, 10), size=28, align="center")

        # Grid panel
        draw_panel(surface, self._grid_rect, title=f"Grid {config.GRID_W}×{config.GRID_H}")
        self._draw_grid(surface)
        self._draw_fighters(surface)

        # Log panel
        draw_panel(surface, self._log_rect, title="Log")
        self._draw_log(surface)

        # HUD panel (teams, score-ish)
        draw_panel(surface, self._hud_rect, title="HUD")
        self._draw_hud(surface)

        # Buttons
        for b in self._buttons:
            b.draw(surface)

    # ---------------- internal helpers ----------------

    def _build_teams_and_fighters(self):
        # Determine source rosters
        if self.career is not None and self.home_team_id is not None and self.away_team_id is not None:
            H_id, A_id = self.home_team_id, self.away_team_id
            H_name = self.career.team_names[H_id]
            A_name = self.career.team_names[A_id]
            H_color = tuple(self.career.team_colors[H_id])
            A_color = tuple(self.career.team_colors[A_id])
            rosterH = sorted(self.career.rosters[H_id], key=lambda r: r.get("ovr", 50), reverse=True)[:config.TEAM_SIZE]
            rosterA = sorted(self.career.rosters[A_id], key=lambda r: r.get("ovr", 50), reverse=True)[:config.TEAM_SIZE]
        else:
            # Exhibition with direct rosters OR fallback stub
            H_name, A_name = "Home", "Away"
            H_color, A_color = (80, 150, 255), (255, 120, 80)
            rosterH = self.home_roster_raw or []
            rosterA = self.away_roster_raw or []
            if not rosterH or not rosterA:
                # Minimal stub fighters if none provided (shouldn't happen in practice)
                def stub(i, tid): return {"fighter_id": i, "team_id": tid, "name": f"T{tid}-{i}", "hp": 10, "max_hp": 10, "ac": 12, "str": 12, "dex": 12, "con": 12}
                rosterH = [stub(i, 0) for i in range(config.TEAM_SIZE)]
                rosterA = [stub(i, 1) for i in range(config.TEAM_SIZE)]

        teamH = BattleTeam(0, H_name, H_color)
        teamA = BattleTeam(1, A_name, A_color)
        fighters = [fighter_from_dict({**fd, "team_id": 0}) for fd in rosterH] + \
                   [fighter_from_dict({**fd, "team_id": 1}) for fd in rosterA]
        return teamH, teamA, fighters

    def _toggle_auto(self) -> None:
        self._auto = not self._auto

    def _step_once(self) -> None:
        if self.combat and self.combat.winner is None:
            self.combat.take_turn()

    def _draw_grid(self, surface: "pygame.Surface") -> None:
        if self._grid_rect is None:
            return
        cell_w = self._grid_rect.width // config.GRID_W
        cell_h = self._grid_rect.height // config.GRID_H
        for y in range(config.GRID_H):
            for x in range(config.GRID_W):
                r = pygame.Rect(
                    self._grid_rect.x + x * cell_w,
                    self._grid_rect.y + y * cell_h,
                    cell_w - 1, cell_h - 1
                )
                pygame.draw.rect(surface, (40, 43, 49), r)

    def _draw_fighters(self, surface: "pygame.Surface") -> None:
        if self._grid_rect is None or not self.combat:
            return
        cell_w = self._grid_rect.width // config.GRID_W
        cell_h = self._grid_rect.height // config.GRID_H

        for f in self.combat.fighters:
            if not hasattr(f, "tx"):
                continue
            x = self._grid_rect.x + f.tx * cell_w + cell_w // 2
            y = self._grid_rect.y + f.ty * cell_h + cell_h // 2
            color = (80, 150, 255) if f.team_id == 0 else (255, 120, 80)
            # body
            pygame.draw.circle(surface, color if f.alive else (80, 80, 80), (x, y), max(8, min(cell_w, cell_h) // 3))
            # HP bar
            max_hp = getattr(f, "max_hp", getattr(f, "hp", 10))
            cur_hp = max(0, getattr(f, "hp", 0))
            w = max(24, cell_w - 12)
            bar_rect = pygame.Rect(x - w // 2, y + (cell_h // 2) - 10, w, 6)
            pygame.draw.rect(surface, (70, 70, 70), bar_rect, border_radius=3)
            if max_hp > 0:
                fill = pygame.Rect(bar_rect.x, bar_rect.y, int(w * (cur_hp / max_hp)), bar_rect.height)
                pygame.draw.rect(surface, (80, 220, 120), fill, border_radius=3)

    def _draw_log(self, surface: "pygame.Surface") -> None:
        if not self.combat or not self._log_rect:
            return
        x = self._log_rect.x + 12
        y = self._log_rect.y + 8
        th = Theme()

        # Prefer typed events if present
        if getattr(self.combat, "events_typed", None):
            # Only render the last ~18 lines
            events = self.combat.events_typed[-18:]
            for ev in events:
                line = format_event(ev, name_of=self._names.get)
                draw_text(surface, line, (x, y), size=18, color=th.fg)
                y += 20
        else:
            lines = self.combat.events[-18:]
            for line in lines:
                draw_text(surface, line, (x, y), size=18, color=th.fg)
                y += 20

    def _draw_hud(self, surface: "pygame.Surface") -> None:
        if not self.combat or not self._hud_rect:
            return
        x = self._hud_rect.x + 12
        y = self._hud_rect.y + 8
        th = Theme()

        home_alive = sum(1 for f in self.combat.fighters if f.team_id == 0 and f.alive)
        away_alive = sum(1 for f in self.combat.fighters if f.team_id == 1 and f.alive)
        home_goals = config.TEAM_SIZE - away_alive
        away_goals = config.TEAM_SIZE - home_alive

        draw_text(surface, f"{self.combat.team_home.name} vs {self.combat.team_away.name}", (x, y), size=20, color=th.fg)
        y += 24
        draw_text(surface, f"Score: {home_goals} - {away_goals}", (x, y), size=20, color=th.fg)
        y += 24
        if self.combat.winner is None:
            draw_text(surface, "Status: In progress", (x, y), size=18, color=th.muted)
        else:
            result = "Draw" if self.combat.winner is None else ("Home" if self.combat.winner == 0 else "Away")
            draw_text(surface, f"Result: {result}", (x, y), size=18, color=th.fg)
