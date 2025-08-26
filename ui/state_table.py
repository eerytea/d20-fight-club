# ui/state_table.py — Standings with gridlines, equal spacing, and scrolling
from __future__ import annotations

from typing import List, Dict, Any

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font

# Try to use the project helper if available
def _get_rows_from_career(career) -> List[Dict[str, Any]]:
    try:
        # Preferred helper
        from core.standings import table_rows_sorted  # type: ignore
        return list(table_rows_sorted(career))
    except Exception:
        # Fallbacks to keep UI resilient
        if hasattr(career, "standings_rows"):
            return list(career.standings_rows())
        if hasattr(career, "table_rows_sorted"):
            return list(career.table_rows_sorted())
        # Last resort: zeroed rows from teams list
        out = []
        for i, t in enumerate(getattr(career, "teams", [])):
            nm = t.get("name", f"Team {i+1}") if isinstance(t, dict) else getattr(t, "name", f"Team {i+1}")
            tid = t.get("tid", i) if isinstance(t, dict) else getattr(t, "tid", i)
            out.append({"tid": int(tid), "name": nm, "PL": 0, "W": 0, "D": 0, "L": 0, "K": 0, "KD": 0, "PTS": 0})
        return out


class TableState(BaseState):
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        # Layout rects
        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        # UI
        self.btn_back: Button | None = None

        # Scroll
        self.scroll_y = 0
        self.row_h = 28
        self.header_h = 36

        # Fonts
        self.f_hdr = get_font(26)
        self.f_cell = get_font(22)

        self._built = False

    def enter(self) -> None:
        self._build()

    # ---------- layout ----------
    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 64

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 3))

        # Back button in toolbar
        bw, bh = 180, 46
        by = self.rect_toolbar.y + (self.rect_toolbar.h - bh) // 2
        self.btn_back = Button(pygame.Rect(self.rect_toolbar.x, by, bw, bh), "Back", self._back)

        self._built = True

    # ---------- actions ----------
    def _back(self) -> None:
        self.app.pop_state()

    # ---------- events ----------
    def handle(self, event) -> None:
        self.btn_back.handle(event)

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect_panel.collidepoint(mx, my):
                self.scroll_y = max(0, self.scroll_y - event.y * (self.row_h * 3))
                self._clamp_scroll()

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        self.btn_back.update((mx, my))

    # ---------- drawing ----------
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        # centered title
        title = "Standings"
        tr = self.f_hdr.get_rect(title)
        tr.center = (self.rect_toolbar.centerx, self.rect_toolbar.centery)
        self.f_hdr.render_to(surf, tr.topleft, title, th.text)
        self.btn_back.draw(surf, th)

        # Table panel
        draw_panel(surf, self.rect_panel, th)

        inner = self.rect_panel.inflate(-12*2, -12*2)
        # Reserve header strip (sticky)
        header_rect = pygame.Rect(inner.x, inner.y, inner.w, self.header_h)
        body_rect   = pygame.Rect(inner.x, header_rect.bottom, inner.w, inner.h - self.header_h)

        # Compute columns: fixed numeric columns + flexible Team column
        # Order: Pos | Team | P | W | D | L | K | KD | PTS
        fixed_cols = [
            ("Pos", 56, "right"),
            ("P",   44, "right"),
            ("W",   44, "right"),
            ("D",   44, "right"),
            ("L",   44, "right"),
            ("K",   44, "right"),
            ("KD",  60, "right"),
            ("PTS", 64, "right"),
        ]
        fixed_w = sum(w for _, w, _ in fixed_cols)
        # 8 vertical separators for fixed cols + 1 for team + left boundary don't require extra width:
        team_w = max(100, inner.w - fixed_w)
        cols = [("Pos", 56, "right"), ("Team", team_w, "left")] + fixed_cols[1:]

        # Precompute x positions
        x = inner.x
        col_boxes = []
        for name, w, align in cols:
            col_boxes.append((name, pygame.Rect(x, 0, w, 0), align))
            x += w

        # Draw header background & text
        pygame.draw.rect(surf, (*th.panel,), header_rect, border_radius=6)
        grid = th.subt  # gridline color

        # Header text
        for (name, r, _align) in col_boxes:
            cr = pygame.Rect(r.x, header_rect.y, r.w, header_rect.h)
            # Vertical gridlines in header
            pygame.draw.line(surf, grid, (cr.right, cr.top), (cr.right, cr.bottom), 1)
            txt = name
            txtr = self.f_hdr.get_rect(txt)
            if name == "Team":
                txtr.midleft = (cr.x + 10, cr.centery)
            elif name == "Pos":
                txtr.midright = (cr.right - 10, cr.centery)
            else:
                txtr.midright = (cr.right - 10, cr.centery)
            self.f_hdr.render_to(surf, txtr.topleft, txt, th.text)

        # Bottom header line
        pygame.draw.line(surf, grid, (header_rect.x, header_rect.bottom), (header_rect.right, header_rect.bottom), 1)

        # Rows (scrollable body)
        saved = surf.get_clip()
        surf.set_clip(body_rect)

        rows = _get_rows_from_career(self.career)
        y = body_rect.y - self.scroll_y
        for idx, row in enumerate(rows, start=1):
            row_rect = pygame.Rect(body_rect.x, int(y), body_rect.w, self.row_h)

            # Alternating row background for readability
            if (idx % 2) == 0:
                pygame.draw.rect(surf, (th.panel[0], th.panel[1], th.panel[2],), row_rect)

            # Cell rectangles and vertical gridlines
            cy = row_rect.y
            for (name, base_r, align) in col_boxes:
                cr = pygame.Rect(base_r.x, cy, base_r.w, self.row_h)

                # draw vertical gridline (right edge)
                pygame.draw.line(surf, grid, (cr.right, cr.top), (cr.right, cr.bottom), 1)

                # text content
                if name == "Pos":
                    txt = f"{idx}."
                elif name == "Team":
                    txt = str(row.get("name", "—"))
                else:
                    key = name if name in ("PTS", "KD") else {
                        "P": "PL", "W": "W", "D": "D", "L": "L", "K": "K"
                    }.get(name, name)
                    val = row.get(key, 0)
                    txt = str(val)

                txtr = self.f_cell.get_rect(txt)
                if name == "Team":
                    txtr.midleft = (cr.x + 10, cr.centery)
                elif align == "right":
                    txtr.midright = (cr.right - 10, cr.centery)
                else:
                    txtr.center = cr.center
                self.f_cell.render_to(surf, txtr.topleft, txt, self.theme.text)

            # Horizontal gridline under each row
            pygame.draw.line(surf, grid, (row_rect.x, row_rect.bottom), (row_rect.right, row_rect.bottom), 1)

            y += self.row_h

        surf.set_clip(saved)

        # Outer border (optional subtle line around inner area)
        pygame.draw.rect(surf, grid, inner, 1, border_radius=6)

    # ---------- utils ----------
    def _clamp_scroll(self) -> None:
        rows = _get_rows_from_career(self.career)
        content_h = len(rows) * self.row_h
        max_scroll = max(0, content_h - (self.rect_panel.h - 12*2 - self.header_h))
        self.scroll_y = max(0, min(self.scroll_y, max_scroll))
