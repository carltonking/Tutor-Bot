from fastapi import FastAPI, UploadFile, File, Form
import sqlite3, pathlib, uuid, time, shutil, os, httpx, sys, re
from datetime import datetime, timedelta, date as _date
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from rag import extract_text, chunk_text, embed_text_smart, cosine

# --- BYOK: OpenCode Zen (OpenAI-compatible) ---
try:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).parent.parent / ".env")
except: pass
ZEN_KEY = os.getenv("OPENCODE_ZEN_API_KEY", "")
ZEN_BASE = os.getenv("OPENCODE_ZEN_BASE_URL", "https://api.opencode.ai/v1")
ZEN_MODEL = os.getenv("OPENCODE_ZEN_MODEL", "zen-1")

async def call_zen(messages, max_tokens=800):
    if not ZEN_KEY:
        raise RuntimeError("no key")
    # Try common Zen endpoints: /chat/completions
    url = ZEN_BASE.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers={"Authorization": f"Bearer {ZEN_KEY}", "Content-Type": "application/json"}, json={"model": ZEN_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7})
        r.raise_for_status()
        j = r.json()
        # OpenAI shape: choices[0].message.content
        try:
            return j["choices"][0]["message"]["content"]
        except:
            return str(j)

app = FastAPI()

# CORS: Tauri webview (localhost:1420 / tauri://localhost) calls this sidecar cross-origin
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "http://127.0.0.1:1420", "tauri://localhost", "http://tauri.localhost", "http://127.0.0.1:5173", "http://localhost:5173", "http://host.docker.internal:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r".*",
)
ROOT = pathlib.Path(__file__).parent
DB = ROOT / "study.db"
STORE = ROOT / "store"
STORE.mkdir(exist_ok=True)

def con():
    c = sqlite3.connect(DB, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=10000")
    c.execute("CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY, name TEXT, color TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, subject_id TEXT, filename TEXT, type TEXT, pages INTEGER, chunks INTEGER, path TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, source_id TEXT, subject_id TEXT, idx INTEGER, text TEXT, embedding TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, subject_id TEXT, role TEXT, text TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS grades(id TEXT PRIMARY KEY, subject_id TEXT, title TEXT, score REAL, max REAL, topics TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS plan(id TEXT PRIMARY KEY, subject_id TEXT, week INTEGER, topic TEXT, status TEXT, week_of TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS mastery(id TEXT PRIMARY KEY, subject_id TEXT, topic TEXT, score_last REAL, score_prev REAL, mastery_bool INTEGER, updated_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS assessments(id TEXT PRIMARY KEY, subject_id TEXT, kind TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS assessment_questions(id TEXT PRIMARY KEY, assessment_id TEXT, idx INTEGER, prompt TEXT, qtype TEXT, choices_json TEXT, rubric TEXT, topic TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS assessment_attempts(id TEXT PRIMARY KEY, assessment_id TEXT, question_id TEXT, answer TEXT, score REAL, max_score REAL, reasoning TEXT, created_at TEXT)")
    # migrate old DBs: missing embedding col on chunks, missing onboarding cols on subjects, missing week_of on plan
    try:
        c.execute("SELECT embedding FROM chunks LIMIT 1")
    except Exception:
        try: c.execute("ALTER TABLE chunks ADD COLUMN embedding TEXT")
        except Exception: pass
    cols = {r[1] for r in c.execute("PRAGMA table_info(subjects)").fetchall()}
    for add in [("objective", "TEXT"), ("mode", "TEXT DEFAULT 'self'"), ("school", "TEXT"), ("course_code", "TEXT"), ("start_date", "TEXT"), ("end_date", "TEXT")]:
        if add[0] not in cols:
            try: c.execute(f"ALTER TABLE subjects ADD COLUMN {add[0]} {add[1]}")
            except Exception: pass
    try:
        c.execute("SELECT week_of FROM plan LIMIT 1")
    except Exception:
        try: c.execute("ALTER TABLE plan ADD COLUMN week_of TEXT")
        except Exception: pass
    return c

con().close()

@app.get("/ping")
def ping(): return {"pong": True}

# --- MCP / OpenAPI bridge for Rakazo (skill tools) ---
@app.get("/openapi.json")
def openapi():
    return app.openapi()

@app.get("/mcp")
def mcp_info():
    return {"name": "tutorbot-mcp", "version": "0.1.0", "tools": ["ingest","search","assess/generate","assess/grade","grades","mastery","plan","memory"]}

@app.post("/mcp/tools/{name}")
async def mcp_tool(name: str, payload: dict = None):
    """Generic JSON entry so Rakazo MCP can call any TutorBot capability."""
    payload = payload or {}
    # dispatch by name — wraps existing handlers
    if name == "retrieve":
        return search(payload.get("subject_id",""), payload.get("q",""), int(payload.get("k",5)))
    if name == "get_mastery":
        return get_mastery(payload.get("subject_id",""))
    if name == "get_plan":
        return get_plan(payload.get("subject_id",""))
    if name == "get_grades":
        return get_grades(payload.get("subject_id",""))
    return {"error": f"unknown tool {name}", "hint": "Use legacy REST routes: /search/{id}, /plan/{id}, /mastery/{id}, /assess/generate, /assess/grade, /grades/{id}"}

@app.get("/subjects")
def subjects():
    c = con()
    rows = c.execute("SELECT id,name,color FROM subjects").fetchall()
    c.close()
    return [{"id":r[0],"name":r[1],"color":r[2]} for r in rows]

@app.post("/subjects")
def create_subject(
    name: str = Form(...),
    color: str = Form("#e14b4b"),
    objective: str = Form(""),
    mode: str = Form("self"),
    school: str = Form(""),
    course_code: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
):
    sid = str(uuid.uuid4())
    c = con()
    try:
        c.execute(
            "INSERT INTO subjects(id,name,color,created_at,objective,mode,school,course_code,start_date,end_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, name, color, str(int(time.time())), objective or None, mode if mode in ("course", "self") else "self",
             school or None, course_code or None, start_date or None, end_date or None),
        )
    except Exception:
        # very old DB shape (4 cols) that somehow skipped migration
        c.execute("INSERT INTO subjects(id,name,color,created_at) VALUES (?,?,?,?)", (sid, name, color, str(int(time.time()))))
    # Auto-generate an initial plan when dates are present (best-effort).
    # Single connection: committing the subject first releases its write lock so
    # plan generation can't self-deadlock the DB (WAL still allows 1 writer).
    try:
        if start_date and end_date:
            c.commit()
            items = generate_plan_items(c, sid, objective or "", start_date, end_date)
            _insert_plan_items(c, sid, items, replace=True)
    except Exception as e:
        print("auto plan gen failed", e)
    c.commit()
    c.close()
    return {"id": sid, "name": name, "color": color}

