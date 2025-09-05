
"""
tools/build_spells.py
Reads data/Spells.xlsx and emits:
  - core/spell_catalog.py  (SLOT_CAPS + SPELLS with fields from the sheet)
  - artifacts/spells_normalized.json
  - artifacts/spell_slots_adjusted.csv
  - artifacts/training_order.csv

Columns expected (fuzzy, case-insensitive):
  'Spell Name', 'Class', 'Level Obtained' (or 'Level obtaining'), 'Slot type',
  optional: 'Tags', 'Die', 'Damage type', 'Save type', 'Range', 'AOE Shape', 'Conditions', 'Training block'
"""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "Spells.xlsx"
ART = ROOT / "artifacts"
CORE = ROOT / "core"
ART.mkdir(exist_ok=True)
CORE.mkdir(exist_ok=True)

CLASS_ALIASES = {
    "Barbarian": "Berserker",
    "Bard": "Skald",
    "Cleric": "War Priest",
    "Ranger": "Stalker",
    "Paladin": "Crusader",
}
def norm_class(name: str) -> str:
    nm = (name or "").strip()
    if not nm: return ""
    cap = nm[:1].upper() + nm[1:]
    return CLASS_ALIASES.get(cap, cap)

def find_col_by_keywords(cols, keywords):
    for c in cols:
        nm = str(c).strip().lower()
        if all(k in nm for k in keywords):
            return c
    return None

def split_classes(val):
    if pd.isna(val): return []
    parts = re.split(r'[,/;]+', str(val))
    return [p.strip() for p in parts if p.strip()]

def parse_training_block(val):
    out = []
    if pd.isna(val): return out
    for part in str(val).split(","):
        chunk = part.strip()
        if not chunk: continue
        if ":" in chunk:
            pos, role = chunk.split(":", 1)
            out.append({"position": pos.strip(), "role": role.strip()})
        else:
            out.append({"position": "", "role": chunk.strip()})
    return out

COMMON_CONDS = [
    "paralyzed","blinded","frightened","stunned","restrained","prone",
    "poisoned","grappled","incapacitated","charmed","deafened","invisible",
    "poison","fear"
]
def extract_conditions(txt):
    found = set()
    if not isinstance(txt, str):
        return []
    low = txt.lower()
    for token in COMMON_CONDS:
        if token in low:
            if token == "poison": found.add("poisoned")
            elif token == "fear": found.add("frightened")
            else: found.add(token)
    return sorted(found)

def parse_tiles(val):
    if pd.isna(val): return None
    m = re.search(r'\d+', str(val).strip())
    return int(m.group()) if m else None

