# ui/state_season_hub.py — Season Hub with visible weekly matchups + auto-fitting button row
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, draw_text, get_font


# ---------- helpers ---------------------------------------------------------

def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _team_name_map(career) -> Dict[int, str]:
    m: Dict[int, str] = {}
    for t in getattr(career, "teams", []) or []:
        tid = int(_get(t, "tid", -1))
        nm  = str(_get(t, "name", f"Team {tid}"))
        if tid >= 0:
            m[tid] = nm
    return m

def _fixtures_for_week(career, week_idx: int) -> List[Tuple[int, int]]:
    """Return a list of (home_tid, away_tid) pairs for the given week."""
    # 1) explicit helper
    if hasattr(career, "fixtures_for_week"):
        try:
            out = career.fixtures_for_week(week_idx)
            if out:
                return [(int(a), int(b)) for (a, b) in out]
        except Exception:
            pass

    # 2) schedule attribute (list/dict/tuples or dicts)
    sched = getattr(career, "schedule", None)
    wk = []
    if isinstance(sched, list):
        wk = sched[week_idx] if 0 <= week_idx < len(sched) else []
    elif isinstance(sched, dict):
        wk = sched.get(week_idx, [])

    pairs: List[Tuple[int, int]] = []
    for f in wk or []:
        if isinstance(f, dict):
            a = f.get("home_tid", f.get("home", f.get("a")))
            b = f.get("away_tid", f.get("away", f.get("b")))
        else:
            try:
                a, b = f
            except Exception:
                a = b = None
        if a is not None and b is not None:
            pairs.append((int(a), int(b)))
    return pairs

def _find_user_fixture(pairs: List[Tuple[int, int]], user_tid: int) -> Optional[Tuple[int, int]]:
    for a, b in pairs:
        if a == user_tid or b == user_tid:
            return (a, b)
    return None

def _extract_result_numbers(result: Any, home_tid: int, away_tid: int) -> Tuple[int, int, Optional[int]]:
    """Pull (kills_home, kills_away, winner_tid) from a result-ish object."""
    kh = _get(result, "kills_home", _get(result, "k_home", _get(result, "home_kills", _get(result, "A", 0))))
    ka = _get(result, "kills_away", _get(result, "k_away", _get(result, "away_kills", _get(result, "B", 0))))
    win_tid = _get(result, "winner_tid", _get(result, "winner", None))

    try: kh = int(kh)
    except Exception: kh = 0
    try: ka = int(ka)
    except Exception: ka = 0
    try:
        win_tid = int(win_tid) if win_tid is not None else None
    except Exception:
        win_tid = None

    if win_tid is None and kh != ka:
        win_tid = home_tid if kh > ka else away_tid
    return kh, ka, win_tid


# ---------- state -----------------------------------------------------------

