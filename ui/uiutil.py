# ui/uiutil.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple, Optional, List

import pygame
import pygame.freetype as ft

# --- Fonts & text (freetype-based, Windows-safe) -----------------------------

_font_cache: dict[int, ft.Font] = {}

def _ensure_init():
    if not pygame.get_init():
        pygame.init()
    if not ft.get_init():
        ft.init()

def get_font(size: int) -> ft.Font:
    _ensure_init()
    size = int(size)
    f = _font_cache.get(size)
    if f is None:
        # Default font via freetype is far more robust than SysFont on Windows
        _font_cache[size] = f = ft.Font(None, size)
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
      align="center"           -> centerx=pos[0], top=pos[1] (headline style)
      also supports any pygame.Rect anchor: "center","midtop","midleft",
      "midright","midbottom","topleft","topright","bottomleft","bottomright"
    """
    font = get_font(size)
    text = str(text)

    # Measure first to position accurately
    r = font.get_rect(text, size=size)

    if not align or align == "topleft":
        r.topleft = pos
    elif align == "center":
        # Keep prior behavior used across states: centered horizontally, top anchored
        r.midtop = (pos[0], pos[1])
    elif hasattr(r, align):
        setattr(r, align, pos)
    else:
        r.topleft = pos

    font.render_to(surf, r.topleft, text, color, size=size)

# --- Simple theme ------------------------------------------------------------

@dataclass
class Theme:
    bg: Tuple[int, int, int] = (20, 24, 28)
    panel: Tuple[int, int, int] = (30, 35, 40)
    panel_border: Tuple[int, int, int] = (50, 55, 60)
    text: Tuple[int, int, int] = (220, 225, 230)
    subt: Tuple[int, int, int] = (190, 195, 205)
    button_bg: Tuple[int, int, int] = (45, 50, 58)
    button_hover: Tuple[int, int, int] = (65, 72, 84)
    button_text: Tuple[int, int, int] = (230, 232, 236)
    sel_row: Tuple[int, int, int] = (55, 60, 75)

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

        # Centered label via freetype
        font = get_font(24)
        r = font.get_rect(self.label)
        r.center = self.rect.center
        font.render_to(surf, r.topleft, self.label, theme.button_text)

class ListView:
    """
    Simple scrollable, selectable list.
    """
    def __init__(
        self,
        rect: pygame.Rect,
        items: List[str],
        row_h: int = 28,
        on_select: Callable[[int], None] | None = None
    ):
        self.rect = pygame.Rect(rect)
        self.items = items[:]
        self.row_h = int(row_h)
        self.scroll = 0
        self.selected = 0 if items else -1
        self.on_select = on_select

    def set_items(self, items: List[str]):
        self.items = items[:]
        self.scroll = 0
        self.selected = 0 if items else -1

    def handle(self, event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * self.row_h)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.rect.y + self.scroll
                idx = rel_y // self.row_h
                if 0 <= idx < len(self.items):
                    self.selected = int(idx)
                    if callable(self.on_select):
                        self.on_select(self.selected)

    def draw(self, surf: pygame.Surface, theme: Theme, title: str | None = None) -> None:
        clip = surf.get_clip()
        draw_panel(surf, self.rect, theme)

        if title:
            draw_text(surf, title, (self.rect.centerx, self.rect.y + 6), 20, theme.subt, align="center")
            top = self.rect.y + 28
        else:
            top = self.rect.y + 8

        inner = pygame.Rect(self.rect.x + 8, top, self.rect.w - 16, self.rect.bottom - 8)
        surf.set_clip(inner)

        y = top - self.scroll
        for i, it in enumerate(self.items):
            row_rect = pygame.Rect(inner.x, y, inner.w, self.row_h)
            if i == self.selected:
                pygame.draw.rect(surf, theme.sel_row, row_rect, border_radius=6)
            draw_text(surf, str(it), (row_rect.x + 8, row_rect.y + 5), 20, theme.text)
            y += self.row_h

        surf.set_clip(clip)
