# ui/state_exhibition.py
import pygame
from typing import Optional, List
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button

from core.career import new_career
from core.sim import GRID_W, GRID_H  # reuse same grid dims
from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles

class ExhibitionState(UIState):
    def __init__(self, app):
        self.app = app
        self.buttons: List[Button] = []
        self.result: Optional[str] = None

    def on_enter(self) -> None:
        W = self.app.WIDTH
        self.buttons = [
            Button(pygame.Rect(24, 24, 120, 40), "Back", on_click=self._back),
            Button(pygame.Rect(24+140, 24, 160, 40), "Play Again", on_click=self._again),
        ]
        self._run_match()

    def on_exit(self) -> None:
        self.buttons.clear()

    def _back(self):
        self.app.pop_state()

    def _again(self):
        self._run_match()

    def _run_match(self):
        # make two random teams from a tiny career and pit top4 vs top4
        car = new_career(seed=9999, team_count=20)
        H_id, A_id = 0, 1
        tH = Team(H_id, car.team_names[H_id], tuple(car.team_colors[H_id]))
        tA = Team(A_id, car.team_names[A_id], tuple(car.team_colors[A_id]))
        # pick top4 by stored 'ovr'
        def top4(tid): 
            return sorted(car.rosters[tid], key=lambda f: f.get("ovr", 50), reverse=True)[:4]
        fighters = [fighter_from_dict({**fd, "team_id": H_id}) for fd in top4(H_id)] + \
                   [fighter_from_dict({**fd, "team_id": A_id}) for fd in top4(A_id)]
        layout_teams_tiles(fighters, GRID_W, GRID_H)
        combat = TBCombat(tH, tA, fighters, GRID_W, GRID_H, seed=1234)

        for _ in range(1200):
            if combat.winner is not None:
                break
            combat.take_turn()
        if combat.winner == 0:
            self.result = f"Winner: {tH.name}"
        elif combat.winner == 1:
            self.result = f"Winner: {tA.name}"
        else:
            self.result = "Draw"

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        for b in self.buttons:
            b.handle_event(event)
        return None

    def update(self, dt: float) -> Optional["UIState"]:
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        draw_text(surface, "Exhibition Match", (24, 24), font=BIG)
        for b in self.buttons:
            b.draw(surface)
        draw_text(surface, self.result or "Running...", (24, 96), font=FONT)
        draw_text(surface, "Note: This is a quick auto-sim. A Watchable Match Viewer can be added next.", (24, 132), font=FONT)
