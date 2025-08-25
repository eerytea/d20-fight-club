# ui/uiutil.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple, Optional, List

import pygame

# --- Fonts & text ------------------------------------------------------------

_font_cache: dict[int, pygame.font.Font] = {}

def get_font(size: int) -> pygame.font.Font:
    size = int(size)
    f = _font_cache.get(size)
    if f is None:
        _font_cache[size] = f = pygame.font.SysFont(None, size)
    return f

def draw_text(
    surf: pygame.Surface,
    text: str,
    pos: Tuple[int, int],
    size: int = 24,
    color=(230, 232, 236),
    align: Optional[str] = None,
) -> None:
    """
    Draw text with optional alignment.
      align=None or "topleft"  -> pos is top-left (default)
      align="center"           -> centerx=pos[0], top=pos[1]
      also supports any pygame.Rect anchor name:
        "center","midtop","midleft","midright","midbottom",
        "topleft","topright","bottomleft","bottomright"
    """
    font = get_font(size)
    img = font.render(str(text), True, color)
    r = img.get_rect()

    if not align or align == "topleft":
        r.topleft = pos
    elif align == "center":
        # common pattern in states: x = surf.get_width()//2, y = some_top
        r.midtop = (pos[0], pos[1])
    elif hasattr(r, align):
        # generic anchor support
        setattr(r, align, pos)
    else:
        # fallback
        r.topleft = pos

    surf.blit(img, r)

# --- Simple theme ------------------------------------------------------------

@dataclass
class Theme:
    bg: Tuple[int, int, int] = (20, 24, 28)
    panel: Tuple[int, int, int] = (30, 35, 40)
    panel_border: Tuple[int, int, int] = (50, 55, 60)
    text: Tuple[int, int, int] = (220, 225, 230)
    button_bg: Tuple[int, int, int] = (45, 50, 58)
    button_hover: Tuple[int, int, int] = (65, 72, 84)
    button_text: Tuple[int, int, int] = (230, 232, 236)

def draw_panel(surf: pygame.Surface, rect: pygame.Rect, theme: Theme) -> None:
    pygame.draw.rect(surf, theme.panel, rect, border_radius=10)
    pygame.draw.rect(surf, theme.panel_border, rect, width=2, border_radius=10)

# --- Widgets ----------------------------------------------------------------

class Button:
    def __init__(self, rect: pygame.Rect, label: str, on_click: Callable[[], None] | None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self._hover = False
        self._pressed = False

    def update(self, mouse_pos) -> None:
        self._hover = self.rect.collidepoint(mouse_pos)

    def handle(self, event) -> None:
        # Keep hover accurate even if update() hasn't run yet this frame
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._hover = self.rect.collidepoint(event.pos)
            if self._hover:
                self._pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._hover = self.rect.collidepoint(event.pos)
            if self._pressed and self._hover and callable(self.on_click):
                try:
                    self.on_click()
                finally:
                    self._pressed = False
            else:
                self._pressed = False

    def draw(self, surf: pygame.Surface, theme: Theme) -> None:
        color = theme.button_hover if self._hover else theme.button_bg
        pygame.draw.rect(surf, color, self.rect, border_radius=12)
        pygame.draw.rect(surf, theme.panel_border, self.rect, width=2, border_radius=12)
        # Centered label
        font = get_font(24)
        img = font.render(self.label, True, theme.button_text)
        r = img.get_rect(center=self.rect.center)
        surf.blit(img, r)

class ListView:
    def __init__(self, rect: pygame.Rect, items: List[str], row_h: int = 26):
        self.rect = pygame.Rect(rect)
        self.items = items[:]
        self.row_h = row_h
        self.scroll = 0

    def set_items(self, items: List[str]):
        self.items = items[:]
        self.scroll = 0

    def handle(self, event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * self.row_h)

    def draw(self, surf: pygame.Surface, theme: Theme) -> None:
        clip = surf.get_clip()
        surf.set_clip(self.rect)
        draw_panel(surf, self.rect, theme)
        y = self.rect.y + 8 - self.scroll
        for it in self.items:
            draw_text(surf, str(it), (self.rect.x + 12, y), 20, theme.text)
            y += self.row_h
        surf.set_clip(clip)
