# ui/state_match.py
from __future__ import annotations

import pygame
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel, get_font

from engine.tbcombat import TBCombat

# --- Optional engine symbols (guard against branch differences) -------------
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
        d.setdefault("team_id", d.get("team_id", 0))
        d.setdefault("class", d.get("class", d.get("cls", "Fighter")))
        d.setdefault("level", int(d.get("level", d.get("lvl", 1))))
        d.setdefault("hp", int(d.get("hp", 12)))
        d.setdefault("max_hp", int(d.get("max_hp", d["hp"])))
        d.setdefault("ac", int(d.get("ac", 10)))
        d.setdefault("atk", int(d.get("atk", 2)))
        d.setdefault("alive", bool(d.get("alive", True)))
        # support both x/y and tx/ty
        if "tx" in d or "ty" in d:
            d.setdefault("x", d.get("tx", 0))
            d.setdefault("y", d.get("ty", 0))
        else:
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

# typed events formatter (if the newer module exists)
try:
    from engine.events import format_event as _format_event
except Exception:
    _format_event = None


class MatchState(BaseState):
    """
    Left: grid of fighters (circles + HP bars) with names under each dot.
    Right: scrollable wrapped event log.
    Bottom: Step / Auto toggle / Finish / Back.
    """

    def __init__(self, app, home_team: Dict[str, Any], away_team: Dict[str, Any]):
        self.app = app
        self.theme = Theme()

        self.home_d = home_team
        self.away_d = away_team

        self.combat: TBCombat | None = None
        self._built = False
        self._started = False

        # UI
        self.rect_panel: pygame.Rect | None = None
        self.rect_grid: pygame.Rect | None = None
        self.rect_log: pygame.Rect | None = None
        self.btn_step: Button | None = None
        self.btn_auto: Button | None = None
        self.btn_finish: Button | None = None
        self.btn_back: Button | None = None

        # Log
        self.events: List[str] = []
        self._last_seen: Dict[str, int] = {k: 0 for k in ("events", "events_typed", "typed_events", "event_log_typed", "log")}
        self._log_scroll = 0  # wrapped-line units; 0 means stick to bottom

        # Name maps (index/pid -> display name)
        self._idx_to_name: Dict[int, str] = {}
        self._pid_to_name: Dict[str, str] = {}

        # Auto
        self.auto = False
        self._auto_steps_per_update = 10

    # ---------------- Lifecycle ----------------
    def enter(self) -> None:
        self._build_match()
        self._build_ui()
        self._rebuild_name_maps()
        self._harvest_new_events()

    def _build_match(self) -> None:
        # IMPORTANT: TB engine expects matchup-local team IDs 0 (left) and 1 (right).
        teamA = TBTeam(0, self.home_d.get("name", "Home"), tuple(self.home_d.get("color", (180, 180, 220))))
        teamB = TBTeam(1, self.away_d.get("name", "Away"), tuple(self.away_d.get("color", (220, 180, 180))))

        # Accept either key: "fighters" or "roster"; normalize to team_id 0/1
        h_roster = self.home_d.get("fighters") or self.home_d.get("roster") or []
        a_roster = self.away_d.get("fighters") or self.away_d.get("roster") or []

        fighters = [_fighter_from_dict({**fd, "team_id": 0}) for fd in h_roster]
        fighters += [_fighter_from_dict({**fd, "team_id": 1}) for fd in a_roster]

        # Pre-layout: engine may re-layout internally, but we seed a sane one using tx/ty
        if _layout_teams_tiles:
            _layout_teams_tiles(fighters, _GRID_W, _GRID_H)
        else:
            # simple two columns
            yL = yR = 1
            for f in fighters:
                if getattr(f, "team_id", 0) == 0:
                    f.tx, f.ty = 1, yL
                    f.x, f.y = f.tx, f.ty
                    yL = 1 if yL >= _GRID_H - 2 else yL + 2
                else:
                    f.tx, f.ty = _GRID_W - 2, yR
                    f.x, f.y = f.tx, f.ty
                    yR = 1 if yR >= _GRID_H - 2 else yR + 2

        # Spin up combat (engine may clone the list; we just follow whatever it exposes)
        self.combat = TBCombat(teamA, teamB, fighters, _GRID_W, _GRID_H, seed=42)

        # Reset log cursors
        for k in self._last_seen.keys():
            self._last_seen[k] = 0
        self.events.clear()
        self._log_scroll = 0
        self._started = False

    def _build_ui(self) -> None:
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)

        left_w = int(self.rect_panel.w * 0.62)
        self.rect_grid = pygame.Rect(self.rect_panel.x + 12, self.rect_panel.y + 12, left_w - 24, self.rect_panel.h - 84)
        self.rect_log = pygame.Rect(self.rect_panel.x + left_w, self.rect_panel.y + 12, self.rect_panel.w - left_w - 12, self.rect_panel.h - 84)

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

    # ---------------- Helpers ----------------
    def _fighters(self) -> List[Any]:
        if self.combat is None:
            return []
        f = getattr(self.combat, "fighters", None)
        return f if isinstance(f, list) else []

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

    # ---- events -> pretty string -------------------------------------------
    def _fmt_event(self, e: Any) -> str:
        # Preferred: engine.events.format_event
        if _format_event:
            try:
                return _format_event(e)
            except Exception:
                pass

        # Newer dict-typed events
        if isinstance(e, dict):
            t = e.get("type") or e.get("event") or e.get("kind") or "event"
            if t in ("round", "round_start"):
                return f"— Round {e.get('round', '?')} —"
            if t in ("move", "move_step", "Move"):
                who = self._name_from_val(e.get("who") or e.get("name") or e.get("actor") or e.get("i"))
                to = e.get("to") or (e.get("x"), e.get("y"))
                return f"{who} moves to {to}"
            if t in ("attack", "Hit", "Miss"):
                who = self._name_from_val(e.get("who") or e.get("attacker") or e.get("src") or e.get("i"))
                tgt = self._name_from_val(e.get("target") or e.get("defender") or e.get("dst") or e.get("j"))
                if t == "attack":
                    nat = e.get("nat")
                    ac = e.get("target_ac")
                    hit = e.get("hit")
                    crit = e.get("critical")
                    if hit:
                        return f"{who} hits {tgt}{' (CRIT!)' if crit else ''} [d20={nat} vs AC {ac}]"
                    else:
                        return f"{who} misses {tgt} [d20={nat} vs AC {ac}]"
                elif t == "Hit":
                    return f"{who} hits {tgt} for {e.get('dmg','?')}"
                else:
                    return f"{who} misses {tgt}"
            if t in ("damage",):
                who = self._name_from_val(e.get("attacker"))
                tgt = self._name_from_val(e.get("defender"))
                amt = e.get("amount", e.get("dmg", "?"))
                return f"{who} deals {amt} to {tgt}"
            if t in ("down", "Down"):
                who = self._name_from_val(e.get("name") or e.get("who") or e.get("target"))
                return f"{who} is down!"
            if t in ("end", "End", "finish"):
                w = e.get("winner")
                return f"End — Winner: {w}" if w else "End of match"
            return str(e)

        # Older Event(kind, payload) objects
        kind = getattr(e, "kind", None) or getattr(e, "type", None)
        payload = getattr(e, "payload", None)
        if kind:
            return self._fmt_event({"type": kind, **(payload or {})})

        return str(e)

    def _measure_w(self, text: str, font_px: int) -> int:
        fobj = get_font(font_px)
        size_attr = getattr(fobj, "size", None)
        try:
            if callable(size_attr):
                w, _ = size_attr(text)
                return int(w)
        except Exception:
            pass
        try:
            return int(fobj.render(text, True, (0, 0, 0)).get_width())
        except Exception:
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

    # ---------------- Input/Update ----------------
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

    def _advance_once(self) -> None:
        if not self.combat:
            return
        fn = getattr(self.combat, "take_turn", None) or getattr(self.combat, "step", None) \
             or getattr(self.combat, "advance", None) or getattr(self.combat, "tick", None)
        if callable(fn):
            try:
                fn()
            except TypeError:
                try:
                    fn(1)
                except Exception:
                    pass

    def _step(self):
        if self.combat and getattr(self.combat, "winner", None) is None:
            self._started = True
            self._advance_once()
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
                self._rebuild_name_maps()
                self._harvest_new_events()
        self._rebuild_name_maps()
        self._harvest_new_events()

    def _back(self):
        self.app.pop_state()

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
            self._rebuild_name_maps()
            self._harvest_new_events()

    # ---------------- Drawing ----------------
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
            wmap = {0: self.home_d.get("name", "Home"), 1: self.away_d.get("name", "Away"),
                    "home": self.home_d.get("name", "Home"), "away": self.away_d.get("name", "Away"),
                    "draw": "Draw"}
            draw_text(surf, f"Winner: {wmap.get(winner, str(winner))}", (self.rect_panel.x + 16, status_y), 22, th.text)
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

        # grid
        for x in range(gw + 1):
            X = origin_x + x * cell_w
            pygame.draw.line(surf, self.theme.panel_border, (X, origin_y), (X, origin_y + gh * cell_h), 1)
        for y in range(gh + 1):
            Y = origin_y + y * cell_h
            pygame.draw.line(surf, self.theme.panel_border, (origin_x, Y), (origin_x + gw * cell_w, Y), 1)

        # fighters
        for f in self._fighters():
            # support tx/ty and x/y
            tx = int(getattr(f, "tx", getattr(f, "x", 0)))
            ty = int(getattr(f, "ty", getattr(f, "y", 0)))
            cx = origin_x + tx * cell_w + cell_w // 2
            cy = origin_y + ty * cell_h + cell_h // 2

            # team color
            base = (200, 200, 200)
            tid = getattr(f, "team_id", 0)
            if self.combat:
                if tid == 0:
                    base = getattr(self.combat.teamA, "color", base)
                elif tid == 1:
                    base = getattr(self.combat.teamB, "color", base)

            alive = bool(getattr(f, "alive", True))
            color = base if alive else (110, 110, 110)

            r = max(6, min(cell_w, cell_h) // 3)
            pygame.draw.circle(surf, color, (cx, cy), r)
            pygame.draw.circle(surf, self.theme.panel_border, (cx, cy), r, 1)

            name = str(getattr(f, "name", getattr(f, "pid", "F")))
            draw_text(surf, name, (cx, cy + r + 2), 16, self.theme.text, align="center")

            hp = max(0, int(getattr(f, "hp", 0)))
            mh = max(1, int(getattr(f, "max_hp", max(hp, 1))))
            bar_w = max(24, cell_w - 6)
            bar_h = 6
            bx = cx - bar_w // 2
            by = cy - r - 10
            pygame.draw.rect(surf, (50, 55, 60), pygame.Rect(bx, by, bar_w, bar_h), border_radius=3)
            if mh > 0:
                fill_w = int(bar_w * (hp / mh))
                pygame.draw.rect(surf, (90, 200, 120), pygame.Rect(bx, by, fill_w, bar_h), border_radius=3)

    def _harvest_new_events(self) -> None:
        if not self.combat:
            return
        for attr in ("events", "events_typed", "typed_events", "event_log_typed", "log"):
            evs = getattr(self.combat, attr, None)
            if not isinstance(evs, list):
                continue
            start = self._last_seen.get(attr, 0)
            fresh = evs[start:]
            if fresh:
                for e in fresh:
                    try:
                        self.events.append(self._fmt_event(e))
                    except Exception:
                        self.events.append(str(e))
                self._last_seen[attr] = start + len(fresh)
        # trim to reasonable history
        if len(self.events) > 1000:
            self.events = self.events[-1000:]

    def _draw_log(self, surf: pygame.Surface) -> None:
        rl = self.rect_log
        if not rl:
            return

        draw_text(surf, "Event Log", (rl.centerx, rl.y + 6), 20, self.theme.subt, align="center")

        clip = surf.get_clip()
        inner = pygame.Rect(rl.x + 8, rl.y + 28, rl.w - 16, rl.h - 36)
        surf.set_clip(inner)

        wrapped = self._wrap_lines(self.events[-1000:], inner.w - 8, 18)
        line_h = 20
        visible = max(1, inner.h // line_h)

        start = max(0, len(wrapped) - visible - self._log_scroll)
        end = min(len(wrapped), start + visible)

        y = inner.y
        for i in range(start, end):
            draw_text(surf, wrapped[i], (inner.x + 4, y), 18, self.theme.text)
            y += line_h

        surf.set_clip(clip)
