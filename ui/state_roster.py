# ui/state_roster.py
from __future__ import annotations

from typing import Optional

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, Button, ListView, draw_panel, draw_text
from .app import App


class RosterState:
    """Roster viewer for the user's team (or the first team if not set)."""
    def __init__(self, app: Optional[App] = None, *, career=None) -> None:
        self.app: App | None = app
        self.career = career
        self.team_id: int = 0

        self.roster_lv: ListView | None = None
        self.btn_back: Button | None = None
        self._detail_rect: "pygame.Rect" | None = None

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return
        self.team_id = getattr(self.career, "user_team_id", 0)

        W, H = self.app.width, self.app.height
        pad = 16
        list_rect = pygame.Rect(pad, pad, max(360, W // 3), H - 80)
        detail_rect = pygame.Rect(list_rect.right + pad, pad, W - list_rect.width - pad * 3, H - 80)
        self._detail_rect = detail_rect

        self.roster_lv = ListView(list_rect, [], row_h=28)
        labels = [f"{f['name']} — {f.get('cls','Ftr')} (OVR {f.get('ovr', 50)})" for f in self.career.rosters[self.team_id]]
        self.roster_lv.set_items(labels)

        self.btn_back = Button(pygame.Rect(pad, H - 56, 160, 40), "Back", on_click=lambda: self.app.pop_state())

    def exit(self) -> None:
        pass

    def handle_event(self, event: "pygame.event.Event") -> bool:
        if self.roster_lv and self.roster_lv.handle_event(event):
            return True
        if self.btn_back.handle_event(event):
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        draw_text(surface, f"Roster — {self.career.team_names[self.team_id]}", (surface.get_width() // 2, 12), size=28, align="center")

        self.roster_lv.draw(surface, title="Players")
        draw_panel(surface, self._detail_rect, title="Details")

        x = self._detail_rect.x + 12
        y = self._detail_rect.y + 8
        idx = getattr(self.roster_lv, "selected", None)
        if idx is None:
            draw_text(surface, "Select a player to view stats", (x, y), size=18, color=th.muted)
        else:
            f = self.career.rosters[self.team_id][idx]
            lines = [
                f"{f.get('name','?')} — {f.get('cls','Fighter')} (OVR {f.get('ovr','?')})",
                f"HP {f.get('hp','?')}/{f.get('max_hp', f.get('hp','?'))} | AC {f.get('ac','?')}",
                f"STR {f.get('str','?')}  DEX {f.get('dex','?')}  CON {f.get('con','?')}",
                f"INT {f.get('int','?')}  WIS {f.get('wis','?')}  CHA {f.get('cha','?')}",
            ]
            wpn = f.get("weapon") or {}
            if isinstance(wpn, dict):
                lines.append(f"Weapon: {wpn.get('name','?')}  dmg {wpn.get('damage','?')}  reach {wpn.get('reach',1)}")
            for line in lines:
                draw_text(surface, line, (x, y), size=18, color=th.fg)
                y += 22

        self.btn_back.draw(surface)
