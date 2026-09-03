# ADR 012 — Backend & Data Layer: Python Sidecar + SQLite + sqlite-vec

Date: 2026-09-03
Status: Decided

## Context
Q13: Persistent per-subject agents need durable storage.

## Decision
**Python sidecar + SQLite + sqlite-vec**, markdown files on disk.
- Per subject slice: DB rows (topics, assessments, grades, mastery) + vector table + memory.md.
- Python owns RAG, assessment generation, LLM grading, session summarization.
- Tauri frontend talks to Python via IPC.

## Consequences
- Offline-capable, local-first, open-source clean (no central DB).
- Reuses QTS Python patterns.
- Need migration story for DB schema.

## Alternatives considered
- Pure filesystem JSON (rejected — need vector + relational for mastery)
