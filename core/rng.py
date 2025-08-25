# core/rng.py
from __future__ import annotations

import random
from typing import Iterable, Union

# We need a stable, cross-process hash. Python's built-in hash() is salted per run,
# so we implement 64-bit FNV-1a for strings/bytes and a simple canonicalization for ints.

_FNV_OFFSET64 = 0xCBF29CE484222325
_FNV_PRIME64 = 0x100000001B3
_MASK64 = 0xFFFFFFFFFFFFFFFF


def _to_bytes(x: Union[int, str, bytes]) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, int):
        # 8 bytes little-endian unsigned representation (wraps for big ints)
        return int(x & _MASK64).to_bytes(8, "little", signed=False)
    # default: encode string
    return str(x).encode("utf-8")


def _fnv1a64(data: bytes) -> int:
    h = _FNV_OFFSET64
    for b in data:
        h ^= b
        h = (h * _FNV_PRIME64) & _MASK64
    return h


def mix(base_seed: int, *parts: Union[int, str, bytes]) -> int:
    """
    Deterministically mix a base seed with any number of parts into a 31-bit positive int.
    Produces the same result across processes and platforms.
    """
    h = _fnv1a64(_to_bytes(base_seed))
    for p in parts:
        h ^= _fnv1a64(_to_bytes(p))
        h = (h * _FNV_PRIME64) & _MASK64
    # Reduce to a positive 31-bit int and avoid 0 (Random(0) is fine, but we keep >0 for clarity)
    out = (h ^ (h >> 33)) & 0x7FFFFFFF
    return out or 1


def child_rng(base_seed: int, *parts: Union[int, str, bytes]) -> random.Random:
    """A Random() instance deterministically derived from base_seed and parts."""
    return random.Random(mix(base_seed, *parts))
