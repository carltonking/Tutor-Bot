from fastapi import FastAPI
import sqlite3, pathlib

app = FastAPI()
DB = pathlib.Path(__file__).parent / "study.db"

def init_db():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY, name TEXT, color TEXT, created_at TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, subject_id TEXT, filename TEXT, type TEXT)")
    con.close()

init_db()

@app.get("/ping")
def ping(): return {"pong": True}

@app.get("/subjects")
def subjects():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT id,name,color FROM subjects").fetchall()
    con.close()
    return [{"id":r[0],"name":r[1],"color":r[2]} for r in rows]
