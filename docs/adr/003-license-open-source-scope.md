# ADR 003 — Open-Source Scope & License

Date: 2026-09-03
Status: Decided (provisional — needs license choice)

## Context
Q4: Entire project open-sourced.

## Decision
**100% open source.** Entire codebase on GitHub, self-hostable by anyone.

## Consequences
- Must choose license: MIT (permissive, maximal adoption) vs. AGPL (prevents hosted closed forks) vs. Apache-2.0. Decision still open.
- No proprietary hosted component; monetization must be via hosted convenience, donations, or not at all.
- Textbook storage liability: cannot redistribute copyrighted chunks; RAG must be local/private per user.
- Inference cost is on deployer (BYOK) — need clear BYOK story from day one.

## Alternatives considered
- Open harness + proprietary grade-sync/eval (rejected per founder intent — wants fully open)
