import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ENV_VARS_TO_ISOLATE = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "RoleIQ_MODEL",
    "RoleIQ_MODEL_ANTHROPIC",
    "RoleIQ_MODEL_OPENAI",
    "RoleIQ_DB_KEY",
)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Never let a developer's real .env/shell keys leak into a test run."""
    for name in _ENV_VARS_TO_ISOLATE:
        monkeypatch.delenv(name, raising=False)
