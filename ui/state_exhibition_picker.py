# ui/state_exhibition_picker.py
from __future__ import annotations

import random
from typing import List, Callable

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

from engine import Team, fighter_from_dict, layout_teams_tiles, TBCombat
from .state_message import MessageState
from .state_match import MatchState

GRID_W, GRID_H = 10, 8


def _rand_seed() -> int:
    return random.randint(1, 2_000_000_000)


class ExhibitionPickerState:
    """
    Pick Home/Away teams with clicks; Start Match builds TBCombat and opens MatchState.
    """

    def __init__(self, app) -> None:
        self.app = app
        self._font = None
        self.team_names: List[str] = [
            "Dragons", "Wolves", "Knights", "Rogues",
            "Mages", "Clerics", "Berserkers", "Rangers"
        ]
        self.home_idx: int = 0
        self.away_idx: int = 1
        self.edit_side: int = 0  # 0=home, 1=away

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 22)

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.pop_state()
                return True
            if event.key == pygame.K_LEFT:
                self.edit_side = 0; return True
            if event.key == pygame.K_RIGHT:
                self.edit_side = 1; return True
            if event.key == pygame.K_UP:
                self._bump(-1); return True
            if event.key == pygame.K_DOWN:
                self._bump(+1); return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._start_match(); return True
            if event.key in (pygame.K_r,):
                self._randomize(); return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # click toggles side if near labels, very simple
            mx, my = event.pos
            w, h = self.app.width, self.app.height
            left_lbl = pygame.Rect(80, 70, 120, 28)
            right_lbl = pygame.Rect(w // 2 + 40, 70, 120, 28)
            if left_lbl.collidepoint(mx, my):
                self.edit_side = 0; return True
            if right_lbl.collidepoint(mx, my):
                self.edit_side = 1; return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()
        title = self._text("Exhibition — Pick Teams", 32, bold=True)
        surface.blit(title, (w // 2 - title.get_width() // 2, 24))

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

    def _bump(self, delta: int):
        if self.edit_side == 0:
            self.home_idx = (self.home_idx + delta) % len(self.team_names)
            if self.home_idx == self.away_idx:
                self.away_idx = (self.away_idx + 1) % len(self.team_names)
        else:
            self.away_idx = (self.away_idx + delta) % len(self.team_names)
            if self.away_idx == self.home_idx:
                self.home_idx = (self.home_idx + 1) % len(self.team_names)

    # ----- start match -----

    def _start_match(self):
        try:
            if self.home_idx == self.away_idx:
                raise ValueError("Home and Away must be different teams.")
            seed = _rand_seed()

            nameH = self.team_names[self.home_idx]
            nameA = self.team_names[self.away_idx]

            def make_team_dict(name: str, tid: int):
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

            tH = make_team_dict(nameH, 0)
            tA = make_team_dict(nameA, 1)

            def build_tb() -> TBCombat:
                teamH = Team(0, tH["name"], tuple(tH["color"]))
                teamA = Team(1, tA["name"], tuple(tA["color"]))
                fighters = [fighter_from_dict({**fd, "team_id": 0}) for fd in tH["fighters"]] + \
                           [fighter_from_dict({**fd, "team_id": 1}) for fd in tA["fighters"]]
                layout_teams_tiles(fighters, GRID_W, GRID_H)
                return TBCombat(teamH, teamA, fighters, GRID_W, GRID_H, seed=seed)

            tb = build_tb()

            # Open match viewer with Reset support
            self.app.safe_push(
                MatchState,
                app=self.app,
                tbcombat=tb,
                title=f"{tH['name']} vs {tA['name']}",
                scheduled=False,
                on_result=None,
                rebuild=build_tb,
            )

        except Exception as e:
            self._push_msg(f"Exhibition failed:\n{e}")
