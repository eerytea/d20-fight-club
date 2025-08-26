# ui/state_table.py — Fixed 9x21 grid (no scroll) + key mapping (K/KD, D/L derived)
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font


def _rows_from_career(career) -> List[Dict[str, Any]]:
    """
    Normalize rows for the UI. We accept either:
      - table_rows_sorted(table, h2h)
      - legacy table_rows_sorted(career) (we’ll detect & adapt)
    Then map keys to what the UI expects.
    """
    rows: List[Dict[str, Any]] = []
    try:
        # Preferred signature
        from core.standings import table_rows_sorted
        raw = table_rows_sorted(career.table, career.h2h)  # type: ignore[arg-type]
    except TypeError:
        # Back-compat: some earlier versions took (career)
        raw = table_rows_sorted(career)  # type: ignore[misc]
    except Exception:
        raw = []

    for r in raw:
        # source keys (present today): P, W, PTS, GF, GA, GD, name, tid
        P = int(r.get("P", r.get("played", 0)))
        W = int(r.get("W", r.get("wins", 0)))
        PTS = int(r.get("PTS", r.get("points", 0)))
        GF = int(r.get("GF", r.get("goals_for", 0)))
        GA = int(r.get("GA", r.get("goals_against", 0)))
        GD = int(r.get("GD", GF - GA))

        # Derive D/L for a 3-1-0 system: PTS = 3*W + 1*D
        D = max(0, min(P, PTS - 3 * W))
        L = max(0, P - W - D)

        rows.append({
            "tid": int(r.get("tid", -1)),
            "name": r.get("name", "Team"),
            "P": P,
            "W": W,
            "D": D,
            "L": L,
            "K": GF,    # kills shown as goals-for
            "KD": GD,   # kill diff shown as goal diff
            "PTS": PTS,
        })
    return rows


class TableState(BaseState):
    """
    Fixed grid:
      rows: 21 (1 header + 20 teams)
      cols: 9  (POS, Team, P, W, D, L, K, KD, PTS)
    """

    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None

        # Fonts sized at draw-time to fit the row height
        self.f_title = get_font(28)
        self.f_hdr   = get_font(22)
        self.f_cell  = get_font(20)

    # --- lifecycle ---
    def enter(self) -> None:
        self._layout()

    def _layout(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 64
        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 3))

        bw, bh = 180, 46
        by = self.rect_toolbar.y + (self.rect_toolbar.h - bh) // 2
        self.btn_back = Button(pygame.Rect(self.rect_toolbar.x, by, bw, bh), "Back", self._back)

    # --- actions ---
    def _back(self) -> None:
        self.app.pop_state()

    # --- events ---
    def handle(self, event) -> None:
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        self.btn_back.update(pygame.mouse.get_pos())

    # --- draw ---
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

        # Table container
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-24, -24)

        # Grid geometry
        ROWS = 21  # 1 header + 20 teams
        COLS = 9   # POS, Team, P, W, D, L, K, KD, PTS

        row_h = max(22, inner.h // ROWS)
        self.f_hdr  = get_font(max(18, min(26, int(row_h * 0.85))))
        self.f_cell = get_font(max(16, min(24, int(row_h * 0.80))))
        self.f_title = get_font(max(24, min(32, int(row_h * 1.0))))

        # Column widths
        fixed_cols: List[Tuple[str, int, str]] = [
            ("Pos", 56, "right"),
            ("P",   44, "right"),
            ("W",   44, "right"),
            ("D",   44, "right"),
            ("L",   44, "right"),
            ("K",   52, "right"),
            ("KD",  60, "right"),
            ("PTS", 64, "right"),
        ]
        fixed_w = sum(w for _, w, _ in fixed_cols)
        team_w  = max(160, inner.w - fixed_w)
        columns = [("Pos", 56, "right"), ("Team", team_w, "left")] + fixed_cols[1:]

        # Column x edges
        xs = [inner.x]
        for _, w, _ in columns:
            xs.append(xs[-1] + w)

        grid_col = th.subt
        line_w = 1

        # Header row
        header_rect = pygame.Rect(inner.x, inner.y, inner.w, row_h)
        pygame.draw.rect(surf, th.panel, header_rect)
        headers = ["Pos", "Team", "P", "W", "D", "L", "K", "KD", "PTS"]

        for i, (name, w, align) in enumerate(columns):
            cell = pygame.Rect(xs[i], header_rect.y, w, row_h)
            txt = headers[i]
            r = self.f_hdr.get_rect(txt)
            if name == "Team":
                r.midleft = (cell.x + 10, cell.centery)
            elif align == "right":
                r.midright = (cell.right - 10, cell.centery)
            else:
                r.center = cell.center
            self.f_hdr.render_to(surf, r.topleft, txt, th.text)

        for x in xs:
            pygame.draw.line(surf, grid_col, (x, header_rect.top), (x, header_rect.bottom), line_w)
        pygame.draw.line(surf, grid_col, (header_rect.left, header_rect.bottom), (header_rect.right, header_rect.bottom), line_w)

        # Body rows (always exactly 20)
        y = header_rect.bottom
        rows = _rows_from_career(self.career)[:20]
        while len(rows) < 20:
            rows.append({"name": "—", "P": 0, "W": 0, "D": 0, "L": 0, "K": 0, "KD": 0, "PTS": 0})

        for idx, row in enumerate(rows, start=1):
            row_rect = pygame.Rect(inner.x, y, inner.w, row_h)

            # Cells
            for i, (name, w, align) in enumerate(columns):
                cell = pygame.Rect(xs[i], row_rect.y, w, row_h)
                if name == "Pos":
                    txt = f"{idx}."
                elif name == "Team":
                    # ellipsize to fit
                    text = str(row.get("name", "—"))
                    if self.f_cell.get_rect(text).width > w - 14:
                        s = text
                        while s and self.f_cell.get_rect(s + "…").width > w - 14:
                            s = s[:-1]
                        txt = (s + "…") if s else "…"
                    else:
                        txt = text
                else:
                    txt = str(row.get(name, 0))

                r = self.f_cell.get_rect(txt)
                if name == "Team":
                    r.midleft = (cell.x + 10, cell.centery)
                elif align == "right":
                    r.midright = (cell.right - 10, cell.centery)
                else:
                    r.center = cell.center
                self.f_cell.render_to(surf, r.topleft, txt, th.text)

            # one line after each team
            pygame.draw.line(surf, grid_col, (row_rect.left, row_rect.bottom), (row_rect.right, row_rect.bottom), line_w)
            y += row_h

        # Vertical grid lines for the body
        body_top = header_rect.bottom
        body_bottom = header_rect.bottom + 20 * row_h
        for x in xs:
            pygame.draw.line(surf, grid_col, (x, body_top), (x, body_bottom), line_w)

        # Outer border
        pygame.draw.rect(surf, grid_col, inner, 1, border_radius=6)
