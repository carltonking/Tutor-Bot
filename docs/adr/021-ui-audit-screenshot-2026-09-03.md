# ADR 021 — UI Audit: GrokBot Desktop Screenshot (2026-09-03)

Date: 2026-09-03
Status: Decided
Source: /Users/carltonking/Downloads/Screenshot 2026-09-03 at 08.55.02.png (copied to docs/grokbot_reference_desktop.png)

## Visual Audit (pixel observations)

**Window chrome:** macOS traffic lights (red/yellow/green) top-left, title bar dark #0E0E0E, `+` icon top-left pane, monitor/external-display icon top-right. Strict dark monochrome, no accent except avatar colors.

**Left Pane (280-320px, dark #121214):**
- Search: pill-shaped, dark #1A1A1E, magnifier, placeholder "Search"
- List rows: 64px height, avatar 40px circle with "eyes" glyph, name 15px white, time 12px muted right-aligned, preview 13px muted Single line truncated ("booked the venue and sent the c...", "Done.")
- Selected row (Sales Outbound): background #1E1E20, rounded 12px, orange avatar (two-dot eyes)
- Other avatars: Chief teal, Inbox Manager blue/purple triangle, Account Manager purple, Talent Scout blue, Expense Manager orange, Offsite crew stacked 3 circles (teal/purple/purple)
- Bottom: user profile "AS Armand Segall" 14px

**Center / Chat Pane (flex, dark #0A0A0C):**
- Header: 52px, avatar + "Sales Outbound" 15px white, bottom border 1px #1E1E1E
- Media card: rounded 16px, image (ocean), overlay tooltip "Daniel Alvarez — Draft — 36 drafts queued / 0 sent" (dark card with small text 11px)
- Status stack card: dark bubble #1C1C1F, rounded 16px, lines: "✓ Salesforce → list pulled · 52 accounts" (bold source, arrow, muted detail). Checkmark 14px.
- Separator: centered "Messages from Account Manager and Chief" (13px muted, with purple/teal pill badges)
- Bot bubbles: dark #1C1C1F, rounded 16px, 14px text, purple/teal inline mentions "Account Manager" "Chief"
- User bubble: white #F0F0F0, black text, rounded 20px, right-aligned, tail? No tail. Reaction: small thumbs-up yellow joined to bottom-right.
- System line: "Created routine 🕒 Overnight outbound" 13px muted, clock icon
- Small dark pill "Done." 14px
- Input bar: pill #1A1A1E, border 1px #2A2A2E, "+" circle button left, placeholder "Message Sales Outbound" 14px muted, mic button white circle right.

**Typography:** System sans (SF Pro / Inter-like), tight line height, 13-15px body, 12px meta.

**Implications for Study App Clone:**
- Reuse exact density: left 300px, chat center, no right panel in screenshot (but we will add collapsible right inspector for Sources/Plan/Mastery — matches GrokBot's `>>` collapsible roster).
- Keep dark palette: bg #0A0A0C, card #1C1C1F, selected #1E1E20, text white/muted #9A9AA0.
- Avatars: droplet shape with eyes, per-subject color (one hue per subject).
- Bubbles: bot = dark, user = white, same radii (16 vs 20).
- Input: pill + mic, same as GrokBot.
- Add right inspector as extension: toggle via >> icon seen in earlier roster screenshot; when open, Shows Sources (NotebookLM file list), Plan timeline, Mastery.

## Decision
Lock this screenshot as primary visual reference for Study App UI spec. Tauri clones window chrome, colors, radii, and layout exactly; right inspector is additive for study domain.

## Consequences
- Design tokens must match these values.
- Prototype must verify fidelity before spec freeze.
