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
