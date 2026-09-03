# 001 — M0 Shell: Tauri + Python Sidecar + SQLite + GrokBot Layout Clone

Status: DONE (2026-09-03)
Blocks: 002, 005
SPEC: §4.1, §5, ADR 011, 012, 021

## Delivered
- Tauri v2 + React-TS scaffold (cargo check ok, vite build ok 197kB)
- GrokBot-clone UI: left 300px sidebar (traffic lights, Search pill, droplet avatars, selected #1E1E20), center chat (status stack, separator, dark/white bubbles, system line, Done pill, pill input + mic), right inspector collapsible (Sources/Plan/Mastery)
- Tokens: --bg #0A0A0C, --card #1C1C1F, radii 16/20, SF Pro 13-15px — audit ADR 021
- Tauri commands: ping, get_subjects; window 1280x800 Study App
- Python sidecar stub FastAPI + SQLite subjects/sources tables + /ping
- README with privacy promise
- Verified: npm run build ✓, cargo check ✓

Next: 002 RAG + Sources (per-subject file list + embed)
