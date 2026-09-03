# 002 — M1 RAG + Sources Panel

Status: DONE (2026-09-03) — naive keyword search; embeddings next
Blocked-by: 001
Blocks: 003

Delivered
- Tabs Sources/Plan/Mastery/Memory (right inspector)
- Sources: upload via @tauri-apps/plugin-dialog (+ Syllabus/Textbook/Notes/Problems), list per-subject, mock fallback if sidecar not running
- Rust: dialog+fs plugins + capabilities
- Python: rag.py (pypdf extract → chunk 512/64), main.py ingest splits pdf→chunks, /sources, /search keyword, store on disk per subject
- Build: vite 198kB, cargo check ok

Next: sqlite-vec + nomic-embed (Ollama) for semantic search; teacher style weighting already in data model (type field)
