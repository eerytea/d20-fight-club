# ui/state_match.py (framework-aligned)
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, draw_text, get_font

# Grid dims come from core.sim (shared with exhibition/schedule)
try:
    from core.sim import GRID_W, GRID_H
except Exception:
    GRID_W, GRID_H = 12, 8

# Engine public API (lazy exports in engine/__init__.py)
from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles


def _norm_tid(x: Any) -> int:
    return 1 if x in (1, "1", True) else 0


def _short_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "?"
    parts = name.split()
    if len(parts) == 1:
        return parts[0][:12]
    first = (parts[0][0] + ".") if parts[0] else ""
    last = parts[-1]
    s = f"{first} {last}"
    return s if len(s) <= 14 else s[:14]


def _fmt_event(d: Dict[str, Any]) -> Optional[str]:
    t = d.get("type")
    if t == "round":
        return f"— Round {d.get('round', '?')} —"
    if t == "move":
        who = d.get("name", "Unknown")
        to = d.get("to", ("?", "?"))
        return f"{who} moves to {to}."
    if t == "blocked":
        who = d.get("name", "Unknown")
        to = d.get("to", ("?", "?"))
        by = d.get("by", "someone")
        return f"{who} tries to move to {to} but is blocked by {by}."
    if t == "hit":
        return f"{d.get('name','?')} hits {d.get('target','?')} for {d.get('dmg','?')}."
    if t == "miss":
        return f"{d.get('name','?')} misses {d.get('target','?')}."
    if t == "down":
        return f"{d.get('name','?')} is down!"
    if t == "end":
        return "— End of match —"
    if t == "note":
        return f"[note] {d.get('msg','')}"
    return None


