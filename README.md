# TutorBot — Rakazo Skill + MCP Sidecar

Turn any [Rakazo](https://github.com/elie222/rakazo) bot into a persistent per-subject tutor. This repo is now a **Rakazo-native specialization** — no fork, no standalone desktop — just a Skill + a local MCP tool server that implements the full tutoring loop.

## What it does (former SPEC, now live)

- **Upload syllabus + class resources** per subject (syllabus / textbook / teacher_notes / practice_problems)
- **RAG 512/64 + nomic-embed (Ollama) + sqlite-vec** — every answer cites sources
- **Assessments** — all types (MCQ, short-answer, quiz, practice exam), banked, style-cloned from teacher problems, topic-tagged, rubric + citation
- **Grading** — LLM-as-judge with rubric + reasoning; **Dispute → re-grade** with alt reasoning
- **Grades → mastery → re-pace** — mastery = ≥80% on last 2 assessments + no recent failure; weak topics auto-injected as remediation weeks
- **Semester plan** — weekly boxes, date-ranged from syllabus dates
- **Memory** — hierarchical `global.md` vs per-subject `memory.md` + session summaries + self-critique; router decides scope; per-message `simpler/deeper/examples/Socratic` writes through
- **Grade sync** — Canvas / Blackboard / Brightspace via Rakazo MCP (BYO token, OS keychain / encrypted store)

## Layout

```
tutorbot-skill/SKILL.md   # paste into Rakazo → Settings → Skills → New
python/                   # MCP sidecar (FastAPI) — the only code to run
  main.py                 # + /openapi.json, /mcp, /mcp/tools/{name}
  rag.py                  # 512/64 chunk + nomic-embed + cosine
  study.db + store/       # per-subject sources/chunks/assessments/grades/mastery
  memory/                 # global.md + subjects/{id}/memory.md
```

## Quick start

```bash
# 1. Rakazo must be running (~/01 - PROJECTS/rakazo)
cd ~/01\ -\ PROJECTS/rakazo && docker compose -f docker-compose.images.yml --env-file .env up -d
open http://127.0.0.1:5173

# 2. Start sidecar
cd ~/01\ -\ PROJECTS/TutorBot/python
python3 -m uvicorn main:app --port 1421 --host 127.0.0.1

# 3. In Rakazo web: paste tutorbot-skill/SKILL.md as a new Skill, then
#    Integrations → Add MCP/OpenAPI → http://host.docker.internal:1421/openapi.json

# 4. Create one bot per subject, open chat, type:  /TutorBot
```

## Legacy

Previous Tauri desktop + 21 ADRs are archived in git history (`git log --before="2026-09-08"`). This repo now tracks only the Skill + MCP.

License: MIT
