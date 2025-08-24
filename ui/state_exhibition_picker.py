# ui/state_exhibition_picker.py
import pygame
from typing import Optional, List, Tuple
from .app import UIState
from .uiutil import draw_text, BIG, FONT, SMALL, Button
from core.career import new_career
from core.ratings import ovr_from_stats

PADDING = 20
PANEL_GAP = 24
ROW_H = 28

class ExhibitionPickerState(UIState):
    """
    Choose Home and Away teams for an exhibition match, then launch MatchState.
    """
    def __init__(self, app):
        self.app = app
        self.career = new_career(seed=4242, team_count=20)

        self.buttons: List[Button] = []
        self.left_rect: Optional[pygame.Rect] = None
        self.right_rect: Optional[pygame.Rect] = None

        self.sel_home: Optional[int] = None
        self.sel_away: Optional[int] = None

        # simple scroll for long lists
        self._scroll_home = 0
        self._scroll_away = 0
        self._max_rows = 0

    # ---------- lifecycle ----------
    def on_enter(self) -> None:
        W, H = self.app.WIDTH, self.app.HEIGHT
        content_top = 110
        panel_w = (W - (PADDING*2) - PANEL_GAP) // 2
        self.left_rect = pygame.Rect(PADDING, content_top, panel_w, H - content_top - PADDING)
        self.right_rect = pygame.Rect(self.left_rect.right + PANEL_GAP, content_top, panel_w, H - content_top - PADDING)

        # buttons (top row)
        self.buttons = [
            Button(pygame.Rect(PADDING, 24, 110, 40), "Back", on_click=self._back),
            Button(pygame.Rect(PADDING+120, 24, 140, 40), "Randomize", on_click=self._randomize),
            Button(pygame.Rect(W - PADDING - 160, 24, 160, 40), "Start Match", on_click=self._start),
        ]

    def on_exit(self) -> None:
        self.buttons.clear()

    # ---------- callbacks ----------
    def _back(self):
        self.app.pop_state()

    def _randomize(self):
        import random
        n = len(self.career.team_names)
        self.sel_home, self.sel_away = random.sample(range(n), 2)

    def _start(self):
        if self.sel_home is None or self.sel_away is None or self.sel_home == self.sel_away:
            return
        from .state_match import MatchState
        # Pass the team indices (relative to the career roster lists)
        self.app.push_state(MatchState(self.app, exhibition=True, teams=(self.sel_home, self.sel_away)))

    # ---------- events ----------
    def handle_event(self, event: pygame.event.Event):
        for b in self.buttons: b.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.left_rect and self.left_rect.collidepoint(mx, my):
                idx = self._row_index_from_click(self.left_rect, my, self._scroll_home)
                if 0 <= idx < len(self.career.team_names):
                    self.sel_home = idx
            elif self.right_rect and self.right_rect.collidepoint(mx, my):
                idx = self._row_index_from_click(self.right_rect, my, self._scroll_away)
                if 0 <= idx < len(self.career.team_names):
                    self.sel_away = idx

        # scroll (mouse wheel)
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.left_rect and self.left_rect.collidepoint(mx, my):
                self._scroll_home = max(0, self._scroll_home - event.y)
            elif self.right_rect and self.right_rect.collidepoint(mx, my):
                self._scroll_away = max(0, self._scroll_away - event.y)

        return None

    def update(self, dt: float):
        # enable Start only when both selections done and different
        can_start = (self.sel_home is not None and self.sel_away is not None and self.sel_home != self.sel_away)
        self.buttons[-1].enabled = can_start
        return None

    # ---------- drawing ----------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        draw_text(surface, "Exhibition — Pick Teams", (PADDING, 70), font=BIG)
        for b in self.buttons: b.draw(surface)

        self._draw_panel(surface, self.left_rect, "Home Team", self.sel_home, self._scroll_home)
        self._draw_panel(surface, self.right_rect, "Away Team", self.sel_away, self._scroll_away)

        # footer hint / conflict warning
        if self.sel_home is not None and self.sel_away is not None and self.sel_home == self.sel_away:
            draw_text(surface, "Home and Away must be different teams.", (PADDING, surface.get_height()-36), font=FONT)

    # ---------- helpers ----------
    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect, title: str, selected: Optional[int], scroll: int):
        pygame.draw.rect(surface, (36, 38, 44), rect, border_radius=10)
        draw_text(surface, title, (rect.x + 12, rect.y - 28), font=BIG)

        # header row
        head = pygame.Rect(rect.x+8, rect.y+8, rect.w-16, ROW_H)
        pygame.draw.rect(surface, (46,48,56), head, border_radius=6)
        draw_text(surface, "Team", (head.x+8, head.y+6), font=FONT)
        draw_text(surface, "Avg OVR", (head.right-110, head.y+6), font=FONT)

        # rows (with simple scroll)
        y = rect.y + 8 + ROW_H + 4
        visible_h = rect.h - (ROW_H + 24)
        self._max_rows = max(1, visible_h // ROW_H)
        start = min(scroll, max(0, len(self.career.team_names) - self._max_rows))
        end = min(len(self.career.team_names), start + self._max_rows)

        for i in range(start, end):
            row_r = pygame.Rect(rect.x+8, y, rect.w-16, ROW_H-4)
            if selected == i:
                pygame.draw.rect(surface, (70, 90, 120), row_r, border_radius=6)
            else:
                pygame.draw.rect(surface, (46,48,56), row_r, border_radius=6)

            name = self.career.team_names[i]
            avg = self._avg_ovr(i)
            draw_text(surface, name, (row_r.x+8, row_r.y+5), font=FONT)
            draw_text(surface, str(avg), (row_r.right-64, row_r.y+5), font=FONT)

            y += ROW_H

        # selection summary
        sum_y = rect.bottom - 52
        sel_txt = "None" if selected is None else self.career.team_names[selected]
        draw_text(surface, f"Selected: {sel_txt}", (rect.x+12, sum_y), font=FONT)

    def _row_index_from_click(self, rect: pygame.Rect, my: int, scroll: int) -> int:
        y0 = rect.y + 8 + ROW_H + 4  # after header
        if my < y0: return -1
        rel = (my - y0) // ROW_H
        start = min(scroll, max(0, len(self.career.team_names) - self._max_rows))
        return int(start + rel)

    def _avg_ovr(self, team_id: int) -> int:
        roster = self.career.rosters.get(team_id, [])
        if not roster: return 50
        vals = []
        for r in roster:
            if r.get("ovr") is not None:
                vals.append(int(r["ovr"]))
            else:
                vals.append(ovr_from_stats({k: r.get(k, 10) for k in ("str","dex","con","int","wis","cha")}))
        return int(sum(vals) / len(vals))
