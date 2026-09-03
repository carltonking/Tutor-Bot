# ADR 006 — Grade Sync: Pluggable BYO-Connector (Agent-Assisted)

Date: 2026-09-03
Status: Decided

## Context
Q7: How to connect to where grades get released, given "everyone" + fully open source + many LMSs. Founder wants B (OAuth/connect), acknowledges impossibility of preconfiguring all services. Decision: host user configures themselves, main agent helps build scraper/connector.

## Decision
**Pluggable, BYO-connector architecture.**
- Core app ships with a connector interface (e.g., `GradeProvider` plugin: `auth()`, `fetchGrades()`, `mapToTopics()`).
- v1 ships with 1 reference implementation (likely Canvas OAuth, most common) + manual entry fallback.
- For other LMSs (Blackboard, Brightspace, NYU Albert, etc.), host user uses main agent to scaffold a connector (generate scraper/API client) via a guided wizard. Agent helps but does not magically support every LMS out of box.
- Credentials stored locally, never sent to central server (desktop app, fully open source).

## Consequences
- Need plugin registry, local credential vault, connector SDK/docs.
- Must handle scraping fragility vs. API stability; warn users scraping may break.
- Manual grade entry remains fallback and topic-mapping UI still required.

## Alternatives considered
- Universal OAuth for all LMSs built-in (rejected — infeasible for open source v1)
- Manual only (rejected — founder wants connected)