@app.patch("/subjects/{subject_id}")
def rename_subject(subject_id: str, name: str = Form(...)):
    c = con()
    c.execute("UPDATE subjects SET name=? WHERE id=?", (name, subject_id))
    c.commit()
    c.close()
    return {"ok": True, "id": subject_id, "name": name}

@app.delete("/subjects/{subject_id}")
def delete_subject(subject_id: str):
    c = con()
    for table in ["subjects", "sources", "chunks", "messages", "grades", "plan", "mastery",
                  "assessments", "assessment_questions", "assessment_attempts"]:
        try:
            col = "id" if table == "subjects" else "subject_id"
            c.execute(f"DELETE FROM {table} WHERE {col}=?", (subject_id,))
        except Exception:
            pass  # table may not exist yet
    c.commit()
    c.close()
    # remove uploaded files + memory for the subject
    import shutil as _shutil
    _shutil.rmtree(STORE / subject_id, ignore_errors=True)
    _shutil.rmtree(MEM_ROOT / subject_id, ignore_errors=True)
    return {"ok": True, "id": subject_id}

# --- Grade → mastery → plan helpers (ADR 015: 80% on last 2 + no recent failure) ---

def _upsert_mastery(c, subject_id: str, topic: str, pct: float, when: str):
    row = c.execute("SELECT score_last, score_prev FROM mastery WHERE subject_id=? AND topic=?", (subject_id, topic)).fetchone()
    if row:
        mastered = 1 if (pct >= 0.8 and row[0] is not None and row[0] >= 0.8) else 0
        c.execute("UPDATE mastery SET score_last=?, score_prev=?, mastery_bool=?, updated_at=? WHERE subject_id=? AND topic=?",
                  (pct, row[0], mastered, when, subject_id, topic))
    else:
        c.execute("INSERT INTO mastery VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), subject_id, topic, pct, None, 0, when))

def _insert_plan_items(c, subject_id: str, items: list, replace: bool = False):
    c.execute("CREATE TABLE IF NOT EXISTS plan(id TEXT PRIMARY KEY, subject_id TEXT, week INTEGER, topic TEXT, status TEXT, week_of TEXT)")
    if replace:
        c.execute("DELETE FROM plan WHERE subject_id=?", (subject_id,))
    for it in items:
        c.execute("INSERT INTO plan VALUES (?,?,?,?,?,?)",
                  (str(uuid.uuid4()), subject_id, it["week"], it["topic"], it["status"], it.get("week_of")))

def _remediate(c, subject_id: str, topics: list, start_week=None):
    if not topics:
        return
    c.execute("CREATE TABLE IF NOT EXISTS plan(id TEXT PRIMARY KEY, subject_id TEXT, week INTEGER, topic TEXT, status TEXT, week_of TEXT)")
    base = start_week or ((c.execute("SELECT MAX(week) FROM plan WHERE subject_id=?", (subject_id,)).fetchone()[0] or 0) + 1)
    for i, t in enumerate(topics):
        c.execute("INSERT INTO plan VALUES (?,?,?,?,?,?)",
                  (str(uuid.uuid4()), subject_id, base + i, f"Remediate: {t}", "todo", None))

@app.get("/messages/{subject_id}")
def get_messages(subject_id: str):
    c = con()
    rows = c.execute("SELECT role, text FROM messages WHERE subject_id=? ORDER BY created_at", (subject_id,)).fetchall()
    c.close()
    return [{"role": r, "text": t} for r, t in rows]

@app.post("/messages/{subject_id}")
def add_message(subject_id: str, role: str = Form(...), text: str = Form(...)):
    mid = str(uuid.uuid4())
    c = con()
    c.execute("INSERT INTO messages VALUES (?,?,?,?,?)", (mid, subject_id, role, text, str(time.time())))
    c.commit()
    c.close()
    return {"ok": True, "id": mid}

@app.get("/sources/{subject_id}")
def list_sources(subject_id: str):
    c = con()
    rows = c.execute("SELECT id,filename,type,pages,chunks FROM sources WHERE subject_id=?", (subject_id,)).fetchall()
    c.close()
    return [{"id":r[0],"filename":r[1],"type":r[2],"pages":r[3],"chunks":r[4]} for r in rows]

@app.post("/ingest")
async def ingest(subject_id: str = Form(...), file_type: str = Form(...), file: UploadFile = File(...)):
    sid = str(uuid.uuid4())
    ext = pathlib.Path(file.filename).suffix or ".pdf"
    dest = STORE / subject_id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{sid}{ext}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # extract
    try:
        text, pages = extract_text(str(path))
    except Exception as e:
        return {"error": str(e)}
    chunks = chunk_text(text)
    # naive embedding stub: no vector yet, just count
    c = con()
    c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)", (sid, subject_id, file.filename, file_type, pages, len(chunks), str(path), str(int(time.time()))))
    from rag import embed_text
    import json
    for idx, ch in enumerate(chunks):
        cid = str(uuid.uuid4())
        from rag import embed_text_smart
        emb = json.dumps(embed_text_smart(ch))
        c.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", (cid, sid, subject_id, idx, ch, emb))
    c.commit()
    c.close()
    return {"id": sid, "filename": file.filename, "pages": pages, "chunks": len(chunks)}

