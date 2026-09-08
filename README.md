# TutorBot — Rakazo Skill + MCP Sidecar

Turn any [Rakazo](https://github.com/elie222/rakazo) bot into a persistent per-subject tutor. This repo is a **Rakazo-native specialization** — no fork, no standalone desktop — a `SKILL.md` (the operating manual) **plus** a local sidecar (`python/`) that owns state. The skill alone is a demo; skill + sidecar is the full loop.

## What it does

- **Ingest per subject** — upload syllabus / textbook / teacher_notes / practice_problems → 512/64 chunk, nomic-embed via Ollama (falls back to deterministic hash embeddings), stored as JSON vectors in SQLite; retrieval is cosine + keyword boost with citations
- **Assessments** — MCQ, short-answer, quiz, practice exam; banked with topic tag + rubric + citation; practice exams bias toward weak + upcoming plan topics; style-conditioned on `practice_problems` chunks when present
- **Grading** — LLM-as-judge (OpenCode Zen) with rubric + reasoning, template fallback when no key; dispute is re-calling `/assess/grade` (no separate alt-model path yet)
- **Grades → mastery → re-pace** — mastery = ≥80% on last 2 for that topic + no recent failure; sub-80% auto-injects `Remediate: <topic>` weeks; applies to both manual grades and quiz attempts
- **Semester plan** — weekly boxes, date-ranged from onboarding `start_date`/`end_date`; topics derived from ingested chunks + plan/grade history, optionally re-ordered by LLM
- **Chat** — RAG-grounded with citation, subject `memory.md` injected as context
- **Memory** — hierarchical `global.md` vs `subjects/{id}/memory.md` + per-day `sessions/YYYY-MM-DD.md`; routing is currently keyword heuristic (LLM router planned)
- **Grade sync** — Canvas token stub (`POST /connectors/canvas/auth` + `GET /connectors/canvas/grades` returns mock); real Canvas API + keychain vault are next

## Layout

```
tutorbot-skill/SKILL.md   # Rakazo skill — paste into Settings → Skills → New (skill alone = prompts only)
python/                   # MCP sidecar — the state owner (must be running)
  main.py                 # FastAPI + /openapi.json, /mcp, /mcp/tools/{name}, /ping
  rag.py                  # 512/64 chunk + nomic-embed (Ollama) / hash fallback + cosine
  study.db                # SQLite: subjects, sources, chunks (embedding JSON), assessments, grades, mastery, plan
  store/{subject_id}/     # uploaded PDFs / text files on disk
  memory/                 # global.md + subjects/{id}/memory.md + sessions/
```

> **Important:** Without the sidecar running, the skill has no persistence — mastery, RAG, and grades will be hallucinated.

## Quick start

```bash
# 1. Rakazo must be running (~/01 - PROJECTS/rakazo)
cd ~/01\ -\ PROJECTS/rakazo && docker compose -f docker-compose.images.yml --env-file .env up -d
open http://127.0.0.1:5173   # create account

# 2. Start sidecar (required — owns DB/RAG/grading)
cd ~/01\ -\ PROJECTS/TutorBot/python
python3 -m uvicorn main:app --port 1421 --host 127.0.0.1  # → http://127.0.0.1:1421/ping

# 3. In Rakazo web: Settings → Skills → New → paste contents of tutorbot-skill/SKILL.md
#    Then Integrations → Add MCP/OpenAPI → http://host.docker.internal:1421/openapi.json
#    (inside Docker, host.docker.internal resolves to your Mac)

# 4. Create one bot per subject, open chat, type:  /TutorBot
```

## Limitations (honest)

- Vectors are JSON in SQLite, not `sqlite-vec` / pgvector — works but not indexed.
- Canvas sync is a mock until a real `Authorization: Bearer <token>` → `GET /api/v1/courses` is wired and tokens move to OS keychain / Rakazo encrypted store.
- Dispute re-grade reuses the same model; alt-model path is TODO.
- Memory routing is keyword heuristic, not LLM.

## Legacy

Previous Tauri desktop + 21 ADRs are archived in git history (`git log --before="2026-09-08"`). This repo now tracks only the Skill + MCP.

License: MIT
