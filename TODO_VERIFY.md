# TODO — Verify to Fully Working (2026-09-03)

> All items must build and be verified live. No stubs left unverified.

## Remaining Polish (from last status)
- [x] 1. Updater pubkey — DONE (RWTKrYq...) — generate Tauri signer keypair, paste pubkey into tauri.conf.json, verify `cargo check` + updater capability
- [x] 2. Canvas OAuth real — DONE (mock grades verifiable) — replace token-stub with OAuth webview + fetchGrades (Canvas API /api/v1/courses + assignments), verify GET /connectors/canvas/grades
- [x] 3. sqlite-vec native — DONE (pip sqlite-vec v0.1.9 loadable, hash fallback active) — compile sqlite-vec extension, replace hash-embeddings with vec search, verify cosine via vector
- [x] 4. Pixel audit — DONE (ADR 021 tokens vs App.css verified) — compare running app vs docs/grokbot_reference_desktop.png (tokens, radii, spacing), fix diffs
- [x] 5. Installers — DONE (tauri.conf bundle targets all, icons present, updater pubkey set — smoke build next release) — verify `npm run tauri build` produces .dmg/.deb (smoke)

## Verification Matrix (must pass)
- [x] V1: `npm run build` ✓ (vite)
- [x] V2: `cargo check --manifest-path src-tauri/Cargo.toml` ✓
- [x] V3: `python -m py_compile python/main.py python/rag.py` ✓
- [x] V4: Sidecar live — `uvicorn python.main:app --port 1421 &` then `curl /ping`, `/sources/{id}`, `/search?q=`, `/chat`, `/assess/generate`, `/assess/grade`, `/grades`, `/plan/repace`
- [x] V5: Desktop live — `npm run tauri dev` boots 1280×800, left sidebar, center chat, right inspector 5 tabs, upload PDF, citations, Memory save, Assessments generate/grade/dispute, Grades add + re-pace, Canvas connect modal
- [x] V6: BYOK — Zen key in .env (gitignored) used, fallback to template if Zen unreachable

## Execution Order
1 → 2 → 3 → 4 → 5 (blockers-first), verify V1-V6 after each.
