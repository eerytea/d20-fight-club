# ui/state_match.py
# Match Viewer state (pygame)
# - Watches a TBCombat instance and renders live events.
# - Buttons: Next Turn, Next Round, Auto, Finish.
# - Event stream priority: events_typed > typed_events > events > _events.
from __future__ import annotations
import pygame
from typing import Any, Dict, List, Tuple, Optional

# --- light dependencies on your UI kit; fall back if not present
try:
    from ui.uiutil import Theme, get_font  # type: ignore
except Exception:  # fallback stubs
    class Theme:
        BG = (18, 18, 22)
        FG = (235, 235, 235)
        ACCENT = (120, 170, 255)
        RED = (220, 64, 64)
        BLUE = (64, 110, 220)
        MUTED = (150, 150, 160)
        PANEL = (28, 28, 34)
        BTN_BG = (38, 38, 46)
        BTN_BG_H = (48, 48, 56)
        BTN_FG = (230, 230, 235)
        HP_GOOD = (70, 200, 120)
        HP_BAD = (220, 80, 80)

    def get_font(px: int) -> pygame.font.Font:
        pygame.font.init()
        return pygame.font.SysFont(None, px)

# -------- utility helpers --------

def _choose_event_source(combat: Any) -> List[Dict[str, Any]]:
    # Accept several attribute spellings
    for attr in ("events_typed", "typed_events", "events", "_events"):
        if hasattr(combat, attr):
            ev = getattr(combat, attr)
            if isinstance(ev, list):
                return ev
    # final fallback: attach one
    combat.typed_events = []
    return combat.typed_events

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
    # unknown: don't crash viewer
    return None

def _wrap_lines(text: str, font: pygame.font.Font, max_w: int) -> List[str]:
    if not text:
        return [""]
    words = text.split(" ")
    out: List[str] = []
    cur = ""
    for w in words:
        trial = w if not cur else f"{cur} {w}"
        if font.size(trial)[0] <= max_w or not cur:
            cur = trial
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out

def _norm_tid(x: Any) -> int:
    return 1 if x in (1, "1", True) else 0

# -------- simple button --------

class Button:
    def __init__(self, rect: pygame.Rect, label: str, on_click):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self._hover = False

    def handle_event(self, e: pygame.event.Event) -> None:
        if e.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos):
                self.on_click()

    def draw(self, surf: pygame.Surface, theme: Theme):
        bg = theme.BTN_BG_H if self._hover else theme.BTN_BG
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        f = get_font(20)
        txt = f.render(self.label, True, theme.BTN_FG)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

# -------- match state --------

