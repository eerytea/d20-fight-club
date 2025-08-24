# ui/state_table.py
import pygame
from typing import Optional, List
from .app import UIState
from .uiutil import draw_text, BIG, FONT, SMALL, Button
from core.types import Career, TableRow

class TableState(UIState):
    def __init__(self, app, career: Career, user_team_id: int):
        self.app = app
        self.career = career
        self.user_team_id = user_team_id
        self.buttons: List[Button] = []

    def on_enter(self) -> None:
        self.buttons = [
            Button(pygame.Rect(24, 24, 120, 40), "Back", on_click=lambda: self.app.pop_state()),
        ]

    def handle_event(self, event: pygame.event.Event): 
        for b in self.buttons: b.handle_event(event)

    def update(self, dt: float): pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        draw_text(surface, "Table (3/1/0)", (24, 24), font=BIG)
        for b in self.buttons: b.draw(surface)

        # header
        x0, y0 = 24, 90
        headers = ["Pos", "Team", "P", "W", "D", "L", "GF", "GA", "Pts"]
        cols = [40, 220, 40, 40, 40, 40, 50, 50, 60]
        x = x0
        for htxt, w in zip(headers, cols):
            draw_text(surface, htxt, (x, y0), font=SMALL); x += w
        y0 += 24

        rows = list(self.career.table.values())
        rows.sort(key=lambda r: (r.points, (r.goals_for - r.goals_against), r.name), reverse=True)

        pos = 1
        for r in rows:
            if r.team_id == self.user_team_id:
                pygame.draw.rect(surface, (70,90,120), pygame.Rect(x0-6, y0-2, sum(cols)+8, 22), border_radius=5)
            x = x0
            vals = [str(pos), r.name, str(r.played), str(r.wins), str(r.draws), str(r.losses),
                    str(r.goals_for), str(r.goals_against), str(r.points)]
            for v, w in zip(vals, cols):
                draw_text(surface, v, (x, y0), font=SMALL); x += w
            y0 += 22
            pos += 1
