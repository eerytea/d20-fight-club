# ui/state_match.py
from __future__ import annotations

from typing import Callable, Optional, List, Any, Tuple

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

# Prefer your shared Button; fall back to a tiny built-in button
try:
    from .uiutil import Button  # expected: Button(pygame.Rect, label, on_click=callable)
except Exception:
    Button = None  # type: ignore


class _SimpleButton:  # fallback if uiutil.Button isn't available
    def __init__(self, rect, label, on_click):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.hover = False
        self._font = pygame.font.SysFont("consolas", 20) if pygame else None

    def handle_event(self, e):
        if pygame is None:
            return False
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.on_click()
            return True
        return False

    def draw(self, surf):
        if pygame is None:
            return
        bg = (120, 120, 120) if self.hover else (98, 98, 98)
        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
        pygame.draw.rect(surf, (50, 50, 50), self.rect, 2, border_radius=6)
        t = self._font.render(self.label, True, (20, 20, 20))
        surf.blit(
            t,
            (self.rect.x + (self.rect.w - t.get_width()) // 2,
             self.rect.y + (self.rect.h - t.get_height()) // 2),
        )


def _draw_panel(surface, rect, title: Optional[str] = None, title_font=None):
    pygame.draw.rect(surface, (30, 34, 42), rect, border_radius=8)
    pygame.draw.rect(surface, (70, 78, 92), rect, 2, border_radius=8)
    if title and title_font:
        t = title_font.render(title, True, (235, 235, 235))
        surface.blit(t, (rect.x + 10, rect.y + 10))


class MatchState:
    """
    Polished match viewer:
      - Left: grid with fighters + HP bars
      - Right: Turn Log (auto scroll, mouse wheel scroll)
      - Bottom: Back, Reset, Next Turn, Auto ON/OFF

    Args:
      tbcombat: the running TBCombat instance
      title:   text shown at top
      scheduled: if True, caller is a season fixture (we'll call on_result at the end)
      on_result(winner_tid_rel, home_goals, away_goals, tb): optional callback when winner is decided
      rebuild(): optional callable to rebuild a fresh TBCombat for Reset
    """

    def __init__(
        self,
        app,
        tbcombat,
        title: str = "Match",
        scheduled: bool = False,
        on_result: Optional[Callable[[int, int, int, Any], None]] = None,
        rebuild: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.app = app
        self.tb = tbcombat
        self.title = title
        self.scheduled = scheduled
        self.on_result = on_result
        self.rebuild = rebuild

        # UI
        self._title_font = None
        self._font = None
        self._small = None

        # Panels
        self._grid_rect = None
        self._log_rect = None
        self._buttons: List[Any] = []

        # Log
        self.log_lines: List[str] = []
        self._log_scroll = 0
        self._last_event_idx = 0
        self._max_log = 400

        # Auto play
        self.auto_play = False
        self._step_delay = 0.25
        self._accum = 0.0

        # Cache teams/colors/dims
        self._teams = self._detect_teams()
        self._grid_w, self._grid_h = self._detect_grid_dims()

        self._finished = False

    # -------- lifecycle --------

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 26)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small = pygame.font.SysFont("consolas", 14)
        self._layout()
        self._pull_new_events()  # prime log

    def exit(self) -> None:
        pass

    # -------- helpers (engine introspection) --------

    def _detect_teams(self) -> Tuple[Optional[Any], Optional[Any]]:
        tb = self.tb
        for a, b in (("teamA", "teamB"), ("team_home", "team_away")):
            if hasattr(tb, a) and hasattr(tb, b):
                return getattr(tb, a), getattr(tb, b)
        if hasattr(tb, "teams") and isinstance(tb.teams, (list, tuple)) and len(tb.teams) >= 2:
            return tb.teams[0], tb.teams[1]  # type: ignore
        return None, None

    def _detect_grid_dims(self) -> Tuple[int, int]:
        tb = self.tb
        for w_name, h_name in (("grid_w", "grid_h"), ("width", "height")):
            if hasattr(tb, w_name) and hasattr(tb, h_name):
                return int(getattr(tb, w_name)), int(getattr(tb, h_name))
        return 10, 8

    def _get_events_container(self) -> Optional[List[Any]]:
        for attr in ("event_log", "events", "log"):
            if hasattr(self.tb, attr):
                obj = getattr(self.tb, attr)
                if isinstance(obj, list):
                    return obj
        return None

    # -------- UI layout --------

    def _layout(self) -> None:
        w, h = self.app.width, self.app.height
        pad = 16
        title_h = 54
        buttons_h = 60

        grid_w = int(w * 0.68)
        self._grid_rect = pygame.Rect(pad, title_h + pad, grid_w - pad * 2, h - (title_h + buttons_h + pad * 3))
        self._log_rect = pygame.Rect(grid_w, title_h + pad, w - grid_w - pad, h - (title_h + buttons_h + pad * 3))

        # Buttons row (right-aligned)
        btn_w, btn_h, gap = 160, 42, 12
        by = h - (buttons_h - (buttons_h - btn_h) // 2)
        bx = w - pad - btn_w

        def mk(label: str, fn):
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            if Button is not None:
                self._buttons.append(Button(rect, label, on_click=fn))  # type: ignore
            else:
                self._buttons.append(_SimpleButton(rect, label, fn))

        self._buttons.clear()
        mk("Back", self._back); bx -= (btn_w + gap)
        self._buttons.append(
            (Button(pygame.Rect(bx, by, btn_w, btn_h), "Reset", self._reset))
            if Button is not None else _SimpleButton(pygame.Rect(bx, by, btn_w, btn_h), "Reset", self._reset)
        ); bx -= (btn_w + gap)
        self._buttons.append(
            (Button(pygame.Rect(bx, by, btn_w, btn_h), "Next Turn", self._next))
            if Button is not None else _SimpleButton(pygame.Rect(bx, by, btn_w, btn_h), "Next Turn", self._next)
        ); bx -= (btn_w + gap)
        self._btn_auto_rect = pygame.Rect(bx, by, btn_w, btn_h)
        self._btn_auto = (
            Button(self._btn_auto_rect, "Auto: OFF", on_click=self._toggle_auto)
            if Button is not None else _SimpleButton(self._btn_auto_rect, "Auto: OFF", self._toggle_auto)
        )
        self._buttons.append(self._btn_auto)

    # -------- events / update / draw --------

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False

        for b in self._buttons:
            if hasattr(b, "handle_event") and b.handle_event(event):
                return True

        if event.type == pygame.MOUSEWHEEL:
            if self._log_rect.collidepoint(pygame.mouse.get_pos()):
                self._log_scroll = max(0, self._log_scroll - event.y * 3)
                return True

        return False

    def update(self, dt: float) -> None:
        if self.auto_play and not self._finished:
            self._accum += dt
            while self._accum >= self._step_delay and not self._finished:
                self._accum -= self._step_delay
                self._step_one_turn()

    def draw(self, surface) -> None:
        if pygame is None:
            return

        title = self._title_font.render(self.title, True, (255, 255, 255))  # type: ignore
        surface.blit(title, (16, 12))

        _draw_panel(surface, self._grid_rect, None, self._title_font)
        _draw_panel(surface, self._log_rect, "Turn Log", self._title_font)

        self._draw_grid(surface, self._grid_rect)
        self._draw_fighters(surface, self._grid_rect)
        self._draw_log(surface, self._log_rect)

        label = f"Auto: {'ON' if self.auto_play else 'OFF'}"
        if hasattr(self._btn_auto, "label"):
            self._btn_auto.label = label  # type: ignore
        for b in self._buttons:
            if hasattr(b, "draw"):
                b.draw(surface)

    # -------- actions --------

    def _back(self) -> None:
        self.app.pop_state()

    def _reset(self) -> None:
        if callable(self.rebuild):
            try:
                self.tb = self.rebuild()
                self._teams = self._detect_teams()
                self._grid_w, self._grid_h = self._detect_grid_dims()
                self.log_lines.clear()
                self._log_scroll = 0
                self._last_event_idx = 0
                self._finished = False
                self.auto_play = False
                self._accum = 0.0
                self._pull_new_events()
            except Exception as e:
                self._push_msg(f"Reset failed:\n{e}")
        else:
            self._push_msg("Reset unavailable (no rebuild function).")

    def _next(self) -> None:
        if not self._finished:
            self._step_one_turn()

    def _toggle_auto(self) -> None:
        self.auto_play = not self.auto_play

    # -------- stepping --------

    def _step_one_turn(self) -> None:
        try:
            before_len = self._events_len()
            self.tb.take_turn()
            self._pull_new_events(start=before_len)
            if getattr(self.tb, "winner", None) is not None and not self._finished:
                self._finished = True
                self._on_finished()
        except Exception as e:
            self._push_msg(f"Engine step failed:\n{e}")
            self.auto_play = False

    def _events_len(self) -> int:
        ev = self._get_events_container()
        return len(ev) if ev is not None else len(self.log_lines)

    def _pull_new_events(self, start: Optional[int] = None) -> None:
        container = self._get_events_container()
        if container is None:
            return
        if start is None:
            start = self._last_event_idx
        new = container[start:]
        for e in new:
            self.log_lines.append(str(e))
        self._last_event_idx = start + len(new)
        if len(self.log_lines) > self._max_log:
            drop = len(self.log_lines) - self._max_log
            self.log_lines = self.log_lines[drop:]

    def _on_finished(self) -> None:
        fighters = getattr(self.tb, "fighters", [])
        home_alive = sum(1 for f in fighters if getattr(f, "team_id", 0) == 0 and getattr(f, "alive", True))
        away_alive = sum(1 for f in fighters if getattr(f, "team_id", 0) == 1 and getattr(f, "alive", True))
        home_goals = max(0, 4 - away_alive)
        away_goals = max(0, 4 - home_alive)
        winner_rel = getattr(self.tb, "winner", -1)

        if callable(self.on_result):
            try:
                self.on_result(int(winner_rel), int(home_goals), int(away_goals), self.tb)
            except Exception:
                pass

        msg = f"Match finished!\nWinner: {'Home' if winner_rel == 0 else ('Away' if winner_rel == 1 else 'Draw')}\nScore (proxy): {home_goals}–{away_goals}"
        self._push_msg(msg)

    # -------- rendering --------

    def _team_color(self, tid: int) -> Tuple[int, int, int]:
        a, b = self._teams
        if tid == 0 and a is not None and hasattr(a, "color"):
            return tuple(getattr(a, "color"))
        if tid == 1 and b is not None and hasattr(b, "color"):
            return tuple(getattr(b, "color"))
        return (180, 110, 110) if tid == 0 else (110, 140, 200)

    def _draw_grid(self, surf, rect) -> None:
        gw, gh = self._grid_w, self._grid_h
        tw = rect.w / gw
        th = rect.h / gh
        pygame.draw.rect(surf, (22, 24, 30), rect, border_radius=6)
        for x in range(gw + 1):
            X = rect.x + int(x * tw)
            pygame.draw.line(surf, (55, 60, 70), (X, rect.y), (X, rect.y + rect.h))
        for y in range(gh + 1):
            Y = rect.y + int(y * th)
            pygame.draw.line(surf, (55, 60, 70), (rect.x, Y), (rect.x + rect.w, Y))

    def _draw_fighters(self, surf, rect) -> None:
        gw, gh = self._grid_w, self._grid_h
        tw = rect.w / gw
        th = rect.h / gh
        fighters = getattr(self.tb, "fighters", [])

        for f in fighters:
            tx = getattr(f, "tx", None)
            ty = getattr(f, "ty", None)
            if tx is None or ty is None:
                continue
            cx = rect.x + int((tx + 0.5) * tw)
            cy = rect.y + int((ty + 0.5) * th)
            r = int(min(tw, th) * 0.35)

            col = self._team_color(getattr(f, "team_id", 0))
            alive = getattr(f, "alive", True)
            body = col if alive else (90, 90, 90)
            pygame.draw.circle(surf, body, (cx, cy), r)
            pygame.draw.circle(surf, (30, 30, 30), (cx, cy), r, 2)

            name = str(getattr(f, "name", ""))
            label = self._small.render(name[:8], True, (240, 240, 240))
            surf.blit(label, (cx - label.get_width() // 2, cy - r - 16))

            hp = float(getattr(f, "hp", 0))
            max_hp = float(getattr(f, "max_hp", max(1, int(hp))))
            pct = max(0.0, min(1.0, hp / max_hp))
            bar_w = int(tw * 0.9)
            bar_h = 6
            bar_x = int(rect.x + tx * tw + (tw - bar_w) / 2)
            bar_y = int(rect.y + (ty + 0.9) * th)
            pygame.draw.rect(surf, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            pygame.draw.rect(surf, (80, 200, 80), (bar_x, bar_y, int(bar_w * pct), bar_h), border_radius=3)

    def _draw_log(self, surf, rect) -> None:
        clip = surf.get_clip()
        surf.set_clip(rect)
        x, y = rect.x + 8, rect.y + 8
        line_h = 18

        lines_per = (rect.h - 16) // line_h
        start = max(0, len(self.log_lines) - lines_per - self._log_scroll)
        end = min(len(self.log_lines), start + lines_per)
        for ln in self.log_lines[start:end]:
            t = self._small.render(str(ln), True, (220, 220, 220))
            surf.blit(t, (x, y))
            y += line_h

        surf.set_clip(clip)

    # -------- misc --------

    def _push_msg(self, text: str) -> None:
        try:
            from .state_message import MessageState
            self.app.push_state(MessageState(app=self.app, text=text))
        except Exception:
            print(text)
