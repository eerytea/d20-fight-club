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
# --- add to ui/uiutil.py ---

class Checkbox:
    def __init__(self, rect: pygame.Rect, label: str, checked: bool = False, on_toggle=None):
        self.rect = rect
        self.label = label
        self.checked = checked
        self.on_toggle = on_toggle

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.checked = not self.checked
                if self.on_toggle:
                    self.on_toggle(self.checked)

    def draw(self, surface):
        box = pygame.Rect(self.rect.x, self.rect.y, self.rect.h, self.rect.h)
        pygame.draw.rect(surface, (54,58,66), box, border_radius=4)
        pygame.draw.rect(surface, (22,24,28), box, 2, border_radius=4)
        if self.checked:
            pygame.draw.line(surface, (180,220,180), (box.x+4, box.centery), (box.right-4, box.centery), 3)
        draw_text(surface, self.label, (self.rect.x + self.rect.h + 8, self.rect.y + 2), font=FONT)

class Slider:
    def __init__(self, rect: pygame.Rect, value: float, on_change=None):
        self.rect = rect
        self.value = max(0.0, min(1.0, float(value)))
        self.on_change = on_change
        self.dragging = False

    def _set_from_x(self, x):
        t = (x - self.rect.x) / max(1, self.rect.w)
        self.value = max(0.0, min(1.0, t))
        if self.on_change:
            self.on_change(self.value)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.dragging = True
            self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])

    def draw(self, surface):
        pygame.draw.rect(surface, (50,54,62), self.rect, border_radius=8)
        pygame.draw.rect(surface, (22,24,28), self.rect, 2, border_radius=8)
        knob_x = int(self.rect.x + self.value * self.rect.w)
        pygame.draw.circle(surface, (200,200,210), (knob_x, self.rect.centery), max(6, self.rect.h//3))

class Dropdown:
    def __init__(self, rect: pygame.Rect, items: list[str], index: int = 0, on_select=None):
        self.rect = rect
        self.items = items
        self.index = max(0, min(index, len(items)-1))
        self.open = False
        self.on_select = on_select

    @property
    def value(self): return self.items[self.index]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
            elif self.open:
                # click in dropdown list
                item_h = self.rect.h
                list_rect = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.w, item_h*len(self.items))
                if list_rect.collidepoint(event.pos):
                    rel = (event.pos[1] - list_rect.y) // item_h
                    if 0 <= rel < len(self.items):
                        self.index = int(rel)
                        if self.on_select: self.on_select(self.value)
                self.open = False

    def draw(self, surface):
        pygame.draw.rect(surface, (50,54,62), self.rect, border_radius=8)
        pygame.draw.rect(surface, (22,24,28), self.rect, 2, border_radius=8)
        draw_text(surface, self.value, (self.rect.x+8, self.rect.y+6), font=FONT)
        # chevron
        pygame.draw.polygon(surface, (220,220,230), [(self.rect.right-16, self.rect.y+10),
                                                     (self.rect.right-6, self.rect.y+10),
                                                     (self.rect.right-11, self.rect.y+18)])
        if self.open:
            item_h = self.rect.h
            list_rect = pygame.Rect(self.rect.x, self.rect.bottom, self.rect.w, item_h*len(self.items))
            pygame.draw.rect(surface, (42,46,52), list_rect, border_radius=8)
            pygame.draw.rect(surface, (22,24,28), list_rect, 2, border_radius=8)
            y = list_rect.y
            for it in self.items:
                pygame.draw.line(surface, (22,24,28), (list_rect.x, y), (list_rect.right, y))
                draw_text(surface, it, (list_rect.x+8, y+6), font=FONT)
                y += item_h
