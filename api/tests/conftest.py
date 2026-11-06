import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# tests never call paid services: real keys in .env are overridden here
os.environ["LLM_PROVIDER"] = "none"
os.environ["SARVAM_API_KEY"] = ""
_TEST_DB = Path(__file__).resolve().parents[2] / "var" / "test.db"
_TEST_DB.unlink(missing_ok=True)  # a fresh schema every run
os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(_TEST_DB))

import pytest


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    from app.security import reset_rate_limits
    reset_rate_limits()
    yield