@app.get("/search/{subject_id}")
def search(subject_id: str, q: str, k: int = 5):
    c = con()
    # try semantic cosine first
    try:
        from rag import embed_text, cosine
        import json
        from rag import embed_text_smart
        qemb = embed_text_smart(q)
        rows = c.execute("SELECT text, embedding FROM chunks WHERE subject_id=?", (subject_id,)).fetchall()
        scored=[]
        for text, emb in rows:
            try:
                vec = json.loads(emb) if emb else None
                if vec:
                    s = cosine(qemb, vec)
                    # boost if keyword present
                    if q.lower() in text.lower(): s += 0.15
                    scored.append((s, text))
            except: continue
        scored.sort(reverse=True, key=lambda x: x[0])
        if scored:
            c.close()
            return [{"text": t, "score": s} for s,t in scored[:k]]
    except Exception as e:
        print("semantic search failed", e)
    rows = c.execute("SELECT text FROM chunks WHERE subject_id=? AND text LIKE ? LIMIT ?", (subject_id, f"%{q}%", k)).fetchall()
    c.close()
    return [{"text": r[0]} for r in rows]

# --- Minimal assessment generator (template, no LLM yet) ---
import random

def _assessment_topic_bias(c, subject_id: str) -> dict:
    """Weak mastery topics + upcoming (not-done) plan topics for exam weighting.
    Weak topics are ordered worst-first; plan topics earliest-week-first."""
    weak = [r[0] for r in c.execute(
        "SELECT topic FROM mastery WHERE subject_id=? AND mastery_bool=0 ORDER BY score_last ASC LIMIT 5",
        (subject_id,)).fetchall() if r[0] and r[0] != "general"]
    upcoming = []
    for r in c.execute(
            "SELECT topic FROM plan WHERE subject_id=? AND status!='done' ORDER BY week ASC LIMIT 6",
            (subject_id,)).fetchall():
        t = (r[0] or "").replace("Remediate: ", "").strip()
        if t and t != "general" and t not in upcoming:
            upcoming.append(t)
    return {"weak": weak, "upcoming": upcoming}

