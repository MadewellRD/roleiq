# Requirements

Reverse-derived from the working codebase and `README.md` (Phase 0 recon), since no standalone requirements document existed before this protocol run. This is the requirements document Phase 3's `product-requirements-desk` audits against — it describes what RoleIQ actually does and is meant to do, not aspirational scope.

## Purpose

RoleIQ takes a job description and a resume and produces a role-specific interview-preparation course: a competency readiness map, SME training modules ordered by interview risk, adaptive interview practice with grading, and a printable battle card.

## Users

One learner, one local machine, one browser tab. No multi-user model exists or is implied anywhere in the code or docs. This is a deliberate scope boundary (see `architecture.md` ADR-04), not an omission.

## Functional requirements

Derived from what is built and verified working (Phase 0):

- **F1 — Ingestion.** Accept a job description and resume as pasted text or an uploaded PDF/DOCX/TXT/MD file, up to a configurable size (`RoleIQ_MAX_UPLOAD_MB`, default 15MB) and PDF page count (`RoleIQ_MAX_PDF_PAGES`, default 200).
- **F2 — Experience Graph.** Build a structured summary of the candidate's roles, projects, technologies, and capabilities from the resume text, grounded only in supplied evidence (no invented experience — enforced in the prompt).
- **F3 — Role Context (optional).** When `RoleIQ_ROLE_CONTEXT_ENABLED=1`, research public company/technical context via server-side web search. Off by default; the step is absent from the UI entirely when disabled, not shown-and-empty.
- **F4 — Readiness analysis.** Correlate the JD against the Experience Graph and (if enabled) Role Context into a competency list, each classified Experienced/Adjacent/Learned/Unknown, with an interview-risk rating and JD-signal evidence. This payload is schema-validated (`role_schema.py`) before the UI trusts it.
- **F5 — Interviewer persona modeling.** Model a plausible interviewer archetype and style from the role/company context.
- **F6 — SME training.** For each competency, generate a training module (what it means, why it matters, SME reasoning patterns, tradeoffs, failure modes, practice prompt). Delivered as a sequential course: highest interview-risk competency first, next one unlocks only after the current module is generated.
- **F7 — Interview simulation.** Ask questions matched to the analyzed competencies, accept typed or (when `OPENAI_API_KEY` is present) recorded-and-transcribed answers, grade against multiple dimensions, and adapt the next question/exercise to answer history.
- **F8 — Evidence-backed research.** On-demand lookup of authoritative sources for an arbitrary technical topic, via server-side web search.
- **F9 — Battle card.** Generate and export a printable/downloadable Markdown summary of the full session: role, risks, proof stories, SME language, interviewer style, and sources.
- **F10 — Persistence.** Save candidate and session state to local SQLite, with narrative content (resume, JD, analysis, history) encrypted at rest.
- **F11 — Guided flow.** Present the above as a wizard: a step tracker with progress, Back/Next, and a recommended-next hint, freely navigable once the initial build completes.

## Non-functional requirements

- **NF1 — Single active AI provider per run.** Exactly one of Anthropic or OpenAI is used for text generation, chosen by key presence, Anthropic taking precedence when both are set. No mixed-provider calls within one analysis.
- **NF2 — Local-only network exposure.** The Streamlit server binds to `127.0.0.1` only; no remote access is a supported configuration today.
- **NF3 — No plaintext sensitive data at rest.** Resume, JD, analysis, and interview-history columns are encrypted; only short metadata (ids, role, company, timestamps) is plain.
- **NF4 — No silent contract failures.** A structurally invalid AI response must surface as a visible, diagnosable error, never as an empty UI section.
- **NF5 — Deterministic, offline-testable core logic.** The pure logic (candidate ID hashing, provider selection, JSON repair, file extraction, competency ordering, wizard step derivation) must be unit-testable without network access or an API key. 60 such tests exist and pass.
- **NF6 — Local CI enforcement.** Every push is checked by `py_compile` + the full test suite before it leaves the machine, independent of whether remote CI is reachable.

## Explicit non-goals (accepted, not gaps)

Carried forward from documented decisions made earlier this session, restated here so Phase 3 doesn't re-flag them as unaddressed:

- Multi-user authentication or access control.
- Session/candidate reload in the UI (`load_candidate()` exists, intentionally unwired).
- Dependency hash-pinning beyond exact version pins.
- Full LLM prompt/response transcript logging (would duplicate the encrypted content in plaintext).
- A PowerShell 5.1 compatibility path for `run-roleiq.ps1`.
- Text-to-speech / voice output (the UI copy was corrected this session to stop implying it exists).

## Open questions for Phase 3/4

- Does "go live" for a single-user local tool require a deployment/release story at all, or does it mean "the local install-and-run path is trustworthy and repeatable"? This determines how much weight `deployment-desk`, `web-release-deployment-desk`, and `web-observability-desk` findings carry in the roadmap.
- Is packaging (a proper installer, a PyPI package, a signed release) in scope, or does "clone + `run-roleiq.ps1`" remain the supported path indefinitely?
