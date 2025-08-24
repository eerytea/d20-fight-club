# ui/state_roster.py
import pygame
from typing import Optional, List, Tuple
from .app import UIState
from .uiutil import draw_text, BIG, FONT, SMALL, Button
from core.types import Career

LEFT_W_FRACTION = 0.45
ROW_H = 28
PAD = 20

SORT_KEYS = ["OVR", "Level", "Age", "Class", "Name"]

class RosterState(UIState):
    """
    Roster screen for the user's team:
    - Left: sortable list
    - Right: details of selected fighter
    """
    def __init__(self, app, career: Career, user_team_id: int):
        self.app = app
        self.career = career
        self.user_team_id = user_team_id

        self.buttons: List[Button] = []
        self.sort_key = "OVR"
        self.sort_asc = False
        self.selected_idx: Optional[int] = 0   # index in visible/sorted list
        self._rows: List[pygame.Rect] = []     # clickable rows for left list
        self._scroll = 0
        self._max_rows = 1

        self._left_rect: Optional[pygame.Rect] = None
        self._right_rect: Optional[pygame.Rect] = None

    # -------- lifecycle --------
    def on_enter(self) -> None:
        W, H = self.app.WIDTH, self.app.HEIGHT
        lw = int(W * LEFT_W_FRACTION)
        self._left_rect = pygame.Rect(PAD, 120, lw - PAD*2, H - 120 - PAD)
        self._right_rect = pygame.Rect(lw + PAD, 120, W - (lw + PAD*2), H - 120 - PAD)

        # top buttons
        x = PAD
        self.buttons = [
            Button(pygame.Rect(x, 24, 120, 40), "Back", on_click=lambda: self.app.pop_state()),
        ]
        x += 140
        # sort key buttons
        for key in SORT_KEYS:
            self.buttons.append(Button(pygame.Rect(x, 24, 100, 40), key, on_click=lambda k=key: self._set_sort(k)))
            x += 110
        # asc/desc toggle
        self.buttons.append(Button(pygame.Rect(x, 24, 110, 40), "Desc", on_click=self._toggle_asc))

    def on_exit(self) -> None:
        self.buttons.clear()
        self._rows.clear()

    # -------- helpers --------
    def _set_sort(self, key: str):
        if key == self.sort_key:
            self._toggle_asc()
        else:
            self.sort_key = key
            self.sort_asc = (key in ("Name", "Class"))  # default asc for text
            self._update_sort_button_label()

    def _toggle_asc(self):
        self.sort_asc = not self.sort_asc
        self._update_sort_button_label()

    def _update_sort_button_label(self):
        # last button is the asc/desc
        self.buttons[-1].label = "Asc" if self.sort_asc else "Desc"

    def _sorted_roster(self) -> List[dict]:
        roster = list(self.career.rosters[self.user_team_id])
        key = self.sort_key
        def kf(f):
            if key == "OVR":   return int(f.get("ovr", 0))
            if key == "Level": return int(f.get("level", 1))
            if key == "Age":   return int(f.get("age", 20))
            if key == "Class": return str(f.get("class", ""))
            if key == "Name":  return str(f.get("name", ""))
            return 0
        roster.sort(key=kf, reverse=not self.sort_asc)
        return roster

    # -------- events/update --------
    def handle_event(self, event: pygame.event.Event):
        for b in self.buttons: b.handle_event(event)

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._left_rect and self._left_rect.collidepoint(mx, my):
                # standard wheel: event.y positive means up → decrease scroll
                self._scroll = max(0, self._scroll - event.y)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # click in left list
            if self._left_rect and self._left_rect.collidepoint(mx, my):
                for i, r in enumerate(self._rows):
                    if r.collidepoint(mx, my):
                        self.selected_idx = i + self._first_row_index()
                        break
        return None

    def update(self, dt: float): 
        return None

    # -------- draw --------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        draw_text(surface, f"Roster — {self.career.team_names[self.user_team_id]}", (PAD, 80), font=BIG)
        for b in self.buttons: b.draw(surface)

        self._draw_list(surface)
        self._draw_details(surface)

    # list panel
    def _draw_list(self, surface: pygame.Surface):
        assert self._left_rect is not None
        pane = self._left_rect
        pygame.draw.rect(surface, (36,38,44), pane, border_radius=10)

        # header
        head = pygame.Rect(pane.x+8, pane.y+8, pane.w-16, ROW_H)
        pygame.draw.rect(surface, (46,48,56), head, border_radius=6)
        draw_text(surface, "Name", (head.x+8, head.y+6), font=FONT)
        draw_text(surface, "Cls", (head.right-190, head.y+6), font=FONT)
        draw_text(surface, "Lv",  (head.right-140, head.y+6), font=FONT)
        draw_text(surface, "Age", (head.right-100, head.y+6), font=FONT)
        draw_text(surface, "OVR", (head.right-50, head.y+6), font=FONT)

        roster = self._sorted_roster()

        # rows with scroll
        self._rows = []
        y = head.bottom + 4
        visible_h = pane.h - (ROW_H + 24)
        self._max_rows = max(1, visible_h // ROW_H)
        first = self._first_row_index()
        last = min(len(roster), first + self._max_rows)

        for i in range(first, last):
            f = roster[i]
            rr = pygame.Rect(pane.x+8, y, pane.w-16, ROW_H-4)
            sel = (self.selected_idx == i)
            pygame.draw.rect(surface, (70,90,120) if sel else (46,48,56), rr, border_radius=6)

            name = str(f.get("name", "Fighter"))
            cls  = str(f.get("class", ""))
            lv   = str(f.get("level", 1))
            age  = str(f.get("age", 20))
            ovr  = str(int(f.get("ovr", 0)))

            draw_text(surface, name, (rr.x+8, rr.y+5), font=FONT)
            draw_text(surface, cls,  (rr.right-190, rr.y+5), font=FONT)
            draw_text(surface, lv,   (rr.right-140, rr.y+5), font=FONT)
            draw_text(surface, age,  (rr.right-100, rr.y+5), font=FONT)
            draw_text(surface, ovr,  (rr.right-50,  rr.y+5), font=FONT)

            self._rows.append(rr)
            y += ROW_H

        # scroll hint
        if len(roster) > self._max_rows:
            draw_text(surface, f"Scroll: {first+1}-{last} / {len(roster)}", (pane.x+12, pane.bottom-22), font=SMALL)

    def _first_row_index(self) -> int:
        # clamp scroll so we never overrun
        roster_len = len(self.career.rosters[self.user_team_id])
        max_first = max(0, roster_len - self._max_rows)
        return min(max(0, self._scroll), max_first)

    # details panel
    def _draw_details(self, surface: pygame.Surface):
        assert self._right_rect is not None
        pane = self._right_rect
        pygame.draw.rect(surface, (36,38,44), pane, border_radius=10)
        draw_text(surface, "Details", (pane.x + 12, pane.y - 28), font=BIG)

        roster = self._sorted_roster()
        if not roster:
            draw_text(surface, "No players.", (pane.x+12, pane.y+12), font=FONT)
            return

        idx = self.selected_idx or 0
        idx = max(0, min(idx, len(roster) - 1))
        f = roster[idx]

        x0, y0 = pane.x + 16, pane.y + 16
        lines = [
            f'Name: {f.get("name","—")}     Class: {f.get("class","—")}     Age: {f.get("age","—")}',
            f'Level: {f.get("level",1)}     OVR: {int(f.get("ovr",0))}     AC: {f.get("ac",10)}',
            f'HP: {f.get("hp","—")}/{f.get("max_hp","—")}     STR {f.get("str","—")}  DEX {f.get("dex","—")}  CON {f.get("con","—")}',
            f'INT {f.get("int","—")}  WIS {f.get("wis","—")}  CHA {f.get("cha","—")}',
        ]
        wy = y0
        for ln in lines:
            draw_text(surface, ln, (x0, wy), font=FONT); wy += 26

        # weapon box
        wbox = pygame.Rect(x0, wy + 8, pane.w - 32, 80)
        pygame.draw.rect(surface, (46,48,56), wbox, border_radius=8)
        w = f.get("weapon", {}) or {}
        w_name = w.get("name", "Unarmed")
        w_dmg = w.get("damage", "1d4")
        w_reach = w.get("reach", 1)
        draw_text(surface, f"Weapon: {w_name}   Damage: {w_dmg}   Reach: {w_reach}", (wbox.x+10, wbox.y+10), font=FONT)

        # (future) compare / transfer / contracts buttons could go here
