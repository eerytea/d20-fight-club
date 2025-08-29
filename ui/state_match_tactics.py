# ui/state_match_tactics.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import traceback

# --- Small shared Button ---
@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: callable
    hover: bool = False
    disabled: bool = False
    def draw(self, surf, font):
        bg = (58,60,70) if not self.hover else (76,78,90)
        if self.disabled: bg = (48,48,54)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, (24,24,28), self.rect, 2, border_radius=10)
        txt = font.render(self.text, True, (235,235,240) if not self.disabled else (160,160,165))
        surf.blit(txt, (self.rect.x + 14, self.rect.y + (self.rect.h - txt.get_height()) // 2))
    def handle(self, ev):
        if self.disabled: return
        if ev.type == pygame.MOUSEMOTION: self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            self.action()

# --- Helpers to grab grid settings from state_match (falls back to sane defaults) ---
def _match_grid_defaults():
    cols, rows, tile = 9, 5, 64
    try:
        import ui.state_match as sm  # type: ignore
        cols = getattr(sm, "GRID_COLS", getattr(sm, "BOARD_COLS", cols))
        rows = getattr(sm, "GRID_ROWS", getattr(sm, "BOARD_ROWS", rows))
        tile = getattr(sm, "TILE", getattr(sm, "TILE_SIZE", tile))
    except Exception:
        pass
    return int(cols), int(rows), int(tile)

def _team_fighters(career, tid: int) -> List[Dict[str,Any]]:
    for t in getattr(career, "teams", []):
        if int(t.get("tid", -1)) == int(tid):
            return t.get("fighters", [])
    return []

def _name(p: Dict[str,Any]) -> str:
    n = p.get("name") or p.get("full_name") or ""
    if n: return str(n)
    first = p.get("first_name") or p.get("firstName") or ""
    last  = p.get("last_name")  or p.get("lastName")  or ""
    return (first + " " + last).strip() or "Player"

def _ovr(p: Dict[str,Any]) -> int:
    return int(p.get("OVR", p.get("ovr", p.get("OVR_RATING", 60))))

def _shorten(text: str, max_len: int=16) -> str:
    return text if len(text) <= max_len else text[:max_len-1] + "…"

class MatchTacticsState:
    """
    Pre-match tactics: show the same grid as the match viewer (no units on it),
    and let the manager drag exactly 5 players from the bench (right panel) onto grid cells.
    On Next, we write a preset lineup into the fixture and push the MatchState.
    """
    def __init__(self, app, career, fixture):
        self.app = app
        self.career = career
        self.fixture = fixture

        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)

        self.grid_cols, self.grid_rows, self.tile = _match_grid_defaults()
        self.rect_board: Optional[pygame.Rect] = None
        self.rect_bench: Optional[pygame.Rect] = None
        self.btn_next: Optional[Button] = None
        self.btn_clear: Optional[Button] = None
        self.btn_back: Optional[Button] = None

        self.user_tid = int(getattr(self.career, "user_tid", 0))
        self.home_tid = int(self.fixture.get("home_id", self.fixture.get("home_tid", self.fixture.get("A", 0))))
        self.away_tid = int(self.fixture.get("away_id", self.fixture.get("away_tid", self.fixture.get("B", 0))))
        self.user_is_home = (self.user_tid == self.home_tid)

        self.bench: List[Dict[str,Any]] = list(_team_fighters(self.career, self.user_tid))
        self.placed: List[Dict[str,Any]] = []  # {pid, cx, cy, data}

        # dragging
        self.drag_src = None  # "bench" or "board"
        self.drag_idx = -1
        self.dragging: Optional[Dict[str,Any]] = None
        self.drag_offset = (0,0)
        self.mx_my = (0,0)

    def enter(self):
        w, h = self.app.screen.get_size()
        pad = 16

        board_w = self.grid_cols * self.tile
        board_h = self.grid_rows * self.tile
        bx = pad + 4
        by = self.h1.get_height() + pad*2 + 4
        self.rect_board = pygame.Rect(bx, by, board_w, board_h)

        bench_w = max(380, w - (self.rect_board.right + pad*3))
        self.rect_bench = pygame.Rect(self.rect_board.right + pad, self.rect_board.y, bench_w, self.rect_board.h)

        hdr = pygame.Rect(pad, pad, w - pad*2, self.h1.get_height() + 12)
        bw, bh, gap = 140, 40, 10
        self.btn_back  = Button(pygame.Rect(hdr.x+8, hdr.y+6, 110, bh), "Back", self._back)
        self.btn_clear = Button(pygame.Rect(hdr.right - (bw*2 + gap) - 8, hdr.y+6, bw, bh), "Clear", self._clear)
        self.btn_next  = Button(pygame.Rect(hdr.right - bw - 8, hdr.y+6, bw, bh), "Next", self._next)

    def handle(self, ev: pygame.event.Event):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE): self._back(); return
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):  self._next(); return
        if ev.type == pygame.MOUSEMOTION:
            self.mx_my = ev.pos
        for b in (self.btn_back, self.btn_clear, self.btn_next):
            if b: b.handle(ev)

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect_bench and self.rect_bench.collidepoint(ev.pos):
                idx = self._bench_index_at(ev.pos)
                if idx is not None and idx < len(self.bench):
                    self.drag_src = "bench"; self.drag_idx = idx
                    self.dragging = dict(self.bench[idx])
                    self.drag_offset = (0,0)
            elif self.rect_board and self.rect_board.collidepoint(ev.pos):
                hit = self._placed_at_pixel(ev.pos)
                if hit is not None:
                    self.drag_src = "board"; self.drag_idx = hit
                    self.dragging = dict(self.placed[hit])
                    cx, cy = self.dragging["cx"], self.dragging["cy"]
                    cell_rect = self._cell_rect(cx, cy)
                    mx,my = ev.pos
                    self.drag_offset = (cell_rect.x - mx, cell_rect.y - my)

        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self.dragging is not None:
                if self.rect_board and self.rect_board.collidepoint(ev.pos):
                    cx, cy = self._snap_to_cell(ev.pos)
                    if self._cell_occupied(cx, cy) is None:
                        self._place_dragging(cx, cy)
                    else:
                        self._cancel_drag()
                else:
                    self._cancel_drag()

    def update(self, dt: float):
        if self.btn_next:
            self.btn_next.disabled = (len(self.placed) != 5)

    def draw(self, screen: pygame.Surface):
        screen.fill((16,16,20))

        title = self.h1.render("Match Tactics", True, (235,235,240))
        screen.blit(title, (16,16))

        pygame.draw.rect(screen, (42,44,52), self.rect_board, border_radius=10)
        pygame.draw.rect(screen, (24,24,28), self.rect_board, 2, border_radius=10)
        for c in range(self.grid_cols):
            for r in range(self.grid_rows):
                rect = self._cell_rect(c, r)
                pygame.draw.rect(screen, (34,36,44), rect)
                pygame.draw.rect(screen, (26,28,34), rect, 1)

        for tok in self.placed:
            rect = self._cell_rect(tok["cx"], tok["cy"])
            self._draw_token(screen, rect, tok["data"], selected=False)

        if self.dragging is not None and self.drag_src == "board":
            mx,my = self.mx_my
            rect = pygame.Rect(mx + self.drag_offset[0], my + self.drag_offset[1], self.tile, self.tile)
            self._draw_token(screen, rect, self.dragging["data"], selected=True)

        pygame.draw.rect(screen, (42,44,52), self.rect_bench, border_radius=10)
        pygame.draw.rect(screen, (24,24,28), self.rect_bench, 2, border_radius=10)
        cap = self.h2.render(f"Select 5 • Placed: {len(self.placed)}/5", True, (215,215,220))
        screen.blit(cap, (self.rect_bench.x + 12, self.rect_bench.y + 8))

        row_h = 28
        inner = self.rect_bench.inflate(-16, -48); inner.y = self.rect_bench.y + 36
        y = inner.y
        for p in self._bench_list():
            r = pygame.Rect(inner.x, y, inner.w, row_h-4)
            pygame.draw.rect(screen, (58,60,70), r, border_radius=8)
            pygame.draw.rect(screen, (24,24,28), r, 2, border_radius=8)
            label = f"{_shorten(_name(p), 24)}   OVR {_ovr(p)}"
            txt = self.font.render(label, True, (230,230,235))
            screen.blit(txt, (r.x + 10, r.y + (r.h - txt.get_height())//2))
            y += row_h

        if self.dragging is not None and self.drag_src == "bench":
            rect = pygame.Rect(self.mx_my[0]-self.tile//2, self.mx_my[1]-self.tile//2, self.tile, self.tile)
            self._draw_token(screen, rect, self.dragging, selected=True)

        for b in (self.btn_back, self.btn_clear, self.btn_next):
            b.draw(screen, self.font)

    # ----- internal helpers -----
    def _bench_list(self) -> List[Dict[str,Any]]:
        placed_ids = {tok["data"]["pid"] for tok in self.placed if "data" in tok and "pid" in tok["data"]}
        return [p for p in self.bench if p.get("pid") not in placed_ids]

    def _bench_index_at(self, pos) -> Optional[int]:
        inner = self.rect_bench.inflate(-16, -48); inner.y = self.rect_bench.y + 36
        if not inner.collidepoint(pos): return None
        row_h = 28
        idx = (pos[1] - inner.y) // row_h
        return int(idx)

    def _cell_rect(self, cx: int, cy: int) -> pygame.Rect:
        return pygame.Rect(self.rect_board.x + cx*self.tile,
                           self.rect_board.y + cy*self.tile,
                           self.tile, self.tile)

    def _snap_to_cell(self, pos) -> Tuple[int,int]:
        x, y = pos
        cx = (x - self.rect_board.x) // self.tile
        cy = (y - self.rect_board.y) // self.tile
        cx = max(0, min(self.grid_cols-1, cx))
        cy = max(0, min(self.grid_rows-1, cy))
        return int(cx), int(cy)

    def _cell_occupied(self, cx: int, cy: int) -> Optional[int]:
        for i, tok in enumerate(self.placed):
            if tok["cx"] == cx and tok["cy"] == cy:
                return i
        return None

    def _placed_at_pixel(self, pos) -> Optional[int]:
        if not self.rect_board.collidepoint(pos): return None
        cx, cy = self._snap_to_cell(pos)
        return self._cell_occupied(cx, cy)

    def _draw_token(self, surf, rect: pygame.Rect, p: Dict[str,Any], selected=False):
        bg = (90,110,140) if selected else (80, 100, 128)
        pygame.draw.rect(surf, bg, rect, border_radius=6)
        pygame.draw.rect(surf, (22,24,28), rect, 2, border_radius=6)
        nm = _shorten(_name(p), 12); ovr = _ovr(p)
        line1 = self.font.render(nm, True, (240,240,245))
        line2 = self.font.render(f"{ovr}", True, (230,230,235))
        surf.blit(line1, (rect.x + 6, rect.y + 4))
        surf.blit(line2, (rect.right - line2.get_width() - 6, rect.bottom - line2.get_height() - 2))

    def _place_dragging(self, cx: int, cy: int):
        if self.drag_src == "bench":
            if len(self.placed) >= 5:
                self._cancel_drag(); return
            pdata = dict(self.dragging)
        else:
            pdata = dict(self.dragging["data"])
            if 0 <= self.drag_idx < len(self.placed):
                self.placed.pop(self.drag_idx)
        self.placed.append({"pid": pdata.get("pid"), "cx": cx, "cy": cy, "data": pdata})
        self.dragging = None; self.drag_src = None; self.drag_idx = -1

    def _cancel_drag(self):
        self.dragging = None; self.drag_src = None; self.drag_idx = -1

    # ----- actions -----
    def _back(self):
        self.app.pop_state()

    def _clear(self):
        self.placed.clear()

    def _next(self):
        if len(self.placed) != 5:
            return
        side = "home" if self.user_is_home else "away"
        lineup = [{"pid": tok["pid"], "cx": int(tok["cx"]), "cy": int(tok["cy"])} for tok in self.placed]
        self.fixture = dict(self.fixture)
        self.fixture["preset_lineup"] = {"side": side, "tid": self.user_tid, "slots": lineup,
                                         "grid_cols": self.grid_cols, "grid_rows": self.grid_rows}

        try:
            from ui.state_match import MatchState  # type: ignore
        except Exception:
            return
        attempts = [
            (self.app, self.career, self.fixture),
            (self.app, self.fixture, self.career),
            (self.app, self.fixture),
        ]
        for args in attempts:
            try:
                self.app.push_state(MatchState(*args))  # type: ignore
                return
            except Exception:
                traceback.print_exc()
                continue
