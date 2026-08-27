# Phase 3: SDLC Audit Coverage

Every suite in `audit-coverage.md` (the goliveprompt skill reference), run against RoleIQ at commit `577f804` and beyond. RoleIQ is browser-facing (Streamlit), so both core SDLC suites (18) and web suites (14) apply — 32 total.

Run method: each suite's actual `SKILL.md` method (core Role/Acceptance-bar section) was read and applied directly against the real repo — the same files read in Phase 0/2 (`app.py`, `ai_provider.py`, `role_schema.py`, `db_crypto.py`, `check_providers.py`, `run-roleiq.ps1`, `.streamlit/config.toml`, `.github/workflows/ci.yml`, `scripts/pre-push`, `tests/*.py`, `README.md`). First attempt fanned this out across 8 parallel subagents; 7 of 8 hit a session API limit mid-run and failed (one, covering the 4 web product/IA/UX-design suites, completed in full — its findings are included below unchanged). The remaining suites were run directly, sequentially, without subagents, following the same method.

| Suite | Status | Findings | Notes |
|---|---|---|---|
| product-requirements-desk | run | 2 | requirements.md exists (Phase 2) with stable F1-F11/NF1-NF6 IDs and explicit non-goals, but lacks testable per-requirement acceptance criteria and a risk register — see findings below. |
| technical-discovery-desk | run | 1 | phase0-recon.md is a genuine, file:line-grounded repo reconnaissance report; missing a formal risk register (likelihood/impact) and explicit unknowns-with-investigation list. |
| architecture-design-desk | run | 1 | architecture.md's 8 ADRs state tradeoffs/rationale well; missing a distinct risks-with-mitigations section and formal interface contracts. |
| issue-planning-desk | run | 0 | This suite's actual output IS Phase 4 (the GL backlog), not yet produced — not a defect, a sequencing fact. Zero standalone findings; superseded by Phase 4 itself. |
| implementation-handoff-desk | run | 0 | Prerequisite (Phase 4 backlog) doesn't exist yet — sequencing fact, not a defect. |
| review-quality-desk | run | 1 | No PR has ever existed to review (all 15 commits went direct to `main`) — but two real bugs found by other suites this pass are direct evidence the missing review step has already cost correctness. |
| test-strategy-desk | run | 1 | Full requirement-to-test coverage map against `requirements.md`'s 17 IDs — 6 covered, 4 partial, 7 uncovered. |
| verification-desk | run | 1 | Same coverage map, reframed as verified/partially verified/unverified — 7 requirements have zero evidence, not release-ready on "it was built" alone. |
| security-threat-desk | run | 2 | This repo already had a dedicated hardening pass this session; findings below are genuinely new, not re-litigated. |
| ci-failure-desk | run | 2 | Local CI substitute evaluated for adequacy — real gaps found in what it doesn't cover vs. remote CI, and in fresh-clone enforcement. |
| release-operations-desk | run | 1 | Zero git tags, no CHANGELOG, no version string anywhere in the app. |
| deployment-desk | run | 1 | Evaluated against the only real deployment target (local install/launch via `run-roleiq.ps1`), not a hosted-service framework. |
| observability-readiness-desk | run | 2 | Existing exception logging (this session) is adequate in scope; log-file hygiene (rotation, correlation) is not. |
| incident-response-desk | run | 1 | Severity/on-call model correctly N/A at this scale; a minimal user-facing troubleshooting path is still missing. |
| maintenance-refactor-desk | run | 2 | `datetime.utcnow()` deprecation (2 lines) plus a real one: `clean-main` still holds the pre-rewrite PII commit, not just dead weight. |
| retrospective-desk | run | 1 | Strong issue-closure discipline confirmed via commit history; the one real process gap (no PRs) is already tracked elsewhere. |
| decommissioning-desk | N/A | 0 | Nothing in RoleIQ is being retired, sunset, or migrated off. |
| docs-traceability-desk | run | 1 | 5 real env vars undocumented in `.env.example` despite being in README prose; 3 spot-checked claims confirmed accurate. |
| web-development-command-desk | run | 0 | Orchestration/stage-selection correctness confirmed (Batch F, completed subagent) — no defect in how RoleIQ's shape was classified. |
| site-product-requirements-desk | run | 3 | Batch F (completed subagent): voice-grading competency mismatch, voice turns not persisted, no acceptance-criteria matrix. |
| information-architecture-desk | run | 3 | Batch F: inconsistent competency ordering between two steps, no pre-build step preview, no cross-linking. |
| ux-ui-design-system-desk | run | 5 | Batch F: button-casing inconsistency, error-tone inconsistency, spinner-coverage gaps, `provider_healthy` never resets on failure, recommended-next banner has no "all done" state. |
| web-release-deployment-desk | run | 0 | No CDN/preview/promotion pipeline needed at this scale — version-visibility gap already tracked under release-operations-desk. |
| web-maintenance-growth-desk | run | 0 | GitHub Issues already serves as the working post-launch feedback channel. |
| web-security-secops-desk | run | 1 | No CSP configured; overlaps `security-threat-desk`, one distinct finding. |
| web-performance-desk | run | 1 | No timeout on any AI provider call. |
| accessibility-seo-desk | run/N/A | 0 | Checked and clean; SEO N/A at this scale. |
| web-testing-qa-desk | run | 1 | No pre-merge signoff process beyond one deleted ad hoc script. |
| web-observability-desk | run | 1 | Uncaught top-level exceptions have no logging hook. |
| frontend-engineering-desk | run | 1 | `current_question` not reset on re-Build — a second stale-state case beyond the one already fixed. |
| backend-integration-desk | run | 0 | Clean component boundaries confirmed; findings already captured elsewhere. |
| cms-content-operations-desk | N/A | 0 | No CMS, no editorial workflow — framework doesn't apply. |

