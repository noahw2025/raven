# RAVEN requirements and readiness

Updated: 2026-09-05. Scores use: 0 absent, 1 design, 2 foundation, 3 functional, 4 locally verified, 5 production-proven in the stated deployment.

Operational note: the refined stack and full local acceptance suite were verified online on 2026-09-03. Docker Desktop, five Docker services, ComfyUI, and the authenticated Windows desktop companion are running. See [PROJECT_STATUS_2026-09-03.md](PROJECT_STATUS_2026-09-03.md) for the implementation handoff.

| Area | Score | Verified now | Remaining production gate |
|---|---:|---|---|
| Text conversation | 4/5 | Local Qwen, correction-aware routing, capability-vs-command grammar, project follow-ups, truthful provenance, bounded RAG, exact usage telemetry | Long-session and adversarial dialogue evaluation |
| Voice conversation | 4/5 | Streaming Parakeet Realtime EOU 120M on CUDA, Silero VAD, Whisper Turbo command verification, contextual entity correction, Chrome PCM WebSocket, ARISE, sentence-streamed Kokoro, barge-in, and the shared deterministic router; synthetic full-path test and 969 regressions pass | Physical Chrome microphone acceptance and real-room echo/noise/interrupt soak |
| Memory and knowledge | 4/5 | Explicit-evidence admission, deterministic thresholds, local embeddings, HNSW vector retrieval + PostgreSQL exact-term ranking + 76/24 hybrid fusion, review/edit/exclude/delete, spaced 3D graph | Contradiction/supersession UX and corpus-scale retrieval evaluation |
| Current web and deep research | 4/5 | Weather, market, SearXNG, YouTube, durable multi-query research, evidence-led second-stage searches, answer-first synthesis, citation audit and coverage repair, quality gate, follow-up RAG, visible model/token/cost telemetry; live 20-source acceptance passed | Scheduled monitoring cache and broader provider-failure chaos suite |

Deep Research uses private local search and bounded server-side page retrieval. In `auto` mode, a configured server-only OpenAI key selects `gpt-5.6-terra` for evidence mapping, narrative synthesis, and audit, with a default $0.25 project cap; otherwise the same stages fall back to the local content model. A snippet/link fallback can never be marked complete. Reports must meet minimum detail, findings, organization, citation-diversity, and citation-validity gates. Failed evidence is retained for an explicit retry.
| Agent runtime | 3/5 | Durable runs, ordered steps, budgets, approvals, audit, cancel, voice mission creation/status | Typed Hermes/external executors, idempotency proof, restart/load benchmark |
| Career preparation | 4/5 | Separate public LinkedIn and official Greenhouse/Lever/Ashby discovery, strict job-detail filtering, role-fit scoring, factual resume/cover letter/answers, PDF/DOCX, approval ledger | Supervised browser adapter with real confirmation evidence; no authenticated LinkedIn scraping |
| Social content | 4/5 | Campaign ledger, local copy generation, visible generation gates, installed SDXL image and Wan 2.1 video workflows, version-hashed ComfyUI queue/history/artifact adapter, approval objects, server-only provider contracts | Instagram/X/YouTube OAuth, sandbox publish and analytics evidence |
| Desktop/home | 4/5 | Loopback-only authenticated companion; fixed Steam/Spotify/ChatGPT/Discord/Apex allowlist; Spotify search and transport grammar; named Discord aliases; arbitrary paths and shell rejected | Owner Spotify Premium OAuth for confirmed playback, Discord alias IDs, token revocation UI, startup persistence, and multi-device audit |
| Security/privacy | 4/5 | Localhost binding, non-root/read-only containers, internal DB, CSP/headers, origin guard, throttling, server-only secrets, fail-closed external actions | Independent ASVS review, encrypted backup/restore drill, container/image scanning |
| Observability/cost | 4/5 | Per-call model, provider, input/output tokens, cost, latency, context manifest, tool/source provenance | Time-series alerts, capacity SLOs, retention policy |

Overall: **38/50 (76%) production readiness across the full vision**. The local demonstration core is substantially stronger than the full-product score. OAuth providers, browser/device acceptance, and consequential external side effects cannot be truthfully certified without the owner's accounts and supervised acceptance tests.

## Voice agent command contract

The voice transcript enters the same deterministic router as text. Capability questions never authorize execution: “Can you open Steam?” reports readiness, while “Open Steam” executes the fixed allowlist action. Deep Research uses the same distinction and keeps “what is it?”, “what did we find?”, and provenance questions attached to the current project. Explicit commands can navigate the UI, search live sources, open allowlisted desktop apps, discover YouTube videos, start durable research/social/career/market/general missions, and report status. A model never receives permission to invent an external action: social publishing, ATS submission, brokerage, and Hermes execution stop unless a typed executor exists and the target-specific approval is valid.

Examples:

- “Raven, start a deep research mission on current Instagram publishing requirements.”
- “Raven, start a career search mission for remote SaaS sales roles.”
- “Raven, what is my latest mission doing?”
- “Raven, find videos on local AI agents on YouTube.”
- “Raven, open Discord.”
- “Raven, open Spotify.”
- “Raven, play Midnight City by M83 on Spotify.”
- “Raven, open ChatGPT.”
- “Raven, join Discord channel general.” (after the `general` alias is configured server-side)

## Blocked by external setup

These are not incomplete local code disguised as finished integrations: Meta/Instagram authorization, X authorization, YouTube publishing OAuth, supervised ATS browser adapter, authenticated Hermes worker, Home Assistant, CRM/email/calendar, and any brokerage sandbox/live account. Each requires credentials, an owner-selected account, provider policy acceptance, or host installation. ComfyUI model/workflow installation is complete locally.
