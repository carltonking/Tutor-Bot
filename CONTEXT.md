# CONTEXT.md — Study App

> Generated via /grill-with-docs — shared glossary for the Study App (open-source GrokBot for studying). Update as decisions settle.

## Vision
Open-sourced GrokBot specifically designed for learning and studying. Main agent that users talk to about needs, which spawns specialized sub-agents per subject. Tracks progress in-app vs. real class performance (grades) and adapts. Self-learning from user feedback on response style and study techniques. Supports course details/textbook upload and specialized assessments.

## Domain Glossary

| Term | Definition | Open Question |
|------|------------|---------------|
| **Main Agent (Orchestrator)** | Primary conversational agent that understands user needs, routes to/owns lifecycle of subject agents, merges cross-subject insights | **Settled: persistent orchestrator, spawns persistent subject agents** |
| **Subject Sub-Agent** | Specialized agent per subject/course. Owns textbook index, assessment history, spaced-repetition schedule, progress | **Settled: persistent for semester (ADR 002)** |
| **Course Context** | User-provided course details (syllabus, topics, schedule) + textbook(s) that ground the sub-agent | **Settled: manual PDF upload, NotebookLM-style file list (ADR 004)** |
| **Assessment** | Specialized, generated evaluation (quiz, practice exam, flashcards) to prepare user. Ground truth for adaptation | Who authors? LLM-generated from textbook vs. templated? Predictive of exam? |
| **Grade Sync** | Connection to LMS/SIS where grades are released (Canvas, Blackboard, NYU Albert, etc.) to compare in-app vs. class performance | OAuth vs. extension vs. manual entry for v1? |
| **Progress Tracking** | In-app performance history + real grade history + delta that drives adaptation | What metric? Mastery per topic, predicted grade? |
| **Self-Learning / Adaptation** | System improves from user feedback on agent response style and study techniques, and from performance delta | Signal: explicit feedback (thumbs) vs. implicit (performance)? Per-user RLHF vs. prompt tuning? |
| **Textbook Ingestion (RAG)** | Parsing, chunking, embedding, citing textbook content for grounded Q&A and assessment generation | Stored verbatim? Chunk strategy? Cost? Legal? |

## Actors
- **Student (primary ICP)** — e.g., NYU sophomore with 4-5 courses, heavy credit load, uses LMS daily
- **Main Agent** — router, memory merger, feedback learner
- **Subject Sub-Agents** — domain specialists

## Core Loop (Settled — ADR 005)
Syllabus+textbook → agent builds semester plan → daily explain (RAG) + assess (all types) → ingest grade mapped to topics x,y,z → remediate weak concepts → re-pace plan until mastery.

## Decisions Log (21 ADRs) — see SPEC.md v0.1
- ADR 001 — Wedge/ICP: universal open source
- ADR 002 — Agent persistence: per-subject persistent
- ADR 003 — License scope: fully open (superseded by ADR 017 MIT)
- ADR 004 — Ingestion: manual PDF + file list
- ADR 005 — Core loop: 1:1 tutor with plan + remediation
- ADR 006 — Grade sync: pluggable BYO-connector
- ADR 007 — Assessments: all types, LLM-graded
- ADR 008 — Memory: hierarchical MD + session summaries
- ADR 009 — Platform: desktop BYOK/local
- ADR 010 — File list: per subject
- ADR 011 — Tauri v2 + Python sidecar
- ADR 012 — Python + SQLite + sqlite-vec
- ADR 013 — RAG + teacher notes/style cloning
- ADR 014 — Orchestration: main router + isolated subjects
- ADR 015 — Grade→topic + mastery (80% x2)
- ADR 016 — UI: GrokBot clone
- ADR 017 — License: MIT
- ADR 018 — Privacy: OS keychain
- ADR 019 — Grading transparency + dispute
- ADR 020 — GrokBot ref (x.ai/bot) + independence
- ADR 021 — UI audit: desktop screenshot tokens & layout

## Open Risks (updated 2026-09-03)
- BYO-connector sandboxing + credential vault
- GrokBot clone fidelity vs. monochrome theme conflict
- Local embedding cost for large textbooks
- License choice still open (MIT vs AGPL)

## Decisions Settled (2026-09-03 Rounds 1–3)
- **ICP/Wedge**: Universal open-source on GitHub — everyone (ADR 001)
- **Agent Persistence**: Per-subject persistent for semester (ADR 002)
- **License**: Fully open source, license TBD (ADR 003)
- **Ingestion**: Manual PDF upload + NotebookLM-style file list (ADR 004) — extended: teacher notes + practice problems as first-class sources (ADR 013)
- **Core Loop**: 1:1 tutor — semester plan + explain + assess + grade-aware remediation until mastery (ADR 005)
- **Grade Sync**: Pluggable BYO-connector, main-agent-assisted scaffold, manual fallback (ADR 006)
- **Assessments**: All types, LLM-graded open-ended (ADR 007)
- **Memory**: Hierarchical MD (global vs. subject) + session summaries + self-critique (ADR 008)
- **Platform**: Desktop Mac/Win/Linux + BYOK / local Ollama (ADR 009)
- **File List**: Per subject-agent Sources panel (ADR 010)
- **Desktop Framework**: Tauri v2 + Python sidecar (ADR 011)
- **Data Layer**: Python + SQLite + sqlite-vec + markdown files (ADR 012)
- **RAG**: 512-chunk + nomic-embed + OCR + syllabus parser, teacher-style conditioning (ADR 013)
- **Orchestration**: Main router + isolated subject agents (ADR 014)
- **Mastery**: Hybrid grade→topic mapping, ≥80% x2 + no recent failure (ADR 015)
- **UI/UX**: GrokBot clone + per-subject Sources/Plan/Mastery (ADR 016)

## Frontier — CLOSED (2026-09-03)
All branches visited. Shared understanding reached. Spec frozen in SPEC.md v0.1 + ADR 021 visual audit.

## Final Decisions (Rounds 1–4)
- **License**: MIT (ADR 017)
- **Privacy**: OS keychain + local-only promise (ADR 018)
- **Grading**: Rubric + reasoning + dispute/re-grade (ADR 019)
- **GrokBot Reference**: https://x.ai/bot + desktop screenshot docs/grokbot_reference_desktop.png — full audit in ADR 021; Study App independent from StudyFlow/QTS (ADR 020)

## Open Risks (from unbiased review)
- Grade sync SSO complexity
- Textbook copyright + RAG cost
- Vague self-learning signal
- Moat is grade-closed-loop, not chat wrapper
- Inference cost vs. open-source monetization
