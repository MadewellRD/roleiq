"""GL-24: both AI provider clients must bound a hung network call instead of
blocking indefinitely, and the resulting error must be distinguishable from
this module's own ai_provider.ProviderError.

Each test spins up a local TCP server that accepts a connection and never
replies, points a real SDK client at it with a short timeout, and confirms
the call raises well inside a generous bound rather than hanging.
"""
import socket
import threading
import time

import anthropic
import openai
import pytest

import ai_provider

TIMEOUT_SECONDS = 0.5
BOUND_SECONDS = 5  # generous ceiling; a real hang would exceed this by orders of magnitude


def _hanging_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(5)

    def accept_and_hang():
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            threading.Thread(target=lambda c: time.sleep(30), args=(conn,), daemon=True).start()

    threading.Thread(target=accept_and_hang, daemon=True).start()
    return srv, port


def test_openai_client_bounds_a_hung_call(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-fake-key")
    srv, port = _hanging_server()
    monkeypatch.setattr(ai_provider, "AI_TIMEOUT_SECONDS", TIMEOUT_SECONDS)
    client = openai.OpenAI(api_key="test-fake-key", base_url=f"http://127.0.0.1:{port}/v1",
                            timeout=ai_provider.AI_TIMEOUT_SECONDS, max_retries=0)

    start = time.time()
    with pytest.raises(openai.APITimeoutError) as exc_info:
        client.responses.create(model="gpt-test", input="hi")
    elapsed = time.time() - start

    assert elapsed < BOUND_SECONDS
    assert not isinstance(exc_info.value, ai_provider.ProviderError)
    srv.close()


def test_anthropic_client_bounds_a_hung_call(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key")
    srv, port = _hanging_server()
    monkeypatch.setattr(ai_provider, "AI_TIMEOUT_SECONDS", TIMEOUT_SECONDS)
    client = anthropic.Anthropic(api_key="test-fake-key", base_url=f"http://127.0.0.1:{port}",
                                  timeout=ai_provider.AI_TIMEOUT_SECONDS, max_retries=0)

    start = time.time()
    with pytest.raises(anthropic.APITimeoutError) as exc_info:
        client.messages.create(model="claude-test", max_tokens=10, messages=[{"role": "user", "content": "hi"}])
    elapsed = time.time() - start

    assert elapsed < BOUND_SECONDS
    assert not isinstance(exc_info.value, ai_provider.ProviderError)
    srv.close()


def test_client_factories_pass_ai_timeout_seconds(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-fake-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key")
    monkeypatch.setattr(ai_provider, "AI_TIMEOUT_SECONDS", 12.5)

    assert ai_provider.openai_client().timeout == 12.5
    assert ai_provider.anthropic_client().timeout == 12.5
