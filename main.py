# main.py
from __future__ import annotations

import os
import sys
import traceback


def main() -> None:
    # Lazy import so heavy UI modules load only when running the game
    from ui import App

    # You can tweak title/FPS here if you like
    app = App(title="D20 Fight Club", fps_cap=60)
    app.run()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        # Allow clean quits without logging as crashes
        raise
    except Exception:
        # Never "just close"—always leave a crash log in saves/crash.log
        repo_dir = os.path.dirname(__file__)
        saves_dir = os.path.join(repo_dir, "saves")
        os.makedirs(saves_dir, exist_ok=True)

        crash_path = os.path.join(saves_dir, "crash.log")
        with open(crash_path, "a", encoding="utf-8") as f:
            f.write("\n=== Crash ===\n")
            traceback.print_exc(file=f)

        # Breadcrumb file some UIs use to hint where the last crash log lives
        try:
            with open(os.path.join(saves_dir, "last_crash.txt"), "w", encoding="utf-8") as f:
                f.write(crash_path)
        except Exception:
            pass

        # Also echo the path to the console so it's easy to find
        print(f"\nCrash written to: {crash_path}", file=sys.stderr)
        raise  # re-raise so you still see the full traceback in the terminal
