"""Not a test module -- a standalone script AppTest runs as the "app" under
test for tests/test_uncaught_exception_logging.py. Importing app triggers its
real logging setup, then raising here reproduces an exception outside every
try/except in app.py itself (GL-22)."""
import app  # noqa: F401  (import side effect only: runs app.py's logging setup)

raise RuntimeError("GL-22 regression probe: uncaught top-level exception")
