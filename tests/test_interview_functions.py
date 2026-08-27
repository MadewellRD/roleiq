"""Coverage for F7 (Interview simulation): grade_answer, adaptive_next,
synthesize_question, and match_competency (tested separately in
test_match_competency.py). Complements test_prompt_injection_wrapping.py,
which already covers guard presence and answer-wrapping -- this file covers
return-value plumbing and the history-window slicing each function does.
"""
import app


def test_grade_answer_returns_the_structured_result(monkeypatch):
    fake_grade = {"overall_score": 8, "coach_note": "Solid answer."}
    monkeypatch.setattr(app, "ai_json", lambda system, user, web=False: fake_grade)

    result = app.grade_answer(
        {"role": "Engineer"}, {"name": "SQL"}, "Explain indexing.", "B-trees speed lookups.", {}
    )
    assert result == fake_grade


def test_grade_answer_embeds_role_question_and_competency(monkeypatch):
    captured = {}

    def fake_ai_json(system, user, web=False):
        captured["user"] = user
        return {}

    monkeypatch.setattr(app, "ai_json", fake_ai_json)
    app.grade_answer({"role": "Staff Engineer"}, {"name": "SQL"}, "Explain indexing.", "answer text", {})

    assert "Staff Engineer" in captured["user"]
    assert "SQL" in captured["user"]
    assert "Explain indexing." in captured["user"] or "indexing" in captured["user"].lower()


def test_adaptive_next_returns_the_structured_result(monkeypatch):
    fake_next = {"next_competency": "SQL", "exercise": "Design an index."}
    monkeypatch.setattr(app, "ai_json", lambda system, user, web=False: fake_next)

    result = app.adaptive_next({}, [])
    assert result == fake_next


def test_adaptive_next_sends_only_last_12_history_entries(monkeypatch):
    captured = {}

    def fake_ai_json(system, user, web=False):
        captured["user"] = user
        return {}

    monkeypatch.setattr(app, "ai_json", fake_ai_json)

    history = [{"question": f"Q{i}", "answer": f"A{i}", "grade": {}, "competency": "X"} for i in range(20)]
    app.adaptive_next({}, history)

    # Oldest entries (0-7) must not appear; the most recent 12 (8-19) must.
    assert "Q0" not in captured["user"]
    assert "Q7" not in captured["user"]
    assert "Q8" in captured["user"]
    assert "Q19" in captured["user"]


def test_synthesize_question_returns_the_text_result(monkeypatch):
    monkeypatch.setattr(app, "ai_call", lambda system, user, web=False, max_tokens=7000: "What about replication?")

    result = app.synthesize_question({}, {}, [])
    assert result == "What about replication?"


def test_synthesize_question_sends_only_last_8_history_entries(monkeypatch):
    captured = {}

    def fake_ai_call(system, user, web=False, max_tokens=7000):
        captured["user"] = user
        return ""

    monkeypatch.setattr(app, "ai_call", fake_ai_call)

    history = [{"question": f"Q{i}", "answer": f"A{i}", "grade": {}, "competency": "X"} for i in range(20)]
    app.synthesize_question({}, {}, history)

    assert "Q0" not in captured["user"]
    assert "Q11" not in captured["user"]
    assert "Q12" in captured["user"]
    assert "Q19" in captured["user"]
