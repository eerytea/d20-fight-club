# main.py
# main.py (add right after you import/create App)
from ui.seedshim import patch_app_seed
patch_app_seed(App)  # now app.derive_seed("preview") is available

from __future__ import annotations

import os
import traceback

from ui.app import App
from ui.state_menu import MenuState


def _write_crash_log(text: str) -> None:
    try:
        os.makedirs("saves", exist_ok=True)
        with open(os.path.join("saves", "crash.log"), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Crash written to: {os.path.abspath(os.path.join('saves','crash.log'))}")
    except Exception:
        # last resort: to console
        print(text)


def main() -> None:
    try:
        app = App(title="D20 Fight Club")
        app.push_state(MenuState())  # MenuState should tolerate being created without 'app'
        app.run()
    except Exception:
        tb = traceback.format_exc()
        _write_crash_log(tb)
        # Avoid re-raising in release runs; in dev you can uncomment:
        # raise


if __name__ == "__main__":
    main()
