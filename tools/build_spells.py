# tools/build_spells.py
from __future__ import annotations
import json, re, sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

# ---- Canonical paths (edit here only if you move files) ----
SRC_XLSX = Path("data/Spells.xlsx")
OUT_JSON = Path("artifacts/spells_normalized.json")
OUT_PY   = Path("core/spell_catalog.py")

# Columns we want in the final normalized schema
TARGET_SCHEMA = [
    "name",                 # str
    "class",                # str  (Classes that can use this)
    "learn_at_level",       # int  (The level that this spell)
    "slot_type",            # int  (0=at-will/whatever you defined; adapt to your meaning)
    "tags",                 # str
    "die",                  # str  (e.g., "1d6, 5th (2d6), 11th (3d6), 17th (4d6)")
    "damage_type",          # str
    "has_save",             # bool
    "save_attr",            # str  (e.g., "DEX SAVE")
    "save_success_multiplier",  # float (e.g., 0.5 means half on save)
    "range_tiles",          # float
    "aoe_shape",            # str  (just shape/size words; visuals live in conditions_text)
    "conditions_text",      # str  (freeform: shape details, sizes, extra notes)
]

# Common column-name variants -> canonical names
COLUMN_ALIASES = {
    # name
    "spell name": "name",
    "spell": "name",
    "name": "name",

    # class
    "class": "class",
    "classes": "class",
    "classes that can use this": "class",

    # level obtained
    "level obtained": "learn_at_level",
    "learn level": "learn_at_level",
    "learn_at_level": "learn_at_level",
    "level": "learn_at_level",

    # slot type
    "slot type": "slot_type",
    "slot": "slot_type",
    "slot_type": "slot_type",

    # misc metadata
    "tags": "tags",
    "die": "die",
    "damage type": "damage_type",
    "damage_type": "damage_type",
    "has save": "has_save",
    "has_save": "has_save",
    "save attr": "save_attr",
    "save_attr": "save_attr",
    "save success multiplier": "save_success_multiplier",
    "save_success_multiplier": "save_success_multiplier",
    "range (tiles)": "range_tiles",
    "range_tiles": "range_tiles",
    "aoe shape": "aoe_shape",
    "aoe_shape": "aoe_shape",
    "conditions": "conditions_text",
    "conditions_text": "conditions_text",
}

BOOL_TRUES = {"y", "yes", "true", "t", "1", 1, True}
BOOL_FALSES = {"n", "no", "false", "f", "0", 0, False, None, ""}

def _snake(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("\n"," ").replace("\r"," ")
    s = re.sub(r"\s+", " ", s)
    return s

def _canon_col(col: str) -> str:
    k = _snake(col)
    return COLUMN_ALIASES.get(k, k)

def _to_int(x: Any, default: int = 0) -> int:
    if pd.isna(x): return default
    try: return int(str(x).strip())
    except: return default

def _to_float(x: Any, default: float = 0.0) -> float:
    if pd.isna(x): return default
    try: return float(str(x).strip())
    except: return default

def _to_bool(x: Any, default: bool = False) -> bool:
    if pd.isna(x): return default
    s = str(x).strip().lower()
    if s in {str(v).lower() for v in BOOL_TRUES}: return True
    if s in {str(v).lower() for v in BOOL_FALSES}: return False
    return default

def _normalize_row(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {k: None for k in TARGET_SCHEMA}

    # Direct mappings with type coercion
    out["name"] = str(d.get("name","")).strip()
    out["class"] = str(d.get("class","")).strip()
    out["learn_at_level"] = _to_int(d.get("learn_at_level"), 1)
    out["slot_type"] = _to_int(d.get("slot_type"), 0)
    out["tags"] = str(d.get("tags","")).strip()
    out["die"] = str(d.get("die","")).strip()
    out["damage_type"] = str(d.get("damage_type","")).strip()
    out["has_save"] = _to_bool(d.get("has_save"), False)
    out["save_attr"] = str(d.get("save_attr","")).strip()
    out["save_success_multiplier"] = _to_float(d.get("save_success_multiplier"), 0.0)
    out["range_tiles"] = _to_float(d.get("range_tiles"), 0.0)
    out["aoe_shape"] = str(d.get("aoe_shape","")).strip()

    # Conditions: only shape/size visuals should live here per your rule
    out["conditions_text"] = str(d.get("conditions_text","")).strip()

    # Minimal validation
    if not out["name"]:
        raise ValueError("Encountered a spell with empty name.")
    if not out["class"]:
        # You can choose to allow empty classes; I’ll warn here.
        pass

    return out

def load_sheet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing Excel: {path}")
    # Use first sheet or a sheet literally named "Spells"
    try:
        df = pd.read_excel(path, sheet_name="Spells")
    except Exception:
        df = pd.read_excel(path)  # first sheet fallback
    # Canonicalize columns
    df = df.rename(columns={c: _canon_col(c) for c in df.columns})
    return df

def normalize(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        d = {k: r.get(k) for k in df.columns}
        rows.append(_normalize_row(d))
    return rows

def write_json(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

HEADER = """# AUTO-GENERATED from artifacts/spells_normalized.json
# Do not edit by hand. Regenerate via:  python -m tools.build_spells
from __future__ import annotations
from typing import Any, Dict, List

# Minimal access layer to keep imports stable across the codebase.
# SPELLS: List[Dict[str, Any]] with keys:
#   name, class, learn_at_level, slot_type, tags, die, damage_type,
#   has_save, save_attr, save_success_multiplier, range_tiles, aoe_shape, conditions_text
"""

def write_catalog_py(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    # Index by lowercase name for quick lookup
    by_name = {str(r["name"]).lower(): r for r in rows}

    # Keep Python file size reasonable by dumping JSON-ish repr
    body = []
    body.append(HEADER)
    body.append(f"SPELLS: List[Dict[str, Any]] = {json.dumps(rows, indent=2, ensure_ascii=False)}\n")
    body.append(f"_SPELL_BY_NAME: Dict[str, Dict[str, Any]] = {{\n")
    for k in sorted(by_name.keys()):
        body.append(f"  {json.dumps(k)}: SPELLS[[s['name'].lower() for s in SPELLS].index({json.dumps(k)})],\n")
    body.append("}\n\n")
    body.append("def all_spells() -> List[Dict[str, Any]]:\n    return SPELLS\n\n")
    body.append("def get_spell(name: str) -> Dict[str, Any]:\n")
    body.append("    return _SPELL_BY_NAME.get(name.lower())\n\n")
    body.append("__all__ = ['SPELLS','all_spells','get_spell']\n")
    path.write_text("".join(body), encoding="utf-8")

def main(argv: List[str] | None = None) -> int:
    print(f"[build_spells] reading {SRC_XLSX}")
    df = load_sheet(SRC_XLSX)
    rows = normalize(df)

    print(f"[build_spells] writing {OUT_JSON}")
    write_json(OUT_JSON, rows)

    print(f"[build_spells] writing {OUT_PY}")
    write_catalog_py(OUT_PY, rows)

    print("[build_spells] done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
