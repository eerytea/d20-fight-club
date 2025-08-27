from __future__ import annotations

import os, json, glob, datetime
import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

# UI kit fallbacks
try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
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

# Career + migrator bits
try:
    from core.career import Career
except Exception:
    Career = None  # type: ignore

try:
    from core.migrate import SCHEMA_VERSION
except Exception:
    SCHEMA_VERSION = "unknown"

SAVE_DIR = "saves"

def _ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def _list_saves() -> List[str]:
    _ensure_dir(SAVE_DIR)
    files = glob.glob(os.path.join(SAVE_DIR, "*.json"))
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files

def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

class SaveLoadState:
    """
    Simple Save/Load screen.
    - New Career
    - Save Now (timestamped filename in saves/)
    - Load Latest (or click any from the list, then 'Load Selected')
    """
    def __init__(self, app):
        self.app = app
        self.toast = ""
        self.toast_timer = 0.0

        self.rc_hdr  = Rect(20, 20, 860, 60)
        self.rc_list = Rect(20, 90, 580, 470)
        self.rc_btns = Rect(620, 90, 260, 470)
        self.rc_back = Rect(20, 570, 860, 40)

        self.row_h = 26
        self.scroll = 0
        self.selected_idx = -1
        self._refresh_files()

        # Buttons
        x, y = self.rc_btns.x + 10, self.rc_btns.y + 10
        w, h, g = 240, 36, 10
        self.btn_new    = Button(Rect(x, y, w, h), "New Career", self._new_career); y += h + g
        self.btn_save   = Button(Rect(x, y, w, h), "Save Now", self._save_now); y += h + g
        self.btn_load_l = Button(Rect(x, y, w, h), "Load Latest", self._load_latest); y += h + g
        self.btn_load_s = Button(Rect(x, y, w, h), "Load Selected", self._load_selected); y += h + g
        self.btn_refresh= Button(Rect(x, y, w, h), "Refresh List", self._refresh_files); y += h + g

        self.btn_back   = Button(Rect(self.rc_back.x, self.rc_back.y, 160, 36), "Back", self._back)

        self._buttons = [self.btn_new, self.btn_save, self.btn_load_l, self.btn_load_s, self.btn_refresh, self.btn_back]

    def _refresh_files(self):
        self.files = _list_saves()
        if self.selected_idx >= len(self.files):
            self.selected_idx = -1

    # ------------- events -------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._back(); return
        if ev.type == pygame.MOUSEWHEEL and self.rc_list.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, self.scroll - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            # pick from list
            list_area = Rect(self.rc_list.x + 8, self.rc_list.y + 34, self.rc_list.w - 16, self.rc_list.h - 42)
            if list_area.collidepoint(mx, my):
                idx = (my - list_area.y) // self.row_h + self.scroll
                if 0 <= idx < len(self.files):
                    self.selected_idx = idx
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt):
        if self.toast_timer > 0:
            self.toast_timer -= dt
            if self.toast_timer <= 0:
                self.toast = ""

    # ------------- drawing -------------
    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        draw_text(screen, f"Save / Load — schema {SCHEMA_VERSION}", self.rc_hdr.x + 10, self.rc_hdr.y + 12, size=22)

        panel(screen, self.rc_list, color=(24,24,28))
        draw_text(screen, "Saved games (newest first)", self.rc_list.x + 10, self.rc_list.y + 8, size=18)
        self._draw_list(screen)

        panel(screen, self.rc_btns, color=(24,24,28))
        for b in self._buttons:
            b.draw(screen)

        if self.toast:
            # tiny toast in header
            draw_text(screen, self.toast, self.rc_hdr.x + 520, self.rc_hdr.y + 18, (240,240,240), 18)

    def _draw_list(self, screen):
        area = Rect(self.rc_list.x + 8, self.rc_list.y + 34, self.rc_list.w - 16, self.rc_list.h - 42)
        pygame.draw.rect(screen, (18,18,22), area, border_radius=6)
        max_rows = area.h // self.row_h
        start = self.scroll
        rows = self.files[start:start+max_rows]
        for i, path in enumerate(rows):
            y = area.y + i*self.row_h
            if (start + i) == self.selected_idx:
                pygame.draw.rect(screen, (60,60,90), Rect(area.x+2, y+1, area.w-4, self.row_h-2), border_radius=4)
            name = os.path.basename(path)
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                mtime = "?"
            draw_text(screen, f"{name}   —  {mtime}", area.x + 8, y + 4, size=18)

    # ------------- actions -------------
    def _toast(self, text: str):
        self.toast = text
        self.toast_timer = 2.0

    def _back(self):
        self.app.pop_state()

    def _new_career(self):
        if Career is None:
            self._toast("Career module missing.")
            return
        try:
            self.app.career = Career.new(seed=12345, n_teams=20, team_size=5, user_team_id=0)
            self._toast("New career created.")
        except Exception:
            self._toast("Failed to create career.")

    def _save_now(self):
        car = getattr(self.app, "career", None)
        if not car:
            self._toast("No career to save.")
            return
        try:
            _ensure_dir(SAVE_DIR)
            path = os.path.join(SAVE_DIR, f"d20fc_{_timestamp()}.json")
            data = car.to_dict()
            # add schema_version if not present
            data.setdefault("schema_version", SCHEMA_VERSION)
            _save_json(path, data)
            self._refresh_files()
            self._toast(f"Saved: {os.path.basename(path)}")
        except Exception:
            self._toast("Save failed.")

    def _load_latest(self):
        files = _list_saves()
        if not files:
            self._toast("No saves found.")
            return
        self._load_path(files[0])

    def _load_selected(self):
        if 0 <= self.selected_idx < len(self.files):
            self._load_path(self.files[self.selected_idx])
        else:
            self._toast("Select a save first.")

    def _load_path(self, path: str):
        if Career is None:
            self._toast("Career module missing.")
            return
        try:
            data = _load_json(path)
            self.app.career = Career.from_dict(data)  # migrator + bootstrap happens inside
            self._toast(f"Loaded: {os.path.basename(path)}")
        except Exception:
            self._toast("Load failed.")
