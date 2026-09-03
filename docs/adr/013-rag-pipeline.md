# ADR 013 — RAG Pipeline + Teacher Notes & Practice Problems

Date: 2026-09-03
Status: Decided

## Context
Q14: PDF → tutor knowledge. Founder adds: must also upload teacher's notes and practice problems so agent creates similar-style (personalized) questions, not generic.

## Decision
**Pipeline:**
- Extract: Poppler/pdf.js → chunk 512 tokens + overlap 64 → embed via nomic-embed-text (Ollama local) or BYOK OpenAI embeddings → sqlite-vec per subject.
- OCR fallback: Tesseract for scanned textbooks/notes.
- Syllabus parser: extract topics/weeks into semester plan graph.
- **Teacher notes & practice problems are first-class sources** alongside textbook: tagged as `source_type = teacher_notes | practice_problems`, weighted higher in retrieval, used as few-shot examples for assessment generation to clone teacher's style.
- Never send full doc to LLM; only top-k retrieved chunks + citations.

## Consequences
- File types: syllabus PDF, textbook PDF, teacher notes (PDF/MD), practice problems (PDF/MD) — all per-subject Sources panel.
- Assessment generator must be style-conditioned: prompt includes retrieved teacher problems as exemplars.
- Embeddings cost on user (local or BYOK).

## Alternatives considered
- Textbook only (extended per founder — needs teacher personalization)
