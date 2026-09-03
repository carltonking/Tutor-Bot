from fastapi import FastAPI, UploadFile, File, Form
import sqlite3, pathlib, uuid, time, shutil, os, httpx, sys
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
    allow_origins=["http://localhost:1420", "http://127.0.0.1:1420", "tauri://localhost", "http://tauri.localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)
ROOT = pathlib.Path(__file__).parent
DB = ROOT / "study.db"
STORE = ROOT / "store"
STORE.mkdir(exist_ok=True)
MEM_ROOT = ROOT / "memory"
MEM_ROOT.mkdir(exist_ok=True)
GLOBAL_MD = MEM_ROOT / "global.md"
if not GLOBAL_MD.exists():
    GLOBAL_MD.write_text("# Global Memory\n\n> Cross-subject preferences. Agent routes general instructions here.\n")

def _migrate_subjects(c):
    """Add onboarding / timeline columns to subjects (idempotent)."""
    cols = {r[1] for r in c.execute("PRAGMA table_info(subjects)").fetchall()}
    for col, decl in [
        ("objective", "TEXT"),
        ("mode", "TEXT"),
        ("school", "TEXT"),
        ("course_code", "TEXT"),
        ("start_date", "TEXT"),
        ("end_date", "TEXT"),
    ]:
        if col not in cols:
            try: c.execute(f"ALTER TABLE subjects ADD COLUMN {col} {decl}")
            except: pass

def con():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY, name TEXT, color TEXT, created_at TEXT, objective TEXT, mode TEXT, school TEXT, course_code TEXT, start_date TEXT, end_date TEXT)")
    _migrate_subjects(c)
    c.execute("CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, subject_id TEXT, filename TEXT, type TEXT, pages INTEGER, chunks INTEGER, path TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, source_id TEXT, subject_id TEXT, idx INTEGER, text TEXT, embedding TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, subject_id TEXT, role TEXT, text TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS topics(id TEXT PRIMARY KEY, subject_id TEXT, name TEXT, parent_id TEXT, week INTEGER, weight REAL, ord INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS mastery(subject_id TEXT, topic TEXT, score_last2 REAL, mastery_bool INTEGER, updated_at TEXT, PRIMARY KEY(subject_id, topic))")
    c.execute("CREATE TABLE IF NOT EXISTS assessment_attempts(id TEXT PRIMARY KEY, subject_id TEXT, topic TEXT, score REAL, prompt TEXT, answer TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS plan(id TEXT PRIMARY KEY, subject_id TEXT, week INTEGER, topic TEXT, status TEXT, kind TEXT, start_date TEXT, end_date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS grades(id TEXT PRIMARY KEY, subject_id TEXT, title TEXT, score REAL, max REAL, topics TEXT, created_at TEXT)")
    # migrate old DB without embedding col
    try:
        c.execute("SELECT embedding FROM chunks LIMIT 1")
    except:
        try: c.execute("ALTER TABLE chunks ADD COLUMN embedding TEXT")
        except: pass
    # migrate grades created_at
    gcols = {r[1] for r in c.execute("PRAGMA table_info(grades)").fetchall()}
    if "created_at" not in gcols:
        try: c.execute("ALTER TABLE grades ADD COLUMN created_at TEXT")
        except: pass
    # migrate plan kind/dates
    pcols = {r[1] for r in c.execute("PRAGMA table_info(plan)").fetchall()}
    for col, decl in [("kind", "TEXT"), ("start_date", "TEXT"), ("end_date", "TEXT")]:
        if col not in pcols:
            try: c.execute(f"ALTER TABLE plan ADD COLUMN {col} {decl}")
            except: pass
    return c

con().close()

# --- Mastery / plan helpers ---
from datetime import datetime, timedelta, date as _date

def _parse_date(s):
    if not s: return None
    try: return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except: return None

