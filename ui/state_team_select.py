# ui/state_team_select.py
from __future__ import annotations

from typing import Optional

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, Button, ListView, draw_panel, draw_text
from .app import App
from core.career import new_career
from core import config


class TeamSelectState:
    def __init__(self, app: Optional[App] = None) -> None:
        self.app: App | None = app
        self.career = None  # will be set in enter()
        self.teams_lv: ListView | None = None
        self.roster_lv: ListView | None = None
        self.btn_start: Button | None = None
        self.btn_back: Button | None = None
        self.selected_team: int | None = None
        self.selected_fighter_idx: int | None = None

    # ------------- lifecycle -------------

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return

        # Build a new career using the app's seed for determinism
        seed = getattr(self.app, "seed", None)
        self.career = new_career(seed=seed, user_team_id=None)

        W, H = self.app.width, self.app.height
        pad = 16

        # Left: teams list
        left_rect = pygame.Rect(pad, pad, max(260, W // 4), H - pad * 3 - 60)
        # Right: roster + details stacked
        right_rect = pygame.Rect(left_rect.right + pad, pad, W - left_rect.width - pad * 3, H - pad * 3 - 60)
        roster_h = int(right_rect.height * 0.62)
        detail_h = right_rect.height - roster_h - pad

        roster_rect = pygame.Rect(right_rect.x, right_rect.y, right_rect.width, roster_h)
        detail_rect = pygame.Rect(right_rect.x, roster_rect.bottom + pad, right_rect.width, detail_h)

        # Buttons
        btn_w, btn_h = 200, 44
        btn_start_rect = pygame.Rect(W - pad - btn_w, H - pad - btn_h, btn_w, btn_h)
        btn_back_rect = pygame.Rect(pad, H - pad - btn_h, btn_w, btn_h)

        # Widgets
        self.teams_lv = ListView(left_rect, self.career.team_names, row_h=30)
        self.roster_lv = ListView(roster_rect, [], row_h=26)
        self._detail_rect = detail_rect

        def on_start():
            if self.selected_team is None:
                self._msg("Pick a team first")
                return
            # finalize career
            self.career.user_team_id = self.selected_team
            # stash for other states
            self.app.data["career"] = self.career
            # try to push Season Hub
            try:
                from .state_season_hub import SeasonHubState
                self.app.replace_state(SeasonHubState(career=self.career))
            except Exception:
                self._msg("Season Hub not wired yet")

        def on_back():
            self.app.pop_state()

        self.btn_start = Button(btn_start_rect, "Start Season", on_click=on_start, enabled=True)
        self.btn_back = Button(btn_back_rect, "Back", on_click=on_back, enabled=True)

    def exit(self) -> None:
        pass

    # ------------- events -------------

    def handle_event(self, event: "pygame.event.Event") -> bool:
        consumed = False
        if self.teams_lv and self.teams_lv.handle_event(event):
            self.selected_team = self.teams_lv.selected
            self.selected_fighter_idx = None
            if self.selected_team is not None:
                # fill roster
                roster = self.career.rosters[self.selected_team]
                labels = [f"{f['name']}  (OVR {f.get('ovr', 50)})" for f in roster]
                self.roster_lv.set_items(labels)
            consumed = True

        if self.roster_lv and self.roster_lv.handle_event(event):
            self.selected_fighter_idx = self.roster_lv.selected
            consumed = True

        if self.btn_start and self.btn_start.handle_event(event):
            consumed = True
        if self.btn_back and self.btn_back.handle_event(event):
            consumed = True

        return consumed

    def update(self, dt: float) -> None:
        pass

    # ------------- rendering -------------

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        draw_text(surface, "Choose Your Team", (surface.get_width() // 2, 20), size=32, align="center")

        # Panels
        self.teams_lv.draw(surface, title="Teams")
        self.roster_lv.draw(surface, title="Roster")

        # Details panel (fighter stats)
        draw_panel(surface, self._detail_rect, title="Details")
        if self.selected_team is not None and self.selected_fighter_idx is not None:
            f = self.career.rosters[self.selected_team][self.selected_fighter_idx]
            x, y = self._detail_rect.x + 12, self._detail_rect.y + 8
            lines = [
                f"{f.get('name','?')} — {f.get('cls','Fighter')} (OVR {f.get('ovr', '?')})",
                f"HP {f.get('hp','?')}/{f.get('max_hp', f.get('hp','?'))}  |  AC {f.get('ac','?')}",
                f"STR {f.get('str','?')}  DEX {f.get('dex','?')}  CON {f.get('con','?')}",
                f"INT {f.get('int','?')}  WIS {f.get('wis','?')}  CHA {f.get('cha','?')}",
            ]
            wpn = f.get("weapon") or {}
            if isinstance(wpn, dict):
                lines.append(f"Weapon: {wpn.get('name','?')}  dmg {wpn.get('damage','?')}  reach {wpn.get('reach',1)}")
            for line in lines:
                draw_text(surface, line, (x, y), size=18, color=th.fg)
                y += 22
        else:
            draw_text(surface, "Select a fighter to see details", (self._detail_rect.x + 12, self._detail_rect.y + 8),
                      size=18, color=th.muted)

        # Buttons
        self.btn_start.draw(surface)
        self.btn_back.draw(surface)

    # ------------- helpers -------------

    def _msg(self, text: str) -> None:
        try:
            from .state_message import MessageState
            self.app.safe_push(MessageState, message=text)
        except Exception:
            print(text)
