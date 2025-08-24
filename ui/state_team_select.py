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

        y = 90
        for i, name in enumerate(self.team_names):
            label = f"> {name}" if i == self.selected_idx else f"  {name}"
            color = (240, 240, 240) if i == self.selected_idx else (180, 180, 180)
            txt = self._font.render(label, True, color)  # type: ignore
            surface.blit(txt, (48, y))
            y += 28

        hint = self._text("UP/DOWN = navigate  |  ENTER = confirm  |  ESC = back", 18)
        surface.blit(hint, (24, h - 36))

    # ------- internal helpers -------

    def _text(self, s: str, size: int, bold: bool = False):
        ft = pygame.font.SysFont("consolas", size, bold=bold)  # type: ignore
        return ft.render(s, True, (255, 255, 255))

    def _push_msg(self, text: str):
        try:
            self.app.push_state(MessageState(text=text))
        except Exception:
            print(text)

    def _confirm_new_game(self):
        try:
            if not self.team_names:
                raise ValueError("No teams available.")
            team_id = int(self.selected_idx)
            seed = self.app.seed or _rand_seed()

            # Build a fresh career for the actual save/game
            career = new_career(seed=seed)
            career.user_team_id = team_id

            if not hasattr(self.app, "data"):
                self.app.data = {}
            self.app.data["career"] = career

            # Go to the season hub
            if hasattr(self.app, "safe_replace"):
                self.app.safe_replace(SeasonHubState, app=self.app, career=career)
            else:
                self.app.push_state(SeasonHubState(app=self.app, career=career))
        except Exception as e:
            self._push_msg(f"New Game failed:\n{e}")