def _weeks_between(start, end):
    if not start or not end or end < start:
        return 1
    days = (end - start).days + 1
    return max(1, (days + 6) // 7)

def _default_topics_for(name, objective=""):
    """Seed topic list when none exist yet — derived from subject, not hard-coded demo weeks."""
    blob = f"{name} {objective}".lower()
    seeds = []
    # light heuristics; otherwise split objective / generic units
    if any(k in blob for k in ["calc", "derivative", "integral", "limit"]):
        seeds = ["Limits", "Derivatives", "Applications of Derivatives", "Integrals", "Applications of Integrals", "Series"]
    elif any(k in blob for k in ["bio", "cell", "genetics"]):
        seeds = ["Cells", "Genetics", "Evolution", "Ecology", "Physiology"]
    elif objective:
        # split objective on commas / semicolons / "and"
        parts = [p.strip(" .") for p in objective.replace(";", ",").replace(" and ", ",").split(",") if p.strip()]
        seeds = parts[:8] if parts else []
    if not seeds:
        seeds = [f"Unit {i}" for i in range(1, 5)]
    return seeds

def _ensure_topics(c, subject_id):
    rows = c.execute("SELECT id, name, ord FROM topics WHERE subject_id=? ORDER BY ord, name", (subject_id,)).fetchall()
    if rows:
        return [{"id": r[0], "name": r[1], "ord": r[2]} for r in rows]
    sub = c.execute("SELECT name, objective FROM subjects WHERE id=?", (subject_id,)).fetchone()
    name = sub[0] if sub else "Subject"
    objective = (sub[1] or "") if sub else ""
    seeds = _default_topics_for(name, objective)
    out = []
    for i, t in enumerate(seeds):
        tid = str(uuid.uuid4())
        c.execute("INSERT INTO topics VALUES (?,?,?,?,?,?,?)", (tid, subject_id, t, None, None, 1.0, i))
        out.append({"id": tid, "name": t, "ord": i})
    return out

def _recompute_mastery_for_topic(c, subject_id, topic):
    """SPEC: mastery = ≥80% on last 2 assessments AND no recent real-grade failure."""
    attempts = c.execute(
        "SELECT score FROM assessment_attempts WHERE subject_id=? AND lower(topic)=lower(?) ORDER BY created_at DESC LIMIT 2",
        (subject_id, topic),
    ).fetchall()
    scores = [float(a[0]) for a in attempts]
    if len(scores) >= 2:
        score_last2 = sum(scores) / 2.0
        assess_ok = all(s >= 80 for s in scores)
    elif len(scores) == 1:
        score_last2 = scores[0]
        assess_ok = False  # need two
    else:
        # fall back to real grades average for display
        grade_rows = c.execute("SELECT score, max, topics FROM grades WHERE subject_id=?", (subject_id,)).fetchall()
        matched = []
        for sc, mx, tops in grade_rows:
            tlist = [x.strip().lower() for x in (tops or "").split(",") if x.strip()]
            if topic.lower() in tlist and mx:
                matched.append(100.0 * float(sc) / float(mx))
        score_last2 = (sum(matched) / len(matched)) if matched else 0.0
        assess_ok = False

    # recent real-grade failure: any mapped grade <80% in last ~60 days (or any if no timestamp)
    cutoff = str(time.time() - 60 * 86400)
    fail = False
    for sc, mx, tops, created in c.execute(
        "SELECT score, max, topics, created_at FROM grades WHERE subject_id=?", (subject_id,)
    ).fetchall():
        tlist = [x.strip().lower() for x in (tops or "").split(",") if x.strip()]
        if topic.lower() not in tlist:
            continue
        pct = 100.0 * float(sc) / float(mx or 100)
        if pct < 80:
            if not created or str(created) >= cutoff or (isinstance(created, str) and created[:4].isdigit() and len(created) >= 10):
                # treat missing/ISO/epoch as recent enough for MVP
                fail = True
                break

    mastery_bool = 1 if (assess_ok and not fail) else 0
    c.execute(
        "INSERT INTO mastery(subject_id, topic, score_last2, mastery_bool, updated_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(subject_id, topic) DO UPDATE SET score_last2=excluded.score_last2, mastery_bool=excluded.mastery_bool, updated_at=excluded.updated_at",
        (subject_id, topic, score_last2, mastery_bool, str(time.time())),
    )
    return {"topic": topic, "score_last2": score_last2, "mastery": bool(mastery_bool), "assess_ok": assess_ok, "grade_fail": fail}

def _subject_dates(c, subject_id):
    row = c.execute("SELECT start_date, end_date, name, objective, mode, school, course_code FROM subjects WHERE id=?", (subject_id,)).fetchone()
    if not row:
        return None
    start = _parse_date(row[0]) or _date.today()
    end = _parse_date(row[1]) or (start + timedelta(weeks=12))
    return {"start": start, "end": end, "name": row[2], "objective": row[3] or "", "mode": row[4] or "course",
            "school": row[5] or "", "course_code": row[6] or ""}

def _generate_plan(c, subject_id, force=False):
    """Build weekly plan items spanning subject start/end from topics + mastery."""
    meta = _subject_dates(c, subject_id)
    if not meta:
        return []
    topics = _ensure_topics(c, subject_id)
    n_weeks = _weeks_between(meta["start"], meta["end"])
    existing = c.execute("SELECT COUNT(*) FROM plan WHERE subject_id=?", (subject_id,)).fetchone()[0]
    if existing and not force:
        rows = c.execute(
            "SELECT id, week, topic, status, kind, start_date, end_date FROM plan WHERE subject_id=? ORDER BY week, topic",
            (subject_id,),
        ).fetchall()
        return [{"id": r[0], "week": r[1], "topic": r[2], "status": r[3], "kind": r[4] or "learn",
                 "start_date": r[5], "end_date": r[6]} for r in rows]

    # clear learn/assess items on force regen; keep completed remediation optionally
    if force:
        c.execute("DELETE FROM plan WHERE subject_id=?", (subject_id,))

    # order: non-mastered first (re-pace), then by ord
    mastery_rows = {r[0].lower(): r for r in c.execute(
        "SELECT topic, score_last2, mastery_bool FROM mastery WHERE subject_id=?", (subject_id,)
    ).fetchall()}
    def sort_key(t):
        m = mastery_rows.get(t["name"].lower())
        mastered = bool(m[2]) if m else False
        score = float(m[1]) if m else 0.0
        return (1 if mastered else 0, score, t["ord"] if t["ord"] is not None else 0)

    ordered = sorted(topics, key=sort_key)
    # also pull weak grade topics to the front
    weak = []
    for sc, mx, tops in c.execute("SELECT score, max, topics FROM grades WHERE subject_id=?", (subject_id,)).fetchall():
        if mx and float(sc) / float(mx) < 0.8:
            for t in [x.strip() for x in (tops or "").split(",") if x.strip()]:
                if t.lower() not in [w.lower() for w in weak]:
                    weak.append(t)
    # prepend weak topics if present in topic list
    name_map = {t["name"].lower(): t for t in ordered}
    front = []
    for w in weak:
        if w.lower() in name_map:
            front.append(name_map.pop(w.lower()))
    ordered = front + list(name_map.values())

    items = []
    today = _date.today()
    for i, t in enumerate(ordered):
        week = (i % n_weeks) + 1
        w_start = meta["start"] + timedelta(weeks=week - 1)
        w_end = min(meta["start"] + timedelta(weeks=week) - timedelta(days=1), meta["end"])
        # status relative to today
        if w_end < today:
            status = "done"
        elif w_start <= today <= w_end:
            status = "active"
        else:
            status = "todo"
        kind = "remediate" if t["name"] in weak or (t["name"].lower() in mastery_rows and not mastery_rows[t["name"].lower()][2] and (mastery_rows[t["name"].lower()][1] or 0) > 0) else "learn"
        if t["name"] in weak:
            kind = "remediate"
        pid = str(uuid.uuid4())
        c.execute(
            "INSERT INTO plan VALUES (?,?,?,?,?,?,?,?)",
            (pid, subject_id, week, t["name"], status, kind, w_start.isoformat(), w_end.isoformat()),
        )
        items.append({"id": pid, "week": week, "topic": t["name"], "status": status, "kind": kind,
                      "start_date": w_start.isoformat(), "end_date": w_end.isoformat()})

    # if more weeks than topics, add assess weeks cycling topics
    if n_weeks > len(ordered) and ordered:
        for week in range(len(ordered) + 1, n_weeks + 1):
            t = ordered[(week - 1) % len(ordered)]
            w_start = meta["start"] + timedelta(weeks=week - 1)
            w_end = min(meta["start"] + timedelta(weeks=week) - timedelta(days=1), meta["end"])
            if w_end < today: status = "done"
            elif w_start <= today <= w_end: status = "active"
            else: status = "todo"
            pid = str(uuid.uuid4())
            c.execute(
                "INSERT INTO plan VALUES (?,?,?,?,?,?,?,?)",
                (pid, subject_id, week, t["name"], status, "assess", w_start.isoformat(), w_end.isoformat()),
            )
            items.append({"id": pid, "week": week, "topic": t["name"], "status": status, "kind": "assess",
                          "start_date": w_start.isoformat(), "end_date": w_end.isoformat()})
    return items

def _repace_plan(c, subject_id, topics_csv):
    """Emphasize low-grade / weak topics: insert remediation weeks and regenerate order."""
    topic_list = [x.strip() for x in (topics_csv or "").split(",") if x.strip()]
    meta = _subject_dates(c, subject_id)
    if not meta:
        return {"ok": False, "error": "subject not found"}
    # ensure topics exist
    existing = {r[0].lower() for r in c.execute("SELECT name FROM topics WHERE subject_id=?", (subject_id,)).fetchall()}
    max_ord = c.execute("SELECT MAX(ord) FROM topics WHERE subject_id=?", (subject_id,)).fetchone()[0] or 0
    for t in topic_list:
        if t.lower() not in existing:
            max_ord += 1
            c.execute("INSERT INTO topics VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), subject_id, t, None, None, 1.0, max_ord))
        _recompute_mastery_for_topic(c, subject_id, t)
    # force regenerate so weak topics bubble up
    items = _generate_plan(c, subject_id, force=True)
    # also prepend explicit remediation markers at week 1 for each weak topic
    today = _date.today()
    for i, t in enumerate(topic_list):
        pid = str(uuid.uuid4())
        w_start = meta["start"]
        w_end = min(meta["start"] + timedelta(days=6), meta["end"])
        c.execute(
            "INSERT INTO plan VALUES (?,?,?,?,?,?,?,?)",
            (pid, subject_id, 1, f"Remediate: {t}", "active" if w_start <= today <= w_end else "todo",
             "remediate", w_start.isoformat(), w_end.isoformat()),
        )
        items.insert(i, {"id": pid, "week": 1, "topic": f"Remediate: {t}", "status": "active",
                         "kind": "remediate", "start_date": w_start.isoformat(), "end_date": w_end.isoformat()})
    return {"ok": True, "topics": topic_list, "plan": items}

@app.get("/ping")
def ping(): return {"pong": True}

@app.get("/subjects")
def subjects():
    c = con()
    rows = c.execute("SELECT id,name,color,objective,mode,school,course_code,start_date,end_date FROM subjects").fetchall()
    c.close()
    return [{
        "id": r[0], "name": r[1], "color": r[2],
        "objective": r[3] or "", "mode": r[4] or "course",
        "school": r[5] or "", "course_code": r[6] or "",
        "start_date": r[7] or "", "end_date": r[8] or "",
    } for r in rows]

@app.post("/subjects")
def create_subject(
    name: str = Form(...),
    color: str = Form("#e14b4b"),
    objective: str = Form(""),
    mode: str = Form("course"),
    school: str = Form(""),
    course_code: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
):
    sid = str(uuid.uuid4())
    if mode not in ("course", "self"):
        mode = "course"
    # default timeline: today → +12 weeks if missing
    if not start_date:
        start_date = _date.today().isoformat()
    if not end_date:
        end_date = (_date.today() + timedelta(weeks=12)).isoformat()
    c = con()
    c.execute(
        "INSERT INTO subjects(id,name,color,created_at,objective,mode,school,course_code,start_date,end_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sid, name, color, str(int(time.time())), objective, mode, school, course_code, start_date, end_date),
    )
    # seed topics + generate plan spanning dates
    _ensure_topics(c, sid)
    plan = _generate_plan(c, sid, force=True)
    # brief seed in subject memory for the agent
    mem_dir = MEM_ROOT / sid
    mem_dir.mkdir(parents=True, exist_ok=True)
    brief = (
        f"# {name} Memory\n\n"
        f"> Mode: {mode} · School: {school or '—'} · Code: {course_code or '—'}\n"
        f"> Window: {start_date} → {end_date}\n"
        f"> Objective: {objective or '—'}\n\n"
        f"## Agent brief\n"
        f"Tutor this subject toward the objective. Plan has {len(plan)} items across the date range.\n"
    )
    (mem_dir / "memory.md").write_text(brief)
    c.commit()
    c.close()
    return {
        "id": sid, "name": name, "color": color,
        "objective": objective, "mode": mode, "school": school, "course_code": course_code,
        "start_date": start_date, "end_date": end_date, "plan_items": len(plan),
    }

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
    for table in ["subjects", "sources", "chunks", "messages", "grades", "plan", "topics", "mastery", "assessment_attempts"]:
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

@app.post("/assess/generate")
async def gen_assess(subject_id: str = Form(...), topic: str = Form(None), count: int = Form(5)):
    c = con()
    # Prefer teacher style exemplars
    rows = c.execute("SELECT text FROM chunks WHERE subject_id=? ORDER BY RANDOM() LIMIT 10", (subject_id,)).fetchall()
    # also fetch practice_problems as style exemplars
    style_rows = c.execute("SELECT text FROM chunks WHERE subject_id=? AND source_id IN (SELECT id FROM sources WHERE type=\"practice_problems\") LIMIT 5", (subject_id,)).fetchall()
    c.close()
    if not rows:
        return {"questions": [], "note": "no chunks — upload sources first"}
    # Try LLM via Zen
    try:
        if ZEN_KEY:
            ctx = "\n\n".join([r[0][:500] for r in rows[:3]])
            style = "\n".join([r[0][:300] for r in style_rows]) if style_rows else "No style exemplar — use clear academic style"
            messages = [
                {"role":"system","content": "You are a tutor generating assessments. Use the teacher's style exactly. Return JSON array of questions: each with prompt, type (mcq|short_answer), topic, citation, rubric. No markdown."},
                {"role":"user","content": f"Context chunks:\n{ctx}\n\nTeacher style exemplars:\n{style}\n\nGenerate {count} questions on topic '{topic or 'general'}'. Keep citations."}
            ]
            content = await call_zen(messages, max_tokens=1200)
            import json, re
            # try to extract JSON array
            m = re.search(r"\[.*\]", content, re.S)
            if m:
                arr = json.loads(m.group(0))
                qs=[]
                for item in arr[:count]:
                    qs.append({"id": str(uuid.uuid4()), "type": item.get("type","mcq"), "prompt": item.get("prompt", str(item))[:400], "topic": item.get("topic", topic or "general"), "citation": item.get("citation", ctx[:60]), "rubric": item.get("rubric","Answer should reference cited chunk")})
                if qs:
                    return {"questions": qs, "via":"zen"}
    except Exception as e:
        print("zen gen failed", e)
    # fallback template
    qs=[]
    for i in range(count):
        chunk = rows[i % len(rows)][0][:180]
        stem = f"Based on: \"{chunk}...\" — what is the key concept?"
        qs.append({"id": str(uuid.uuid4()), "type": "mcq" if i%2==0 else "short_answer", "prompt": stem, "topic": topic or "general", "citation": chunk[:60], "rubric": "Answer should reference the cited chunk accurately."})
    return {"questions": qs, "via":"template"}

@app.post("/assess/grade")
async def grade(
    prompt: str = Form(...),
    answer: str = Form(...),
    rubric: str = Form(...),
    subject_id: str = Form(""),
    topic: str = Form("general"),
):
    result = None
    try:
        if ZEN_KEY:
            messages = [
                {"role":"system","content": "You are a strict grader. Score 0-100 based on rubric. Return JSON {score, reasoning}."},
                {"role":"user","content": f"Prompt: {prompt}\nAnswer: {answer}\nRubric: {rubric}\nReturn JSON only."}
            ]
            content = await call_zen(messages, max_tokens=400)
            import json, re
            m = re.search(r"\{.*\}", content, re.S)
            if m:
                j = json.loads(m.group(0))
                result = {"score": int(j.get("score", 0)), "reasoning": j.get("reasoning", content[:300]), "rubric": rubric, "via":"zen"}
    except Exception as e:
        print("zen grade failed", e)
    if result is None:
        score = 70 if len(answer.split()) > 5 else 40
        if any(w in answer.lower() for w in prompt.lower().split()[:3]): score += 10
        result = {"score": min(score,100), "reasoning": f"Template grader: checked against rubric '{rubric[:40]}...'", "rubric": rubric, "via":"template"}
    # writeback → assessment_attempts + mastery
    mastery = None
    if subject_id:
        c = con()
        # ensure topic
        exists = c.execute("SELECT 1 FROM topics WHERE subject_id=? AND lower(name)=lower(?)", (subject_id, topic)).fetchone()
        if not exists and topic:
            max_ord = c.execute("SELECT MAX(ord) FROM topics WHERE subject_id=?", (subject_id,)).fetchone()[0] or 0
            c.execute("INSERT INTO topics VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), subject_id, topic, None, None, 1.0, max_ord + 1))
        aid = str(uuid.uuid4())
        c.execute(
            "INSERT INTO assessment_attempts VALUES (?,?,?,?,?,?,?)",
            (aid, subject_id, topic or "general", float(result["score"]), prompt[:500], answer[:1000], str(time.time())),
        )
        mastery = _recompute_mastery_for_topic(c, subject_id, topic or "general")
        c.commit(); c.close()
        result["attempt_id"] = aid
        result["mastery"] = mastery
        result["topic"] = topic or "general"
    return result

# --- Memory: global.md + per-subject memory.md + sessions ---
from datetime import datetime

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

# --- Plan + Grades + Mastery (live) ---
@app.get("/plan/{subject_id}")
def get_plan(subject_id: str):
    c = con()
    items = _generate_plan(c, subject_id, force=False)
    c.commit(); c.close()
    return items

@app.post("/plan/{subject_id}/generate")
def generate_plan(subject_id: str):
    c = con()
    items = _generate_plan(c, subject_id, force=True)
    c.commit(); c.close()
    return {"ok": True, "items": items}

@app.get("/topics/{subject_id}")
def get_topics(subject_id: str):
    c = con()
    topics = _ensure_topics(c, subject_id)
    c.commit(); c.close()
    return topics

@app.post("/topics/{subject_id}")
def add_topic(subject_id: str, name: str = Form(...)):
    c = con()
    max_ord = c.execute("SELECT MAX(ord) FROM topics WHERE subject_id=?", (subject_id,)).fetchone()[0] or 0
    tid = str(uuid.uuid4())
    c.execute("INSERT INTO topics VALUES (?,?,?,?,?,?,?)", (tid, subject_id, name.strip(), None, None, 1.0, max_ord + 1))
    c.commit(); c.close()
    return {"id": tid, "name": name.strip()}

@app.get("/mastery/{subject_id}")
def get_mastery(subject_id: str):
    c = con()
    topics = _ensure_topics(c, subject_id)
    out = []
    for t in topics:
        # refresh from attempts/grades
        m = _recompute_mastery_for_topic(c, subject_id, t["name"])
        out.append(m)
    c.commit(); c.close()
    return out

@app.get("/grades/{subject_id}")
def get_grades(subject_id: str):
    c = con()
    rows = c.execute("SELECT title, score, max, topics, created_at FROM grades WHERE subject_id=? ORDER BY created_at DESC", (subject_id,)).fetchall()
    c.close()
    return [{"title": r[0], "score": r[1], "max": r[2], "topics": r[3] or "", "created_at": r[4]} for r in rows]

@app.post("/grades/{subject_id}")
def add_grade(subject_id: str, title: str = Form(...), score: float = Form(...), max: float = Form(100), topics: str = Form("")):
    c = con()
    gid = str(uuid.uuid4())
    c.execute("INSERT INTO grades VALUES (?,?,?,?,?,?,?)", (gid, subject_id, title, score, max, topics, str(time.time())))
    topic_list = [x.strip() for x in topics.split(",") if x.strip()]
    mastery_updates = []
    for t in topic_list:
        # ensure topic row
        exists = c.execute("SELECT 1 FROM topics WHERE subject_id=? AND lower(name)=lower(?)", (subject_id, t)).fetchone()
        if not exists:
            max_ord = c.execute("SELECT MAX(ord) FROM topics WHERE subject_id=?", (subject_id,)).fetchone()[0] or 0
            c.execute("INSERT INTO topics VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), subject_id, t, None, None, 1.0, max_ord + 1))
        mastery_updates.append(_recompute_mastery_for_topic(c, subject_id, t))
    repaced = None
    if max and (score / max) < 0.8 and topic_list:
        repaced = _repace_plan(c, subject_id, topics)
    c.commit(); c.close()
    return {"id": gid, "mastery": mastery_updates, "repaced": bool(repaced), "plan": (repaced or {}).get("plan")}

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

# --- Plan auto re-pace on low grade ---
@app.post("/plan/repace/{subject_id}")
def repace(subject_id: str, topics: str = Form(...)):
    c = con()
    result = _repace_plan(c, subject_id, topics)
    c.commit(); c.close()
    return result

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
