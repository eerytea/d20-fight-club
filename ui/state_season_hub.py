# ui/state_season_hub.py
from __future__ import annotations

import random
from typing import Optional, List

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

try:
    from .uiutil import Button
except Exception:
    Button = None  # type: ignore

from engine import Team, fighter_from_dict, layout_teams_tiles, TBCombat
from .state_message import MessageState
from .state_match import MatchState
from .state_roster import RosterState
from .state_schedule import ScheduleState
from .state_table import TableState

GRID_W, GRID_H = 10, 8


class SeasonHubState:
    """
    Manager hub: Play My Match, Roster, Schedule, Table, Save, Settings
    """

    def __init__(self, app, career):
        self.app = app
        self.career = career
        self._title_font = None
        self._font = None
        self._small = None
        self._buttons = []

    def enter(self):
        if pygame is None: return
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 26)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small = pygame.font.SysFont("consolas", 14)
        self._layout()

    def _layout(self):
        self._buttons.clear()
        w, h = self.app.width, self.app.height
        btn_w, btn_h, gap = 180, 44, 14
        x = 24; y = 100

        def mk(label, fn):
            rect = pygame.Rect(x, y, btn_w, btn_h)
            y_loc = y
            if Button:
                self._buttons.append(Button(rect, label, on_click=fn))
            else:
                self._buttons.append(_SimpleButton(rect, label, fn))
            return y_loc

        y = 100
        mk("Play My Match", self._play_my_match); y += btn_h + gap
        mk("Roster", self._open_roster); y += btn_h + gap
        mk("Schedule", self._open_schedule); y += btn_h + gap
        mk("Table", self._open_table); y += btn_h + gap
        mk("Save", self._save); y += btn_h + gap
        mk("Settings", self._open_settings); y += btn_h + gap
        mk("Back to Menu", self._back_to_menu)

    def handle_event(self, e):
        if pygame is None: return False
        for b in self._buttons:
            if b.handle_event(e): return True
        return False

    def update(self, dt): pass

    def draw(self, surf):
        if pygame is None: return
        w, h = surf.get_size()
        t = self._title_font.render("Season Hub", True, (255,255,255))
        surf.blit(t, (24, 24))

        cur = self._small.render(f"Week {self.career.week+1}", True, (220,220,220))
        surf.blit(cur, (24, 60))

        # next fixture info for YOUR team
        your = self.career.user_team_id
        fx = self._find_my_fixture()
        if fx:
            hn = self.career.team_names[fx.home_id]
            an = self.career.team_names[fx.away_id]
            info = f"Next: {hn} vs {an} ({'played' if fx.played else 'unplayed'})"
        else:
            info = "No fixture this week"
        surf.blit(self._font.render(info, True, (230,230,230)), (220, 110))

        for b in self._buttons:
            b.draw(surf)

    # ----- actions -----

    def _back_to_menu(self):
        self.app.pop_state()

    def _open_roster(self):
        self.app.safe_push(RosterState, app=self.app, career=self.career)

    def _open_schedule(self):
        self.app.safe_push(ScheduleState, app=self.app, career=self.career)

    def _open_table(self):
        self.app.safe_push(TableState, app=self.app, career=self.career)

    def _open_settings(self):
        try:
            from .state_settings import SettingsState
            self.app.safe_push(SettingsState, app=self.app)
        except Exception:
            self._msg("Settings screen not available.")

    def _save(self):
        try:
            from core.save import save_career  # prefer named function
            save_career(self.career)
            self._msg("Game saved.")
        except Exception:
            try:
                # fallback: try generic 'save'
                from core.save import save as _save
                _save(self.career)
                self._msg("Game saved.")
            except Exception as e:
                self._msg(f"Save failed:\n{e}")

    def _play_my_match(self):
        fx = self._find_my_fixture()
        if not fx:
            self._msg("No unplayed fixture for your team this week.")
            return

        # Build TBCombat with top 4 fighters each side
        tb, title, rebuild = self._build_tb_for_fixture(fx)

        def on_result(winner_rel, hg, ag, tb_obj):
            # update fixture & table (3/1/0)
            fx.home_goals, fx.away_goals, fx.played = int(hg), int(ag), True
            tH = self.career.table[fx.home_id]
            tA = self.career.table[fx.away_id]
            tH.played += 1; tA.played += 1
            tH.goals_for += hg; tH.goals_against += ag
            tA.goals_for += ag; tA.goals_against += hg
            if hg > ag:
                tH.wins += 1; tH.points += 3; tA.losses += 1
            elif ag > hg:
                tA.wins += 1; tA.points += 3; tH.losses += 1
            else:
                tH.draws += 1; tA.draws += 1; tH.points += 1; tA.points += 1

        self.app.safe_push(MatchState, app=self.app, tbcombat=tb, title=title, scheduled=True, on_result=on_result, rebuild=rebuild)

    # ----- helpers -----

    def _find_my_fixture(self):
        you = self.career.user_team_id
        wk = self.career.week
        for f in self.career.fixtures:
            if f.week == wk and not f.played and (f.home_id == you or f.away_id == you):
                return f
        return None

    def _build_tb_for_fixture(self, fx):
        # Pull top 4 by OVR
        def top4(tid):
            roster = self.career.rosters[tid]
            return sorted(roster, key=lambda f: f.get("ovr", 50), reverse=True)[:4]

        def mk_team(tid):
            return Team(0 if tid == fx.home_id else 1,
                        self.career.team_names[tid],
                        tuple(self.career.team_colors[tid]))

        def mk_fighters():
            H = [fighter_from_dict({**fd, "team_id": 0}) for fd in top4(fx.home_id)]
            A = [fighter_from_dict({**fd, "team_id": 1}) for fd in top4(fx.away_id)]
            return H + A

        seed = (self.career.seed * 10007) ^ (fx.week * 997) ^ (fx.home_id * 31 + fx.away_id * 17)

        def build():
            teamH = mk_team(fx.home_id)
            teamA = mk_team(fx.away_id)
            fighters = mk_fighters()
            layout_teams_tiles(fighters, GRID_W, GRID_H)
            return TBCombat(teamH, teamA, fighters, GRID_W, GRID_H, seed=seed)

        tb = build()
        title = f"{self.career.team_names[fx.home_id]} vs {self.career.team_names[fx.away_id]}"
        return tb, title, build

    def _msg(self, text: str):
        self.app.push_state(MessageState(app=self.app, text=text))


class _SimpleButton:
    def __init__(self, rect, label, on_click):
        self.rect, self.label, self.on_click = rect, label, on_click
        self.hover=False; self._font=pygame.font.SysFont("consolas",18) if pygame else None
    def handle_event(self,e):
        if e.type==pygame.MOUSEMOTION: self.hover=self.rect.collidepoint(e.pos)
        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and self.rect.collidepoint(e.pos):
            self.on_click(); return True
        return False
    def draw(self,surf):
        bg=(120,120,120) if self.hover else (98,98,98)
        pygame.draw.rect(surf,bg,self.rect,border_radius=6)
        pygame.draw.rect(surf,(50,50,50),self.rect,2,border_radius=6)
        t=self._font.render(self.label,True,(20,20,20))
        surf.blit(t,(self.rect.x+(self.rect.w-t.get_width())//2,self.rect.y+(self.rect.h-t.get_height())//2))