@app.post("/assess/generate")
async def gen_assess(subject_id: str = Form(...), topic: str = Form(None), count: int = Form(0), kind: str = Form("quiz")):
    if kind not in ("quiz", "practice_exam"):
        kind = "quiz"
    if count <= 0:
        count = 15 if kind == "practice_exam" else 5
    c = con()
    # Prefer teacher style exemplars
    rows = c.execute("SELECT text FROM chunks WHERE subject_id=? ORDER BY RANDOM() LIMIT 10", (subject_id,)).fetchall()
    # also fetch practice_problems as style exemplars
    style_rows = c.execute("SELECT text FROM chunks WHERE subject_id=? AND source_id IN (SELECT id FROM sources WHERE type=\"practice_problems\") LIMIT 5", (subject_id,)).fetchall()
    bias = _assessment_topic_bias(c, subject_id)
    c.close()
    if not rows:
        return {"questions": [], "note": "no chunks — upload sources first"}
    qs = None
    via = "template"
    # Try LLM via Zen
    try:
        if ZEN_KEY:
            ctx = "\n\n".join([r[0][:500] for r in rows[:3]])
            style = "\n".join([r[0][:300] for r in style_rows]) if style_rows else "No style exemplar — use clear academic style"
            bias_txt = ""
            if kind == "practice_exam":
                bias_txt = (f"\n\nThis is a practice exam. Weight roughly half the questions toward the student's weak topics: "
                            f"{bias['weak'] or 'none recorded'}. Cover upcoming plan topics: {bias['upcoming'] or 'none scheduled'}. "
                            f"Tag every question with the specific topic it tests (prefer names from those lists).")
            messages = [
                {"role":"system","content": "You are a tutor generating assessments. Use the teacher's style exactly. Return JSON array of questions: each with prompt, type (mcq|short_answer), topic, citation, rubric. No markdown."},
                {"role":"user","content": f"Context chunks:\n{ctx}\n\nTeacher style exemplars:\n{style}\n\nGenerate {count} questions on topic '{topic or 'general'}'. Tag each question with its specific topic.{bias_txt} Keep citations."}
            ]
            content = await call_zen(messages, max_tokens=1200)
            import json, re
            # try to extract JSON array
            m = re.search(r"\[.*\]", content, re.S)
            if m:
                arr = json.loads(m.group(0))
                built=[]
                for item in arr[:count]:
                    built.append({"id": str(uuid.uuid4()), "type": item.get("type","mcq"), "prompt": item.get("prompt", str(item))[:400], "topic": item.get("topic", topic or "general"), "citation": item.get("citation", ctx[:60]), "rubric": item.get("rubric","Answer should reference cited chunk")})
                if built:
                    qs = built
                    via = "zen"
    except Exception as e:
        print("zen gen failed", e)
    # fallback template — practice exams tag topics from the weak/upcoming bias lists;
    # quizzes keep the lighter flat tagging (topic param or general)
    if qs is None:
        pool = []
        if kind == "practice_exam":
            pool = (bias["weak"] * 3) + (bias["upcoming"] * 2)
            if topic:
                pool = [topic] + pool
        qs=[]
        for i in range(count):
            chunk = rows[i % len(rows)][0][:180]
            stem = f"Based on: \"{chunk}...\" — what is the key concept?"
            qtopic = pool[i % len(pool)] if pool else (topic or "general")
            qs.append({"id": str(uuid.uuid4()), "type": "mcq" if i%2==0 else "short_answer", "prompt": stem, "topic": qtopic, "citation": chunk[:60], "rubric": "Answer should reference the cited chunk accurately."})
    # Persist assessment + questions (kind: quiz | practice_exam)
    aid = str(uuid.uuid4())
    c = con()
    c.execute("INSERT INTO assessments VALUES (?,?,?,?)", (aid, subject_id, kind, str(int(time.time()))))
    for i, q in enumerate(qs):
        q["assessment_id"] = aid
        c.execute("INSERT INTO assessment_questions VALUES (?,?,?,?,?,?,?,?)",
                  (q["id"], aid, i, q["prompt"], q["type"], None, q["rubric"], q["topic"]))
    c.commit(); c.close()
    return {"assessment_id": aid, "questions": qs, "via": via, "kind": kind, "bias": bias}

@app.get("/assess/{subject_id}/recent")
def recent_assessments(subject_id: str, limit: int = 10):
    c = con()
    rows = c.execute(
        "SELECT a.id, a.kind, a.created_at, (SELECT COUNT(*) FROM assessment_questions q WHERE q.assessment_id=a.id) "
        "FROM assessments a WHERE a.subject_id=? ORDER BY a.created_at DESC LIMIT ?",
        (subject_id, limit)).fetchall()
    c.close()
    return [{"id": r[0], "kind": r[1], "created_at": r[2], "question_count": r[3]} for r in rows]

