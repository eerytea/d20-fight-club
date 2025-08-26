import importlib
CANDIDATES = [
    "ui.state_menu",
    "ui.state_team_select",
    "ui.state_exhibition_picker",
    "ui.state_season_hub",
    "ui.state_match",
    "ui.state_roster_browser",
    "ui.uiutil",
    "ui.app",
]
bad = []
for m in CANDIDATES:
    try:
        importlib.import_module(m)
        print(f"[OK] {m}")
    except Exception as e:
        bad.append((m, e))
        print(f"[FAIL] {m}: {e}")

if bad:
    raise SystemExit(1)
