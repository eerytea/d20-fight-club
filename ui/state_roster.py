# ui/state_roster.py
from __future__ import annotations

from typing import List, Any, Optional, Tuple

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

try:
    from .uiutil import Button
except Exception:
    Button = None  # type: ignore

from .state_message import MessageState


class _SimpleButton:
    def __init__(self, rect, label, on_click):
        self.rect, self.label, self.on_click = rect, label, on_click
        self.hover = False
        self._font = pygame.font.SysFont("consolas", 18) if pygame else None

    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.on_click()
            return True
        return False

    def draw(self, surf):
        bg = (120, 120, 120) if self.hover else (98, 98, 98)
        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
        pygame.draw.rect(surf, (50, 50, 50), self.rect, 2, border_radius=6)
        t = self._font.render(self.label, True, (20, 20, 20))
        surf.blit(t, (self.rect.x + (self.rect.w - t.get_width()) // 2,
                      self.rect.y + (self.rect.h - t.get_height()) // 2))


def _draw_panel(surface, rect, title=None):
    pygame.draw.rect(surface, (30, 34, 42), rect, border_radius=8)
    pygame.draw.rect(surface, (70, 78, 92), rect, 2, border_radius=8)
    if title:
        ft = pygame.font.SysFont("consolas", 20)
        t = ft.render(title, True, (235, 235, 235))
        surface.blit(t, (rect.x + 10, rect.y + 10))


def _g(fd: dict, key: str, *alts, default="—"):
    for k in (key, *alts):
        if k in fd:
            return fd[k]
    return default


def _fighter_row(fd: dict) -> str:
    name = _g(fd, "name")
    cls = _g(fd, "cls", "class")
    ovr = _g(fd, "ovr", default="")
    lvl = _g(fd, "level", default="")
    return f"{name:16} {cls:8} OVR:{ovr} Lv:{lvl}"


class RosterState:
    """
    Roster viewer:
      - sortable list with paging
      - click to select; SHIFT-click to multi-select
      - Compare button (requires 2 selected)
      - Detail panel on the right
    """

    PAGE = 10

    def __init__(self, app, career=None) -> None:
        self.app = app
        self.career = career or self.app.data.get("career")
        self._title_font = None
        self._font = None
        self._small = None

        self._sort_key = "ovr"
        self._sort_asc = False
        self._page = 0

        self._selected: List[int] = []  # indexes within current page
        self._last_clicked: Optional[int] = None

        self._btn_prev = None
        self._btn_next = None
        self._btn_compare = None
        self._btn_back = None

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 26)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small = pygame.font.SysFont("consolas", 14)
        self._layout_buttons()

    def exit(self) -> None:
        pass

    # ---- layout ----
    def _layout_buttons(self):
        w, h = self.app.width, self.app.height
        btn_w, btn_h, gap = 150, 40, 10
        by = h - 64
        bx = w - 24 - btn_w
        mk = lambda label, fn, x: (Button(pygame.Rect(x, by, btn_w, btn_h), label, on_click=fn)
                                   if Button else _SimpleButton(pygame.Rect(x, by, btn_w, btn_h), label, fn))
        self._btn_back = mk("Back", self._back, bx); bx -= (btn_w + gap)
        self._btn_compare = mk("Compare", self._compare, bx); bx -= (btn_w + gap)
        self._btn_next = mk("Next Page", self._next_page, bx); bx -= (btn_w + gap)
        self._btn_prev = mk("Prev Page", self._prev_page, bx)

    # ---- events/update/draw ----

    def handle_event(self, e) -> bool:
        if pygame is None:
            return False
        for b in (self._btn_prev, self._btn_next, self._btn_compare, self._btn_back):
            if b and b.handle_event(e):
                return True

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self._list_rect.collidepoint(e.pos):
                idx = (e.pos[1] - self._list_rect.y) // 22  # row height
                absolute = self._page * self.PAGE + idx
                roster = self._sorted_roster()
                if 0 <= absolute < len(roster):
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        # multi-select toggle
                        if absolute in self._selected:
                            self._selected.remove(absolute)
                        else:
                            self._selected.append(absolute)
                    else:
                        self._selected = [absolute]
                    self._last_clicked = absolute
                    return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surf) -> None:
        if pygame is None:
            return
        w, h = surf.get_size()
        title = self._title_font.render("Roster", True, (255, 255, 255))
        surf.blit(title, (24, 24))

        # sort header
        sort_text = f"Sort: {self._sort_key.upper()} ({'ASC' if self._sort_asc else 'DESC'})"
        st = self._small.render(sort_text + "  •  Click rows (Shift=multi)", True, (210, 210, 210))
        surf.blit(st, (24, 60))

        # panels
        left = pygame.Rect(24, 90, w // 2 - 36, h - 170)
        right = pygame.Rect(w // 2 + 12, 90, w - (w // 2 + 36), h - 170)
        _draw_panel(surf, left, "Players")
        _draw_panel(surf, right, "Details")

        self._list_rect = pygame.Rect(left.x + 8, left.y + 34, left.w - 16, left.h - 42)
        roster = self._sorted_roster()
        start = self._page * self.PAGE
        end = min(len(roster), start + self.PAGE)

        # rows
        y = self._list_rect.y
        for i in range(start, end):
            row = _fighter_row(roster[i])
            sel = (i in self._selected)
            if sel:
                pygame.draw.rect(surf, (60, 66, 80), (self._list_rect.x, y, self._list_rect.w, 22))
            t = self._font.render(row, True, (240, 240, 240) if sel else (200, 200, 200))
            surf.blit(t, (self._list_rect.x + 6, y + 2))
            y += 22

        # details panel
        sel_fd = roster[self._selected[0]] if self._selected else (roster[start] if start < end else None)
        self._draw_details(surf, right, sel_fd)

        # page info
        pages = max(1, (len(roster) + self.PAGE - 1) // self.PAGE)
        pi = self._small.render(f"Page {self._page+1}/{pages}  •  {len(roster)} players", True, (210, 210, 210))
        surf.blit(pi, (24, h - 36))

        for b in (self._btn_prev, self._btn_next, self._btn_compare, self._btn_back):
            if b:
                b.draw(surf)

    # ---- data helpers ----

    def _sorted_roster(self) -> List[dict]:
        career = self.career
        if not career:
            return []
        roster = list(career.rosters[career.user_team_id])
        keymap = {
            "name": lambda f: str(_g(f, "name")),
            "cls": lambda f: str(_g(f, "cls", "class")),
            "ovr": lambda f: int(_g(f, "ovr", default=0) or 0),
            "level": lambda f: int(_g(f, "level", default=1) or 1),
            "age": lambda f: int(_g(f, "age", default=20) or 20),
        }
        k = keymap.get(self._sort_key, keymap["ovr"])
        roster.sort(key=k, reverse=not self._sort_asc)
        return roster

    # ---- actions ----

    def _back(self):
        self.app.pop_state()

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._selected.clear()

    def _next_page(self):
        roster = self._sorted_roster()
        pages = max(1, (len(roster) + self.PAGE - 1) // self.PAGE)
        if self._page + 1 < pages:
            self._page += 1
            self._selected.clear()

    def _compare(self):
        roster = self._sorted_roster()
        if len(self._selected) != 2:
            self._msg("Select exactly two players (Shift-click).")
            return
        a = roster[self._selected[0]]
        b = roster[self._selected[1]]
        lines = [
            f"{_g(a,'name'):16} vs {_g(b,'name')}",
            f"Class: {_g(a,'cls','class'):10} | {_g(b,'cls','class')}",
            f"OVR:   {_g(a,'ovr','OVR','rating',default='—'):>3} | {_g(b,'ovr','OVR','rating',default='—')}",
            f"Level: {_g(a,'level',default='—'):>3} | {_g(b,'level',default='—')}",
            f"Age:   {_g(a,'age',default='—'):>3} | {_g(b,'age',default='—')}",
            f"HP:    {_g(a,'hp',default='—'):>3} | {_g(b,'hp',default='—')}",
            f"ATK:   {_g(a,'atk','attack',default='—'):>3} | {_g(b,'atk','attack',default='—')}",
            f"DEF:   {_g(a,'defense','def',default='—'):>3} | {_g(b,'defense','def',default='—')}",
            f"SPD:   {_g(a,'speed',default='—'):>3} | {_g(b,'speed',default='—')}",
            f"STR:   {_g(a,'str',default='—'):>3} | {_g(b,'str',default='—')}",
            f"DEX:   {_g(a,'dex',default='—'):>3} | {_g(b,'dex',default='—')}",
            f"CON:   {_g(a,'con',default='—'):>3} | {_g(b,'con',default='—')}",
            f"Weapon: {_g(a,'weapon','wpn',default={'name':'—'}).get('name','—')} | {_g(b,'weapon','wpn',default={'name':'—'}).get('name','—')}",
        ]
        self._msg("\n".join(lines))

    def _msg(self, text: str):
        self.app.push_state(MessageState(app=self.app, text=text))

    # ---- render details ----

    def _draw_details(self, surf, rect, f: Optional[dict]):
        if f is None:
            t = self._font.render("Select a player…", True, (210, 210, 210))
            surf.blit(t, (rect.x + 12, rect.y + 40))
            return
        y = rect.y + 40
        lines = [
            f"Name: {_g(f,'name')}",
            f"Class: {_g(f,'cls','class')}",
            f"Level: {_g(f,'level',default='—')}   OVR: {_g(f,'ovr',default='—')}",
            f"HP: {_g(f,'hp',default='—')}  ATK: {_g(f,'atk','attack',default='—')}  DEF: {_g(f,'defense','def',default='—')}",
            f"AC: {_g(f,'ac',default='—')}  SPD: {_g(f,'speed',default='—')}",
            f"STR: {_g(f,'str',default='—')}  DEX: {_g(f,'dex',default='—')}  CON: {_g(f,'con',default='—')}",
        ]
        for s in lines:
            surf.blit(self._font.render(s, True, (230, 230, 230)), (rect.x + 12, y))
            y += 24
