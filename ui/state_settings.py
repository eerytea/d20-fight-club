# ui/state_settings.py
from __future__ import annotations

import pygame
from typing import Optional

# Fallback Button (if not using shared UI kit)
class Button:
    def __init__(self, rect: pygame.Rect, label: str, cb, enabled: bool=True):
        self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        self.hover = False
    def handle_event(self, e):
        if not self.enabled: return False
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.cb(); return True
        return False
    def draw(self, screen):
        bg = (60, 60, 72) if self.enabled else (40, 40, 48)
        if self.hover and self.enabled: bg = (80, 80, 95)
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, (24, 24, 28), self.rect, 2, border_radius=8)
        font = pygame.font.SysFont(None, 22)
        txt = font.render(self.label, True, (235, 235, 240))
        screen.blit(txt, (self.rect.x + 14, self.rect.y + (self.rect.h - txt.get_height()) // 2))

class SettingsState:
    def __init__(self, app):
        self.app = app
        self.font = pygame.font.SysFont(None, 24)
        self.h1 = pygame.font.SysFont(None, 32)
        self._btn_res_prev: Optional[Button] = None
        self._btn_res_next: Optional[Button] = None
        self._btn_apply: Optional[Button] = None
        self._btn_back: Optional[Button] = None
        self._res_idx = 0
        self._res_opts = [(1024, 576), (1280, 720), (1600, 900), (1920, 1080)]

    def enter(self):
        self._layout()

    def _layout(self):
        w, h = self.app.screen.get_size()
        panel = pygame.Rect(24, 96, max(420, int(w * 0.35)), h - 120)
        btn_w, btn_h, gap = 160, 42, 12
        bx = panel.right - btn_w - 24; by = panel.bottom - btn_h - 16
        mk = lambda label, fn, x: (Button(pygame.Rect(x, by, btn_w, btn_h), label, fn))

        self._btn_back = mk("Back", self._back, bx); bx -= (btn_w + gap)
        self._btn_apply = mk("Apply", self._apply, bx); bx -= (btn_w + gap)
        self._btn_res_next = mk("Res Next", self._res_next, bx); bx -= (btn_w + gap)
        self._btn_res_prev = mk("Res Prev", self._res_prev, bx)

        self._panel = panel

    # --- events ---
    def handle(self, e):
        for b in (self._btn_res_prev, self._btn_res_next, self._btn_apply, self._btn_back):
            if b and b.handle_event(e): return
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._back()

    def update(self, dt: float):
        pass

    def draw(self, screen: pygame.Surface):
        w, h = screen.get_size()
        screen.fill((18, 18, 22))
        pygame.draw.rect(screen, (42, 44, 52), self._panel, border_radius=12)
        pygame.draw.rect(screen, (24, 24, 28), self._panel, 2, border_radius=12)

        title = self.h1.render("Settings", True, (235, 235, 240))
        screen.blit(title, (self._panel.x + 24, self._panel.y + 16))

        # Resolution preview
        cur = self._res_opts[self._res_idx]
        lbl = self.font.render(f"Resolution: {cur[0]} x {cur[1]}", True, (225, 225, 230))
        screen.blit(lbl, (self._panel.x + 24, self._panel.y + 64))

        for b in (self._btn_res_prev, self._btn_res_next, self._btn_apply, self._btn_back):
            if b: b.draw(screen)

    # --- actions ---
    def _res_prev(self): self._res_idx = (self._res_idx - 1) % len(self._res_opts)
    def _res_next(self): self._res_idx = (self._res_idx + 1) % len(self._res_opts)

    def _apply(self):
        w, h = self._res_opts[self._res_idx]
        self.app.screen = pygame.display.set_mode((w, h))
        self.app.width, self.app.height = w, h
        self._layout()

    def _back(self):
        self.app.pop_state()
