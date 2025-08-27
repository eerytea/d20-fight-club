from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List

try:
    from ui.uiutil import Button, draw_text, panel
except Exception:
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=8)
            font = pygame.font.SysFont("arial", 18)
            txt = font.render(self.label, True, (255,255,255) if self.enabled else (170,170,170))
            screen.blit(txt, (self.rect.x+10, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=10)

def _team_by_tid(teams: List[Dict[str, Any]], tid: int):
    for t in teams:
        if int(t.get("tid", t.get("id", -1))) == int(tid):
            return t
    return {"tid": tid, "name": f"Team {tid}", "fighters": []}

def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

class TrainingState:
    """
    Per-player weekly training focus: DEX vs STR (%). STR displayed as (100-DEX).
    Saved into career.staff['training_focus'][f'{tid}:{pid}'] = {'DEX': d, 'STR': 1-d}
    """
    def __init__(self, app, career, tid: int):
        self.app = app
        self.career = career
        self.tid = int(tid)

        self.rc_hdr  = Rect(20, 20, 860, 50)
        self.rc_list = Rect(20, 80, 860, 460)
        self.rc_btns = Rect(20, 550, 860, 50)

        self.row_h = 28
        self.scroll = 0

        x = self.rc_btns.x
        self.btn_save = Button(Rect(x, self.rc_btns.y + 8, 140, 34), "Save", self._save)
        self.btn_back = Button(Rect(x + 160, self.rc_btns.y + 8, 140, 34), "Back", self._back)
        self._buttons = [self.btn_save, self.btn_back]

        # Load existing focus map
        self.focus_store: Dict[str, Dict[str, float]] = {}
        staff = getattr(self.career, "staff", {}) or {}
        if isinstance(staff, dict):
            self.focus_store = dict(staff.get("training_focus", {}))

        team = _team_by_tid(getattr(self.career, "teams", []), self.tid)
        self.fighters: List[Dict[str, Any]] = list(team.get("fighters", []))

    # events
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEWHEEL and self.rc_list.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            # Hit-test +/- for DEX focus
            area = Rect(self.rc_list.x + 8, self.rc_list.y + 40, self.rc_list.w - 16, self.rc_list.h - 48)
            if area.collidepoint(mx, my):
                start = self.scroll
                max_rows = area.h // self.row_h
                rows = self.fighters[start:start+max_rows]
                for i, p in enumerate(rows):
                    y = area.y + i*self.row_h
                    pid = str(p.get("pid", p.get("id", 0)))
                    key = f"{self.tid}:{pid}"
                    dex = float(self.focus_store.get(key, {}).get("DEX", 0.5))
                    # button rects
                    rc_minus = Rect(area.x + 420, y + 4, 22, 20)
                    rc_plus  = Rect(area.x + 478, y + 4, 22, 20)
                    if rc_minus.collidepoint(mx, my):
                        dex = _clamp01(dex - 0.1)
                        self.focus_store[key] = {"DEX": dex, "STR": 1.0 - dex}
                        break
                    if rc_plus.collidepoint(mx, my):
                        dex = _clamp01(dex + 0.1)
                        self.focus_store[key] = {"DEX": dex, "STR": 1.0 - dex}
                        break
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill((12,12,16))
        team = _team_by_tid(getattr(self.career, "teams", []), self.tid)
        name = team.get("name", f"Team {self.tid}")

        panel(screen, self.rc_hdr)
        draw_text(screen, f"Training Focus — {name}", self.rc_hdr.x + 10, self.rc_hdr.y + 12, size=22)

        panel(screen, self.rc_list, color=(24,24,28))
        draw_text(screen, "Click - / + to adjust DEX % (STR is 100 - DEX).", self.rc_list.x + 10, self.rc_list.y + 10, size=18)
        self._draw_rows(screen)

        for b in self._buttons:
            b.draw(screen)

    def _draw_rows(self, screen):
        area = Rect(self.rc_list.x + 8, self.rc_list.y + 40, self.rc_list.w - 16, self.rc_list.h - 48)
        pygame.draw.rect(screen, (18,18,22), area, border_radius=6)
        cols = [("PID", 60), ("Name", 220), ("DEX %", 120), ("STR %", 120)]
        # header
        x = area.x + 10; y = area.y + 6
        cx = x
        for title, w in cols:
            draw_text(screen, title, cx, y, (220,220,230), 18); cx += w
        y += 26

        start = self.scroll
        max_rows = (area.h - 32) // self.row_h
        rows = self.fighters[start:start+max_rows]
        for p in rows:
            pid = str(p.get("pid", p.get("id", 0)))
            key = f"{self.tid}:{pid}"
            dex = float(self.focus_store.get(key, {}).get("DEX", 0.5))
            dexp = int(round(dex*100))
            strp = 100 - dexp

            cx = x
            draw_text(screen, pid, cx, y, (230,230,235), 18); cx += cols[0][1]
            draw_text(screen, str(p.get("name","?")), cx, y, (230,230,235), 18); cx += cols[1][1]

            # DEX row with - / +
            draw_text(screen, f"{dexp}%", cx, y, (230,230,235), 18)
            pygame.draw.rect(screen, (60,60,80), Rect(cx + 80, y + 4, 22, 20), border_radius=4)
            draw_text(screen, "-", cx + 86, y + 4, (255,255,255), 18)
            pygame.draw.rect(screen, (60,60,80), Rect(cx + 138, y + 4, 22, 20), border_radius=4)
            draw_text(screen, "+", cx + 143, y + 4, (255,255,255), 18)
            cx += cols[2][1]

            draw_text(screen, f"{strp}%", cx, y, (230,230,235), 18)

            y += self.row_h

    # actions
    def _save(self):
        # Ensure staff dict
        if not isinstance(self.career.staff, dict):
            self.career.staff = {}
        # Persist
        self.career.staff["training_focus"] = dict(self.focus_store)

    def _back(self):
        self.app.pop_state()
