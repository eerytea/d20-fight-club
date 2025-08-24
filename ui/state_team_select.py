# ui/state_team_select.py
from __future__ import annotations

import random
from typing import Optional, List

try:
    import pygame
except Exception:
    pygame = None  # type: ignore

from core.career import new_career
from .state_season_hub import SeasonHubState
from .state_message import MessageState


def _rand_seed() -> int:
    return random.randint(1, 2_000_000_000)


class TeamSelectState:
    """
    Very small "New Game → Pick Your Team" screen.

    Controls:
      - Up/Down: move selection
      - Enter  : confirm and start a new career with this team
      - Esc    : go back / quit (pops this state)

    It builds the actual Career on confirm so we don't waste time before the user chooses.
    """

    def __init__(self, app) -> None:
        self.app = app
        self._font = None
        self.team_names: List[str] = []
        self.selected_idx: int = 0

    # ------- lifecycle -------

    def enter(self) -> None:
        if pygame is None:
            return
        # font
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 22)

        # Create a "preview" career so we can list team names
        # (We'll build the real one on confirm with a fresh seed)
        try:
            preview = new_career(seed=self.app.seed or _rand_seed())
            self.team_names = list(preview.team_names)
        except Exception as e:
            self._push_msg(f"Couldn't build team list:\n{e}")

    def exit(self) -> None:
        pass

    # ------- events / update / draw -------

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE,):
                self.app.pop_state()
                return True
            if event.key in (pygame.K_UP,):
                self.selected_idx = (self.selected_idx - 1) % max(1, len(self.team_names))
                return True
            if event.key in (pygame.K_DOWN,):
                self.selected_idx = (self.selected_idx + 1) % max(1, len(self.team_names))
                return True
            if event.ke
