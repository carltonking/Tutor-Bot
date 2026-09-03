# Study App — SPEC (v0.1 — from /grill-with-docs)

> Generated 2026-09-03 via /grill-with-docs → /to-spec. Primary sources: CONTEXT.md + docs/adr/001-021 + docs/grokbot_reference_desktop.png + x.ai/bot. Drawn from 21 ADRs. Keep updated; do not duplicate CONTEXT glossary.

## 1. Vision & Scope

**Vision:** Open-source GrokBot for studying — desktop tutor where the main agent spawns persistent per-subject sub-agents that ingest syllabus/textbook/teacher notes/practice problems, build a semester plan, explain, assess (all types, LLM-graded), sync real grades via pluggable BYO-connectors, track mastery per topic, and remediate until confidence. Self-improving via hierarchical markdown memory + session summaries.

**Platform:** Desktop (Mac/Win/Linux) via **Tauri v2 + Python sidecar**, **BYOK or local Ollama**, local-first, MIT licensed, greenfield independent of StudyFlow/QTS (ADR 009, 011, 017, 020).

**Who it's for:** Universal open-source on GitHub — anyone/student can self-host (ADR 001). Reference LMS for v1 is Canvas; others via BYO-connector scaffold.

**Non-goals (v1):** No hosted inference, no pre-built universal LMS sync (BYO), no mobile, no web, no cross-project code reuse.

## 2. Definitions (from CONTEXT.md)

- **Main Agent (Orchestrator):** Persistent router, global memory owner, scaffolds subject agents and grade connectors (ADR 002, 014).
- **Subject Sub-Agent:** Persistent per subject for semester, owns vector store, assessment history, plan slice, mastery, memory.md (ADR 002).
- **Course Context:** Manual PDF uploads per subject: syllabus, textbook, teacher notes, practice problems (ADR 004, 013).
- **Assessment:** MCQs, flashcards/SR, quizzes, practice exams, short-answer — grounded in retrieved chunks + teacher style, open-ended graded by LLM (ADR 007).
- **Grade Sync:** Pluggable `GradeProvider` (auth/fetchGrades/mapToTopics) + manual fallback; host configures, main agent assists scaffolding (ADR 006).
- **Progress / Mastery:** Topic graph per course, grade→topic hybrid mapping, mastery = ≥80% on last 2 assessments + no recent real-grade failure (ADR 015).
- **Memory:** Hierarchical MD — global.md + per-subject memory.md + per-session summaries + self-critique, routing LLM decides scope (ADR 008).
- **RAG:** Chunk 512/64, local nomic-embed-text or BYOK embeddings → sqlite-vec per subject, OCR fallback, syllabus parser, teacher style conditioning (ADR 013).

## 3. User Journeys