class SeasonHubState(BaseState):
    """
    Header: "Your Team: <name>" (left) + "Week N" (right)
    Panel:  "This Week's Matchups" list (clipped, left-aligned)
    Buttons: Play / Sim Week / Schedule / Table / Roster / Back (auto size to fit)
    """

    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)
        self.rect_buttons = pygame.Rect(0, 0, 0, 0)

        self.btn_play: Button | None = None
        self.btn_sim : Button | None = None
        self.btn_sched: Button | None = None
        self.btn_table: Button | None = None
        self.btn_roster: Button | None = None
        self.btn_back: Button | None = None

        self.f_title = get_font(42)
        self.f_h2    = get_font(34)
        self.f_row   = get_font(28)
        self.f_msg   = get_font(22)

        self._last_saved_msg: Optional[str] = None
        self._msg_timer: float = 0.0

    # lifecycle
    def enter(self) -> None:
        self._layout()

    def _layout(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 80

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2,
                                        H - (toolbar_h + pad * 4) - 56)
        self.rect_buttons = pygame.Rect(pad, self.rect_panel.bottom + pad, W - pad * 2, 56)

        # Auto-fit 6 buttons
        labels = ["Play", "Sim Week", "Schedule", "Table", "Roster", "Back"]
        n = len(labels)
        gap = 12
        avail_w = self.rect_buttons.w - gap * (n - 1)
        bw = max(120, min(180, avail_w // n))  # clamp width so they always fit
        bh = 48
        x = self.rect_buttons.x
        y = self.rect_buttons.y

        btn_rects = [pygame.Rect(x + i * (bw + gap), y, bw, bh) for i in range(n)]
        self.btn_play   = Button(btn_rects[0], labels[0], self._play, font_size=22)
        self.btn_sim    = Button(btn_rects[1], labels[1], self._sim_week, font_size=22)
        self.btn_sched  = Button(btn_rects[2], labels[2], self._open_schedule, font_size=22)
        self.btn_table  = Button(btn_rects[3], labels[3], self._open_table, font_size=22)
        self.btn_roster = Button(btn_rects[4], labels[4], self._open_roster, font_size=22)
        self.btn_back   = Button(btn_rects[5], labels[5], self._back, font_size=22)

    # navigation/actions
    def _back(self) -> None:
        self.app.pop_state()

    def _open_schedule(self) -> None:
        try:
            from .state_schedule import ScheduleState
            wk = int(getattr(self.career, "week_index", 0))
            self.app.push_state(ScheduleState(self.app, self.career, wk))
        except Exception as e:
            self._last_saved_msg = f"Open Schedule failed: {e}"
            self._msg_timer = 2.5

    def _open_table(self) -> None:
        try:
            from .state_table import TableState
            self.app.push_state(TableState(self.app, self.career))
        except Exception as e:
            self._last_saved_msg = f"Open Table failed: {e}"
            self._msg_timer = 2.5

    def _open_roster(self) -> None:
        try:
            from .state_roster import RosterState
            self.app.push_state(RosterState(self.app, self.career))
        except Exception as e:
            self._last_saved_msg = f"Open Roster failed: {e}"
            self._msg_timer = 2.5

    def _sim_week(self) -> None:
        try:
            if hasattr(self.career, "simulate_week_ai"):
                self.career.simulate_week_ai()
            elif hasattr(self.career, "sim_week_ai"):
                self.career.sim_week_ai()
            self._last_saved_msg = "Week simulated."
            self._msg_timer = 2.5
        except Exception as e:
            self._last_saved_msg = f"Sim failed: {e}"
            self._msg_timer = 3.0

    def _play(self) -> None:
        # Find the user's fixture *now*, to avoid stale caches.
        wk = int(getattr(self.career, "week_index", 0))
        pairs = _fixtures_for_week(self.career, wk)
        user_tid = int(getattr(self.career, "user_team_id", -1))
        fx = _find_user_fixture(pairs, user_tid)

        if not fx:
            self._last_saved_msg = "No match for your team this week."
            self._msg_timer = 2.5
            return

        home_tid, away_tid = fx

        def _on_finish(result: Any) -> None:
            try:
                kh, ka, winner_tid = _extract_result_numbers(result, home_tid, away_tid)
                if hasattr(self.career, "record_result"):
                    try:
                        self.career.record_result(home_tid, away_tid, kh, ka, winner_tid)
                    except TypeError:
                        self.career.record_result(home_tid, away_tid, kh, ka)
                if hasattr(self.career, "advance_week_if_done"):
                    self.career.advance_week_if_done()
                names = _team_name_map(self.career)
                self._last_saved_msg = f"Result saved: {names.get(home_tid,'?')} {kh}-{ka} {names.get(away_tid,'?')}"
                self._msg_timer = 3.0
            except Exception as e:
                self._last_saved_msg = f"Save failed: {e}"
                self._msg_timer = 3.0

        try:
            from .state_match import MatchState
            st = MatchState(self.app, career=self.career, home_tid=home_tid, away_tid=away_tid,
                            week_index=wk, on_finish=_on_finish)
        except TypeError:
            from .state_match import MatchState
            st = MatchState(self.app, self.career, home_tid, away_tid, _on_finish)
        self.app.push_state(st)

    # input/update
    def handle(self, event) -> None:
        self.btn_play.handle(event)
        self.btn_sim.handle(event)
        self.btn_sched.handle(event)
        self.btn_table.handle(event)
        self.btn_roster.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        # Enable/disable Play depending on having a fixture
        wk = int(getattr(self.career, "week_index", 0))
        pairs = _fixtures_for_week(self.career, wk)
        user_tid = int(getattr(self.career, "user_team_id", -1))
        self.btn_play.enabled = _find_user_fixture(pairs, user_tid) is not None

        if self._msg_timer > 0:
            self._msg_timer = max(0.0, self._msg_timer - dt)

        mp = pygame.mouse.get_pos()
        self.btn_play.update(mp)
        self.btn_sim.update(mp)
        self.btn_sched.update(mp)
        self.btn_table.update(mp)
        self.btn_roster.update(mp)
        self.btn_back.update(mp)

    # draw
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        names = _team_name_map(self.career)
        user_tid = int(getattr(self.career, "user_team_id", -1))
        user_name = names.get(user_tid, "—")
        week_ix = int(getattr(self.career, "week_index", 0)) + 1

        draw_text(surf, f"Your Team: {user_name}",
                  (self.rect_toolbar.x + 12, self.rect_toolbar.centery), 28, th.text, align="midleft")
        draw_text(surf, f"Week {week_ix}",
                  (self.rect_toolbar.right - 12, self.rect_toolbar.centery), 32, th.subt, align="midright")

        # Optional banner
        if self._msg_timer > 0 and self._last_saved_msg:
            msg_rect = pygame.Rect(self.rect_panel.x, self.rect_panel.y - 28, self.rect_panel.w, 24)
            draw_text(surf, self._last_saved_msg, (msg_rect.centerx, msg_rect.centery), 20, th.subt, align="center")

        # Matchups panel
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-20, -20)

        hdr = "This Week's Matchups"
        rr = self.f_h2.get_rect(hdr); rr.midtop = (inner.centerx, inner.y + 4)
        self.f_h2.render_to(surf, rr.topleft, hdr, th.text)

        list_top = rr.bottom + 8
        list_rect = pygame.Rect(inner.x, list_top, inner.w, inner.bottom - list_top)
        clip = surf.get_clip(); surf.set_clip(list_rect)

        # Compute fixtures *now* so first frame always shows them
        wk = int(getattr(self.career, "week_index", 0))
        pairs = _fixtures_for_week(self.career, wk)
        lh = max(30, int(self.f_row.height * 1.25))
        y = list_rect.y + 4
        for a, b in pairs:
            left  = names.get(int(a), f"Team {a}")
            right = names.get(int(b), f"Team {b}")
            self.f_row.render_to(surf, (list_rect.x + 10, y), f"{left}  vs  {right}", th.text)
            y += lh

        surf.set_clip(clip)

        # Buttons
        self.btn_play.draw(surf, th)
        self.btn_sim.draw(surf, th)
        self.btn_sched.draw(surf, th)
        self.btn_table.draw(surf, th)
        self.btn_roster.draw(surf, th)
        self.btn_back.draw(surf, th)


def create(app, career):
    return SeasonHubState(app, career)
