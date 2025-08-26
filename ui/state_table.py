# ui/state_table.py — Standings: one-row-one-line, crisp grid, auto-fit
from __future__ import annotations

from typing import List, Dict, Any, Tuple
import math
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font


def _rows_from_career(career) -> List[Dict[str, Any]]:
    try:
        from core.standings import table_rows_sorted  # type: ignore
        return list(table_rows_sorted(career))
    except Exception:
        if hasattr(career, "standings_rows"):
            return list(career.standings_rows())
        if hasattr(career, "table_rows_sorted"):
            return list(career.table_rows_sorted())
        out = []
        for i, t in enumerate(getattr(career, "teams", []), start=1):
            nm = t.get("name", f"Team {i}") if isinstance(t, dict) else getattr(t, "name", f"Team {i}")
            tid = t.get("tid", i) if isinstance(t, dict) else getattr(t, "tid", i)
            out.append({"tid": int(tid), "name": nm, "PL": 0, "W": 0, "D": 0, "L": 0, "K": 0, "KD": 0, "PTS": 0})
        return out


def _ellipsize(font, text: str, max_w: int) -> str:
    if font.get_rect(text).width <= max_w:
        return text
    s = text
    while s and font.get_rect(s + "…").width > max_w:
        s = s[:-1]
    return (s + "…") if s else "…"