def _wrap_lines(text: str, font, max_w: int) -> List[str]:
    if not text:
        return [""]
    words = text.split(" ")
    out: List[str] = []
    cur = ""
    for w in words:
        trial = w if not cur else f"{cur} {w}"
        if font.get_rect(trial).width <= max_w or not cur:
            cur = trial
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def _choose_events(obj: Any) -> List[Dict[str, Any]]:
    # engine preferred
    for attr in ("events_typed", "typed_events", "events", "_events"):
        if hasattr(obj, attr):
            ev = getattr(obj, attr)
            if isinstance(ev, list):
                return ev
    # dict wrapper fallback
    if isinstance(obj, dict):
        for k in ("events_typed", "typed_events", "events", "_events"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
        obj["typed_events"] = []
        return obj["typed_events"]
    # last resort: attach to object
    try:
        setattr(obj, "typed_events", [])
        return getattr(obj, "typed_events")
    except Exception:
        return []


class MatchState(BaseState):
    """
    Season Hub calls: MatchState(app, tH_dict, tA_dict)
    This state also accepts: MatchState(app, combat_obj [, None])
    """

    def __init__(self, app, home_or_engine: Any, away: Any | None = None, *, on_finish=None, auto: bool = False):
        self.app = app
        self.theme = Theme()

        self._layout_built = False
        self._grid_rect = pygame.Rect(0, 0, 0, 0)
        self._side_rect = pygame.Rect(0, 0, 0, 0)
        self._btn_rect = pygame.Rect(0, 0, 0, 0)

        self.btn_next_turn: Button | None = None
        self.btn_next_round: Button | None = None
        self.btn_auto: Button | None = None
        self.btn_finish: Button | None = None

        self.on_finish = on_finish
        self.auto = bool(auto)
        self._auto_timer = 0.0
        self._auto_period = 0.20

        # Create or accept engine
        if isinstance(home_or_engine, TBCombat):
            self.engine = home_or_engine
        elif away is None and isinstance(home_or_engine, dict) and "combat" in home_or_engine:
            self.engine = home_or_engine["combat"]
        else:
            self.engine = self._build_engine_from_teams(home_or_engine, away)

        # Event list
        self.events = _choose_events(self.engine)

        # Fighters reference (for draw)
        self._fighters = getattr(self.engine, "fighters", [])

        # Log
        self.log_lines: List[str] = []
        self._ev_idx = 0
        self._log_line_h = 22  # set after fonts built
        self.log_scroll = 0

    # --- engine construction ---
    def _build_engine_from_teams(self, home: dict, away: dict) -> TBCombat:
        # Convert team dicts → Team objects and Fighter objects
        nameH = str(home.get("name", "Home"))
        nameA = str(away.get("name", "Away"))
        colH = tuple(home.get("color", (220, 64, 64)))
        colA = tuple(away.get("color", (64, 110, 220)))

        teamA = Team(id=int(home.get("tid", 0)), name=nameH, color=colH)  # type: ignore[arg-type]
        teamB = Team(id=int(away.get("tid", 1)), name=nameA, color=colA)  # type: ignore[arg-type]

        fH = [fighter_from_dict({**fd}) for fd in home.get("fighters", [])]
        fA = [fighter_from_dict({**fd}) for fd in away.get("fighters", [])]
        for f in fH:
            setattr(f, "team_id", 0)
        for f in fA:
            setattr(f, "team_id", 1)
        fighters = fH + fA

        # Lay out desired tiles; engine will fall back from tx/ty → x/y if x/y missing
        layout_teams_tiles(fighters, GRID_W, GRID_H)

        # Seed: attempt to derive from names for stability
        seed = (hash(nameH) ^ (hash(nameA) << 1)) & 0xFFFFFFFF

        return TBCombat(teamA, teamB, fighters, GRID_W, GRID_H, seed=seed)

    # --- state lifecycle ---
    def enter(self) -> None:
        self._build_layout()
        # Ingest any preexisting round marker
        self._ingest_new_events(initial=True)

    def handle(self, event) -> None:
        if not self._layout_built:
            return
        for b in (self.btn_next_turn, self.btn_next_round, self.btn_auto, self.btn_finish):
            if b is not None:
                b.handle(event)
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._side_rect.collidepoint(mx, my):
                self.log_scroll = max(0, self.log_scroll - event.y * (self._log_line_h * 3))

    def update(self, dt: float) -> None:
        if not self._layout_built:
            self._build_layout()

        # button hovers
        mx, my = pygame.mouse.get_pos()
        for b in (self.btn_next_turn, self.btn_next_round, self.btn_auto, self.btn_finish):
            if b is not None:
                b.update((mx, my))

        self._ingest_new_events()

        if self.auto and not self._ended():
            self._auto_timer += dt
            while self._auto_timer >= self._auto_period and not self._ended():
                self._auto_timer -= self._auto_period
                self._step_once_and_ingest()

    def draw(self, surf) -> None:
        if not self._layout_built:
            self._build_layout()
        surf.fill(self.theme.bg)

        # panels
        draw_panel(surf, self._grid_rect, self.theme)
        draw_panel(surf, self._side_rect, self.theme)
        draw_panel(surf, self._btn_rect, self.theme)

        # fighters
        for f in self._fighters:
            alive = getattr(f, "alive", True)
            hp = getattr(f, "hp", 0)
            if not alive or hp <= 0:
                continue
            tid = _norm_tid(getattr(f, "team_id", 0))
            x = int(getattr(f, "x", 0))
            y = int(getattr(f, "y", 0))
            name = getattr(f, "name", "?")
            max_hp = getattr(f, "max_hp", hp)
            self._draw_fighter(surf, x, y, name, tid, hp, max_hp)

        # log
        self._draw_log(surf)

        # buttons
        for b in (self.btn_next_turn, self.btn_next_round, self.btn_auto, self.btn_finish):
            if b is not None:
                b.draw(surf, self.theme)

    # --- UI layout & draw helpers ---
    def _build_layout(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 12
        sidebar_w = 360
        btn_h = 64

        self._grid_rect = pygame.Rect(pad, pad, W - sidebar_w - pad * 3, H - btn_h - pad * 2)
        self._side_rect = pygame.Rect(self._grid_rect.right + pad, pad, sidebar_w, self._grid_rect.height)
        self._btn_rect = pygame.Rect(pad, self._grid_rect.bottom + pad, W - pad * 2, btn_h)

        # grid cell sizes
        self._cell_w = max(24, self._grid_rect.w // int(getattr(self.engine, "GRID_W", GRID_W)))
        self._cell_h = max(24, self._grid_rect.h // int(getattr(self.engine, "GRID_H", GRID_H)))

        # fonts
        tile_h = self._cell_h
        self._font_name = get_font(max(12, min(int(tile_h * 0.28), 28)))
        self._font_log = get_font(18)
        self._log_line_h = self._font_log.get_sized_height()

        # buttons
        bw = 160
        gap = 10
        x = self._btn_rect.x
        y = self._btn_rect.y
        self.btn_next_turn = Button(pygame.Rect(x, y, bw, self._btn_rect.h), "Next Turn", self._action_next_turn)
        self.btn_next_round = Button(pygame.Rect(x + (bw + gap), y, bw, self._btn_rect.h), "Next Round", self._action_next_round)
        self.btn_auto = Button(pygame.Rect(x + 2 * (bw + gap), y, bw, self._btn_rect.h), "Auto: OFF", self._toggle_auto)
        self.btn_finish = Button(pygame.Rect(self._btn_rect.right - bw, y, bw, self._btn_rect.h), "Finish", self._finish)

        self._layout_built = True

    def _cell_rect(self, gx: int, gy: int) -> pygame.Rect:
        return pygame.Rect(
            self._grid_rect.x + gx * self._cell_w,
            self._grid_rect.y + gy * self._cell_h,
            self._cell_w,
            self._cell_h,
        )

    def _draw_fighter(self, surf, gx: int, gy: int, name: str, tid: int, hp: int, max_hp: int):
        r = self._cell_rect(gx, gy)
        # dot
        color = (220, 64, 64) if tid == 0 else (64, 110, 220)
        dot = min(r.w, r.h) // 4 + 4
        pygame.draw.circle(surf, color, (r.centerx, r.top + dot + 4), dot)

        # name
        nm = _short_name(name)
        txt_rect = self._font_name.get_rect(nm)
        txt_rect.midtop = (r.centerx, r.top + dot * 2 + 6)
        self._font_name.render_to(surf, txt_rect.topleft, nm, self.theme.text)

        # HP bar
        frac = 0.0 if max_hp <= 0 else max(0.0, min(1.0, hp / float(max_hp)))
        bar_w = int(r.w * 0.9)
        bar_h = max(6, int(r.h * 0.12))
        bar_x = r.centerx - bar_w // 2
        bar_y = txt_rect.bottom + 4

        pygame.draw.rect(surf, (40, 40, 46), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = max(0, int(bar_w * frac))
        fill_col = (70, 200, 120) if frac >= 0.5 else (220, 80, 80)
        pygame.draw.rect(surf, fill_col, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

    def _draw_log(self, surf):
        pad = 10
        inner = self._side_rect.inflate(-2 * pad, -2 * pad)
        y = inner.y - self.log_scroll
        # clip
        clip = surf.get_clip()
        surf.set_clip(inner)
        # draw lines
        for line in self.log_lines:
            self._font_log.render_to(surf, (inner.x, y), line, self.theme.text)
            y += self._log_line_h
        surf.set_clip(clip)

    def _append_log(self, s: str):
        pad = 10
        inner_w = self._side_rect.w - 2 * pad
        for line in _wrap_lines(s, self._font_log, inner_w):
            self.log_lines.append(line)
        total_px = len(self.log_lines) * self._log_line_h
        visible_px = self._side_rect.h - 2 * pad
        self.log_scroll = max(0, total_px - visible_px)

    # --- events/stepping ---
    def _ingest_new_events(self, initial: bool = False):
        while self._ev_idx < len(self.events):
            ev = self.events[self._ev_idx]
            self._ev_idx += 1
            if isinstance(ev, dict):
                msg = _fmt_event(ev)
                if msg:
                    self._append_log(msg)
        if initial and not any(isinstance(e, dict) and e.get("type") == "round" for e in self.events):
            self._append_log("— Round 1 —")

    def _step_once_and_ingest(self):
        step = getattr(self.engine, "step_action", None)
        if callable(step) and not self._ended():
            before = len(self.events)
            step()
            self._ingest_new_events()
            if len(self.events) == before:
                self._append_log("[warn] step_action produced no events.")
        else:
            self._append_log("[note] No engine attached to step.")

    def _action_next_turn(self):
        if self._ended():
            return
        base_len = len(self.events)
        self._step_once_and_ingest()
        first_name = None
        for ev in self.events[base_len:]:
            if isinstance(ev, dict) and "name" in ev and ev.get("type") not in ("down", "end", "round", "note"):
                first_name = ev["name"]
                break
        if first_name is None:
            return
        while not self._ended():
            pre_len = len(self.events)
            self._step_once_and_ingest()
            new_chunk = self.events[pre_len:]
            if any(isinstance(ev, dict) and ev.get("type") in ("round", "end") for ev in new_chunk):
                break
            actor_changed = False
            for ev in new_chunk:
                if isinstance(ev, dict):
                    nm = ev.get("name")
                    if nm and nm != first_name and ev.get("type") not in ("down", "note"):
                        actor_changed = True
                        break
            if actor_changed or not new_chunk:
                break

    def _action_next_round(self):
        if self._ended():
            return
        start_round = self._current_round()
        while not self._ended():
            pre_len = len(self.events)
            self._step_once_and_ingest()
            new_chunk = self.events[pre_len:]
            if any(isinstance(ev, dict) and ev.get("type") in ("round", "end") for ev in new_chunk):
                break
            if self._current_round() != start_round:
                break

    def _toggle_auto(self):
        self.auto = not self.auto
        if self.btn_auto:
            self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"

    def _finish(self):
        if callable(self.on_finish):
            try:
                self.on_finish(self)
            except Exception:
                pass
        else:
            try:
                self.app.pop_state()
            except Exception:
                pass

    def _ended(self) -> bool:
        if hasattr(self.engine, "winner") and getattr(self.engine, "winner") is not None:
            return True
        return any(isinstance(ev, dict) and ev.get("type") == "end" for ev in self.events)

    def _current_round(self) -> int:
        for ev in reversed(self.events):
            if isinstance(ev, dict) and ev.get("type") == "round":
                try:
                    return int(ev.get("round", 1))
                except Exception:
                    return 1
        return 1


# Back-compat: some code may also import create() or State_Match
def create(app, *args, **kwargs) -> MatchState:
    return MatchState(app, *args, **kwargs)

State_Match = MatchState
__all__ = ["MatchState", "create", "State_Match"]
