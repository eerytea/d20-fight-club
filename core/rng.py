from __future__ import annotations
import hashlib
import random

def int_from_str(s: str, bits: int = 48) -> int:
    """Stable non-crypto hash -> int."""
    h = hashlib.sha1(s.encode("utf-8")).hexdigest()
    return int(h[:bits // 4], 16)

def mix(seed: int, *labels: str) -> int:
    """Mix a base seed with any number of string labels deterministically."""
    cur = int(seed)
    for lab in labels:
        cur = (cur * 1_000_003) ^ int_from_str(f"{cur}:{lab}")
        cur &= (1 << 63) - 1  # keep positive 63-bit
    return cur

def child_seed(parent_seed: int, label: str) -> int:
    return mix(parent_seed, label)

def child_rng(parent_seed: int, label: str) -> random.Random:
    return random.Random(child_seed(parent_seed, label))
