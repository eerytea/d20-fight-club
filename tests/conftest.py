# tests/conftest.py
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"  # headless
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pytest, pygame

@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()