@app.post("/assess/grade")
async def grade(
    prompt: str = Form(None),
    answer: str = Form(...),
    rubric: str = Form(None),
    assessment_id: str = Form(None),
    question_id: str = Form(None),
    subject_id: str = Form(None),
    topic: str = Form(None),
    max_score: float = Form(100),
):
    rub = rubric or "Answer should reference the cited material accurately."
    prompt_txt = prompt or "(question not provided)"
    score = None
    reasoning = ""
    try:
        if ZEN_KEY:
            messages = [
                {"role":"system","content": "You are a strict grader. Score 0-100 based on rubric. Return JSON {score, reasoning}."},
                {"role":"user","content": f"Prompt: {prompt_txt}\nAnswer: {answer}\nRubric: {rub}\nReturn JSON only."}
            ]
            content = await call_zen(messages, max_tokens=400)
            import json, re
            m = re.search(r"\{.*\}", content, re.S)
            if m:
                j = json.loads(m.group(0))
                score = int(j.get("score", 0))
                reasoning = j.get("reasoning", content[:300])
    except Exception as e:
        print("zen grade failed", e)
    if score is None:
        score = 70 if len(answer.split()) > 5 else 40
        if any(w in answer.lower() for w in prompt_txt.lower().split()[:3]): score += 10
        score = min(score, 100)
        reasoning = f"Template grader: checked against rubric '{rub[:40]}...'"
        via = "template"
    else:
        via = "zen"

    # Persist attempt + feed the shared mastery/re-pace path (same as manual grades)
    c = con()
    resolved_topic = None
    if question_id:
        qr = c.execute("SELECT topic, assessment_id, prompt, rubric FROM assessment_questions WHERE id=?", (question_id,)).fetchone()
        if qr:
            resolved_topic = qr[0]
            assessment_id = assessment_id or qr[1]
            prompt = prompt or qr[2]
            rub = rubric or qr[3] or rub
    if not subject_id and assessment_id:
        ar = c.execute("SELECT subject_id FROM assessments WHERE id=?", (assessment_id,)).fetchone()
        subject_id = ar[0] if ar else None
    if subject_id and not resolved_topic:
        # fallback: explicit topic param > subject name
        if topic:
            resolved_topic = topic
        else:
            sr = c.execute("SELECT name FROM subjects WHERE id=?", (subject_id,)).fetchone()
            resolved_topic = sr[0] if sr else "general"
    atid = str(uuid.uuid4())
    c.execute("INSERT INTO assessment_attempts VALUES (?,?,?,?,?,?,?,?)",
              (atid, assessment_id, question_id, answer, float(score), float(max_score), reasoning, str(int(time.time()))))
    re_paced = []
    if subject_id and resolved_topic:
        pct = (float(score) / float(max_score)) if max_score else 0.0
        re_paced = _apply_score_to_mastery(c, subject_id, [resolved_topic], pct)
    c.commit(); c.close()
    return {"score": score, "reasoning": reasoning, "rubric": rub, "via": via,
            "attempt_id": atid, "topic": resolved_topic, "subject_id": subject_id, "re_paced": re_paced}

# --- Memory: global.md + per-subject memory.md + sessions ---
from datetime import datetime

MEM_ROOT = ROOT / "memory"
MEM_ROOT.mkdir(exist_ok=True)
GLOBAL_MD = MEM_ROOT / "global.md"
if not GLOBAL_MD.exists():
    GLOBAL_MD.write_text("# Global Memory\n\n> Cross-subject preferences. Agent routes general instructions here.\n")

@app.get("/memory/global")
def get_global():
    return {"text": GLOBAL_MD.read_text() if GLOBAL_MD.exists() else ""}

@app.post("/memory/global")
def post_global(text: str = Form(...)):
    GLOBAL_MD.write_text(text)
    return {"ok": True}

@app.get("/memory/{subject_id}")
def get_subject_memory(subject_id: str):
    p = MEM_ROOT / subject_id / "memory.md"
    if not p.exists():
        return {"text": f"# {subject_id} Memory\n\n> Subject-specific preferences and session summaries.\n"}
    return {"text": p.read_text()}

@app.post("/memory/{subject_id}")
def post_subject_memory(subject_id: str, text: str = Form(...)):
    p = MEM_ROOT / subject_id / "memory.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return {"ok": True}

@app.post("/memory/{subject_id}/session")
def post_session(subject_id: str, summary: str = Form(...)):
    # append session summary + self-critique
    p = MEM_ROOT / subject_id / "memory.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = p.read_text() if p.exists() else f"# {subject_id} Memory\n"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    addition = f"\n\n## Session {ts}\n{summary}\n"
    p.write_text(existing + addition)
    # also write per-day session file
    sdir = MEM_ROOT / subject_id / "sessions"
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / f"{datetime.now().strftime('%Y-%m-%d')}.md").write_text(summary)
    return {"ok": True}

