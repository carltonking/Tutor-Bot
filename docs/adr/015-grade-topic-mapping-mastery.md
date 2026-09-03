# ADR 015 — Grade→Topic Mapping + Mastery Definition

Date: 2026-09-03
Status: Decided

## Context
Q16: Who maps grade to topics and what is mastery?

## Decision
**Hybrid mapping + threshold mastery:**
- LLM proposes topic mapping from syllabus + test description (e.g., "Midterm 1 = Ch 3-4 = derivatives, integrals"), user confirms in UI.
- Mastery = topic score ≥80% on last 2 assessments + no recent real-grade failure on that topic. Until then, semester plan auto-injects remediation.
- UI shows topic bars and remediation queue.

## Consequences
- Need topic graph, assessment→topic tags, grade→topic join table, confirmation UI.
- Plan scheduler must support auto-replanning.

## Alternatives considered
- Manual only or LLM only (rejected — hybrid balances accuracy + UX)