class TableState(BaseState):
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None

        # Sizing (computed each draw to fit neatly)
        self.header_h = 32
        self.row_h    = 26
        self.scroll_y = 0
        self.scroll_enabled = False

        self.f_title = get_font(24)
        self.f_hdr   = get_font(22)
        self.f_cell  = get_font(20)

        self._built = False

    def enter(self) -> None:
        self._build()

    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 60

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 3))

        bw, bh = 160, 42
        by = self.rect_toolbar.y + (self.rect_toolbar.h - bh) // 2
        self.btn_back = Button(pygame.Rect(self.rect_toolbar.x, by, bw, bh), "Back", self._back)

        self._built = True

    def _back(self) -> None:
        self.app.pop_state()

    def handle(self, event) -> None:
        self.btn_back.handle(event)
        if event.type == pygame.MOUSEWHEEL and self.scroll_enabled:
            mx, my = pygame.mouse.get_pos()
            if self.rect_panel.collidepoint(mx, my):
                self.scroll_y = max(0, self.scroll_y - event.y * (self.row_h * 3))
                self._clamp_scroll()

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        self.btn_back.update((mx, my))

    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        title = "Standings"
        tr = self.f_title.get_rect(title); tr.center = self.rect_toolbar.center
        self.f_title.render_to(surf, tr.topleft, title, th.text)
        self.btn_back.draw(surf, th)

        # Table panel & inner
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-12*2, -12*2)

        header_rect = pygame.Rect(inner.x, inner.y, inner.w, self.header_h)
        body_rect   = pygame.Rect(inner.x, header_rect.bottom, inner.w, inner.h - self.header_h)

        rows = _rows_from_career(self.career)
        n = max(1, len(rows))

        # Compute a row height that fits all rows, within sane bounds
        ideal_rh = math.floor(body_rect.h / n)
        self.row_h = max(22, min(32, ideal_rh))

        # Font sizes proportional to row height (kept readable)
        self.f_hdr   = get_font(max(18, min(26, int(self.row_h * 0.9))))
        self.f_cell  = get_font(max(16, min(24, int(self.row_h * 0.78))))
        self.f_title = get_font(max(22, min(28, int(self.header_h * 0.8))))

        # Only enable scroll if we can’t fit even with min row height
        visible_rows = body_rect.h // self.row_h
        self.scroll_enabled = n > visible_rows

        # Column layout: Pos | Team | P | W | D | L | K | KD | PTS
        fixed_cols: List[Tuple[str, int, str]] = [
            ("Pos", 50, "right"),
            ("P",   40, "right"),
            ("W",   40, "right"),
            ("D",   40, "right"),
            ("L",   40, "right"),
            ("K",   40, "right"),
            ("KD",  56, "right"),
            ("PTS", 56, "right"),
        ]
        fixed_w = sum(w for _, w, _ in fixed_cols)
        team_w  = max(140, inner.w - fixed_w)
        columns = [("Pos", 50, "right"), ("Team", team_w, "left")] + fixed_cols[1:]

        # x positions for vertical gridlines
        xs = [inner.x]
        for _, w, _ in columns:
            xs.append(xs[-1] + w)

        # Gridline thickness (slightly thicker for row lines so they POP)
        grid_col = th.subt
        row_line_w = 2  # <- makes every row separator obvious

        # HEADER
        pygame.draw.rect(surf, (*th.panel,), header_rect, border_radius=4)
        for i, (name, w, align) in enumerate(columns):
            cell = pygame.Rect(xs[i], header_rect.y, w, self.header_h)
            txtr = self.f_hdr.get_rect(name)
            if name == "Team":
                txtr.midleft = (cell.x + 10, cell.centery)
            elif align == "right":
                txtr.midright = (cell.right - 10, cell.centery)
            else:
                txtr.center = cell.center
            self.f_hdr.render_to(surf, txtr.topleft, name, th.text)
        # Header gridlines
        for x in xs:
            pygame.draw.line(surf, grid_col, (x, header_rect.top), (x, header_rect.bottom), 1)
        pygame.draw.line(surf, grid_col, (header_rect.left, header_rect.bottom), (header_rect.right, header_rect.bottom), 1)

        # BODY
        saved = surf.get_clip()
        surf.set_clip(body_rect)

        y = body_rect.y - (self.scroll_y if self.scroll_enabled else 0)
        for idx, row in enumerate(rows, start=1):
            row_rect = pygame.Rect(body_rect.x, int(y), body_rect.w, self.row_h)

            # Subtle alternating fill
            if (idx % 2) == 0:
                pygame.draw.rect(surf, (th.panel[0], th.panel[1], th.panel[2]), row_rect)

            # cells
            for i, (name, w, align) in enumerate(columns):
                cell = pygame.Rect(xs[i], row_rect.y, w, self.row_h)
                if name == "Pos":
                    txt = f"{idx}."
                elif name == "Team":
                    txt = _ellipsize(self.f_cell, str(row.get("name", "—")), w - 14)
                else:
                    key = name if name in ("PTS", "KD") else {"P": "PL", "W": "W", "D": "D", "L": "L", "K": "K"}.get(name, name)
                    txt = str(row.get(key, 0))
                txtr = self.f_cell.get_rect(txt)
                if name == "Team":
                    txtr.midleft = (cell.x + 10, cell.centery)
                elif align == "right":
                    txtr.midright = (cell.right - 10, cell.centery)
                else:
                    txtr.center = cell.center
                self.f_cell.render_to(surf, txtr.topleft, txt, th.text)

            # Horizontal gridline **after every single row**
            pygame.draw.line(surf, grid_col, (row_rect.left, row_rect.bottom), (row_rect.right, row_rect.bottom), row_line_w)

            y += self.row_h

        # Vertical gridlines down the body
        for x in xs:
            pygame.draw.line(surf, grid_col, (x, body_rect.top), (x, body_rect.bottom), 1)

        surf.set_clip(saved)

        # Border around inner area
        pygame.draw.rect(surf, grid_col, inner, 1, border_radius=6)

    def _clamp_scroll(self) -> None:
        rows = _rows_from_career(self.career)
        inner = self.rect_panel.inflate(-12*2, -12*2)
        body_h = inner.h - self.header_h
        content_h = len(rows) * self.row_h
        max_scroll = max(0, content_h - body_h)
        self.scroll_y = max(0, min(self.scroll_y, max_scroll))
