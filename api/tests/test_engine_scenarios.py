import pytest
from app.judge.scenarios import SCENARIOS, _check

@pytest.mark.parametrize("s", SCENARIOS, ids=[s.id for s in SCENARIOS])
def test_scenario(s):
    ok, problems, _ = _check(s)
    assert ok, problems
