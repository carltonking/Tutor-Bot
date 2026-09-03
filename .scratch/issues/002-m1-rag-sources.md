# 002 — M1 RAG + Sources Panel

Status: TODO
Blocks: 003
Blocked-by: 001
SPEC: §4.2 RAG Service, §4.3 sources/chunks/vectors, ADR 004, 010, 013

Deliverables
- Per-subject Sources panel (right inspector tab): upload PDF (syllabus/textbook/teacher_notes/practice_problems), file list with type badge/pages/status, remove, re-index
- Backend: pdf.js/Poppler extract → chunk 512/64 → nomic-embed-text (Ollama) or BYOK embeddings → sqlite-vec per subject table, OCR fallback Tesseract, citation (page) stored, syllabus parser → topics
- Chat retrieval: top-k chunks cited in answer
- Teacher style exemplars: practice_problems tagged, retrieved as few-shot for later assessment gen

Acceptance
- Upload 10-page PDF → indexed rows appear, citations show in chat answer
