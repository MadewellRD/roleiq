"""Coverage for F3 (Role Context conditional path) and F5 (interviewer
persona modeling) -- previously zero coverage of either.
"""
import pytest
from streamlit.testing.v1 import AppTest

import app
import ai_provider


# ---- F5: interviewer_model() unit coverage ----

def test_interviewer_model_returns_the_structured_result(monkeypatch):
    fake_persona = {"persona_archetype": "Staff Engineer", "seniority": "Senior"}
    monkeypatch.setattr(app, "ai_json", lambda system, user, web=False: fake_persona)

    result = app.interviewer_model({"role": "Engineer"}, {}, "ACME")
    assert result == fake_persona


def test_interviewer_model_embeds_company_and_analysis(monkeypatch):
    captured = {}

    def fake_ai_json(system, user, web=False):
        captured["user"] = user
        return {}

    monkeypatch.setattr(app, "ai_json", fake_ai_json)
    app.interviewer_model({"role": "Staff Engineer"}, {}, "ACME Corp")

    assert "ACME Corp" in captured["user"]
    assert "Staff Engineer" in captured["user"]


# ---- F3: role_context() unit coverage ----

def test_role_context_returns_the_structured_result(monkeypatch):
    fake_ctx = {"company_context": ["Public cloud infra company."], "status": None}
    monkeypatch.setattr(app, "ai_json", lambda system, user, web=False: fake_ctx)

    result = app.role_context("job description text", "ACME", "Engineer")
    assert result == fake_ctx


def test_role_context_requests_web_search(monkeypatch):
    captured = {}

    def fake_ai_json(system, user, web=False):
        captured["web"] = web
        return {}

    monkeypatch.setattr(app, "ai_json", fake_ai_json)
    app.role_context("jd", "ACME", "Engineer")

    assert captured["web"] is True


# ---- F3: ROLE_CONTEXT_ENABLED on/off, end to end via AppTest ----

FAKE_GRAPH = {"candidate_summary": "x", "roles": [], "projects": [], "capabilities": [], "evidence_phrases": []}
FAKE_ANALYSIS = {
    "role": "Engineer", "company": "ACME", "executive_summary": "x",
    "competencies": [{"name": "X", "importance": "High", "jd_signal": "x", "candidate_level": "Experienced", "evidence": "x", "gap": "", "sme_language": [], "interview_risk": "High"}],
    "proof_paths": [], "training_priorities": [], "likely_questions": ["Q"], "red_flags": [],
}
FAKE_PERSONA = {"persona_archetype": "x", "seniority": "x", "priorities": [], "style": "x", "likely_followups": [], "pressure_tests": [], "what_good_sounds_like": [], "what_bad_sounds_like": []}
FAKE_ROLE_CONTEXT = {
    "company_context": ["Real company context."], "technical_stack_signals": [], "engineering_culture_signals": [],
    "role_specific_signals": [], "likely_interview_themes": [], "sources": [], "inferences": [],
}


def _make_fake_ai_json(role_context_calls):
    def fake_ai_json(system, user, web=False):
        if "Build a persistent candidate Experience Graph" in system:
            return FAKE_GRAPH
        if "RoleIQ Role Context Plane" in system:
            role_context_calls.append(1)
            return FAKE_ROLE_CONTEXT
        if "a rigorous SME immersion" in system:
            return FAKE_ANALYSIS
        if "Model a likely interviewer persona" in system:
            return FAKE_PERSONA
        return {}
    return fake_ai_json


@pytest.fixture
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("RoleIQ_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("RoleIQ_DB_KEY", "kQ8Yv3ZqJf9c2mN5pL7wX0aB4dR6tU1sE3gH8jK2mO4=")


def _build(at):
    at.session_state["jd_text"] = "We need an engineer with distributed systems experience for this role. " * 5
    at.session_state["resume_text"] = "Senior engineer with distributed systems background over many years. " * 5
    build_btn = [b for b in at.button if b.label == "Build RoleIQ role model"][0]
    build_btn.click().run(timeout=30)
    assert not at.exception, f"build raised: {at.exception}"


def test_role_context_disabled_by_default_produces_deferred_stub(_isolated_db, monkeypatch):
    monkeypatch.delenv("RoleIQ_ROLE_CONTEXT_ENABLED", raising=False)
    role_context_calls = []
    monkeypatch.setattr(ai_provider, "ai_json", _make_fake_ai_json(role_context_calls))

    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    _build(at)

    assert role_context_calls == [], "role_context() should not be called when the flag is off"
    assert at.session_state["context"]["status"] == "deferred"
    assert at.session_state["context"]["company_context"] == []


def test_role_context_enabled_calls_the_real_function(_isolated_db, monkeypatch):
    monkeypatch.setenv("RoleIQ_ROLE_CONTEXT_ENABLED", "1")
    role_context_calls = []
    monkeypatch.setattr(ai_provider, "ai_json", _make_fake_ai_json(role_context_calls))

    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    _build(at)

    assert role_context_calls == [1], "role_context() should be called exactly once when the flag is on"
    assert at.session_state["context"]["company_context"] == ["Real company context."]
    assert "status" not in at.session_state["context"] or at.session_state["context"].get("status") != "deferred"
