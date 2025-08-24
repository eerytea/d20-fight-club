# main.py
from ui.app import App
from ui.state_menu import MenuState

def main():
    app = App(width=1280, height=720, title="D20 Fight Club")
    app.push_state(MenuState())   # <<< make sure this line exists
    app.run()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        from pathlib import Path
        import traceback, time
        Path("saves").mkdir(parents=True, exist_ok=True)
        Path("saves/crash.log").write_text(
            f"[{time.ctime()}]\n{traceback.format_exc()}\n", encoding="utf-8"
        )
        # Try to show a polite UI message if Pygame is still alive
        try:
            from ui.state_message import MessageState
            from ui.app import App
            app = App()
            app.push_state(MessageState("Crash", f"{e}\nSee saves/crash.log"))
            app.run()
        except Exception:
            pass
        raise
