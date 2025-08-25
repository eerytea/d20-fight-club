# ui/uiutil.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence, Tuple, List

try:
    import pygame
except Exception:  # pragma: no cover
    pygame = None  # type: ignore


# ---------------------------- Theme & Fonts ----------------------------

@dataclass(frozen=True)
class Theme:
    bg: Tuple[int, int, int] = (22, 24, 28)
    panel: Tuple[int, int, int] = (34, 37, 43)
    panel_border: Tuple[int, int, int] = (55, 59, 66)
    accent: Tuple[int, int, int] = (60, 140, 255)
    accent_hover: Tuple[int, int, int] = (80, 160, 255)
    fg: Tuple[int, int, int] = (230, 233, 239)
    muted: Tuple[int, int, int] = (170, 175, 185)
    danger: Tuple[int, int, int] = (235, 80, 80)


_font_cache: dict[int, "pygame.font.Font"] = {}


def get_font(size: int) -> "pygame.font.Font":
    if pygame is None:
        raise RuntimeError("pygame not available")
    if size not in _font_cache:
        if not pygame.font.get_init():
            pygame.font.init()
        _font_cache[size] = pygame.font.SysFont(None, size)
    return _font_cache[size]


# ---------------------------- Drawing helpers ----------------------------

def draw_text(
    surface: "pygame.Surface",
    text: str,
    pos: Tuple[int, int],
    size: int = 22,
    color: Tuple[int, int, int] = Theme().fg,
    align: str = "topleft",
) -> "pygame.Rect":
    font = get_font(size)
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, align, pos)
    surface.blit(img, rect)
    return rect


def draw_panel(surface: "pygame.Surface", rect: "pygame.Rect", title: Optional[str] = None) -> None:
    th = Theme()
    pygame.draw.rect(surface, th.panel, rect, border_radius=12)
    pygame.draw.rect(surface, th.panel_border, rect, width=2, border_radius=12)
    if title:
        draw_text(surface, title, (rect.x + 12, rect.y + 8), size=20, color=th.muted)


# ---------------------------- Widgets ----------------------------

class Button:
    def __init__(
        self,
        rect: "pygame.Rect",
        label: str,
        on_click: Optional[Callable[[], None]] = None,
        *,
        enabled: bool = True,
    ) -> None:
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.enabled = enabled
        self._hover = False

    def handle_event(self, event: "pygame.event.Event") -> bool:
        if pygame is None:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.enabled and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface: "pygame.Surface") -> None:
        th = Theme()
        base = th.accent if self.enabled else th.panel_border
        fill = th.accent_hover if (self._hover and self.enabled) else base
        pygame.draw.rect(surface, fill, self.rect, border_radius=10)
        pygame.draw.rect(surface, th.panel_border, self.rect, width=2, border_radius=10)
        draw_text(
            surface,
            self.label,
            self.rect.center,
            size=22,
            color=(255, 255, 255) if self.enabled else th.muted,
            align="center",
        )


class ListView:
    """
    Simple vertical list; supports click to select and mouse wheel scrolling.
    items: Sequence[str] (rendered) but you can store your own 'data' alongside in your code.
    """
    def __init__(
        self,
        rect: "pygame.Rect",
        items: Sequence[str] | None = None,
        *,
        row_h: int = 28,
    ) -> None:
        self.rect = rect
        self.items: List[str] = list(items) if items else []
        self.row_h = row_h
        self.selected: int | None = None
        self.scroll: int = 0  # in rows

    def set_items(self, items: Sequence[str]) -> None:
        self.items = list(items)
        self.selected = None
        self.scroll = 0

    def _rows_visible(self) -> int:
        inner_h = self.rect.height - 16  # padding
        return max(1, inner_h // self.row_h)

    def _first_visible_index(self) -> int:
        return max(0, self.scroll)

    def _last_visible_index(self) -> int:
        return min(len(self.items), self._first_visible_index() + self._rows_visible())

    def index_at(self, pos: Tuple[int, int]) -> Optional[int]:
        x, y = pos
        if not self.rect.collidepoint(pos):
            return None
        inner_y = y - (self.rect.y + 8)
        idx = self._first_visible_index() + (inner_y // self.row_h)
        if self._first_visible_index() <= idx < self._last_visible_index():
            return idx
        return None

    def handle_event(self, event: "pygame.event.Event") -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self.index_at(event.pos)
            if idx is not None:
                self.selected = idx
                return True
        elif event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, min(max(0, len(self.items) - self._rows_visible()), self.scroll - event.y))
            return True
        return False

    def draw(self, surface: "pygame.Surface", title: Optional[str] = None) -> None:
        th = Theme()
        draw_panel(surface, self.rect, title=title)
        x = self.rect.x + 12
        y = self.rect.y + 8
        start = self._first_visible_index()
        end = self._last_visible_index()
        for i in range(start, end):
            label = self.items[i]
            row_rect = pygame.Rect(self.rect.x + 6, y - 2, self.rect.width - 12, self.row_h)
            if self.selected == i:
                pygame.draw.rect(surface, (70, 75, 85), row_rect, border_radius=6)
            draw_text(surface, label, (x, y), size=18, color=th.fg)
            y += self.row_h
