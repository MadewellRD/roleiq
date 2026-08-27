"""GL-25: a version string exists next to APP_TITLE and is visible in the UI."""
import re

import app


def test_app_version_is_defined_next_to_app_title():
    assert re.match(r"^\d+\.\d+\.\d+$", app.APP_VERSION)


def test_app_version_appears_in_header_caption(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key")
    monkeypatch.setenv("RoleIQ_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("RoleIQ_DB_KEY", "kQ8Yv3ZqJf9c2mN5pL7wX0aB4dR6tU1sE3gH8jK2mO4=")

    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("../app.py")
    at.run()

    captions = " ".join(c.value for c in at.caption)
    assert f"v{app.APP_VERSION}" in captions
