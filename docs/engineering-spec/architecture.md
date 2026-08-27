# Architecture Decisions

Lightweight ADRs for the real decisions already embedded in the codebase, recorded here for the first time in Phase 2 since none existed as standalone artifacts before this protocol run. Each is derived from actual code and commit history (Phase 0), not proposed fresh.

## Component boundaries

```
app.py            UI, orchestration, session_state, wizard flow, SQLite calls
ai_provider.py     Anthropic/OpenAI abstraction, model selection, structured output, JSON repair
role_schema.py     Pydantic contract for the analyze() payload; normalization + validation
db_crypto.py       Fernet encryption/decryption for SQLite narrative columns
check_providers.py Standalone live-call smoke test (manual, not part of the app or CI)
```

Interface contracts: `app.py` never talks to Anthropic/OpenAI SDKs directly — everything routes through `ai_provider.ai_json`/`ai_provider.ai_text`. `app.py` never writes plaintext narrative content to SQLite — everything routes through `db_crypto.encrypt_text`/`decrypt_text`. `role_schema.validate_analysis` sits between `ai_provider`'s output and everything `app.py` does with an analysis payload. These are consistent boundaries, not incidental — verified by full-file read, no direct SDK or sqlite-plaintext calls found outside their owning module.

## ADR-01: Exactly one active text provider, chosen by key presence

Anthropic wins when both `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are set. Voice transcription is a deliberate exception, always OpenAI, because Anthropic has no speech-to-text endpoint — this is a real API capability gap, not a design preference. Rationale in `ai_provider.py`'s own module docstring. Alternative considered and rejected implicitly by the code: routing different call types to different providers based on capability — not built, would add real complexity for a single-user tool with no need to optimize per-call provider choice.

## ADR-02: Structured output first, text-extraction-and-repair as fallback

Every non-search call uses the provider's native structured-output mechanism (forced tool call on Anthropic, `json_object` format on OpenAI). Search calls can't force a tool alongside server-side search, so those fall back to fence-stripping + a balanced-brace scan + one repair pass via a second LLM call. This is a real, tested degradation ladder (`ai_provider.py:parse_json_text`, `_repair_json`), not a single fragile path.

## ADR-03: A schema contract sits between the provider and the UI

Added mid-session after a real bug: the Anthropic tool schema is deliberately permissive (`additionalProperties: true`) because `ai_json()` is shared across call sites with different shapes, so nothing at the API level enforced `analyze()`'s requested fields. A technically-valid-but-wrong-shaped reply used to render as a silently empty UI section. `role_schema.py` closes this for the highest-value call (`analyze()`) specifically — not applied to the other nine `ai_json`/`ai_call` sites. **Open scope question, not yet decided**: should the same contract-validation pattern extend to `build_experience_graph`, `training_module`, `grade_answer`, etc., or is `analyze()` the only call site where a malformed reply causes a genuinely silent (vs. merely incomplete) UI failure? Phase 3's `architecture-design-desk` pass should make this call explicitly rather than leaving it implicit.

## ADR-04: Single-user, local-only, no authentication

No login, no session isolation beyond one Streamlit browser tab, no remote binding (`.streamlit/config.toml` pins `address = 127.0.0.1`). This is a stated, repeated decision (README, code comments, this session's security-hardening pass), not an oversight — the alternative (multi-user auth) was explicitly evaluated and rejected as out of scope for what RoleIQ is today.

## ADR-05: Encryption at rest for narrative content, not metadata

`resume`, `experience_graph`, `jd`, `analysis`, `context`, `history` are Fernet-encrypted; `id`, `name`, `candidate_id`, `role`, `company`, timestamps are plain. Rationale: the encrypted columns carry PII and interview transcripts, the plain columns are short identifiers/labels that a future "list saved candidates" feature would need to query without a full-table decrypt. Key management is deliberately minimal — no rotation tool, no KMS integration; losing `RoleIQ_DB_KEY` means the old data is unrecoverable, accepted as reasonable for a single-user local tool.

## ADR-06: Candidate identity is content-derived, not random

`candidate_id()` hashes the cleaned resume text. Re-uploading the same resume updates the same row instead of creating a duplicate — an intentional dedup convenience under the single-user threat model, not a defect. Explicitly documented as an accepted-risk decision (would need to change if RoleIQ ever became multi-user, since two different people's byte-identical resume text would then collide).

## ADR-07: Wizard state is session-only, not persisted

`wizard_step`, `wizard_visited`, `trained_modules` live in `st.session_state` only. Rationale, stated at the time: `load_candidate()` (the read-side of the persistence layer) is already unwired — nothing in the app today reloads *any* prior state, including `analysis`/`graph`/`history`, all of which already persist to SQLite but are never read back. Persisting wizard-only state on top of that would write data nothing can currently read. Revisit if/when session-resume becomes an actual feature (see requirements.md's non-goals).

## ADR-08: Prompt injection mitigated by explicit delimiting, not input sanitization

All 10 LLM-calling functions wrap user-supplied content in `<untrusted_input source="...">` tags plus a system-prompt instruction to treat tagged content as data, never instructions. Explicitly documented as best-effort, not a hard boundary — a sufficiently crafted payload could still resemble the tag itself; the mitigation is a real, tested reduction in attack surface, not a claimed elimination of it.

## What is not yet decided

Everything in this file describes decisions already made. It does not yet contain a decision about deployment topology, versioning/release strategy, or whether the single-provider-per-run model should ever change — these are open, not implicitly resolved by omission, and Phase 3/4 should treat them as such.
