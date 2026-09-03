# Tutor Bot — GrokBot for Studying

Open-source desktop tutor (Tauri v2 + Python + SQLite). Main agent spawns persistent per-subject agents. Manual PDFs per subject → RAG (512 chunk + nomic-embed) → assessments style-cloned from teacher notes → grade→topic mastery (80% x2) → plan re-pace. BYOK/Ollama, OS keychain.

**Privacy:** Nothing leaves your machine except to your chosen LLM provider. Keys/tokens in OS keychain. Local-first, offline.

## Quick start
```bash
npm install
npm run tauri dev   # desktop
# python sidecar (future): uvicorn python.main:app --port 1421
```

## Docs
- `CONTEXT.md` — glossary
- `SPEC.md` — spec
- `docs/adr/` — 21 ADRs + GrokBot audit
- `docs/grokbot_reference_desktop.png` — primary visual reference

License: MIT
