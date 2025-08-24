# ui/state_settings.py
from __future__ import annotations

import json, os

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

try:
    from .uiutil import Button
except Exception:
    Button = None  # type: ignore

from .state_message import MessageState


SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves", "settings.json")


class SettingsState:
    def __init__(self, app):
        self.app = app
        self._title_font = None
        self._font = None
        self._small = None

        self.resolutions = [(1280, 720), (1366, 768), (1600, 900), (1920, 1080)]
        self.res_index = 0
        self.volume = 0.7

        self._btn_apply = self._btn_back = self._btn_res_prev = self._btn_res_next = None

    def enter(self):
        if pygame is None: return
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 26)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small = pygame.font.SysFont("consolas", 14)
        self._load_settings()
        self._layout()

    def _layout(self):
        w, h = self.app.width, self.app.height
        btn_w, btn_h, gap = 150, 40, 10
        by = h - 64
        bx = w - 24 - btn_w
        mk = lambda label, fn, x: (Button(pygame.Rect(x, by, btn_w, btn_h), label, on_click=fn)
                                   if Button else _SimpleButton(pygame.Rect(x, by, btn_w, btn_h), label, fn))
        self._btn_back = mk("Back", self._back, bx); bx -= (btn_w + gap)
        self._btn_apply = mk("Apply", self._apply, bx); bx -= (btn_w + gap)
        self._btn_res_next = mk("Res Next", self._res_next, bx); bx -= (btn_w + gap)
        self._btn_res_prev = mk("Res Prev", self._res_prev, bx)

    def handle_event(self, e):
        if pygame is None: return False
        for b in (self._btn_res_prev, self._btn_res_next, self._btn_apply, self._btn_back):
            if b and b.handle_event(e): return True
        # mouse wheel to adjust volume if over volume bar
        if e.type == pygame.MOUSEWHEEL:
            self.volume = min(1.0, max(0.0, self.volume + e.y * 0.05))
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self._vol_rect.collidepoint(e.pos):
                rel = (e.pos[0] - self._vol_rect.x) / self._vol_rect.w
                self.volume = min(1.0, max(0.0, rel))
                return True
        return False

    def update(self, dt): pass

    def draw(self, surf):
        if pygame is None: return
        w, h = surf.get_size()
        title = self._title_font.render("Settings", True, (255,255,255))
        surf.blit(title, (24, 24))

        # Resolution
        res = self.resolutions[self.res_index]
        surf.blit(self._font.render(f"Resolution: {res[0]} x {res[1]} (use Res Prev/Next)", True, (230,230,230)), (40, 100))

        # Volume bar
        surf.blit(self._font.render("Master Volume (scroll or click):", True, (230,230,230)), (40, 150))
        self._vol_rect = pygame.Rect(40, 180, 320, 18)
        pygame.draw.rect(surf, (60,60,60), self._vol_rect, border_radius=8)
        fill_w = int(self._vol_rect.w * self.volume)
        pygame.draw.rect(surf, (80,200,80), (self._vol_rect.x, self._vol_rect.y, fill_w, self._vol_rect.h), border_radius=8)

        for b in (self._btn_res_prev, self._btn_res_next, self._btn_apply, self._btn_back):
            if b: b.draw(surf)

    # actions

    def _apply(self):
        # apply resolution
        res = self.resolutions[self.res_index]
        try:
            if hasattr(self.app, "apply_resolution"):
                self.app.apply_resolution(res)
            else:
                pygame.display.set_mode(res)  # type: ignore
                self.app.width, self.app.height = res
        except Exception as e:
            self._msg(f"Resolution apply failed:\n{e}")

        # apply volume
        try:
            pygame.mixer.init()  # safe if already inited
            pygame.mixer.music.set_volume(self.volume)
        except Exception:
            pass

        self._save_settings()
        self._msg("Settings applied and saved.")

    def _res_prev(self):
        self.res_index = (self.res_index - 1) % len(self.resolutions)

    def _res_next(self):
        self.res_index = (self.res_index + 1) % len(self.resolutions)

    def _back(self): self.app.pop_state()

    def _msg(self, text:str):
        self.app.push_state(MessageState(app=self.app, text=text))

    # persistence
    def _load_settings(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.res_index = int(data.get("res_index", self.res_index))
                self.volume = float(data.get("volume", self.volume))
        except Exception:
            pass

    def _save_settings(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump({"res_index": self.res_index, "volume": self.volume}, f)
        except Exception:
            pass


class _SimpleButton:
    def __init__(self, rect, label, on_click):
        self.rect, self.label, self.on_click = rect, label, on_click
        self.hover=False; self._font=pygame.font.SysFont("consolas",18) if pygame else None
    def handle_event(self,e):
        if e.type==pygame.MOUSEMOTION: self.hover=self.rect.collidepoint(e.pos)
        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and self.rect.collidepoint(e.pos):
            self.on_click(); return True
        return False
    def draw(self,surf):
        bg=(120,120,120) if self.hover else (98,98,98)
        pygame.draw.rect(surf,bg,self.rect,border_radius=6)
        pygame.draw.rect(surf,(50,50,50),self.rect,2,border_radius=6)
        t=self._font.render(self.label,True,(20,20,20))
        surf.blit(t,(self.rect.x+(self.rect.w-t.get_width())//2,self.rect.y+(self.rect.h-t.get_height())//2))
