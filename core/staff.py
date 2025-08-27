from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class StaffMember:
    role: str     # 'coach' | 'scout' | 'physio'
    name: str
    rating: int   # 1..100 (rough strength)
    salary: int = 0

def make_staff(role: str, name: str, rating: int, salary: int = 0) -> Dict[str, Any]:
    return {"role": role, "name": name, "rating": int(rating), "salary": int(salary)}
