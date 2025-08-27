# tests/conftest.py
from __future__ import annotations
import os

# Run pygame tests headlessly (no window pops up)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
