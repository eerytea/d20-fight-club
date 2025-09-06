# tests/test_training_artifacts.py
import csv, os
from pathlib import Path

REQ_TR = {"class","level","feature","value"}
REQ_SL = {"class","level","slot_type","slots"}

def _read_headers(path: Path):
    assert path.exists(), f"Missing {path}"
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return set(r.fieldnames or [])

def test_training_and_slots_artifacts_exist_and_have_columns():
    tr = Path("artifacts/training_order.csv")
    sl = Path("artifacts/spell_slots_adjusted.csv")
    trh = _read_headers(tr)
    slh = _read_headers(sl)
    assert REQ_TR.issubset(trh), f"training_order.csv missing {REQ_TR - trh}"
    assert REQ_SL.issubset(slh), f"spell_slots_adjusted.csv missing {REQ_SL - slh}"
