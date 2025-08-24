# ui/state_season_hub.py
from __future__ import annotations

class SeasonHubState:
    """
    Minimal placeholder to satisfy imports during tests.
    Your real implementation can render buttons, schedule, table, etc.
    """
    def __init__(self, *args, **kwargs) -> None:
        pass

    # Optional lifecycle hooks your app might call; harmless no-ops here.
    def enter(self) -> None: 
        pass

    def exit(self) -> None:
        pass

    def handle_event(self, event) -> bool:
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        pass
