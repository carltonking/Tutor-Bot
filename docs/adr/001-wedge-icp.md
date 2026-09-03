# ADR 001 — Wedge & ICP

Date: 2026-09-03
Status: Decided

## Context
Q1: Who is first user? Project is open-sourced on GitHub for everyone and anyone.

## Decision
Build as **general-purpose open-source** from day one — not NYU-wedge. Anyone can self-host/clone. No institutional gating.

## Consequences
- Pro: Maximum reach, community contributions.
- Con: No focused validation loop; risks trying to satisfy every LMS/curriculum. Must still pick a reference LMS (e.g., Canvas) for grade-sync v1 or defer grade-sync to manual entry. Need to define "works for everyone" without over-generalizing data model.

## Alternatives considered
- NYU-only wedge (rejected for this project — founder wants universal access)
