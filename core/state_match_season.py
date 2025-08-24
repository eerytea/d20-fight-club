# ui/state_match_season.py
import pygame
from typing import Optional, List
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button
from core.types import Career, Fixture
from core.sim import GRID_W, GRID_H, simulate_fixture_full, simulate_week_full_except
from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles

class SeasonMatchState(UIState):
    """
    Lets the user play their scheduled match for the current week.
    After it ends, autosims all other fixtures that week (full combat),
    applies results, then returns to Season Hub.
    """
    def __init__(self, app, career: Career, user_team_id: int):
        self.app = app
        self.career = career
        self.user_team_id = user_team_id
        self.buttons: List[Button] = []
        self.log: List[str] = []
        self.auto = False
        self._auto_timer = 0.0
        self.combat: Optional[TBCombat] = None
        self.fixture_index_in_week: Optional[int] = None  # index of user's fixture among this week's fixtures
        self._fixture: Optional[Fixture] = None

    def on_enter(self) -> None:
        self.buttons = [
            Button(pygame.Rect(16, 16, 110, 36), "Back", on_click=self._back_abort),
            Button(pygame.Rect(136, 16, 110, 36), "Reset", on_click=self._reset),
            Button(pygame.Rect(256, 16, 130, 36), "Next Turn", on_click=self._next),
            Button(pygame.Rect(396, 16, 130, 36), "Auto: OFF", on_click=self._toggle_auto),
            Button(pygame.Rect(546, 16, 160, 36), "Finish & Sim", on_click=self._finish_and_sim_rest),
        ]
        self._setup_user_fixture()

    def _setup_user_fixture(self):
        wk = self.career.week
        week_fx = [f for f in self.career.fixtures if f.week == wk]
        # find user's fixture
        idx = None
        for i, fx in enumerate(week_fx):
            if fx.home_id == self.user_team_id or fx.away_id == self.user_team_id:
                idx = i; self._fixture = fx; break
        self.fixture_index_in_week = idx

        if self._fixture is None:
            self.log = ["No fixture for your team this week."]
            return

        # Build teams+fighters from the career roster
        from core.sim import _build_top4_teams_for_fixture  # internal helper
        teamH, teamA, fighters = _build_top4_teams_for_fixture(self.career, self._fixture)
        self.combat = TBCombat(teamH, teamA, fighters, GRID_W, GRID_H, seed=777)
        self.log = []
        self._drain_log()  # initial init/round events

    def _back_abort(self):
        # return without applying results
        from .state_season_hub import SeasonHubState
        self.app.replace_state(SeasonHubState(self.app, self.career, self.user_team_id))

    def _reset(self):
        self._setup_user_fixture()

    def _toggle_auto(self):
        self.auto = not self.auto
        self.buttons[3].label = f"Auto: {'ON' if self.auto else 'OFF'}"

    def _next(self):
        if not self.combat or self.combat.winner is not None:
            return
        before = len(self.combat.events)
        self.combat.take_turn()
        self._drain_log(start=before)

    def _drain_log(self, start: int = 0):
        if not self.combat: return
        for e in self.combat.events[start:]:
            k = e.kind; p = e.payload
            if k == "init":           self._push(f"Init: {p['name']} = {p['init']}")
            elif k == "round_start":  self._push(f"— Round {p['round']} —")
            elif k == "turn_start":   self._push(f"{p['actor']}'s turn")
            elif k == "move_step":    self._push(f"  moves to {p['to']}")
            elif k == "attack":
                txt = f"  attacks {p['defender']} (d20={p['nat']} vs AC {p['target_ac']})"
                if p.get("critical"): txt += " — CRIT!"
                if not p['hit']:      txt += " — MISS"
                self._push(txt)
            elif k == "damage":       self._push(f"    → {p['defender']} takes {p['amount']} (HP {p['hp_after']})")
            elif k == "down":         self._push(f"    ✖ {p['name']} is down")
            elif k == "end":
                if "winner" in p:     self._push(f"Match ends — Winner: {p['winner']} ({p.get('reason','')})")
                else:                 self._push(f"Match ends — Draw ({p.get('reason','')})")
            elif k == "round_end":    self._push(f"— End Round {p['round']} —")

    def _push(self, s: str):
        self.log.append(s)
        self.log = self.log[-28:]

    def _finish_and_sim_rest(self):
        """Apply this match’s result to the fixture, then autosim others and return to hub."""
        if not self._fixture:
            self._back_abort(); return
        if self._fixture.played:
            # already applied (avoid double)
            pass
        else:
            # compute "goals" by re-summarizing final board (same method as autosim)
            from core.sim import _apply_result
            # Count KOs inflicted by each side:
            downs_by_home = sum(1 for f in self.combat.fighters if f.team_id == 1 and not f.alive)
            downs_by_away = sum(1 for f in self.combat.fighters if f.team_id == 0 and not f.alive)
            _apply_result(self.career, self._fixture, downs_by_home, downs_by_away)

        # sim the rest of the week
        if self.fixture_index_in_week is not None:
            simulate_week_full_except(self.career, self.fixture_index_in_week)
        # go back to hub
        from .state_season_hub import SeasonHubState
        self.app.replace_state(SeasonHubState(self.app, self.career, self.user_team_id))

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        for b in self.buttons: b.handle_event(event)
        return None

    def update(self, dt: float) -> Optional["UIState"]:
        if self.auto and self.combat and self.combat.winner is None:
            self._auto_timer -= dt
            if self._auto_timer <= 0.0:
                self._next()
                self._auto_timer = 0.35
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((16, 18, 24))
        for b in self.buttons: b.draw(surface)

        # arena grid
        arena_w = surface.get_width() - 380
        arena_h = surface.get_height()
        cell_w = max(24, arena_w // GRID_W)
        cell_h = max(24, arena_h // GRID_H)
        for gx in range(GRID_W):
            pygame.draw.line(surface, (34,36,44), (gx*cell_w, 0), (gx*cell_w, arena_h))
        for gy in range(GRID_H):
            pygame.draw.line(surface, (34,36,44), (0, gy*cell_h), (arena_w, gy*cell_h))

        # fighters
        if self.combat:
            for f in self.combat.fighters:
                if not f.alive: continue
                cx = f.tx * cell_w + cell_w//2
                cy = f.ty * cell_h + cell_h//2
                col = (120,180,255) if f.team_id == 0 else (255,140,140)
                pygame.draw.circle(surface, col, (cx, cy), min(cell_w, cell_h)//3)
                frac = max(0.0, min(1.0, f.hp / max(1, f.max_hp)))
                bw, bh = int(cell_w*0.8), 6
                bx, by = cx - bw//2, cy - (cell_h//2) + 4
                pygame.draw.rect(surface, (60,62,70), pygame.Rect(bx, by, bw, bh), border_radius=4)
                c = (90,220,140) if frac>0.5 else (240,210,120) if frac>0.25 else (240,120,120)
                pygame.draw.rect(surface, c, pygame.Rect(bx+1, by+1, int((bw-2)*frac), bh-2), border_radius=4)
                nm = FONT.render(f.name, True, (235,238,240))
                surface.blit(nm, (cx - nm.get_width()//2, cy + 6))

        # sidebar log
        x0 = surface.get_width() - 380
        pygame.draw.rect(surface, (20,22,30), pygame.Rect(x0, 0, 380, surface.get_height()))
        draw_text(surface, "Turn Log", (x0 + 16, 16), font=BIG)
        y = 64
        for line in self.log:
            draw_text(surface, line, (x0 + 16, y), font=FONT)
            y += 22
