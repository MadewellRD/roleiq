import contextlib, os, re, json, sqlite3, hashlib, textwrap, tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import ai_provider
import db_crypto

APP_TITLE = "RoleIQ"
AI_STATUS = ai_provider.status()
MODEL = AI_STATUS["model"]
ROLE_CONTEXT_ENABLED = os.getenv("RoleIQ_ROLE_CONTEXT_ENABLED", "0") == "1"
DB_PATH = os.getenv("RoleIQ_DB", str(Path(__file__).with_name("roleiq.db")))

# Upload safety caps. Keep RoleIQ_MAX_UPLOAD_MB in sync with .streamlit/config.toml's
# [server] maxUploadSize -- raising one without the other leaves the lower cap in force.
MAX_UPLOAD_MB = int(os.getenv("RoleIQ_MAX_UPLOAD_MB", "15"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_PDF_PAGES = int(os.getenv("RoleIQ_MAX_PDF_PAGES", "200"))

st.set_page_config(page_title=APP_TITLE, page_icon="W", layout="wide")

_db_parent = Path(DB_PATH).expanduser().resolve().parent
if not _db_parent.is_dir():
    st.error(f"RoleIQ_DB directory does not exist: {_db_parent}")
    st.stop()

# ---------------- persistence ----------------
# resume/experience_graph/jd/analysis/context/history hold real narrative
# content (candidate PII, interview transcripts) and are encrypted at rest via
# db_crypto (RoleIQ_DB_KEY). id/name/candidate_id/role/company/timestamps are
# short metadata, not the sensitive content this is guarding, and stay plain.
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS candidates (
        id TEXT PRIMARY KEY, name TEXT, resume TEXT, experience_graph TEXT,
        created_at TEXT, updated_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY, candidate_id TEXT, role TEXT, company TEXT,
        jd TEXT, analysis TEXT, context TEXT, history TEXT, created_at TEXT,
        updated_at TEXT
    )""")
    conn.commit()
    return conn


def candidate_id(resume: str) -> str:
    # Content-derived, not random: re-saving the same resume text updates the
    # same row instead of creating a duplicate. Intentional dedup convenience
    # for RoleIQ's single-user local usage model, not a bug -- two different
    # people producing byte-identical resume text is not a realistic collision
    # this app needs to defend against.
    return hashlib.sha256(clean_text(resume).encode()).hexdigest()[:16]


def save_candidate(resume: str, name: str, graph: Dict[str, Any]):
    cid = candidate_id(resume)
    now = datetime.utcnow().isoformat()
    with contextlib.closing(db()) as conn:
        conn.execute("""INSERT INTO candidates(id,name,resume,experience_graph,created_at,updated_at)
                        VALUES(?,?,?,?,?,?)
                        ON CONFLICT(id) DO UPDATE SET name=excluded.name,resume=excluded.resume,
                        experience_graph=excluded.experience_graph,updated_at=excluded.updated_at""",
                     (cid, name, db_crypto.encrypt_text(resume), db_crypto.encrypt_text(json.dumps(graph)), now, now))
        conn.commit()
    return cid


def load_candidate(cid: str):
    # Not wired into the UI -- there is no "load a previous candidate" flow;
    # adding one is a feature, not a hardening fix, and out of scope here.
    # Kept as the tested read-side counterpart to save_candidate.
    with contextlib.closing(db()) as conn:
        row = conn.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["resume"] = db_crypto.decrypt_text(data["resume"])
    data["experience_graph"] = db_crypto.decrypt_text(data["experience_graph"])
    return data


def save_session(sid: str, cid: str, role: str, company: str, jd: str,
                 analysis: Dict[str, Any], context: Dict[str, Any], history: List[Dict[str, Any]]):
    now = datetime.utcnow().isoformat()
    with contextlib.closing(db()) as conn:
        conn.execute("""INSERT INTO sessions(id,candidate_id,role,company,jd,analysis,context,history,created_at,updated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(id) DO UPDATE SET analysis=excluded.analysis,context=excluded.context,
                        history=excluded.history,updated_at=excluded.updated_at""",
                     (sid,cid,role,company,
                      db_crypto.encrypt_text(jd),
                      db_crypto.encrypt_text(json.dumps(analysis)),
                      db_crypto.encrypt_text(json.dumps(context)),
                      db_crypto.encrypt_text(json.dumps(history)),
                      now,now))
        conn.commit()

# ---------------- extraction ----------------
def extract_file(uploaded) -> str:
    name = uploaded.name.lower()
    data = uploaded.getvalue()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File too large ({len(data) // 1024 // 1024} MB). Maximum is {MAX_UPLOAD_MB} MB.")
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        import pypdf
        from pypdf import PdfReader
        try:
            reader = PdfReader(uploaded)
            if len(reader.pages) > MAX_PDF_PAGES:
                raise ValueError(f"PDF has too many pages (max {MAX_PDF_PAGES}).")
            pages: List[str] = []
            for page in reader.pages:
                try:
                    pages.append(page.extract_text() or "")
                except pypdf.errors.PyPdfError:
                    continue
            return "\n".join(pages)
        except pypdf.errors.PyPdfError as e:
            raise ValueError("Could not read this PDF. It may be corrupted, password-protected, or not a valid PDF.") from e
    if name.endswith(".docx"):
        from zipfile import BadZipFile
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
        try:
            doc = Document(uploaded)
            return "\n".join(p.text for p in doc.paragraphs)
        except (BadZipFile, PackageNotFoundError, KeyError) as e:
            raise ValueError("Could not read this DOCX file. It may be corrupted or not a valid Word document.") from e
    raise ValueError("Supported files: PDF, DOCX, TXT, MD")


def clean_text(s: str) -> str:
    s = re.sub(r"\r\n?", "\n", s or "")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()

# ---------------- AI ----------------
def client():
    """OpenAI client, kept for the OpenAI-only voice transcription path.

    Text generation routes through ai_provider and follows the active provider.
    """
    return ai_provider.openai_client()


def ai_call(system: str, user: str, web: bool = False, max_tokens: int = 7000) -> str:
    return ai_provider.ai_text(system, user, web=web, max_tokens=max_tokens)


def ai_json(system: str, user: str, web: bool = False) -> Dict[str, Any]:
    """Structured call.

    ai_provider uses the active provider's native structured output, so the
    payload arrives parsed instead of being scraped out of prose.
    """
    return ai_provider.ai_json(system, user, web=web)


def build_experience_graph(resume: str) -> Dict[str, Any]:
    system = """Build a persistent candidate Experience Graph from a resume. Extract only supported facts. Model roles, projects, responsibilities, technologies, domains, architectures, outcomes, leadership, and transferable patterns. Do not invent dates, employers, metrics, or technologies."""
    user = f"""RESUME:\n{resume[:40000]}\n\nReturn JSON:\n{{\n  \"candidate_summary\": \"...\",\n  \"roles\": [{{\"title\":\"\",\"company\":\"\",\"period\":\"\",\"responsibilities\":[\"\"],\"technologies\":[\"\"],\"outcomes\":[\"\"],\"domains\":[\"\"]}}],\n  \"projects\": [{{\"name\":\"\",\"problem\":\"\",\"solution\":\"\",\"technologies\":[\"\"],\"architecture_patterns\":[\"\"],\"outcomes\":[\"\"]}}],\n  \"capabilities\": [\"\"],\n  \"evidence_phrases\": [\"\"]\n}}"""
    return ai_json(system, user)


def role_context(jd: str, company: str, role: str) -> Dict[str, Any]:
    system = """You are the RoleIQ Role Context Plane. Research public technical context about the employer and role. Use only public sources discovered through web search. Separate verified facts from reasonable inference. Return JSON only. Source each material claim with a URL and title when available."""
    user = f"""ROLE: {role}\nCOMPANY: {company or 'Unknown'}\nJOB DESCRIPTION:\n{jd[:30000]}\n\nResearch the company and role. Prioritize official engineering/technical blogs, architecture documentation, product documentation, public talks, GitHub, and reputable technical sources. Return:\n{{\n  \"company_context\": [\"...\"],\n  \"technical_stack_signals\": [\"...\"],\n  \"engineering_culture_signals\": [\"...\"],\n  \"role_specific_signals\": [\"...\"],\n  \"likely_interview_themes\": [\"...\"],\n  \"sources\": [{{\"title\":\"\",\"url\":\"\",\"claim_supported\":\"\"}}],\n  \"inferences\": [\"...\"]\n}}"""
    return ai_json(system, user, web=True)


def analyze(jd: str, resume: str, graph: Dict[str, Any], company: str, role_ctx: Dict[str, Any]) -> Dict[str, Any]:
    system = """You are RoleIQ, a rigorous SME immersion and interview-preparation engine. Never invent candidate experience. Correlate the JD with the candidate Experience Graph and Role Context Plane. Distinguish Experienced, Adjacent, Learned, Unknown. Build a role-specific competency graph and truth boundaries."""
    user = f"""JOB DESCRIPTION:\n{jd[:30000]}\n\nEXPERIENCE GRAPH:\n{json.dumps(graph)[:35000]}\n\nROLE CONTEXT:\n{json.dumps(role_ctx)[:25000]}\n\nReturn JSON:\n{{\n  \"role\": \"\", \"company\": \"\", \"executive_summary\": \"\",\n  \"competencies\": [{{\"name\":\"\",\"importance\":\"Critical|High|Medium|Low\",\"jd_signal\":\"\",\"candidate_level\":\"Experienced|Adjacent|Learned|Unknown\",\"evidence\":\"\",\"gap\":\"\",\"sme_language\":[\"\"],\"interview_risk\":\"Low|Medium|High\"}}],\n  \"proof_paths\": [{{\"requirement\":\"\",\"candidate_story\":\"\",\"how_to_frame\":\"\",\"truth_boundary\":\"\"}}],\n  \"training_priorities\": [\"\"],\n  \"likely_questions\": [\"\"],\n  \"red_flags\": [\"\"]\n}}\nPrefer 8-14 competencies."""
    return ai_json(system, user)


def interviewer_model(analysis: Dict[str, Any], role_ctx: Dict[str, Any], company: str) -> Dict[str, Any]:
    system = """Model a likely interviewer persona and interview style from the role, JD, and public company context. Do not claim to know a specific person unless supplied. Return JSON only."""
    user = f"""COMPANY: {company}\nANALYSIS: {json.dumps(analysis)}\nROLE CONTEXT: {json.dumps(role_ctx)}\nReturn:\n{{\"persona_archetype\":\"\",\"seniority\":\"\",\"priorities\":[\"\"],\"style\":\"\",\"likely_followups\":[\"\"],\"pressure_tests\":[\"\"],\"what_good_sounds_like\":[\"\"],\"what_bad_sounds_like\":[\"\"]}}"""
    return ai_json(system, user)


def training_module(analysis: Dict[str, Any], competency: Dict[str, Any], role_ctx: Dict[str, Any]) -> Dict[str, Any]:
    system = """You are RoleIQ's SME coach. Teach credible practitioner reasoning. Ground candidate-specific material only in supplied evidence. Do not coach deception. Return JSON only."""
    user = f"""ROLE ANALYSIS: {json.dumps(analysis)}\nCOMPETENCY: {json.dumps(competency)}\nROLE CONTEXT: {json.dumps(role_ctx)}\nReturn:\n{{\"what_it_means\":\"\",\"why_the_role_cares\":\"\",\"how_an_sme_thinks\":[\"\"],\"architecture_or_workflow\":[\"\"],\"tradeoffs\":[\"\"],\"failure_modes\":[\"\"],\"language_upgrade\":[\"\"],\"candidate_bridge\":\"\",\"practice_prompt\":\"\",\"gold_standard_answer_outline\":[\"\"],\"red_line\":\"\"}}"""
    return ai_json(system, user)


def adaptive_next(analysis: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, Any]:
    system = """You are the RoleIQ adaptive curriculum engine. Based on interview answer history, select the highest-value remediation next. Prioritize repeated weaknesses and critical competencies. Return JSON only."""
    user = f"""ANALYSIS: {json.dumps(analysis)}\nANSWER HISTORY: {json.dumps(history[-12:])}\nReturn {{\"next_competency\":\"\",\"reason\":\"\",\"exercise_type\":\"concept|architecture|tradeoff|story|pressure_test\",\"exercise\":\"\",\"success_criteria\":[\"\"]}}"""
    return ai_json(system, user)


def grade_answer(analysis: Dict[str, Any], competency: Dict[str, Any], question: str, answer: str, persona: Dict[str, Any]) -> Dict[str, Any]:
    system = """You are an exacting technical interviewer. Grade substance, not buzzword density. Flag unsupported claims. Account for interviewer style. Return JSON only."""
    user = f"""ROLE: {analysis.get('role','')}\nCOMPETENCY: {json.dumps(competency)}\nINTERVIEWER: {json.dumps(persona)}\nQUESTION: {question}\nANSWER: {answer}\nReturn {{\"overall_score\":0,\"technical_accuracy\":0,\"depth\":0,\"specificity\":0,\"tradeoff_reasoning\":0,\"business_alignment\":0,\"sme_language\":0,\"credibility\":0,\"what_worked\":[\"\"],\"what_is_missing\":[\"\"],\"unsupported_or_risky_claims\":[\"\"],\"better_answer_outline\":[\"\"],\"coach_note\":\"\"}}\nScores 0-10."""
    return ai_json(system, user)


def sources_for_topic(topic: str) -> Dict[str, Any]:
    system = """Research the technical topic using web search. Return concise, evidence-backed source list. Prefer primary/official technical documentation and authoritative engineering sources. JSON only."""
    return ai_json(system, f"Topic: {topic}\nReturn {{\"claims\":[{{\"claim\":\"\",\"source\":\"\",\"url\":\"\"}}]}}", web=True)


def battle_card(analysis, role_ctx, persona, history, candidate_graph) -> str:
    system = """Create a concise interview battle card in Markdown. Use only supplied facts. Make truth boundaries explicit. Include role, top risks, proof stories, SME language, interviewer style, likely questions, remediation, and sources."""
    user = f"""ANALYSIS:{json.dumps(analysis)}\nROLE CONTEXT:{json.dumps(role_ctx)}\nINTERVIEWER:{json.dumps(persona)}\nHISTORY:{json.dumps(history)}\nEXPERIENCE GRAPH:{json.dumps(candidate_graph)}\nProduce a compact printable battle card."""
    return ai_call(system, user, max_tokens=6000)


def synthesize_question(analysis, persona, history) -> str:
    system = """Generate one realistic next interview question. Adapt difficulty to answer history and interviewer style. Avoid repeating prior questions. Return only the question."""
    return ai_call(system, f"ANALYSIS:{json.dumps(analysis)}\nPERSONA:{json.dumps(persona)}\nHISTORY:{json.dumps(history[-8:])}", max_tokens=500)

# ---------------- UI ----------------
st.markdown("# RoleIQ")
st.caption("Walk the Walk. Talk the Talk. — role immersion, SME fluency, adaptive interview preparation.")

with st.sidebar:
    st.subheader("Role inputs")
    jd_file = st.file_uploader("Job Description", type=["pdf","docx","txt","md"], key="jd")
    resume_file = st.file_uploader("Resume", type=["pdf","docx","txt","md"], key="resume")
    company = st.text_input("Company", value=st.session_state.get("company", ""))
    role_hint = st.text_input("Role title (optional)", value=st.session_state.get("role_hint", ""))
    st.divider()
    st.caption(f"Provider: {AI_STATUS['provider_label']}")
    st.caption(f"Model: {MODEL or 'not configured'}")
    st.caption("Persistence: local SQLite")
    st.caption("Role Context Plane: deferred by default (enable with RoleIQ_ROLE_CONTEXT_ENABLED=1)")
    if AI_STATUS["connected"]:
        st.success(f"AI connected — {AI_STATUS['provider_label']}")
        if AI_STATUS["both_keys"]:
            st.caption("Both keys present; Anthropic takes precedence.")
    else:
        st.warning("Add ANTHROPIC_API_KEY or OPENAI_API_KEY to enable analysis")
    st.caption("Voice transcription: " + ("OpenAI ready" if AI_STATUS["voice"] else "requires OPENAI_API_KEY"))

jd_default = st.session_state.get("jd_text", "")
resume_default = st.session_state.get("resume_text", "")
col1, col2 = st.columns(2)
with col1:
    jd_text = st.text_area("Job Description", value=jd_default, height=330, placeholder="Paste the complete JD here…")
    if jd_file and st.button("Load JD file"):
        try: st.session_state.jd_text = clean_text(extract_file(jd_file)); st.rerun()
        except Exception as e: st.error(str(e))
with col2:
    resume_text = st.text_area("Current Resume", value=resume_default, height=330, placeholder="Paste your resume here…")
    if resume_file and st.button("Load Resume file"):
        try: st.session_state.resume_text = clean_text(extract_file(resume_file)); st.rerun()
        except Exception as e: st.error(str(e))

if st.button("Build RoleIQ Role Model", type="primary", use_container_width=True):
    if len(jd_text.strip()) < 200: st.error("The JD is too short.")
    elif len(resume_text.strip()) < 100: st.error("The resume is too short.")
    else:
        try:
            with st.status("Building RoleIQ context…", expanded=True) as status:
                st.write("Building persistent Experience Graph…")
                graph = build_experience_graph(clean_text(resume_text))
                cid = save_candidate(clean_text(resume_text), "Candidate", graph)
                provisional_role = role_hint or "Target role"
                if ROLE_CONTEXT_ENABLED:
                    st.write("Resolving company and public technical context…")
                    ctx = role_context(clean_text(jd_text), company, provisional_role)
                else:
                    st.write("Using local role context mode (public context plane deferred)…")
                    ctx = {"company_context": [], "technical_stack_signals": [], "engineering_culture_signals": [], "role_specific_signals": [], "likely_interview_themes": [], "sources": [], "inferences": [], "status": "deferred"}
                st.write("Mapping JD competencies to candidate evidence…")
                analysis = analyze(clean_text(jd_text), clean_text(resume_text), graph, company, ctx)
                st.write("Modeling likely interviewer behavior…")
                persona = interviewer_model(analysis, ctx, company)
                sid = hashlib.sha256((cid + clean_text(jd_text)).encode()).hexdigest()[:16]
                st.session_state.update({"candidate_id":cid,"session_id":sid,"jd_text":jd_text,"resume_text":resume_text,
                    "company":company,"role_hint":role_hint,"graph":graph,"context":ctx,"analysis":analysis,
                    "persona":persona,"history":[],"module":None,"grade":None,"next":None})
                save_session(sid,cid,analysis.get("role",provisional_role),company,jd_text,analysis,ctx,[])
                status.update(label="RoleIQ role model ready", state="complete")
        except Exception as e: st.error(str(e))

analysis = st.session_state.get("analysis")
if analysis:
    ctx = st.session_state.get("context", {})
    persona = st.session_state.get("persona", {})
    history = st.session_state.setdefault("history", [])
    graph = st.session_state.get("graph", {})
    st.divider()
    st.subheader(f"{analysis.get('role','Target Role')} {('— ' + analysis.get('company')) if analysis.get('company') else ''}")
    st.write(analysis.get("executive_summary", ""))

    tabs = st.tabs(["Readiness Map", "Role Context", "Experience Graph", "SME Training", "Interview", "Sources & Battle Card"])

    with tabs[0]:
        comps = analysis.get("competencies", [])
        for c in comps:
            label = f"{c.get('name','')} — {c.get('candidate_level','')} / {c.get('interview_risk','')} risk"
            with st.expander(label):
                a,b = st.columns(2)
                with a:
                    st.write(f"**Importance:** {c.get('importance')}")
                    st.write(f"**JD signal:** {c.get('jd_signal')}")
                    st.write(f"**Evidence:** {c.get('evidence')}")
                    st.write(f"**Gap:** {c.get('gap')}")
                with b: st.write("**SME language:** " + ", ".join(c.get("sme_language", [])))
        st.markdown("**Training priorities**")
        for x in analysis.get("training_priorities", []): st.write("• " + x)

    with tabs[1]:
        st.markdown("**Company context**")
        for x in ctx.get("company_context", []): st.write("• " + x)
        st.markdown("**Technical signals**")
        for x in ctx.get("technical_stack_signals", []): st.write("• " + x)
        st.markdown("**Likely interview themes**")
        for x in ctx.get("likely_interview_themes", []): st.write("• " + x)
        if ctx.get("inferences"): st.info("Inference: " + " | ".join(ctx["inferences"]))

    with tabs[2]:
        st.write(graph.get("candidate_summary", ""))
        for r in graph.get("roles", []):
            with st.expander(f"{r.get('title','')} — {r.get('company','')}"):
                st.write("**Responsibilities:** " + "; ".join(r.get("responsibilities", [])))
                st.write("**Technologies:** " + ", ".join(r.get("technologies", [])))
                st.write("**Outcomes:** " + "; ".join(r.get("outcomes", [])))
        st.markdown("**Capabilities**")
        st.write(", ".join(graph.get("capabilities", [])))

    with tabs[3]:
        names = [c.get("name", "") for c in analysis.get("competencies", [])]
        if names:
            selected = st.selectbox("Competency", names)
            comp = next(c for c in analysis["competencies"] if c.get("name") == selected)
            if st.button("Generate SME Module", key="train"):
                try:
                    with st.spinner("Building module…"): st.session_state.module = training_module(analysis, comp, ctx)
                except Exception as e: st.error(str(e))
            m = st.session_state.get("module")
            if m:
                st.write("**What it means**", m.get("what_it_means", ""))
                st.write("**Why the role cares**", m.get("why_the_role_cares", ""))
                st.write("**How an SME thinks**"); [st.write("• "+x) for x in m.get("how_an_sme_thinks", [])]
                st.write("**Architecture / workflow**"); [st.write(f"{i}. {x}") for i,x in enumerate(m.get("architecture_or_workflow", []),1)]
                st.write("**Tradeoffs**", " | ".join(m.get("tradeoffs", [])))
                st.write("**Failure modes**", " | ".join(m.get("failure_modes", [])))
                st.write("**Language upgrades**"); [st.write("• "+x) for x in m.get("language_upgrade", [])]
                st.info("Candidate bridge: " + m.get("candidate_bridge", ""))
                st.error("Truth boundary: " + m.get("red_line", ""))
                st.write("**Practice prompt**", m.get("practice_prompt", ""))
                st.write("**Gold-standard outline**"); [st.write("• "+x) for x in m.get("gold_standard_answer_outline", [])]

    with tabs[4]:
        st.markdown("### Interviewer model")
        st.write(f"**Archetype:** {persona.get('persona_archetype','')}  |  **Seniority:** {persona.get('seniority','')}")
        st.write("**Style:** " + persona.get("style", ""))
        st.write("**Priorities:** " + ", ".join(persona.get("priorities", [])))
        if "current_question" not in st.session_state:
            st.session_state.current_question = analysis.get("likely_questions", ["Walk me through your approach."])[0]
        st.markdown("### Live interview")
        st.write("**Question:** " + st.session_state.current_question)
        answer = st.text_area("Your answer", height=190, key="answer_box", placeholder="Answer naturally. The system is evaluating reasoning, not memorization.")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Grade & Continue", type="primary"):
                if not answer.strip(): st.error("Give an answer first.")
                else:
                    comp = analysis.get("competencies", [{}])[0]
                    # Prefer a competency whose SME language appears in the question.
                    for c in analysis.get("competencies", []):
                        if any(t.lower() in st.session_state.current_question.lower() for t in c.get("sme_language", [])):
                            comp = c; break
                    try:
                        with st.spinner("Evaluating…"):
                            grade = grade_answer(analysis, comp, st.session_state.current_question, answer, persona)
                            history.append({"question":st.session_state.current_question,"answer":answer,"grade":grade,"competency":comp.get("name")})
                            st.session_state.grade = grade
                            st.session_state.next = adaptive_next(analysis, history)
                            st.session_state.current_question = synthesize_question(analysis, persona, history)
                            save_session(st.session_state.session_id, st.session_state.candidate_id, analysis.get("role",""), st.session_state.company, st.session_state.jd_text, analysis, ctx, history)
                            st.rerun()
                    except Exception as e: st.error(str(e))
        with c2:
            if st.button("Next Question"):
                st.session_state.current_question = synthesize_question(analysis, persona, history)
                st.rerun()
        g = st.session_state.get("grade")
        if g:
            st.metric("Overall readiness", f"{g.get('overall_score',0)}/10")
            cols = st.columns(4)
            for col,(label,key) in zip(cols,[("Accuracy","technical_accuracy"),("Depth","depth"),("Tradeoffs","tradeoff_reasoning"),("Credibility","credibility")]): col.metric(label,f"{g.get(key,0)}/10")
            st.write("**What worked**"); [st.write("• "+x) for x in g.get("what_worked", [])]
            st.write("**Missing**"); [st.write("• "+x) for x in g.get("what_is_missing", [])]
            if g.get("unsupported_or_risky_claims"): st.warning(" | ".join(g["unsupported_or_risky_claims"]))
            st.info(g.get("coach_note", ""))
        if st.session_state.get("next"):
            n=st.session_state.next
            st.markdown("### Adaptive curriculum")
            st.write(f"**Next target:** {n.get('next_competency','')} — {n.get('reason','')}")
            st.write(f"**Exercise:** {n.get('exercise','')}")
            st.write("**Success criteria:** " + "; ".join(n.get("success_criteria", [])))
        st.markdown("### Voice interview")
        st.caption("One-day MVP mode: record a turn, transcribe it, grade it, and optionally hear the interviewer response. Full low-latency Realtime/WebRTC can replace this transport later.")
        if not ai_provider.voice_available():
            st.info("Recorded answers require OPENAI_API_KEY — Anthropic exposes no speech-to-text API. Typed answers above use the active provider.")
        else:
            audio = st.audio_input("Record your answer")
            if audio:
                if st.button("Process recorded answer", key="voice_process"):
                    path = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                            f.write(audio.getvalue()); path=f.name
                        st.session_state.voice_transcript = ai_provider.transcribe(path)
                        st.rerun()
                    except Exception as e: st.error(str(e))
                    finally:
                        if path and os.path.exists(path):
                            os.unlink(path)
        if st.session_state.get("voice_transcript"):
            st.write("**Transcript:** " + st.session_state.voice_transcript)
            if st.button("Grade transcript", key="voice_grade"):
                comp=analysis.get("competencies", [{}])[0]
                try:
                    st.session_state.grade=grade_answer(analysis,comp,st.session_state.current_question,st.session_state.voice_transcript,persona)
                    st.rerun()
                except Exception as e: st.error(str(e))

    with tabs[5]:
        st.markdown("### Evidence-backed technical sources")
        topic = st.text_input("Research a technical claim/topic", placeholder="e.g. MCP tool orchestration, RAG evaluation")
        if st.button("Find authoritative sources") and topic.strip():
            try: st.session_state.sources = sources_for_topic(topic.strip())
            except Exception as e: st.error(str(e))
        for s in st.session_state.get("sources", {}).get("claims", []):
            st.markdown(f"**{s.get('claim','')}** — [{s.get('source','source')}]({s.get('url','#')})")
        st.markdown("### Interview battle card")
        if st.button("Generate battle card"):
            try:
                with st.spinner("Compiling battle card…"):
                    st.session_state.battle = battle_card(analysis,ctx,persona,history,graph)
            except Exception as e: st.error(str(e))
        if st.session_state.get("battle"):
            st.download_button("Download Markdown battle card", st.session_state.battle, file_name="RoleIQ_Interview_Battle_Card.md", mime="text/markdown")
            st.markdown(st.session_state.battle)
        if ROLE_CONTEXT_ENABLED:
            st.markdown("### Public context sources")
            for s in ctx.get("sources", []):
                st.markdown(f"- [{s.get('title','Source')}]({s.get('url','#')}) — {s.get('claim_supported','')}")

else:
    st.info("Start with a JD and resume. RoleIQ will build a persistent Experience Graph, resolve role/company context, model interviewer behavior, train SME fluency, and adapt interview practice to your answer history.")
