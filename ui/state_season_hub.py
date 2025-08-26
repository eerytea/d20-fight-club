# ui/state_season_hub.py — Season Hub with clean matchups list + robust Play/save
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
    """
    Return a list of (home_tid, away_tid) for the given week.
    Tries multiple shapes so we don't break if core changes slightly.
    """
    # 1) explicit helper
    if hasattr(career, "fixtures_for_week"):
        try:
            pairs = career.fixtures_for_week(week_idx)
            if pairs:
                return [(int(a), int(b)) for (a, b) in pairs]
        except Exception:
            pass

    # 2) schedule attribute
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
    """
    Try hard to pull (kills_home, kills_away, winner_tid) out of whatever the MatchState gives us.
    """
    kh = _get(result, "kills_home", None)
    ka = _get(result, "kills_away", None)
    if kh is None: kh = _get(result, "k_home", _get(result, "home_kills", _get(result, "A", 0)))
    if ka is None: ka = _get(result, "k_away", _get(result, "away_kills", _get(result, "B", 0)))

    win_tid = _get(result, "winner_tid", None)
    if win_tid is None:
        # Some engines return winner team_id relative to fixture ordering
        w = _get(result, "winner", None)
        if isinstance(w, int):
            win_tid = w
        elif isinstance(w, str):
            # If name returned, we can't safely map; leave None → UI/core can treat as draw
            win_tid = None

    # Ensure ints
    try: kh = int(kh)
    except Exception: kh = 0
    try: ka = int(ka)
    except Exception: ka = 0
    try:
        win_tid = int(win_tid) if win_tid is not None else None
    except Exception:
        win_tid = None

    # If winner missing, infer by score
    if win_tid is None and kh != ka:
        win_tid = home_tid if kh > ka else away_tid

    return kh, ka, win_tid


# ---------- state -----------------------------------------------------------

