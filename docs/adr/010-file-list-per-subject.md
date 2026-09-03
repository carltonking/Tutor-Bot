# ADR 010 — File List: Per Subject Agent

Date: 2026-09-03
Status: Decided

## Context
Q11: File list per subject agent.

## Decision
**Per subject-agent Sources panel**, like one NotebookLM notebook per course. Each subject shows its PDFs, syllabus, textbook, with add/remove/re-index status.

## Consequences
- UI: subject sidebar → subject page with Sources panel.
- Backend: per-subject file store, per-subject vector index, per-subject RAG scope.

## Alternatives considered
- Global file list (rejected)
