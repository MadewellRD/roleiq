# RoleIQ — Walk the Walk. Talk the Talk.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

RoleIQ is a role-specific SME immersion and interview-preparation MVP.

## V1 architecture

JD + Resume -> Experience Graph -> Competency/Readiness Model -> SME Training -> Interview Simulation -> Answer History -> Adaptive Curriculum -> Battle Card

The Role Context Plane is implemented behind a feature flag but is **disabled by default**. nMCP / Context Resolution Plane integration is intentionally deferred until the planned production context layer is live.

Set `RoleIQ_ROLE_CONTEXT_ENABLED=1` only when public company/technical context research is desired and the deployment has web-search capability.

## AI providers

RoleIQ runs against **either** Anthropic **or** OpenAI — never both at once for text. The active provider is chosen purely by which API key is present:

| Keys present | Active provider |
| --- | --- |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) |
| `OPENAI_API_KEY` | OpenAI |
| both | Anthropic (takes precedence) |
| neither | None — the UI stays input-only |

All provider logic lives in `ai_provider.py`; `app.py` only calls `ai_call()`. Server-side web search is mapped per provider (`web_search` on OpenAI Responses, `web_search_20250305` on Anthropic Messages), so the Role Context Plane and evidence-backed research work on either side.

Default models: `claude-sonnet-5` (Anthropic), `gpt-5.6-luna` (OpenAI). Override with `RoleIQ_MODEL_ANTHROPIC` / `RoleIQ_MODEL_OPENAI`. A legacy `RoleIQ_MODEL` value is still honoured, but only when it names a model belonging to the active provider — a stale OpenAI model id cannot leak into an Anthropic run.

### Voice is OpenAI-only, by design

Anthropic exposes no speech-to-text endpoint. Recorded-answer transcription is therefore wired explicitly to `OPENAI_API_KEY` and runs on OpenAI even when Claude is handling text. Without that key the voice section hides itself and typed answers work as normal.

## Data at rest

RoleIQ persists to a local SQLite file (`roleiq.db` by default, override with `RoleIQ_DB`). The narrative-content columns — `resume`, `experience_graph`, `jd`, `analysis`, `context`, and `history` (full interview Q&A transcripts) — are encrypted with [Fernet](https://cryptography.io/en/latest/fernet/) symmetric encryption before they're written. Short metadata columns (ids, role, company, timestamps) are left plain.

Set `RoleIQ_DB_KEY` to a generated key to persist encrypted data across restarts:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If `RoleIQ_DB_KEY` is unset, RoleIQ generates a throwaway key for that process only and warns loudly — anything saved becomes unreadable the moment the app restarts. There is no key-rotation or re-encryption tool; losing the key means deleting `roleiq.db` and starting fresh, which is an acceptable tradeoff for a single-user local tool. `roleiq.log` (diagnostic error/exception logging — see below) is **not** encrypted like the database is.

## Included

- PDF/DOCX/TXT/MD JD and resume ingestion
- Persistent SQLite candidate Experience Graph
- JD-to-experience correlation with Experienced / Adjacent / Learned / Unknown classification
- SME training modules with architecture, tradeoffs, failure modes, language upgrades, and truth boundaries
- Interviewer persona modeling
- Adaptive interview curriculum based on answer history
- Recorded voice-answer transcription and grading (OpenAI key required)
- Evidence-backed technical research mode
- Exportable Markdown interview battle card
- Deferred Role Context Plane adapter for later activation

## Run

```bash
cp .env.example .env
# set ANTHROPIC_API_KEY (or OPENAI_API_KEY)
streamlit run app.py
```

On Windows, `run-roleiq.ps1` creates the venv, installs dependencies, validates the source, reports which provider is active, and launches the app.

### Structured output

Analysis, grading, training and curriculum calls all return JSON. Rather than
scraping JSON out of prose, `ai_json()` uses each provider's native structured
output — a forced `emit_json` tool call on Anthropic, `json_object` response
format on OpenAI — so the payload arrives already parsed.

Web-search calls cannot force a tool alongside a server-side search, so those
take a hardened path: fence stripping, a balanced-brace scan that respects
string literals, then a single repair pass. Every fallback degrades one step at
a time; if a provider rejects the structured wrapper entirely, the call reverts
to plain text extraction rather than failing.

Output caps are reported as caps. A reply cut off mid-object raises a message
naming the limit and the env var to raise, instead of a `JSONDecodeError`
pointing at a column number. Defaults: `RoleIQ_JSON_MAX_TOKENS=16000`,
`RoleIQ_MAX_TOKENS=7000`.

### Valid JSON is not valid RoleIQ data

`ai_json()` guarantees the reply parses as JSON. It does not guarantee the
reply has the fields RoleIQ actually asked for — the Anthropic tool schema is
deliberately permissive (`additionalProperties: true`) because its shape
differs per call site, so nothing at the API level enforces `analyze()`'s
requested `competencies`/`training_priorities`/etc. Without a check, a
technically-valid-but-wrong-shaped reply used to render as an empty UI
section instead of a visible failure.

`role_schema.py` closes that gap for the role-analysis payload: it normalizes
a small set of known key variants (`summary` → `executive_summary`,
`competency_graph` → `competencies`, and similar — never overwriting a
correctly-named field, never inventing a value), then validates against a
Pydantic model requiring at least one competency. A contract mismatch raises
`ContractError` with a diagnostic — expected fields, the keys actually
returned, provider, and model — shown directly in the UI instead of a blank
section.

## Verifying a deployment

```bash
python check_providers.py
```

Reports the active provider and model, then makes one small live call to confirm
the JSON pipeline works end to end. Run it from the shell that holds your API
key. Note that `run-roleiq.ps1` sets an interactively-entered key for that
session only — put the key in `.env` if you want it to persist across launches.

## Development

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite covers candidate ID hashing, provider selection precedence, JSON
repair/balanced-object parsing, file extraction (including corrupt-file
handling), SQLite save/load round-trips (including verifying that stored data
is actually ciphertext, not plaintext), and prompt-injection wrapping — all
without network access or an API key. CI (`.github/workflows/ci.yml`) runs
`py_compile` across every module plus the full suite on every push/PR to
`main`.

### Local CI

`git hooks` aren't tracked by git, so after cloning, install the pre-push
check once:

```bash
cp scripts/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push
```

It runs the same `py_compile` + `pytest` checks as CI and blocks the push if
either fails — the active enforcement mechanism while GitHub Actions is
unavailable (see CI status in the repo's Actions tab). Remote CI stays
configured and will resume working automatically once that's resolved.

Full live UI/API execution requires installing the packages in
`requirements.txt` and supplying an API key; see "Verifying a deployment"
above for a one-shot live smoke check via `check_providers.py`.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
