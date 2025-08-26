# engine/__init__.py
from .tbcombat import TBCombat, Team, fighter_from_dict

# --- Back-compat shim for tests that call TBCombat.take_turn() ---
# Your engine's public step method is step_action(); older tests call take_turn().
# Attach a method alias at import time so both names work.
if not hasattr(TBCombat, "take_turn"):
    def _take_turn(self):
        # Advance one atomic action; mirrors step_action()
        return self.step_action()
    setattr(TBCombat, "take_turn", _take_turn)

__all__ = ["TBCombat", "Team", "fighter_from_dict"]