### 3.1 First run
1. Install desktop app (GitHub Release). Onboarding: choose provider (OpenAI/Anthropic key or Ollama local), keys → OS keychain (ADR 018). Promise banner: "Nothing leaves your machine except to your chosen provider."
2. Main agent chat: "What subjects this semester?" → user says "Calculus II, Bio 101" → main agent spawns two subject agents (left sidebar shows droplet avatars, like GrokBot's Bob/Projects Manager).
3. Per subject: Sources panel → upload syllabus PDF + textbook PDF + teacher notes + practice problems (per-subject file list, ADR 010). RAG indexes, syllabus parser builds topic graph + semester timeline.
4. Agent proposes semester plan (weekly boxes) + first assessment. User confirms.

### 3.2 Daily loop (ADR 005)
- Open subject channel (GrokBot channel pattern — one channel = one subject, roster shows Members).
- Chat: "Explain Stokes' theorem" → RAG-grounded answer with citations.
- Take assessment card (inline in chat, like GrokBot's status stack card): 10 MCQs + 2 short-answers, grounded + style-cloned from teacher problems.
- Submit → LLM grades open-ended (show rubric + reasoning + citations + Dispute → re-grade, ADR 019). Score stored per topic.
- Mastery bars update (right inspector). Weak topics injected into plan.
- Evening: session summary auto-written to subject memory.md + self-critique ("what to improve").
- Real grade arrives: manual entry or connector fetch → hybrid mapping proposes "Midterm 1 = topics X,Y,Z" → user confirms → plan re-paces, remediation queue updated.

### 3.3 Grade connector setup
- From main agent: "Connect my grades" → marketplace view (dark, like GrokBot Plugins: `Canvas ✓Added / Add`, `Blackboard [Add]`) → pick provider → wizard (OAuth or scraper template) → agent scaffolds connector (local code) → credentials to keychain → test fetch → done. Unsupported LMS: agent generates scraper skeleton guided by user.

### 3.4 Feedback / memory
- Per-message controls: "simpler / deeper / more examples / Socratic" → updates memory routed to global or subject (LLM router).
- Direct instruction ("always be concise") → writes to global.md or subject memory.md immediately.
- Session summary visible in Memory tab, editable.

## 4. Architecture

### 4.1 High-level
- **Frontend:** Tauri v2 (Rust) + TypeScript (React or Svelte). Window chrome cloned from screenshot: traffic lights, search pill, + New Subject dropdown, left 300px sidebar, center chat, collapsible right inspector (>>), input pill + mic, dark #0A0A0C / #1C1C1F.
- **Backend:** Python sidecar (FastAPI or IPC) — owns RAG, embeddings, syllabus parser, assessment generation/grading, mastery calc, memory summarization, connector runtime. Communicates via Tauri IPC / localhost.
- **Storage:** SQLite (one DB, per-subject prefixes or separate files) + sqlite-vec per subject for vectors, markdown files for memory (global.md, subjects/<id>/memory.md, sessions/<date>.md), file store for PDFs (subjects/<id>/sources/*). Offline-first.
- **LLM:** BYOK (OpenAI, Anthropic, etc.) or local Ollama. Never proxy. Provider selector in settings marketplace.

### 4.2 Components
1. **Orchestrator (Main Agent):** Router, tool-caller, subject lifecycle (create/archive), connector scaffolding wizard, global memory I/O.
2. **Subject Agent:** System prompt = global.md + subject memory.md + topic graph + mastery state + retrieved chunks. Tools: retrieve, generateAssessment, grade, updatePlan, logGrade, summarizeSession.
3. **RAG Service:** pdf.js/Poppler → chunk 512+64 → nomic-embed-text (Ollama) → sqlite-vec, OCR Tesseract fallback, citations.
4. **Syllabus Parser:** LLM extracts topics, weeks, weights → topic graph + plan timeline.
5. **Assessment Engine:** Retrieves teacher problems as few-shot exemplars + textbook chunks → generates questions + rubric + topic tags + citations → bank → scheduler (FSRS for flashcards).
6. **Grader:** LLM-as-judge with rubric + retrieved chunks, returns score + reasoning + citations; dispute path re-runs with alt model.
7. **Plan Scheduler:** Weekly timeline, auto-inserts remediation for non-mastered topics.
8. **Memory Service:** Session summarizer + router (LLM decides global vs subject), markdown read/write, human-editable.
9. **Connector Runtime:** Plugin interface `GradeProvider { id, auth(), fetchGrades(), mapToTopics() }`, registry, keychain vault, local execution sandbox.
10. **UI Shell:** Sidebar, channel header, status/score cards, bot/user bubbles (dark vs white), separator "Messages from X and Y", system lines, input pill, right inspector (Sources/Plan/Mastery/Memory), plugin marketplace.

### 4.3 Data Model (SQLite + files)
- `subjects(id, name, color_droplet, created_at, archived_at)`
- `sources(id, subject_id, filename, type: syllabus|textbook|teacher_notes|practice_problems, path, pages, indexed_at, vector_count)`
- `chunks(id, source_id, subject_id, text, embedding_id, page, citation)`
- `vectors(subject_id, chunk_id, embedding)` (sqlite-vec)
- `topics(id, subject_id, name, parent_id, week, weight)`
- `assessments(id, subject_id, type, title, generated_at, source_refs)`
- `questions(id, assessment_id, topic_id, prompt, style_exemplar_ids, answer, rubric, citation_ids)`
- `attempts(id, question_id, user_answer, score, reasoning, graded_by, disputed, created_at)`
- `grades(id, subject_id, title, score, max, date, raw_text, topic_ids[])` + manual vs connector provenance
- `mastery(subject_id, topic_id, score_last2, mastery_bool, updated_at)`
- `plan_items(id, subject_id, topic_id, type: learn|assess|remediate, week, status)`
- Files: `global.md`, `subjects/<id>/memory.md`, `subjects/<id>/sessions/YYYY-MM-DD.md`, `subjects/<id>/sources/*`

## 5. UI/UX Spec — GrokBot Clone (primary: docs/grokbot_reference_desktop.png)

**Design tokens (audit ADR 021):** bg #0A0A0C, sidebar #121214, card #1C1C1F, selected #1E1E20, pill input #1A1A1E border #2A2A2E, text white #FFFFFF, muted #9A9AA0, radii: card 16, user bubble 20, sidebar row 12, avatar 40 circle with eyes glyph, typography SF Pro/Inter 12-15px, checkmark 14px.

**Layout (GrokBot 1:1):**
- **Window:** Tauri native chrome, red/yellow/green traffic lights left, `+` new Subject/Channel top, monitor icon top-right.
- **Left 300px:** Search pill, scroll list of subjects + Main agent row (Chief = Main). Each row: droplet avatar color per subject, name, time (e.g., "Yesterday", "8:54 AM"), preview truncated. Selected = Sales Outbound pattern (orange, Done.). Bottom: profile "AS" + name.
- **Header 52px:** Selected subject avatar + name + bottom border.
- **Center chat (flex):** Media card (for plan preview image) + status stack card (checklist: "✓ Salesforce → list pulled · 52 accounts" pattern → for Study App: "✓ Syllabus parsed → 12 topics" "✓ Textbook indexed → 842 chunks" etc.) + separator "Messages from [Agent] and [Main]" + bot bubbles (dark) + user bubbles (white + thumbs-up reaction) + system line "Created routine 🕒 Overnight outbound" → for Study App: "Created plan 🕒 Semester pace" + pill "Done." + input bar: `[+] Message <Subject> [🎤]` pill #1A1A1E.
- **Right inspector (collapsible via >>, 340px):** Tabs: `Members` (roster), `Sources` (per-subject file list with name/type/pages/status), `Plan` (weekly timeline), `Mastery` (topic bars), `Memory` (editable MD). Hidden by default on narrow, toggles like GrokBot roster.
- **Plugins/Marketplace view:** Full-width dark page, tabs `Marketplace / Yours`, Search, sections `Featured` (Canvas, Blackboard) + `Agent Orchestration` — each row icon + name + description + `✓Added / Add` chip.

**Study-specific cards (map GrokBot status card):**
- Assessment card: question + citations + "Draft badge" style → "Topic: integrals · Source: p.124"
- Grade card: "✓ Midterm 1 → 78% · mapped to: derivatives, integrals (confirm)"
- Mastery card: topic bar 0–100%, remediation queue

**Theme:** Strict dark monochrome per profile; avatar droplets are the only color.

## 6. Security & Privacy
- Keys/tokens in OS keychain via Tauri stronghold, never plaintext (ADR 018).
- Promise: "No textbook/grade/memory leaves your machine except to your chosen LLM provider." Display in onboarding + README.
- BYO-connectors run locally sandboxed; scraping warns "may break."
- No central server.

## 7. Build & Distribution
- GitHub repo `Study App`, MIT LICENSE, README with BYOK setup + Ollama guide + privacy promise.
- Releases: Tauri bundler → .dmg (mac arm64/x64), .exe/.msi (win), .deb/.AppImage (linux). GitHub Releases + auto-updater.
- CI: Rust + Python lint, typecheck, tests.

## 8. Open Questions → Tickets
- Exact topic extraction schema (syllabus parser prompt)
- FSRS parameters for flashcards
- Provider abstraction (unified LLM interface for OpenAI/Anthropic/Ollama)
- Sandbox for generated connectors (limit fs/net)
- Mastery re-pacing algorithm (how much remediation per week)

## 9. Milestones (for /to-tickets)

**M0 — Shell:** Tauri + Python sidecar IPC, SQLite+vvec, left sidebar + chat shell cloned from screenshot, dark tokens, traffic lights, search, `+ New Subject` → subject avatar list, input pill. Prove desktop boots Mac/Win/Linux.

**M1 — RAG + Sources:** Per-subject Sources panel (upload PDF, list, remove, indexed status), pdf→chunk→embed→sqlite-vec, OCR, syllabus → topic graph, citations in chat. Teacher notes/problems as `type` + style exemplar weighting.

**M2 — Tutor Loop:** Subject agent chat (global + subject memory + RAG), explain with citations, mastery bars skeleton, session summary → memory.md. BYOK/Ollama selector in marketplace.

**M3 — Assessments:** Generator (RAG + teacher style → questions + rubric), all types, bank, scheduler, grader (LLM-as-judge), rubric+reasoning+dispute UI, assessment card in chat, topic-mapped scoring.

**M4 — Plan + Grades:** Semester plan timeline, auto-repace, manual grade entry + hybrid grade→topic mapping UI (LLM propose → confirm), Mastery = 80% x2, remediation injection. Manual fallback done.

**M5 — Memory:** Hierarchical MD (global.md + subject memory.md), router LLM, per-message "simpler/deeper/examples/Socratic" controls, direct instruction → memory write, Memory tab editor, per-session self-critique.

**M6 — Connectors (BYO):** Plugin interface + registry + keychain vault + marketplace (Canvas reference + manual), wizard that scaffolds connector via main agent, sandbox, local run. Docs for writing connectors.

**M7 — Polish & Ship:** Pixel-perfect GrokBot audit pass vs. screenshot, mastery dashboard visuals, plan calendar, auto-updater, installers, README, LICENSE (MIT), privacy docs, open-source release.

## 10. Primary Sources
- CONTEXT.md (89 lines)
- ADR 001–021 (20 ADRs + UI audit)
- docs/grokbot_reference_desktop.png (522K, GrokBot Sales Outbound desktop, dark marketplace/roster images)
- x.ai/bot + /bot/guides (channel/roster/plugin visuals)

## 11. Next: /to-tickets
Run `/to-tickets` to split M0–M7 into tracer-bullet tickets with blocking edges (RAG → Assessments → Plan → Grades → Memory → Connectors), then `/implement` per ticket (each drives /tdd + /code-review).
