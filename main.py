# main.py
from __future__ import annotations
import os, traceback

# Adjust this import if your App lives elsewhere:
from ui.app import App

# Ensure App has derive_seed() for deterministic previews
from ui.seedshim import patch_app_seed
patch_app_seed(App)

def main() -> int:
    try:
        app = App()
        app.run()
        return 0
    except Exception:
        os.makedirs("saves", exist_ok=True)
        with open(os.path.join("saves", "crash.log"), "a", encoding="utf-8") as f:
            f.write("\n=== Crash ===\n")
            traceback.print_exc(file=f)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
