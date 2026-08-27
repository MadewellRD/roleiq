import ai_provider


def test_anthropic_wins_when_both_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    assert ai_provider.provider() == "anthropic"


def test_openai_when_only_openai_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    assert ai_provider.provider() == "openai"


def test_none_when_neither_set():
    assert ai_provider.provider() is None
    status = ai_provider.status()
    assert status["connected"] is False


def test_model_provider_specific_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    monkeypatch.setenv("RoleIQ_MODEL_ANTHROPIC", "claude-custom")
    assert ai_provider.model() == "claude-custom"


def test_model_legacy_fallback_respects_active_provider(monkeypatch):
    # Anthropic active: a claude-prefixed legacy value is honored...
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    monkeypatch.setenv("RoleIQ_MODEL", "claude-legacy")
    assert ai_provider.model() == "claude-legacy"

    # ...but a non-claude legacy value is ignored, falling back to the default,
    # so a stale OpenAI model id can't leak into an Anthropic run.
    monkeypatch.setenv("RoleIQ_MODEL", "gpt-legacy")
    assert ai_provider.model() == ai_provider.ANTHROPIC_DEFAULT_MODEL


def test_voice_available_requires_openai_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    assert ai_provider.voice_available() is False

    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    assert ai_provider.voice_available() is True
