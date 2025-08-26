# ui/state_match.py
from __future__ import annotations

import pygame
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel, get_font

from engine.tbcombat import TBCombat

# Optional engine symbols (tolerant to branch/API differences)
try:
    from engine.tbcombat import Team as TBTeam
except Exception:
    @dataclass
    class TBTeam:
        tid: int
        name: str
        color: Tuple[int, int, int]

try:
    from engine.tbcombat import fighter_from_dict as _fighter_from_dict
except Exception:
    def _fighter_from_dict(fd: Dict[str, Any]):
        d = dict(fd)
        d.setdefault("pid", str(d.get("pid") or d.get("id") or d.get("name") or "F"))
        d.setdefault("name", str(d.get("name") or d["pid"]))
        d.setdefault("team_id", d.get("team_id", d.get("team", 0)))
        d.setdefault("class", d.get("class", d.get("cls", "Fighter")))
        d.setdefault("level", int(d.get("level", d.get("lvl", 1))))
        d.setdefault("hp", int(d.get("hp", 12)))
        d.setdefault("max_hp", int(d.get("max_hp", d["hp"])))
        d.setdefault("ac", int(d.get("ac", 10)))
        d.setdefault("atk", int(d.get("atk", 2)))
        d.setdefault("alive", bool(d.get("alive", True)))
        d.setdefault("x", int(d.get("x", 0)))
        d.setdefault("y", int(d.get("y", 0)))
        return SimpleNamespace(**d)

try:
    from engine.tbcombat import layout_teams_tiles as _layout_teams_tiles
except Exception:
    _layout_teams_tiles = None

try:
    from engine.tbcombat import GRID_W as _GRID_W, GRID_H as _GRID_H
except Exception:
    _GRID_W, _GRID_H = 15, 9

# Optional typed events formatter (fallback to robust pretty-printer)
try:
    from engine.events import format_event as _format_event
except Exception:
    _format_event = None  # will use our own formatter


