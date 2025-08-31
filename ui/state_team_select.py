# ui/state_team_select.py
from __future__ import annotations
import pygame
from typing import Any, Dict, List, Optional, Tuple
from core.constants import RACE_DISPLAY

def _pretty(s: Any) -> str:
    if s is None: return "-"
    t = str(s)
    if "_" in t: t = t.replace("_", " ")
    return t.title()

def _short_name(full: str) -> str:
    if not full: return "-"
    parts = str(full).split()
    return parts[0] if len(parts)==1 else f"{parts[0]} {parts[-1][0]}."

class TeamSelect:
    def __init__(self, career):
        self.car = career
        self.font = pygame.font.SysFont("Inter", 18)
        self.small = pygame.font.SysFont("Inter", 16)
        self.title_font = pygame.font.SysFont("Inter", 24, bold=True)

        self.rect = pygame.Rect(40, 40, 960, 580)
        self.scroll = 0
        self.rows_per_page = 6

    def _teams(self) -> List[Dict[str, Any]]:
        return getattr(self.car, "teams", [])

    def draw(self, screen):
        pygame.draw.rect(screen, (30,32,38), self.rect, border_radius=12)
        pygame.draw.rect(screen, (22,24,28), self.rect, width=2, border_radius=12)

        title = self.title_font.render("Team Select", True, (235,235,240))
        screen.blit(title, (self.rect.x + 16, self.rect.y + 12))

        y0 = self.rect.y + 52
        teams = self._teams()
        x = self.rect.x + 16
        y = y0

        card_w, card_h = 300, 120
        gap = 18

        for i,t in enumerate(teams):
            card = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(screen, (40,42,50), card, border_radius=10)
            pygame.draw.rect(screen, (22,24,28), card, width=2, border_radius=10)

            team_name = t.get("name", f"Team {t.get('tid',i)}")
            screen.blit(self.font.render(team_name, True, (230,230,236)), (card.x+12, card.y+10))

            roster = t.get("fighters", [])  # keep data key
            # Show Players in the UI text
            screen.blit(self.small.render(f"Players: {len(roster)}", True, (200,202,212)), (card.x+12, card.y+40))

            # quick peek row
            peek_y = card.y + 70
            px = card.x + 12
            for j, p in enumerate(roster[:4]):
                nm = _short_name(p.get("name", f"P{j+1}"))
                cls = _pretty(p.get("class", "-"))
                screen.blit(self.small.render(f"{nm} — {cls}", True, (210,212,220)), (px, peek_y))
                peek_y += 18

            x += card_w + gap
            if (i+1) % 3 == 0:
                x = self.rect.x + 16
                y += card_h + gap
