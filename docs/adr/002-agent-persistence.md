# ADR 002 — Subject Sub-Agent Persistence

Date: 2026-09-03
Status: Decided

## Context
Q3: Should each subject agent be persistent for the semester?

## Decision
**Persistent per subject for the semester.** Each sub-agent owns its course's vector store, assessment history, spaced-repetition schedule, and progress state for the term.

## Consequences
- Requires durable per-subject memory isolation (separate RAG index, conversation history, progress DB rows).
- Main agent is orchestrator/router and cross-subject merger.
- Need lifecycle: create at course creation, persist until semester end / archival, handle semester rollover.

## Alternatives considered
- Ephemeral per-task agents (rejected — would lose tracking/progress requirement)
