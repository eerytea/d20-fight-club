# main.py
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _repo_root() -> Path:
    """Return the folder containing this file (repo root)."""
    return Path(__file__).resolve().parent


def _ensure_cwd() -> None:
    """Make sure the process is running from the repo root (so relative paths work)."""
    os.chdir(_repo_root())


def _crash_log_path() -> Path:
    root = _repo_root()
    (root / "saves").mkdir(parents=True, exist_ok=True)
    return root / "saves" / "crash.log"


def _write_crash_log(exc: BaseException) -> None:
    log_path = _crash_log_path()
    with log_path.open("w", encoding="utf-8") as f:
        f.write("=== D20 Fight Club Crash Log ===\n")
        f.write(f"Python: {sys.version}\n")
        try:
            import pygame  # type: ignore

            f.write(f"Pygame: {getattr(pygame, '__version__', 'unknown')}\n")
        except Exception:
            f.write("Pygame: not imported\n")
        f.write("\nTraceback:\n")
        f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    print(f"\nCrash written to: {log_path}")


def main() -> None:
    _ensure_cwd()

    # Import here so crash logging still works if imports fail
    from ui.app import App
    from ui.state_menu import MenuState

    # Create the app and push the main menu
    app = App(title="D20 Fight Club", fps_cap=60)
    app.push_state(MenuState())  # Make sure a state is on the stack
    app.run()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:
        _write_crash_log(exc)
        # Re-raise for visibility during dev; comment this out if you prefer silent exit
        raise
