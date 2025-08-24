# tests/test_ui_smoke.py
import pygame
import pygame_gui
import time

import main as game_main  # your main.py

def press(ui_element, state):
    """Send a UI_BUTTON_PRESSED event to the current state."""
    evt = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {"ui_element": ui_element})
    state.handle(evt)
    # let manager process and update
    state.update(0.016)

def test_main_flow_smoke():
    app = game_main.App()
    app.apply_resolution((800, 600))  # smaller, faster
    app.state.update(0.016)

    # MAIN MENU -> New Game (creates league) -> Team Select
    assert isinstance(app.state, game_main.MenuState)
    press(app.state.btn_new, app.state)
    assert isinstance(app.state, game_main.TeamSelectState)

    # TEAM SELECT -> Manage This Team -> Manager Menu
    # pick first team in list
    # selection lists use text labels; call set_current_selection directly:
    if app.state.sel.item_list:
        first_label = app.state.sel.item_list[0]
        # Robust selection across pygame_gui versions:
    sel = app.state.sel
    if hasattr(sel, "select_item"):
    sel.select_item(first_label)
    else:
    # Fallback: synthesize the selection event
    evt = pygame.event.Event(pygame_gui.UI_SELECTION_LIST_NEW_SELECTION, {
        "ui_element": sel,
        "text": first_label
    })
    app.state.handle(evt)
        press(app.state.btn_manage, app.state)
    assert isinstance(app.state, game_main.ManagerMenuState)

    # MANAGER MENU -> View Roster
    press(app.state.btn_ros, app.state)
    assert isinstance(app.state, game_main.RosterState)

    # ROSTER -> Back -> Manager Menu
    press(app.state.btn_back, app.state)
    assert isinstance(app.state, game_main.ManagerMenuState)

    # MANAGER MENU -> View Schedule
    press(app.state.btn_sched, app.state)
    assert isinstance(app.state, game_main.ScheduleState)
    press(app.state.btn_back, app.state)

    # MANAGER MENU -> View Table
    press(app.state.btn_table, app.state)
    assert isinstance(app.state, game_main.TableState)
    press(app.state.btn_back, app.state)

    # MANAGER MENU -> Play Match (your fixture)
    press(app.state.btn_play, app.state)
    assert isinstance(app.state, game_main.MatchState)

    # Step a few turns (auto mode on for speed)
    press(app.state.btn_auto, app.state)  # Auto: ON
    # Run for ~5 seconds simulated time
    start = time.time()
    while time.time() - start < 1.5:
        app.state.update(0.2)
    # Turn off auto and take a manual step
    press(app.state.btn_auto, app.state)
    press(app.state.btn_next, app.state)

    # Back out to menu tree
    press(app.state.btn_back, app.state)
    # Depending on scheduled/exhibition we go to ManagerMenuState or MenuState
    assert isinstance(app.state, (game_main.ManagerMenuState, game_main.MenuState))

    # If we’re in Manager Menu, hit Save Game (sanity check)
    if isinstance(app.state, game_main.ManagerMenuState):
        press(app.state.btn_save, app.state)

    # No exceptions == pass
    app.running = False
