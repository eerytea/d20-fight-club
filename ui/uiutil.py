# ui/uiutil.py — tiny UI kit: Theme, Button, ListView, text/panel helpers
from __future__ import annotations

from typing import Callable, List, Optional, Tuple
import pygame
import pygame.freetype

# --------------- FONTS ---------------

_FONT_CACHE: dict[int, pygame.freetype.Font] = {}

def get_font(size: int) -> pygame.freetype.Font:
    """Cached freetype font (system default)."""
    if size not in _FONT_CACHE:
        # SysFont(None, size) picks a default; stable in headless and Windows
        _FONT_CACHE[size] = pygame.freetype.SysFont(None, size)
        # Slightly tighter baseline for crisper UI text
        _FONT_CACHE[size].pad = True
    return _FONT_CACHE[size]


# --------------- THEME ---------------

class Theme:
    """Centralized colors used across screens."""
    def __init__(self):
        # Background and panels
        self.bg: Tuple[int, int, int]     = (20, 22, 26)
        self.panel: Tuple[int, int, int]  = (34, 37, 44)

        # Text
        self.text: Tuple[int, int, int]   = (230, 230, 236)
        self.subt: Tuple[int, int, int]   = (168, 173, 182)

        # Accents
        self.accent: Tuple[int, int, int] = (70, 110, 190)   # selection / primary
        self.accent2: Tuple[int, int, int]= (90, 130, 210)

        # List row highlight fill
        self.sel_row: Tuple[int, int, int]= (70, 110, 190)

        # Buttons
        self.btn_bg: Tuple[int, int, int] = (52, 56, 64)
        self.btn_hover: Tuple[int, int, int] = (62, 66, 74)
        self.btn_text: Tuple[int, int, int]  = self.text

        # Panel borders / grid lines (subtle)
        self.grid: Tuple[int, int, int] = self.subt


# --------------- TEXT/PANEL HELPERS ---------------

def draw_text(
    surf: pygame.Surface,
    text: str,
    pos: Tuple[int, int],
    size: int,
    color: Tuple[int, int, int],
    align: str = "center",
) -> None:
    """
    Render text using freetype with alignment.
    align: 'center', 'topleft', 'topright', 'bottomleft', 'bottomright',
           'midleft', 'midright', 'left', 'right'
    For 'left'/'right', we anchor at midleft/midright using the given (x,y).
    """
    fnt = get_font(int(size))
    rect = fnt.get_rect(text)

    ax = align.lower()
    if ax == "left":
        rect.midleft = pos
    elif ax == "right":
        rect.midright = pos
    elif ax in ("center", "topleft", "topright", "bottomleft", "bottomright", "midleft", "midright"):
        setattr(rect, ax, pos)
    else:
        rect.center = pos

    fnt.render_to(surf, rect.topleft, text, color)


def draw_panel(surf: pygame.Surface, rect: pygame.Rect, theme: Theme, radius: int = 8) -> None:
    """Rounded panel with a subtle border."""
    pygame.draw.rect(surf, theme.panel, rect, border_radius=radius)
    pygame.draw.rect(surf, theme.grid,  rect, width=1, border_radius=radius)


# --------------- BUTTON ---------------

class Button:
    def __init__(self, rect: pygame.Rect, label: str, onclick: Callable[[], None] | None = None, *,
                 font_size: int = 22):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.onclick = onclick
        self.enabled = True
        self.hovered = False
        self._font_size = font_size

    def handle(self, event) -> None:
        if not self.enabled:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if callable(self.onclick):
                    self.onclick()

    def update(self, mouse_pos: Tuple[int, int]) -> None:
        self.hovered = self.enabled and self.rect.collidepoint(mouse_pos)

    def draw(self, surf: pygame.Surface, theme: Theme) -> None:
        col = theme.btn_hover if self.hovered else theme.btn_bg
        pygame.draw.rect(surf, col, self.rect, border_radius=10)
        pygame.draw.rect(surf, theme.grid, self.rect, width=1, border_radius=10)
        draw_text(
            surf,
            self.label,
            (self.rect.centerx, self.rect.centery),
            self._font_size,
            theme.btn_text,
            align="center",
        )


# --------------- LISTVIEW ---------------

class ListView:
    """
    Scrollable, selectable list with reliable clipping and selection.
    - Pass `on_select(index)` to get click callbacks.
    - Use `draw(..., top_offset=...)` to leave space for a header you draw outside.
    """
    def __init__(
        self,
        rect: pygame.Rect,
        items: List[str],
        row_h: int = 28,
        on_select: Callable[[int], None] | None = None,
    ):
        self.rect = pygame.Rect(rect)
        self.items = items[:]
        self.row_h = int(row_h)
        self.scroll = 0
        self.selected = 0 if items else -1
        self.on_select = on_select
        self._last_top = self.rect.y + 8  # set during draw()

    def set_items(self, items: List[str]):
        self.items = items[:]
        self.scroll = 0
        self.selected = 0 if items else -1

    def handle(self, event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll = max(0, self.scroll - event.y * self.row_h * 3)
                self._clamp_scroll()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self._last_top + self.scroll
                idx = int(rel_y // self.row_h)
                if 0 <= idx < len(self.items):
                    self.selected = idx
                    if callable(self.on_select):
                        self.on_select(idx)

    def update(self, _mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        # Present for API compatibility with states; nothing needed here.
        pass

    def _clamp_scroll(self) -> None:
        inner_h = self.rect.h - 16  # symmetric 8px padding top/bottom
        content_h = len(self.items) * self.row_h
        max_scroll = max(0, content_h - inner_h)
        if self.scroll > max_scroll:
            self.scroll = max_scroll
        if self.scroll < 0:
            self.scroll = 0

    def draw(self, surf: pygame.Surface, theme: Theme, *, top_offset: int = 8, font_size: int = 20) -> None:
        """
        Draws only the list content area inside `self.rect` (caller draws panel/header).
        top_offset: pixels from rect.y to start the first row (to leave space for a title).
        """
        # Store for click mapping
        self._last_top = self.rect.y + int(top_offset)

        # Compute inner content rect (clipping)
        inner_x = self.rect.x + 8
        inner_y = self._last_top
        inner_w = self.rect.w - 16
        inner_h = (self.rect.bottom - 8) - inner_y  # NOTE: height, not bottom-y
        inner = pygame.Rect(inner_x, inner_y, inner_w, max(0, inner_h))

        clip = surf.get_clip()
        surf.set_clip(inner)

        # Draw rows
        y = inner_y - self.scroll
        for i, it in enumerate(self.items):
            row_rect = pygame.Rect(inner_x, int(y), inner_w, self.row_h)
            if i == self.selected:
                pygame.draw.rect(surf, theme.sel_row, row_rect, border_radius=6)
            draw_text(surf, str(it), (row_rect.x + 8, row_rect.y + self.row_h // 2), font_size, theme.text, align="left")
            y += self.row_h

        surf.set_clip(clip)
