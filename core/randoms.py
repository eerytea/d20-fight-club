# core/randoms.py
from __future__ import annotations
import random, hashlib

class SeededRNG:
    """
    Deterministic random with domain separation.
    Master seed -> sub-seeds via labels like ('season',1,'week',3,'match','A_vs_B')
    """
    def __init__(self, master_seed: int | str):
        self.master_seed = str(master_seed)

    def _derive_int_seed(self, *labels) -> int:
        h = hashlib.sha256()
        h.update(self.master_seed.encode("utf-8"))
        for x in labels:
            h.update(str(x).encode("utf-8"))
        # Convert first 8 bytes to an int
        return int.from_bytes(h.digest()[:8], "big", signed=False)

    def rng(self, *labels) -> random.Random:
        return random.Random(self._derive_int_seed(*labels))

    def randint(self, a: int, b: int, *labels) -> int:
        return self.rng(*labels).randint(a, b)

    def choice(self, seq, *labels):
        return self.rng(*labels).choice(seq)