# core/ratings.py
from __future__ import annotations
from typing import Dict

AGE_XP_MULT = [(18,23,1.25),(24,28,1.00),(29,200,0.75)]
TRAIT_MULT = {"Bad":0.85,"Normal":1.00,"Star":1.10,"Superstar":1.20}

def ovr_from_stats(stats: Dict[str,int]) -> int:
    # light-weight composite; tweak later
    # weights emphasize physicals slightly for baseline balance
    weights = {"str":1.0,"dex":1.1,"con":1.1,"int":0.9,"wis":0.9,"cha":1.0}
    num = sum(stats.get(k,10)*w for k,w in weights.items())
    den = sum(weights.values())
    return max(30, min(99, int(round((num/den)*3))))  # map ~8-18 into ~30-99

def age_xp_mult(age: int) -> float:
    for lo, hi, m in AGE_XP_MULT:
        if lo <= age <= hi:
            return m
    return 1.0

def dev_trait_mult(trait: str) -> float:
    return TRAIT_MULT.get(trait, 1.0)

def project_potential_l20(stats: Dict[str,int]) -> int:
    # very simple: +2 ASI twice (like 5e-ish) to the best stat under 20
    s = stats.copy()
    for _ in range(2):
        best = max(s, key=lambda k: s[k])
        if s[best] < 20:
            s[best] = min(20, s[best]+2)
    return ovr_from_stats(s)
