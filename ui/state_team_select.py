# ui/state_team_select.py
import pygame
from typing import Optional, List, Tuple

from .app import UIState
from .uiutil import draw_text, Button, BIG, FONT, SMALL

from core.career import new_career
from core.ratings import ovr_from_stats


class TeamSelectState(UIState):
    TOP_OFFSET = 140  # push panels down so they don't overlap top title/buttons

    def __init__(self, app, seed: int = 20250824):
        self.app = app
        self.seed = seed
        self.career = new_career(seed=seed, team_count=20)

        self.selected_team: Optional[int] = None
        self.selected_fighter_idx: Optional[int] = None  # index within visible roster list
        self._fighter_row_rects: List[pygame.Rect] = []  # clickable rects for roster rows

        # layout rects (computed in on_enter because we need app.WIDTH/HEIGHT)
        self.col_left: Optional[pygame.Rect] = None
        self.col_right: Optional[pygame.Rect] = None

        self.buttons: List[Button] = []

    # ---------- lifecycle ----------
    def on_enter(self):
        W, H = self.app.WIDTH, self.app.HEIGHT
        # left pane ~35%, right pane the rest
        left_w = int(W * 0.35)
        self.col_left = pygame.Rect(24, self.TOP_OFFSET, left_w - 32, H - self.TOP_OFFSET - 32)
        self.col_right = pygame.Rect(self.col_left.right + 24, self.TOP_OFFSET,
                                     W - (self.col_left.right + 24) - 24, H - self.TOP_OFFSET - 32)

        # Buttons along the top bar
        btn_w, btn_h = 160, 40
        start_rect = pygame.Rect(W - 24 - btn_w, 24, btn_w, btn_h)
        back_rect = pygame.Rect(24, 24, 120, btn_h)

        self.buttons = [
            Button(start_rect, "Start Career", on_click=self._start),
            Button(back_rect, "Back", on_click=self._back),
        ]

    def on_exit(self):
        self.buttons.clear()
        self._fighter_row_rects.clear()

    # ---------- navigation ----------
    def _back(self):
        self.app.pop_state()

    def _start(self):
        if self.selected_team is None:
            return
        from .state_season_hub import SeasonHubState
        self.app.push_state(SeasonHubState(self.app, self.career, user_team_id=self.selected_team))

    # ---------- helpers ----------
    def _avg_ovr(self, team_id: int) -> int:
        roster = self.career.rosters.get(team_id, [])
        if not roster:
            return 50
        vals = []
        for r in roster:
            if r.get("ovr") is not None:
                vals.append(int(r["ovr"]))
            else:
                vals.append(
                    ovr_from_stats({k: r.get(k, 10) for k in ("str", "dex", "con", "int", "wis", "cha")})
                )
        return int(sum(vals) / len(vals))

    def _visible_roster(self) -> List[dict]:
        """Return the slice of roster shown in the list (top 6 for now)."""
        if self.selected_team is None:
            return []
        return self.career.rosters[self.selected_team][:6]

    # ---------- events/update ----------
    def handle_event(self, event: pygame.event.Event):
        for b in self.buttons:
            b.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # click in team list (left)
            if self.col_left and self.col_left.collidepoint(mx, my):
                row_h = 28
                # first row y start inside pane
                first_y = self.col_left.y + 8
                idx = (my - first_y) // row_h
                if 0 <= idx < len(self.career.team_names):
                    self.selected_team = idx
                    self.selected_fighter_idx = 0  # reset selection to first fighter
                    return

            # click on a fighter row (right)
            for i, rect in enumerate(self._fighter_row_rects):
                if rect.collidepoint(mx, my):
                    self.selected_fighter_idx = i
                    return

        return None

    def update(self, dt: float):
        # Start Career enabled only when a team is selected
        self.buttons[0].enabled = (self.selected_team is not None)
        return None

    # ---------- drawing ----------
    def _draw_header(self, surface: pygame.Surface):
        # Title and hint bar at the very top
        draw_text(surface, "Team Select", (24, 24), font=BIG)
        hint = "Choose a team on the left. Click a fighter on the right to view details."
        draw_text(surface, hint, (24, 24 + 44), font=FONT)

    def _draw_team_list(self, surface: pygame.Surface):
        assert self.col_left is not None
        pane = self.col_left
        pygame.draw.rect(surface, (36, 38, 44), pane, border_radius=10)
        draw_text(surface, "Teams", (pane.x + 12, pane.y - 28), font=BIG)

        y = pane.y + 8
        row_h = 28
        for i, name in enumerate(self.career.team_names):
            avg = self._avg_ovr(i)
            row_r = pygame.Rect(pane.x + 6, y, pane.w - 12, row_h - 4)
            if i == self.selected_team:
                pygame.draw.rect(surface, (70, 90, 120), row_r, border_radius=6)
            txt = f"{i:02d}  {name}   (Avg OVR {avg})"
            draw_text(surface, txt, (pane.x + 12, y))
            y += row_h

    def _draw_roster_and_details(self, surface: pygame.Surface):
        assert self.col_right is not None
        pane = self.col_right
        pygame.draw.rect(surface, (36, 38, 44), pane, border_radius=10)
        draw_text(surface, "Roster", (pane.x + 12, pane.y - 28), font=BIG)

        self._fighter_row_rects = []  # rebuild each frame
        if self.selected_team is None:
            draw_text(surface, "← Select a team on the left", (pane.x + 12, pane.y + 12))
            return

        roster = self._visible_roster()

        # top half: roster list (clickable rows)
        list_h = int(pane.h * 0.55)
        list_area = pygame.Rect(pane.x + 8, pane.y + 8, pane.w - 16, list_h - 16)
        pygame.draw.rect(surface, (46, 48, 56), list_area, border_radius=8)

        y = list_area.y + 8
        row_h = 28
        for i, f in enumerate(roster):
            r = pygame.Rect(list_area.x + 6, y, list_area.w - 12, row_h - 4)
            self._fighter_row_rects.append(r)
            # highlight selected
            if self.selected_fighter_idx == i:
                pygame.draw.rect(surface, (70, 90, 120), r, border_radius=6)
            label = f'{f.get("name","Fighter")} | Lv {f.get("level",1)} | {f.get("class","")} | OVR {f.get("ovr","?")}'
            draw_text(surface, label, (r.x + 8, r.y + 3), font=FONT)
            y += row_h

        # bottom: details of selected fighter (default to first if none chosen)
        idx = self.selected_fighter_idx or 0
        idx = max(0, min(idx, max(0, len(roster) - 1)))
        detail = roster[idx] if roster else {}

        det_area = pygame.Rect(
            pane.x + 8,
            pane.y + list_h + 8,
            pane.w - 16,
            pane.h - list_h - 24
        )
        pygame.draw.rect(surface, (46, 48, 56), det_area, border_radius=8)

        x0, y0 = det_area.x + 10, det_area.y + 10
        draw_text(surface, "Details", (x0, y0), font=FONT)
        y0 += 28

        lines = [
            f'Name: {detail.get("name","—")}   Class: {detail.get("class","—")}   Age: {detail.get("age","—")}',
            f'Level: {detail.get("level",1)}   AC: {detail.get("ac",10)}   HP: {detail.get("hp","—")}/{detail.get("max_hp","—")}',
            f'STR {detail.get("str","—")}  DEX {detail.get("dex","—")}  CON {detail.get("con","—")}  INT {detail.get("int","—")}  WIS {detail.get("wis","—")}  CHA {detail.get("cha","—")}',
            f'Weapon: {detail.get("weapon",{}).get("name","Unarmed")}  Dmg: {detail.get("weapon",{}).get("damage","1d2")}  Reach: {detail.get("weapon",{}).get("reach",1)}',
        ]
        for ln in lines:
            draw_text(surface, ln, (x0, y0), font=SMALL)
            y0 += 22

    def draw(self, surface: pygame.Surface):
        # background
        surface.fill((18, 18, 22))
        # header/title + top buttons
        self._draw_header(surface)
        for b in self.buttons:
            b.draw(surface)
        # panels
        self._draw_team_list(surface)
        self._draw_roster_and_details(surface)
