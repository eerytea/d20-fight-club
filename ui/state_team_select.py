# ui/state_team_select.py
from __future__ import annotations

import random
from typing import List, Any, Callable, Optional

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

# optional shared Button
try:
    from .uiutil import Button
except Exception:
    Button = None  # type: ignore

from core.career import new_career
from .state_message import MessageState
from .state_season_hub import SeasonHubState  # target after choosing team


def _rand_seed() -> int:
    return random.randint(1, 2_000_000_000)


# ---------- small UI helpers (panels & list widgets) ----------

def _draw_panel(surface, rect, title: Optional[str] = None):
    pygame.draw.rect(surface, (30, 34, 42), rect, border_radius=8)
    pygame.draw.rect(surface, (70, 78, 92), rect, width=2, border_radius=8)
    if title:
        font = pygame.font.SysFont("consolas", 20)
        t = font.render(title, True, (220, 220, 220))
        surface.blit(t, (rect.x + 10, rect.y + 8))


class _ListWidget:
    """
    Simple scrollable list widget.
    items: list[Any]
    get_label: Callable[[Any], str]
    on_select: Callable[[int, Any], None]
    """
    def __init__(
        self,
        rect: "pygame.Rect",
        items: List[Any],
        get_label: Callable[[Any], str],
        on_select: Callable[[int, Any], None],
        item_h: int = 26,
        selected_index: int = 0,
    ):
        self.rect = rect
        self.items = items
        self.get_label = get_label
        self.on_select = on_select
        self.item_h = item_h
        self.selected_index = selected_index
        self.scroll = 0
        self._font = pygame.font.SysFont("consolas", 18)

    def set_items(self, items: List[Any], keep_selection: bool = False):
        self.items = items
        if not keep_selection:
            self.selected_index = 0
        self.scroll = 0

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll = max(0, self.scroll - event.y * 3)  # y>0 wheel up
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.rect.y
                idx = self.scroll + (rel_y // self.item_h)
                if 0 <= idx < len(self.items):
                    self.selected_index = idx
                    self.on_select(self.selected_index, self.items[self.selected_index])
                    return True
        return False

    def draw(self, surface):
        # clip to rect
        clip = surface.get_clip()
        surface.set_clip(self.rect)
        x, y = self.rect.x, self.rect.y
        w, h = self.rect.w, self.rect.h

        # background
        pygame.draw.rect(surface, (22, 24, 30), self.rect, border_radius=6)

        # visible range
        lines = h // self.item_h
        start = self.scroll
        end = min(len(self.items), start + lines)

        for i in range(start, end):
            row_y = y + (i - start) * self.item_h
            is_sel = (i == self.selected_index)
            if is_sel:
                pygame.draw.rect(surface, (60, 66, 80), (x, row_y, w, self.item_h))
            label = self.get_label(self.items[i])
            txt = self._font.render(label, True, (240, 240, 240) if is_sel else (200, 200, 200))
            surface.blit(txt, (x + 8, row_y + 4))

        surface.set_clip(clip)


class TeamSelectState:
    """
    Two-pane picker:
      - Left: team list
      - Right: roster (top) and player details (bottom)
      - Bottom: Start Game / Back buttons
    """

    def __init__(self, app) -> None:
        self.app = app
        self._title_font = None
        self._font = None
        self._small = None

        self.team_names: List[str] = []
        self.rosters: List[List[dict]] = []  # mirrors career.rosters shape

        # widgets
        self._team_list: Optional[_ListWidget] = None
        self._roster_list: Optional[_ListWidget] = None
        self._btn_start = None
        self._btn_back = None

        self._active_team_idx: int = 0
        self._active_fighter: Optional[dict] = None

    # ---------- lifecycle ----------

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 28)
        self._font = pygame.font.SysFont("consolas", 20)
        self._small = pygame.font.SysFont("consolas", 16)

        try:
            preview = new_career(seed=self.app.seed or _rand_seed())
            self.team_names = list(preview.team_names)
            # preview.rosters: List[List[dict-like]]
            self.rosters = list(preview.rosters)

            # layout rects
            w, h = self.app.width, self.app.height
            pad = 24
            left_rect = pygame.Rect(pad, 110, w // 3 - pad * 1.5, h - 210)
            right_rect = pygame.Rect(w // 3 + pad // 2, 110, w - (w // 3 + pad * 1.5), h - 210)

            roster_top_h = int(right_rect.h * 0.58)
            roster_rect = pygame.Rect(right_rect.x, right_rect.y, right_rect.w, roster_top_h)
            detail_rect = pygame.Rect(right_rect.x, right_rect.y + roster_top_h + 10, right_rect.w, right_rect.h - roster_top_h - 10)

            # widgets
            self._team_list = _ListWidget(
                left_rect,
                items=self.team_names,
                get_label=lambda s: str(s),
                on_select=self._on_team_selected,
                item_h=26,
                selected_index=0,
            )
            # initial roster for team 0
            initial_roster = self.rosters[0] if self.rosters else []
            self._roster_list = _ListWidget(
                roster_rect,
                items=initial_roster,
                get_label=_fighter_label,
                on_select=self._on_fighter_selected,
                item_h=26,
                selected_index=0,
            )
            self._active_fighter = initial_roster[0] if initial_roster else None
            self._detail_rect = detail_rect
            self._left_rect = left_rect
            self._roster_rect = roster_rect
            self._right_rect = right_rect

            # buttons bottom-right
            btn_w, btn_h = 180, 44
            btn_gap = 16
            by = self.app.height - 76
            bx2 = self.app.width - (btn_w + 24)
            bx1 = bx2 - (btn_w + btn_gap)

            def make_btn(rect, label, fn):
                if Button is not None:
                    return Button(rect, label, on_click=fn)  # type: ignore
                # fallback
                class _B:
                    def __init__(self, rect, label, on_click):
                        self.rect, self.label, self.on_click = rect, label, on_click
                        self.hover = False
                        self._font = pygame.font.SysFont("consolas", 20)
                    def handle_event(self, e):
                        if e.type == pygame.MOUSEMOTION:
                            self.hover = self.rect.collidepoint(e.pos)
                        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
                            self.on_click()
                            return True
                        return False
                    def draw(self, surf):
                        bg = (120, 120, 120) if self.hover else (100, 100, 100)
                        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
                        pygame.draw.rect(surf, (60, 60, 60), self.rect, 2, border_radius=6)
                        t = self._font.render(self.label, True, (20, 20, 20))
                        surf.blit(t, (self.rect.x + (self.rect.w - t.get_width()) // 2,
                                      self.rect.y + (self.rect.h - t.get_height()) // 2))
                return _B(rect, label, fn)

            self._btn_back = make_btn(pygame.Rect(bx1, by, btn_w, btn_h), "Back", self._back)
            self._btn_start = make_btn(pygame.Rect(bx2, by, btn_w, btn_h), "Start Game", self._start_game)

        except Exception as e:
            self._msg(f"Couldn't build team list:\n{e}")

    def exit(self) -> None:
        pass

    # ---------- events / update / draw ----------

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        # list interactions
        if self._team_list and self._team_list.handle_event(event):
            return True
        if self._roster_list and self._roster_list.handle_event(event):
            return True
        # buttons
        if self._btn_back and self._btn_back.handle_event(event):
            return True
        if self._btn_start and self._btn_start.handle_event(event):
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()

        title = self._title_font.render("New Game — Pick Team", True, (255, 255, 255))  # type: ignore
        surface.blit(title, (24, 24))

        # left panel: teams
        _draw_panel(surface, self._left_rect, "Teams")
        if self._team_list:
            self._team_list.draw(surface)

        # right panels: roster + details
        _draw_panel(surface, self._roster_rect, "Roster")
        if self._roster_list:
            self._roster_list.draw(surface)

        _draw_panel(surface, self._detail_rect, "Details")
        self._draw_fighter_details(surface, self._detail_rect, self._active_fighter)

        # buttons
        if self._btn_start:
            self._btn_start.draw(surface)
        if self._btn_back:
            self._btn_back.draw(surface)

    # ---------- callbacks ----------

    def _on_team_selected(self, idx: int, _val: Any) -> None:
        self._active_team_idx = idx
        roster = self.rosters[idx] if 0 <= idx < len(self.rosters) else []
        if self._roster_list:
            self._roster_list.set_items(roster)
        self._active_fighter = roster[0] if roster else None

    def _on_fighter_selected(self, idx: int, fighter: Any) -> None:
        self._active_fighter = fighter

    # ---------- actions ----------

    def _msg(self, text: str):
        self.app.push_state(MessageState(app=self.app, text=text))

    def _back(self):
        self.app.pop_state()

    def _start_game(self):
        try:
            if not self.team_names:
                raise ValueError("No teams available.")
            team_id = int(self._active_team_idx)
            seed = self.app.seed or _rand_seed()

            career = new_career(seed=seed)
            career.user_team_id = team_id
            self.app.data["career"] = career

            # go to hub
            self.app.safe_replace(SeasonHubState, app=self.app, career=career)

            # optional: immediately open roster if present
            try:
                from .state_roster import RosterState  # type: ignore
                self.app.safe_push(RosterState, app=self.app, career=career)
            except Exception:
                pass
        except Exception as e:
            self._msg(f"Starting game failed:\n{e}")

    # ---------- render details ----------

    def _draw_fighter_details(self, surf, rect, f: Optional[dict]) -> None:
        if f is None:
            txt = self._font.render("Select a fighter…", True, (210, 210, 210))
            surf.blit(txt, (rect.x + 10, rect.y + 12))
            return

        y = rect.y + 12
        line = lambda s: self._small.render(s, True, (220, 220, 220))

        # safe getters
        def g(k, *alts, default="—"):
            for key in (k, *alts):
                if key in f:
                    return f[key]
            return default

        lines = [
            f"Name: {g('name')}",
            f"Class: {g('cls','class')}",
            f"Level: {g('level', default=1)}",
            f"OVR: {g('ovr', default='—')}",
            f"HP: {g('hp', default='—')}  ATK: {g('atk','attack', default='—')}  DEF: {g('defense','def', default='—')}",
            f"SPD: {g('speed', default='—')}  AC: {g('ac', default='—')}",
            f"STR: {g('str', default='—')}  DEX: {g('dex', default='—')}  CON: {g('con', default='—')}",
        ]

        for s in lines:
            surf.blit(line(s), (rect.x + 10, y))
            y += 22


# ---- display helpers ----

def _fighter_label(fd: dict) -> str:
    name = str(fd.get("name", "Fighter"))
    ovr = fd.get("ovr")
    lvl = fd.get("level")
    parts = [name]
    if isinstance(ovr, int):
        parts.append(f"(OVR {ovr})")
    if isinstance(lvl, int):
        parts.append(f"Lv {lvl}")
    return " ".join(parts)
