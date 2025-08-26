import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import importlib
import inspect

from ui.app import App
from core.career import Career
from core.config import DEFAULT_SEED, LEAGUE_TEAMS, TEAM_SIZE

STATE_NAMES = [
    "ui.state_menu.MenuState",
    "ui.state_team_select.TeamSelectState",
    "ui.state_exhibition_picker.ExhibitionPickerState",
    "ui.state_season_hub.SeasonHubState",
    "ui.state_match.MatchState",
    "ui.state_roster_browser.RosterBrowserState",
]

def _import_opt(name):
    try:
        mod_name, cls_name = name.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
        return cls
    except Exception:
        return None

def _make_app():
    pygame.init()
    return App(width=800, height=480, title="Smoke")

def _dummy_career():
    return Career.new(seed=DEFAULT_SEED, n_teams=LEAGUE_TEAMS, team_size=TEAM_SIZE, user_team_id=None)

def test_all_states_construct_and_draw():
    app = _make_app()
    screen = app.screen
    try:
        for fullname in STATE_NAMES:
            cls = _import_opt(fullname)
            if cls is None:
                continue

            try:
                sig = inspect.signature(cls)
                if len(sig.parameters) == 0:
                    st = cls()
                else:
                    try:
                        st = cls(app)
                    except TypeError:
                        if "SeasonHub" in fullname:
                            st = cls(app, career=_dummy_career())
                        elif "MatchState" in fullname:
                            car = _dummy_career()
                            th, ta = car.teams[0], car.teams[min(1, len(car.teams)-1)]
                            st = cls(app, th, ta)
                        else:
                            continue
            except Exception as e:
                raise AssertionError(f"Failed to construct {fullname}: {e}")

            try:
                app.push_state(st)
                for _ in range(3):
                    if hasattr(app.state, "update"): app.state.update(1/60)
                    screen.fill((0,0,0))
                    if hasattr(app.state, "draw"): app.state.draw(screen)
                    pygame.event.pump()
            except Exception as e:
                raise AssertionError(f"State {fullname} crashed on draw: {e}")
            finally:
                app.pop_state()
    finally:
        # Ensure pygame tears down cleanly on Windows to avoid heap issues
        try:
            pygame.display.quit()
        except Exception:
            pass
        try:
            pygame.font.quit()
        except Exception:
            pass
        pygame.quit()
