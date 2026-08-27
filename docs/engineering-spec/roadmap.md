# Phase 4: Go-Live Roadmap

31 GL items, deduplicated from Phase 3's 36 raw findings (several findings from different suites converged on the same root cause — each is cross-referenced to every suite that raised it, counted once; low-priority "nicety" findings still get their own item per the protocol's "nothing dropped for being small" rule, sequenced into the final sprint rather than omitted). Every item traces to a real recon fact or audit finding; none invented. 8 sprints, named milestones, dependency order preserved.

## M1 — Process & Quick Fixes (Sprint 1)

- **GL-01** — Adopt branch-per-task, PR-per-change for all work from here forward. No more direct commits to `main`.
  Source: `review-quality-desk`, `retrospective-desk`, `web-testing-qa-desk`, `implementation-handoff-desk` (all converged on the same gap: zero PR history, 15/15 commits direct to `main`).
  Acceptance: the next 3 merged GL items each shipped on their own branch, merged via PR, zero direct commits to `main` in between.
  Depends on: none — foundational, gates how every other GL item ships.

- **GL-02** — Delete the dangling `clean-main` and `rewrite-main` local git branches.
  Source: `maintenance-refactor-desk` (cross-ref `security-threat-desk`) — `clean-main` still holds the pre-rewrite commit with candidate PII, local-only but a live foot-gun against any future `git push --all`.
  Acceptance: `git branch` shows neither branch; `git reflog` confirms deletion, not force-push.
  Depends on: none.

- **GL-03** — Add `.claude/settings.local.json` to the project's own `.gitignore`.
  Source: `security-threat-desk` — exclusion currently depends on a per-machine global gitignore, not a project guarantee.
  Acceptance: `git check-ignore -v .claude/settings.local.json` resolves via `D:\dev\roleiq\.gitignore`, not the global config.
  Depends on: none.

- **GL-04** — Fix `datetime.utcnow()` deprecation in `app.py:79,106`.
  Source: `maintenance-refactor-desk`.
  Acceptance: `pytest -q` runs with zero `DeprecationWarning` for this specific call; both sites use `datetime.now(datetime.UTC)`.
  Depends on: none.

- **GL-05** — Document the 5 undocumented env vars in `.env.example` (`RoleIQ_DB`, `RoleIQ_JSON_MAX_TOKENS`, `RoleIQ_MAX_TOKENS`, `RoleIQ_LOG_LEVEL`, `RoleIQ_MODEL`).
  Source: `docs-traceability-desk`.
  Acceptance: all 5 appear in `.env.example` as commented-out entries, matching the existing pattern for the other 7.
  Depends on: none.

## M2 — Bug Fixes (Sprint 2)

- **GL-06** — Fix voice-answer grading to use the same SME-language competency matching the typed path uses, instead of always grading against `competencies[0]`.
  Source: `site-product-requirements-desk` — highest-severity finding of the whole audit; silently wrong coaching feedback.
  Acceptance: grading a voice-transcribed answer selects the same competency the typed path would select for an identical question (test asserts this directly).
  Depends on: GL-01 (ships via PR).

- **GL-07** — Persist voice-graded turns to `history`/`save_session`, or explicitly tell the user they won't be saved.
  Source: `site-product-requirements-desk`.
  Acceptance: a voice-graded turn appears in `history` and survives a `save_session` round-trip the same as a typed turn — or the voice UI states plainly that it won't.
  Depends on: GL-06 (same code path).

- **GL-08** — Reset `current_question` in the Build handler's `session_state.update()` so re-Building doesn't leave the previous role's question displayed.
  Source: `frontend-engineering-desk`.
  Acceptance: Build → answer a question → re-Build with a different JD/resume → Interview step shows a question generated from the *new* analysis, not the old one, without requiring a manual "Next Question" click.
  Depends on: GL-01.

- **GL-09** — Make `provider_healthy` reflect current state: reset it (or relabel the badge) when a later AI call fails after an earlier success.
  Source: `ux-ui-design-system-desk`.
  Acceptance: trigger one successful build, then a failing AI call (e.g. by invalidating the key mid-session) — sidebar no longer claims "Provider healthy."
  Depends on: GL-01.

## M3 — Test Coverage (Sprint 3)

