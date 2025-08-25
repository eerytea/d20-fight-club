# ui/state_table.py
from __future__ import annotations

from typing import Optional, List, Tuple

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, draw_panel, draw_text, Button
from .app import App


class TableState:
    """Simple standings table viewer."""
    def __init__(self, app: Optional[App] = None, *, career=None) -> None:
        self.app: App | None = app
        self.career = career
        self.btn_back: Button | None = None
        self._panel: "pygame.Rect" | None = None

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return
        pad = 16
        self._panel = pygame.Rect(pad, pad, self.app.width - pad * 2, self.app.height - 80)
        self.btn_back = Button(pygame.Rect(pad, self.app.height - 56, 160, 40), "Back", on_click=lambda: self.app.pop_state())

    def exit(self) -> None:
        pass

    def handle_event(self, event: "pygame.event.Event") -> bool:
        return self.btn_back.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        draw_text(surface, "Standings", (surface.get_width() // 2, 12), size=28, align="center")
        draw_panel(surface, self._panel, title="Table")

        # Sort table rows
        rows = list(self.career.table.values())
        rows.sort(key=lambda r: (-r.points, -(r.goals_for - r.goals_against), -r.goals_for, r.name))

        x = self._panel.x + 12
        y = self._panel.y + 32
        headers = ["#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]
        widths = [32, 260, 40, 40, 40, 40, 48, 48, 48, 48]
        for i, h in enumerate(headers):
            draw_text(surface, h, (x + sum(widths[:i]), y), size=18, color=th.muted)
        y += 24

        for rank, r in enumerate(rows, start=1):
            vals = [
                str(rank),
                r.name,
                str(r.played),
                str(r.wins),
                str(r.draws),
                str(r.losses),
                str(r.goals_for),
                str(r.goals_against),
                str(r.goals_for - r.goals_against),
                str(r.points),
            ]
            for i, v in enumerate(vals):
                draw_text(surface, v, (x + sum(widths[:i]), y), size=18, color=th.fg)
            y += 22

        self.btn_back.draw(surface)
