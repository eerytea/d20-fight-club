import pygame
from typing import List, Optional

from .app import UIState
from .uiutil import draw_text, Button, BIG, FONT, SMALL

from core.types import Career, Fixture, TableRow
from core.sim import simulate_week_ai
from core.save import save_career

class SeasonHubState(UIState):
    def __init__(self, app, career: Career, user_team_id: int):
        self.app = app
        self.career = career
        self.user_team_id = user_team_id
        self.buttons: List[Button] = []

        W, H = app.WIDTH, app.HEIGHT
        self.area_sched = pygame.Rect(24, 80, int(W*0.55)-32, H-120)
        self.area_table = pygame.Rect(self.area_sched.right+24, 80, W - (self.area_sched.right+24) - 24, H-120)

        btn_w, btn_h = 160, 40
        self.buttons = [
            Button(pygame.Rect(24, 24, 160, btn_h), "Back", on_click=self._back),
            Button(pygame.Rect(24+180, 24, btn_w, btn_h), "Advance Week", on_click=self._advance),
            Button(pygame.Rect(24+180+180, 24, btn_w, btn_h), "Save", on_click=self._save),
        ]

    def on_enter(self): pass
        Button(pygame.Rect(24+180+180+180, 24, 160, 40), "Play My Match", on_click=self._play_my_match),
        # in on_enter button list, add:
        Button(pygame.Rect(24+180+180+180+180, 24, 120, 40), "Schedule", on_click=self._open_schedule),
        Button(pygame.Rect(24+180+180+180+180+140, 24, 100, 40), "Table", on_click=self._open_table),
    def _save_now(self):
        try:
        from core.save import save_career
        save_career(self.career, "saves/career.json")
        # (optional) flash a tiny toast or push MessageState
        except Exception as e:
        from .state_message import MessageState
        self.app.push_state(MessageState("Save Error", str(e)))


    # add methods:
    def _open_schedule(self):
        from .state_schedule import ScheduleState
        self.app.push_state(ScheduleState(self.app, self.career))

    def _open_table(self):
        from .state_table import TableState
        self.app.push_state(TableState(self.app, self.career, self.user_team_id))

    def _play_my_match(self):
        # find user's fixture this week
        wk = self.career.week
        my_fx = [f for f in self.career.fixtures if f.week == wk and (f.home_id == self.user_team_id or f.away_id == self.user_team_id)]
        if not my_fx:
        return
        from .state_match_season import SeasonMatchState
        self.app.push_state(SeasonMatchState(self.app, self.career, self.user_team_id))

    def on_exit(self): pass

    def _back(self):
        self.app.pop_state()

    def _advance(self):
        simulate_week_ai(self.career)

    def _save(self):
        save_career(self.career, "saves/career.json")

    def handle_event(self, event: pygame.event.Event):
        for b in self.buttons: b.handle_event(event)
        return None

    def update(self, dt: float):
        return None

    # ---- drawing helpers ----
    def _draw_schedule(self, surface: pygame.Surface):
        pygame.draw.rect(surface, (36,38,44), self.area_sched, border_radius=10)
        draw_text(surface, f"Week {self.career.week} — Fixtures", (self.area_sched.x+12, self.area_sched.y-28), font=BIG)

        y = self.area_sched.y + 8
        fixtures = [f for f in self.career.fixtures if f.week == self.career.week]
        if not fixtures:
            draw_text(surface, "No fixtures this week (season likely finished).", (self.area_sched.x+12, y))
            return

        for fx in fixtures:
            h = self.career.team_names[fx.home_id]
            a = self.career.team_names[fx.away_id]
            if fx.played:
                score = f"{fx.home_goals}-{fx.away_goals}"
            else:
                score = "vs"
            draw_text(surface, f"{h}  {score}  {a}", (self.area_sched.x+12, y)); y += 26

    def _draw_table(self, surface: pygame.Surface):
        pygame.draw.rect(surface, (36,38,44), self.area_table, border_radius=10)
        draw_text(surface, "Table (3/1/0)", (self.area_table.x+12, self.area_table.y-28), font=BIG)

        # header
        x0, y0 = self.area_table.x+12, self.area_table.y+8
        headers = ["Pos", "Team", "P", "W", "D", "L", "GF", "GA", "Pts"]
        cols = [40, 180, 40, 40, 40, 40, 50, 50, 50]
        x = x0
        for htxt, w in zip(headers, cols):
            draw_text(surface, htxt, (x, y0), font=SMALL); x += w
        y0 += 24

        # rows sorted by points then GD then name
        rows = list(self.career.table.values())
        if not rows:
            draw_text(surface, "Table will populate as weeks are played.", (x0, y0))
            return
        rows.sort(key=lambda r: (r.points, (r.goals_for - r.goals_against), r.name), reverse=True)

        pos = 1
        for r in rows:
            color = (230, 230, 235)
            if r.team_id == self.user_team_id:
                pygame.draw.rect(surface, (70,90,120), pygame.Rect(x0-6, y0-2, sum(cols)+8, 22), border_radius=5)
            x = x0
            vals = [str(pos), r.name, str(r.played), str(r.wins), str(r.draws), str(r.losses),
                    str(r.goals_for), str(r.goals_against), str(r.points)]
            for v, w in zip(vals, cols):
                draw_text(surface, v, (x, y0), font=SMALL); x += w
            y0 += 22
            pos += 1

    def draw(self, surface: pygame.Surface):
        surface.fill((18,18,22))
        title = f"D20 Fight Club — Season Hub (Your team: {self.career.team_names[self.user_team_id]})"
        draw_text(surface, title, (24, 24), font=BIG)
        for b in self.buttons: b.draw(surface)
        self._draw_schedule(surface)
        self._draw_table(surface)
