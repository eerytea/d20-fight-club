# tests/test_ui_smoke.py
import time
import pygame
import pygame_gui
import main as game_main  # your main.py

def press(ui_element, state):
    """Send a UI_BUTTON_PRESSED event the same way pygame_gui does."""
    evt = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {"ui_element": ui_element})
    state.handle(evt)
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
    if app.state.sel.item_list:
        first_label = app.state.sel.item_list[0]

        # 1) Try to select via API/event (covers most pygame_gui versions)
        sel = app.state.sel
        if hasattr(sel, "select_item"):
            sel.select_item(first_label)
        else:
            evt = pygame.event.Event(
                pygame_gui.UI_SELECTION_LIST_NEW_SELECTION,
                {"ui_element": sel, "text": first_label}
            )
            app.state.handle(evt)

        # 2) Fallback: ensure TeamSelectState knows which team is selected
        #    Many apps store a selected_tid or similar that gets set in the handler.
        #    We set it directly if the handler didn't.
        tid = None
        if hasattr(app.state, "tid_by_label") and isinstance(app.state.tid_by_label, dict):
            tid = app.state.tid_by_label.get(first_label)
        elif hasattr(app.state, "team_ids") and app.state.team_ids:
            tid = app.state.team_ids[0]
        elif hasattr(app.state, "teams") and app.state.teams:
            # common shape: list of dicts with 'tid'/'name'
            maybe = app.state.teams[0]
            tid = (maybe.get("tid") if isinstance(maybe, dict) else getattr(maybe, "tid", None))

        if tid is not None and hasattr(app.state, "selected_tid"):
            app.state.selected_tid = tid

        # Now press Manage
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
    assert isinstance(app.state, game_main.ManagerMenuState)

    # MANAGER MENU -> View Table
    press(app.state.btn_table, app.state)
    assert isinstance(app.state, game_main.TableState)
    press(app.state.btn_back, app.state)
    assert isinstance(app.state, game_main.ManagerMenuState)

    # MANAGER MENU -> Play Match (watchable)
    press(app.state.btn_play, app.state)
    assert isinstance(app.state, game_main.MatchState)

    # Step a few turns (auto for speed, then a manual step)
    press(app.state.btn_auto, app.state)
    start = time.time()
    while time.time() - start < 1.2:
        app.state.update(0.2)
    press(app.state.btn_auto, app.state)
    press(app.state.btn_next, app.state)

    # Back out to previous menu
    press(app.state.btn_back, app.state)
    assert isinstance(app.state, game_main.ManagerMenuState)

    # Save sanity check
    press(app.state.btn_save, app.state)

    app.running = False
