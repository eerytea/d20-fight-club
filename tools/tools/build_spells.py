# tools/build_spells.py
"""
Builds spell catalog & caps from data/Spells.xlsx.

Outputs:
  - core/spell_catalog.py
  - artifacts/spells_normalized.json
  - artifacts/spell_slots_adjusted.csv
  - artifacts/training_order.csv

Column expectations in Spells.xlsx (single sheet or first sheet):
  Spell (name), Class, Level (0–9; 0 = cantrip),
  Saving Throw (non-empty => has save),
  Training (formatted like 'DPS:AOE', 'DPS:Ranged', 'Tank:Control', etc.)
Notes:
  - Uses class alias map Bard->Skald, Cleric->War Priest, Ranger->Stalker, Paladin->Crusader.
  - Half-on-save rule: if has save and Level > 4 => half_on_save=True.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd

# -------- Paths
ROOT = Path(__file__).resolve().parents[1]
DATA_XLSX = ROOT / "data" / "Spells.xlsx"
ARTIFACTS = ROOT / "artifacts"
CORE = ROOT / "core"
OUT_PY = CORE / "spell_catalog.py"
ARTIFACTS.mkdir(exist_ok=True)

# -------- Class aliasing (must match runtime mapping in classes.py)
CLASS_ALIASES = {
    "Barbarian": "Berserker",
    "Bard": "Skald",
    "Cleric": "War Priest",
    "Ranger": "Stalker",
    "Paladin": "Crusader",
}
def norm_class(name: str) -> str:
    nm = (name or "").strip()
    cap = nm[:1].upper() + nm[1:]
    return CLASS_ALIASES.get(cap, cap)

# -------- Load and normalize sheet
assert DATA_XLSX.exists(), f"Missing {DATA_XLSX}"
sheets = pd.read_excel(DATA_XLSX, sheet_name=None)
df = list(sheets.values())[0].copy()  # first sheet wins
df.columns = [c.strip() for c in df.columns]

# Required-ish columns
colmap = {
    "Spell": None,
    "Class": None,
    "Level": None,
    "Saving Throw": None,
    "Training": None,
}
for k in list(colmap):
    if k in df.columns: colmap[k] = k

# Try some fallbacks
if colmap["Spell"] is None:
    for alt in ["Name", "Spell Name"]:
        if alt in df.columns: colmap["Spell"] = alt; break
if colmap["Level"] is None:
    for alt in ["Lvl", "Spell Level", "Circle", "Tier"]:
        if alt in df.columns: colmap["Level"] = alt; break

# Minimal check
need = ["Spell", "Class", "Level"]
missing = [k for k in need if colmap[k] is None]
if missing:
    raise ValueError(f"Spells.xlsx is missing required columns: {missing}")

# Normalize fields
df["_spell"] = df[colmap["Spell"]].astype(str).str.strip()
df["_class"] = df[colmap["Class"]].astype(str).map(norm_class)
df["_level"] = pd.to_numeric(df[colmap["Level"]], errors="coerce").fillna(0).astype(int)
df["_has_save"] = False
if colmap["Saving Throw"] is not None:
    has = df[colmap["Saving Throw"]].astype(str).str.strip().str.lower()
    df["_has_save"] = ~has.isin(["", "none", "n/a", "na", "-", "—"])

# Parse training "Position:Role"
df["_position"] = ""
df["_role"] = ""
if colmap["Training"] is not None:
    parts = df[colmap["Training"]].astype(str).str.split(":", n=1, expand=True)
    if parts.shape[1] == 2:
        df["_position"] = parts[0].fillna("").str.strip()
        df["_role"] = parts[1].fillna("").str.strip()
    else:
        df["_role"] = df[colmap["Training"]].fillna("").astype(str).str.strip()

# half_on_save rule
df["_half_on_save"] = df["_has_save"] & (df["_level"] > 4)

# -------- Build SLOT_CAPS by (class, spell level) counting distinct spells
counts = (
    df.groupby(["_class", "_level"])["_spell"]
      .nunique()
      .reset_index(name="available_spells")
)

# dict: {Class: {spell_level: available_spells}}
slot_caps: Dict[str, Dict[int, int]] = {}
for _, row in counts.iterrows():
    c = row["_class"]; lvl = int(row["_level"]); n = int(row["available_spells"])
    slot_caps.setdefault(c, {})[lvl] = n

# -------- Normalized list for runtime (and JSON export)
spells_norm: List[Dict[str, Any]] = []
for _, r in df.iterrows():
    spells_norm.append({
        "spell": r["_spell"],
        "class": r["_class"],
        "level": int(r["_level"]),
        "role": r["_role"],
        "position": r["_position"],
        "has_save": bool(r["_has_save"]),
        "half_on_save": bool(r["_half_on_save"]),
    })

# -------- Training-order CSV (Role, Position, Class, then Level, then Spell)
training_sorted = pd.DataFrame(spells_norm).sort_values(
    by=["role", "position", "class", "level", "spell"],
    ascending=[True, True, True, True, True]
)
training_sorted.to_csv(ARTIFACTS / "training_order.csv", index=False)

# -------- Spell slots adjusted CSV (if you keep base tables elsewhere, this is for QA)
# We just dump the slot_caps into a flat CSV for simple inspection.
cap_rows = []
for cls, lvmap in sorted(slot_caps.items()):
    for lvl, cap in sorted(lvmap.items()):
        cap_rows.append({"class": cls, "level": lvl, "proposed_slots": int(cap)})
pd.DataFrame(cap_rows).to_csv(ARTIFACTS / "spell_slots_adjusted.csv", index=False)

# -------- JSON export of normalized spells
with open(ARTIFACTS / "spells_normalized.json", "w", encoding="utf-8") as f:
    json.dump(spells_norm, f, indent=2)

# -------- Emit Python module used at runtime
catalog_py = [
    "# AUTO-GENERATED by tools/build_spells.py -- DO NOT EDIT BY HAND",
    "from __future__ import annotations",
    "",
    "# SLOT_CAPS: caps each spell-level's slots to number of distinct spells available",
    f"SLOT_CAPS = {json.dumps(slot_caps, indent=2, sort_keys=True)}",
    "",
    "# SPELLS: normalized list used by training/learn logic & combat flags",
    f"SPELLS = {json.dumps(spells_norm, indent=2)}",
    "",
]
OUT_PY.write_text("\n".join(catalog_py), encoding="utf-8")
print(f"Wrote {OUT_PY}")
print("Done.")
