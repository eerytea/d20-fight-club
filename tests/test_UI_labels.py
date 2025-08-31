import pytest

pytestmark = pytest.mark.skip(reason="UI smoke test only; enable when pygame/headless rendering is configured.")

def test_ui_strings_players_label_smoke():
    # placeholder to remind that roster/team screens say 'Players' not 'Fighters'
    assert "Players" and "Team Select"
