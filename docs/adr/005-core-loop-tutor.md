# ADR 005 — Core Loop: 1:1 Tutor with Semester Plan + Remediation

Date: 2026-09-03
Status: Decided

## Context
Q6: What is daily job? User clarified subject agent is 1:1 tutor: constructs semester plan from syllabus+textbook, explains concepts, tests with quizzes/practice exams, ingests grades mapped to topics x,y,z, identifies struggling concepts, strengthens until mastery (mutual confidence).

## Decision
Core loop = **Semester-plan-driven tutoring**:
1. Ingest syllabus + textbook → agent builds semester plan (paced to not fall behind)
2. Daily: explain concepts on demand (RAG-grounded)
3. Assess via quizzes/practice exams (all types, LLM-graded)
4. Ingest real grades mapped to topics → compare in-app vs. class
5. Remediate weak concepts until mastery threshold (agent + user agree)
6. Update plan (re-paced)

## Consequences
- Need: topic graph per course (syllabus → topics x,y,z), assessment→topic mapping, mastery per topic, plan scheduler.
- Need: grade→topic mapping (user or LLM maps "Midterm 1 = Ch 1-4 = topics x,y,z").
- Mastery definition needed (e.g., 80% on topic-specific assessments + user confirmation).
- Main agent is plan overseer; sub-agents own topic mastery.

## Alternatives considered
- Single habit (quiz-only or chat-only) — rejected, founder wants full tutor loop.
