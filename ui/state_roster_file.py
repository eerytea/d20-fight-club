# ui/state_roster_browser.py
from __future__ import annotations

import pygame
from typing import List, Dict, Optional, Any, Tuple
import random

# ----- Try to use your UI kit. Provide simple fallbacks if it's missing. -----
try:
    from .uiutil import Theme, Button, ListView, draw_panel, draw_text
    HAS_UIKIT = True
except Exception:
    HAS_UIKIT = False
    # Minimal fallbacks (basic look) — used only if uiutil isn't available.
    class Theme:
        def __init__(self):
            self.bg = (20, 24, 28)
            self.panel = (32, 36, 44)
            self.text = (230, 230, 235)
            self.accent = (90, 140, 255)
            self.btn_bg = (50, 55, 64)
            self.btn_bg_hover = (70, 75, 84)
            self.btn_text = (240, 240, 245)
        @staticmethod
        def default():
            return Theme()

    def draw_panel(surf, rect, title=None):
        pygame.draw.rect(surf, (32, 36, 44), rect, border_radius=8)
        if title:
            font = pygame.font.SysFont(None, 20)
            txt = font.render(title, True, (220, 220, 225))
            surf.blit(txt, (rect.x + 10, rect.y + 8))

    def draw_text(surf, text, pos, color=(230, 230, 235), size=18):
        font = pygame.font.SysFont(None, size)
        surf.blit(font.render(text, True, color), pos)

    class Button:
        def __init__(self, rect: pygame.Rect, text: str, on_click):
            self.rect = pygame.Rect(rect)
            self.text = text
            self.on_click = on_click
            self._hover = False
            self._font = pygame.font.SysFont(None, 22)
