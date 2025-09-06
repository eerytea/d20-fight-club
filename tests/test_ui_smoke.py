# tests/test_ui_smoke.py
import pygame
from ui.app import App
from ui.state_menu import MenuState
from ui.state_team_select import TeamSelect
from ui.state_schedule import ScheduleState
from ui.state_table import TableState

def _tick(state, frames=2):
    for _ in range(frames):
        state.update(0.016)
        state.draw(state.app.screen)
        pygame.display.flip()

def test_main_menu_smoke():
    pygame.init()
    try:
        app = App(width=640, height=360, title="smoke")
        st = MenuState(app)
        _tick(st, 2)
    finally:
        pygame.quit()

def test_team_select_smoke():
    pygame.init()
    try:
        app = App(width=640, height=360, title="smoke")
        st = TeamSelect(app)
        _tick(st, 2)
    finally:
        pygame.quit()

def test_schedule_table_smoke():
    pygame.init()
    try:
        app = App(width=640, height=360, title="smoke")
        sch = ScheduleState(app)
        tbl = TableState(app)
        _tick(sch, 1); _tick(tbl, 1)
    finally:
        pygame.quit()
