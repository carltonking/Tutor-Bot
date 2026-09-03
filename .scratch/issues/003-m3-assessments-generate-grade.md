# 003 — M3 Assessments: Generate + Grade (LLM) — style-cloned

Status: TODO
Blocked-by: 002
Blocks: 004
SPEC: ADR 007, 013, 019

Deliverables
- Generator: RAG (topic + teacher exemplars) → questions (MCQ, short-answer, flashcards, practice exam) + rubric + topic tags + citation_ids → bank
- Scheduler/FSRS for flashcards
- Grader: LLM-as-judge, returns score + reasoning + citations, Dispute → re-grade path
- UI: assessment card inline in chat (like GrokBot status stack), rubric/reasoning disclosed, topic-mapped scoring fed to mastery

Acceptance: generate 5 Qs from uploaded textbook + grade open-ended with dispute
