# tests/test_ui_smoke.py
import pygame

def test_imports_and_minimal_run():
    from ui.app import App
    from ui.state_menu import MenuState

    app = App(width=640, height=400, title="Smoke")
    app.push_state(MenuState())

    # Tick a handful of frames in headless mode
    for _ in range(5):
        for event in pygame.event.get():
            pass
        st = app.state
        assert st is not None
        st.update(1/60)
        app.screen.fill((0, 0, 0))
        st.draw(app.screen)
        pygame.display.flip()

    pygame.quit()
