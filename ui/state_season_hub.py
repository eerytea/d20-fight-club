# ui/state_season_hub.py — Season Hub with robust career adapters
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import pygame

from .app import BaseState
from .uiutil import Theme, Button, draw_panel, draw_text, get_font


# ---------- generic helpers -------------------------------------------------

def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _safe_int(v, default: int = -1) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default

def _team_id_from(obj: Any, default: int = -1) -> int:
    for k in ("tid", "team_id", "id", "index"):
        val = _get(obj, k, None)
        if val is not None:
            try:
                return int(val)
            except Exception:
                pass
    return default

def _name_from(obj: Any, default: str = "Team") -> str:
    for k in ("name", "full_name", "display_name", "abbr", "short"):
        v = _get(obj, k, None)
        if v:
            return str(v)
    return default

def _team_name_map(career) -> Dict[int, str]:
    # Prefer a direct helper if present
    m: Dict[int, str] = {}
    if hasattr(career, "team_name"):
        for t in getattr(career, "teams", []) or []:
            tid = _team_id_from(t, -1)
            if tid >= 0:
                try:
                    m[tid] = str(career.team_name(tid))  # type: ignore[attr-defined]
                except Exception:
                    pass
    if m:
        return m

    # Fall back to scanning teams list
    for t in getattr(career, "teams", []) or []:
        tid = _team_id_from(t, -1)
        nm = _name_from(t, f"Team {tid}")
        if tid >= 0:
            m[tid] = nm

    # As a last resort, some careers expose team_names dict
    tn = getattr(career, "team_names", None)
    if isinstance(tn, dict):
        for k, v in tn.items():
            try:
                m[int(k)] = str(v)
            except Exception:
                pass
    return m


# ---------- fixtures adapters -----------------------------------------------

def _pair_from_any(item) -> Optional[Tuple[int, int]]:
    """Parse a fixture object into (home_tid, away_tid)."""
    if item is None:
        return None
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        try:
            return (int(item[0]), int(item[1]))
        except Exception:
            return None
    if isinstance(item, dict):
        for hk, ak in (("home_tid", "away_tid"), ("home_id", "away_id"),
                       ("home", "away"), ("h", "v"), ("a", "b")):
            ha = item.get(hk, None)
            aw = item.get(ak, None)
            if ha is not None and aw is not None:
                try:
                    return (int(ha), int(aw))
                except Exception:
                    pass
    # attributes?
    ha = _get(item, "home_tid", _get(item, "home", _get(item, "h", None)))
    aw = _get(item, "away_tid", _get(item, "away", _get(item, "v", None)))
    if ha is not None and aw is not None:
        try:
            return (int(ha), int(aw))
        except Exception:
            return None
    return None

