# ui/state_team_select.py
from __future__ import annotations

import random
from typing import List, Optional

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

from core.career import new_career
from .state_season_hub import SeasonHubState  # placeholder or your real hub
from .state_message import MessageState


def _rand_seed() -> int:
    return random.randint(1, 2_000_000_000)


class TeamSelectState:
    """
    Minimal "New Game → pick your team" screen.

    Controls:
      UP/DOWN  — select team
      ENTER    — confirm
      ESC      — back
    """

    def __init__(self, app) -> None:
        self.app = app
        self._font = None
        self.team_names: List[str] = []
        self.selected_idx: int = 0

    # ----- lifecycle -----

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 22)

        try:
            # build a preview career just to fetch team names
            preview = new_career(seed=self.app.seed or _rand_seed())
            self.team_names = list(preview.team_names)
        except Exception as e:
            self._push_msg(f"Couldn't build team list:\n{e}")

    def exit(self) -> None:
        pass

    # ----- events / update / draw -----

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.pop_state()
                return True
            if event.key == pygame.K_UP:
                if self.team_names:
                    self.selected_idx = (self.selected_idx - 1) % len(self.team_names)
                return True
            if event.key == pygame.K_DOWN:
                if self.team_names:
                    self.selected_idx = (self.selected_idx + 1) % len(self.team_names)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_new_game()
                return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()
        title = self._text("Pick Your Team", 32, bold=True)
        surface.blit(title, (24, 24))

        y = 100
        for i, name in enumerate(self.team_names):
            selected = (i == self.selected_idx)
            prefix = "> " if selected else "  "
            color = (240, 240, 240) if selected else (180, 180, 180)
            txt = self._font.render(prefix + name, True, color)  # type: ignore
            surface.blit(txt, (64, y))
            y += 28

        hint = self._text("UP/DOWN select  •  ENTER confirm  •  ESC back", 18)
        surface.blit(hint, (24, h - 36))

    # ----- internals -----

    def _text(self, s: str, size: int, bold: bool = False):
        ft = pygame.font.SysFont("consolas", size, bold=bold)  # type: ignore
        return ft.render(s, True, (255, 255, 255))

    def _push_msg(self, text: str):
        try:
            self.app.push_state(MessageState(app=self.app, text=text))
        except Exception:
            print(text)

    def _confirm_new_game(self):
        try:
            if not self.team_names:
                raise ValueError("No teams to choose from.")
            team_id = int(self.selected_idx)
            seed = self.app.seed or _rand_seed()

            # fresh career for the run
            career = new_career(seed=seed)
            career.user_team_id = team_id

            # stash in app
            self.app.data["career"] = career

            # go to season hub
            if hasattr(self.app, "safe_replace"):
                self.app.safe_replace(SeasonHubState, app=self.app, career=career)
            else:
                self.app.push_state(SeasonHubState(app=self.app, career=career))
        except Exception as e:
            self._push_msg(f"New Game failed:\n{e}")
