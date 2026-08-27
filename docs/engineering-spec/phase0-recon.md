# Phase 0: Total Repo Reconnaissance

RoleIQ, D:\dev\roleiq, github.com/MadewellRD/roleiq. Recorded 2026-08-27. Every tracked file read in full; nothing sampled.

## Stack, languages, versions

Python 3.14.2 (dev venv), Streamlit app, single-process, local-first. No frontend framework beyond Streamlit's own rendering — no separate JS/TS build.

Pinned exact (`requirements.txt`):
```
streamlit==1.62.0
openai==3.4.0
anthropic==1.1.0
pypdf==6.16.2
python-docx==1.2.0
python-dotenv==1.2.3
pydantic==2.13.4
cryptography==50.0.1
```
Dev-only (`requirements-dev.txt`): `pytest==9.1.1`, plus `-r requirements.txt`.

## Entry points and runtime topology

- `app.py` (611 lines) — the entire UI and orchestration layer. `streamlit run app.py` or via `run-roleiq.ps1`. Single Streamlit session per browser tab; no multi-user isolation, no auth (documented, accepted-by-design for a single-user local tool).
- `ai_provider.py` (490 lines) — provider abstraction (Anthropic/OpenAI), model selection, structured-output handling, JSON repair.
- `role_schema.py` (99 lines) — Pydantic contract validation for the `analyze()` payload, added to close a silent-blank-page defect.
- `db_crypto.py` (78 lines) — Fernet encryption for SQLite narrative columns.
- `check_providers.py` (77 lines) — standalone live-call smoke test, run manually.
- `run-roleiq.ps1` (233 lines) — Windows launch script: venv setup, dependency install, compile check, key prompt, launch.

No server component beyond Streamlit's own dev server. No queue, no background worker, no separate API layer. `.streamlit/config.toml` binds to `127.0.0.1` explicitly, XSRF and CORS protection both on.

## Build, test, lint commands — current pass state, verified this session

- `python -m py_compile app.py ai_provider.py check_providers.py db_crypto.py role_schema.py` — **PASS**.
- `pytest -q` — **60 passed**, 0 failed, 4 deprecation warnings (see Dead/duplicated/half-finished below). No network, no API key required for any test.
- No linter configured (no `ruff`/`flake8`/`.flake8`/`pyproject.toml` lint config found anywhere in the tree). This is a real gap, not a suite that quietly passed.
- No `pyproject.toml` at all — dependency and tooling config lives only in `requirements*.txt`.

## CI configuration and current pipeline state

`.github/workflows/ci.yml`: on push/PR to `main`, checkout → setup-python 3.14 → `pip install -r requirements-dev.txt` → `py_compile` across all 5 modules → `pytest -q`. No secrets configured (none needed, no live-call tests).

**Current state: red.** Last 4 runs all failed in 3-4 seconds with `"your account is locked due to a billing issue"` — a GitHub Actions account-level billing lock, not a code or workflow defect. This is a pre-existing, already-flagged condition, not new to this recon.

Local substitute exists: `scripts/pre-push` (tracked) installs to `.git/hooks/pre-push`, runs the same `py_compile` + `pytest` checks, blocks the push on failure. Verified firing correctly on the last two pushes today. `README.md`'s "Local CI" section documents the one-time install step per clone.

No branch protection on `main` (`gh api repos/.../branches/main/protection` → 404, "Branch not protected"). Every commit to date has gone **directly to `main`** — no branches, no PRs opened, zero PR history. This is the single biggest structural gap against the go-live protocol's Phase 6 requirement ("No direct commits to main. Branch per task, named to the GL id. PR per change").

## Environment and secrets surface

`.env.example` documents all env vars, placeholders only, no real values. Verified: no hardcoded API-key-shaped strings, AWS-key-shaped strings, or PEM private-key blocks anywhere in tracked source (`*.py`, `*.ps1`, `*.toml`, `*.yml`, `*.md`, `*.txt`). No `.env` or credential-shaped filename tracked in git.

