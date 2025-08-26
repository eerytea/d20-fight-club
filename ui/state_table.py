# ui/state_table.py — Fixed 9×21 grid (no scroll), real team names, perfect fit
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font

# ---- helpers ---------------------------------------------------------------

def _team_name_map(career) -> Dict[int, str]:
    m: Dict[int, str] = {}
    teams = getattr(career, "teams", []) or []
    for t in teams:
        if isinstance(t, dict):
            tid = int(t.get("tid", -1))
            nm  = str(t.get("name", f"Team {tid}"))
        else:
            tid = int(getattr(t, "tid", -1))
            nm  = str(getattr(t, "name", f"Team {tid}"))
        if tid >= 0:
            m[tid] = nm
    return m

def _rows_from_career(career) -> List[Dict[str, Any]]:
    """
    Normalize rows for the UI. Read whatever the core produces and convert to:
      {tid, name, P, W, D, L, K, KD, PTS}
    - K  ← GF (or kills/for)
    - KD ← GD (goal/kill diff)
    - If D/L absent: derive for 3-1-0 (PTS = 3*W + D; L = P-W-D)
    """
    name_by_tid = _team_name_map(career)

    rows_raw: List[Dict[str, Any]] = []
    try:
        from core.standings import table_rows_sorted  # type: ignore
        # Try common signatures
        try:
            rows_raw = list(table_rows_sorted(career))
        except TypeError:
            # Older/newer variants may accept (table, h2h)
            rows_raw = list(table_rows_sorted(getattr(career, "table", None), getattr(career, "h2h", None)))  # type: ignore
    except Exception:
        rows_raw = []

    norm: List[Dict[str, Any]] = []
    if not rows_raw:
        # Safe fallback from career.teams
        teams = getattr(career, "teams", []) or []
        for t in teams:
            if isinstance(t, dict):
                tid = int(t.get("tid", -1))
                nm  = str(t.get("name", f"Team {tid}"))
            else:
                tid = int(getattr(t, "tid", -1))
                nm  = str(getattr(t, "name", f"Team {tid}"))
            norm.append({"tid": tid, "name": nm, "P":0,"W":0,"D":0,"L":0,"K":0,"KD":0,"PTS":0})
        return norm

    for r in rows_raw:
        # Accept multiple key shapes
        tid = int(r.get("tid", r.get("id", -1)))
        P   = int(r.get("P",   r.get("PL", r.get("played", 0))))
        W   = int(r.get("W",   r.get("wins", 0)))
        PTS = int(r.get("PTS", r.get("points", 0)))
        GF  = int(r.get("GF",  r.get("K", r.get("for", 0))))
        GA  = int(r.get("GA",  r.get("against", 0)))
        GD  = int(r.get("GD",  r.get("KD", GF - GA)))

        # Derive D/L when missing
        D   = int(r.get("D", max(0, PTS - 3*W)))
        L   = int(r.get("L", max(0, P - W - D)))

        nm  = r.get("name")
        if not nm or nm.startswith("Team "):
            nm = name_by_tid.get(tid, nm or f"Team {tid}")

        norm.append({"tid": tid, "name": nm, "P": P, "W": W, "D": D, "L": L, "K": GF, "KD": GD, "PTS": PTS})
    return norm

# ---- state -----------------------------------------------------------------

class TableState(BaseState):
    """9 columns × 21 rows (1 header + 20 teams), no scrolling, crisp grid."""
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None

        self.f_title = get_font(28)
        self.f_hdr   = get_font(22)
        self.f_cell  = get_font(20)

    # lifecycle
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

    def _back(self) -> None:
        self.app.pop_state()

    # events/update
    def handle(self, event) -> None:
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        self.btn_back.update(pygame.mouse.get_pos())

    # draw
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        title = "Standings"
        tr = self.f_title.get_rect(title); tr.center = self.rect_toolbar.center
        self.f_title.render_to(surf, tr.topleft, title, th.text)
        self.btn_back.draw(surf, th)

        # Panel
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-24, -24)

        # Grid geometry
        ROWS = 21     # 1 header + 20 teams
        COLS = 9
        # Subtract 1px to ensure bottom border fits inside panel
        row_h = max(22, (inner.h - 1) // ROWS)

        # Fonts sized to row height
        self.f_hdr  = get_font(max(18, min(26, int(row_h * 0.85))))
        self.f_cell = get_font(max(16, min(24, int(row_h * 0.80))))

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

        grid = th.grid
        line_w = 1

        # Header
        header_rect = pygame.Rect(inner.x, inner.y, inner.w, row_h)
        pygame.draw.rect(surf, th.panel, header_rect)
        headers = ["Pos", "Team", "P", "W", "D", "L", "K", "KD", "PTS"]
        for i, (name, w, align) in enumerate(columns):
            cell = pygame.Rect(xs[i], header_rect.y, w, row_h)
            txt = headers[i]
            r = self.f_hdr.get_rect(txt)
            if name == "Team":     r.topleft  = (cell.x + 10, cell.y + (row_h - r.height)//2)
            elif align == "right": r.topright = (cell.right - 10, cell.y + (row_h - r.height)//2)
            else:                  r.center   = cell.center
            self.f_hdr.render_to(surf, r.topleft, txt, th.text)

        for x in xs:
            pygame.draw.line(surf, grid, (x, header_rect.top), (x, header_rect.bottom), line_w)
        pygame.draw.line(surf, grid, (header_rect.left, header_rect.bottom), (header_rect.right, header_rect.bottom), line_w)

        # Body
        y = header_rect.bottom
        rows = _rows_from_career(self.career)[:20]
        while len(rows) < 20:
            rows.append({"name": "—", "P":0,"W":0,"D":0,"L":0,"K":0,"KD":0,"PTS":0})

        for idx, row in enumerate(rows, start=1):
            row_rect = pygame.Rect(inner.x, y, inner.w, row_h)
            for i, (name, w, align) in enumerate(columns):
                cell = pygame.Rect(xs[i], row_rect.y, w, row_h)
                if name == "Pos":
                    txt = f"{idx}."
                elif name == "Team":
                    txt = str(row.get("name", "—"))
                    # ellipsize if needed
                    if self.f_cell.get_rect(txt).width > w - 14:
                        s = txt
                        while s and self.f_cell.get_rect(s + "…").width > w - 14:
                            s = s[:-1]
                        txt = (s + "…") if s else "…"
                else:
                    txt = str(row.get(name, 0))

                r = self.f_cell.get_rect(txt)
                if name == "Team":     r.topleft  = (cell.x + 10, cell.y + (row_h - r.height)//2)
                elif align == "right": r.topright = (cell.right - 10, cell.y + (row_h - r.height)//2)
                else:                  r.center   = cell.center
                self.f_cell.render_to(surf, r.topleft, txt, th.text)

            pygame.draw.line(surf, grid, (row_rect.left, row_rect.bottom), (row_rect.right, row_rect.bottom), line_w)
            y += row_h

        body_top = header_rect.bottom
        body_bottom = header_rect.bottom + 20 * row_h
        for x in xs:
            pygame.draw.line(surf, grid, (x, body_top), (x, body_bottom), line_w)

        pygame.draw.rect(surf, grid, inner, 1, border_radius=6)
