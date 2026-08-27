import app


def _analysis(competencies):
    return {"competencies": competencies}


def test_matches_competency_whose_sme_language_appears_in_question():
    analysis = _analysis([
        {"name": "SQL", "sme_language": ["query plan", "index"]},
        {"name": "Distributed Systems", "sme_language": ["consensus", "replication"]},
    ])
    comp = app.match_competency(analysis, "How would you handle replication lag?")
    assert comp["name"] == "Distributed Systems"


def test_falls_back_to_first_competency_when_no_match():
    analysis = _analysis([
        {"name": "SQL", "sme_language": ["query plan"]},
        {"name": "Distributed Systems", "sme_language": ["consensus"]},
    ])
    comp = app.match_competency(analysis, "Tell me about a time you disagreed with a teammate.")
    assert comp["name"] == "SQL"


def test_empty_competencies_returns_empty_dict():
    assert app.match_competency(_analysis([]), "Any question") == {}


def test_match_is_case_insensitive():
    analysis = _analysis([{"name": "Kubernetes", "sme_language": ["Pod Scheduling"]}])
    comp = app.match_competency(analysis, "walk me through pod scheduling under resource pressure")
    assert comp["name"] == "Kubernetes"


def test_typed_and_voice_paths_would_match_the_same_competency():
    # Regression test for the original bug: voice grading always used
    # competencies[0] instead of matching the question like the typed path.
    # Both call sites now go through this same function, so this just
    # confirms match_competency itself is deterministic for identical input.
    analysis = _analysis([
        {"name": "SQL", "sme_language": ["index"]},
        {"name": "Distributed Systems", "sme_language": ["consensus"]},
    ])
    question = "Explain a consensus protocol you've implemented."
    assert app.match_competency(analysis, question) == app.match_competency(analysis, question)
    assert app.match_competency(analysis, question)["name"] == "Distributed Systems"
