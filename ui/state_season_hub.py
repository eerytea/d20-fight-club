# ui/state_season_hub.py
from __future__ import annotations
import pygame, random, traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# engine bits
from engine.constants import GRID_COLS, GRID_ROWS
from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles

# screens we navigate to
from ui.state_match import MatchState
# (Optionally: schedule/table/roster states if you have them.)
# from ui.state_schedule import ScheduleState
# from ui.state_table import TableState
# from ui.state_roster import RosterState

PAD = 16
BG = (16,16,20)
CARD = (42,44,52)
BORDER = (24,24,28)
TEXT = (235,235,240)
TEXT_MID = (210,210,218)

@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: callable
    hover: bool = False
    disabled: bool = False
    def draw(self, surf, font):
        bg = (58,60,70) if not self.hover else (76,78,90)
        if self.disabled: bg = (48,48,54)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, BORDER, self.rect, 2, border_radius=10)
        lbl = font.render(self.text, True, TEXT if not self.disabled else (165,165,170))
        surf.blit(lbl, (self.rect.centerx - lbl.get_width()//2, self.rect.centery - lbl.get_height()//2))
    def handle(self, ev):
        if self.disabled: return
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.action()

def _team_name(career, tid: int) -> str:
    try:
        if hasattr(career, "team_name") and callable(career.team_name):
            return career.team_name(int(tid))
        for t in getattr(career, "teams", []):
            if int(t.get("tid", -1)) == int(tid):
                return t.get("name", f"Team {tid}")
        teams = getattr(career, "teams", {})
        if isinstance(teams, dict) and tid in teams:
            return teams[tid].get("name", f"Team {tid}")
    except Exception:
        pass
    return f"Team {tid}"

def _fighters_for_team(career, tid: int) -> List[Dict[str,Any]]:
    ts = getattr(career, "teams", {})
    if isinstance(ts, dict):
        t = ts.get(tid, {})
        return list(t.get("fighters", []))
    for t in ts or []:
        if int(t.get("tid", -1)) == tid:
            return list(t.get("fighters", []))
    return []

def _top5(lst: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    try:
        return sorted(lst, key=lambda p: int(p.get("ovr", p.get("OVR", 60))), reverse=True)[:5]
    except Exception:
        return lst[:5]

class SeasonHubState:
    def __init__(self, app, career):
        self.app = app
        self.career = career
        self.font = pygame.font.SysFont(None, 22)
        self.h1   = pygame.font.SysFont(None, 28)
        self.h2   = pygame.font.SysFont(None, 20)
        self.btns: List[Button] = []
        self.rect_panel = None

    def enter(self):
        self._layout()

    # ---------- layout & draw ----------
    def _layout(self):
        w, h = self.app.screen.get_size()
        self.btns.clear()
        panel_w = min(720, w - 2*PAD)
        panel_h = min(480, h - 2*PAD)
        self.rect_panel = pygame.Rect((w - panel_w)//2, (h - panel_h)//2, panel_w, panel_h)

        bx = self.rect_panel.x + PAD
        by = self.rect_panel.bottom - PAD - 44
        gap = 8; bw = 140; bh = 44

        def add(label, fn, disabled=False):
            nonlocal bx
            r = pygame.Rect(bx, by, bw, bh)
            self.btns.append(Button(r, label, fn, disabled=disabled))
            bx += bw + gap

        add("Play", self._play)
        add("Sim Week", self._sim_week)
        add("Schedule", self._open_schedule)
        add("Table", self._open_table)
        add("Roster", self._open_roster)
        add("Back", self._back)

    def draw(self, screen):
        screen.fill(BG)
        pygame.draw.rect(screen, CARD, self.rect_panel, border_radius=12)
        pygame.draw.rect(screen, BORDER, self.rect_panel, 2, border_radius=12)

        title = self.h1.render("Season Hub", True, TEXT)
        screen.blit(title, (self.rect_panel.x + PAD, self.rect_panel.y + PAD))

        wk = getattr(self.career, "week", getattr(self.career, "date", {}).get("week", 1))
        wk_lbl = self.h2.render(f"Week {wk}", True, TEXT_MID)
        screen.blit(wk_lbl, (self.rect_panel.right - PAD - wk_lbl.get_width(), self.rect_panel.y + PAD + 4))

        for b in self.btns:
            b.draw(screen, self.font)

    def handle(self, ev):
        if ev.type == pygame.VIDEORESIZE:
            self._layout()
        for b in self.btns:
            b.handle(ev)
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._back()

    def update(self, dt: float):
        pass

    # ---------- actions ----------
    def _play(self):
        """
        Push the match viewer for the user's next fixture (uses MatchState).
        """
        try:
            wk = getattr(self.career, "week", getattr(self.career, "date", {}).get("week", 1))
            user_tid = getattr(self.career, "user_tid", getattr(self.career, "user_team_id", 0))
            # find fixture where user participates this week
            fx = None
            fixtures = getattr(self.career, "fixtures_by_week", None)
            if fixtures and 0 <= wk-1 < len(fixtures):
                for f in fixtures[wk-1]:
                    if not isinstance(f, dict): continue
                    h = int(f.get("home_id", f.get("home_tid", f.get("A", -1))))
                    a = int(f.get("away_id", f.get("away_tid", f.get("B", -1))))
                    if h == user_tid or a == user_tid:
                        fx = dict(f); break
            if fx is None and hasattr(self.career, "fixtures") and isinstance(self.career.fixtures, dict):
                season = self.career.date["season"] if isinstance(self.career.date, dict) else getattr(self.career, "season", 1)
                key = f"S{season}W{wk}"
                for f in self.career.fixtures.get(key, []):
                    if not isinstance(f, dict): continue
                    if int(f.get("home", f.get("home_id", -1))) == user_tid or int(f.get("away", f.get("away_id", -1))) == user_tid:
                        fx = dict(f); break
            if fx is None:
                return
            # normalize keys
            fx["home_id"] = int(fx.get("home_id", fx.get("home_tid", fx.get("A", fx.get("home", 0)))))
            fx["away_id"] = int(fx.get("away_id", fx.get("away_tid", fx.get("B", fx.get("away", 1)))))
            fx["week"]    = int(fx.get("week", wk))

            # Go to match viewer (it will build TBCombat with GRID_COLS/ROWS)
            self.app.push_state(MatchState(self.app, self.career, fx))
        except Exception:
            traceback.print_exc()

    def _sim_week(self):
        """
        Simulate all fixtures for the current week EXCEPT the user's match, using
        the same 16×16 grid the viewer uses. Results are written back to career.
        """
        wk = getattr(self.career, "week", getattr(self.career, "date", {}).get("week", 1))
        season = self.career.date["season"] if isinstance(self.career.date, dict) else getattr(self.career, "season", 1)
        user_tid = int(getattr(self.career, "user_tid", getattr(self.career, "user_team_id", 0)))
        rng = random.Random(getattr(self.career, "seed", 0) ^ (wk * 7919))

        # Collect fixtures list for this week
        fixtures: List[Dict[str,Any]] = []
        src = getattr(self.career, "fixtures_by_week", None)
        if src and 0 <= wk-1 < len(src):
            for f in src[wk-1]:
                if isinstance(f, dict):
                    dd = dict(f)
                    dd["home_id"] = int(dd.get("home_id", dd.get("home_tid", dd.get("A", dd.get("home", 0)))))
                    dd["away_id"] = int(dd.get("away_id", dd.get("away_tid", dd.get("B", dd.get("away", 1)))))
                    dd["week"] = int(dd.get("week", wk))
                    fixtures.append(dd)
        elif hasattr(self.career, "fixtures") and isinstance(self.career.fixtures, dict):
            key = f"S{season}W{wk}"
            for f in self.career.fixtures.get(key, []):
                if isinstance(f, dict):
                    dd = dict(f)
                    dd["home_id"] = int(dd.get("home_id", dd.get("home_tid", dd.get("A", dd.get("home", 0)))))
                    dd["away_id"] = int(dd.get("away_id", dd.get("away_tid", dd.get("B", dd.get("away", 1)))))
                    dd["week"] = int(dd.get("week", wk))
                    fixtures.append(dd)

        # Sim each AI-vs-AI match
        for fx in fixtures:
            h = int(fx["home_id"]); a = int(fx["away_id"])
            if h == user_tid or a == user_tid:
                # skip the user's playable match; they'll watch/play it via Play
                continue

            # Build fighters (top 5) for both teams
            f_home_src = _top5(_fighters_for_team(self.career, h))
            f_away_src = _top5(_fighters_for_team(self.career, a))
            f_home = [fighter_from_dict({**fd, "team_id": 0}) for fd in f_home_src]
            f_away = [fighter_from_dict({**fd, "team_id": 1}) for fd in f_away_src]
            fighters = f_home + f_away

            # Layout on a 16x16 grid
            layout_teams_tiles(fighters, GRID_COLS, GRID_ROWS)

            # Create combat on 16x16 and auto-resolve
            tA = Team(0, _team_name(self.career, h))
            tB = Team(1, _team_name(self.career, a))
            seed = rng.randint(0, 10_000_000)
            combat = TBCombat(tA, tB, fighters, GRID_COLS, GRID_ROWS, seed=seed)

            guard = 0
            while combat.winner is None and guard < 2000:
                combat.take_turn()
                guard += 1

            # Record result
            home_kos = len([f for f in combat.fighters if getattr(f, "team_id", 0) == 1 and not getattr(f, "alive", True)])
            away_kos = len([f for f in combat.fighters if getattr(f, "team_id", 0) == 0 and not getattr(f, "alive", True)])
            if combat.winner == 0:   winner = "home"
            elif combat.winner == 1: winner = "away"
            else:                    winner = "draw"

            try:
                if hasattr(self.career, "record_result") and callable(self.career.record_result):
                    self.career.record_result(season, wk, h, a, {"winner": winner, "home_hp": home_kos, "away_hp": away_kos})
                else:
                    # best-effort in-place fixture write
                    fx["played"] = True; fx["is_played"] = True
                    fx["score_home"] = home_kos; fx["score_away"] = away_kos
                    fx["winner"] = winner
            except Exception:
                traceback.print_exc()

        # Advance week
        try:
            if isinstance(self.career.date, dict):
                self.career.date["week"] = wk + 1
            else:
                setattr(self.career, "week", wk + 1)
        except Exception:
            pass

    def _open_schedule(self):
        # if you have a schedule screen, push it here
        # self.app.push_state(ScheduleState(self.app, self.career))
        pass

    def _open_table(self):
        # if you have a table/standings screen, push it here
        # self.app.push_state(TableState(self.app, self.career))
        pass

    def _open_roster(self):
        # if you have a roster screen, push it (read-only version of team select)
        # self.app.push_state(RosterState(self.app, self.career))
        pass

    def _back(self):
        self.app.pop_state()
