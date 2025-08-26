# ui/state_table.py — 9×21 grid, fonts reduced slightly to fit the panel
from __future__ import annotations
from typing import Dict, List, Any, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font


def _team_name_map(career) -> Dict[int, str]:
    m: Dict[int, str] = {}
    for t in getattr(career, "teams", []) or []:
        if isinstance(t, dict):
            tid = int(t.get("tid", -1)); nm = str(t.get("name", f"Team {tid}"))
        else:
            tid = int(getattr(t, "tid", -1)); nm = str(getattr(t, "name", f"Team {tid}"))
        if tid >= 0: m[tid] = nm
    return m

def _rows_from_career(career) -> List[Dict[str, Any]]:
    name_by_tid = _team_name_map(career)
    rows_raw: List[Dict[str, Any]] = []

    try:
        from core.standings import table_rows_sorted  # type: ignore
        try:
            rows_raw = list(table_rows_sorted(career))
        except TypeError:
            rows_raw = list(table_rows_sorted(getattr(career, "table", None), getattr(career, "h2h", None)))  # type: ignore
    except Exception:
        rows_raw = []

    if not rows_raw:
        # Safe fallback
        teams = getattr(career, "teams", []) or []
        return [{"tid": int(_t.get("tid", -1) if isinstance(_t, dict) else getattr(_t, "tid", -1)),
                 "name": str(_t.get("name", "Team") if isinstance(_t, dict) else getattr(_t, "name", "Team")),
                 "P": 0, "W": 0, "D": 0, "L": 0, "K": 0, "KD": 0, "PTS": 0}
                for _t in teams]

    norm: List[Dict[str, Any]] = []
    for r in rows_raw:
        tid = int(r.get("tid", r.get("id", -1)))
        P   = int(r.get("P",   r.get("PL", r.get("played", 0))))
        W   = int(r.get("W",   r.get("wins", 0)))
        PTS = int(r.get("PTS", r.get("points", 0)))
        GF  = int(r.get("GF",  r.get("K", r.get("for", 0))))
        GA  = int(r.get("GA",  r.get("against", 0)))
        GD  = int(r.get("GD",  r.get("KD", GF - GA)))
        D   = int(r.get("D", max(0, PTS - 3*W)))
        L   = int(r.get("L", max(0, P - W - D)))
        name = r.get("name") or name_by_tid.get(tid, f"Team {tid}")
        norm.append({"tid": tid, "name": name, "P": P, "W": W, "D": D, "L": L, "K": GF, "KD": GD, "PTS": PTS})
    return norm


class TableState(BaseState):
    """Fixed 9 columns × 21 rows (1 header + 20 teams), slightly smaller fonts."""
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None

        self.f_title = get_font(26)  # down 2
        self.f_hdr   = get_font(20)  # down 2
        self.f_cell  = get_font(18)  # down 2

    def enter(self) -> None:
        self._layout()

    def _layout(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 64
        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 3))

        bw, bh = 160, 44
        by = self.rect_toolbar.y + (self.rect_toolbar.h - bh) // 2
        self.btn_back = Button(pygame.Rect(self.rect_toolbar.x, by, bw, bh), "Back", self._back)

    def _back(self) -> None:
        self.app.pop_state()

    def handle(self, event) -> None:
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        self.btn_back.update(pygame.mouse.get_pos())

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

        ROWS = 21  # header + 20
        COLS = 9
        # Give a tad more breathing room than before
        row_h = max(21, (inner.h - 4) // ROWS)

        # Fonts scaled off row_h, then nudged down 1
        self.f_hdr  = get_font(max(16, min(24, int(row_h * 0.82))) - 1)
        self.f_cell = get_font(max(14, min(22, int(row_h * 0.78))) - 1)

        fixed_cols: List[Tuple[str, int, str]] = [
            ("Pos", 54, "right"),
            ("P",   42, "right"),
            ("W",   42, "right"),
            ("D",   42, "right"),
            ("L",   42, "right"),
            ("K",   50, "right"),
            ("KD",  58, "right"),
            ("PTS", 60, "right"),
        ]
        fixed_w = sum(w for _, w, _ in fixed_cols)
        team_w  = max(150, inner.w - fixed_w)
        columns = [("Pos", 54, "right"), ("Team", team_w, "left")] + fixed_cols[1:]

        xs = [inner.x]
        for _, w, _ in columns:
            xs.append(xs[-1] + w)

        grid = th.grid
        line_w = 1

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
