# RAVEN implementation state — 2026-09-09

## Outcome and scope

This is an implemented, running product-rebuild pass, not a certification that every requirement is production-complete. Open http://localhost:8080 in Chrome. The original voice pipeline and typed tool router remain; this pass adds real workspace composition and fixes command regressions without claiming measured microphone accuracy or latency improvements.

## Implemented

- Home: original miniature six-station world, clickable navigation, activity-driven avatar/signals, reduced motion, shared text/voice entry. Operations projects real database records instead of inventing work or percentages.
- Career: Overview, Discover, Applications, Profile, Documents; structured factual history/preferences; full saved job descriptions and fit rationale; linked versioned document downloads; local-only career generation. New discovery adds local embedding similarity to lexical fit (65% lexical, 35% nonnegative cosine), not a hiring probability.
- Content: persistent campaign create/edit/archive/delete/duplicate-brief; platform selection; seven workspace tabs; caption edits; actual image previews; separate variants; safe local media-record deletion; existing approval/publishing controls.
- Research: Report, Sources, Findings, Artifacts views; real cancellation; named execution stages; token usage updated before completion; downloaded report includes its source ledger.
- Hermes: live worker inventory, real `web_search`/`web_extract` readiness, 71 installed skill descriptions separated from enabled tools, and authenticated MCP `initialize` + `tools/list` probes for explicitly configured HTTP servers. Configuration alone is never reported as connectivity.
- Research UX consolidation: Research Lab is now the only user-facing research launcher. “Ask Hermes to research …” creates the same durable Research Lab project; Hermes web discovery is an internal fallback, and its one-query test is labelled as an advanced connection diagnostic.
- Graph: cross-page semantic memory filtering routes before Spotify keywords; existing node editing/deletion remains. Category requests currently use semantic retrieval, not a complete typed entity ontology.
- Routing: transcript regressions for repeated corrections, liked/like songs, navigation, YouTube variants, research status/cancellation, and graph zoom/filter actions.
- Research failover: free OpenRouter first, optional server-side NVIDIA NIM second, then local Ollama. Structured output handles HTTP-200 errors, truncation, fenced JSON and unavailable providers. No paid fallback. Private career facts stay local.
- Windows startup: the canonical launcher now starts ComfyUI and the authenticated desktop bridge before Docker reads its environment. Docker-only startup intentionally cannot create a Windows host process.

## Architecture and boundaries

Chrome UI -> authenticated FastAPI API -> shared typed router -> domain services and durable database jobs. PostgreSQL/pgvector holds users, job state, career records, campaigns, research, memory and provenance. Local nomic embeddings support retrieval and graph coordinates; the visualization is not a literal display of every vector dimension.

Voice remains local Parakeet realtime EOU/Silero with selective Whisper verification, Qwen3:8b dialogue and Kokoro output. Browser and physical microphone performance needs real audio acceptance tests. Hermes is an isolated research-only worker, not unrestricted desktop access. Windows desktop companion is a separate authenticated service.

ComfyUI runs locally from the installed Windows portable runtime. RAVEN queues workflows, checks history and proxies generated files without exposing provider credentials. `start-raven.ps1` starts it and the desktop bridge before Docker.

Research uses SearXNG/public page extraction -> evidence map -> synthesis -> audit/quality checks -> report, findings and searchable chunks. Remote free-model quotas and factual quality remain constraints. Mechanical/model review is not independent fact verification.

## Evidence

- 1,036 Python regression tests passed on the final deployed image.
- Headless real Chrome: six station destinations, Career tabs, Content tabs, desktop/mobile rendering, no page errors.
- API integration: synthetic campaign persistence/rename/duplicate/delete, real research cancellation and world state, Hermes connectivity, typed voice-channel UI actions.
- Actual ComfyUI image generated, artifact returned HTTP 200 image/png (686,100 bytes), and Chrome decoded and displayed it in Content Studio. Asset: 18c5a770-2aaf-4f13-b093-d0a1d09469c7. Screenshot: tests/world-live-comfyui.png.
- Previously truncated `egyptian cats` research was retried and completed as an audited 10,156-character report: 19,508 input / 8,154 output tokens at $0. Project: 98cc3c83-ce9e-47db-bb82-e123194e3385.
- Canonical startup acceptance: ComfyUI ready; authenticated Windows bridge v1.8 reachable from the Raven container; Steam, Discord, Chrome, Epic, Apex, Spotify, ChatGPT and YouTube detected; all six Docker services healthy.
- Hermes acceptance: isolated worker returned enabled `web_search` and `web_extract`; live Silero query returned the official repository through Hermes. No MCP server is currently configured, so no MCP server is claimed connected.
- Actual free-model research completed: 27433740-5f4e-4f82-a556-5b10d179a116, 11 sources, 3 structured findings, 17,409 input / 7,506 output tokens. Report downloaded successfully. Manual review found unsupported/generalized prose; stricter evidence instructions were added afterward, not yet independently benchmarked.
- Image/video workflow readiness checks pass. A new video render was NOT executed in this pass.
- Only synthetic campaign test records were deleted; existing user records and ComfyUI output files were preserved.

## Remaining, in priority order

Forge was added on September 10 as a first-class engineering workspace. Its PostgreSQL controller, Hermes runtime boundary, local/OpenRouter/NVIDIA provider routes, persistent events/artifacts, Git-aware diff capture, job controls and UI are implemented. Core syntax and Compose configuration are verified; the newly added Forge path tests and a real provider-backed engineering job still require execution on the rebuilt stack. See [Forge architecture](../FORGE_ARCHITECTURE.md). Codex remains intentionally disabled and optional.

1. Real microphone acceptance recordings: duplicate/stale turns, interruptions, proper names, research-under-load p50/p95 latency. Current pass does not prove these fixed.
2. Research quality benchmark: official-source coverage, citation entailment, numerical claims, freshness and answer relevance. The pipeline completes; expert-quality answers are not guaranteed. Improve dynamic query planning beyond the current template.
3. Career: live discovery relevance validation and grounded tailoring against the owner's complete factual profile. Universal unattended application is NOT implemented. Provider-specific adapters, credentials and target-specific approval/confirmation remain necessary; never bypass CAPTCHA or invent answers.
4. Content: automated scheduling, richer caption variants, uploads/media-library organization and live approved publishing require further work. Image generation is verified; video and external publishing still need end-to-end acceptance.
5. Hermes: add the chosen MCP server definitions and their server-side authentication variables, then use the built-in handshake/discovery test. Additional toolsets remain permission-gated; installed skills are not callable by default.
6. Graph: typed entity/category extraction, relation editing and semantic-cluster quality tests; verify visible voice zoom/filter/edit acknowledgements.
7. Desktop/Spotify: recheck companion startup, foreground/close operations and authorized playback using the real device. No new music or external application actions were run in this pass.
8. Production: load/concurrency, backup/restore, secret rotation, durable retry/idempotency, full security review and deployment hardening. Do not expose this localhost demo directly to the Internet.

## Reproduce checks

From the raven folder: `docker compose exec -T -e PYTHONPATH=/app raven pytest -q -p no:cacheprovider`.
Browser/API scripts: tests/e2e_world.cjs and tests/e2e_product_api.cjs (the latter creates/deletes synthetic campaigns and leaves cancelled research audit fixtures).
Do not restart the app during a research acceptance run; interrupted jobs intentionally fail instead of silently claiming completion.
