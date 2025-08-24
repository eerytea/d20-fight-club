# ui/state_team_select.py
from __future__ import annotations
from typing import Any, List, Optional, Callable

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

# Prefer shared Button if present
try:
    from .uiutil import Button  # type: ignore
except Exception:
    Button = None  # type: ignore


def _mk_button(rect, label: str, on_click: Callable[[], None]):
    if Button is not None:
        return Button(rect, label, on_click=on_click)
    return _SimpleButton(rect, label, on_click)


class _SimpleButton:
    def __init__(self, rect, label: str, on_click: Callable[[], None]):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.hover = False
        self._font = pygame.font.SysFont("consolas", 20) if pygame else None

    def handle_event(self, e) -> bool:
        if pygame is None:
            return False
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.on_click()
            return True
        return False

    def draw(self, surf) -> None:
        if pygame is None:
            return
        bg = (120, 120, 120) if self.hover else (98, 98, 98)
        pygame.draw.rect(surf, bg, self.rect, border_radius=8)
        pygame.draw.rect(surf, (50, 50, 50), self.rect, 2, border_radius=8)
        t = self._font.render(self.label, True, (20, 20, 20))
        surf.blit(t, (self.rect.x + (self.rect.w - t.get_width()) // 2,
                      self.rect.y + (self.rect.h - t.get_height()) // 2))


class TeamSelectState:
    """
    Two-pane New Game selector:
      - Left: teams list
      - Right: roster (top) + fighter details (bottom)
      - Start Season button creates a new Career with the chosen team and goes to Season Hub
    """

    def __init__(self, app: Optional[Any] = None) -> None:
        self.app = app
        self._font = None
        self._title_font = None

        self.career = None  # temp career scaffold for preview
        self.selected_team: Optional[int] = None
        self.selected_fighter_idx: Optional[int] = None

        self._buttons: List[Any] = []
        self._start_btn = None
        self._back_btn = None

    # ---- lifecycle ----

    def enter(self) -> None:
        if pygame is None:
            return
        if not pygame.font.get_init():
            pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 20)
        self._title_font = pygame.font.SysFont("consolas", 28)

        # Build a temporary career with a deterministic seed
        seed = getattr(self.app, "seed", 12345)
        self._build_preview_career(seed)
        self._layout_buttons()

    def exit(self) -> None:
        pass

    # ---- helpers ----

    def _build_preview_career(self, seed: int) -> None:
        """Create a temporary Career to preview teams/rosters."""
        from core.career import new_career  # type: ignore

        # new_career should generate team_names, team_colors, rosters, fixtures, etc.
        # we pass user_team_id=None so it's not locked yet
        self.career = new_career(seed=seed, user_team_id=None)

        # Basic guard: if your generator only made 2 teams, it's still fine, but
        # normally you should see many teams (e.g., 12 or 20). Configure in core/config.py
        if not getattr(self.career, "team_names", None):
            raise RuntimeError("Career generator returned no teams")

    def _layout_buttons(self) -> None:
        if pygame is None:
            return
        w, h = getattr(self.app, "width", 1024), getattr(self.app, "height", 600)
        # bottom buttons
        y = h - 64
        self._buttons.clear()
        self._start_btn = _mk_button(pygame.Rect(w - 300, y, 180, 44), "Start Season", self._start)
        self._back_btn = _mk_button(pygame.Rect(24, y, 120, 44), "Back", self._back)
        self._buttons.extend([self._start_btn, self._back_btn])

    # ---- input ----

    def handle_event(self, e) -> bool:
        if pygame is None:
            return False

        # Click in team list
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            tl_rect = self._teams_rect()
            if tl_rect.collidepoint(mx, my):
                idx = self._team_idx_from_pos(my, tl_rect)
                if idx is not None:
                    self.selected_team = idx
                    self.selected_fighter_idx = None
                    return True

            roster_rect, detail_rect = self._roster_rect(), self._detail_rect()
            if roster_rect.collidepoint(mx, my) and self.selected_team is not None:
                fidx = self._fighter_idx_from_pos(my, roster_rect, self.selected_team)
                if fidx is not None:
                    self.selected_fighter_idx = fidx
                    return True

        for b in self._buttons:
            if b.handle_event(e):
                return True
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self._back()
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    # ---- drawing ----

    def _teams_rect(self):
        w, h = getattr(self.app, "width", 1024), getattr(self.app, "height", 600)
        return pygame.Rect(24, 24, 320, h - 24 - 80)

    def _roster_rect(self):
        w, h = getattr(self.app, "width", 1024), getattr(self.app, "height", 600)
        return pygame.Rect(24 + 320 + 24, 24, w - (24 + 320 + 24 + 24), (h - 24 - 80) * 2 // 3)

    def _detail_rect(self):
        w, h = getattr(self.app, "width", 1024), getattr(self.app, "height", 600)
        top = 24 + ((h - 24 - 80) * 2 // 3) + 12
        return pygame.Rect(24 + 320 + 24, top, w - (24 + 320 + 24 + 24), (h - 24 - 80) - ((h - 24 - 80) * 2 // 3) - 12)

    def draw(self, surf) -> None:
        if pygame is None:
            return
        w, h = surf.get_size()

        # Titles
        title = self._title_font.render("New Game – Pick Your Team", True, (255, 255, 255))
        surf.blit(title, (w // 2 - title.get_width() // 2, 12))

        # Panels
        pygame.draw.rect(surf, (40, 44, 52), self._teams_rect(), border_radius=8)
        pygame.draw.rect(surf, (40, 44, 52), self._roster_rect(), border_radius=8)
        pygame.draw.rect(surf, (40, 44, 52), self._detail_rect(), border_radius=8)

        # Team list
        if self.career:
            self._draw_team_list(surf, self._teams_rect(), self.career.team_names)

            # Roster + details
            if self.selected_team is not None:
                roster = self.career.rosters[self.selected_team]
                self._draw_roster(surf, self._roster_rect(), roster)
                if self.selected_fighter_idx is not None and 0 <= self.selected_fighter_idx < len(roster):
                    self._draw_fighter_detail(surf, self._detail_rect(), roster[self.selected_fighter_idx])

        # Buttons
        for b in self._buttons:
            b.draw(surf)

    # ---- drawing helpers ----

    def _draw_team_list(self, surf, rect, names: List[str]) -> None:
        line_h = 26
        for i, name in enumerate(names):
            y = rect.y + 10 + i * line_h
            if y + line_h > rect.bottom - 10:
                break
            sel = (i == self.selected_team)
            color = (255, 255, 255) if not sel else (255, 230, 120)
            t = self._font.render(name, True, color)
            surf.blit(t, (rect.x + 10, y))

    def _draw_roster(self, surf, rect, roster: List[dict]) -> None:
        line_h = 22
        header = self._font.render("Name   (OVR  Lvl  Class)", True, (180, 180, 180))
        surf.blit(header, (rect.x + 10, rect.y + 8))
        for i, fd in enumerate(roster):
            y = rect.y + 34 + i * line_h
            if y + line_h > rect.bottom - 8:
                break
            name = str(fd.get("name", f"F{i+1}"))
            ovr  = int(fd.get("ovr", 50))
            lvl  = int(fd.get("level", 1))
            cls  = str(fd.get("cls", fd.get("class", "Fighter")))
            label = f"{name:16s} ({ovr:>3}  {lvl:>2}  {cls})"
            sel = (i == self.selected_fighter_idx)
            color = (220, 220, 220) if not sel else (120, 220, 255)
            t = self._font.render(label, True, color)
            surf.blit(t, (rect.x + 10, y))

    def _draw_fighter_detail(self, surf, rect, fd: dict) -> None:
        x, y = rect.x + 10, rect.y + 8
        lines = []
        for k in ("name", "cls", "level", "ovr", "hp", "ac", "str", "dex", "con", "int", "wis", "cha"):
            v = fd.get(k, fd.get(k.upper(), ""))
            lines.append(f"{k.upper():>4}: {v}")
        for ln in lines:
            t = self._font.render(ln, True, (220, 220, 220))
            surf.blit(t, (x, y))
            y += 22

    # ---- index helpers ----

    def _team_idx_from_pos(self, my: int, rect) -> Optional[int]:
        line_h = 26
        idx = (my - (rect.y + 10)) // line_h
        if idx < 0 or self.career is None:
            return None
        if idx >= len(self.career.team_names):
            return None
        return int(idx)

    def _fighter_idx_from_pos(self, my: int, rect, team_id: int) -> Optional[int]:
        line_h = 22
        idx = (my - (rect.y + 34)) // line_h
        if idx < 0 or self.career is None:
            return None
        roster = self.career.rosters[team_id]
        if idx >= len(roster):
            return None
        return int(idx)

    # ---- actions ----

    def _start(self) -> None:
        if self.career is None or self.selected_team is None:
            return
        try:
            # Create a fresh *real* career with the chosen user team
            from core.career import new_career  # type: ignore
            career = new_career(seed=getattr(self.app, "seed", 12345), user_team_id=self.selected_team)

            from ui.state_season_hub import SeasonHubState
            if hasattr(self.app, "safe_push"):
                self.app.safe_replace(SeasonHubState, app=self.app, career=career)
            else:
                self.app.replace_state(SeasonHubState(self.app, career))
        except Exception as e:
            self._message(f"Couldn't start season:\n{e}")

    def _back(self) -> None:
        if hasattr(self.app, "pop_state"):
            self.app.pop_state()

    def _message(self, text: str) -> None:
        try:
            from .state_message import MessageState
            if hasattr(self.app, "push_state"):
                self.app.push_state(MessageState(app=self.app, text=text))
            else:
                print(text)
        except Exception:
            print(text)
