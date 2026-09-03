# ADR 008 — Memory: Markdown Hierarchical (Global vs. Subject) with Session Summaries

Date: 2026-09-03
Status: Decided

## Context
Q9: Self-learning / adaptation. Wants markdown system memory, session summaries with self-improvement, direct user requests update memory, routing to global vs. subject memory.

## Decision
**Hierarchical MD memory:**
- Per subject-agent: `memory.md` + per-session summaries (what went well, what to improve). Agent writes summary after each session, including self-critique.
- Global: `global.md` for cross-subject preferences ("always explain simply", "use Socratic").
- Direct user instruction ("respond more concisely") updates relevant memory immediately.
- Agent decides routing: general preference → global; subject-specific → subject memory (C — both implicit + explicit, with routing).
- Implementation: markdown files on disk (desktop app), versioned, human-editable.

## Consequences
- Need: memory read/write tools for agents, summarizer prompt, routing classifier (LLM decides global vs. subject).
- Need: UI to view/edit memory (like ALFRED profile).
- Privacy: local only.

## Alternatives considered
- Single global memory (rejected)
- Pure vector memory (rejected — founder wants inspectable MD)
