# ADR 018 — Privacy: OS Keychain + Local-Only Promise

Date: 2026-09-03
Status: Decided

## Context
Q19: Where grade credentials and secrets live for pluggable BYO-connectors.

## Decision
**OS keychain via Tauri stronghold.** All LMS tokens/passwords, LLM API keys stored in OS keychain, never in plaintext SQLite, never leaves device. README will explicitly promise: "No textbook, grade, or memory data ever leaves your machine except to your chosen LLM provider (BYOK/local)."

## Consequences
- Need Tauri keychain plugin.
- Privacy docs must mention FERPA-adjacent handling: local-only, user controls provider.
- Grade scrapers run locally.

## Alternatives considered
- Encrypted SQLite (rejected — keychain is OS-native and stronger)
