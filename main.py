from ui.app import App
from ui.state_menu import MenuState

def main():
    app = App()
    app.push_state(MenuState())
    app.run()

if __name__ == "__main__":
    main()
