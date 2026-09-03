# ADR 007 — Assessments: All Types, LLM-Graded Open-Ended

Date: 2026-09-03
Status: Decided

## Context
Q8: Specialized assessments. Decision: D — all types, LLM assesses open-ended.

## Decision
Support **all assessment types**, LLM as grader for open-ended:
- MCQs, flashcards/spaced repetition, quizzes, full practice exams, short-answer / free-response.
- Generated from uploaded PDFs (RAG-grounded, cited).
- Open-ended graded by LLM with rubric + example answer + topic mapping.
- Variety configurable per subject or per plan step.

## Consequences
- Need: assessment generator (RAG → question + rubric + topic tags + citations), grader (LLM-as-judge), spaced-repetition scheduler (e.g., FSRS), question bank per subject.
- Need to guard LLM grading consistency (rubric, self-check, allow user to dispute).
- Cost: generation + grading = 2x LLM calls per open-ended item.

## Alternatives considered
- MCQs only (rejected)
