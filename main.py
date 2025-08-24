# main.py
from ui.app import App
from ui.state_menu import MenuState

def main():
    app = App(width=1280, height=720, title="D20 Fight Club")
    app.push_state(MenuState())   # <<< make sure this line exists
    app.run()

if __name__ == "__main__":
    main()
