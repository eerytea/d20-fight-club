# ui/state_schedule.py
from __future__ import annotations

from typing import Optional, List

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore

from .uiutil import Theme, Button, ListView, draw_panel, draw_text
from .app import App


class ScheduleState:
    def __init__(self, app: Optional[App] = None, *, career=None) -> None:
        self.app: App | None = app
        self.career = career
        self.week: int = 0
        self.list_view: ListView | None = None
        self.btn_prev: Button | None = None
        self.btn_next: Button | None = None
        self.btn_back: Button | None = None
        self._panel: "pygame.Rect" | None = None

    def enter(self) -> None:
        if pygame is None or self.app is None:
            return
        self.week = self.career.week

        pad = 16
        self._panel = pygame.Rect(pad, pad, self.app.width - pad * 2, self.app.height - 80)
        self.list_view = ListView(pygame.Rect(self._panel.x + 8, self._panel.y + 32, self._panel.width - 16, self._panel.height - 40), [], row_h=28)

        def prev_w():
            self.week = max(0, self.week - 1)
            self._refresh()

        def next_w():
            self.week = min(max(f.week for f in self.career.fixtures), self.week + 1)
            self._refresh()

        self.btn_prev = Button(pygame.Rect(pad, self.app.height - 56, 120, 40), "< Week", on_click=prev_w)
        self.btn_next = Button(pygame.Rect(pad + 130, self.app.height - 56, 120, 40), "Week >", on_click=next_w)
        self.btn_back = Button(pygame.Rect(self.app.width - pad - 160, self.app.height - 56, 160, 40), "Back", on_click=lambda: self.app.pop_state())

        self._refresh()

    def exit(self) -> None:
        pass

    def handle_event(self, event: "pygame.event.Event") -> bool:
        if self.list_view and self.list_view.handle_event(event):
            return True
        if self.btn_prev.handle_event(event):
            return True
        if self.btn_next.handle_event(event):
            return True
        if self.btn_back.handle_event(event):
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        surface.fill(th.bg)
        draw_text(surface, f"Schedule — Week {self.week}", (surface.get_width() // 2, 12), size=28, align="center")
        draw_panel(surface, self._panel, title="Fixtures")
        self.list_view.draw(surface)
        self.btn_prev.draw(surface)
        self.btn_next.draw(surface)
        self.btn_back.draw(surface)

    # ---- helpers ----
    def _refresh(self) -> None:
        week_fx = [f for f in self.career.fixtures if f.week == self.week]
        labels = []
        for fx in week_fx:
            hn = self.career.team_names[fx.home_id]
            an = self.career.team_names[fx.away_id]
            if fx.played:
                labels.append(f"{hn} {fx.home_goals}-{fx.away_goals} {an}")
            else:
                labels.append(f"{hn} vs {an} (not played)")
        self.list_view.set_items(labels)
