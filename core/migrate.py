from __future__ import annotations
from typing import Any, Dict, List

from core.adapters import as_fixture_dict, flatten_fixtures

SCHEMA_VERSION = 1

def normalize_save_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make an old save 'look like' our new schema without losing data.
    - ensures schema_version
    - ensures fixtures flat list exists
    - normalizes fixtures_by_week shape (aliases → canonical)
    """
    out = dict(d)
    out.setdefault("schema_version", SCHEMA_VERSION)

    fbw = out.get("fixtures_by_week", None)
    if isinstance(fbw, list) and fbw and isinstance(fbw[0], list):
        # normalize each fixture
        out["fixtures_by_week"] = [[as_fixture_dict(fx) for fx in wk] for wk in fbw]
        out["fixtures"] = flatten_fixtures(out["fixtures_by_week"])
    else:
        # if only flat fixtures exist, try to infer weeks
        flat = out.get("fixtures", [])
        if flat:
            normalized = [as_fixture_dict(fx) for fx in flat]
            out["fixtures"] = normalized
            # group by week (ensure list length)
            max_w = max((int(fx.get("week", 1)) for fx in normalized), default=1)
            fbw2: List[List[Dict[str, Any]]] = [[] for _ in range(max_w)]
            for fx in normalized:
                w = max(1, int(fx.get("week", 1)))
                fbw2[w-1].append(fx)
            out["fixtures_by_week"] = fbw2
    return out
