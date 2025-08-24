# ui/state_message.py
from __future__ import annotations

from typing import Optional, List

try:
    import pygame
except Exception:
    pygame = None  # type: ignore


class MessageState:
    """
    Simple popup message.

    Controls:
      - ENTER / ESC: close
      - Mouse click: close
    Usage:
      app.push_state(MessageState(app=self, text="Hello"))
    """

    def __init__(self, app, text: str, on_close: Optional[callable] = None) -> None:
        self.app = app
        self.text = text
        self.on_close = on_close
        self._font = None
        self._small = None

    # ----- lifecycle -----

    def enter(self) -> None:
        if pygame is None:
            return
        pygame.font.init()
        self._font = pygame.font.SysFont("consolas", 22)
        self._small = pygame.font.SysFont("consolas", 16)

    def exit(self) -> None:
        if callable(self.on_close):
            try:
                self.on_close()
            except Exception:
                pass

    # ----- events / update / draw -----

    def handle_event(self, event) -> bool:
        if pygame is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.app.pop_state()
                return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.app.pop_state()
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        if pygame is None:
            return
        w, h = surface.get_size()

        # Dim background
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        # Message box
        box_w = min(800, int(w * 0.8))
        box_h = min(400, int(h * 0.6))
        box_x = (w - box_w) // 2
        box_y = (h - box_h) // 2

        pygame.draw.rect(surface, (28, 32, 40), (box_x, box_y, box_w, box_h), border_radius=12)
        pygame.draw.rect(surface, (70, 80, 95), (box_x, box_y, box_w, box_h), width=2, border_radius=12)

        # Title
        title = self._font.render("Message", True, (255, 255, 255))  # type: ignore
        surface.blit(title, (box_x + 16, box_y + 12))

        # Body text (wrapped)
        lines = _wrap_text(self.text, self._font, box_w - 32)  # type: ignore
        y = box_y + 52
        for ln in lines[:14]:  # cap lines so we don't overflow
            surf = self._font.render(ln, True, (220, 220, 220))  # type: ignore
            surface.blit(surf, (box_x + 16, y))
            y += 26

        # Footer hint
        hint = self._small.render("ENTER / ESC to close", True, (200, 200, 200))  # type: ignore
        surface.blit(hint, (box_x + 16, box_y + box_h - 28))


# --- helpers ---

def _wrap_text(text: str, font, max_width: int) -> List[str]:
    """Very small word-wrapper using pygame font metrics."""
    if not text:
        return []
    parts = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: List[str] = []
    for para in parts:
        words = para.split(" ")
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= max_width:
                line = test
            else:
                if line:
                    out.append(line)
                line = w
        if line:
            out.append(line)
    return out
