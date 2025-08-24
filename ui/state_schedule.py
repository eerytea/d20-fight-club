# ui/state_schedule.py
import pygame
from typing import Optional, List
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button
from core.types import Career

class ScheduleState(UIState):
    def __init__(self, app, career: Career):
        self.app = app
        self.career = career
        self.buttons: List[Button] = []
        self.week_offset = 0  # 0 = current, -1 prev, +1 next

    def on_enter(self) -> None:
        self.buttons = [
            Button(pygame.Rect(24, 24, 120, 40), "Back", on_click=lambda: self.app.pop_state()),
            Button(pygame.Rect(160, 24, 40, 40), "<", on_click=self._prev),
            Button(pygame.Rect(210, 24, 40, 40), ">", on_click=self._next),
        ]

    def _prev(self): self.week_offset -= 1
    def _next(self): self.week_offset += 1

    def handle_event(self, event: pygame.event.Event): 
        for b in self.buttons: b.handle_event(event)

    def update(self, dt: float): pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        wk = max(1, self.career.week + self.week_offset)
        draw_text(surface, f"Schedule — Week {wk}", (24, 24), font=BIG)
        for b in self.buttons: b.draw(surface)
        y = 90
        fixtures = [f for f in self.career.fixtures if f.week == wk]
        if not fixtures:
            draw_text(surface, "No fixtures.", (24, y), font=FONT); return
        for fx in fixtures:
            h = self.career.team_names[fx.home_id]
            a = self.career.team_names[fx.away_id]
            score = "vs" if not fx.played else f"{fx.home_goals}-{fx.away_goals}"
            draw_text(surface, f"{h}  {score}  {a}", (24, y), font=FONT)
            y += 26