class MatchState(BaseState):
    """Left grid (fighters + HP), right scrollable event log, bottom controls."""
    def __init__(self, app, home_team: Dict[str, Any], away_team: Dict[str, Any]):
        self.app = app
        self.theme = Theme()

        self.home_d = home_team
        self.away_d = away_team

        self.combat: TBCombat | None = None
        self._started = False

        # UI rects/buttons
        self.btn_step: Button | None = None
        self.btn_auto: Button | None = None
        self.btn_finish: Button | None = None
        self.btn_back: Button | None = None
        self.rect_panel: pygame.Rect | None = None
        self.rect_grid: pygame.Rect | None = None
        self.rect_log: pygame.Rect | None = None

        # Log state
        self.events: List[str] = []
        self._last_seen: Dict[str, int] = {
            "events_typed": 0,
            "typed_events": 0,
            "event_log_typed": 0,
            "events": 0,
            "log": 0,
        }
        self._log_scroll = 0  # 0 = stick to bottom; >0 scroll up by N wrapped lines

        # Name maps (rebuilt from live engine list)
        self._idx_to_name: Dict[int, str] = {}
        self._pid_to_name: Dict[str, str] = {}

        # Auto pacing
        self.auto = False
        self._auto_steps_per_update = 12

        self._built = False

    # ----- Helpers: current fighter list from the engine ---------------------
    def _fighters(self) -> List[Any]:
        if self.combat is not None:
            f = getattr(self.combat, "fighters", None)
            if isinstance(f, list) and f:
                return f
        return []

    def _rebuild_name_maps(self) -> None:
        self._idx_to_name.clear()
        self._pid_to_name.clear()
        for i, f in enumerate(self._fighters()):
            name = str(getattr(f, "name", getattr(f, "pid", f"F{i}")))
            self._idx_to_name[i] = name
            pid = getattr(f, "pid", None)
            if isinstance(pid, str):
                self._pid_to_name[pid] = name

    def _name_from_val(self, v: Any) -> str:
        if isinstance(v, str):
            return self._pid_to_name.get(v, v)
        if isinstance(v, int):
            return self._idx_to_name.get(v, f"#{v}")
        if isinstance(v, dict):
            return str(v.get("name") or self._pid_to_name.get(v.get("pid", ""), v.get("pid", "?")))
        if hasattr(v, "name"):
            return str(getattr(v, "name"))
        if hasattr(v, "pid"):
            pid = getattr(v, "pid")
            return self._pid_to_name.get(pid, str(pid))
        return "?"

    # ----- Event formatting --------------------------------------------------
    def _fmt_event(self, e: Any) -> str:
        if _format_event:
            try:
                return _format_event(e)
            except Exception:
                pass

        if isinstance(e, dict):
            t = e.get("type") or e.get("event") or "event"
            if t == "round":
                return f"— Round {e.get('round', '?')} —"
            if t in ("start", "StartRound"):
                return "Start of round"
            if t in ("move", "Move"):
                who = self._name_from_val(e.get("who") or e.get("actor") or e.get("src") or e.get("i"))
                to = e.get("to") or (e.get("x"), e.get("y"))
                return f"{who} moves to {to}"
            if t in ("hit", "Hit"):
                who = self._name_from_val(e.get("who") or e.get("attacker") or e.get("src") or e.get("i"))
                tgt = self._name_from_val(e.get("target") or e.get("defender") or e.get("dst") or e.get("j"))
                dmg = e.get("dmg") or e.get("damage") or "?"
                return f"{who} hits {tgt} for {dmg}"
            if t in ("miss", "Miss"):
                who = self._name_from_val(e.get("who") or e.get("attacker") or e.get("src") or e.get("i"))
                tgt = self._name_from_val(e.get("target") or e.get("defender") or e.get("dst") or e.get("j"))
                return f"{who} misses {tgt}"
            if t in ("down", "Down"):
                who = self._name_from_val(e.get("who") or e.get("target") or e.get("i") or e.get("j"))
                return f"{who} is down!"
            if t in ("end", "End", "finish"):
                return "End of match"
            # fallback pretty dict with name resolution
            try:
                parts = []
                for k, v in e.items():
                    if k in ("who", "attacker", "src", "i", "target", "defender", "dst", "j"):
                        v = self._name_from_val(v)
                    parts.append(f"{k}={v}")
                return ", ".join(parts)
            except Exception:
                return str(e)
        try:
            return str(e)
        except Exception:
            return repr(e)

    # ----- Lifecycle ---------------------------------------------------------
    def enter(self) -> None:
        self._build_match()
        self._build_ui()
        self._rebuild_name_maps()
        self._harvest_new_events()

    def _build_match(self):
        teamA = TBTeam(self.home_d["tid"], self.home_d.get("name", "Home"),
                       tuple(self.home_d.get("color", (180, 180, 220))))
        teamB = TBTeam(self.away_d["tid"], self.away_d.get("name", "Away"),
                       tuple(self.away_d.get("color", (220, 180, 180))))

        h_roster = self.home_d.get("fighters") or self.home_d.get("roster") or []
        a_roster = self.away_d.get("fighters") or self.away_d.get("roster") or []
        fighters = [_fighter_from_dict({**fd, "team_id": teamA.tid}) for fd in h_roster]
        fighters += [_fighter_from_dict({**fd, "team_id": teamB.tid}) for fd in a_roster]

        # Pre-layout
        if _layout_teams_tiles:
            _layout_teams_tiles(fighters, _GRID_W, _GRID_H)
        else:
            y = 1
            for f in fighters:
                if getattr(f, "team_id", teamA.tid) == teamA.tid:
                    f.x, f.y = 1, y
                else:
                    f.x, f.y = _GRID_W - 2, y
                y = 1 if y >= _GRID_H - 2 else y + 2

        self.combat = TBCombat(teamA, teamB, fighters, _GRID_W, _GRID_H, seed=42)

        # Some branches reset positions inside TBCombat; re-assert a sane layout if needed
        self._ensure_layout()

        for k in self._last_seen.keys():
            self._last_seen[k] = 0
        self.events.clear()
        self._log_scroll = 0
        self._started = False

    def _ensure_layout(self) -> None:
        fs = self._fighters()
        if not fs:
            return
        # Detect obviously broken layouts (all (0,0) or very few unique tiles)
        coords = [(int(getattr(f, "x", 0)), int(getattr(f, "y", 0))) for f in fs]
        uniq = set(coords)
        if len(uniq) >= max(2, len(fs) // 2) and not all(x == 0 and y == 0 for x, y in coords):
            return  # looks fine

        # Re-layout the *live* fighters on the combat object
        if _layout_teams_tiles:
            _layout_teams_tiles(fs, _GRID_W, _GRID_H)
        else:
            # two columns layout
            yL = yR = 1
            for f in fs:
                tid = getattr(f, "team_id", 0)
                if tid == getattr(getattr(self.combat, "teamA", None), "tid", -1):
                    f.x, f.y = 1, yL
                    yL = 1 if yL >= _GRID_H - 2 else yL + 2
                else:
                    f.x, f.y = _GRID_W - 2, yR
                    yR = 1 if yR >= _GRID_H - 2 else yR + 2

    def _build_ui(self):
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)

        split = int(self.rect_panel.w * 0.62)
        self.rect_grid = pygame.Rect(self.rect_panel.x + 12, self.rect_panel.y + 12, split - 24, self.rect_panel.h - 84)
        self.rect_log = pygame.Rect(self.rect_panel.x + split, self.rect_panel.y + 12, self.rect_panel.w - split - 12, self.rect_panel.h - 84)

        btn_w, btn_h, gap = 140, 42, 10
        y = self.rect_panel.bottom - (btn_h + 10)
        x = self.rect_panel.x + 12
        self.btn_step = Button(pygame.Rect(x, y, btn_w, btn_h), "Step", self._step)
        x += btn_w + gap
        self.btn_auto = Button(pygame.Rect(x, y, btn_w, btn_h), "Auto: OFF", self._toggle_auto)
        x += btn_w + gap
        self.btn_finish = Button(pygame.Rect(x, y, btn_w, btn_h), "Finish", self._finish)
        self.btn_back = Button(pygame.Rect(self.rect_panel.right - (btn_w + 12), y, btn_w, btn_h), "Back", self._back)

        self._built = True

    # ----- Advance control ---------------------------------------------------
    def _advance_once(self) -> None:
        if not self.combat:
            return
        c = self.combat
        for name in ("take_turn", "step", "advance", "tick", "update"):
            fn = getattr(c, name, None)
            if not callable(fn):
                continue
            try:
                fn(1)
                return
            except TypeError:
                try:
                    fn()
                    return
                except Exception:
                    continue
            except Exception:
                continue

    def _step(self):
        if self.combat and getattr(self.combat, "winner", None) is None:
            self._started = True
            self._advance_once()
            self._ensure_layout()
            self._rebuild_name_maps()
            self._harvest_new_events()

    def _toggle_auto(self):
        self.auto = not self.auto
        if self.btn_auto:
            self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"
        if self.auto:
            self._started = True

    def _finish(self):
        if not self.combat or getattr(self.combat, "winner", None) is not None:
            return
        self._started = True
        for i in range(20000):
            if getattr(self.combat, "winner", None) is not None:
                break
            self._advance_once()
            if i % 16 == 0:
                self._ensure_layout()
                self._rebuild_name_maps()
                self._harvest_new_events()
        self._ensure_layout()
        self._rebuild_name_maps()
        self._harvest_new_events()

    def _back(self):
        self.app.pop_state()

    # ----- Event harvesting --------------------------------------------------
    def _harvest_new_events(self):
        if not self.combat:
            return
        streams = ["events_typed", "typed_events", "event_log_typed", "events", "log"]
        for attr in streams:
            evs = getattr(self.combat, attr, None)
            if isinstance(evs, list):
                start = self._last_seen.get(attr, 0)
                fresh = evs[start:]
                if fresh:
                    for e in fresh:
                        try:
                            self.events.append(self._fmt_event(e))
                        except Exception:
                            self.events.append(str(e))
                    self._last_seen[attr] = start + len(fresh)
        if len(self.events) > 600:
            self.events = self.events[-600:]

    # ----- Input / Update ----------------------------------------------------
    def handle(self, event) -> None:
        if not self._built:
            return
        self.btn_step.handle(event)
        self.btn_auto.handle(event)
        self.btn_finish.handle(event)
        self.btn_back.handle(event)

        if event.type == pygame.MOUSEWHEEL and self.rect_log:
            mx, my = pygame.mouse.get_pos()
            if self.rect_log.collidepoint(mx, my):
                self._log_scroll = max(0, self._log_scroll + event.y * 4)

    def update(self, dt: float) -> None:
        if not self._built:
            self.enter()
            return

        mx, my = pygame.mouse.get_pos()
        self.btn_step.update((mx, my))
        self.btn_auto.update((mx, my))
        self.btn_finish.update((mx, my))
        self.btn_back.update((mx, my))

        if self.auto and self.combat and getattr(self.combat, "winner", None) is None:
            for _ in range(self._auto_steps_per_update):
                if getattr(self.combat, "winner", None) is not None:
                    break
                self._advance_once()
            self._ensure_layout()
            self._rebuild_name_maps()
            self._harvest_new_events()

    # ----- Drawing -----------------------------------------------------------
    def draw(self, surf) -> None:
        if not self._built:
            self.enter()
        th = self.theme
        surf.fill(th.bg)

        title = f"{self.home_d.get('name','Home')} vs {self.away_d.get('name','Away')}"
        draw_text(surf, title, (surf.get_width() // 2, 16), 30, th.text, align="center")

        draw_panel(surf, self.rect_panel, th)
        draw_panel(surf, self.rect_grid, th)
        draw_panel(surf, self.rect_log, th)

        status_y = self.rect_panel.y + 16
        winner = getattr(self.combat, "winner", None)
        if self._started and winner is not None:
            wmap = {"home": self.home_d.get("name", "Home"),
                    "away": self.away_d.get("name", "Away"),
                    "draw": "Draw", 0: self.home_d.get("name", "Home"),
                    1: self.away_d.get("name", "Away")}
            wtxt = wmap.get(winner, str(winner))
            draw_text(surf, f"Winner: {wtxt}", (self.rect_panel.x + 16, status_y), 22, th.text)
        else:
            draw_text(surf, "Status: Running" if self.auto else "Status: Paused",
                      (self.rect_panel.x + 16, status_y), 22, th.subt)

        self._draw_grid(surf)
        self._draw_log(surf)

        self.btn_step.draw(surf, th)
        self.btn_auto.draw(surf, th)
        self.btn_finish.draw(surf, th)
        self.btn_back.draw(surf, th)

    def _draw_grid(self, surf: pygame.Surface) -> None:
        if not self.rect_grid:
            return
        rg = self.rect_grid
        gw, gh = _GRID_W, _GRID_H
        cell_w = max(12, (rg.w - 12) // gw)
        cell_h = max(12, (rg.h - 12) // gh)
        origin_x = rg.x + (rg.w - cell_w * gw) // 2
        origin_y = rg.y + (rg.h - cell_h * gh) // 2

        for x in range(gw + 1):
            X = origin_x + x * cell_w
            pygame.draw.line(surf, self.theme.panel_border, (X, origin_y), (X, origin_y + gh * cell_h), 1)
        for y in range(gh + 1):
            Y = origin_y + y * cell_h
            pygame.draw.line(surf, self.theme.panel_border, (origin_x, Y), (origin_x + gw * cell_w, Y), 1)

        fighters = self._fighters()
        for f in fighters:
            x, y = int(getattr(f, "x", 0)), int(getattr(f, "y", 0))
            cx = origin_x + x * cell_w + cell_w // 2
            cy = origin_y + y * cell_h + cell_h // 2

            team_id = getattr(f, "team_id", 0)
            base = (200, 200, 200)
            if self.combat:
                tA = getattr(self.combat, "teamA", None) or getattr(self.combat, "team_home", None)
                tB = getattr(self.combat, "teamB", None) or getattr(self.combat, "team_away", None)
                if tA and team_id == getattr(tA, "tid", -1):
                    base = getattr(tA, "color", base)
                elif tB and team_id == getattr(tB, "tid", -1):
                    base = getattr(tB, "color", base)
            alive = bool(getattr(f, "alive", True))
            color = base if alive else (110, 110, 110)

            radius = max(6, min(cell_w, cell_h) // 3)
            pygame.draw.circle(surf, color, (cx, cy), radius)
            pygame.draw.circle(surf, self.theme.panel_border, (cx, cy), radius, 1)

            name = str(getattr(f, "name", getattr(f, "pid", "F")))
            draw_text(surf, name, (cx, cy + radius + 2), 16, self.theme.text, align="center")

            hp = max(0, int(getattr(f, "hp", 0)))
            mh = max(1, int(getattr(f, "max_hp", max(hp, 1))))
            bar_w = max(24, cell_w - 6)
            bar_h = 6
            bx = cx - bar_w // 2
            by = cy - radius - 10
            pygame.draw.rect(surf, (50, 55, 60), pygame.Rect(bx, by, bar_w, bar_h), border_radius=3)
            if mh > 0:
                fill_w = int(bar_w * (hp / mh))
                pygame.draw.rect(surf, (90, 200, 120), pygame.Rect(bx, by, fill_w, bar_h), border_radius=3)

    # ---- Text wrapping & log drawing ---------------------------------------
    def _measure_w(self, text: str, font_px: int) -> int:
        """Robust text width measurement that works even if Font.size is shadowed."""
        fobj = get_font(font_px)
        # If 'size' is a callable method, use it. Otherwise, render as a fallback.
        size_attr = getattr(fobj, "size", None)
        try:
            if callable(size_attr):
                w, _ = size_attr(text)
                return int(w)
        except Exception:
            pass
        try:
            surf = fobj.render(text, True, (0, 0, 0))
            return int(surf.get_width())
        except Exception:
            # final fallback: rough estimate (monospace-ish)
            return int(len(text) * (font_px * 0.55))

    def _wrap_lines(self, lines: List[str], width_px: int, font_size: int) -> List[str]:
        wrapped: List[str] = []
        for line in lines:
            words = str(line).split()
            if not words:
                wrapped.append("")
                continue
            cur = words[0]
            for w in words[1:]:
                test = f"{cur} {w}"
                if self._measure_w(test, font_size) <= width_px:
                    cur = test
                else:
                    wrapped.append(cur)
                    cur = w
            wrapped.append(cur)
        return wrapped

    def _draw_log(self, surf: pygame.Surface) -> None:
        rl = self.rect_log
        if not rl:
            return

        draw_text(surf, "Event Log", (rl.centerx, rl.y + 6), 20, self.theme.subt, align="center")

        clip = surf.get_clip()
        inner = pygame.Rect(rl.x + 8, rl.y + 28, rl.w - 16, rl.h - 36)
        surf.set_clip(inner)

        wrapped = self._wrap_lines(self.events[-600:], inner.w - 8, 18)
        line_h = 20
        visible = max(1, inner.h // line_h)

        start = max(0, len(wrapped) - visible - self._log_scroll)
        end = min(len(wrapped), start + visible)

        y = inner.y
        for i in range(start, end):
            draw_text(surf, wrapped[i], (inner.x + 4, y), 18, self.theme.text)
            y += line_h

        surf.set_clip(clip)