- **GL-10** — Commit a real, repeatable `AppTest`-driven wizard integration test (rebuild the ad hoc script used once this session, deleted, never committed).
  Source: `test-strategy-desk`, `verification-desk`, `web-testing-qa-desk` (all three converged on this exact gap).
  Acceptance: `pytest` runs a committed test file that drives the actual Streamlit app via `AppTest` through Build → wizard navigation → SME Training sequential lock, with mocked AI calls, no live key required.
  Depends on: GL-06, GL-08 (test should cover the fixed behavior, not the old bugs).

- **GL-11** — Add test coverage for F7 (Interview simulation: `grade_answer`, `adaptive_next`, `synthesize_question`, SME-language competency matching) — currently zero committed coverage.
  Source: `test-strategy-desk`, `verification-desk`.
  Acceptance: each of the four functions has at least one test exercising its logic with a mocked AI response.
  Depends on: GL-06 (tests the fixed matching logic).

- **GL-12** — Add test coverage for F3 (Role Context conditional path) and F5 (interviewer persona modeling) — currently zero committed coverage.
  Source: `test-strategy-desk`, `verification-desk`.
  Acceptance: a test exercises the `ROLE_CONTEXT_ENABLED` on/off branches and the persona-modeling call path with mocked responses.
  Depends on: none.

## M4 — UX Consistency (Sprint 4)

- **GL-13** — Standardize button-label casing across the app (pick one rule, apply everywhere).
  Source: `ux-ui-design-system-desk`.
  Acceptance: every `st.button`/`st.download_button` label in `app.py` follows one documented casing rule.
  Depends on: GL-01.

- **GL-14** — Standardize error-message tone: wrap raw `st.error(str(e))` sites with user-facing guidance, or document why they're deliberately left raw.
  Source: `ux-ui-design-system-desk`.
  Acceptance: all 9 raw `st.error(str(e))` sites either gain guidance text or an inline comment stating the rationale for staying raw.
  Depends on: none.

- **GL-15** — Add spinner/busy-indicator coverage to the 3 AI-call buttons currently missing one (voice transcribe, voice grade, source lookup).
  Source: `ux-ui-design-system-desk`.
  Acceptance: all `st.button`-triggered AI/network calls in `app.py` show a spinner or equivalent during the call.
  Depends on: none.

- **GL-16** — Give the "Recommended next" banner an "all steps visited" terminal state instead of perpetually pointing at the last step.
  Source: `ux-ui-design-system-desk`.
  Acceptance: after visiting every wizard step once, navigating to a non-final step shows no banner (or one that says review is complete).
  Depends on: none.

## M5 — Docs & Requirements Depth (Sprint 5)

- **GL-17** — Add testable "Given X, observable Y" acceptance criteria to every requirement in `requirements.md`.
  Source: `product-requirements-desk`, `site-product-requirements-desk` (converged).
  Acceptance: every F/NF requirement ID has at least one testable criterion line.
  Depends on: none.

- **GL-18** — Add a risk register to `requirements.md`/`architecture.md` with likelihood/impact and stated mitigations.
  Source: `technical-discovery-desk`, `architecture-design-desk` (converged).
  Acceptance: a risks section lists at minimum the risks already surfaced this phase (CI billing lock, wizard test gap, no-PR history, key-loss-is-unrecoverable) scored by likelihood/impact with a mitigation per risk.
  Depends on: none.

- **GL-19** — Fix competency-ordering inconsistency between Readiness Map (model order) and SME Training (risk order) — align them or state the difference explicitly in the UI.
  Source: `information-architecture-desk`.
  Acceptance: either both steps use the same order, or Readiness Map states the order it uses.
  Depends on: none.

- **GL-20** — Add a brief pre-Build preview of the wizard's step structure.
  Source: `information-architecture-desk`.
  Acceptance: the six post-Build steps are named somewhere visible before Build is clicked.
  Depends on: none.

## M6 — Observability & CI Hardening (Sprint 6)

- **GL-21** — Add rotation/size cap to `roleiq.log` (switch from `FileHandler` to a rotating handler).
  Source: `observability-readiness-desk`.
  Acceptance: the log handler is a `RotatingFileHandler`/`TimedRotatingFileHandler` with a stated size/backup-count policy.
  Depends on: none.

