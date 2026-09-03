# ADR 016 — UI/UX: GrokBot Clone + NotebookLM per-Subject Layout

Date: 2026-09-03
Status: Decided

## Context
Q17: UI layout. Founder wants clone of GrokBot UI/UX. Recommended was NotebookLM-style per-subject layout.

## Decision
**Clone GrokBot UI/UX** as base, composed with per-subject structure:
- Left sidebar: agent list (main + subject agents)
- Center: chat/tutor + assessment cards (GrokBot chat styling)
- Right: Sources panel (per-subject PDFs/notes/problems) + Semester Plan timeline + Mastery dashboard (topic bars)
- Inside subject: tabs for Plan / Chat / Assess / Grades / Memory (if GrokBot has similar).
- Semester plan visualized as weekly timeline.
- Theme: dark, strictly monochrome per profile (no accent colors) unless GrokBot clone overrides — need to reconcile.

## Consequences
- Need to capture GrokBot reference screenshots/figma; ensure clone respects original but adapts to per-subject isolation.
- Need to audit GrokBot's actual layout — research task for prototype phase.

## Alternatives considered
- Pure NotebookLM (extended to GrokBot clone per founder)
