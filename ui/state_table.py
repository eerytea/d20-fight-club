# ui/state_table.py — standings table with grid lines and better name fallback
from __future__ import annotations
from typing import Dict, List, Any, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, get_font, draw_text


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _safe_int(v, default: int = -1) -> int:
    try:
        if v is None: return default
        return int(v)
    except Exception:
        return default

def _team_id_from(obj: Any, default: int = -1) -> int:
    for k in ("tid", "team_id", "id", "index"):
        val = _get(obj, k, None)
        if val is not None:
            try:
                return int(val)
            except Exception:
                pass
    return default

def _name_from(obj: Any, default: str = "Team") -> str:
    for k in ("name", "full_name", "display_name", "abbr", "short"):
        v = _get(obj, k, None)
        if v:
            return str(v)
    return default

def _team_name_map(career) -> Dict[int, str]:
    m: Dict[int, str] = {}
    if hasattr(career, "team_name"):
        for t in getattr(career, "teams", []) or []:
            tid = _team_id_from(t, -1)
            if tid >= 0:
                try: m[tid] = str(career.team_name(tid))
                except Exception: pass
    if m:
        return m

    for t in getattr(career, "teams", []) or []:
        tid = _team_id_from(t, -1)
        nm = _name_from(t, f"Team {tid}")
        if tid >= 0:
            m[tid] = nm

    tn = getattr(career, "team_names", None)
    if isinstance(tn, dict):
        for k, v in tn.items():
            try: m[int(k)] = str(v)
            except Exception: pass
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
        return [{"tid": _team_id_from(_t, -1),
                 "name": name_by_tid.get(_team_id_from(_t, -1), _name_from(_t, "Team")),
                 "P": 0, "W": 0, "D": 0, "L": 0, "K": 0, "KD": 0, "PTS": 0}
                for _t in teams]

    norm: List[Dict[str, Any]] = []
    for r in rows_raw:
        tid = _safe_int(r.get("tid", r.get("id", _get(r, "tid", -1))), -1)
        name = r.get("name") or r.get("team") or name_by_tid.get(tid, f"Team {tid}")
        P   = _safe_int(r.get("P", r.get("PL", r.get("played", r.get("Gp", 0)))), 0)
        W   = _safe_int(r.get("W", r.get("wins", 0)), 0)
        D   = _safe_int(r.get("D", r.get("draws", r.get("ties", 0))), 0)
        L   = _safe_int(r.get("L", r.get("losses", 0)), 0)
        GF  = _safe_int(r.get("K", r.get("GF", r.get("for", 0))), 0)
        GA  = _safe_int(r.get("GA", r.get("against", 0)), 0)
        KD  = _safe_int(r.get("KD", r.get("GD", GF - GA)), GF - GA)
        PTS = _safe_int(r.get("PTS", r.get("points", 3*W + D)), 3*W + D)
        norm.append({"tid": tid, "name": name, "P": P, "W": W, "D": D, "L": L, "K": GF, "KD": KD, "PTS": PTS})
    return norm

def _ellipsize(font, text: str, max_w: int) -> str:
    if not text:
        return ""
    t = text
    # freetype.Font.get_rect works without specifying size
    while font.get_rect(t).width > max_w and len(t) > 1:
        t = t[:-1]
    if t != text and len(t) >= 1:
        if len(t) > 1:
            t = t[:-1] + "…"
        else:
            t = "…"
    return t


class TableState(BaseState):
    """Fixed 9 columns × 21 rows (1 header + 20 teams)."""
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)

        self.btn_back: Button | None = None

        self.f_title = get_font(26)
        self.f_hdr   = get_font(20)
        self.f_cell  = get_font(18)

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

        # Data
        rows = _rows_from_career(self.career)
        # ensure max 20 teams visually (header + 20 rows)
        rows = rows[:20]

        # Grid metrics
        ROWS = 1 + len(rows)  # header + teams
        COLS = 9
        row_h = max(21, (inner.h - 4) // max(ROWS, 1))

        # Font sizing to fit comfortably
        self.f_hdr  = get_font(max(16, min(24, int(row_h * 0.82))) - 1)
        self.f_cell = get_font(max(14, min(22, int(row_h * 0.78))) - 1)

        # Column widths
        fixed_cols: List[Tuple[str, int, str]] = [
            ("Pos", 54, "right"),
            ("P",   44, "right"),
            ("W",   44, "right"),
            ("D",   44, "right"),
            ("L",   44, "right"),
            ("K",   54, "right"),
            ("KD",  60, "right"),
            ("PTS", 66, "right"),
        ]
        fixed_w = sum(w for _, w, _ in fixed_cols)
        team_w  = max(160, inner.w - fixed_w)
        columns = [("Pos", 54, "right"), ("Team", team_w, "left")] + fixed_cols[1:]

        # Column x positions
        xs = [inner.x]
        for _, w, _ in columns:
            xs.append(xs[-1] + w)

        # Colors
        grid_color = getattr(th, "grid", (72, 72, 72))
        line_w = 1

        # Draw header background
        header_rect = pygame.Rect(inner.x, inner.y, inner.w, row_h)
        pygame.draw.rect(surf, th.panel, header_rect)

        # Header labels
        headers = ["Pos", "Team", "P", "W", "D", "L", "K", "KD", "PTS"]
        for ci, (label, width, align) in enumerate(columns):
            cx = xs[ci]
            cell_rect = pygame.Rect(cx, inner.y, width, row_h)
            text_pos = (cell_rect.right - 6, cell_rect.centery) if align == "right" else (cell_rect.x + 6, cell_rect.centery)
            draw_text(surf, headers[ci], text_pos, self.f_hdr.size, th.text, align="midright" if align == "right" else "midleft")

        # Horizontal line below header
        pygame.draw.line(surf, grid_color, (inner.x, inner.y + row_h), (inner.right, inner.y + row_h), line_w)

        # Team rows
        for ri, r in enumerate(rows):
            y = inner.y + row_h * (ri + 1)
            # grid line for each row
            pygame.draw.line(surf, grid_color, (inner.x, y + row_h), (inner.right, y + row_h), line_w)

            pos = ri + 1
            name = str(r.get("name", f"Team {r.get('tid', ri)}"))
            P = r.get("P", 0); W = r.get("W", 0); D = r.get("D", 0); L = r.get("L", 0)
            K = r.get("K", 0); KD = r.get("KD", 0); PTS = r.get("PTS", 0)

            vals = [pos, name, P, W, D, L, K, KD, PTS]
            # draw cells
            for ci, (col, width, align) in enumerate(columns):
                cx = xs[ci]
                rect = pygame.Rect(cx, y, width, row_h)
                if ci == 1:  # Team col, ellipsize
                    t = _ellipsize(self.f_cell, str(vals[ci]), width - 12)
                    posxy = (rect.x + 6, rect.centery)
                    draw_text(surf, t, posxy, self.f_cell.size, th.text, align="midleft")
                else:
                    t = str(vals[ci])
                    posxy = (rect.right - 6, rect.centery) if align == "right" else (rect.x + 6, rect.centery)
                    draw_text(surf, t, posxy, self.f_cell.size, th.text, align="midright" if align == "right" else "midleft")

        # Vertical grid lines
        for xi in xs:
            pygame.draw.line(surf, grid_color, (xi, inner.y), (xi, inner.y + row_h * ROWS), line_w)

        # Outer border
        pygame.draw.rect(surf, grid_color, pygame.Rect(inner.x, inner.y, inner.w, row_h * ROWS), line_w)


def create(app, career):
    return TableState(app, career)
