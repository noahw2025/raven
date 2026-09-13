# RAVEN project status and implementation handoff

Status date: 2026-09-02. This is the current handoff for beginning the next tooling and task implementation phase.

## Executive status

RAVEN is a substantial local-first foundation, not yet a finished autonomous operator. The locally demonstrated core covers unified text and voice, semantic memory, private RAG, current web tools, durable Deep Research, a visual knowledge graph, missions and approvals, career-material generation, tool/cost telemetry, and an authenticated fixed-allowlist Windows launcher.

The current verified pass completed 26 unit tests plus live capability, security/connectedness, voice, and media-command suites. It verified capability-versus-command routing, research continuity, YouTube discovery/open, local STT/TTS and ARISE, hybrid memory contracts, and real allowlisted launches for Steam, Spotify, ChatGPT, Discord, and Apex Legends.

Current operational state: **online and healthy at `http://localhost:8080`**. PostgreSQL/pgvector, Ollama, SearXNG, RAVEN, and the local voice service are running in Docker; the authenticated Windows desktop companion is connected on loopback.

Overall readiness remains approximately **76% across the full product vision**. The local demonstration core is stronger than that number; missing points are principally authenticated external connectors, reliable long-running execution, native wake operation, and production evaluation.

## What is implemented

| Capability | State | What works |
|---|---|---|
| Text dialogue | Locally verified | Qwen3 8B, bounded history/RAG, current-time truth, capability/command grammar, project follow-ups, provenance, token/cost/latency records |
| Voice dialogue | Locally verified | Browser microphone, Faster-Whisper, Kokoro, ARISE while the page is active, adaptive turn ending, interruption/barge-in logic, shared text/voice tool router |
| Semantic memory | Locally verified | Evidence-bound memory proposals, deterministic admission thresholds, review/reject/duplicate ledger, local embeddings, HNSW vector search plus PostgreSQL lexical ranking fused 76/24, edit/exclude/archive/delete |
| Knowledge graph | Functional/polished demo | Memories, documents, goals, tasks, inferred vector relations, model node, collision-aware Fibonacci 3D layout, smaller nodes, label plates, 3D/2D/list modes, filters and inspection |
| Current tools | Locally verified | Server date/time, Open-Meteo weather, point-in-time market quote, SearXNG web search, YouTube discovery and safe open |
| Deep Research | Locally verified | 6/9/12 focused searches, authoritative-domain targeting, safe page extraction, evidence cards, evidence map, answer-first synthesis, citation audit/repair, quality gate, saved follow-up RAG |
| Missions/runtime | Functional foundation | Durable runs and ordered steps, events, budgets, approval gates, cancellation, voice/text mission creation and status |
| Career Center | Locally verified preparation | Greenhouse/Lever/Ashby discovery, scoring, canonical candidate profile, targeted resume, cover letter, application answers, PDF/DOCX, immutable evidence/version ledger |
| Social Studio | Functional foundation | Campaigns, local text generation, visible brief/strategy/prompt/queue/generate/review/distribute gates, real ComfyUI queue/history/artifact adapter, draft/post/event ledgers, approval boundary, provider-neutral Instagram/X/YouTube contracts |
| Desktop applications | Connected and verified | Loopback-only authenticated Windows companion; fixed Steam, Discord, Chrome, Epic, Apex, Spotify, and ChatGPT actions; named Discord-channel resolver; arbitrary paths/shell commands rejected |
| Spotify | Launcher verified; playback setup optional | App launch and exact-song search work without API credentials. Confirmed playback refreshes owner OAuth, selects one verified track, and says “playing” only after Spotify confirms it |
| Trust/observability | Locally verified | Tools/readiness registry, approvals, audit events, per-call provider/model/tokens/cost/latency/context manifests, secret-free frontend APIs |

## Model and data architecture

| Function | Current choice | Cost/location |
|---|---|---|
| General text and voice reasoning | `qwen3:8b` through Ollama | Local, $0 API cost |
| Embeddings | `nomic-embed-text`, 768 dimensions | Local, $0 API cost |
| Speech recognition | Faster-Whisper `base.en`, CPU int8 | Local voice container |
| Speech synthesis | Kokoro ONNX 82M, `af_heart` | Local voice container |
| Search | Self-hosted SearXNG | Local service with outbound search |
| Deep Research synthesis/audit | `gpt-5.6-terra` when server OpenAI key is configured; local Qwen fallback | Server-only, default $0.25/project cap |
| Canonical storage | PostgreSQL 16 + pgvector | Internal Docker network and persistent volume |

