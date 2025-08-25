# ui/seedshim.py
from __future__ import annotations
import hashlib

def _mix(seed: int, label: str) -> int:
    h = hashlib.sha1(f"{seed}:{label}".encode("utf-8")).hexdigest()[:12]
    return (seed * 1_000_003) ^ int(h, 16)

def patch_app_seed(AppClass):
    """
    Monkey-patch AppClass to add derive_seed(self, label: str) -> int.
    Call once, right after importing your App class.
    """
    if hasattr(AppClass, "derive_seed"):
        return AppClass

    def derive_seed(self, label: str) -> int:
        base = getattr(self, "seed", 1337)
        return _mix(int(base), str(label))

    setattr(AppClass, "derive_seed", derive_seed)
    return AppClass
