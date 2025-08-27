from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, List

class StaffRole(Enum):
    SCOUT = auto()
    COACH = auto()
    PHYSIO = auto()

@dataclass
class Staff:
    id: str
    name: str
    role: StaffRole
    club_id: str
    wage: int = 0
    contract_end_year: int = 0
    attrs: Dict[str, float] = field(default_factory=dict)  # role-specific ratings
    professionalism: float = 10.0
    adaptability: float = 10.0

# Recommended attributes per role:
# - SCOUT: {"judge_ability", "judge_potential", "region_knowledge:<id>", "race_knowledge:<race>"}
# - COACH: {"offense", "defense", "support", "tactics", "conditioning", "youth"}
# - PHYSIO: {"prevention", "treatment", "rehab", "sports_science"}

@dataclass
class ClubStaff:
    club_id: str
    staff_ids: List[str] = field(default_factory=list)
