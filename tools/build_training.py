# tools/build_training.py
from __future__ import annotations
import sys, csv
from pathlib import Path
from typing import List, Dict, Any

# Canonical paths
SRC_TRAINING = Path("data/training_order.csv")
SRC_SLOTS    = Path("data/spell_slots_adjusted.csv")
OUT_DIR      = Path("artifacts")
OUT_TRAINING = OUT_DIR / "training_order.csv"
OUT_SLOTS    = OUT_DIR / "spell_slots_adjusted.csv"

# Minimal schemas (tweak if your columns differ)
REQUIRED_TRAINING = {"class","level","feature","value"}   # e.g., class=Wizard, level=3, feature="SpellAttackBonus", value=+1
REQUIRED_SLOTS    = {"class","level","slot_type","slots"} # e.g., slot_type=0/1/etc, slots=int per level

def _read_csv(path: Path) -> List[Dict[str,Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
    return rows

def _require(cols: set, required: set, label: str) -> None:
    missing = required - cols
    if missing:
        raise ValueError(f"{label}: missing columns {sorted(missing)}")

def _write_csv(path: Path, rows: List[Dict[str,Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        # still write headers from required schema to make runtime happy
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

def main(argv=None) -> int:
    print(f"[build_training] reading {SRC_TRAINING} and {SRC_SLOTS}")
    tr = _read_csv(SRC_TRAINING)
    sl = _read_csv(SRC_SLOTS)

    if tr:
        _require(set(tr[0].keys()), REQUIRED_TRAINING, "training_order.csv")
    if sl:
        _require(set(sl[0].keys()), REQUIRED_SLOTS, "spell_slots_adjusted.csv")

    # (Place for optional normalization—trim spaces, fix cases, cast ints, etc.)
    # Example quick normalizations:
    def norm_rows(rows):
        out = []
        for r in rows:
            out.append({k.strip(): (v.strip() if isinstance(v,str) else v) for k,v in r.items()})
        return out

    tr = norm_rows(tr)
    sl = norm_rows(sl)

    print(f"[build_training] writing {OUT_TRAINING} and {OUT_SLOTS}")
    _write_csv(OUT_TRAINING, tr)
    _write_csv(OUT_SLOTS, sl)

    print("[build_training] done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