class SeasonHubState(BaseState):
    """
    Season hub:
      - Header bar: "Your Team: <name>" (left) and "Week N" (right).
      - Big panel: "This Week's Matchups" + clipped list of fixtures.
      - Buttons row: Play / Sim Week / Schedule / Table / Roster / Back.
      - After a match completes, saves result & shows a one-line banner.
    """

    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.theme = Theme()

        # Layout rects
        self.rect_toolbar = pygame.Rect(0, 0, 0, 0)
        self.rect_panel   = pygame.Rect(0, 0, 0, 0)
        self.rect_buttons = pygame.Rect(0, 0, 0, 0)

        # Buttons
        self.btn_play: Button | None = None
        self.btn_sim : Button | None = None
        self.btn_sched: Button | None = None
        self.btn_table: Button | None = None
        self.btn_roster: Button | None = None
        self.btn_back: Button | None = None

        # Fonts
        self.f_title = get_font(42)
        self.f_h2    = get_font(34)
        self.f_row   = get_font(28)
        self.f_msg   = get_font(22)

        # UI state
        self._last_saved_msg: Optional[str] = None
        self._msg_timer: float = 0.0

        # Cached for Play button
        self._cached_pairs: List[Tuple[int, int]] = []
        self._cached_user_fixture: Optional[Tuple[int, int]] = None

    # -------- lifecycle --------
    def enter(self) -> None:
        self._layout()

    def _layout(self) -> None:
        W, H = self.app.width, self.app.height
        pad = 16
        toolbar_h = 80

        self.rect_toolbar = pygame.Rect(pad, pad, W - pad * 2, toolbar_h)
        # main list panel
        self.rect_panel   = pygame.Rect(pad, self.rect_toolbar.bottom + pad, W - pad * 2, H - (toolbar_h + pad * 4) - 64)
        # buttons bar
        self.rect_buttons = pygame.Rect(pad, self.rect_panel.bottom + pad, W - pad * 2, 64)

        # Buttons row
        bw, bh = 180, 56
        gap = 16
        bx = self.rect_buttons.x
        by = self.rect_buttons.y
        self.btn_play   = Button(pygame.Rect(bx, by, bw, bh), "Play", self._play)
        self.btn_sim    = Button(pygame.Rect(bx + (bw + gap)*1, by, bw, bh), "Sim Week", self._sim_week)
        self.btn_sched  = Button(pygame.Rect(bx + (bw + gap)*2, by, bw, bh), "Schedule", self._open_schedule)
        self.btn_table  = Button(pygame.Rect(bx + (bw + gap)*3, by, bw, bh), "Table", self._open_table)
        self.btn_roster = Button(pygame.Rect(bx + (bw + gap)*4, by, bw, bh), "Roster", self._open_roster)
        self.btn_back   = Button(pygame.Rect(self.rect_buttons.right - bw, by, bw, bh), "Back", self._back)

    # -------- navigation/actions --------
    def _back(self) -> None:
        self.app.pop_state()

    def _open_schedule(self) -> None:
        try:
            from .state_schedule import ScheduleState
            wk = getattr(self.career, "week_index", 0)
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
        # Simulate the whole week (AI helpers), if available
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
        if not self._cached_user_fixture:
            self._last_saved_msg = "No match for your team this week."
            self._msg_timer = 2.5
            return

        home_tid, away_tid = self._cached_user_fixture

        # Callback after match ends
        def _on_finish(result: Any) -> None:
            try:
                kh, ka, winner_tid = _extract_result_numbers(result, home_tid, away_tid)
                # Record & advance
                if hasattr(self.career, "record_result"):
                    try:
                        self.career.record_result(home_tid, away_tid, kh, ka, winner_tid)
                    except TypeError:
                        # fallback signatures
                        try:
                            self.career.record_result(home_tid, away_tid, kh, ka)
                        except TypeError:
                            self.career.record_result(home_tid, away_tid, (kh, ka))  # type: ignore
                if hasattr(self.career, "advance_week_if_done"):
                    self.career.advance_week_if_done()

                # Message banner
                names = _team_name_map(self.career)
                self._last_saved_msg = f"Result saved: {names.get(home_tid, f'Team {home_tid}')}" \
                                       f" {kh}-{ka} {names.get(away_tid, f'Team {away_tid}')}"
                self._msg_timer = 3.0
            except Exception as e:
                self._last_saved_msg = f"Save failed: {e}"
                self._msg_timer = 3.0

        # Push match state with flexible constructor
        try:
            from .state_match import MatchState
        except Exception as e:
            self._last_saved_msg = f"Match screen missing: {e}"
            self._msg_timer = 3.0
            return

        try:
            # Preferred: named args
            st = MatchState(self.app, career=self.career, home_tid=home_tid, away_tid=away_tid,
                            week_index=getattr(self.career, "week_index", 0), on_finish=_on_finish)
        except TypeError:
            # Fallback: (app, career, home_tid, away_tid, on_finish)
            try:
                st = MatchState(self.app, self.career, home_tid, away_tid, _on_finish)
            except TypeError:
                # Last resort: (app, home_tid, away_tid, on_finish)
                st = MatchState(self.app, home_tid, away_tid, _on_finish)
        self.app.push_state(st)

    # -------- input --------
    def handle(self, event) -> None:
        self.btn_play.handle(event)
        self.btn_sim.handle(event)
        self.btn_sched.handle(event)
        self.btn_table.handle(event)
        self.btn_roster.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        # Cache current week fixtures/user fixture for quick access & Play enabled state
        wk = getattr(self.career, "week_index", 0)
        pairs = _fixtures_for_week(self.career, wk)
        self._cached_pairs = pairs
        user_tid = int(getattr(self.career, "user_team_id", -1))
        self._cached_user_fixture = _find_user_fixture(pairs, user_tid)

        # Enable/disable Play depending on having a fixture
        self.btn_play.enabled = self._cached_user_fixture is not None

        # Dismiss transient message after a few seconds
        if self._msg_timer > 0:
            self._msg_timer = max(0.0, self._msg_timer - dt)

        mp = pygame.mouse.get_pos()
        self.btn_play.update(mp)
        self.btn_sim.update(mp)
        self.btn_sched.update(mp)
        self.btn_table.update(mp)
        self.btn_roster.update(mp)
        self.btn_back.update(mp)

    # -------- draw --------
    def draw(self, surf) -> None:
        th = self.theme
        surf.fill(th.bg)

        # Toolbar
        draw_panel(surf, self.rect_toolbar, th)
        names = _team_name_map(self.career)
        user_tid = int(getattr(self.career, "user_team_id", -1))
        user_name = names.get(user_tid, "—")
        week_ix = int(getattr(self.career, "week_index", 0)) + 1

        # Left: Your Team
        draw_text(surf, f"Your Team: {user_name}",
                  (self.rect_toolbar.x + 12, self.rect_toolbar.centery),
                  28, th.text, align="midleft")
        # Right: Week N
        draw_text(surf, f"Week {week_ix}",
                  (self.rect_toolbar.right - 12, self.rect_toolbar.centery),
                  32, th.subt, align="midright")

        # Saved message banner (optional)
        if self._msg_timer > 0 and self._last_saved_msg:
            msg_rect = pygame.Rect(self.rect_panel.x, self.rect_panel.y - 28, self.rect_panel.w, 24)
            draw_text(surf, self._last_saved_msg, (msg_rect.centerx, msg_rect.centery), 20, th.subt, align="center")

        # Matchups panel
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-20, -20)

        # Box title
        hdr = "This Week's Matchups"
        rr = self.f_h2.get_rect(hdr); rr.midtop = (inner.centerx, inner.y + 4)
        self.f_h2.render_to(surf, rr.topleft, hdr, th.text)

        # List area under title — with clipping
        list_top = rr.bottom + 8
        list_rect = pygame.Rect(inner.x, list_top, inner.w, inner.bottom - list_top)
        clip = surf.get_clip(); surf.set_clip(list_rect)

        pairs = self._cached_pairs
        lh = max(30, int(self.f_row.height * 1.25))
        y = list_rect.y + 4
        for (a, b) in pairs:
            left  = names.get(int(a), f"Team {a}")
            right = names.get(int(b), f"Team {b}")
            # hard left anchor so text never drifts out of box
            self.f_row.render_to(surf, (list_rect.x + 10, y), f"{left}  vs  {right}", th.text)
            y += lh

        surf.set_clip(clip)

        # Buttons row
        self.btn_play.draw(surf, th)
        self.btn_sim.draw(surf, th)
        self.btn_sched.draw(surf, th)
        self.btn_table.draw(surf, th)
        self.btn_roster.draw(surf, th)
        self.btn_back.draw(surf, th)


def create(app, career):
    return SeasonHubState(app, career)
