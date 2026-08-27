"""Typed contract between the provider's structured-output layer and RoleIQ's UI.

ai_provider.ai_json() guarantees valid JSON, not valid RoleIQ data: the
Anthropic tool schema (ai_provider.ANTHROPIC_JSON_TOOL) is deliberately
permissive (empty properties, additionalProperties=True) because its shape
differs per call site, so nothing at the API level enforces analyze()'s
requested fields. Without a check here, a technically-valid-but-wrong-shaped
reply (e.g. {"role": "...", "summary": "..."} instead of the requested
executive_summary/competencies/...) renders silently as an empty UI section
instead of a visible failure.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError

# Key variants a model has been observed to substitute for RoleIQ's canonical
# analyze() schema. Only renames when the canonical key is absent -- never
# overwrites a correctly-named field, and never invents a value that wasn't
# already present under some name.
KEY_ALIASES = {
    "summary": "executive_summary",
    "competency_graph": "competencies",
    "trainingPriorities": "training_priorities",
    "questions": "likely_questions",
    "risks": "red_flags",
}


class ContractError(RuntimeError):
    """Raised when a provider reply is valid JSON but not valid RoleIQ data."""


class Competency(BaseModel):
    name: str = ""
    importance: str = ""
    jd_signal: str = ""
    candidate_level: str = ""
    evidence: str = ""
    gap: str = ""
    sme_language: List[str] = Field(default_factory=list)
    interview_risk: str = ""


class ProofPath(BaseModel):
    requirement: str = ""
    candidate_story: str = ""
    how_to_frame: str = ""
    truth_boundary: str = ""


class RoleAnalysis(BaseModel):
    role: str = ""
    company: str = ""
    executive_summary: str = ""
    # analyze()'s prompt asks for 8-14; requiring at least 1 is the floor that
    # catches a structurally-valid-but-empty reply, which is the exact
    # silent-blank-page failure mode this module exists to prevent.
    competencies: List[Competency] = Field(min_length=1)
    proof_paths: List[ProofPath] = Field(default_factory=list)
    training_priorities: List[str] = Field(default_factory=list)
    likely_questions: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)


def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(raw)
    for old_key, new_key in KEY_ALIASES.items():
        if old_key in normalized and new_key not in normalized:
            normalized[new_key] = normalized.pop(old_key)
    return normalized


def validate_analysis(raw: Dict[str, Any], provider_label: str, model: str) -> Dict[str, Any]:
    """Normalize known key variants, then enforce RoleIQ's analyze() contract.

    Raises ContractError -- not a bare pydantic ValidationError -- carrying a
    diagnostic drawer (expected shape, keys actually returned, provider,
    model) so a contract mismatch is a visible, debuggable failure instead of
    a silently-empty UI section.
    """
    normalized = _normalize(raw)
    try:
        validated = RoleAnalysis(**normalized)
    except ValidationError as e:
        received_keys = ", ".join(sorted(raw.keys())) or "(none)"
        expected = ", ".join(RoleAnalysis.model_fields.keys())
        raise ContractError(
            "ROLE ANALYSIS CONTRACT FAILURE\n\n"
            f"Expected fields: {expected}\n"
            "(competencies requires at least 1 item)\n\n"
            f"Received keys: {received_keys}\n\n"
            f"Provider: {provider_label}\n"
            f"Model: {model}\n\n"
            f"{e}"
        ) from e
    return validated.model_dump()
