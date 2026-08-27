# Phase 1: Status Assessment

From the Phase 0 scan only. 2026-08-27.

## Where we are

RoleIQ works. Paste a JD and resume, it builds an experience graph, correlates it against the JD into a competency readiness map, walks the learner through sequential SME training ordered by interview risk, runs adaptive interview practice with grading, and produces a downloadable battle card. The core loop is real, not a mockup — the code that runs it is the code that was read in Phase 0, end to end, no stubs.

The provider layer, encryption, prompt-injection mitigation, structured-output contract validation, and the wizard UI were all built and verified this session, each with real tests (60 passing, no network dependency) and, for the wizard specifically, a live AppTest-driven click-through that exercised the actual button handlers. This is not aspirational — it is checked-in, pushed, and currently working.

What RoleIQ is **not**: a hosted, multi-user, deployed service. It is a single-user local tool, explicitly and repeatedly documented as such (README, code comments, commit messages). There is no server to deploy, no multi-tenant data model, no production environment beyond "someone's machine with a venv." This is a real constraint on what "go live" can mean here, and Phase 3/4 need to work within it rather than manufacture a deployment story that doesn't exist.

## What works

- File ingestion (PDF/DOCX/TXT/MD) with size/page caps and sanitized error handling on corrupt input.
- Provider abstraction: Anthropic-first, OpenAI fallback, native structured output with a JSON-repair fallback path, truncation reported as truncation.
- `role_schema.py` contract validation on the highest-value AI call (`analyze()`) — a malformed reply now fails loudly with a diagnostic instead of rendering a blank UI section. This was a real, previously-shipped bug, found and fixed this session.
- Encryption at rest (Fernet) for every sensitive SQLite column (resume, JD, analysis, history), with a documented, tested failure mode for a missing/wrong key.
- Prompt-injection mitigation across all 10 LLM-calling functions.
- Centralized exception logging, scoped to never log secrets or full prompt/response bodies.
- The wizard/guided-flow UI: step tracker, sequential SME-training lock by interview risk, Recommended-next guidance, all freely navigable post-Build.
- Local CI (`scripts/pre-push`) — verified firing and blocking correctly on every push this session.
- 60 automated tests, all passing, zero network dependency, zero API key dependency.
- Documentation (`README.md`) is current and was updated in the same commit as every feature it describes — no drift found in Phase 0.

## What is partial

- **Remote CI is red**, but not from a code defect — a GitHub Actions billing lock on the account, confirmed by the API's own error message, unfixable from inside this repo. Local CI is the working substitute and is documented as such. This stays `blocked`, not `in_progress`, until the account issue is resolved — that is a human action, not a task.
- **Test coverage of the UI layer itself is thin.** The 60 tests are strong on pure logic (JSON repair, encryption round-trips, provider selection, competency ordering) but the wizard's actual Streamlit interaction — the newest and most complex piece of UI code in the repo — has zero *permanent, committed* test coverage. It was verified once, ad hoc, with a throwaway script, then deleted. That verification needs to become a real test.
- **`datetime.utcnow()` deprecation warning** — small, live, already-surfacing technical debt in `app.py`.
- Two dangling local git branches from an earlier history rewrite — harmless, unused, should be cleaned up rather than carried forward indefinitely.

## What is missing entirely

Named plainly, not softened:

- **No branch/PR workflow has ever been used.** Every one of 15 commits went straight to `main`. No branch protection exists. This is the single largest gap against how the go-live protocol requires work to happen from here forward.
- **No lint configuration of any kind** — no `ruff`, no `flake8`, no `pyproject.toml`. `py_compile` catches syntax errors only, nothing about style, unused imports, or common bug patterns.
- **No architecture decision records and no standalone requirements document.** What exists lives as prose inside `README.md` and commit messages. That is real documentation, but it is not a requirements artifact a `product-requirements-desk` or `architecture-design-desk` audit can trace against.
- **No observability beyond local exception logging.** No metrics, no dashboards, no alerts, no SLOs — never built, never discussed before this protocol run.
- **No incident-response process or runbook** — never built. For a single-user local tool this may turn out to be legitimately N/A rather than a gap; Phase 3's `incident-response-desk` pass makes that call explicitly rather than this document assuming it.
- **No release/versioning discipline** — zero git tags, no CHANGELOG, no version string anywhere in the app itself.
- **No deployment target of any kind exists to audit** — this reshapes rather than skips the deployment-facing suites in Phase 3 (`deployment-desk`, `web-release-deployment-desk`, `web-observability-desk`, `incident-response-desk`): each needs to state plainly whether "go live" for a local single-user tool means something narrower than for a hosted service, not silently apply hosted-service assumptions.
- **No accessibility or SEO work has ever been done** — Streamlit's own defaults only, never evaluated.

## Ranked, by blocking severity

1. **Branch/PR workflow absence** — blocks every Phase 6 task from being executed to protocol. Must be adopted starting with the first GL task, no exceptions, no grace period.
2. **Phase 3 audit itself** — nothing below this list can be trusted as complete until it runs; it is the thing standing between "looks done" and "is done."
3. **Wizard UI test coverage gap** — the most recently shipped, most complex code has the thinnest safety net. Real risk of a regression shipping unnoticed.
4. **CI red / no branch protection** — real but partially mitigated by local CI already in place; full fix needs a human to clear the billing lock, tracked as `blocked`.
5. **No lint tooling** — cheap to add, currently zero cost being paid, but also zero value being captured.
6. **Missing formal requirements/architecture docs, no release/versioning discipline, dangling branches, `datetime.utcnow()` debt** — real, all backlog-worthy, none blocking.