class State_Match:
    """
    Public surface:
      - enter(app, **kwargs)  (optional)
      - handle_event(e)
      - update(dt)
      - draw(screen)
    Construct with (app, combat, on_finish=None, user_tid=0, auto=False)
    """
    def __init__(self, app, combat: Any, on_finish=None, user_tid: int = 0, auto: bool = False):
        self.app = app
        self.combat = combat
        self.events = _choose_event_source(combat)
        self.on_finish = on_finish
        # normalize team IDs defensively
        for f in getattr(self.combat, "fighters", []):
            if hasattr(f, "team_id"):
                f.team_id = _norm_tid(getattr(f, "team_id", 0))
            elif isinstance(f, dict):
                f["team_id"] = _norm_tid(f.get("team_id", 0))

        # layout
        self.W = getattr(app, "width", 1280)
        self.H = getattr(app, "height", 720)
        self.theme = getattr(app, "theme", Theme())

        self.sidebar_w = 360
        self.bottom_h = 64
        self.pad = 12

        # derived rects
        self.grid_rect = pygame.Rect(self.pad, self.pad,
                                     self.W - self.sidebar_w - 3*self.pad,
                                     self.H - self.bottom_h - 2*self.pad)
        self.sidebar_rect = pygame.Rect(self.grid_rect.right + self.pad, self.pad,
                                        self.sidebar_w, self.grid_rect.height)
        self.buttons_rect = pygame.Rect(self.pad, self.grid_rect.bottom + self.pad,
                                        self.W - 2*self.pad, self.bottom_h)

        # grid size from combat
        self.GW = int(getattr(self.combat, "GRID_W", 8))
        self.GH = int(getattr(self.combat, "GRID_H", 6))

        # cell math (no gridlines drawn)
        self.cell_w = max(24, self.grid_rect.width // self.GW)
        self.cell_h = max(24, self.grid_rect.height // self.GH)

        # fonts scale to tile height
        self._recalc_fonts()

        # colors
        self.COLOR_BY_TID = {
            0: getattr(self.theme, "RED", (220, 64, 64)),
            1: getattr(self.theme, "BLUE", (64, 110, 220)),
        }
        self.user_tid = _norm_tid(user_tid)

        # log + scroll
        self.log_lines: List[str] = []
        self.log_scroll = 0  # pixels from top
        self._log_line_h = self.font_log.get_linesize()
        self._ev_idx = 0

        # buttons
        bw = 160
        gap = 10
        bx = self.buttons_rect.x
        by = self.buttons_rect.y
        self.btn_next_turn = Button(pygame.Rect(bx, by, bw, self.bottom_h), "Next Turn", self._action_next_turn)
        self.btn_next_round = Button(pygame.Rect(bx + (bw + gap), by, bw, self.bottom_h), "Next Round", self._action_next_round)
        self.btn_auto = Button(pygame.Rect(bx + 2*(bw + gap), by, bw, self.bottom_h), "Auto: OFF", self._toggle_auto)
        self.btn_finish = Button(pygame.Rect(self.buttons_rect.right - bw, by, bw, self.bottom_h), "Finish", self._finish)

        self.auto = bool(auto)
        self._auto_timer = 0.0
        self._auto_period = 0.20  # seconds per step when Auto

        # start banner if not already present
        if not any(ev.get("type") == "round" for ev in self.events):
            self._append_log("— Round 1 —")

    # ------- state lifecycle (optional) -------
    def enter(self, **kwargs):  # called by app if present
        pass

    # ------- input -------
    def handle_event(self, e: pygame.event.Event) -> None:
        # buttons
        self.btn_next_turn.handle_event(e)
        self.btn_next_round.handle_event(e)
        self.btn_auto.handle_event(e)
        self.btn_finish.handle_event(e)

        # mouse wheel scroll on sidebar
        if e.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.sidebar_rect.collidepoint(mx, my):
                self.log_scroll -= e.y * (self._log_line_h * 3)
                self.log_scroll = max(0, self.log_scroll)

        # keyboard shortcuts
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._finish()
            elif e.key == pygame.K_n:
                self._action_next_turn()
            elif e.key == pygame.K_r:
                self._action_next_round()
            elif e.key == pygame.K_a:
                self._toggle_auto()

    # ------- update/draw -------
    def update(self, dt: float) -> None:
        # bring in any engine events that appeared since last frame (e.g., if engine pre-simmed)
        self._ingest_new_events()

        if self.auto and not self._ended():
            self._auto_timer += dt
            while self._auto_timer >= self._auto_period and not self._ended():
                self._auto_timer -= self._auto_period
                self._step_once_and_ingest()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(self.theme.BG)

        # grid area (no gridlines)
        pygame.draw.rect(screen, self.theme.PANEL, self.grid_rect, border_radius=12)

        # draw fighters
        for f in getattr(self.combat, "fighters", []):
            alive = getattr(f, "alive", True) if not isinstance(f, dict) else f.get("alive", True)
            hp = getattr(f, "hp", 0) if not isinstance(f, dict) else f.get("hp", 0)
            if not alive or hp <= 0:
                continue
            tid = _norm_tid(getattr(f, "team_id", 0) if not isinstance(f, dict) else f.get("team_id", 0))
            x = getattr(f, "x", 0) if not isinstance(f, dict) else f.get("x", 0)
            y = getattr(f, "y", 0) if not isinstance(f, dict) else f.get("y", 0)
            name = getattr(f, "name", "?") if not isinstance(f, dict) else f.get("name", "?")
            self._draw_fighter(screen, x, y, name, tid, hp, getattr(f, "max_hp", hp) if not isinstance(f, dict) else f.get("max_hp", hp))

        # sidebar log
        self._draw_log(screen)

        # buttons
        self.btn_next_turn.draw(screen, self.theme)
        self.btn_next_round.draw(screen, self.theme)
        self.btn_auto.draw(screen, self.theme)
        self.btn_finish.draw(screen, self.theme)

    # ------- internal helpers -------

    def _recalc_fonts(self):
        tile_h = self.cell_h
        name_px = max(12, min(int(tile_h * 0.28), 28))
        hp_px = max(10, min(int(tile_h * 0.22), 24))
        log_px = 18
        self.font_name = get_font(name_px)
        self.font_hp = get_font(hp_px)
        self.font_log = get_font(log_px)

    def _cell_rect(self, gx: int, gy: int) -> pygame.Rect:
        x = self.grid_rect.x + gx * self.cell_w
        y = self.grid_rect.y + gy * self.cell_h
        return pygame.Rect(x, y, self.cell_w, self.cell_h)

    def _draw_fighter(self, screen: pygame.Surface, gx: int, gy: int, name: str, tid: int, hp: int, max_hp: int):
        r = self._cell_rect(gx, gy)
        # dot
        color = self.COLOR_BY_TID.get(tid, self.theme.ACCENT)
        dot = min(r.width, r.height) // 4 + 4
        pygame.draw.circle(screen, color, (r.centerx, r.top + dot + 4), dot)

        # name
        nm = _short_name(name)
        txt = self.font_name.render(nm, True, self.theme.FG)
        name_rect = txt.get_rect(midtop=(r.centerx, r.top + dot*2 + 6))
        screen.blit(txt, name_rect)

        # HP bar (under name)
        frac = 0.0 if max_hp <= 0 else max(0.0, min(1.0, hp / float(max_hp)))
        bar_w = int(r.width * 0.9)
        bar_h = max(6, int(r.height * 0.12))
        bar_x = r.centerx - bar_w // 2
        bar_y = name_rect.bottom + 4
        # background
        pygame.draw.rect(screen, (40, 40, 46), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        # fill
        fill_w = max(0, int(bar_w * frac))
        fill_col = self.theme.HP_GOOD if frac >= 0.5 else self.theme.HP_BAD
        pygame.draw.rect(screen, fill_col, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

    def _draw_log(self, screen: pygame.Surface):
        pygame.draw.rect(screen, self.theme.PANEL, self.sidebar_rect, border_radius=12)
        pad = 10
        inner = self.sidebar_rect.inflate(-2*pad, -2*pad)
        y = inner.y - self.log_scroll

        # draw lines
        for line in self.log_lines:
            surf = self.font_log.render(line, True, self.theme.FG)
            screen.blit(surf, (inner.x, y))
            y += self._log_line_h

        # soft edge fade (optional)
        # top
        top_fade = pygame.Surface((inner.width, min(30, inner.height)), pygame.SRCALPHA)
        top_fade.fill((0, 0, 0, 90))
        screen.blit(top_fade, (inner.x, inner.y))
        # bottom
        bot_fade = pygame.Surface((inner.width, min(30, inner.height)), pygame.SRCALPHA)
        bot_fade.fill((0, 0, 0, 90))
        screen.blit(bot_fade, (inner.x, inner.bottom - bot_fade.get_height()))

        # clip to sidebar
        clip_old = screen.get_clip()
        screen.set_clip(inner)
        # (already drawn within bounds)
        screen.set_clip(clip_old)

    def _append_log(self, s: str):
        # wrap to sidebar width
        pad = 10
        inner_w = self.sidebar_rect.width - 2*pad
        for line in _wrap_lines(s, self.font_log, inner_w):
            self.log_lines.append(line)
        # auto-scroll to bottom on new lines
        total_px = len(self.log_lines) * self._log_line_h
        visible_px = self.sidebar_rect.height - 2*pad
        self.log_scroll = max(0, total_px - visible_px)

    # ---- event ingestion / stepping ----

    def _ingest_new_events(self):
        # read any new events from combat.events*
        while self._ev_idx < len(self.events):
            ev = self.events[self._ev_idx]
            self._ev_idx += 1
            msg = _fmt_event(ev)
            if msg:
                self._append_log(msg)

    def _step_once_and_ingest(self):
        # perform exactly one engine step_action() and ingest its events
        step = getattr(self.combat, "step_action", None)
        if callable(step) and not self._ended():
            before = len(self.events)
            step()
            # pull new events
            self._ingest_new_events()
            # safety: if engine emitted nothing, avoid tight loop in Auto
            if len(self.events) == before:
                # give viewer *something* to hold onto
                self._append_log("[warn] step_action produced no events.")

    def _action_next_turn(self):
        if self._ended():
            return
        # first step
        base_len = len(self.events)
        self._step_once_and_ingest()
        # try to continue while the same actor is acting (heuristic by 'name' fields)
        first_name = None
        for ev in self.events[base_len:]:
            if "name" in ev and ev.get("type") not in ("down", "end", "round", "note"):
                first_name = ev["name"]
                break
        if first_name is None:
            return
        # keep stepping while actor stays the same and no round/end occurs
        while not self._ended():
            pre_len = len(self.events)
            self._step_once_and_ingest()
            new_chunk = self.events[pre_len:]
            if any(ev.get("type") in ("round", "end") for ev in new_chunk):
                break
            actor_changed = False
            for ev in new_chunk:
                nm = ev.get("name")
                if nm and nm != first_name and ev.get("type") not in ("down", "note"):
                    actor_changed = True
                    break
            if actor_changed or not new_chunk:
                break

    def _action_next_round(self):
        if self._ended():
            return
        # advance until we observe a 'round' event or the match ends
        start_round = self._current_round()
        while not self._ended():
            pre_len = len(self.events)
            self._step_once_and_ingest()
            # if new events contain round or end, stop
            new_chunk = self.events[pre_len:]
            if any(ev.get("type") in ("round", "end") for ev in new_chunk):
                break
            # safety if engine stalled
            if self._current_round() != start_round:
                break

    def _toggle_auto(self):
        self.auto = not self.auto
        self.btn_auto.label = f"Auto: {'ON' if self.auto else 'OFF'}"

    def _finish(self):
        # Prefer callback; else try app.pop_state(); else no-op
        if callable(self.on_finish):
            try:
                self.on_finish(self)
            except Exception:
                pass
        else:
            pop = getattr(self.app, "pop_state", None)
            if callable(pop):
                try:
                    pop()
                except Exception:
                    pass

    def _ended(self) -> bool:
        return bool(getattr(self.combat, "winner", None)) or any(ev.get("type") == "end" for ev in self.events)

    def _current_round(self) -> int:
        # scan backwards for last round marker
        for ev in reversed(self.events):
            if ev.get("type") == "round":
                return int(ev.get("round", 1))
        return 1

# convenience: factory
def create(app, combat, on_finish=None, user_tid: int = 0, auto: bool = False) -> State_Match:
    return State_Match(app, combat, on_finish=on_finish, user_tid=user_tid, auto=auto)
