# ADR 009 — Platform: Desktop (Mac/Win/Linux) + BYO Provider / Local Models

Date: 2026-09-03
Status: Decided

## Context
Q10: Desktop for all three OSs, any provider or local models.

## Decision
**Desktop app** for macOS, Windows, Linux. **BYOK + local**.
- User can connect any provider (OpenAI, Anthropic, etc.) or use local models (Ollama).
- No hosted inference; keys stored locally in OS keychain.
- Framework to be decided (Tauri vs. Electron), but constraint is desktop + cross-platform + local file access for PDFs/memory.md.

## Consequences
- Need: desktop framework choice, auto-updater, keychain integration, Ollama integration.
- RAG/embeddings must run locally or via BYOK (cost on user).
- Distribution: GitHub Releases + installers.

## Alternatives considered
- Web app (rejected per founder)
