# ADR 011 — Desktop Framework: Tauri v2

Date: 2026-09-03
Status: Decided

## Context
Q12: Mac/Win/Linux desktop. Choice between Tauri and Electron.

## Decision
**Tauri v2** — TypeScript frontend + Rust/Python sidecar for RAG and agent runtime.

## Rationale
- Tiny bundle, fast, secure, native local file access for PDFs/memory.md.
- Python sidecar handles RAG and agent logic (reuse from QTS/Quant-Projects).
- Ollama/local model integration clean.
- Monochrome dark theme preference (profile) fits Tauri's native windowing.

## Consequences
- Build pipeline: Rust toolchain + Python sidecar.
- IPC between Tauri frontend and Python agent runtime.

## Alternatives considered
- Electron (rejected — bundle size)
- Web-wrapped-later (rejected — founder wants desktop native)
