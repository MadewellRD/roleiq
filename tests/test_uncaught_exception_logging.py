"""GL-22: an exception outside every try/except in app.py must still reach
roleiq.log, not just stderr.

Streamlit's script runner (exec_code.py) catches such an exception itself and
logs it through a logger that streamlit/logger.py builds with propagate=False
-- so app.py's root-logger handlers alone never see it. app.py closes this by
attaching its file handler directly to that named logger (see the comment
above `logging.getLogger("streamlit.error_util").addHandler(...)` in app.py).
This test reproduces the exact failure this fix addresses: without it, the
message below would never appear in roleiq.log.
"""
import logging
from pathlib import Path

from streamlit.testing.v1 import AppTest

PROBE = str(Path(__file__).parent / "fixtures" / "gl22_uncaught_probe.py")


def test_uncaught_exception_reaches_roleiq_log(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key")
    monkeypatch.setenv("RoleIQ_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("RoleIQ_DB_KEY", "kQ8Yv3ZqJf9c2mN5pL7wX0aB4dR6tU1sE3gH8jK2mO4=")

    at = AppTest.from_file(PROBE)
    at.run()

    assert at.exception  # Streamlit's own script runner did catch it...

    log_path = Path(__file__).parent.parent / "roleiq.log"
    assert log_path.exists()
    assert "GL-22 regression probe: uncaught top-level exception" in log_path.read_text(encoding="utf-8")


def test_streamlit_error_util_logger_has_roleiq_file_handler():
    # Structural check, independent of any one probe run: the specific
    # logger Streamlit's script runner uses for this message must carry
    # app.py's RotatingFileHandler, not rely on propagation (which is
    # disabled on this logger by Streamlit itself).
    import app  # noqa: F401 (runs app.py's logging setup as a side effect)

    handler_classes = [type(h).__name__ for h in logging.getLogger("streamlit.error_util").handlers]
    assert "RotatingFileHandler" in handler_classes
