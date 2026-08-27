"""GL-31: roleiq.log entries carry a per-session correlation id.

app._SessionIdFilter stamps every record passing through the shared file
handler with Streamlit's own ScriptRunContext.session_id (truncated to 8
chars), falling back to "-" when no script context exists (e.g. a plain
module import). It's a handler-level filter, not a per-logger one, because
the same handler also receives streamlit.error_util's records directly (see
GL-22) -- those never pass through this file's own `logger`.
"""
import logging

import app


def test_filter_stamps_dash_when_no_script_run_context():
    record = logging.LogRecord("roleiq", logging.INFO, __file__, 1, "msg", None, None)
    filt = app._SessionIdFilter()
    assert filt.filter(record) is True
    assert record.session_id == "-"


def test_session_id_is_a_real_value_inside_a_running_app(tmp_path, monkeypatch):
    # Reads the observed id back through session_state rather than the real
    # roleiq.log file: pytest's own log-capture plugin temporarily detaches
    # the root logger's real handlers for the duration of each test (so a
    # record logged via app.logger, which reaches the file only by
    # propagating to root, never makes it to disk while a test is running) --
    # this sidesteps that entirely by asking the filter directly, from
    # inside the running app where a real ScriptRunContext exists.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key")
    monkeypatch.setenv("RoleIQ_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("RoleIQ_DB_KEY", "kQ8Yv3ZqJf9c2mN5pL7wX0aB4dR6tU1sE3gH8jK2mO4=")

    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    probe = tmp_path / "probe.py"
    probe.write_text(
        "import sys, logging\n"
        f"sys.path.insert(0, {str(Path(__file__).parent.parent)!r})\n"
        "import streamlit as st\n"
        "import app\n"
        "record = logging.LogRecord('roleiq', logging.INFO, __file__, 1, 'msg', None, None)\n"
        "app._SessionIdFilter().filter(record)\n"
        "st.session_state['_gl31_session_id'] = record.session_id\n"
    )

    at = AppTest.from_file(str(probe))
    at.run()
    assert not at.exception

    observed = at.session_state["_gl31_session_id"]
    assert observed != "-"
    assert len(observed) == 8
