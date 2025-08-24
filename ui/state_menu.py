# ui/state_menu.py
import os
import pygame
from typing import Optional, List
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button

GRID_COLOR = (28, 30, 35)
GRID_MINOR = (24, 26, 30)
BG_DARK = (12, 12, 16)
TITLE_GLOW = (240, 240, 245)

class MenuState(UIState):
    def __init__(self):
        self.buttons: List[Button] = []
        self.font_title: Optional[pygame.font.Font] = None
        self.font_sub: Optional[pygame.font.Font] = None

    def on_enter(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()
        # Use larger sizes to mimic the screenshot
        self.font_title = pygame.font.Font(None, 64)
        self.font_sub = pygame.font.Font(None, 28)

        W, H = pygame._app_ref.WIDTH, pygame._app_ref.HEIGHT  # type: ignore[attr-defined]
        bw, bh, gap = 320, 44, 12
        x = (W - bw) // 2
        y0 = int(H * 0.38)

        def add_button(label, cb):
            rect = pygame.Rect(x, add_button.y, bw, bh)
            self.buttons.append(Button(rect, label, on_click=cb))
            add_button.y += bh + gap
        add_button.y = y0  # type: ignore[attr-defined]

        # Callbacks
        def cb_new():
            from .state_team_select import TeamSelectState
            pygame._app_ref.push_state(TeamSelectState(pygame._app_ref))  # type: ignore[attr-defined]

        def cb_load():
            from core.save import load_career
            from .state_season_hub import SeasonHubState
            from .state_message import MessageState
            path = "saves/career.json"
            if not os.path.exists(path):
                pygame._app_ref.push_state(  # type: ignore[attr-defined]
                    MessageState("No Save Found", f"Couldn't find {path}. Start a New Game first.")
                ); return
            try:
                car = load_career(path)
                # TODO: store user_team_id in save later; default to 0 for now
                pygame._app_ref.push_state(SeasonHubState(pygame._app_ref, car, user_team_id=0))  # type: ignore[attr-defined]
            except Exception as e:
                pygame._app_ref.push_state(  # type: ignore[attr-defined]
                    MessageState("Load Error", f"Failed to load save:\n{e}")
                )

        def cb_exhibition():
            from .state_exhibition_picker import ExhibitionPickerState
            pygame._app_ref.push_state(ExhibitionPickerState(pygame._app_ref))  # type: ignore[attr-defined]



        def cb_settings():
            from .state_settings import SettingsState
            pygame._app_ref.push_state(SettingsState())  # type: ignore[attr-defined]

        def cb_quit():
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        # Buttons (labels to match your screenshot)
        add_button("New Game", cb_new)
        add_button("Load Game", cb_load)
        add_button("Play Match", cb_exhibition)
        add_button("Settings", cb_settings)
        add_button("Quit", cb_quit)

    def on_exit(self) -> None:
        self.buttons.clear()

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        for b in self.buttons: b.handle_event(event)
        # keyboard: Esc quits
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        return None

    def update(self, dt: float) -> Optional["UIState"]:
        return None

    # ------- drawing helpers -------
    def _draw_grid_bg(self, surface: pygame.Surface):
        surface.fill(BG_DARK)
        w, h = surface.get_width(), surface.get_height()
        # subtle grid
        step = 32
        for x in range(0, w, step):
            pygame.draw.line(surface, GRID_MINOR if (x//step)%4 else GRID_COLOR, (x, 0), (x, h))
        for y in range(0, h, step):
            pygame.draw.line(surface, GRID_MINOR if (y//step)%4 else GRID_COLOR, (0, y), (w, y))
        # vignette
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 120), (0, 0, w, h))
        pygame.draw.rect(s, (0, 0, 0, 0), pygame.Rect(32, 32, w-64, h-64))
        surface.blit(s, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    def _draw_title(self, surface: pygame.Surface):
        # Glow-ish title
        cx = surface.get_width() // 2
        y = 90
        title = "D20 Fight Club — Manager"
        sub = "No career loaded"
        if self.font_title:
            t_img = self.font_title.render(title, True, TITLE_GLOW)
            t_rect = t_img.get_rect(center=(cx, y))
            # soft glow background
            glow = pygame.Surface((t_rect.w+60, t_rect.h+40), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255,255,255,25), glow.get_rect())
            surface.blit(glow, (t_rect.x-30, t_rect.y-20))
            surface.blit(t_img, t_rect)
        if self.font_sub:
            s_img = self.font_sub.render(sub, True, (210, 210, 215))
            s_rect = s_img.get_rect(center=(cx, y + 50))
            surface.blit(s_img, s_rect)

    # ------- main draw -------
    def draw(self, surface: pygame.Surface) -> None:
        self._draw_grid_bg(surface)
        self._draw_title(surface)
        for b in self.buttons:
            b.draw(surface)