- **GL-22** — Add a top-level exception hook so an uncaught exception outside existing try/except blocks still reaches `roleiq.log`, or explicitly accept the current narrow gap.
  Source: `web-observability-desk`.
  Acceptance: either a verified top-level hook exists, or `architecture.md`/`requirements.md` records the decision to accept this gap with reasoning.
  Depends on: none.

- **GL-23** — Add a `pip install --dry-run` (or equivalent) step to local CI (`scripts/pre-push`) so a `requirements.txt` regression can't pass silently against a stale local venv.
  Source: `ci-failure-desk`.
  Acceptance: `scripts/pre-push` fails if `requirements-dev.txt` can't resolve/install cleanly, verified by deliberately breaking a pin and confirming the hook catches it.
  Depends on: none.

- **GL-24** — Set an explicit timeout on both AI provider clients (`ai_provider.py`), with a distinct timeout error message.
  Source: `web-performance-desk`, `backend-integration-desk` (converged).
  Acceptance: a simulated hung call is bounded by the timeout and raises a message distinguishable from a generic `ProviderError`.
  Depends on: none.

## M7 — Release Readiness (Sprint 7)

- **GL-25** — Add a version string to the app and tag the commit that closes this sprint.
  Source: `release-operations-desk`.
  Acceptance: a version string exists next to `APP_TITLE` in `app.py`; `git tag` shows at least one tag.
  Depends on: M1-M6 substantially complete (tags a meaningful milestone, not an arbitrary point).

- **GL-26** — Add a short "Troubleshooting" section to `README.md` (no internet during install, wrong Python version, execution-policy prompts) doubling as the minimal incident-response self-diagnosis path.
  Source: `deployment-desk`, `incident-response-desk` (converged).
  Acceptance: `README.md` has a Troubleshooting section covering the 2-3 most likely local-launch failures, pointing at `roleiq.log` and `check_providers.py` first.
  Depends on: none.

- **GL-27** — Run a dependency/CVE scan (`pip-audit` or equivalent) against `requirements.txt` and record the result.
  Source: `security-threat-desk`.
  Acceptance: a scan result (clean or with findings) is recorded in `docs/engineering-spec/`, dated.
  Depends on: none.

## M8 — Final Polish (Sprint 8)

- **GL-28** — Document the CSP gap as an accepted risk (no Content-Security-Policy configured, mitigated by loopback-only binding and zero `unsafe_allow_html` usage).
  Source: `web-security-secops-desk`.
  Acceptance: `architecture.md` records the decision explicitly, matching the pattern already used for other accepted-risk items.
  Depends on: none.

- **GL-29** — Add a lightweight reminder that the pre-push hook must be installed per-clone (since remote CI is also currently down, a missed install step means zero enforcement, silently).
  Source: `ci-failure-desk`.
  Acceptance: either a `pre-commit`-time check for whether `.git/hooks/pre-push` exists, or an explicit, recorded decision that the `README.md` documentation is accepted as sufficient.
  Depends on: none.

- **GL-30** — Add cross-links between related wizard steps (e.g. a Readiness Map competency's "Evidence" field linking to its source Experience Graph entry).
  Source: `information-architecture-desk` (recorded there as "a findability nicety, not a defect" — still a real finding, not dropped).
  Acceptance: not required to block go-live; closed by either implementing a link or by an explicit recorded decision to defer indefinitely.
  Depends on: none.

- **GL-31** — Add per-session/request correlation to `roleiq.log` entries so a user-reported issue can be isolated within a shared, unbounded log file.
  Source: `observability-readiness-desk` (recorded there as a "nicety" — still a real finding, not dropped).
  Acceptance: not required to block go-live; closed by either adding a session id to the log format or an explicit recorded decision to defer.
  Depends on: GL-21 (same subsystem).

## Backlog notes

- Every GL item above traces to a named Phase 3 suite or a Phase 0/1 recon fact — none invented, consistent with the audit's own INV-01 rule.
- Cross-referenced findings (e.g. GL-01, GL-06/07, GL-17, GL-18, GL-24, GL-26) were raised independently by 2-4 different suites converging on the same root cause — counted once here, all sources listed, per the protocol's "nothing summarized away" rule applied to *duplicates*, not to genuinely distinct findings.
- No finding from Phase 3 was dropped. Every "Findings: none" or "Status: N/A" suite in `audit-coverage.md` is exactly that — a suite that ran and found nothing, or a suite whose framework genuinely doesn't apply — not a suite whose findings got folded silently into this list.
