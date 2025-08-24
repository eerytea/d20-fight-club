# ui/state_exhibition_picker.py
from __future__ import annotations

import random
from typing import List

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

from engine import Team, fighter_from_dict, layout_teams_tiles, TBCombat
from .state_message import MessageState
from .state_match import MatchState  # our simple match viewer

GRID_W, GRID_H = 10, 8


def _rand_seed() -> int:
    return random.randint(1, 2_000_000_000)


class ExhibitionPickerState:
    """
    Pick Home/Away teams then run a quick match.

    Controls:
      LEFT/RIGHT — choose which side you're editing
      UP/DOWN    — change team name (just from a simple list)
      ENTER      — start match
      R          — randomize both
      ESC        — back
    """

    def __init__(self, app) -> None:
        self.app = app
        self._font = None
        # simple sample list; if you prefer, you can import from a creator or career
        self.team_names: List[str] = [
            "Dragons", "Wolves", "Knights", "Rogues", "Mages", "Clerics", "Berserkers", "Rangers"
        ]
        self.home_idx: int = 0
        self.away_idx: int = 1
        self.edit_side: int = 0  # 0=home, 1=away

    # ----- lifecycle -----

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 22)

    # ----- events / update / draw -----

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.pop_state()
                return True
            if event.key == pygame.K_LEFT:
                self.edit_side = 0
                return True
            if event.key == pygame.K_RIGHT:
                self.edit_side = 1
                return True
            if event.key == pygame.K_UP:
                if self.edit_side == 0:
                    self.home_idx = (self.home_idx - 1) % len(self.team_names)
                    if self.home_idx == self.away_idx:
                        self.away_idx = (self.away_idx + 1) % len(self.team_names)
                else:
                    self.away_idx = (self.away_idx - 1) % len(self.team_names)
                    if self.away_idx == self.home_idx:
                        self.home_idx = (self.home_idx + 1) % len(self.team_names)
                return True
            if event.key == pygame.K_DOWN:
                if self.edit_side == 0:
                    self.home_idx = (self.home_idx + 1) % len(self.team_names)
                    if self.home_idx == self.away_idx:
                        self.away_idx = (self.away_idx + 1) % len(self.team_names)
                else:
                    self.away_idx = (self.away_idx + 1) % len(self.team_names)
                    if self.away_idx == self.home_idx:
                        self.home_idx = (self.home_idx + 1) % len(self.team_names)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._start_match()
                return True
            if event.key in (pygame.K_r,):
                self._randomize()
                return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()
        title = self._text("Exhibition — Pick Teams", 32, bold=True)
        surface.blit(title, (24, 24))

        y = 110
        left_x = 80
        right_x = w // 2 + 40

        home_lbl = self._text("Home", 24, bold=(self.edit_side == 0))
        away_lbl = self._text("Away", 24, bold=(self.edit_side == 1))
        surface.blit(home_lbl, (left_x, 70))
        surface.blit(away_lbl, (right_x, 70))

        home_name = self.team_names[self.home_idx]
        away_name = self.team_names[self.away_idx]
        surface.blit(self._font.render(home_name, True, (230, 230, 230)), (left_x, y))  # type: ignore
        surface.blit(self._font.render(away_name, True, (230, 230, 230)), (right_x, y))  # type: ignore

        hint = self._text("LEFT/RIGHT side • UP/DOWN change • ENTER start • R randomize • ESC back", 18)
        surface.blit(hint, (24, h - 36))

    # ----- helpers -----

    def _text(self, s: str, size: int, bold: bool = False):
        ft = pygame.font.SysFont("consolas", size, bold=bold)  # type: ignore
        return ft.render(s, True, (255, 255, 255))

    def _push_msg(self, text: str):
        try:
            self.app.push_state(MessageState(app=self.app, text=text))
        except Exception:
            print(text)

    def _randomize(self):
        n = len(self.team_names)
        self.home_idx = random.randrange(n)
        self.away_idx = (self.home_idx + random.randrange(1, n)) % n

    def _start_match(self):
        try:
            if self.home_idx == self.away_idx:
                raise ValueError("Home and Away must be different teams.")
            seed = _rand_seed()

            # Build micro-teams like in the tests (4 fighters/side)
            def _make_team_dict(name: str, tid: int):
                color = (80 + 40 * tid, 110, 180)
                fighters = []
                for i in range(4):
                    fighters.append({
                        "fighter_id": tid * 100 + i,
                        "team_id": tid,
                        "name": f"{name[:8]}-{i}",
                        "hp": 10, "max_hp": 10,
                        "ac": 12, "str": 12, "dex": 12, "con": 12,
                        "weapon": {"name": "Dagger", "damage": "1d4", "reach": 1}
                    })
                return {"name": name, "color": color, "fighters": fighters}

            nameH = self.team_names[self.home_idx]
            nameA = self.team_names[self.away_idx]
            tH = _make_team_dict(nameH, 0)
            tA = _make_team_dict(nameA, 1)

            teamH = Team(0, tH["name"], tuple(tH["color"]))
            teamA = Team(1, tA["name"], tuple(tA["color"]))

            fighters = [fighter_from_dict({**fd, "team_id": 0}) for fd in tH["fighters"]] + \
                       [fighter_from_dict({**fd, "team_id": 1}) for fd in tA["fighters"]]

            layout_teams_tiles(fighters, GRID_W, GRID_H)
            tb = TBCombat(teamH, teamA, fighters, GRID_W, GRID_H, seed=seed)

            if hasattr(self.app, "safe_push"):
                self.app.safe_push(MatchState, app=self.app, tbcombat=tb)
            else:
                self.app.push_state(MatchState(app=self.app, tbcombat=tb))

        except Exception as e:
            self._push_msg(f"Exhibition failed:\n{e}")
