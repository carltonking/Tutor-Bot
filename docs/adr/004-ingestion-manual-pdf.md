# ADR 004 — Ingestion v1: Manual PDF Upload

Date: 2026-09-03
Status: Decided

## Context
Q5: Manual PDF upload, with a file-list UI like Google NotebookLM.

## Decision
**v1 ingestion = manual PDF upload.** No auto Canvas/SIS import. UI shows per-subject (or per-project) list of uploaded files, like NotebookLM's sources panel.

## Consequences
- Simple, legally safer, works for everyone.
- Need: per-subject file store, PDF parsing pipeline (text extraction, OCR fallback, chunking, embeddings), file-list management (add/remove/re-index).
- Open question: is file list per subject-agent or global? (See Round 2 Q)
- Defer LMS grade-sync auto-import; grades may be manual in v1 unless grade-sync ADR decides otherwise.

## Alternatives considered
- Auto Canvas import (deferred)
