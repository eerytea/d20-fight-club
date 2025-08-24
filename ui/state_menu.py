# ui/state_menu.py
import os
import pygame
from typing import Optional
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button

class MenuState(UIState):
    def __init__(self):
        self.buttons = []

    def on_enter(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()

        W, H = pygame._app_ref.WIDTH, pygame._app_ref.HEIGHT  # type: ignore[attr-defined]
        x, y0, bw, bh, gap = 60, 120, 260, 48, 14

        def add_button(label, cb):
            rect = pygame.Rect(x, add_button.y, bw, bh)
            self.buttons.append(Button(rect, label, on_click=cb))
            add_button.y += bh + gap
        add_button.y = y0  # type: ignore[attr-defined]

        # Callbacks
        def cb_new():
            from .state_team_select import TeamSe
