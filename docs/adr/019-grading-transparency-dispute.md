# ADR 019 — Grading Transparency: Rubric + Reasoning + Dispute

Date: 2026-09-03
Status: Decided

## Context
Q20: LLM-graded open-ended assessments — can student dispute?

## Decision
**Full transparency + dispute flow:**
- Show: rubric, retrieved citations, LLM reasoning, score.
- Actions: "Dispute → re-grade with different model" or "Human override mastery."
- Disputes stored as feedback to improve grader; may influence future rubric generation.

## Consequences
- Need grader explainability UI, re-grade path, mastery override.
- Need to store dispute events per assessment.

## Alternatives considered
- Score + explanation only (rejected — trust requires transparency)
