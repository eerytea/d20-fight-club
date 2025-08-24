# ui/state_match.py
from __future__ import annotations

from typing import Optional, List

try:
    import pygame
except Exception:
    pygame = None  # type: ignore


class MatchState:
    """
    Minimal match viewer for a prepared TBCombat instance.

    Expected ctor:
        MatchState(app=app, tbcombat=tb)

    Controls:
      SPACE  — step one turn
      A      — toggle auto-run
      ESC    — back to previous screen
    """
    def __init__(self, app, tbcombat) -> None:
        self.app = app
        self.tb = tbcombat
        self.auto = False
        self._font = None
        self._small = None
        self._log_cache: List[str] = []

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 22)
        self._small = pygame.font.SysFont("consolas", 16)

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.pop_state()
                return True
            if event.key == pygame.K_SPACE:
                self._step()
                return True
            if event.key in (pygame.K_a,):
                self.auto = not self.auto
                return True
        return False

    def update(self, dt: float) -> None:
        if self.auto and self.tb.winner is None:
            # Do a few turns per frame for speed
            for _ in range(10):
                if self.tb.winner is not None:
                    break
                self._step()

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()

        # Title bar
        title = self._font.render("Match", True, (255, 255, 255))  # type: ignore
        surface.blit(title, (24, 18))

        # Grid (very simple visualization)
        grid_x, grid_y = 24, 60
        cell = 40
        cols = getattr(self.tb, "grid_w", 10)
        rows = getattr(self.tb, "grid_h", 8)

        # draw cells
        for y in range(rows):
            for x in range(cols):
                rect = pygame.Rect(grid_x + x * cell, grid_y + y * cell, cell - 2, cell - 2)
                pygame.draw.rect(surface, (32, 36, 44), rect)

        # draw fighters
        for f in self.tb.fighters:
            # default to 0,0 if not laid out for any reason
            tx = getattr(f, "tx", 0)
            ty = getattr(f, "ty", 0)
            fx = grid_x + tx * cell + 4
            fy = grid_y + ty * cell + 4
            color = (100, 200, 255) if f.team_id == 0 else (255, 160, 120)
            size = cell - 10
            pygame.draw.rect(surface, color, pygame.Rect(fx, fy, size, size), border_radius=6)

            # HP bar
            max_hp = max(1, getattr(f, "hp", 1))
            hp = max(0, getattr(f, "hp", 0))
            pct = max(0.0, min(1.0, hp / float(max_hp)))
            bar_w = size
            bar_h = 6
            bar_x = fx
            bar_y = fy + size + 2
            pygame.draw.rect(surface, (50, 50, 60), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(surface, (80, 220, 120), (bar_x, bar_y, int(bar_w * pct), bar_h))

            # name
            name_surf = self._small.render(f.name, True, (230, 230, 230))  # type: ignore
            surface.blit(name_surf, (fx, fy - 14))

        # Event log (right side)
        log_x = grid_x + cols * cell + 24
        log_y = grid_y
        surface.blit(self._font.render("Log", True, (255, 255, 255)), (log_x, log_y))  # type: ignore
        log_y += 28

        # show last ~20 events
        self._log_cache = getattr(self.tb, "event_log", [])[-20:]
        for line in self._log_cache:
            txt = self._small.render(line, True, (200, 200, 200))  # type: ignore
            surface.blit(txt, (log_x, log_y))
            log_y += 18

        # Footer / status
        footer = []
        footer.append("[SPACE] step")
        footer.append("[A] auto: " + ("ON" if self.auto else "OFF"))
        footer.append("[ESC] back")
        if self.tb.winner is not None:
            footer.append(f"WINNER: {'Home' if self.tb.winner == 0 else 'Away'}")
        hint = self._small.render("  •  ".join(footer), True, (220, 220, 220))  # type: ignore
        surface.blit(hint, (24, h - 30))

    # ---- internal ----

    def _step(self):
        try:
            if self.tb.winner is None:
                self.tb.take_turn()
        except Exception as e:
            # if a step fails, show a popup and stop auto
            self.auto = False
            try:
                from .state_message import MessageState
                self.app.push_state(MessageState(text=f"Match step error:\n{e}"))
            except Exception:
                print("Match step error:", e)
