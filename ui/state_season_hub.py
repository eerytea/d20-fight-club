from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional, Tuple

# UI kit
try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=6)
            font = pygame.font.SysFont("arial", 18)
            surf = font.render(self.label, True, (255,255,255) if self.enabled else (180,180,180))
            screen.blit(surf, (self.rect.x+8, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(255,255,255), size=20):
        font = pygame.font.SysFont("arial", size)
        surf = font.render(text, True, color)
        surface.blit(surf, (x, y))
    def panel(surface, rect, color=(40,40,40)):
        pygame.draw.rect(surface, color, rect, border_radius=6)

# Screens we link to
try:
    from ui.states.state_match import MatchState
except Exception:
    from ui.state_match import MatchState  # fallback

try:
    from ui.states.state_reputation import ReputationState
except Exception:
    ReputationState = None

# Sim week fallback
def _try_sim_week(career) -> bool:
    # Prefer bound methods on career if available
    for name in ("simulate_week_ai", "simulate_week", "sim_week_ai", "sim_week"):
        fn = getattr(career, name, None)
        if callable(fn):
            try:
                fn()
                return True
            except Exception:
                pass
    # Fallback to module-level
    try:
        from core.sim import simulate_week_ai
        simulate_week_ai(career)
        return True
    except Exception:
        return False

# Robust fixtures reader
def _fixtures_for_week(career, week_index: int) -> List[Tuple[Any, Any]]:
    """Return list of (home_tid, away_tid) for week_index (0-based)."""
    # Common shapes
    fx_by_week = getattr(career, "fixtures_by_week", None) or getattr(career, "rounds", None)
    if isinstance(fx_by_week, list) and 0 <= week_index < len(fx_by_week):
        week = fx_by_week[week_index]
        out = []
        for p in week:
            if isinstance(p, dict):
                a = p.get("home_id") or p.get("home_tid") or p.get("home") or p.get("A")
                b = p.get("away_id") or p.get("away_tid") or p.get("away") or p.get("B")
                out.append((a, b))
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                out.append((p[0], p[1]))
        return out

    # Flat fixtures + each has a week field
    fx = getattr(career, "fixtures", None) or getattr(career, "schedule", None)
    if isinstance(fx, list):
        out = []
        for m in fx:
            w = m.get("week") if isinstance(m, dict) else getattr(m, "week", None)
            if w is None:
                continue
            # weeks might be 1-based
            if int(w) - 1 == week_index or int(w) == week_index:
                if isinstance(m, dict):
                    a = m.get("home_id") or m.get("home_tid") or m.get("home") or m.get("A")
                    b = m.get("away_id") or m.get("away_tid") or m.get("away") or m.get("B")
                else:
                    a = getattr(m, "home_id", getattr(m, "home_tid", getattr(m, "home", getattr(m, "A", None))))
                    b = getattr(m, "away_id", getattr(m, "away_tid", getattr(m, "away", getattr(m, "B", None))))
                out.append((a, b))
        if out:
            return out
    return []

def _current_week_index(career) -> int:
    # prefer explicit week_index if present; else derive from 1-based week
    if hasattr(career, "week_index"):
        try:
            return max(0, int(getattr(career, "week_index")))
        except Exception:
            pass
    try:
        return max(0, int(getattr(career, "week", 1)) - 1)
    except Exception:
        return 0

def _team_name(career, tid) -> str:
    if hasattr(career, "team_name"):
        try:
            return str(career.team_name(tid))
        except Exception:
            pass
    teams = getattr(career, "teams", None)
    if isinstance(teams, list):
        for t in teams:
            if str(t.get("tid", t.get("id"))) == str(tid):
                return t.get("name", f"Team {tid}")
    if isinstance(teams, dict):
        t = teams.get(str(tid)) or teams.get(int(tid)) if str(tid).isdigit() else None
        if t:
            return t.get("name", f"Team {tid}")
    return f"Team {tid}"

class SeasonHubState:
    def __init__(self, app, career, user_tid: Optional[Any] = None):
        self.app = app
        self.career = career
        self.user_tid = user_tid if user_tid is not None else getattr(career, "user_tid", 0)
        self.toast = ""
        self._toast_t = 0.0

        # layout
        self.rc_hdr = Rect(20, 20, 860, 40)
        self.rc_mid = Rect(20, 70, 860, 420)
        self.rc_btns = Rect(20, 500, 860, 60)
        self._build_buttons()

    # ---------------- buttons ----------------

    def _build_buttons(self):
        bx, by, bw, bh, gap = self.rc_btns.x, self.rc_btns.y, 130, 36, 10
        self.btn_play = Button(Rect(bx, by, bw, bh), "Play", self._on_play)
        self.btn_sim = Button(Rect(bx + (bw+gap), by, bw, bh), "Sim Week", self._on_sim_week)
        self.btn_sched = Button(Rect(bx + 2*(bw+gap), by, bw, bh), "Schedule", self._on_schedule)
        self.btn_table = Button(Rect(bx + 3*(bw+gap), by, bw, bh), "Table", self._on_table)
        self.btn_roster = Button(Rect(bx + 4*(bw+gap), by, bw, bh), "Roster", self._on_roster)
        if ReputationState:
            self.btn_rep = Button(Rect(bx + 5*(bw+gap), by, bw, bh), "Reputation", self._on_reputation)
            self._buttons = [self.btn_play, self.btn_sim, self.btn_sched, self.btn_table, self.btn_roster, self.btn_rep]
        else:
            self._buttons = [self.btn_play, self.btn_sim, self.btn_sched, self.btn_table, self.btn_roster]

    # ---------------- events -----------------

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                if hasattr(b, "handle"):
                    b.handle(ev)
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.app.pop_state()

    def update(self, dt):
        self._toast_t = max(0.0, self._toast_t - dt)
        # enable/disable Play depending on fixture present
        wk = _current_week_index(self.career)
        pairs = _fixtures_for_week(self.career, wk)
        has_user = any(str(a) == str(self.user_tid) or str(b) == str(self.user_tid) for a, b in pairs)
        self.btn_play.enabled = has_user

    def draw(self, screen):
        screen.fill((12, 12, 16))
        panel(screen, self.rc_hdr, color=(30,30,38))
        # header
        user_name = _team_name(self.career, self.user_tid)
        wk = _current_week_index(self.career)
        draw_text(screen, f"Your Team: {user_name}    Week {wk+1}", self.rc_hdr.x+8, self.rc_hdr.y+8, (235,235,240), 22)

        # mid panel: this week's fixtures
        panel(screen, self.rc_mid, color=(24,24,28))
        draw_text(screen, "This Week's Matchups", self.rc_mid.x+8, self.rc_mid.y+8, (210,210,220), 18)
        pairs = _fixtures_for_week(self.career, wk)
        y = self.rc_mid.y + 36
        for (a, b) in pairs[:18]:
            an = _team_name(self.career, a)
            bn = _team_name(self.career, b)
            draw_text(screen, f"{an}  vs  {bn}", self.rc_mid.x+16, y, (220,220,230), 18)
            y += 24

        # buttons
        for b in self._buttons:
            if hasattr(b, "draw"):
                b.draw(screen)

        # toast
        if self._toast_t > 0:
            draw_text(screen, self.toast, self.rc_btns.x, self.rc_btns.y - 24, (255,230,120), 18)

    # --------------- actions ---------------

    def _on_play(self):
        # find user fixture
        wk = _current_week_index(self.career)
        pairs = _fixtures_for_week(self.career, wk)
        f = None
        for a, b in pairs:
            if str(a) == str(self.user_tid) or str(b) == str(self.user_tid):
                f = {"home_tid": a, "away_tid": b, "comp_kind": "league"}
                break
        if not f:
            self._toast("No user match this week.")
            return

        # build fighters list shape your engine expects
        fighters = self._fighters_for(self.career, f["home_tid"], f["away_tid"])

        def on_finish(result: Dict[str, Any]):
            # Persist the result if your career exposes a method; otherwise ignore gracefully
            saved = False
            for name in ("record_result", "save_match_result", "apply_result"):
                fn = getattr(self.career, name, None)
                if callable(fn):
                    try:
                        fn(result)
                        saved = True
                        break
                    except Exception:
                        pass
            # Advance week if your career has it
            for name in ("advance_week", "next_week"):
                fn = getattr(self.career, name, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception:
                        pass
            self._toast("Result saved and week advanced." if saved else "Match finished.")

        ms = MatchState(self.app, self.career, f, fighters, grid_w=11, grid_h=11, seed=getattr(self.career, "seed", 12345), on_finish=on_finish)
        self.app.push_state(ms)

    def _fighters_for(self, career, home_tid, away_tid) -> List[Dict]:
        # Expect career.teams list with 'fighters' or 'players'
        def roster_of(tid):
            teams = getattr(career, "teams", [])
            for t in teams:
                if str(t.get("tid", t.get("id"))) == str(tid):
                    roster = t.get("fighters") or t.get("players") or []
                    # Normalize team_id
                    out = []
                    for i, p in enumerate(roster):
                        d = dict(p) if isinstance(p, dict) else p.__dict__.copy()
                        d.setdefault("pid", d.get("id", i))
                        d["team_id"] = 0 if str(tid) == str(home_tid) else 1
                        d.setdefault("name", d.get("n", f"F{i}"))
                        d.setdefault("hp", d.get("hp", d.get("HP", 10)))
                        d.setdefault("max_hp", d.get("max_hp", d.get("HP_max", d.get("hp", 10))))
                        d.setdefault("ac", d.get("ac", d.get("AC", 10)))
                        d.setdefault("alive", d.get("alive", True))
                        out.append(d)
                    return out
            return []
        return roster_of(home_tid) + roster_of(away_tid)

    def _on_sim_week(self):
        ok = _try_sim_week(self.career)
        self._toast("Week simulated." if ok else "Sim failed.")

    def _on_schedule(self):
        # if you have a schedule screen, push it; else toast
        self._toast("Schedule coming soon (adapter hook).")

    def _on_table(self):
        self._toast("Table screen available in your build (open from menu).")

    def _on_roster(self):
        self._toast("Roster screen coming soon (adapter hook).")

    def _on_reputation(self):
        if ReputationState:
            self.app.push_state(ReputationState(self.app, self.career))

    def _toast(self, msg: str, secs: float = 2.0):
        self.toast = msg
        self._toast_t = secs
