# ui/state_match.py
from __future__ import annotations

import pygame
from dataclasses import dataclass, is_dataclass, asdict
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

from .app import BaseState
from .uiutil import Theme, Button, draw_text, draw_panel, get_font

from engine.tbcombat import TBCombat
try:
    from engine.tbcombat import Team as TBTeam
except Exception:
    @dataclass
    class TBTeam:
        tid: int
        name: str
        color: Tuple[int, int, int]

# optional helpers if present
try:
    from engine.tbcombat import layout_teams_tiles as _layout_teams_tiles
except Exception:
    _layout_teams_tiles = None

try:
    from engine.tbcombat import GRID_W as _GRID_W, GRID_H as _GRID_H
except Exception:
    _GRID_W, _GRID_H = 15, 9

try:
    from engine.events import format_event as _format_event
except Exception:
    _format_event = None


def _mk_fighter(fd: Dict[str, Any]) -> Any:
    d = dict(fd)
    d.setdefault("pid", str(d.get("pid") or d.get("id") or d.get("name") or "F"))
    d.setdefault("name", str(d.get("name") or d["pid"]))
    d.setdefault("team_id", d.get("team_id", 0))
    d.setdefault("class", d.get("class", d.get("cls", "Fighter")))
    d.setdefault("level", int(d.get("level", d.get("lvl", 1))))
    hp = int(d.get("hp", 12))
    d.setdefault("hp", hp)
    d.setdefault("max_hp", int(d.get("max_hp", hp)))
    d.setdefault("ac", int(d.get("ac", 10)))
    d.setdefault("atk", int(d.get("atk", 2)))
    d.setdefault("alive", bool(d.get("alive", True)))
    d.setdefault("x", int(d.get("x", d.get("tx", 0))))
    d.setdefault("y", int(d.get("y", d.get("ty", 0))))
    d.setdefault("tx", d["x"])
    d.setdefault("ty", d["y"])
    return SimpleNamespace(**d)