Secrets in use: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` (never logged, never written to disk, confirmed by full-file read this session and in the earlier security-hardening pass). `RoleIQ_DB_KEY` (Fernet key for DB-at-rest encryption; auto-generates an ephemeral, loudly-warned, process-only key if unset). `RoleIQ_TRANSCRIBE_MODEL`, `RoleIQ_MODEL_ANTHROPIC`, `RoleIQ_MODEL_OPENAI`, `RoleIQ_MODEL` (legacy), `RoleIQ_ROLE_CONTEXT_ENABLED`, `RoleIQ_MAX_UPLOAD_MB`, `RoleIQ_MAX_PDF_PAGES`, `RoleIQ_LOG_LEVEL`, `RoleIQ_DB` (path override) — all read via `os.getenv`, all documented in `.env.example`.

`roleiq.log` (diagnostic logging, exception-only content, not secrets) and `roleiq.db` (Fernet-encrypted narrative columns) are both gitignored and correctly absent from the tracked tree; both were present as local artifacts on disk from today's testing and have been cleaned up as part of this recon.

## Dead code, duplicated code, half-finished work

- `load_candidate()` (`app.py`) — fully implemented, zero call sites. **Intentionally dead**, documented in-code and in commit history: kept as the tested read-side counterpart to `save_candidate`, not wired into the UI because there is no "resume a previous session" feature (explicitly out of scope, documented in three places: code comment, README's "Guided flow" section, and the wizard-conversion commit message).
- `datetime.utcnow()` — used in `app.py` (2 call sites, `save_candidate`/`save_session`), triggers a `DeprecationWarning` under Python 3.14 (`datetime.now(datetime.UTC)` is the replacement). Not yet fixed. Real, small, live technical debt — goes in the backlog.
- No duplicated logic found across the 5 Python modules — each has a single clear responsibility (UI/orchestration, provider abstraction, schema validation, encryption, smoke test) with no copy-pasted blocks between them.
- Two dangling local git branches, `clean-main` and `rewrite-main`, both artifacts of an earlier history rewrite (used once, this session, to strip a Co-Authored-By trailer before the repo went public). Neither has unique commits beyond what `main` already contains upstream of the rewrite point. Local-only, never pushed, harmless, but unused — cleanup candidate.
- No stub functions, no `NotImplementedError`, no placeholder return values found anywhere in the 5 modules (verified by full-file read across all of them this session and in the prior security/wizard passes).

## Existing docs and specs

- `README.md` — substantial and current: architecture overview, AI provider precedence table, voice-is-OpenAI-only rationale, "Data at rest" (encryption), "Guided flow" (wizard), "Included" feature list, "Run" instructions, "Structured output" pipeline explanation, "Valid JSON is not valid RoleIQ data" (the contract-validation fix), "Verifying a deployment", "Development" (pytest), "Local CI", "License". No staleness found against current code during this recon — the README was actively maintained alongside every feature commit today.
- `LICENSE` — Apache 2.0, correctly attributed.
- No `docs/` directory existed before this recon — `docs/engineering-spec/` is new, created this phase.
- No architecture decision records, no formal requirements doc, no test plan document — these exist only as prose inside `README.md` and commit messages. This is itself a Phase 3 finding surface (`product-requirements-desk`, `architecture-design-desk`), not resolved here.

## Git state

- Current branch: `main`, up to date with `origin/main` (`b411a47`), nothing to push.
- Uncommitted work at scan time: none tracked. One untracked directory, `.claude/` (contains `settings.json` — a permissions allowlist built by an earlier `/fewer-permission-prompts` run this session — and `settings.local.json`, pre-existing). Per protocol rule ("uncommitted work found at scan time gets committed or discarded deliberately before new work starts"): `.claude/settings.local.json` is a personal/local Claude Code setting file, not a project artifact — left untracked, correct as-is. `.claude/settings.json` is a real, shareable permissions allowlist (`Bash(tasklist *)`) that was built but never committed. Decision: commit it now, deliberately, as part of Phase 0 cleanup rather than carrying it forward as loose state — it's a one-line, low-risk, already-reviewed addition from earlier in this same session.
- 14 commits total on `main`, all direct (no PR history, no branches used for feature work — see CI section above).
- 12 GitHub issues, all filed and all closed via `Fixes #N` commit trailers — good traceability discipline already in place, just not yet paired with a branch/PR workflow.
- Two dangling local branches (`clean-main`, `rewrite-main`) noted above.