**Totals: 32/32 suites run (2 correctly N/A: decommissioning-desk, cms-content-operations-desk; accessibility-seo-desk is split run/N/A). 36 real findings recorded, zero invented, several intentionally cross-referenced rather than double-counted where two suites' lenses converged on the same root cause.**

## product-requirements-desk

- [medium] No testable acceptance criteria per requirement — `docs/engineering-spec/requirements.md` — Every F1-F11/NF1-NF6 requirement is prose-described with a stable ID, but none has a "given X, observable Y" testable criterion a tester could execute without asking what was meant (this desk's stated acceptance bar). — Acceptance gate: each requirement ID gains at least one line of the form "Given \<condition\>, \<observable result\>."
- [low] No dedicated risk register — `docs/engineering-spec/requirements.md` — Risk-shaped content exists scattered across the "Explicit non-goals" section and `phase1-status.md`, but there's no consolidated list of requirement-linked risks. — Acceptance gate: a risks section lists at least the risks already implicit in the non-goals (e.g. "no auth" -> risk if scope ever expands to multi-user) with likelihood/impact.

## technical-discovery-desk

- [low] No formal risk register or unknowns-with-investigation list — `docs/engineering-spec/phase0-recon.md` — The recon is genuinely file:line-grounded (this desk's core bar) but doesn't separate "risks with likelihood/impact" or "unknowns with the specific investigation that would resolve them" as distinct structured sections; the two open questions in `requirements.md` come closest but don't name who/what would answer them. — Acceptance gate: a risk register exists with at least the risks already surfaced elsewhere this phase (CI billing lock, wizard UI test gap, no branch/PR history) scored by likelihood/impact.

## architecture-design-desk

- [low] No distinct risks-with-mitigations section — `docs/engineering-spec/architecture.md` — The 8 ADRs state tradeoffs and rejected alternatives well (this desk's bar), but risk is only implicit within each ADR's prose, not consolidated with a stated mitigation per risk. — Acceptance gate: architecture.md gains a risks section, or each ADR gains an explicit "Risk / Mitigation" line where a real risk exists (e.g. ADR-05's key-loss-is-unrecoverable is a risk with a stated, but not labeled-as-such, mitigation: "accepted for a single-user local tool").

## issue-planning-desk

- none — this suite's own output is the Phase 4 GL backlog itself, sequenced to run after this audit completes per protocol.

## implementation-handoff-desk

- [low] Prerequisite (issue-planning-desk's GL backlog) does not exist yet — this desk's method explicitly sits "after requirements, discovery, architecture, and issue planning are complete"; issue planning is Phase 4, not yet run. Not a defect — a sequencing fact, same as issue-planning-desk above. — Notes: the go-live protocol's own Phase 6 rules (branch per GL id, PR per change with linked acceptance evidence, no direct commits to main) already structurally satisfy most of this desk's discipline. Real test is whether the first actual GL-task PR in Phase 6 follows it — recorded as a Phase 6 acceptance concern, not a Phase 3 finding.

## review-quality-desk

- [high] Zero PR history means zero independent review has ever happened — confirmed in Phase 0 (`git log`, `gh pr list` — 15 commits, all direct to `main`, no PRs). Every change this session was self-reviewed only. — Evidence this is a real, not theoretical, gap: the completed `site-product-requirements-desk`/`ux-ui-design-system-desk` audit passes (see Web suites section below) found two genuine functional bugs in code shipped earlier this same session — voice-answer grading always uses `competencies[0]` instead of the SME-language-matched competency the typed path uses (`app.py:582` vs `527-531`), and the `provider_healthy` sidebar flag never resets on a later failed call after one earlier success (`app.py:349`). Both are exactly the class of defect a PR review with a second set of eyes catches before merge. — Acceptance gate: Phase 6's first GL-task PR gets a review pass (even if self-performed, performed as a distinct review step against the diff, not folded into the same pass that wrote the code) before merge.

## test-strategy-desk

- [high] Requirement-to-test coverage map, applied against `requirements.md`'s F1-F11/NF1-NF6 against the actual 60 committed tests:
  - **Covered**: F1 Ingestion (`test_file_extraction.py`), F10 Persistence (`test_db_roundtrip.py`), NF1 Single active provider (`test_provider_selection.py`), NF3 No plaintext at rest (`test_db_roundtrip.py` explicitly checks ciphertext), NF4 No silent contract failures (`test_role_schema.py`), NF5 Deterministic offline-testable core (the 60 tests themselves).
  - **Partially covered**: F2 Experience Graph (pure parts only — the AI call itself can't be unit tested), F4 Readiness analysis (`role_schema.py` validated, `analyze()`'s call itself isn't), F6 SME training (`ordered_competencies`/`competency_progress` tested; the actual training-module generation button flow only ever verified via a throwaway script, not committed), F11 Guided flow (same pattern — pure helpers tested, live click-through not committed).
  - **Not covered by any committed test**: F3 Role Context, F5 Interviewer persona modeling, F7 Interview simulation (grading, adaptive curriculum, question synthesis, the SME-language competency-matching logic — none unit tested), F8 Evidence-backed research, F9 Battle card, NF2 Local-only network exposure (verified once manually via curl this session, not by an automated test), NF6 Local CI enforcement (no test exercises `scripts/pre-push` itself, e.g. that it actually exits nonzero on a failing suite).
  - Acceptance gate: at minimum, F7 (the highest-complexity, most user-facing untested function set) and the wizard UI click-through (F6/F11, currently only verified ad hoc) get committed test coverage before this is called adequate.

## verification-desk

- [high] Applying the same requirement inventory as test-strategy-desk with `verified`/`partially verified`/`unverified` status per this desk's model: F1, F10, NF1, NF3, NF4, NF5 are **verified** (test name evidence exists). F2, F4, F6, F11 are **partially verified** (some evidence, gaps named above). F3, F5, F7, F8, F9, NF2, NF6 are **unverified** — no test, check, or QA note exists as evidence, only "the feature was built and appears to work." Per this desk's own rule ("passing CI alone is not proof every requirement is satisfied... a `verified` status that rests on either without a requirement-specific link is not acceptable"), none of the unverified items can be called release-ready on CI-passing alone. — Acceptance gate: same as test-strategy-desk's — F7 and the wizard click-through need real evidence, not implied correctness from "it was built."

## security-threat-desk

- [medium] `.claude/settings.local.json`'s exclusion from git depends on a machine-level global gitignore, not the project's own — `git check-ignore -v` confirms it's excluded only via `C:\Users\TWSTD/.config/git/ignore`, a per-machine config, not `D:\dev\roleiq\.gitignore`. This file holds an auto-accumulated permission allowlist (not secrets today, verified by reading it in full) but the exclusion is an environment-specific safety net, not a project guarantee — a fresh clone on a machine without that global rule configured would have no protection against `.claude/settings.local.json` being swept into a future `git add -A`. — Acceptance gate: `.gitignore` gains `.claude/settings.local.json` (or `.claude/*.local.json`) so the exclusion holds regardless of the contributor's machine config.
- [low] No dependency/CVE scan has ever been run against the pinned versions — `requirements.txt` (streamlit==1.62.0, openai==3.4.0, anthropic==1.1.0, pypdf==6.16.2, python-docx==1.2.0, python-dotenv==1.2.3, pydantic==2.13.4, cryptography==50.0.1) — exact pins close the unbounded-drift risk (already fixed this session) but nothing has checked whether any of these exact versions carry a known CVE. — Acceptance gate: a `pip-audit` (or equivalent) run against `requirements.txt`, with results recorded, even if the result is "clean."
Notes: Everything else this desk would normally flag — encryption at rest, prompt-injection mitigation, upload/page caps, sanitized exceptions, execution-policy hygiene, secret handling in run-roleiq.ps1, exact dependency pins — was already addressed in a dedicated hardening pass this session (commits 606cd19 through 6e26208) and re-verified by reading the current code rather than assumed fixed; no regression found.

## ci-failure-desk

- [medium] Local CI (`scripts/pre-push`) doesn't verify a clean-environment install the way remote CI does — `.github/workflows/ci.yml` runs `pip install -r requirements-dev.txt` into a fresh runner every time; `scripts/pre-push` only runs `py_compile`/`pytest` against whatever's already installed in the local `.venv`. A `requirements.txt` regression (an accidentally incompatible pin, a typo) would pass local CI silently as long as the developer's existing venv still has the old good versions installed, and only surface once remote CI comes back online. — Acceptance gate: local CI adds a step that at least checks `pip install -r requirements-dev.txt --dry-run` succeeds, or documents this gap explicitly as accepted.
- [medium] The pre-push hook is not installed automatically — confirmed in `README.md`'s own "Local CI" section: it's a one-time manual `cp scripts/pre-push .git/hooks/pre-push` per clone, because git hooks aren't tracked. Combined with remote CI currently being down (billing lock), a contributor who clones and misses that one documented step gets **zero** enforcement on push, with nothing in the repo itself to warn them. — Acceptance gate: either a `git commit`-time reminder (a lightweight `pre-commit` hook checking whether `pre-push` is installed) or explicit acceptance that this is a documentation-only safeguard.

## release-operations-desk

- [medium] No release/versioning discipline exists — confirmed in Phase 0: `git tag` returns nothing, no `CHANGELOG.md`, no version string anywhere in `app.py`/`README.md`/any config file. 15 commits and 12 closed issues have shipped with no way to answer "what version of RoleIQ is this" for a given checkout. — Acceptance gate: at minimum, a version string in `app.py` (e.g. next to `APP_TITLE`) and a tag on the commit that closes Phase 6's first sprint.

## deployment-desk

- [low] `run-roleiq.ps1`'s failure modes are clear but there's no troubleshooting section for the most likely real-world failure (no internet during `pip install`) — the script's own error handling (`$LASTEXITCODE -ne 0` checks) surfaces a generic "Dependency installation failed" without guidance, and `README.md` has no troubleshooting section to fill the gap. For a single-user local tool where the install script IS the entire release/deployment story, this is the one path that matters most. — Acceptance gate: `README.md` gains a short troubleshooting note for the 2-3 most likely local-launch failures (no internet, wrong Python version, execution-policy prompts).
Notes: The rest of this desk's normal scope (rollout gates, feature flags, staged deployment, post-deploy verification) is N/A — there is no deployment target beyond "clone and run locally" (see `architecture.md`, `requirements.md` open questions), and that's a stated scope boundary, not an unaddressed gap.

## observability-readiness-desk

- [medium] `roleiq.log` has no rotation or size cap — `app.py`'s `logging.basicConfig` uses a plain `FileHandler`, not `RotatingFileHandler`/`TimedRotatingFileHandler` — the file grows unbounded for the life of the local install. For a long-running local install this eventually becomes a real disk-usage and log-searchability problem. — Acceptance gate: switch to a rotating handler with a stated size/backup-count policy, or document the manual cleanup expectation.
- [low] No per-session/request correlation in log entries — log format is `%(asctime)s %(levelname)s %(name)s: %(message)s`, with no session or request id, so if a user reports "something broke," there's no way to isolate which lines in a shared, unbounded log file belong to that run. — Acceptance gate: not required for go-live at single-user local scale; recorded as a nicety.
Notes: The exception-only logging that DOES exist (added this session, `app.py`, 9 call sites via `logger.exception(...)`) is adequate in scope and content (confirmed: never logs secrets or full prompt/response bodies, by design) — this finding is about operational hygiene of the log file itself, not about what gets logged.

## incident-response-desk

- [medium] No self-diagnosis path exists for a user whose local install breaks — there's no on-call/severity model to build (single-user local tool, no team, no customers — genuinely N/A for that part of this desk's usual scope), but there's also no minimal runbook pointing a user at `roleiq.log` or `check_providers.py` when something goes wrong; `README.md` documents both but not as a "something's broken, start here" troubleshooting flow. — Acceptance gate: `README.md` gains a short "Troubleshooting" section pointing at `roleiq.log` first, then `check_providers.py` for provider-specific issues (this overlaps with the deployment-desk troubleshooting finding above — one section can satisfy both).
Notes: Severity classification, triage paths, and incident runbooks in the traditional sense are N/A — no production environment, no on-call, no customers to page (see `architecture.md` ADR-04).

## maintenance-refactor-desk

- [low] `datetime.utcnow()` deprecation warning — `app.py:79` (`save_candidate`) and `app.py:106` (`save_session`), confirmed live (surfaces in every `pytest` run this session). Python 3.14's replacement is `datetime.now(datetime.UTC)`. — Acceptance gate: both call sites updated, `pytest -q` runs clean of this specific `DeprecationWarning`.
- [medium, cross-referenced to security-threat-desk] `clean-main` isn't just an unused branch — it still holds the pre-history-rewrite commit containing the candidate PII (name, resume, interview transcript) that was deliberately purged from `main`'s history earlier this session. Confirmed via `git log main..clean-main --oneline`: one unique commit, `881f219`, the original "Initial RoleIQ V1.92" — the exact commit the history rewrite existed to remove. It is local-only and has never been pushed (confirmed in Phase 0), so there is no current exposure, but it's a live foot-gun: any future `git push --all`, `git push clean-main`, or similar would put that PII commit on the public remote. `rewrite-main`, by contrast, has zero unique commits (`git log main..rewrite-main` is empty) — fully redundant, no special concern beyond tidiness. — Acceptance gate: `clean-main` is deleted locally (`rewrite-main` too, for tidiness) before any operation that could push all local branches is ever run.

## retrospective-desk

- Real material exists and was reviewed (`git log --oneline`, all 15 commits and their messages): the session shipped a full security-hardening pass (upload caps, encryption at rest, prompt-injection mitigation, logging, dependency pinning, script hygiene — 6 commits, each closing a filed GitHub issue via `Fixes #N`), a real bug fix (silent contract-validation failure, `role_schema.py`), a UI redesign (wizard/LMS flow), and process infrastructure (local CI). Issue-per-fix discipline was consistently good — every one of 12 closed issues has a real commit closing it via trailer, not just a manual close.
- [medium] The one consistent process gap across the entire session: zero PR history, direct commits to `main` throughout — already the top-ranked gap in `phase1-status.md` and the sole finding of `review-quality-desk` above; recorded here as the session's single clearest retrospective action item rather than restated as a new finding. — Acceptance gate: n/a here, tracked via review-quality-desk's finding and Phase 6's branch/PR requirement.
Notes: no findings invented beyond what's grounded in the actual commit history read this pass.

## decommissioning-desk

Status: N/A
Notes: Nothing in RoleIQ is currently being retired, sunset, or migrated off — verified against the full Phase 0 file inventory and this phase's suite-by-suite pass; no candidate found. (The two dangling git branches are a maintenance-refactor-desk finding, not a decommission one — they were never a shipped feature being retired, just leftover rewrite artifacts.)

## docs-traceability-desk

- [medium] Five env vars used in real code are undocumented in `.env.example` — confirmed by cross-referencing every `RoleIQ_*` reference in `app.py`/`ai_provider.py`/`db_crypto.py` against `.env.example`'s contents: `RoleIQ_DB` (SQLite path override, `app.py`), `RoleIQ_JSON_MAX_TOKENS`/`RoleIQ_MAX_TOKENS` (`ai_provider.py` output caps), `RoleIQ_LOG_LEVEL` (`app.py`, added this session), `RoleIQ_MODEL` (legacy single-provider override, `ai_provider.py`). All five are genuinely mentioned in `README.md` prose, so this isn't undocumented behavior — but `.env.example` is the actual copy-paste template a new user follows, and these five got left out while seven other vars were added to it incrementally as features shipped. — Acceptance gate: `.env.example` gains commented-out entries for all five, matching the pattern already used for the other seven.
Notes: Spot-checked three other concrete README claims against current code, all confirmed accurate, no drift: the AI-provider precedence table (`README.md` vs `ai_provider.py:provider()`), the wizard step list description in the "Guided flow" section (vs `app.py:build_steps()`), and the "Data at rest" section's encrypted-column list (vs `db_crypto.py` usage sites in `app.py`'s `save_candidate`/`save_session`/`load_candidate`). README.md remains actively maintained, consistent with Phase 0's finding — this one gap is the exception, not evidence of broader drift.

## web-development-command-desk (orchestrator)

- none — target-surface classification (single-process Streamlit session-state app, no routing framework, no separate frontend build) confirmed correct; stage selection for this batch (site-product-requirements → information-architecture → ux-ui-design-system) matched the command desk's declared dependency order. No orchestration-level defect.

## site-product-requirements-desk

- [high] Voice-answer grading ignores the competency-matching the typed path uses — `app.py:582` vs `app.py:527-531` — The typed "Grade & Continue" path searches `analysis["competencies"]` for the one whose `sme_language` terms appear in the current question before grading. The voice "Grade transcript" path hardcodes `comp = analysis.get("competencies", [{}])[0]` — always grades against the first competency regardless of what was actually asked, producing silently mismatched coaching feedback. — Acceptance gate: grading a voice-transcribed answer selects the same SME-language-matched competency the typed path would for an identical question.
- [medium] Voice-graded turns are never saved — `app.py:581-586` vs `app.py:532-541` — The typed path appends to `history`, calls `adaptive_next`, synthesizes the next question, and calls `save_session`. The voice path only sets `st.session_state.grade` — no history append, no adaptive update, no persistence, no UI indication the turn won't be saved. — Acceptance gate: voice-graded turns are appended to `history`/`save_session` the same as typed turns, or the UI explicitly states they won't be.
- [low] No testable acceptance-criteria matrix in `requirements.md` — prose IDs exist but no "Given X, observable Y" per requirement (same finding as product-requirements-desk above — not double-counted in the GL backlog).

## information-architecture-desk

- [low-medium] Competency ordering is inconsistent between two steps showing the same data — Readiness Map iterates competencies in whatever order the model returned them (`app.py:436-437`); SME Training explicitly re-sorts by `interview_risk` (`ordered_competencies()`, `app.py:185-191`). A competency third in one step can be first in the other with no explanation. — Acceptance gate: either both steps use the same order, or Readiness Map states the order it uses.
- [low] No preview of the wizard's step structure before the initial Build — the six-step journey is entirely undisclosed until after Build completes.
- [low] No cross-links between related steps (e.g. Readiness Map's "Evidence" field vs. the Experience Graph entry it references) — recorded as a findability nicety, not a defect.

## ux-ui-design-system-desk

- [medium] Button-label casing is inconsistent — Title Case ("Build RoleIQ Role Model", "Back", "Next", "Generate SME Module") interleaved with sentence case ("Process recorded answer", "Grade transcript", "Generate battle card") with no stated rule, sometimes within the same wizard step.
- [medium] Error-message tone is inconsistent — 9 `st.error(str(e))` sites surface raw exception text with no guidance, vs. 2 sites that give plain-language help. For an app whose primary risk surface is live AI-provider calls, raw SDK/network error text is the common case, not the edge case.
- [medium] Spinner/busy-indicator coverage is inconsistent — three multi-second AI-call buttons (voice transcribe, voice grade, source lookup) show zero busy feedback while the equivalent typed-grading, SME-module, and battle-card buttons all use `st.spinner`. A user clicking one of the three sees nothing happen until the response returns.
- [medium] `provider_healthy` is a one-way flag that never resets on failure — set `True` once on first successful build (`app.py:349`), never cleared, including inside the generic exception handler that catches later failures. After one success, the sidebar keeps showing "Provider healthy" through any subsequent failed call.
- [low-medium] "Recommended next" banner has no "all steps visited" state — once every step has been seen once, `recommended_step` unconditionally returns the last step forever after, so revisiting any earlier step for review shows "Recommended next: Sources & Battle Card" even with nothing new to recommend.
Notes: No formal design system exists (vanilla Streamlit widgets throughout) — evaluated for consistency of what exists, not faulted for lacking a component library, a reasonable scope boundary for a single-developer local tool. Layout patterns (two/three/four-column arrangements) checked and found consistent — no finding.

## web-release-deployment-desk

Status: run
Findings:
- none
Notes: No CDN, no preview environments, no production-promotion pipeline exist or are planned — genuinely N/A at this project's scale (single-user local tool, confirmed `architecture.md`/`requirements.md`). The one thing that IS relevant — "can you tell what version of RoleIQ you're running" — is already captured as release-operations-desk's finding above (zero git tags); not duplicated here.

## web-maintenance-growth-desk

Status: run
Findings:
- none
Notes: No experiments infrastructure exists or is needed. Post-launch feedback/bug tracking already has a real, working channel — GitHub Issues, in active use (12 closed issues this session, each with a real fix commit). No gap found at this project's scale.

## web-security-secops-desk

- [low] No Content-Security-Policy is configured — `.streamlit/config.toml` has no CSP directive (Streamlit 1.62 has no first-class CSP config option). Risk is meaningfully reduced by the app's other properties (loopback-only binding, no `unsafe_allow_html` usage anywhere in `app.py` — confirmed by grep, no third-party scripts loaded), but a CSP is still a real defense-in-depth gap against any future change that does render less-trusted HTML. — Acceptance gate: documented as an accepted gap given the current no-unsafe-HTML posture, revisited if that ever changes.
Notes: `enableXsrfProtection=true` and `enableCORS=true` (`.streamlit/config.toml`, both correctly set this session after catching an inverted `enableCORS` assumption during that same work) re-verified as currently correct. Session-cookie behavior is managed internally by Streamlit's own runtime and isn't inspectable from repo source alone — flagged as unverifiable from static analysis rather than guessed at. This suite overlaps with `security-threat-desk`; its one distinct finding (CSP) is recorded here, not duplicated there.

## web-performance-desk

- [medium] No timeout is set on any AI provider call — `ai_provider.py`'s `openai_client()`/`anthropic_client()` construct SDK clients with no explicit timeout, and no `.messages.create`/`.responses.create` call site passes one either. A hung or extremely slow API response has nothing bounding how long the UI waits, with no user-facing indication of how long is "too long." — Acceptance gate: an explicit timeout is set on both provider clients, with a timeout-specific error message distinct from a generic `ProviderError`.
Notes: Core Web Vitals, bundle size, and CDN caching don't apply — no client bundle is shipped (server-rendered Streamlit). The two real, controllable performance surfaces are upload caps (already capped this session) and AI-call bounding (the finding above).

## accessibility-seo-desk

Status: run (accessibility) / N/A (SEO)
Findings:
- none — checked and confirmed clean: the SME Training checklist's status markers pair emoji with a plain-text word ("✅ Trained", "▶ Up next", "🔒 Locked"), not emoji alone; no `unsafe_allow_html` usage anywhere in `app.py`, so Streamlit's default widget accessibility (labels, focus order) isn't undermined.
Notes: SEO is N/A — RoleIQ is a local single-user tool, never publicly indexed. No accessibility tool (axe, Lighthouse) has ever been run against the rendered app — this assessment is a static-code read, not a rendered-DOM audit, recorded as a coverage limitation.

## web-testing-qa-desk

- [medium] No pre-merge manual signoff process exists — beyond one ad hoc, uncommitted smoke-test script this session (an `AppTest`-driven wizard click-through, run once, then deleted), there's no repeatable smoke-test step before a change ships, and zero PRs have ever existed to gate on one. Going into Phase 6's PR-per-task workflow, this needs to be real, not ad hoc. — Acceptance gate: the ad hoc `AppTest` smoke script gets rebuilt as a committed, repeatable test (same fix as `test-strategy-desk`'s wizard-coverage finding).
Notes: Cross-browser and responsive-design testing are N/A — Streamlit renders through one engine with no custom breakpoints or CSS in this app. Visual regression tooling doesn't exist and isn't warranted at this scale.

## web-observability-desk

- [medium] An uncaught exception outside the app's own `try/except` blocks would surface only as Streamlit's generic error page, captured nowhere — the 9 `logger.exception(...)` sites only fire inside explicit try/except blocks; nothing hooks genuinely unexpected top-level exceptions. — Acceptance gate: a top-level exception hook is verified to actually reach `roleiq.log`, or this gap is explicitly accepted given how narrow the surface already is.
Notes: RUM, synthetic checks, and launch monitoring in the hosted-service sense are N/A — no production deployment exists.

## frontend-engineering-desk

- [medium] `current_question` isn't reset on re-Build — the Build handler's `session_state.update()` resets `history`/`grade`/`next`/`trained_modules`/`wizard_step`/`wizard_visited`, but not `current_question`. Since the Interview step only initializes it lazily on first render (`if "current_question" not in st.session_state`), re-Building with a new JD/resume leaves the *previous* role's question displayed until "Next Question" is clicked. — Acceptance gate: `current_question` (or its removal) is added to the Build handler's reset dict.
Notes: `st.rerun()` usage checked across every state-mutating button handler — consistent, no finding.

## backend-integration-desk

Status: run
Findings:
- none beyond what's already captured under architecture-design-desk (contract-validation scope question) and web-performance-desk (no call timeout) — not duplicated here.
Notes: The `app.py` <-> `ai_provider.py` and SQLite <-> `db_crypto.py` boundaries are clean single-direction contracts, confirmed by full-file read. No caching exists for repeated AI calls — reasonable given RoleIQ's interactive-session usage pattern, not a gap.

## cms-content-operations-desk

Status: N/A
Notes: RoleIQ has no content management system, no editorial workflow, no publishing pipeline — this desk's entire framework doesn't apply to a single-developer local tool with no editorial surface.
