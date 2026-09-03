# ADR 014 — Agent Orchestration: Main Router + Isolated Subject Agents

Date: 2026-09-03
Status: Decided

## Context
Q15: How main agent spawns subject agents.

## Decision
**Main agent is router + global memory owner; sidebar lists subject agents.**
- Main chat can "create Calculus II agent" or "help me build a Canvas connector" and spawns it.
- Sidebar switch: pick subject to talk directly to that sub-agent.
- Isolation: each subject agent sees only: global.md + its own memory.md + its own vector store + its own assessment history.
- Cross-subject tasks go through main agent.

## Consequences
- Need orchestrator (LangGraph or custom router) + subject agent registry + lifecycle (create/archive).
- Strict isolation prevents cross-contamination.

## Alternatives considered
- Pure switcher or pure router (rejected — need both)
