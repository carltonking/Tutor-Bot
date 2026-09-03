# ADR 020 — GrokBot Reference (x.ai/bot) + Project Independence

Date: 2026-09-03
Status: Decided

## Context
Q21: GrokBot reference is https://x.ai/bot. Founder wants Study App independent from other projects (StudyFlow, QTS, etc.).

## Decision
- **GrokBot reference:** https://x.ai/bot — "Message Bots like teammates" — paradigm: create a Bot per job, bots work in parallel, keep context, learn from each other, take projects start-to-end, ask for approval. Study App's main-agent → persistent subject-agents maps directly to this: one Bot per subject, main Bot as orchestrator.
- **Independence:** Study App is greenfield, no code reuse from StudyFlow/QTS. Fresh repo, fresh Tauri+Python stack.

## Evidence from x.ai/bot (fetched 2026-09-03)
- "Give tasks to Bots like you would a teammate... Bots keep context on how you work and get smarter over time"
- "Work with many Bots at once — Create a Bot, give it a task, add another... one on a project, one on outbound, one on systems. AI teammates work in parallel"
- "Bots get smarter over time — Bots keep context and learn from each other"
- "Connect the Bots — Put a few Bots in the same thread and they pass work between themselves"

## Consequences
- UI/UX clone must reflect this teammate model: agent list = bots, each with job/topic, parallel work, handoff.
- No shared code with StudyFlow/QTS; document Study App as standalone.
- Need to capture screenshots from x.ai/bot for fidelity during design phase.

## Alternatives considered
- Reuse StudyFlow/QTS engine (rejected per founder)