def _fixtures_for_week(career, week_idx: int) -> List[Tuple[int, int]]:
    """Return a list of (home_tid, away_tid) pairs for the given week, regardless of shape."""
    # Method adapters first
    for meth in ("fixtures_for_week", "get_fixtures_for_week", "week_fixtures", "fixtures_in_week"):
        fn = getattr(career, meth, None)
        if callable(fn):
            try:
                out = fn(week_idx)
                pairs: List[Tuple[int, int]] = []
                for it in out or []:
                    p = _pair_from_any(it)
                    if p: pairs.append(p)
                if pairs:
                    return pairs
            except Exception:
                pass

    # Common attribute shapes
    candidates = [
        "schedule",          # list[week] or flat list with 'week'
        "fixtures",          # list[week] or flat list with 'week'
        "fixtures_by_week",  # dict[int] -> list
        "rounds",            # list[week]
        "weeks",             # list[week]
    ]

    for attr in candidates:
        obj = getattr(career, attr, None)
        if obj is None:
            continue

        # list of weeks
        if isinstance(obj, list):
            wk = obj[week_idx] if 0 <= week_idx < len(obj) else []
            pairs: List[Tuple[int, int]] = []
            for it in wk or []:
                p = _pair_from_any(it)
                if p: pairs.append(p)
            if pairs:
                return pairs

        # dict by week index
        if isinstance(obj, dict):
            wk = obj.get(week_idx, [])
            pairs: List[Tuple[int, int]] = []
            for it in wk or []:
                p = _pair_from_any(it)
                if p: pairs.append(p)
            if pairs:
                return pairs

        # flat list with a `week` field on each item
        if isinstance(obj, list):
            pairs: List[Tuple[int, int]] = []
            for it in obj:
                w = _get(it, "week", _get(it, "round", _get(it, "week_index", None)))
                if w is not None and int(w) == int(week_idx):
                    p = _pair_from_any(it)
                    if p: pairs.append(p)
            if pairs:
                return pairs

    # No fixtures found
    return []

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

        self._last_msg: Optional[str] = None
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
        bw = max(120, min(180, avail_w // n))
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
            wk = _safe_int(getattr(self.career, "week_index", 0), 0)
            self.app.push_state(ScheduleState(self.app, self.career, wk))
        except Exception as e:
            self._last_msg = f"Open Schedule failed: {e}"
            self._msg_timer = 2.5

    def _open_table(self) -> None:
        try:
            from .state_table import TableState
            self.app.push_state(TableState(self.app, self.career))
        except Exception as e:
            self._last_msg = f"Open Table failed: {e}"
            self._msg_timer = 2.5

    def _open_roster(self) -> None:
        try:
            from .state_roster import RosterState
            self.app.push_state(RosterState(self.app, self.career))
        except Exception as e:
            self._last_msg = f"Open Roster failed: {e}"
            self._msg_timer = 2.5

    def _try_sim_method(self) -> bool:
        # Try a few common names, first one that exists wins
        for name in ("simulate_week_ai", "simulate_week", "sim_week_ai", "sim_week"):
            fn = getattr(self.career, name, None)
            if callable(fn):
                fn()  # assume no-arg
                return True
        return False

    def _sim_week(self) -> None:
        try:
            ok = self._try_sim_method()
            if ok:
                # Some careers separate advancement
                adv = getattr(self.career, "advance_week_if_done", None)
                if callable(adv):
                    try: adv()
                    except Exception: pass
                self._last_msg = "Week simulated."
            else:
                self._last_msg = "No sim method found on career."
            self._msg_timer = 2.5
        except Exception as e:
            self._last_msg = f"Sim failed: {e}"
            self._msg_timer = 3.0

    def _play(self) -> None:
        wk = _safe_int(getattr(self.career, "week_index", 0), 0)
        pairs = _fixtures_for_week(self.career, wk)
        user_tid = _safe_int(getattr(self.career, "user_team_id", -1), -1)
        fx = _find_user_fixture(pairs, user_tid)
        if not fx:
            self._last_msg = "No match for your team this week."
            self._msg_timer = 2.5
            return

        home_tid, away_tid = fx
        names = _team_name_map(self.career)

        def _on_finish(result: Any) -> None:
            try:
                kh, ka, winner_tid = _extract_result_numbers(result, home_tid, away_tid)
                if hasattr(self.career, "record_result"):
                    try:
                        self.career.record_result(home_tid, away_tid, kh, ka, winner_tid)
                    except TypeError:
                        self.career.record_result(home_tid, away_tid, kh, ka)
                adv = getattr(self.career, "advance_week_if_done", None)
                if callable(adv):
                    adv()
                self._last_msg = f"Saved: {names.get(home_tid,'?')} {kh}-{ka} {names.get(away_tid,'?')}"
                self._msg_timer = 3.0
            except Exception as e:
                self._last_msg = f"Save failed: {e}"
                self._msg_timer = 3.0

        try:
            from .state_match import MatchState
            st = None
            try:
                st = MatchState(self.app, career=self.career, home_tid=home_tid, away_tid=away_tid,
                                week_index=wk, on_finish=_on_finish)
            except TypeError:
                st = MatchState(self.app, self.career, home_tid, away_tid, _on_finish)
            self.app.push_state(st)
        except Exception as e:
            self._last_msg = f"Play failed: {e}"
            self._msg_timer = 3.0

    # input/update
    def handle(self, event) -> None:
        self.btn_play.handle(event)
        self.btn_sim.handle(event)
        self.btn_sched.handle(event)
        self.btn_table.handle(event)
        self.btn_roster.handle(event)
        self.btn_back.handle(event)

    def update(self, dt: float) -> None:
        wk = _safe_int(getattr(self.career, "week_index", 0), 0)
        pairs = _fixtures_for_week(self.career, wk)
        user_tid = _safe_int(getattr(self.career, "user_team_id", -1), -1)
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
        user_tid = _safe_int(getattr(self.career, "user_team_id", -1), -1)
        user_name = names.get(user_tid, "—")
        week_ix = _safe_int(getattr(self.career, "week_index", 0), 0) + 1

        draw_text(surf, f"Your Team: {user_name}",
                  (self.rect_toolbar.x + 12, self.rect_toolbar.centery), 28, th.text, align="midleft")
        draw_text(surf, f"Week {week_ix}",
                  (self.rect_toolbar.right - 12, self.rect_toolbar.centery), 32, th.subt, align="midright")

        # Optional banner
        if self._msg_timer > 0 and self._last_msg:
            msg_rect = pygame.Rect(self.rect_panel.x, self.rect_panel.y - 28, self.rect_panel.w, 24)
            draw_text(surf, self._last_msg, (msg_rect.centerx, msg_rect.centery), 20, th.subt, align="center")

        # Matchups panel
        draw_panel(surf, self.rect_panel, th)
        inner = self.rect_panel.inflate(-20, -20)

        hdr = "This Week's Matchups"
        rr = self.f_h2.get_rect(hdr); rr.midtop = (inner.centerx, inner.y + 4)
        self.f_h2.render_to(surf, rr.topleft, hdr, th.text)

        list_top = rr.bottom + 8
        list_rect = pygame.Rect(inner.x, list_top, inner.w, inner.bottom - list_top)
        clip = surf.get_clip(); surf.set_clip(list_rect)

        wk = _safe_int(getattr(self.career, "week_index", 0), 0)
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
