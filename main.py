import pathlib
import traceback

from ui.app import App
from ui.state_menu import MenuState


def main():
    try:
        app = App(width=1024, height=576, title="D20 Fight Club")
        app.push_state(MenuState())
        app.run()
    except Exception:
        # Minimal crash logging compatible with your saves/ folder
        pathlib.Path("saves").mkdir(exist_ok=True)
        with open("saves/crash.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise


if __name__ == "__main__":
    main()
