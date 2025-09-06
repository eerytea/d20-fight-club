# tests/test_grid_and_spells.py
import importlib

def test_grid_is_16x16():
    const = importlib.import_module("engine.constants")
    assert const.GRID_COLS == 16
    assert const.GRID_ROWS == 16

def test_spell_catalog_loads_and_has_minimal_fields():
    cat = importlib.import_module("core.spell_catalog")
    spells = cat.all_spells()
    assert isinstance(spells, list)
    # Not asserting count—just structure
    required = {
        "name","class","learn_at_level","slot_type","tags","die","damage_type",
        "has_save","save_attr","save_success_multiplier","range_tiles","aoe_shape","conditions_text"
    }
    if spells:
        s0 = spells[0]
        assert required.issubset(set(s0.keys()))
