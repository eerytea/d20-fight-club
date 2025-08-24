# ui/__init__.py
from importlib import import_module

__all__ = [
    "App",
    "MenuState",
    "TeamSelectState",
    "SeasonHubState",
    "MatchState",
    "ExhibitionPickerState",
    "MessageState",
]

def __getattr__(name: str):
    if name == "App":
        return import_module(".app", __name__).App
    if name == "MenuState":
        return import_module(".state_menu", __name__).MenuState
    if name == "TeamSelectState":
        return import_module(".state_team_select", __name__).TeamSelectState
    if name == "SeasonHubState":
        return import_module(".state_season_hub", __name__).SeasonHubState
    if name == "MatchState":
        return import_module(".state_match", __name__).MatchState
    if name == "ExhibitionPickerState":
        return import_module(".state_exhibition_picker", __name__).ExhibitionPickerState
    if name == "MessageState":
        return import_module(".state_message", __name__).MessageState
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
