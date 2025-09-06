# tools/debug_spells_artifact.py
from __future__ import annotations
import json, itertools
from pathlib import Path

ART = Path("artifacts/spells_normalized.json")

def main() -> int:
    if not ART.exists():
        print(f"[debug] Missing {ART}. Run: python -m tools.build_spells")
        return 2
    rows = json.loads(ART.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        print("[debug] Artifact root is not a non-empty list.")
        return 2
    for i, r in enumerate(itertools.islice(rows, 5)):
        if isinstance(r, dict):
            print(f"Row {i} keys: {sorted(r.keys())}")
        else:
            print(f"Row {i} is not a dict: {type(r)}")
    print(f"[debug] Total rows: {len(rows)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
