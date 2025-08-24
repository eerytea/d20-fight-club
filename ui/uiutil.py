import pygame
from typing import Tuple, Optional, Callable

pygame.font.init()
FONT = pygame.font.Font(pygame.font.get_default_font(), 20)
SMALL = pygame.font.Font(pygame.font.get_default_font(), 16)
BIG = pygame.font.Font(pygame.font.get_default_font(), 28)

def draw_text(surface: pygame.Surface, text: str, pos: Tuple[int,int], color=(230,230,235), font=FONT) -> pygame.Rect:
    img = font.render(text, True, color)
    r = img.get_rect(topleft=pos)
    surface.blit(img, r)
    return r

class Button:
    def __init__(self, rect: pygame.Rect, label: str, on_click: Optional[Callable]=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.enabled = True
        self.hover = False

    def handle_event(self, event: pygame.event.Event):
        if not self.enabled: return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.on_click:
                self.on_click()

    def draw(self, surface: pygame.Surface):
        bg = (58,62,70) if self.enabled else (40,42,48)
        if self.hover and self.enabled:
            bg = (78,84,94)
        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (22,24,28), self.rect, 2, border_radius=8)
        # center label
        img = FONT.render(self.label, True, (240,240,245))
        ir = img.get_rect(center=self.rect.center)
        surface.blit(img, ir)
