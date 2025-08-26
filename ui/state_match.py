# ui/state_match.py
from __future__ import annotations

import pygame
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple, Optional, DefaultDict
from collections import defaultdict

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
        color: Tuple[int, int, int]  # <- correct Python typing

# Optional helpers if present
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


# -------------------- helpers & constants --------------------
TARGET_CELL_W = 72
TARGET_CELL_H = 92
DOT_RADIUS_F  = 0.22  # fraction of min(cell_w, cell_h)

COLOR_RED  = (220, 70, 70)
COLOR_BLUE = (70, 120, 230)
COLOR_HP_BG   = (50, 55, 60)
COLOR_HP_FILL = (90, 200, 120)

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

def _short_name(name: str) -> str:
    """Format 'F. Lastname' with modest fallback."""
    parts = [p for p in str(name).strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        s = parts[0]
        return s if len(s) <= 14 else s[:13] + "…"
    first, last = parts[0], parts[-1]
    return f"{first[0].upper()}. {last}"


class MatchState(BaseState):
    """Match viewer:
       - Smaller in-cell name as 'F. Lastname'
       - Downed fighters hidden
       - Overlap avoided visually via offsets (engine now also prevents same-tile)
       - User team = red, opponent = blue (fallback Home red / Away blue)
       - Next Turn (one actor), Next Round, Auto, Finish
    """

    def __init__(self, app, home_team: Dict[str, Any], away_team: Dict[str, Any]):
        self.app = app
        self.theme = Theme()

        self.home_d = home_team
        self.away_d = away_team

        self.combat: Optional[TBCombat] = None
        self._started = False

        # Will be set in _decide_team_colors()
        self._color_for_tid: Dict[int, Tuple[int, int, int]] = {0: COLOR_RED, 1: COLOR_BLUE}

        # teams as TBTeam objects
        self._teams_by_tid: Dict[int, TBTeam] = {}

        # UI rects + buttons
        self.rect_panel = pygame.Rect(0, 0, 0, 0)
        self.rect_grid  = pygame.Rect(0, 0, 0, 0)
        self.rect_log   = pygame.Rect(0, 0, 0, 0)
        self.btn_turn:   Optional[Button] = None
        self.btn_round:  Optional[Button] = None
        self.btn_auto:   Optional[Button] = None
        self.btn_finish: Optional[Button] = None  # behaves like Back

        # log + tracking
        self.events: List[str] = []
        self._last_seen = {k: 0 for k in ("events_typed","typed_events","event_log_typed","events","log")}
        self._last_round_seen = 0
        self._log_scroll = 0

        # name maps
        self._idx_to_name: Dict[int, str] = {}
        self._pid_to_name: Dict[str, str] = {}
        self._name_to_pid: Dict[str, str] = {}

        # HP cache
        self._hp_max: Dict[str, int] = {}
        self._hp_cur: Dict[str, int] = {}
        self._alive_prev: Dict[str, bool] = {}

        # raw events for Next Turn
        self._raw_attr: Optional[str] = None
        self._raw_seen: int = 0

        self.auto = False
        self._auto_steps_per_update = 10
        self._built = False

    # ---------- basic getters ----------
    def _fighters(self) -> List[Any]:
        return getattr(self.combat, "fighters", []) if self.combat else []

    def _fighter_alive(self, f: Any) -> bool:
        pid = str(getattr(f, "pid", getattr(f, "name", "")))
        hp  = self._hp_cur.get(pid, int(getattr(f, "hp", 1)))
        return hp > 0 and bool(getattr(f, "alive", True))

    def _fighter_hp(self, f: Any) -> Tuple[int,int]:
        pid = str(getattr(f, "pid", getattr(f, "name", "")))
        mh  = self._hp_max.get(pid, int(getattr(f, "max_hp", getattr(f, "hp", 12))))
        hp  = self._hp_cur.get(pid, int(getattr(f, "hp", mh)))
        mh = max(1, mh); hp = max(0, min(mh, hp))
        return hp, mh

    def _rebuild_name_maps(self) -> None:
        self._idx_to_name.clear()
        self._pid_to_name.clear()
        self._name_to_pid.clear()
        for i, f in enumerate(self._fighters()):
            name = str(getattr(f, "name", getattr(f, "pid", f"F{i}")))
            pid  = str(getattr(f, "pid", name))
            self._idx_to_name[i] = name
            self._pid_to_name[pid] = name
            self._name_to_pid[name] = pid

    def _current_round_from_engine(self) -> Optional[int]:
        return getattr(self.combat, "round", None) if self.combat else None

    # ---------- colors ----------
    def _decide_team_colors(self) -> None:
        """Make user's team red, opponent blue. Fallback to Home=red/Away=blue."""
        user_tid = None
        car = getattr(self.app, "career", None)
        if car is not None:
            user_tid = getattr(car, "user_team_id", None)

        ht = int(self.home_d.get("tid", 0))
        at = int(self.away_d.get("tid", 1))
        if user_tid is not None:
            if ht == user_tid:
                self._color_for_tid = {ht: COLOR_RED, at: COLOR_BLUE}
            elif at == user_tid:
                self._color_for_tid = {ht: COLOR_BLUE, at: COLOR_RED}
            else:
                self._color_for_tid = {ht: COLOR_RED, at: COLOR_BLUE}
        else:
            self._color_for_tid = {ht: COLOR_RED, at: COLOR_BLUE}

    def _team_color_for_tid(self, tid: int) -> Tuple[int, int, int]:
        return self._color_for_tid.get(int(tid), COLOR_BLUE)

    # ---------- HP & identity caches ----------
    def _init_hp_cache(self) -> None:
        self._hp_max.clear()
        self._hp_cur.clear()
        self._alive_prev.clear()
        for f in self._fighters():
            pid = str(getattr(f, "pid", getattr(f, "name", "")))
            if not pid: continue
            mh = int(getattr(f, "max_hp", getattr(f, "hp", 12)))
            hp = int(getattr(f, "hp", mh))
            self._hp_max[pid] = max(1, mh)
            self._hp_cur[pid] = max(0, min(mh, hp))
            self._alive_prev[pid] = bool(getattr(f, "alive", True))

    def _pid_from_event_field(self, val: Any) -> Optional[str]:
        if val is None: return None
        if isinstance(val, str):
            return self._name_to_pid.get(val, val)
        if isinstance(val, int):
            nm = self._idx_to_name.get(val)
            return self._name_to_pid.get(nm, None)
        if isinstance(val, dict):
            if "pid" in val: return str(val["pid"])
            if "name" in val: return self._name_to_pid.get(str(val["name"]))
        if hasattr(val, "pid"): return str(getattr(val, "pid"))
        if hasattr(val, "name"): return self._name_to_pid.get(str(getattr(val, "name")))
        return None

    # ---------- event formatting ----------
    def _name_from_val(self, v: Any) -> str:
        if isinstance(v, str): return self._pid_to_name.get(v, v)
        if isinstance(v, int): return self._idx_to_name.get(v, f"#{v}")
        if isinstance(v, dict):
            if "name" in v: return str(v["name"])
            pid = v.get("pid")
            if pid is not None: return self._pid_to_name.get(str(pid), str(pid))
        if hasattr(v, "name"): return str(getattr(v, "name"))
        if hasattr(v, "pid"):  return self._pid_to_name.get(str(getattr(v, "pid")), str(getattr(v, "pid")))
        return "?"

    def _fmt_event(self, e: Any) -> str:
        if _format_event:
            try:
                s = _format_event(e)
                if isinstance(s, str) and s.strip(): return s
            except Exception:
                pass

        if isinstance(e, dict):
            t = e.get("type") or e.get("event") or e.get("kind") or "event"
            actor_keys = ("name","who","actor","src","attacker","unit","who_id","actor_id","src_id","attacker_id")
            targ_keys  = ("target","defender","dst","target_id","defender_id","dst_id")

            def who_from() -> str:
                nm = e.get("who_name") or e.get("actor_name") or e.get("attacker_name") or e.get("unit_name")
                if nm: return str(nm)
                for k in actor_keys:
                    if k in e: return self._name_from_val(e[k])
                return "?"

            def tgt_from() -> str:
                nm = e.get("target_name") or e.get("defender_name")
                if nm: return str(nm)
                for k in targ_keys:
                    if k in e: return self._name_from_val(e[k])
                return "?"

            if t in ("round","StartRound","start"):
                r = e.get("round", e.get("r", "?"))
                try: self._last_round_seen = int(r)
                except Exception: pass
                return f"— Round {r} —"
            if t in ("move","Move"):
                to = e.get("to") or (e.get("x"), e.get("y"))
                return f"{who_from()} moves to {to}"
            if t in ("hit","Hit"):
                dmg = e.get("dmg") or e.get("damage") or e.get("amount") or "?"
                return f"{who_from()} hits {tgt_from()} for {dmg}"
            if t in ("miss","Miss"):
                return f"{who_from()} misses {tgt_from()}"
            if t in ("down","Down"):
                nm = e.get("name") or e.get("who") or e.get("target") or e.get("defender") or who_from() or tgt_from()
                return f"{self._name_from_val(nm)} is down!"
            if t in ("end","End","finish"):
                return "End of match"

            parts = []
            for k, v in e.items():
                if k in actor_keys or k in targ_keys: v = self._name_from_val(v)
                parts.append(f"{k}={v}")
            return ", ".join(parts)

        # fallback: replace indices with names where possible
        import re as _re
        s = str(e)
        def repl(m):
            key, val = m.group(1), int(m.group(2))
            return f" {key}={self._idx_to_name.get(val, f'#{val}')}"
        return _re.sub(r"\b(i|j|a|b|src|dst|attacker|defender)\s*=\s*(\d+)", repl, s)

    # ---------- lifecycle ----------
    def enter(self) -> None:
        self._build_match()
        self._decide_team_colors()
        self._build_ui()
        self._rebuild_name_maps()
        self._init_hp_cache()
        self._reset_raw_tracker()
        self._harvest_new_events()
        self._built = True

    def _build_match(self) -> None:
        ht = int(self.home_d.get("tid", 0))
        at = int(self.away_d.get("tid", 1))
        tA = TBTeam(ht, self.home_d.get("name","Home"), COLOR_RED)
        tB = TBTeam(at, self.away_d.get("name","Away"), COLOR_BLUE)
        self._teams_by_tid = {ht: tA, at: tB}

        h_roster = self.home_d.get("fighters") or self.home_d.get("roster") or []
        a_roster = self.away_d.get("fighters") or self.away_d.get("roster") or []
        fighters: List[Any] = []
        for idx, fd in enumerate(h_roster):
            fighters.append(_mk_fighter({**fd, "team_id": ht, "pid": fd.get("pid") or f"H{idx}"}))
        for idx, fd in enumerate(a_roster):
            fighters.append(_mk_fighter({**fd, "team_id": at, "pid": fd.get("pid") or f"A{idx}"}))

        if _layout_teams_tiles: _layout_teams_tiles(fighters, _GRID_W, _GRID_H)
        else: self._layout_two_columns(fighters, ht, at)

        self.combat = TBCombat(tA, tB, fighters, _GRID_W, _GRID_H, seed=42)
        self._ensure_layout()

        # reset trackers
        for k in self._last_seen: self._last_seen[k] = 0
        self.events.clear()
        self._log_scroll = 0
        self._last_round_seen = 0
        self._started = False

    def _layout_two_columns(self, fighters: List[Any], ht: int, at: int) -> None:
        left  = [f for f in fighters if getattr(f, "team_id", 0) == ht]
        right = [f for f in fighters if getattr(f, "team_id", 0) == at]
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
            else:
                tids = {int(getattr(f,"team_id",0)) for f in fs}
                if len(tids) == 2:
                    ht, at = sorted(list(tids))[:2]
                else:
                    ht, at = 0, 1
                self._layout_two_columns(fs, ht, at)

    def _build_ui(self) -> None:
        W, H = self.app.width, self.app.height
        self.rect_panel = pygame.Rect(16, 60, W - 32, H - 76)
        split = int(self.rect_panel.w * 0.70)
        self.rect_grid = pygame.Rect(self.rect_panel.x + 12, self.rect_panel.y + 12,
                                     split - 24, self.rect_panel.h - 84)
        self.rect_log  = pygame.Rect(self.rect_panel.x + split, self.rect_panel.y + 12,
                                     self.rect_panel.w - split - 24, self.rect_panel.h - 84)

        btn_w, btn_h, gap = 160, 44, 10
        y = self.rect_panel.bottom - (btn_h + 10)
        x = self.rect_panel.x + 12
        self.btn_turn   = Button(pygame.Rect(x, y, btn_w, btn_h), "Next Turn",  self._next_turn)
        x += btn_w + gap
        self.btn_round  = Button(pygame.Rect(x, y, btn_w, btn_h), "Next Round", self._next_round)
        x += btn_w + gap
        self.btn_auto   = Button(pygame.Rect(x, y, btn_w, btn_h), f"Auto: {'ON' if self.auto else 'OFF'}", self._toggle_auto)
        self.btn_finish = Button(pygame.Rect(self.rect_panel.right - (btn_w + 12), y, btn_w, btn_h), "Finish", self._back)

    # ---------- raw event tracker ----------
    def _reset_raw_tracker(self) -> None:
        for attr in ("events_typed","typed_events","event_log_typed","events","log"):
            if isinstance(getattr(self.combat, attr, None), list):
                self._raw_attr = attr
                self._raw_seen = len(getattr(self.combat, attr))
                break

    def _raw_since(self, base: int) -> List[Any]:
        if not self._raw_attr or not self.combat: return []
        evs = getattr(self.combat, self._raw_attr, [])
        return evs[base:]

    # ---------- controls ----------
    def _advance_once(self) -> None:
        if not self.combat: return
        c = self.combat
        for name in ("take_turn","step","advance","tick","update"):
            fn = getattr(c, name, None)
            if not callable(fn): continue
            try:
                fn(1); return
            except TypeError:
                try: fn(); return
                except Exception: continue
            except Exception:
                continue

    def _harvest_and_refresh(self) -> None:
        self._ensure_layout()
        self._rebuild_name_maps()
        self._harvest_new_events()

    def _next_turn(self):
        if not self.combat or getattr(self.combat, "winner", None) is not None: return
        self._started = True
        base_raw = len(getattr(self.combat, self._raw_attr, [])) if self._raw_attr else 0
        start_round = self._current_round_from_engine() or self._last_round_seen
        actor_name: Optional[str] = None

        for _ in range(500):
            self._advance_once()
            self._harvest_and_refresh()
            if getattr(self.combat, "winner", None) is not None: break

            new_raw = self._raw_since(base_raw)
            for e in new_raw:
                if isinstance(e, dict):
                    nm = e.get("name") or e.get("actor") or e.get("who") or e.get("src")
                    if nm:
                        nm = self._name_from_val(nm)
                        if actor_name is None:
                            actor_name = nm
                        elif nm != actor_name:
                            return  # stop on actor change

            cur_round = self._current_round_from_engine() or self._last_round_seen
            if cur_round is not None and start_round is not None and cur_round > start_round:
                return

    def _next_round(self):
        if not self.combat or getattr(self.combat, "winner", None) is not None: return
        self._started = True
        target = (self._current_round_from_engine() or self._last_round_seen) + 1
        for _ in range(20000):
            if getattr(self.combat, "winner", None) is not None: break
            self._advance_once()
            self._harvest_and_refresh()
            cur = self._current_round_from_engine() or self._last_round_seen
            if cur >= target: break

    def _toggle_auto(self):
        self.auto = not self.auto
        if self.btn_auto: self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"
        if self.auto: self._started = True

    def _back(self): self.app.pop_state()

    # ---------- event ingest (updates HP & log) ----------
    def _harvest_new_events(self):
        if not self.combat: return

        def detect_newly_dead() -> List[str]:
            newly: List[str] = []
            for f in self._fighters():
                pid = str(getattr(f, "pid", getattr(f, "name", "")))
                if not pid: continue
                alive = bool(getattr(f, "alive", True))
                prev  = self._alive_prev.get(pid, True)
                if prev and not alive:
                    newly.append(self._pid_to_name.get(pid, pid))
                self._alive_prev[pid] = alive
            return newly

        for attr in ("events_typed","typed_events","event_log_typed","events","log"):
            evs = getattr(self.combat, attr, None)
            if not isinstance(evs, list): continue
            start = self._last_seen.get(attr, 0)
            fresh = evs[start:]
            if fresh and start == 0:
                print("[Match] sample events:", fresh[:5])

            # update HP cache first
            for e in fresh:
                try:
                    if isinstance(e, dict):
                        t = e.get("type") or e.get("event") or e.get("kind")
                        if t in ("hit","Hit"):
                            dmg = int(e.get("dmg") or e.get("damage") or e.get("amount") or 0)
                            tgt = e.get("target", e.get("defender", e.get("dst")))
                            pid = self._pid_from_event_field(tgt)
                            if pid and pid in self._hp_max:
                                self._hp_cur[pid] = max(0, self._hp_cur.get(pid, self._hp_max[pid]) - dmg)
                        elif t in ("down","Down"):
                            nm = e.get("name") or e.get("target") or e.get("defender")
                            pid = self._pid_from_event_field(nm) if nm is not None else None
                            if pid and pid in self._hp_max:
                                self._hp_cur[pid] = 0
                except Exception:
                    pass

            # then log lines
            for e in fresh:
                try:
                    s = self._fmt_event(e)
                    if s.strip() == "? is down!":
                        new_dead = detect_newly_dead()
                        if new_dead:
                            s = f"{new_dead[0]} is down!"
                    if isinstance(s, str) and s.startswith("— Round "):
                        try:
                            num = int(s.replace("— Round ","").replace(" —","").strip())
                            self._last_round_seen = max(self._last_round_seen, num)
                        except Exception:
                            pass
                    self.events.append(s)
                except Exception:
                    self.events.append(str(e))

            self._last_seen[attr] = start + len(fresh)

        if len(self.events) > 800: self.events = self.events[-800:]

    # ---------- update/draw ----------
    def handle(self, event) -> None:
        if self.btn_turn:   self.btn_turn.handle(event)
        if self.btn_round:  self.btn_round.handle(event)
        if self.btn_auto:   self.btn_auto.handle(event)
        if self.btn_finish: self.btn_finish.handle(event)
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

        if self.auto and self.combat and getattr(self.combat, "winner", None) is None:
            for _ in range(self._auto_steps_per_update):
                if getattr(self.combat, "winner", None) is not None: break
                self._advance_once()
            self._harvest_and_refresh()

    def draw(self, surf: pygame.Surface) -> None:
        if not self._built: self.enter()
        th = self.theme
        surf.fill(th.bg)

        title = f"{self.home_d.get('name','Home')} vs {self.away_d.get('name','Away')}"
        draw_text(surf, title, (surf.get_width()//2, 16), 28, th.text, align="center")

        draw_panel(surf, self.rect_panel, th)
        draw_panel(surf, self.rect_grid, th)   # no gridlines
        draw_panel(surf, self.rect_log, th)

        status_y = self.rect_panel.y + 16
        winner = getattr(self.combat, "winner", None) if self.combat else None
        if self._started and winner is not None:
            wmap = {"home": self.home_d.get("name","Home"),
                    "away": self.away_d.get("name","Away"),
                    "draw": "Draw", 0: self.home_d.get("name","Home"),
                    1: self.away_d.get("name","Away")}
            draw_text(surf, f"Winner: {wmap.get(winner, str(winner))}", (self.rect_panel.x + 16, status_y), 20, th.text)
        else:
            draw_text(surf, "Status: Running" if self.auto else "Status: Paused",
                      (self.rect_panel.x + 16, status_y), 20, th.subt)

        self._draw_grid(surf)
        self._draw_log(surf)

        if self.btn_turn:   self.btn_turn.draw(surf, th)
        if self.btn_round:  self.btn_round.draw(surf, th)
        if self.btn_auto:   self.btn_auto.draw(surf, th)
        if self.btn_finish: self.btn_finish.draw(surf, th)

    # ---------- grid (auto-scaled cells; offsets for crowded tiles; hide downed) ----------
    def _draw_grid(self, surf: pygame.Surface) -> None:
        rg = self.rect_grid
        gw, gh = _GRID_W, _GRID_H

        scale_w = max(0.1, min(1.0, (rg.w - 12) / (gw * TARGET_CELL_W)))
        scale_h = max(0.1, min(1.0, (rg.h - 12) / (gh * TARGET_CELL_H)))
        s = min(scale_w, scale_h)

        cell_w = max(40, int(TARGET_CELL_W * s))
        cell_h = max(60, int(TARGET_CELL_H * s))

        used_w, used_h = cell_w * gw, cell_h * gh
        ox = rg.x + max(0, (rg.w - used_w) // 2)
        oy = rg.y + max(0, (rg.h - used_h) // 2)

        # alive fighters per tile (hide downed)
        per_tile: DefaultDict[Tuple[int,int], List[Any]] = defaultdict(list)
        for f in self._fighters():
            if not self._fighter_alive(f): continue
            x = int(getattr(f, "x", getattr(f, "tx", 0)))
            y = int(getattr(f, "y", getattr(f, "ty", 0)))
            per_tile[(x,y)].append(f)

        # small visual offsets for up to 4 fighters; engine also prevents stacking now
        def offsets(n: int) -> List[Tuple[float,float]]:
            if n <= 1: return [(0.0, 0.0)]
            if n == 2: return [(-0.22, 0.0), (0.22, 0.0)]
            if n == 3: return [(-0.22, -0.18), (0.22, -0.18), (0.0, 0.22)]
            return [(-0.22, -0.18), (0.22, -0.18), (-0.22, 0.22), (0.22, 0.22)]

        for (x, y), flist in per_tile.items():
            cx = ox + x * cell_w
            cy = oy + y * cell_h
            cell_rect = pygame.Rect(cx, cy, cell_w, cell_h)

            # layout within cell
            name_y = cell_rect.y + max(4, int(cell_h * 0.08))
            bar_y  = name_y + max(14, int(cell_h * 0.16))
            dot_row_y = bar_y + 10

            r = max(8, int(min(cell_w, cell_h) * DOT_RADIUS_F))
            base_cx = cell_rect.centerx
            base_cy = dot_row_y + r

            offs = offsets(len(flist))
            for idx, f in enumerate(flist):
                dx, dy = offs[min(idx, len(offs)-1)]
                dot_cx = int(base_cx + dx * cell_w)
                dot_cy = int(base_cy + dy * cell_h)

                tid = int(getattr(f, "team_id", 0))
                color = self._team_color_for_tid(tid)

                hp, mh = self._fighter_hp(f)
                name_full = str(getattr(f, "name", getattr(f, "pid", "F")))
                name_disp = _short_name(name_full)

                # smaller name as requested
                name_size = 14 if len(flist) <= 2 else 12
                draw_text(surf, name_disp, (dot_cx, name_y), name_size, self.theme.text, align="center")

                # HP bar (centered per dot)
                bar_w = int(min(cell_rect.w * 0.9, max(48, cell_w * (0.78 if len(flist) <= 2 else 0.66))))
                bar_h = 7
                bx = dot_cx - bar_w // 2
                by = bar_y
                pygame.draw.rect(surf, COLOR_HP_BG, pygame.Rect(bx, by, bar_w, bar_h), border_radius=3)
                fill_w = int(bar_w * (hp / mh))
                pygame.draw.rect(surf, COLOR_HP_FILL, pygame.Rect(bx, by, fill_w, bar_h), border_radius=3)

                # dot
                pygame.draw.circle(surf, color, (dot_cx, dot_cy), r)
                pygame.draw.circle(surf, self.theme.panel_border, (dot_cx, dot_cy), r, 1)

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
