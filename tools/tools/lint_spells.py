# tools/lint_spells.py
from __future__ import annotations
import json, sys, re
from pathlib import Path
from typing import Dict, Any, List, Tuple

ARTIFACT = Path("artifacts/spells_normalized.json")

DAMAGE_TYPES = {
    "Slashing","Piercing","Bludgeoning","Fire","Cold","Lightning","Thunder",
    "Acid","Poison","Psychic","Radiant","Necrotic","Force"
}
SAVE_ATTRS = {"STR SAVE","DEX SAVE","CON SAVE","INT SAVE","WIS SAVE","CHA SAVE","—"}
ALLOWED_AOE = {"", "Self","Line","Cone","Circle","Blast","Any two"}  # extend as needed

DIE_RX = re.compile(r"^\s*\d+d\d+(\s*,\s*\d+(?:st|nd|rd|th)\s+level\s*\(\d+d\d+\)\s*)*\.?\s*$", re.I)

REQUIRED = {
    "name","class","learn_at_level","slot_type","tags","die","damage_type",
    "has_save","save_attr","save_success_multiplier","range_tiles","aoe_shape","conditions_text"
}

def _err(msg: str) -> None:
    print(f"[lint] ERROR: {msg}")

def _warn(msg: str) -> None:
    print(f"[lint] WARN: {msg}")

def _ok(msg: str) -> None:
    print(f"[lint] OK: {msg}")

def load_rows() -> List[Dict[str,Any]]:
    if not ARTIFACT.exists():
        _err(f"Missing {ARTIFACT}. Run: python -m tools.build_spells")
        sys.exit(2)
    rows = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        _err("Artifact root must be a list.")
        sys.exit(2)
    return rows

def check_rows(rows: List[Dict[str,Any]]) -> Tuple[int,int]:
    errors = 0; warns = 0
    seen_names = set()
    for i, r in enumerate(rows):
        missing = REQUIRED - set(r.keys())
        if missing:
            errors += 1; _err(f"Row {i}: missing fields: {sorted(missing)}")
            continue

        name = str(r["name"]).strip()
        if not name:
            errors += 1; _err(f"Row {i}: empty name")
        elif name.lower() in seen_names:
            warns += 1; _warn(f"Row {i}: duplicate name '{name}' (case-insensitive)")
        seen_names.add(name.lower())

        # Numeric & enum checks
        lvl = int(r.get("learn_at_level", 0))
        if lvl < 1: errors += 1; _err(f"{name}: learn_at_level must be >=1 (got {lvl})")

        slot = int(r.get("slot_type", -999))
        if slot < 0: warns += 1; _warn(f"{name}: slot_type < 0 (got {slot})—is that intentional?")

        rng = float(r.get("range_tiles", -1))
        if rng < 0: warns += 1; _warn(f"{name}: negative range_tiles (got {rng})")

        ssm = float(r.get("save_success_multiplier", -1))
        if not (0.0 <= ssm <= 1.0):
            warns += 1; _warn(f"{name}: save_success_multiplier not in [0,1] (got {ssm})")

        dmg = str(r.get("damage_type","")).strip()
        if dmg and dmg not in DAMAGE_TYPES:
            warns += 1; _warn(f"{name}: damage_type '{dmg}' not in {sorted(DAMAGE_TYPES)}")

        save_attr = str(r.get("save_attr","")).strip()
        if save_attr and save_attr not in SAVE_ATTRS:
            warns += 1; _warn(f"{name}: save_attr '{save_attr}' not in {sorted(SAVE_ATTRS)}")

        aoe = str(r.get("aoe_shape","")).strip()
        if aoe not in ALLOWED_AOE:
            warns += 1; _warn(f"{name}: aoe_shape '{aoe}' not in {sorted(ALLOWED_AOE)}")

        die = str(r.get("die","")).strip()
        if die and not DIE_RX.match(die):
            warns += 1; _warn(f"{name}: die '{die}' not in expected pattern (check punctuation and spacing)")

        # Conditions text should only carry visuals/notes (cannot auto-check fully)
        # Keep a soft check for junk like massive paragraphs:
        cond = str(r.get("conditions_text",""))
        if len(cond) > 300:
            warns += 1; _warn(f"{name}: conditions_text very long ({len(cond)} chars)—trim to visuals/notes only")

    return errors, warns

def main() -> int:
    rows = load_rows()
    e,w = check_rows(rows)
    if e == 0:
        _ok(f"Lint passed with {w} warning(s).")
        return 0
    else:
        _err(f"Lint failed: {e} error(s), {w} warning(s).")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
