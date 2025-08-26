# ui/state_table.py — Standings fixed 9x21 grid (1 header + 20 teams), no scroll, crisp gridlines
from __future__ import annotations

from typing import List, Dict, Any, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font


# Pull standings rows from core; fall back gracefully if helper is absent
def _rows_from_career(career) -> List[Dict[str, Any]]:
    try:
        from core.standings import table_rows_sorted  # type: ignore
        return list(table_rows_sorted(career))
    except Exception:
        # Fallbacks keep UI resilient
        if hasattr(career, "standings_rows"):
            return list(career.standings_rows())
        if hasattr(career, "table_rows_sorted"):
            return list(career.table_rows_sorted())
        out = []
        for i, t in enumerate(getattr(career, "teams", []), start=1):
            if isinstance(t, dict):
                nm, tid = t.get("name", f"Team {i}"), t.get("tid", i)
            else:
                nm, tid = getattr(t, "name", f"Team {i}"), getattr(t, "tid", i)
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
    """
    Fixed grid:
      rows: 21 (1 header + 20 teams)
      cols: 9  (POS, Team, P, W, D, L, K, KD, PTS)
    Always fits inside the panel; no scrolling.
    """

    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        # Layout
        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        # UI
        self.btn_back: Button | None = None

        # Fonts (sized at draw-time to fit the cell height)
        self.f_title = get_font(26)
        self.f_hdr   = get_font(22)
        self.f_cell  = get_font(20)

        self._built = False

    # ---------- lifecycle ----------
    def enter(self) -> None:
        self._build()

    def _build(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 64

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 3))

        # Back button
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

    def update(self, dt: float) -> None:
        self.btn_back.update(pygame.mouse.get_pos())

    # ---------- drawing ----------
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        title = "Standings"
        tr = self.f_title.get_rect(title)
        tr.center = self.rect_toolbar.center
        self.f_title.render_to(surf, tr.topleft, title, th.text)
        self.btn_back.draw(surf, th)

        # Table panel
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-12*2, -12*2)

        # --- Grid sizing: 9 columns x 21 rows (1 header + 20 teams) ---
        ROWS = 21
        COLS = 9
        # Compute row height to fill inner exactly
        row_h = max(20, inner.h // ROWS)  # min readable
        # Recompute fonts to fit rows nicely
        self.f_hdr  = get_font(max(18, min(26, int(row_h * 0.85))))
        self.f_cell = get_font(max(16, min(24, int(row_h * 0.80))))
        self.f_title = get_font( max(24, min(32, int(row_h * 1.0))) )

        # Column widths: numeric columns fixed; Team expands to fill the rest
        # POS, P, W, D, L, K, KD, PTS
        fixed_cols: List[Tuple[str, int, str]] = [
            ("Pos", 52, "right"),
            ("P",   44, "right"),
            ("W",   44, "right"),
            ("D",   44, "right"),
            ("L",   44, "right"),
            ("K",   44, "right"),
            ("KD",  64, "right"),
            ("PTS", 64, "right"),
        ]
        fixed_w = sum(w for _, w, _ in fixed_cols)
        team_w  = max(140, inner.w - fixed_w)
        columns = [("Pos", 52, "right"), ("Team", team_w, "left")] + fixed_cols[1:]

        # Compute column x positions
        xs = [inner.x]
        for _, w, _ in columns:
            xs.append(xs[-1] + w)

        # Colors & line width
        grid_col = th.subt
        line_w = 1  # grid thickness

        # Fetch latest rows EVERY draw so results are current
        rows = _rows_from_career(self.career)

        # --------- Draw header row (y = 0) ----------
        hdr_rect = pygame.Rect(inner.x, inner.y, inner.w, row_h)
        # header background
        pygame.draw.rect(surf, (*th.panel,), hdr_rect)
        # header text
        headers = ["Pos", "Team", "P", "W", "D", "L", "K", "KD", "PTS"]
        for i, (name, w, align) in enumerate(columns):
            cell = pygame.Rect(xs[i], hdr_rect.y, w, row_h)
            txt = headers[i]
            txtr = self.f_hdr.get_rect(txt)
            if name == "Team":
                txtr.midleft = (cell.x + 10, cell.centery)
            elif align == "right":
                txtr.midright = (cell.right - 10, cell.centery)
            else:
                txtr.center = cell.center
            self.f_hdr.render_to(surf, txtr.topleft, txt, th.text)

        # vertical lines in header
        for x in xs:
            pygame.draw.line(surf, grid_col, (x, hdr_rect.top), (x, hdr_rect.bottom), line_w)
        # bottom line under header
        pygame.draw.line(surf, grid_col, (hdr_rect.left, hdr_rect.bottom), (hdr_rect.right, hdr_rect.bottom), line_w)

        # --------- Draw team rows (rows 1..20) ----------
        y = hdr_rect.bottom
        # Exactly 20 data rows shown; if fewer teams, blank rows fill; if more, extra are truncated
        total_teams = 20
        # ensure deterministic order & lengths
        rows = list(rows)[:total_teams]
        # Pad to 20 with blanks if needed
        while len(rows) < total_teams:
            rows.append({"name": "—", "PL": 0, "W": 0, "D": 0, "L": 0, "K": 0, "KD": 0, "PTS": 0})

        for idx, row in enumerate(rows, start=1):
            row_rect = pygame.Rect(inner.x, y, inner.w, row_h)

            # very subtle alternating fill to help tracking
            if (idx % 2) == 0:
                pygame.draw.rect(surf, (th.panel[0], th.panel[1], th.panel[2]), row_rect)

            # cells per column
            for i, (name, w, align) in enumerate(columns):
                cell = pygame.Rect(xs[i], row_rect.y, w, row_h)

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

            # horizontal line under this team (one team → one line)
            pygame.draw.line(surf, grid_col, (row_rect.left, row_rect.bottom), (row_rect.right, row_rect.bottom), line_w)

            y += row_h

        # Final vertical gridlines down the body
        body_top = hdr_rect.bottom
        body_bottom = hdr_rect.bottom + total_teams * row_h
        for x in xs:
            pygame.draw.line(surf, grid_col, (x, body_top), (x, body_bottom), line_w)

        # outer border around inner table
        pygame.draw.rect(surf, grid_col, inner, 1, border_radius=6)