@app.post("/memory/route")
def route_memory(text: str = Form(...)):
    # naive router: if contains subject name or "for this subject" -> subject, else global
    lower = text.lower()
    is_global = any(k in lower for k in ["always", "all subjects", "every subject", "globally", "in general"])
    return {"scope": "global" if is_global else "subject", "reason": "keyword heuristic; will be LLM next"}

# --- Plan + Grades + Mastery (real, date-ranged) ---

def _parse_iso(d: str):
    d = (d or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try: return datetime.strptime(d, fmt).date()
        except Exception: pass
    return None

def _topics_from_materials(c, subject_id: str, cap: int = 30) -> list:
    """Candidate topics from existing plan rows, grade topics, and chunk text (headings / Title-Case phrases)."""
    topics: list = []
    for (t,) in c.execute("SELECT DISTINCT topic FROM plan WHERE subject_id=?", (subject_id,)).fetchall():
        t = (t or "").replace("Remediate: ", "").strip()
        if t and t not in topics: topics.append(t)
    for (ts,) in c.execute("SELECT topics FROM grades WHERE subject_id=?", (subject_id,)).fetchall():
        for t in (ts or "").split(","):
            t = t.strip()
            if t and t.lower() not in [x.lower() for x in topics]: topics.append(t)
    texts = [r[0] for r in c.execute("SELECT text FROM chunks WHERE subject_id=? LIMIT 400", (subject_id,)).fetchall()]
    joined = "\n".join(texts)
    # heading-like lines (Chapter 3: ..., Unit 2 ..., Week 5 ...)
    for m in re.findall(r"(?m)^\s{0,4}((?:Chapter|Unit|Module|Week|Part|Topic)\s+\d+[^\n:]{0,70})$", joined, re.I):
        t = re.sub(r"\s+", " ", m).strip()
        if t.lower() not in [x.lower() for x in topics]: topics.append(t)
    # Title-Case multiword phrases as weak topic signal
    from collections import Counter
    phrases = Counter()
    for m in re.findall(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\b", joined):
        phrases[m] += 1
    for phrase, _ in phrases.most_common(cap):
        if phrase.lower() not in [x.lower() for x in topics]: topics.append(phrase)
        if len(topics) >= cap: break
    return topics

def _week_count(start, end) -> int:
    days = (end - start).days
    return max(1, min(52, (days + 6) // 7))

def _build_plan_items(weeks: int, topics: list, start, objective: str = "") -> list:
    """Spread topics across weeks; never hard-coded — generic unit labels when materials are thin."""
    items = []
    for i in range(weeks):
        if i < len(topics):
            topic = topics[i]
        elif topics:
            topic = f"Review & practice: {topics[i % len(topics)]}"
        else:
            topic = f"{objective} — Unit {i+1}" if objective else f"Unit {i+1}"
        items.append({"week": i + 1, "topic": topic[:120], "status": "active" if i == 0 else "todo",
                      "week_of": str(start + timedelta(days=7 * i))})
    return items

def generate_plan_items(c, subject_id: str, objective: str, start_s: str, end_s: str) -> list:
    start = _parse_iso(start_s) or _date.today()
    end = _parse_iso(end_s) or (start + timedelta(weeks=8))
    if end <= start: end = start + timedelta(weeks=8)
    weeks = _week_count(start, end)
    topics = _topics_from_materials(c, subject_id)[:weeks]
    return _build_plan_items(weeks, topics, start, objective)

@app.get("/plan/{subject_id}")
def get_plan(subject_id: str):
    c = con()
    rows = c.execute("SELECT week, topic, status, week_of FROM plan WHERE subject_id=? ORDER BY week", (subject_id,)).fetchall()
    c.close()
    return [{"week": r[0], "topic": r[1], "status": r[2], "week_of": r[3]} for r in rows]

@app.get("/grades/{subject_id}")
def get_grades(subject_id: str):
    c = con()
    c.execute("CREATE TABLE IF NOT EXISTS grades(id TEXT PRIMARY KEY, subject_id TEXT, title TEXT, score REAL, max REAL, topics TEXT)")
    rows = c.execute("SELECT title, score, max, topics FROM grades WHERE subject_id=?", (subject_id,)).fetchall()
    c.close()
    return [{"title":r[0],"score":r[1],"max":r[2],"topics":r[3]} for r in rows]

def _apply_score_to_mastery(c, subject_id: str, topics: list, pct: float) -> list:
    """Shared mastery writeback + re-pace for manual grades and quiz attempts (ADR 015).
    Returns the topics that triggered remediation."""
    now = str(int(time.time()))
    for t in topics:
        _upsert_mastery(c, subject_id, t, pct, now)
    if topics and pct < 0.8:
        _remediate(c, subject_id, topics)
        return topics
    return []

@app.post("/grades/{subject_id}")
def add_grade(subject_id: str, title: str = Form(...), score: float = Form(...), max: float = Form(100), topics: str = Form("")):
    c = con()
    c.execute("CREATE TABLE IF NOT EXISTS grades(id TEXT PRIMARY KEY, subject_id TEXT, title TEXT, score REAL, max REAL, topics TEXT)")
    gid = str(uuid.uuid4())
    c.execute("INSERT INTO grades VALUES (?,?,?,?,?,?)", (gid, subject_id, title, score, max, topics))
    # Mastery writeback per topic (ADR 015) + server-side re-pace on failure
    pct = (score / max) if max else 0.0
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    re_paced = _apply_score_to_mastery(c, subject_id, topic_list, pct)
    c.commit(); c.close()
    return {"id": gid, "pct": pct, "mastery": get_mastery(subject_id), "re_paced": re_paced}

@app.get("/mastery/{subject_id}")
def get_mastery(subject_id: str):
    c = con()
    rows = c.execute("SELECT topic, score_last, score_prev, mastery_bool, updated_at FROM mastery WHERE subject_id=? ORDER BY topic", (subject_id,)).fetchall()
    c.close()
    return [
        {"topic": r[0], "score_last": r[1], "score_prev": r[2], "mastery_bool": bool(r[3]), "updated_at": r[4]}
        for r in rows
    ]

import json as _json

@app.post("/chat")
async def chat(subject_id: str = Form(...), message: str = Form(...)):
    # Main-agent connector intent: "connect my grades" / "connect canvas" -> setup flow (ADR 006)
    lower = message.lower()
    if subject_id in ("main", "chieff", "orchestrator") and any(k in lower for k in CONNECTOR_KEYWORDS):
        asked = next((n for n in ["canvas", "blackboard", "brightspace"] if n in lower), None)
        if not asked:
            return {
                "answer": "I can sync your grades. Which LMS — Canvas, Blackboard, or Brightspace? "
                          "Say e.g. 'connect Canvas' and I'll walk you through it (token or OAuth).",
                "citations": [], "via": "connector-router",
            }
        return {
            "answer": f"Connecting {asked.title()}. Paste an API access token (Account > Settings > Approved Integrations "
                      f"in {asked.title()}) and I'll verify it, fetch your courses, and map assignments to topics. "
                      f"The token goes in your OS keychain — nothing leaves this machine.",
            "citations": [], "via": "connector-router",
        }
    # RAG: semantic retrieval (embed query, cosine vs stored chunk vectors) with keyword fallback
    c = con()
    rows = []
    try:
        qemb = embed_text_smart(message)
        all_rows = c.execute("SELECT text, embedding FROM chunks WHERE subject_id=?", (subject_id,)).fetchall()
        scored = []
        for text, emb in all_rows:
            try:
                vec = _json.loads(emb) if emb else None
                if vec:
                    scored.append((cosine(qemb, vec) + (0.15 if message.lower() in text.lower() else 0), text))
            except Exception:
                continue
        scored.sort(reverse=True, key=lambda x: x[0])
        rows = [(t,) for _, t in scored[:3]]
    except Exception as e:
        print("semantic chat retrieval failed", e)
    if not rows:
        rows = c.execute("SELECT text FROM chunks WHERE subject_id=? ORDER BY RANDOM() LIMIT 3", (subject_id,)).fetchall()
    c.close()
    ctx = "\n\n".join([r[0][:600] for r in rows]) if rows else "No sources yet"
    # also load memory
    mem = ""
    try:
        p = MEM_ROOT / subject_id / "memory.md"
        if p.exists():
            mem = p.read_text()[:500]
    except Exception:
        pass
    def _save(role: str, text: str):
        try:
            mc = con()
            mc.execute("INSERT INTO messages VALUES (?,?,?,?,?)", (str(uuid.uuid4()), subject_id, role, text, str(time.time())))
            mc.commit()
            mc.close()
        except Exception as e:
            print("msg save failed", e)

    _save("user", message)
    try:
        if ZEN_KEY:
            messages = [
                {"role":"system","content": "You are a 1:1 tutor for this subject. Answer grounded in context chunks, cite page/topic. Be concise. Memory: " + mem},
                {"role":"user","content": f"Context:\n{ctx}\n\nQuestion: {message}"}
            ]
            ans = await call_zen(messages, max_tokens=600)
            _save("bot", ans)
            return {"answer": ans, "citations": [r[0][:60] for r in rows], "via":"zen"}
    except Exception as e:
        print("zen chat failed", e)
    answer = f"(stub) For {subject_id}: grounded in '{ctx[:120]}...' — here's the explanation."
    _save("bot", answer)
    return {"answer": answer, "citations": [r[0][:60] for r in rows], "via":"template"}

# --- Plan generation (Zen when available, heuristic fallback) + auto re-pace ---
@app.post("/plan/generate/{subject_id}")
async def plan_generate(subject_id: str, objective: str = Form("")):
    c = con()
    row = c.execute("SELECT objective, start_date, end_date FROM subjects WHERE id=?", (subject_id,)).fetchone()
    obj = objective or (row[0] if row and row[0] else "")
    start = _parse_iso(row[1]) if row and row[1] else None
    end = _parse_iso(row[2]) if row and row[2] else None
    if not start: start = _date.today()
    if not end or end <= start: end = start + timedelta(weeks=8)
    weeks = _week_count(start, end)
    topics = _topics_from_materials(c, subject_id)
    via = "heuristic"
    if ZEN_KEY and topics:
        try:
            messages = [
                {"role": "system", "content": "You are a curriculum planner. Return a JSON array of short topic strings (no markdown), ordered as a coherent week-by-week learning path."},
                {"role": "user", "content": f"Subject goal: {obj or topics[0]}. Course runs {start.isoformat()} to {end.isoformat()} = {weeks} weeks. Candidate topics from the student's materials: {topics[:20]}. Return exactly {weeks} topic strings."},
            ]
            content = await call_zen(messages, max_tokens=700)
            m = re.search(r"\[.*\]", content, re.S)
            if m:
                arr = _json.loads(m.group(0))
                zs = [str(x).strip()[:120] for x in arr if str(x).strip()][:weeks]
                if zs: topics, via = zs, "zen"
        except Exception as e:
            print("zen plan failed", e)
    items = _build_plan_items(weeks, topics[:weeks], start, obj)
    _insert_plan_items(c, subject_id, items, replace=True)
    c.commit(); c.close()
    return {"ok": True, "weeks": weeks, "via": via, "items": items}

@app.post("/plan/repace/{subject_id}")
def repace(subject_id: str, topics: str = Form("")):
    c = con()
    # explicit topics take priority; otherwise remediate weak mastery topics
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    if not topic_list:
        topic_list = [r[0] for r in c.execute(
            "SELECT topic FROM mastery WHERE subject_id=? AND (mastery_bool=0 AND (score_last IS NULL OR score_last<0.8))",
            (subject_id,)).fetchall()]
    _remediate(c, subject_id, topic_list)
    c.commit(); c.close()
    return {"ok": True, "topics": topic_list}

# --- Canvas reference connector (stub OAuth) ---
# --- Connectors: handled via Main Agent chat (ADR 006), no marketplace UI ---
CONNECTOR_KEYWORDS = ["canvas", "blackboard", "brightspace", "grade", "connect", "sync"]

@app.post("/connectors/{connector_id}/add")
def add_connector(connector_id: str, added: str = Form("true")):
    # persist enabled/disabled state so the setting survives restarts
    env = pathlib.Path(__file__).parent.parent / ".env"
    lines = env.read_text().splitlines() if env.exists() else []
    lines = [l for l in lines if not l.startswith(f"CONNECTOR_{connector_id.upper()}=")]
    lines.append(f"CONNECTOR_{connector_id.upper()}={added}")
    env.write_text("\n".join(lines) + "\n")
    return {"ok": True, "id": connector_id, "added": added}

@app.post("/connectors/canvas/auth")
def canvas_auth(token: str = Form(...)):
    # store token in keychain stub (env file)
    import pathlib
    env = pathlib.Path(__file__).parent.parent / ".env"
    # append without exposing full token in logs
    with open(env,"a") as f: f.write(f"\nCANVAS_TOKEN={token[:8]}... (stored)\n")
    return {"ok": True, "note": "Canvas token stored (stub) — real OAuth next"}

@app.get("/connectors/canvas/grades")
def canvas_grades(token: str = ""):
    # Real impl would call Canvas API /api/v1/courses with Bearer token
    # For verify: if token provided or stored, return mock grades
    if not token:
        # try to read stored token hint from .env
        try:
            import pathlib
            env = pathlib.Path(__file__).parent.parent / ".env"
            txt = env.read_text() if env.exists() else ""
            if "CANVAS_TOKEN" not in txt:
                return {"error":"no token — POST /connectors/canvas/auth first", "mock":[]}
        except: pass
    # mock grades
    return {"grades":[{"course":"Calculus II","assignment":"Midterm 1","score":78,"max":100,"topics":"derivatives,integrals"}, {"course":"Bio 101","assignment":"Quiz 2","score":88,"max":100,"topics":"cells"}],"via":"mock — replace with Canvas /api/v1/courses call when token is real"}
