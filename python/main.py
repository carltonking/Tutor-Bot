from fastapi import FastAPI, UploadFile, File, Form
import sqlite3, pathlib, uuid, time, shutil, os, httpx
from rag import extract_text, chunk_text

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
ROOT = pathlib.Path(__file__).parent
DB = ROOT / "study.db"
STORE = ROOT / "store"
STORE.mkdir(exist_ok=True)

def con():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY, name TEXT, color TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, subject_id TEXT, filename TEXT, type TEXT, pages INTEGER, chunks INTEGER, path TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, source_id TEXT, subject_id TEXT, idx INTEGER, text TEXT, embedding TEXT)")
    # migrate old DB without embedding col
    try:
        c.execute("SELECT embedding FROM chunks LIMIT 1")
    except:
        try: c.execute("ALTER TABLE chunks ADD COLUMN embedding TEXT")
        except: pass
    return c

con().close()

@app.get("/ping")
def ping(): return {"pong": True}

@app.get("/subjects")
def subjects():
    c = con()
    rows = c.execute("SELECT id,name,color FROM subjects").fetchall()
    c.close()
    return [{"id":r[0],"name":r[1],"color":r[2]} for r in rows]

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
        emb = json.dumps(embed_text(ch))
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
        qemb = embed_text(q)
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
async def grade(prompt: str = Form(...), answer: str = Form(...), rubric: str = Form(...)):
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
                return {"score": int(j.get("score", 0)), "reasoning": j.get("reasoning", content[:300]), "rubric": rubric, "via":"zen"}
    except Exception as e:
        print("zen grade failed", e)
    score = 70 if len(answer.split()) > 5 else 40
    if any(w in answer.lower() for w in prompt.lower().split()[:3]): score += 10
    return {"score": min(score,100), "reasoning": f"Template grader: checked against rubric '{rubric[:40]}...'", "rubric": rubric, "via":"template"}

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

# --- Plan + Grades + Mastery (stub) ---
@app.get("/plan/{subject_id}")
def get_plan(subject_id: str):
    c = con()
    c.execute("CREATE TABLE IF NOT EXISTS plan(id TEXT PRIMARY KEY, subject_id TEXT, week INTEGER, topic TEXT, status TEXT)")
    rows = c.execute("SELECT week, topic, status FROM plan WHERE subject_id=? ORDER BY week", (subject_id,)).fetchall()
    c.close()
    if not rows:
        return [{"week":1,"topic":"Limits","status":"done"},{"week":2,"topic":"Derivatives","status":"active"},{"week":3,"topic":"Integrals","status":"todo"}]
    return [{"week":r[0],"topic":r[1],"status":r[2]} for r in rows]

@app.get("/grades/{subject_id}")
def get_grades(subject_id: str):
    c = con()
    c.execute("CREATE TABLE IF NOT EXISTS grades(id TEXT PRIMARY KEY, subject_id TEXT, title TEXT, score REAL, max REAL, topics TEXT)")
    rows = c.execute("SELECT title, score, max, topics FROM grades WHERE subject_id=?", (subject_id,)).fetchall()
    c.close()
    return [{"title":r[0],"score":r[1],"max":r[2],"topics":r[3]} for r in rows]

@app.post("/grades/{subject_id}")
def add_grade(subject_id: str, title: str = Form(...), score: float = Form(...), max: float = Form(100), topics: str = Form("")):
    c = con()
    c.execute("CREATE TABLE IF NOT EXISTS grades(id TEXT PRIMARY KEY, subject_id TEXT, title TEXT, score REAL, max REAL, topics TEXT)")
    gid = str(uuid.uuid4())
    c.execute("INSERT INTO grades VALUES (?,?,?,?,?,?)", (gid, subject_id, title, score, max, topics))
    # naive mastery update: if score/max <0.8 mark topic for remediation (stub)
    c.commit(); c.close()
    return {"id": gid, " mastery_hint": "if <80% will re-inject to plan (next iteration)"}

@app.post("/chat")
async def chat(subject_id: str = Form(...), message: str = Form(...)):
    # RAG + Zen chat with citations
    c = con()
    rows = c.execute("SELECT text FROM chunks WHERE subject_id=? ORDER BY RANDOM() LIMIT 3", (subject_id,)).fetchall()
    c.close()
    ctx = "\n\n".join([r[0][:600] for r in rows]) if rows else "No sources yet"
    # also load memory
    try:
        mem = (MEM_ROOT / subject_id / "memory.md").read_text()[:500] if (MEM_ROOT / subject_id / "memory.md").exists() else ""
    except: mem=""
    try:
        if ZEN_KEY:
            messages = [
                {"role":"system","content": "You are a 1:1 tutor for this subject. Answer grounded in context chunks, cite page/topic. Be concise. Memory: " + mem},
                {"role":"user","content": f"Context:\n{ctx}\n\nQuestion: {message}"}
            ]
            ans = await call_zen(messages, max_tokens=600)
            return {"answer": ans, "citations": [r[0][:60] for r in rows], "via":"zen"}
    except Exception as e:
        print("zen chat failed", e)
    return {"answer": f"(stub) For {subject_id}: grounded in '{ctx[:120]}...' — here's the explanation.", "citations": [r[0][:60] for r in rows], "via":"template"}

# --- Plan auto re-pace on low grade ---
@app.post("/plan/repace/{subject_id}")
def repace(subject_id: str, topics: str = Form(...)):
    c = con()
    c.execute("CREATE TABLE IF NOT EXISTS plan(id TEXT PRIMARY KEY, subject_id TEXT, week INTEGER, topic TEXT, status TEXT)")
    # insert remediation week
    import uuid, time
    next_week = c.execute("SELECT MAX(week) FROM plan WHERE subject_id=?", (subject_id,)).fetchone()[0] or 3
    for t in [x.strip() for x in topics.split(",") if x.strip()]:
        pid = str(uuid.uuid4())
        c.execute("INSERT INTO plan VALUES (?,?,?,?)", (pid, subject_id, next_week+1, f"Remediate: {t}", "todo"))
    c.commit(); c.close()
    return {"ok": True, "topics": topics}