class MatchState(BaseState):
    """Gridless viewer: large dots, names + HP on top, scrollable log, Next Turn / Next Round / Auto / Finish."""
    def __init__(self, app, home_team: Dict[str, Any], away_team: Dict[str, Any]):
        self.app = app
        self.theme = Theme()

        self.home_d = home_team
        self.away_d = away_team

        self.combat: TBCombat | None = None
        self._started = False

        # Our own team objects for color/name lookup (don’t rely on TBCombat attrs)
        self._teams_by_tid: Dict[int, TBTeam] = {}

        # UI rects + buttons
        self.rect_panel = pygame.Rect(0, 0, 0, 0)
        self.rect_grid  = pygame.Rect(0, 0, 0, 0)
        self.rect_log   = pygame.Rect(0, 0, 0, 0)
        self.btn_turn:   Button | None = None
        self.btn_round:  Button | None = None
        self.btn_auto:   Button | None = None
        self.btn_finish: Button | None = None
        self.btn_back:   Button | None = None

        # Event log + name maps
        self.events: List[str] = []
        self._last_seen = {k: 0 for k in ("events_typed", "typed_events", "event_log_typed", "events", "log")}
        self._idx_to_name: Dict[int, str] = {}
        self._pid_to_name: Dict[str, str] = {}
        self._log_scroll = 0
        self._last_round_no: int | None = None  # for Next Round detection

        self.auto = False
        self._auto_steps_per_update = 10
        self._built = False

    # ---------- helpers ----------
    def _fighters(self) -> List[Any]:
        if not self.combat: return []
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
            if "name" in v: return str(v["name"])
            pid = v.get("pid")
            if pid is not None: return self._pid_to_name.get(str(pid), str(pid))
        if hasattr(v, "name"):  # object w/ name attr
            return str(getattr(v, "name"))
        if hasattr(v, "pid"):
            pid = getattr(v, "pid")
            return self._pid_to_name.get(str(pid), str(pid))
        return "?"

    def _team_color_for_tid(self, tid: int) -> Tuple[int, int, int]:
        t = self._teams_by_tid.get(int(tid))
        if t: return tuple(getattr(t, "color", (200, 200, 200)))
        return (200, 200, 200)

    # ---------- event normalization + formatting ----------
    def _normalize_event(self, e: Any) -> Dict[str, Any]:
        """Return a dict-like view of the event regardless of representation."""
        if isinstance(e, dict):
            d = dict(e)
            d.setdefault("type", d.get("type") or d.get("event") or d.get("kind") or "event")
            return d
        if is_dataclass(e):
            d = asdict(e)
            d.setdefault("type", getattr(e, "type", e.__class__.__name__))
            return d
        if hasattr(e, "__dict__"):
            d = dict(e.__dict__)
            d.setdefault("type", getattr(e, "type", e.__class__.__name__))
            return d
        # string or unknown — return as string-wrapped dict
        return {"type": "str", "s": str(e)}

    def _fmt_event(self, e_raw: Any) -> str:
        if _format_event:
            try:
                return _format_event(e_raw)
            except Exception:
                pass

        e = self._normalize_event(e_raw)
        t = e.get("type", "event")

        def who_from(keys=("who","actor","attacker","src","i","a","idx","actor_idx","attacker_idx","src_idx")):
            for k in keys:
                if k in e: return self._name_from_val(e[k])
            return "?"

        def tgt_from(keys=("target","defender","dst","j","b","target_idx","defender_idx","dst_idx")):
            for k in keys:
                if k in e: return self._name_from_val(e[k])
            return "?"

        if t in ("round","StartRound","start","Round","Start"):
            rn = e.get("round", e.get("r", None))
            try:
                self._last_round_no = int(rn) if rn is not None else self._last_round_no
            except Exception:
                pass
            rn_txt = rn if rn is not None else "?"
            return f"— Round {rn_txt} —"

        if t in ("move","Move"):
            to = e.get("to")
            if not to:
                to = (e.get("x"), e.get("y"))
            return f"{who_from()} moves to {to}"

        if t in ("hit","Hit"):
            dmg = e.get("dmg") or e.get("damage") or e.get("amount") or "?"
            return f"{who_from()} hits {tgt_from()} for {dmg}"

        if t in ("miss","Miss"):
            return f"{who_from()} misses {tgt_from()}"

        if t in ("down","Down","KO"):
            w = who_from()
            if w == "?":
                w = tgt_from()
            return f"{w} is down!"

        if t in ("end","End","finish","Finish"):
            return "End of match"

        # string fallback with index->name substitution
        s = e.get("s")
        if s is not None:
            import re as _re
            def repl(m):
                key, val = m.group(1), int(m.group(2))
                return f" {key}={self._idx_to_name.get(val, f'#{val}')}"
            return _re.sub(r"\b(i|j|a|b|src|dst|attacker|defender)\s*=\s*(\d+)", repl, s)

        # generic dict pretty-print resolving any actor/target-ish keys to names
        try:
            parts = []
            for k, v in e.items():
                if k in ("who","actor","attacker","src","i","a","idx","actor_idx","attacker_idx","src_idx",
                         "target","defender","dst","j","b","target_idx","defender_idx","dst_idx"):
                    v = self._name_from_val(v)
                parts.append(f"{k}={v}")
            return ", ".join(parts)
        except Exception:
            return str(e_raw)

    # ---------- lifecycle ----------
    def enter(self) -> None:
        self._build_match()
        self._build_ui()
        self._rebuild_name_maps()
        self._harvest_new_events()
        self._built = True

    def _build_match(self) -> None:
        # Build our own team objects (ids 0/1)
        tA = TBTeam(0, self.home_d.get("name","Home"), tuple(self.home_d.get("color",(180,180,220))))
        tB = TBTeam(1, self.away_d.get("name","Away"), tuple(self.away_d.get("color",(220,180,180))))
        self._teams_by_tid = {0: tA, 1: tB}

        # Fighters mapped into tid 0/1
        h_roster = self.home_d.get("fighters") or self.home_d.get("roster") or []
        a_roster = self.away_d.get("fighters") or self.away_d.get("roster") or []
        fighters: List[Any] = []
        for idx, fd in enumerate(h_roster): fighters.append(_mk_fighter({**fd, "team_id": 0, "pid": fd.get("pid") or f"H{idx}"}))
        for idx, fd in enumerate(a_roster): fighters.append(_mk_fighter({**fd, "team_id": 1, "pid": fd.get("pid") or f"A{idx}"}))

        # Pre-layout (engine helper if available, else two columns)
        if _layout_teams_tiles: _layout_teams_tiles(fighters, _GRID_W, _GRID_H)
        else: self._layout_two_columns(fighters)

        # Start combat
        self.combat = TBCombat(tA, tB, fighters, _GRID_W, _GRID_H, seed=42)

        self._ensure_layout()

        # reset log tracking
        for k in self._last_seen: self._last_seen[k] = 0
        self.events.clear()
        self._log_scroll = 0
        self._last_round_no = None
        self._started = False

    def _layout_two_columns(self, fighters: List[Any]) -> None:
        left  = [f for f in fighters if getattr(f, "team_id", 0) == 0]
        right = [f for f in fighters if getattr(f, "team_id", 0) == 1]
        gapL = max(1, _GRID_H // (len(left)  + 1)) if left  else 2
        gapR = max(1, _GRID_H // (len(right) + 1)) if right else 2
        for i, f in enumerate(left,  start=1): f.x = f.tx = 1;               f.y = f.ty = min(_GRID_H-1, i*gapL)
        for i, f in enumerate(right, start=1): f.x = f.tx = max(0,_GRID_W-2); f.y = f.ty = min(_GRID_H-1, i*gapR)

    def _ensure_layout(self) -> None:
        fs = self._fighters()
        if not fs: return
        coords = [(int(getattr(f,"x",getattr(f,"tx",0))), int(getattr(f,"y",getattr(f,"ty",0)))) for f in fs]
        if len(set(coords)) <= 2:
            if _layout_teams_tiles: _layout_teams_tiles(fs, _GRID_W, _GRID_H)
            else: self._layout_two_columns(fs)

    def _build_ui(self) -> None:
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)
        split = int(self.rect_panel.w * 0.62)
        self.rect_grid = pygame.Rect(self.rect_panel.x + 12, self.rect_panel.y + 12, split - 24, self.rect_panel.h - 84)
        self.rect_log  = pygame.Rect(self.rect_panel.x + split, self.rect_panel.y + 12, self.rect_panel.w - split - 24, self.rect_panel.h - 84)

        # Five buttons: Next Turn, Next Round, Auto, Finish, Back
        btn_w, btn_h, gap = 150, 44, 10
        y = self.rect_panel.bottom - (btn_h + 10)
        x = self.rect_panel.x + 12
        self.btn_turn   = Button(pygame.Rect(x, y, btn_w, btn_h), "Next Turn", self._next_turn)
        x += btn_w + gap
        self.btn_round  = Button(pygame.Rect(x, y, btn_w, btn_h), "Next Round", self._next_round)
        x += btn_w + gap
        self.btn_auto   = Button(pygame.Rect(x, y, btn_w, btn_h), f"Auto: {'ON' if self.auto else 'OFF'}", self._toggle_auto)
        x += btn_w + gap
        self.btn_finish = Button(pygame.Rect(x, y, btn_w, btn_h), "Finish", self._finish)
        self.btn_back   = Button(pygame.Rect(self.rect_panel.right - (btn_w + 12), y, btn_w, btn_h), "Back", self._back)

    # ---------- control ----------
    def _advance_once(self) -> None:
        if not self.combat: return
        c = self.combat
        for name in ("take_turn","step","advance","tick","update"):
            fn = getattr(c, name, None)
            if not callable(fn): continue
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

    def _refresh_after_advance(self) -> None:
        self._ensure_layout()
        self._rebuild_name_maps()
        self._harvest_new_events()

    def _next_turn(self):
        if self.combat and getattr(self.combat, "winner", None) is None:
            self._started = True
            self._advance_once()
            self._refresh_after_advance()

    def _next_round(self):
        if not self.combat: return
        self._started = True
        start_round = self._last_round_no
        for _ in range(5000):
            if getattr(self.combat, "winner", None) is not None:
                break
            self._advance_once()
            # harvest periodically so we see the round boundary
            self._harvest_new_events()
            if self._last_round_no is not None and start_round is not None and self._last_round_no > start_round:
                break
        self._refresh_after_advance()

    def _toggle_auto(self):
        self.auto = not self.auto
        if self.btn_auto: self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"
        if self.auto: self._started = True

    def _finish(self):
        if not self.combat: return
        self._started = True
        for i in range(20000):
            if getattr(self.combat, "winner", None) is not None: break
            self._advance_once()
            if i % 12 == 0: self._harvest_new_events()
        self._refresh_after_advance()

    def _back(self): self.app.pop_state()

    # ---------- events ----------
    def _harvest_new_events(self):
        if not self.combat: return
        for attr in ("events_typed","typed_events","event_log_typed","events","log"):
            evs = getattr(self.combat, attr, None)
            if not isinstance(evs, list): continue
            start = self._last_seen.get(attr, 0)
            fresh = evs[start:]
            if fresh:
                for e in fresh:
                    # update round tracker from raw event if possible
                    try:
                        ev = self._normalize_event(e)
                        if ev.get("type") in ("round","StartRound","Round","start","Start"):
                            rn = ev.get("round", ev.get("r", None))
                            if rn is not None:
                                try: self._last_round_no = int(rn)
                                except Exception: pass
                    except Exception:
                        pass
                    # append formatted string
                    try: self.events.append(self._fmt_event(e))
                    except Exception: self.events.append(str(e))
                self._last_seen[attr] = start + len(fresh)
        if len(self.events) > 800: self.events = self.events[-800:]

    # ---------- update/draw ----------
    def handle(self, event) -> None:
        if self.btn_turn:   self.btn_turn.handle(event)
        if self.btn_round:  self.btn_round.handle(event)
        if self.btn_auto:   self.btn_auto.handle(event)
        if self.btn_finish: self.btn_finish.handle(event)
        if self.btn_back:   self.btn_back.handle(event)
        if event.type == pygame.MOUSEWHEEL and self.rect_log:
            mx, my = pygame.mouse.get_pos()
            if self.rect_log.collidepoint(mx, my):
                self._log_scroll = max(0, self._log_scroll + event.y * 4)

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        if self.btn_turn:   self.btn_turn.update((mx,my))
        if self.btn_round:  self.btn_round.update((mx,my))
        if self.btn_auto:   self.btn_auto.update((mx,my))
        if self.btn_finish: self.btn_finish.update((mx,my))
        if self.btn_back:   self.btn_back.update((mx,my))

        if self.auto and self.combat and getattr(self.combat, "winner", None) is None:
            for _ in range(self._auto_steps_per_update):
                if getattr(self.combat, "winner", None) is not None: break
                self._advance_once()
            self._refresh_after_advance()

    def draw(self, surf: pygame.Surface) -> None:
        if not self._built: self.enter()
        th = self.theme
        surf.fill(th.bg)

        title = f"{self.home_d.get('name','Home')} vs {self.away_d.get('name','Away')}"
        draw_text(surf, title, (surf.get_width()//2, 16), 30, th.text, align="center")

        draw_panel(surf, self.rect_panel, th)
        draw_panel(surf, self.rect_grid, th)
        draw_panel(surf, self.rect_log, th)

        status_y = self.rect_panel.y + 16
        winner = getattr(self.combat, "winner", None) if self.combat else None
        if self._started and winner is not None:
            wmap = {"home": self.home_d.get("name","Home"),
                    "away": self.away_d.get("name","Away"),
                    "draw": "Draw", 0: self.home_d.get("name","Home"),
                    1: self.away_d.get("name","Away")}
            draw_text(surf, f"Winner: {wmap.get(winner, str(winner))}", (self.rect_panel.x + 16, status_y), 26, th.text)
        else:
            draw_text(surf, "Status: Running" if self.auto else "Status: Paused",
                      (self.rect_panel.x + 16, status_y), 22, th.subt)

        self._draw_gridless_fighters(surf)
        self._draw_log(surf)

        if self.btn_turn:   self.btn_turn.draw(surf, th)
        if self.btn_round:  self.btn_round.draw(surf, th)
        if self.btn_auto:   self.btn_auto.draw(surf, th)
        if self.btn_finish: self.btn_finish.draw(surf, th)
        if self.btn_back:   self.btn_back.draw(surf, th)

    # ---------- fighter rendering (no gridlines) ----------
    def _draw_gridless_fighters(self, surf: pygame.Surface) -> None:
        rg = self.rect_grid
        gw, gh = _GRID_W, _GRID_H
        # Larger "cells" to give more breathing room
        cell_w = max(20, (rg.w - 12) // gw)
        cell_h = max(20, (rg.h - 12) // gh)
        ox = rg.x + (rg.w - cell_w * gw) // 2
        oy = rg.y + (rg.h - cell_h * gh) // 2

        # no gridlines — just draw fighters
        for f in self._fighters():
            x = int(getattr(f, "x", getattr(f, "tx", 0)))
            y = int(getattr(f, "y", getattr(f, "ty", 0)))
            cx = ox + x * cell_w + cell_w // 2
            cy = oy + y * cell_h + cell_h // 2

            tid = int(getattr(f, "team_id", 0))
            base = self._team_color_for_tid(tid)
            alive = bool(getattr(f, "alive", True))
            color = base if alive else (110, 110, 110)

            r = max(10, min(cell_w, cell_h) // 2)
            # HP bar and name ABOVE the dot to reduce overlap
            name = str(getattr(f, "name", getattr(f, "pid", "F")))
            hp = max(0, int(getattr(f, "hp", 0)))
            mh = max(1, int(getattr(f, "max_hp", max(hp, 1))))
            bar_w = max(32, cell_w - 2)
            bar_h = 7
            bar_x = cx - bar_w // 2
            bar_y = cy - r - 20  # higher above dot

            # name just above the bar
            draw_text(surf, name, (cx, bar_y - 18), 14, self.theme.text, align="center")
            # HP bar
            pygame.draw.rect(surf, (50, 55, 60), pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=3)
            if mh > 0:
                fill_w = int(bar_w * (hp / mh))
                pygame.draw.rect(surf, (90, 200, 120), pygame.Rect(bar_x, bar_y, fill_w, bar_h), border_radius=3)

            # the dot
            pygame.draw.circle(surf, color, (cx, cy), r)
            pygame.draw.circle(surf, self.theme.panel_border, (cx, cy), r, 1)

    # ---------- log ----------
    def _measure_w(self, text: str, font_px: int) -> int:
        font = get_font(font_px)
        size_attr = getattr(font, "size", None)
        try:
            if callable(size_attr):
                w, _ = size_attr(text)
                return int(w)
        except Exception:
            pass
        try:
            return int(font.render(text, True, (0, 0, 0)).get_width())
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

    def _draw_log(self, surf: pygame.Surface) -> None:
        rl = self.rect_log
        draw_text(surf, "Event Log", (rl.centerx, rl.y + 6), 20, self.theme.subt, align="center")

        clip = surf.get_clip()
        inner = pygame.Rect(rl.x + 8, rl.y + 28, rl.w - 16, rl.h - 36)
        surf.set_clip(inner)

        wrapped = self._wrap_lines(self.events[-800:], inner.w - 8, 18)
        line_h = 20
        visible = max(1, inner.h // line_h)
        start = max(0, len(wrapped) - visible - self._log_scroll)
        end = min(len(wrapped), start + visible)

        y = inner.y
        for i in range(start, end):
            draw_text(surf, wrapped[i], (inner.x + 4, y), 18, self.theme.text)
            y += line_h

        surf.set_clip(clip)
