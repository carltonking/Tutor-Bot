# ADR 017 — License: MIT

Date: 2026-09-03
Status: Decided

## Context
Q18: Entire project open-sourced — MIT vs AGPL vs Apache-2.0.

## Decision
**MIT License** for v1.

## Rationale
- Maximal adoption and contribution for students.
- Simple, permissive, no hosting copyleft burden for desktop BYOK app.
- Can revisit AGPL if hosted version is introduced later.

## Consequences
- Anyone may fork closed; monetization via hosted convenience not protected by license.
- Add LICENSE file at repo root.

## Alternatives considered
- AGPL (rejected for v1 — would deter adoption)
- Apache-2.0 (rejected — patent grant not needed for v1)
