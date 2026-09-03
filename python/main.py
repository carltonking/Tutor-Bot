from fastapi import FastAPI, UploadFile, File, Form
import sqlite3, pathlib, uuid, time, shutil, os
from rag import extract_text, chunk_text

app = FastAPI()
ROOT = pathlib.Path(__file__).parent
DB = ROOT / "study.db"
STORE = ROOT / "store"
STORE.mkdir(exist_ok=True)

def con():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY, name TEXT, color TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, subject_id TEXT, filename TEXT, type TEXT, pages INTEGER, chunks INTEGER, path TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, source_id TEXT, subject_id TEXT, idx INTEGER, text TEXT)")
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
    for idx, ch in enumerate(chunks):
        cid = str(uuid.uuid4())
        c.execute("INSERT INTO chunks VALUES (?,?,?,?,?)", (cid, sid, subject_id, idx, ch))
    c.commit()
    c.close()
    return {"id": sid, "filename": file.filename, "pages": pages, "chunks": len(chunks)}

@app.get("/search/{subject_id}")
def search(subject_id: str, q: str, k: int = 5):
    # naive keyword search until embeddings land (sqlite-vec next)
    c = con()
    rows = c.execute("SELECT text FROM chunks WHERE subject_id=? AND text LIKE ? LIMIT ?", (subject_id, f"%{q}%", k)).fetchall()
    c.close()
    return [{"text": r[0]} for r in rows]

# --- Minimal assessment generator (template, no LLM yet) ---
import random

@app.post("/assess/generate")
def gen_assess(subject_id: str = Form(...), topic: str = Form(None), count: int = Form(5)):
    c = con()
    rows = c.execute("SELECT text FROM chunks WHERE subject_id=? LIMIT 20", (subject_id,)).fetchall()
    c.close()
    if not rows:
        return {"questions": [], "note": "no chunks — upload sources first"}
    qs = []
    for i in range(count):
        chunk = rows[i % len(rows)][0][:180]
        stem = f"Based on: \"{chunk}...\" — what is the key concept?"
        qs.append({
            "id": str(uuid.uuid4()),
            "type": "mcq" if i%2==0 else "short_answer",
            "prompt": stem,
            "topic": topic or "general",
            "citation": chunk[:60],
            "rubric": "Answer should reference the cited chunk accurately."
        })
    return {"questions": qs}

@app.post("/assess/grade")
def grade(prompt: str = Form(...), answer: str = Form(...), rubric: str = Form(...)):
    # stub grader: keyword overlap
    score = 70 if len(answer.split()) > 5 else 40
    if any(w in answer.lower() for w in prompt.lower().split()[:3]): score += 10
    return {"score": min(score,100), "reasoning": f"Stub grader: checked against rubric '{rubric[:40]}...'", "rubric": rubric}

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
