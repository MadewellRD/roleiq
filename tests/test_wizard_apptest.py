"""End-to-end wizard integration test, driven via Streamlit's AppTest.

Exercises the actual app.py code paths through real button clicks and
session_state -- not just the pure helper functions tests/test_wizard_steps.py
already covers. All AI provider calls are mocked (no network, no API key).

This rebuilds, as a committed and repeatable test, the ad hoc verification
script used once during the wizard's original implementation and then
discarded -- see GL-10 in docs/engineering-spec/roadmap.md.
"""
import pytest
from streamlit.testing.v1 import AppTest

import ai_provider

FAKE_GRAPH = {
    "candidate_summary": "Backend engineer with distributed systems depth.",
    "roles": [], "projects": [], "capabilities": [], "evidence_phrases": [],
}
FAKE_ANALYSIS = {
    "role": "Backend Engineer", "company": "ACME", "executive_summary": "Solid fit.",
    "competencies": [
        {"name": "Distributed Systems", "importance": "Critical", "jd_signal": "x", "candidate_level": "Experienced", "evidence": "x", "gap": "", "sme_language": ["consensus"], "interview_risk": "High"},
        {"name": "SQL", "importance": "Medium", "jd_signal": "x", "candidate_level": "Adjacent", "evidence": "x", "gap": "", "sme_language": ["index"], "interview_risk": "Low"},
    ],
    "proof_paths": [], "training_priorities": ["Distributed Systems"],
    "likely_questions": ["Tell me about a distributed system you built."], "red_flags": [],
}
FAKE_PERSONA = {"persona_archetype": "Staff Engineer", "seniority": "Senior", "priorities": [], "style": "direct", "likely_followups": [], "pressure_tests": [], "what_good_sounds_like": [], "what_bad_sounds_like": []}
FAKE_MODULE = {"what_it_means": "x", "why_the_role_cares": "x", "how_an_sme_thinks": [], "architecture_or_workflow": [], "tradeoffs": [], "failure_modes": [], "language_upgrade": [], "candidate_bridge": "x", "practice_prompt": "x", "gold_standard_answer_outline": [], "red_line": "x"}
FAKE_GRADE = {"overall_score": 7, "technical_accuracy": 7, "depth": 7, "specificity": 7, "tradeoff_reasoning": 7, "business_alignment": 7, "sme_language": 7, "credibility": 7, "what_worked": ["clear"], "what_is_missing": [], "unsupported_or_risky_claims": [], "better_answer_outline": [], "coach_note": "good"}
FAKE_NEXT = {"next_competency": "SQL", "reason": "x", "exercise_type": "concept", "exercise": "x", "success_criteria": []}


def _fake_ai_json(system, user, web=False):
    if "Build a persistent candidate Experience Graph" in system:
        return FAKE_GRAPH
    if "a rigorous SME immersion" in system:
        return FAKE_ANALYSIS
    if "Model a likely interviewer persona" in system:
        return FAKE_PERSONA
    if "RoleIQ's SME coach" in system:
        return FAKE_MODULE
    if "an exacting technical interviewer" in system:
        return FAKE_GRADE
    if "RoleIQ adaptive curriculum engine" in system:
        return FAKE_NEXT
    return {}


def _fake_ai_text(system, user, web=False, max_tokens=7000):
    if "Generate one realistic next interview question" in system:
        return "A follow-up question."
    if "Create a concise interview battle card" in system:
        return "# Battle Card\n\nCompact summary."
    return ""


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("RoleIQ_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("RoleIQ_DB_KEY", "kQ8Yv3ZqJf9c2mN5pL7wX0aB4dR6tU1sE3gH8jK2mO4=")
    monkeypatch.setattr(ai_provider, "ai_json", _fake_ai_json)
    monkeypatch.setattr(ai_provider, "ai_text", _fake_ai_text)


def _build(at):
    at.session_state["jd_text"] = "We need a backend engineer with distributed systems and SQL experience. " * 5
    at.session_state["resume_text"] = "Senior backend engineer, 8 years building distributed systems at scale. " * 5
    build_btn = [b for b in at.button if b.label == "Build RoleIQ Role Model"][0]
    build_btn.click().run(timeout=30)
    assert not at.exception, f"build raised: {at.exception}"
    return at


def test_build_produces_wizard_state():
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    assert not at.exception
    _build(at)
    assert at.session_state["analysis"]["role"] == "Backend Engineer"
    assert at.session_state["provider_healthy"] is True
    assert at.session_state["wizard_step"] == "readiness_map"
    assert at.session_state["trained_modules"] == {}


def test_segmented_control_reflects_current_step():
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    _build(at)
    assert at.segmented_control[0].value == "readiness_map"


def test_sme_training_locks_by_interview_risk_then_unlocks_in_order():
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    _build(at)

    at.session_state["wizard_step"] = "sme_training"
    at.run(timeout=30)
    assert not at.exception

    md_text = " ".join(m.value for m in at.markdown)
    assert "Distributed Systems" in md_text  # highest risk, up next
    caption_text = " ".join(c.value for c in at.caption)
    assert "Locked" in caption_text and "SQL" in caption_text

    train_btn = [b for b in at.button if b.label == "Generate SME Module"][0]
    train_btn.click().run(timeout=30)
    assert not at.exception
    assert 0 in at.session_state["trained_modules"]
    assert at.session_state["trained_modules"][0] == FAKE_MODULE

    md_text = " ".join(m.value for m in at.markdown)
    assert "SQL" in md_text  # now the up-next one


def test_interview_step_auto_populates_first_question():
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    _build(at)
    at.session_state["wizard_step"] = "interview"
    at.run(timeout=30)
    assert not at.exception
    assert at.session_state["current_question"] == "Tell me about a distributed system you built."


def test_grade_and_continue_persists_to_history():
    at = AppTest.from_file("../app.py")
    at.run(timeout=30)
    _build(at)
    at.session_state["wizard_step"] = "interview"
    at.run(timeout=30)

    at.session_state["answer_box"] = "We used Raft for consensus across replicas."
    grade_btn = [b for b in at.button if b.label == "Grade & Continue"][0]
    grade_btn.click().run(timeout=30)
    assert not at.exception

    assert len(at.session_state["history"]) == 1
    turn = at.session_state["history"][0]
    assert turn["competency"] == "Distributed Systems"  # SME-language matched, not competencies[0] by luck
    assert at.session_state["grade"] == FAKE_GRADE
    assert at.session_state["next"] == FAKE_NEXT