Secrets remain in the ignored `.env`/server environment. The current configuration contains an OpenAI key and desktop-bridge token; neither value was read or exposed during this audit. Hermes is not configured. Social and YouTube publishing and the career-application adapter remain disabled and therefore fail closed. ComfyUI is locally configured without a cloud API key.

## What is not complete

1. **Hermes execution:** the mission ledger exists, but `HERMES_URL` and `HERMES_TOKEN` are not configured and real long-running computer/coding execution is not connected.
2. **Job submission:** job discovery and targeted materials work; the supervised Chrome/ATS form adapter is not deployed, so RAVEN cannot truthfully complete applications yet.
3. **Social publishing:** draft/campaign/approval infrastructure exists; Instagram, X, and YouTube OAuth/publishing adapters still need owner credentials and sandbox proof.
4. **Media generation environment:** complete locally. ComfyUI 0.34.0 runs on CUDA with SDXL 1.0 for images and Wan 2.1 T2V 1.3B for WebM video. Both workflows passed queue/history/artifact-proxy tests through RAVEN. Publishing generated media still requires the destination platform's OAuth and public-media hosting rules.
5. **Persistent desktop startup:** the expanded allowlisted bridge is connected, but it is not installed as a managed startup service with token rotation/revocation UX. Named Discord channels require `DISCORD_CHANNELS_JSON`; confirmed Spotify playback requires owner OAuth and an active Premium device.
6. **Native wake/home assistant:** ARISE is browser-active, not an OS-level always-on keyword service. Home Assistant, email, calendar, CRM, and notification connectors are unimplemented.
7. **Autonomy reliability:** missions still need idempotent executor checkpoints, retry/backoff policy, recovery after restart, schedules/monitors, quota handling, and artifact handoffs.
8. **Production validation:** no long-duration voice soak, real-room microphone matrix, concurrency/load benchmark, independent ASVS review, container/dependency scan, or encrypted backup/restore drill has been completed.
9. **Trading:** current quote/research is read-only. Paper trading is the next acceptable boundary; unattended live-money execution remains blocked.

## Recommended next implementation sequence

### Phase 1 — dependable task execution

- Connect Hermes through a typed authenticated adapter.
- Add idempotency keys, step checkpoints, retries/backoff, cancellation propagation, restart recovery, artifact records, and executor health telemetry.
- Add scheduled tasks/monitors and owner notifications.
- Acceptance gate: a multi-step research/coding mission survives a RAVEN restart, never duplicates a consequential step, and returns inspectable artifacts and costs.

### Phase 2 — Career Center submission pilot

- Deploy a supervised browser adapter for one ATS family first, preferably Greenhouse.
- Support deterministic field mapping, resume upload, unknown-question takeover, target-specific approval, duplicate prevention, and confirmation capture.
- Acceptance gate: three sandbox/test applications use the correct targeted resume, stop for unknown or sensitive questions, and record verifiable submission evidence.

### Phase 3 — social content pipeline

- Tune SDXL/Wan production presets and add typography/compositing after generation; the local generation engine and artifact ledger are connected.
- Configure one owner-selected platform in sandbox/developer mode, beginning with Instagram Professional or YouTube.
- Implement draft → asset → review → approval → publish → external ID/permalink → analytics flow.
- Acceptance gate: a test campaign produces versioned assets and captions, publishes only after approval, and ingests performance evidence without exposing credentials.

### Phase 4 — personal operations connectors

- Add email, calendar, CRM, and Home Assistant adapters with read-only scopes first.
- Promote each write operation separately after target-specific approval and idempotency tests.
- Acceptance gate: RAVEN can explain exactly what it read, what it plans to change, and what external evidence confirms the change.

## First-session checklist

1. Start Docker Desktop.
2. From `outputs\raven`, run `docker compose up -d --build`.
3. Run the test commands in `docs/TESTING_SECURITY.md` before making connector changes.
4. Confirm the Windows companion after a reboot with `start-desktop-bridge.ps1`.
5. Pick one next vertical slice. The recommended choice is **Hermes/runtime reliability first**, because every later autonomous tool benefits from the same checkpoints, approvals, retries, and artifact contracts.

## Source-of-truth documents

- `docs/PROJECT_STATUS_2026-09-02.md` — current implementation handoff.
- `docs/REQUIREMENTS_AND_READINESS.md` — scored readiness and remaining gates.
- `RAVEN_SYSTEM_BLUEPRINT.md` — architecture and runtime flow.
- `docs/TESTING_SECURITY.md` — repeatable verification and security boundary.
- `CAREER_AUTOPILOT_PRODUCTION_REPORT_2026-08-09.md` — Career Center implementation detail.
- `SOCIAL_DESKTOP_CAREER_ARCHITECTURE.md` — connector contracts and setup boundaries.
