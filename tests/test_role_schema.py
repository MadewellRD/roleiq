import pytest

import role_schema


def _valid_analysis(**overrides):
    base = {
        "role": "Engineer",
        "company": "ACME",
        "executive_summary": "Solid fit",
        "competencies": [{
            "name": "Python", "importance": "High", "jd_signal": "x",
            "candidate_level": "Experienced", "evidence": "x", "gap": "",
            "sme_language": ["async"], "interview_risk": "Low",
        }],
        "proof_paths": [],
        "training_priorities": ["Kubernetes"],
        "likely_questions": ["Tell me about..."],
        "red_flags": [],
    }
    base.update(overrides)
    return base


def test_valid_analysis_passes_through():
    result = role_schema.validate_analysis(_valid_analysis(), "Anthropic (Claude)", "claude-sonnet-5")
    assert result["competencies"][0]["name"] == "Python"
    assert result["training_priorities"] == ["Kubernetes"]


def test_missing_competencies_raises_contract_error():
    # The exact bug this module exists to catch: valid JSON, wrong shape.
    bad = {"role": "Engineer", "company": "ACME", "summary": "blah"}
    with pytest.raises(role_schema.ContractError, match="CONTRACT FAILURE"):
        role_schema.validate_analysis(bad, "Anthropic (Claude)", "claude-sonnet-5")


def test_empty_competencies_list_raises_contract_error():
    # Structurally present but empty -- the silent-blank-page failure mode.
    bad = _valid_analysis(competencies=[])
    with pytest.raises(role_schema.ContractError, match="CONTRACT FAILURE"):
        role_schema.validate_analysis(bad, "Anthropic (Claude)", "claude-sonnet-5")


def test_contract_error_message_includes_diagnostics():
    bad = {"role": "Engineer", "company": "ACME", "summary": "blah"}
    with pytest.raises(role_schema.ContractError) as exc_info:
        role_schema.validate_analysis(bad, "Anthropic (Claude)", "claude-sonnet-5")
    message = str(exc_info.value)
    assert "Received keys: company, role, summary" in message
    assert "Provider: Anthropic (Claude)" in message
    assert "Model: claude-sonnet-5" in message
    assert "competencies" in message


@pytest.mark.parametrize("alias,canonical", [
    ("summary", "executive_summary"),
    ("competency_graph", "competencies"),
    ("trainingPriorities", "training_priorities"),
    ("questions", "likely_questions"),
    ("risks", "red_flags"),
])
def test_known_key_aliases_normalize(alias, canonical):
    payload = _valid_analysis()
    value = payload.pop(canonical)
    payload[alias] = value
    result = role_schema.validate_analysis(payload, "Anthropic (Claude)", "claude-sonnet-5")
    if canonical == "competencies":
        assert len(result[canonical]) == len(value)
    else:
        assert result[canonical] == value


def test_alias_does_not_overwrite_correctly_named_field():
    # Both the canonical key and an alias present -- canonical must win, not
    # be silently clobbered by the alias.
    payload = _valid_analysis(executive_summary="canonical value")
    payload["summary"] = "alias value should be ignored"
    result = role_schema.validate_analysis(payload, "Anthropic (Claude)", "claude-sonnet-5")
    assert result["executive_summary"] == "canonical value"
