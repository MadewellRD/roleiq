"""RoleIQ AI provider layer.

RoleIQ talks to exactly ONE text provider per run: whichever one has an active
connection. Detection is purely key-based.

    ANTHROPIC_API_KEY set -> Anthropic (Claude)
    OPENAI_API_KEY set    -> OpenAI
    both set              -> Anthropic wins
    neither set           -> no provider; the UI degrades to input-only

Voice transcription is a deliberate exception. Anthropic exposes no
speech-to-text endpoint, so the recorded-answer path is wired explicitly to
OPENAI_API_KEY and is simply unavailable when that key is absent, regardless of
which provider is handling text.

JSON responses do not rely on the model formatting its prose nicely. Every
non-search call goes through the provider's native structured-output mechanism
(a forced tool call on Anthropic, json_object response format on OpenAI), which
returns parsed JSON rather than text that has to be scraped. Web-search calls
cannot force a tool, so those fall back to a hardened extractor plus a one-shot
repair pass. Truncation is reported as truncation instead of surfacing as a
cryptic JSONDecodeError.

Model selection, in order of precedence:

    RoleIQ_MODEL_ANTHROPIC / RoleIQ_MODEL_OPENAI   provider-specific override
    RoleIQ_MODEL                                   legacy single-provider value,
                                                   honoured only when it names a
                                                   model belonging to the active
                                                   provider
    built-in default below
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

_logger = logging.getLogger("roleiq")

OPENAI_DEFAULT_MODEL = "gpt-5.6-luna"
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-5"

# Anthropic exposes no transcription API; this is always an OpenAI model.
TRANSCRIBE_MODEL = os.getenv("RoleIQ_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

# Structured analysis payloads (8-14 competencies, proof paths, gradings) run
# long. A tight cap truncates them mid-object, which used to surface as a
# JSONDecodeError pointing at a column number.
DEFAULT_TEXT_MAX_TOKENS = int(os.getenv("RoleIQ_MAX_TOKENS", "7000"))
DEFAULT_JSON_MAX_TOKENS = int(os.getenv("RoleIQ_JSON_MAX_TOKENS", "16000"))

# Server-side web search, one definition per provider.
OPENAI_WEB_SEARCH_TOOL: Dict[str, Any] = {"type": "web_search"}
ANTHROPIC_WEB_SEARCH_TOOL: Dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 6,
}

# Freeform structured output: one forced tool whose input IS the payload.
JSON_TOOL_NAME = "emit_json"
JSON_TOOL_DESCRIPTION = (
    "Emit the requested result as a single JSON object. Use exactly the keys and "
    "value shapes described in the user message. Emit nothing else."
)
ANTHROPIC_JSON_TOOL: Dict[str, Any] = {
    "name": JSON_TOOL_NAME,
    "description": JSON_TOOL_DESCRIPTION,
    "input_schema": {"type": "object", "properties": {}, "additionalProperties": True},
}

PROVIDER_LABELS = {"anthropic": "Anthropic (Claude)", "openai": "OpenAI"}

# Server-side tools can hand the turn back with stop_reason="pause_turn" on long
# runs. Continue the turn this many times before giving up.
_MAX_PAUSE_CONTINUATIONS = 4


class ProviderError(RuntimeError):
    """Raised for provider-level problems the UI should show verbatim."""


class TruncatedResponse(ProviderError):
    """The model hit its output cap before finishing."""


# ---------------------------------------------------------------- detection --
def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def openai_key() -> str:
    return _env("OPENAI_API_KEY")


def anthropic_key() -> str:
    return _env("ANTHROPIC_API_KEY")


def provider() -> Optional[str]:
    """The active text provider, or None when no key is configured."""
    if anthropic_key():
        return "anthropic"
    if openai_key():
        return "openai"
    return None


def model() -> str:
    """Resolve the model id for the active provider."""
    active = provider()
    if active is None:
        return ""

    if active == "anthropic":
        override, default = _env("RoleIQ_MODEL_ANTHROPIC"), ANTHROPIC_DEFAULT_MODEL
    else:
        override, default = _env("RoleIQ_MODEL_OPENAI"), OPENAI_DEFAULT_MODEL

    if override:
        return override

    # A stale RoleIQ_MODEL left over from single-provider deployments must not
    # leak an OpenAI model id into an Anthropic run, or vice versa.
    legacy = _env("RoleIQ_MODEL")
    if legacy and legacy.lower().startswith("claude") == (active == "anthropic"):
        return legacy

    return default


def voice_available() -> bool:
    """Recorded-answer transcription needs an OpenAI key, always."""
    return bool(openai_key())


def status() -> Dict[str, Any]:
    """Snapshot for the sidebar and startup checks."""
    active = provider()
    return {
        "provider": active,
        "provider_label": PROVIDER_LABELS.get(active, "none"),
        "model": model(),
        "connected": active is not None,
        "voice": voice_available(),
        "openai_key": bool(openai_key()),
        "anthropic_key": bool(anthropic_key()),
        "both_keys": bool(openai_key() and anthropic_key()),
    }


def _active_or_raise() -> str:
    active = provider()
    if active is None:
        raise ProviderError(
            "No AI provider is configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "in .env or deployment secrets."
        )
    return active


def _truncated(max_tokens: int) -> TruncatedResponse:
    return TruncatedResponse(
        "%s stopped at the %d-token output cap before finishing its reply. "
        "Raise RoleIQ_JSON_MAX_TOKENS (or RoleIQ_MAX_TOKENS) and retry."
        % (PROVIDER_LABELS.get(provider(), "The model"), max_tokens)
    )


# ------------------------------------------------------------------ clients --
def openai_client():
    key = openai_key()
    if not key:
        raise ProviderError(
            "OPENAI_API_KEY is not configured. Add it to .env or deployment secrets."
        )
    from openai import OpenAI

    return OpenAI(api_key=key)


def anthropic_client():
    key = anthropic_key()
    if not key:
        raise ProviderError(
            "ANTHROPIC_API_KEY is not configured. Add it to .env or deployment secrets."
        )
    from anthropic import Anthropic

    return Anthropic(api_key=key)


# -------------------------------------------------------------- text calls --
def _openai_text(system: str, user: str, web: bool, max_tokens: int) -> Tuple[str, bool]:
    kwargs: Dict[str, Any] = {
        "model": model(),
        "instructions": system,
        "input": user,
        "max_output_tokens": max_tokens,
    }
    if web:
        kwargs["tools"] = [OPENAI_WEB_SEARCH_TOOL]
    response = openai_client().responses.create(**kwargs)
    truncated = getattr(response, "status", None) == "incomplete"
    return response.output_text, truncated


def _anthropic_block_text(content) -> str:
    parts: List[str] = []
    for block in content or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(p for p in parts if p).strip()


def _anthropic_text(system: str, user: str, web: bool, max_tokens: int) -> Tuple[str, bool]:
    client = anthropic_client()
    kwargs: Dict[str, Any] = {
        "model": model(),
        "max_tokens": max_tokens,
        "system": system,
    }
    if web:
        kwargs["tools"] = [ANTHROPIC_WEB_SEARCH_TOOL]

    messages: List[Dict[str, Any]] = [{"role": "user", "content": user}]
    collected: List[str] = []
    truncated = False

    for _ in range(_MAX_PAUSE_CONTINUATIONS + 1):
        response = client.messages.create(messages=messages, **kwargs)
        text = _anthropic_block_text(response.content)
        if text:
            collected.append(text)
        stop = getattr(response, "stop_reason", None)
        if stop == "max_tokens":
            truncated = True
            break
        if stop != "pause_turn":
            break
        messages = messages + [{"role": "assistant", "content": response.content}]
    else:
        # Every iteration kept returning pause_turn -- the continuation cap
        # was actually hit rather than the turn completing naturally. Not
        # raised as TruncatedResponse: the cause is different (continuation
        # cap, not the token cap) and this still returns usable partial text.
        _logger.warning(
            "Anthropic pause_turn continuation cap (%d) reached; reply may be incomplete.",
            _MAX_PAUSE_CONTINUATIONS,
        )

    return "\n".join(collected).strip(), truncated


def _text_call(system: str, user: str, web: bool, max_tokens: int) -> Tuple[str, bool]:
    if _active_or_raise() == "anthropic":
        return _anthropic_text(system, user, web, max_tokens)
    return _openai_text(system, user, web, max_tokens)


def ai_text(
    system: str,
    user: str,
    web: bool = False,
    max_tokens: int = DEFAULT_TEXT_MAX_TOKENS,
) -> str:
    """Free-text generation against the active provider."""
    text, _ = _text_call(system, user, web, max_tokens)
    return text


# ------------------------------------------------------- structured output --
_ANTHROPIC_TOOL_HINTS = ("input_schema", "tool_choice", "tools.0", "tools:", "tools[")


def _anthropic_json(system: str, user: str, max_tokens: int) -> Optional[Dict[str, Any]]:
    """Force a tool call so the payload arrives already parsed."""
    try:
        response = anthropic_client().messages.create(
            model=model(),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[ANTHROPIC_JSON_TOOL],
            tool_choice={"type": "tool", "name": JSON_TOOL_NAME},
        )
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001 - narrow by message, re-raise the rest
        message = str(exc).lower()
        if any(hint in message for hint in _ANTHROPIC_TOOL_HINTS):
            return None  # API rejected the tool wrapper; fall back to text mode
        raise

    if getattr(response, "stop_reason", None) == "max_tokens":
        raise _truncated(max_tokens)

    for block in response.content or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == JSON_TOOL_NAME:
            data = block.input
            if isinstance(data, dict) and data:
                return data
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            data = block.get("input")
            if isinstance(data, dict) and data:
                return data
    return None


_OPENAI_FORMAT_HINTS = ("format", "json_object", "unsupported", "unknown parameter")


def _openai_json(system: str, user: str, max_tokens: int) -> Optional[Dict[str, Any]]:
    """Ask the Responses API for a guaranteed-valid JSON object."""
    kwargs: Dict[str, Any] = {
        "model": model(),
        "instructions": system,
        "input": user,
        "max_output_tokens": max_tokens,
        "text": {"format": {"type": "json_object"}},
    }
    try:
        response = openai_client().responses.create(**kwargs)
    except TypeError:
        return None  # SDK too old for text.format; fall back to text mode
    except Exception as exc:  # noqa: BLE001 - narrow by message, re-raise the rest
        message = str(exc).lower()
        if any(hint in message for hint in _OPENAI_FORMAT_HINTS):
            return None
        raise

    if getattr(response, "status", None) == "incomplete":
        raise _truncated(max_tokens)

    data = _loads_or_none(response.output_text)
    return data if isinstance(data, dict) else None


def _structured_json(system: str, user: str, max_tokens: int) -> Optional[Dict[str, Any]]:
    if _active_or_raise() == "anthropic":
        return _anthropic_json(system, user, max_tokens)
    return _openai_json(system, user, max_tokens)


# ------------------------------------------------------------- json rescue --
def _loads_or_none(text: Any) -> Any:
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _strip_fences(raw: str) -> str:
    """Return the contents of a fenced block, or the whole string if unfenced."""
    text = (raw or "").strip()
    match = re.search(r"```(?:json|JSON)?\s*(.*?)\s*```", text, re.S)
    if match:
        return match.group(1).strip()
    # Unterminated fence (a truncated reply) - drop the opener.
    return re.sub(r"^```(?:json|JSON)?\s*", "", text).strip()


def _balanced_objects(text: str) -> Iterator[str]:
    """Yield top-level {...} spans, respecting string literals and escapes."""
    depth = 0
    start = None
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
                if depth == 0 and start is not None:
                    yield text[start : index + 1]
                    start = None


def parse_json_text(raw: str) -> Optional[Dict[str, Any]]:
    """Best-effort recovery of a JSON object from prose-wrapped model output."""
    stripped = _strip_fences(raw)
    for candidate in ((raw or "").strip(), stripped):
        data = _loads_or_none(candidate)
        if isinstance(data, dict):
            return data
    for candidate in _balanced_objects(stripped):
        data = _loads_or_none(candidate)
        if isinstance(data, dict):
            return data
    return None


_REPAIR_SYSTEM = (
    "You repair malformed JSON. Return the same data as one valid JSON object. "
    "Preserve every field and value that can be recovered, close anything the "
    "input left unterminated, and drop any trailing fragment that cannot be "
    "completed. Add no commentary and invent no new content."
)


def _repair_json(raw: str, max_tokens: int) -> Optional[Dict[str, Any]]:
    """One rescue attempt on output that would not parse."""
    if not (raw or "").strip():
        return None
    user = "Malformed JSON to repair:\n\n" + raw[:60000]
    try:
        data = _structured_json(_REPAIR_SYSTEM, user, max_tokens)
    except TruncatedResponse:
        return None
    if isinstance(data, dict) and data:
        return data
    text, _ = _text_call(_REPAIR_SYSTEM, user, False, max_tokens)
    return parse_json_text(text)


def ai_json(
    system: str,
    user: str,
    web: bool = False,
    max_tokens: int = DEFAULT_JSON_MAX_TOKENS,
) -> Dict[str, Any]:
    """Structured generation against the active provider.

    Non-search calls use the provider's native structured output, so the result
    is parsed JSON rather than text that has to survive a regex. Search calls
    cannot force a tool, so they fall back to extraction and a repair pass.
    """
    _active_or_raise()

    if not web:
        data = _structured_json(system, user, max_tokens)
        if isinstance(data, dict) and data:
            return data

    text, truncated = _text_call(system, user, web, max_tokens)

    data = parse_json_text(text)
    if isinstance(data, dict):
        return data

    if truncated:
        raise _truncated(max_tokens)

    data = _repair_json(text, max_tokens)
    if isinstance(data, dict):
        return data

    preview = (text or "").strip().replace("\n", " ")[:200]
    raise ProviderError(
        "%s returned a reply that is not valid JSON and could not be repaired. "
        "Retry the operation. First 200 characters: %s"
        % (PROVIDER_LABELS.get(provider(), "The model"), preview or "(empty reply)")
    )


# --------------------------------------------------------------- voice path --
def transcribe(file_path: str) -> str:
    """Speech-to-text. OpenAI only, by design -- Anthropic has no audio API."""
    if not voice_available():
        raise ProviderError(
            "Voice transcription requires OPENAI_API_KEY. Anthropic does not expose "
            "a speech-to-text endpoint, so recorded answers always route to OpenAI."
        )
    with open(file_path, "rb") as handle:
        result = openai_client().audio.transcriptions.create(
            model=TRANSCRIBE_MODEL, file=handle
        )
    return result.text