def main():
    assert SRC.exists(), f"Missing {SRC}"
    sheets = pd.read_excel(SRC, sheet_name=None)
    df = list(sheets.values())[0].copy()
    cols = list(df.columns)

    C_SPELL = find_col_by_keywords(cols, ["spell","name"]) or find_col_by_keywords(cols, ["spell"])
    C_CLASS = find_col_by_keywords(cols, ["class"])
    C_LVL_OBT = (find_col_by_keywords(cols, ["level","obtain"]) 
                 or find_col_by_keywords(cols, ["level","gained"])
                 or find_col_by_keywords(cols, ["level","obtaining"]))
    C_SLOT = find_col_by_keywords(cols, ["slot","type"]) or find_col_by_keywords(cols, ["slot"])
    C_TAGS = find_col_by_keywords(cols, ["tag"])
    C_DIE = find_col_by_keywords(cols, ["die"])
    C_DMG = find_col_by_keywords(cols, ["damage","type"]) or find_col_by_keywords(cols, ["damage"])
    C_SAVE = find_col_by_keywords(cols, ["save","type"]) or find_col_by_keywords(cols, ["save"])
    C_RANGE = find_col_by_keywords(cols, ["range"])
    C_AOE = find_col_by_keywords(cols, ["aoe"]) or find_col_by_keywords(cols, ["area"])
    C_COND = find_col_by_keywords(cols, ["condition"])
    C_TRAIN = find_col_by_keywords(cols, ["training","block"]) or find_col_by_keywords(cols, ["training"])

    assert C_SPELL and C_CLASS and C_LVL_OBT and C_SLOT, "Missing core columns"

    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        name = str(r[C_SPELL]).strip() if not pd.isna(r[C_SPELL]) else ""
        classes = split_classes(r[C_CLASS])
        lvl_raw = pd.to_numeric(r[C_LVL_OBT], errors='coerce')
        slot_raw = pd.to_numeric(r[C_SLOT], errors='coerce')
        lvl_char = int(lvl_raw) if not pd.isna(lvl_raw) else 0
        slot_type = int(slot_raw) if not pd.isna(slot_raw) else 0

        tags = "" if (C_TAGS is None or pd.isna(r.get(C_TAGS, None))) else str(r[C_TAGS]).strip()
        die  = "" if (C_DIE  is None or pd.isna(r.get(C_DIE,  None))) else str(r[C_DIE]).strip()
        dmg  = "" if (C_DMG  is None or pd.isna(r.get(C_DMG,  None))) else str(r[C_DMG]).strip()
        save = "" if (C_SAVE is None or pd.isna(r.get(C_SAVE, None))) else str(r[C_SAVE]).strip()
        rng  = r.get(C_RANGE, None) if C_RANGE else None
        aoe  = "" if (C_AOE  is None or pd.isna(r.get(C_AOE,  None))) else str(r[C_AOE]).strip()
        cond = "" if (C_COND is None or pd.isna(r.get(C_COND, None))) else str(r[C_COND]).strip()
        train= r.get(C_TRAIN, "") if C_TRAIN else ""

        has_save = bool(save and save.lower() not in ("none","n/a","na","-","—"))
        save_success_multiplier = 0.0 if (has_save and slot_type == 0) else (0.5 if has_save else 1.0)

        parsed_range_tiles = parse_tiles(rng) if C_RANGE else None
        cond_tokens = extract_conditions(cond)
        training_pairs = parse_training_block(train)

        for cls in classes or [""]:
            cls_norm = norm_class(cls)
            rows.append({
                "spell": name,
                "class": cls_norm,
                "learn_at_level": lvl_char,
                "slot_type": slot_type,
                "tags": tags,
                "die": die,
                "damage_type": dmg,
                "has_save": has_save,
                "save_attr": save.upper() if has_save else "",
                "save_success_multiplier": save_success_multiplier,
                "range_tiles": parsed_range_tiles,
                "aoe_shape": aoe,
                "conditions_text": cond,
                "conditions": cond_tokens,
                "training_pairs": training_pairs,
            })

    norm = pd.DataFrame(rows)
    # SLOT_CAPS
    caps = (norm.groupby(["class","slot_type"])["spell"].nunique().reset_index(name="proposed_slots"))
    # JSON
    ART.joinpath("spells_normalized.json").write_text(json.dumps(norm.to_dict(orient="records"), indent=2), encoding="utf-8")
    caps.to_csv(ART / "spell_slots_adjusted.csv", index=False)

    # Training order preview
    def first_pair(tp):
        if not isinstance(tp, list) or not tp: return {"position":"", "role":""}
        return tp[0] if isinstance(tp[0], dict) else {"position":"", "role":""}

    norm["_pos"] = norm["training_pairs"].apply(lambda tp: first_pair(tp)["position"])
    norm["_role"]= norm["training_pairs"].apply(lambda tp: first_pair(tp)["role"])
    norm.sort_values(by=["_pos","_role","class","slot_type","learn_at_level","spell"]) \
        .drop(columns=["_pos","_role"]).to_csv(ART / "training_order.csv", index=False)

    # Emit core/spell_catalog.py
    # Count distinct spells per class/slot
    seen = {}
    for row in norm.to_dict(orient="records"):
        key = (row["class"], int(row["slot_type"]), row["spell"])
        seen[key] = True
    slot_caps = {}
    for (cls, lvl, _), _ in seen.items():
        slot_caps.setdefault(cls, {}).setdefault(int(lvl), 0)
        slot_caps[cls][int(lvl)] += 1

    CORE.joinpath("spell_catalog.py").write_text(
        "from __future__ import annotations\n"
        f"SLOT_CAPS = {json.dumps(slot_caps, indent=2, sort_keys=True)}\n\n"
        f"SPELLS = {json.dumps(norm.to_dict(orient='records'), indent=2)}\n",
        encoding="utf-8"
    )

if __name__ == "__main__":
    main()
