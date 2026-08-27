"""RoleIQ provider smoke test.

Makes one small live call against whichever provider is active and reports
which path served it. Run it from the same shell that has your API key:

    .venv\\Scripts\\python.exe check_providers.py

Costs a few hundred tokens. Exit code 0 means the app's JSON path is healthy.
"""

import json
import sys

from dotenv import load_dotenv

load_dotenv()

import ai_provider  # noqa: E402

PROBE_SYSTEM = "You are a fixture used to smoke-test a JSON pipeline."
PROBE_USER = (
    "Return JSON with exactly these keys:\n"
    '{"ok": true, "provider_seen": "<the company that made you>", '
    '"competencies": ["one", "two", "three"]}'
)


def main() -> int:
    state = ai_provider.status()

    print("Provider : %s" % state["provider_label"])
    print("Model    : %s" % (state["model"] or "(none)"))
    print("Voice    : %s" % ("available (OpenAI)" if state["voice"] else "unavailable"))
    if state["both_keys"]:
        print("Note     : both keys present, Anthropic takes precedence")
    print("")

    if not state["connected"]:
        print("FAIL  No API key found.")
        print("      Set ANTHROPIC_API_KEY (or OPENAI_API_KEY) in this shell, or")
        print("      copy .env.example to .env and put the key there so it persists.")
        return 1

    print("[1/2] Native structured output (forced tool / json_object)...")
    try:
        structured = ai_provider._structured_json(PROBE_SYSTEM, PROBE_USER, 2000)
    except Exception as exc:  # noqa: BLE001 - this is the diagnostic
        print("      ERROR %s: %s" % (type(exc).__name__, exc))
        structured = None

    if isinstance(structured, dict) and structured:
        print("      PASS  parsed natively, no text scraping needed")
        print("      %s" % json.dumps(structured)[:200])
    else:
        print("      SKIP  provider declined the structured wrapper")
        print("            (the app falls back to text extraction + repair)")

    print("")
    print("[2/2] Full ai_json path as the app calls it...")
    try:
        data = ai_provider.ai_json(PROBE_SYSTEM, PROBE_USER, max_tokens=2000)
    except Exception as exc:  # noqa: BLE001 - this is the diagnostic
        print("      FAIL  %s: %s" % (type(exc).__name__, exc))
        return 1

    if not isinstance(data, dict) or not data:
        print("      FAIL  empty result")
        return 1

    print("      PASS  %s" % json.dumps(data)[:200])
    print("")
    print("RoleIQ's JSON pipeline is healthy on %s." % state["provider_label"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
