import pygame
from typing import Optional, List, Tuple

from .app import UIState
from .uiutil import draw_text, Button, BIG, FONT, SMALL

from core.career import new_career
from core.ratings import ovr_from_stats

class TeamSelectState(UIState):
    def __init__(self, app, seed: int = 20250824):
        self.app = app
        self.seed = seed
        self.career = new_career(seed=seed, team_count=20)

        self.selected_team: Optional[int] = None
        self.buttons: List[Button] = []

        # layout rects
        W, H = app.WIDTH, app.HEIGHT
        TOP_OFFSET = 140
        left_rect = pygame.Rect(20, TOP_OFFSET, W//2 - 40, H - TOP_OFFSET - 40)
        right_rect = pygame.Rect(W//2 + 20, TOP_OFFSET, W//2 - 40, H - TOP_OFFSET - 40)

        # buttons
        btn_w, btn_h = 160, 40
        start_rect = pygame.Rect(W-24-btn_w, 24, btn_w, btn_h)
        back_rect  = pygame.Rect(24, 24, 120, btn_h)
        self.buttons = [
            Button(start_rect, "Start Career", on_click=self._start),
            Button(back_rect,  "Back",        on_click=self._back),
        ]
 def __init__(self, app):
        self.app = app
        self.selected_team_id = None
        self.selected_fighter = None
        self._fighter_rows = []  # store clickable rects for fighters

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # check if clicked a fighter row
            for fighter, rect in self._fighter_rows:
                if rect.collidepoint(mx, my):
                    self.selected_fighter = fighter
                    break
        return None

    def draw(self, surface):
        # ... draw left and right panels as before

        # --- Right panel roster ---
        self._fighter_rows = []
        x, y = right_rect.x + 10, right_rect.y + 40
        for fighter in roster:   # however you load them
            rect = pygame.Rect(x, y, right_rect.w - 20, 28)
            pygame.draw.rect(surface, (50,50,60), rect, 0, border_radius=4)
            label = f"{fighter['name']} Lv{fighter['level']} OVR{fighter.get('ovr',0)}"
            draw_text(surface, label, (x+6, y+4))
            self._fighter_rows.append((fighter, rect))
            y += 32

        # --- Fighter details ---
        if self.selected_fighter:
            f = self.selected_fighter
            draw_text(surface, f"Class: {f['class']}  Age: {f['age']}", (right_rect.x+10, y+20))
            # etc.

    def on_enter(self): pass
    def on_exit(self): pass

    # ----- navigation -----
    def _back(self):
        self.app.pop_state()

    def _start(self):
        if self.selected_team is None: 
            return
        # Defer to Season Hub, pass career + user team id
        from .state_season_hub import SeasonHubState
        self.app.push_state(SeasonHubState(self.app, self.career, user_team_id=self.selected_team))

    # ----- events/update/draw -----
    def handle_event(self, event: pygame.event.Event):
        for b in self.buttons: 
            b.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # click in left list to select team
            mx, my = event.pos
            if self.col_left.collidepoint(mx, my):
                idx = (my - self.col_left.y) // 28
                if 0 <= idx < len(self.career.team_names):
                    self.selected_team = idx
        return None

    def update(self, dt: float):
        # enable Start only when team selected
        self.buttons[0].enabled = (self.selected_team is not None)
        return None

    def _avg_ovr(self, team_id: int) -> int:
        roster = self.career.rosters[team_id]
        if not roster: return 50
        # creator already stored an 'ovr', but compute if missing
        vals = [(r.get("ovr") if r.get("ovr") is not None else ovr_from_stats(
                 {k:r.get(k,10) for k in ("str","dex","con","int","wis","cha")}
               )) for r in roster]
        return int(sum(vals)/len(vals))

    def _draw_team_list(self, surface: pygame.Surface):
        pygame.draw.rect(surface, (36,38,44), self.col_left, border_radius=10)
        draw_text(surface, "Teams", (self.col_left.x+12, self.col_left.y-28), font=BIG)

        y = self.col_left.y + 8
        for i, name in enumerate(self.career.team_names):
            avg = self._avg_ovr(i)
            color = (220,220,230)
            row_r = pygame.Rect(self.col_left.x+6, y, self.col_left.w-12, 24)
            if i == self.selected_team:
                pygame.draw.rect(surface, (70,90,120), row_r, border_radius=6)
            txt = f"{i:02d}  {name}   (Avg OVR {avg})"
            draw_text(surface, txt, (self.col_left.x+12, y))
            y += 28

    def _draw_roster_and_details(self, surface: pygame.Surface):
        pygame.draw.rect(surface, (36,38,44), self.col_right, border_radius=10)
        draw_text(surface, "Roster", (self.col_right.x+12, self.col_right.y-28), font=BIG)
        if self.selected_team is None:
            draw_text(surface, "← Select a team on the left", (self.col_right.x+12, self.col_right.y+12))
            return

        roster = self.career.rosters[self.selected_team][:6]  # show top 6
        # top half: roster list
        y = self.col_right.y + 8
        list_h = int(self.col_right.h * 0.55)
        list_area = pygame.Rect(self.col_right.x+8, y, self.col_right.w-16, list_h-16)
        pygame.draw.rect(surface, (46,48,56), list_area, border_radius=8)
        y2 = list_area.y + 8
        for f in roster:
            txt = f'{f.get("name","Fighter")} | Lv {f.get("level",1)} | {f.get("class","")} | OVR {f.get("ovr","?")}'
            draw_text(surface, txt, (list_area.x+10, y2))
            y2 += 24

        # bottom: details (of first fighter for now)
        detail = roster[0] if roster else {}
        det_area = pygame.Rect(self.col_right.x+8, self.col_right.y+list_h+8, self.col_right.w-16, self.col_right.h - list_h - 24)
        pygame.draw.rect(surface, (46,48,56), det_area, border_radius=8)
        x0, y0 = det_area.x+10, det_area.y+10
        draw_text(surface, "Details", (x0, y0), font=FONT)
        y0 += 28
        lines = [
            f'Name: {detail.get("name","—")}   Class: {detail.get("class","—")}   Age: {detail.get("age","—")}',
            f'Level: {detail.get("level",1)}   AC: {detail.get("ac",10)}   HP: {detail.get("hp","—")}/{detail.get("max_hp","—")}',
            f'STR {detail.get("str","—")}  DEX {detail.get("dex","—")}  CON {detail.get("con","—")}  INT {detail.get("int","—")}  WIS {detail.get("wis","—")}  CHA {detail.get("cha","—")}',
            f'Weapon: {detail.get("weapon",{}).get("name","Unarmed")}  Dmg: {detail.get("weapon",{}).get("damage","1d2")}  Reach: {detail.get("weapon",{}).get("reach",1)}',
        ]
        for ln in lines:
            draw_text(surface, ln, (x0, y0), font=SMALL); y0 += 22

    def draw(self, surface: pygame.Surface):
        surface.fill((18,18,22))
        draw_text(surface, "D20 Fight Club — Team Select", (24, 24), font=BIG)
        for b in self.buttons: b.draw(surface)
        self._draw_team_list(surface)
        self._draw_roster_and_details(surface)
