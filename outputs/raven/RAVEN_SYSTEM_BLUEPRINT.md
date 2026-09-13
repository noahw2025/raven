# RAVEN system blueprint — iteration 3

Status date: 2026-09-02. This describes the last locally verified build and distinguishes verified behavior from connectors that are only architected. Docker Desktop was not running during the 2026-09-02 audit, so the application was offline; see `docs/PROJECT_STATUS_2026-09-02.md`.

## Current outcome

RAVEN is a Dockerized, local-first personal intelligence environment with unified text and turn-based voice, structured semantic memory, private RAG, live web lookup, an inspectable 3D knowledge map, durable mission records, approvals, audit history, and per-call model telemetry. A loopback-only authenticated Windows companion can open a fixed application allowlist; RAVEN is not yet an unattended social, email, smart-home, or brokerage operator because those authenticated gateways are not connected.

## Runtime and models

| Function | Service | Model/runtime | Where it runs | API cost |
|---|---|---|---|---:|
| Text reasoning | Ollama | `qwen3:8b` | local GPU container | $0 |
| Spoken reasoning | Ollama | `qwen3:8b` | local GPU container, no-think mode | $0 |
| Memory curation | Ollama | `qwen3:8b` | local GPU container | $0 |
| Verified factual rendering | RAVEN policy | deterministic weather/market response | server-side | $0 |
| Embeddings | Ollama | `nomic-embed-text`, 768 dimensions | local container, pinned | $0 |
| Speech recognition | Faster-Whisper | `base.en`, CPU int8 | isolated voice container | $0 |
| Speech synthesis | Kokoro ONNX | 82M, `af_heart` | isolated voice container | $0 |
| General live search | SearXNG | metasearch JSON | local container with outbound search | $0 |
| Point-in-time market quotes | read-only feed | requested ticker | backend only | $0 |
| Deep Research quality tier | OpenAI | `gpt-5.6-terra` in auto mode, local Qwen fallback | backend only, $0.25/project default cap | provider rate |

The browser never receives an OpenAI key, Ollama credential, database password, session signing secret, or connector token. `.env` is read by Docker services; static files contain no secrets.

## Request flow

1. Chrome captures a turn with echo cancellation, noise suppression, and automatic gain control.
2. Adaptive energy detection estimates the room noise floor and combines voiced frames, duration, transcription confidence, and no-speech probability before ending a turn; the current patient endpoint window is approximately 1.15 seconds.
3. The audio buffer is sent only to the local RAVEN backend, proxied to Faster-Whisper, transcribed, and immediately discarded.
4. The chat router embeds the transcript, applies owner/archive/exclusion filters in SQL, retrieves a bounded set of memories and chunks, and optionally calls live search for current-data intent.
5. `qwen3:8b` produces general text and short spoken responses in no-think voice mode. Deep Research can use server-side `gpt-5.6-terra` for evidence mapping, synthesis, and audit when configured, with local Qwen as fallback.
6. Kokoro synthesizes the bounded spoken answer locally; interruption and visible voice-state controls remain active during playback.
7. Microphone energy during playback can interrupt after three sustained frames; the visible Interrupt button is a deterministic fallback.
8. The same conversation and message tables store voice and text turns. Raw audio is never stored.

## ARISE wake phrase

ARISE automatically arms while the RAVEN page is open when microphone permission has already been granted. Overlapping 2.4-second windows are sent to the local Faster-Whisper service with `ARISE Raven` as hot words. A recognized whole-word `ARISE` opens the voice session and speaks, “Good day, Noah. What can I help you with today?” Ending the session returns to wake listening unless ARISE is switched off. The first browser microphone approval still requires a user gesture. This is intentionally labeled **browser-active**, not OS-level always-on.

## Memory admission: how RAVEN decides

Memory creation is a two-stage decision, not keyword matching:

1. The local Qwen curator may propose up to four explicit durable facts, preferences, relationships, goals, decisions, corrections, or standing instructions. Each proposal includes an exact quote and independent confidence, future-utility, durability, specificity, importance, sensitivity, and rationale fields.
2. Deterministic server gates make the final decision. A candidate needs confidence ≥ 0.82, future utility ≥ 0.72, durability ≥ 0.72, specificity ≥ 0.65, importance ≥ 3/5, an exact verbatim user quote, and no credential/secret pattern. Similarity ≥ 0.92 consolidates it as a duplicate. Sensitive candidates or confidence below 0.86 go to review.

Every outcome—saved, review, duplicate, rejected, or no candidate—is recorded in `memory_decisions`. The Memory Vault shows the candidate, reason code, all four scores, and evidence. Confidence is the curator's estimate that the user explicitly stated the fact. Vector similarity is a separate retrieval/duplicate score and never decides truth.

## RAG, vectors, and the graph

- PostgreSQL 16 is the canonical database; pgvector provides cosine distance and HNSW indexes. PostgreSQL full-text ranking supplies exact-term evidence, and retrieval fuses 76% vector meaning with 24% lexical relevance before applying the context limit.
- `nomic-embed-text` generates 768-dimensional vectors locally. Embeddings stay server-side and are omitted by response serialization.
- Retrieval is filtered by `user_id`, `archived`, and `excluded` before ranking and then clipped by chunk count and character limit.
- The Knowledge Graph includes memories, documents, goals, tasks, and the live embedding-model node.
- Canonical relationships and goal/task membership are visually distinct from vector-inferred similarity and `embedded_by` edges.
- The UI supports perspective 3D rotation, fly zoom, 2D mode, list mode, type filtering, search, inspection, active-memory glow, and two-hop local expansion.

## Database map

| Area | Tables | Purpose |
|---|---|---|
| Identity/conversation | `users`, `conversations`, `messages` | owner scope and unified history |
| Memory/RAG | `memories`, `memory_decisions`, `memory_usage`, `documents`, `chunks`, `citations`, `memory_relations` | admission, provenance, vectors, retrieval, graph |
| Work | `goals`, `tasks`, `runs`, `run_steps`, `run_events` | durable objectives and multi-step execution state |
| Authority | `approvals`, `audit`, `notifications` | explicit decisions and traceability |
| Operations | `tools`, `integrations`, `model_usage` | truthful readiness, data sent, tokens, latency, cost |

## Observability

Each model call persists provider, model, channel, purpose, input/output/audio tokens, cost, total latency, prompt/response characters, bounded context manifest, retrieval count, search use, and stage timings. The dashboard shows 24-hour totals and the last prompt. Toolchain → Model + Cost exposes individual records. Voice shows STT, model, TTS, token, and cost telemetry after each turn.

## Security boundary

- Web binds to `127.0.0.1:8080`; PostgreSQL has no host port.
- The localhost-only single-owner build opens without an entry passkey. Optional `RAVEN_REQUIRE_LOGIN=true` mode uses an HttpOnly, SameSite=Strict cookie. Production LAN/internet exposure still requires TLS, real identity, rate limits, encrypted backups, and a reverse proxy.
- Database access is tenant-scoped before vector ranking.
- Files and audio are processed without raw retention.
- Brokerage execution is blocked. Consequential connector writes require an approval record with target, reason, payload summary, reversibility, expiry, and audit trail.

## Last verified measurements

The latest complete measurements are from the 2026-08-09 acceptance run; Docker was offline during the 2026-09-02 audit.

- 25 unit tests passed, followed by dialogue, security/connectedness, and explicit voice end-to-end suites.
- Voice E2E: exact `ARISE Raven, can you hear me?` transcription; STT 704 ms; Kokoro TTS 671 ms; date/provenance/conversation-continuity checks passed.
- Current tools: weather 1,191 ms, market quote 171 ms, three current web results, five verified YouTube results, and safe YouTube open passed.
- Dialogue/tool suite: capability-versus-command behavior, research continuity, provenance, Career Center truth, and authenticated Steam/Spotify/ChatGPT/Discord/Apex launches passed. Spotify playback is separately verified through OAuth and never conflated with opening a search.
- The final voice suite returned 57 knowledge-graph nodes.
- A general local text turn measured 52,774 ms in that hardware state, so conversational model latency remains a priority even though deterministic tool replies were single-digit milliseconds.

### Earlier iteration measurements (historical)

- Five services healthy: RAVEN, PostgreSQL/pgvector, Ollama, SearXNG, voice.
- Synthetic Kokoro → Faster-Whisper ARISE loop: exact wake phrase, 611 ms STT, detection true.
- Voice greeting: Qwen2.5 3B 781–880 ms; Kokoro 878–943 ms; 270 tokens; $0 API cost.
- Estimated post-pause first audio: about 2.36 seconds; about 2.97 seconds including the measured synthetic STT pass.
- Live Google/Alphabet test: three SearXNG results plus a point-in-time quote in 1.32 seconds.
- Browser UI: dashboard telemetry, 17 graph nodes, 60 relationships, embedding node, 3D/2D/list modes, six memory decisions, and zero console errors.
- Automated local E2E: health, authentication, voice model, TTS audio, wake phrase, interruption thresholds, web search, graph metadata, tokens, and latency passed.

## Production gaps and next gates

1. Train and evaluate a dedicated ARISE keyword model for OS/tray operation; the current phrase spotter is browser-active.
2. Add streaming ASR and streaming/overlapped TTS to reduce time-to-first-audio below 1.5 seconds on this hardware.
3. Run real-room false accept/reject, echo, barge-in, and long-session tests with the owner's microphone and speakers.
4. Implement authenticated, allowlisted Hermes/desktop, email/calendar, CRM, social, and Home Assistant adapters one at a time with read-only scopes first.
5. Add idempotent mission checkpoints, retry policy, artifact handoff, scheduled monitoring, and connector-level cost/quota telemetry.
6. Keep trading at research/paper-trading stage until independent security and financial controls are complete.

## Key code locations

## Iteration 5 addendum — current intelligence and executable voice

- The server clock in `RAVEN_TIMEZONE` is authoritative; date/time requests never depend on model training data.
- Every model context receives the current server ISO timestamp. Current weather, market, and web requests route to live tools before generation and record actual provenance.
- Voice sessions reuse the most recent six-hour conversation and recover from transient turn failures without closing. Noise admission now combines voiced-frame count, duration, STT confidence, and no-speech probability; barge-in requires six sustained frames.
- `research_projects`, `research_queries`, `research_sources`, `research_findings`, and `research_events` implement durable Deep Research. A worker plans 6/9/12 diverse searches, retrieves bounded public HTML with SSRF controls, extracts fact-dense evidence cards, builds an evidence map, writes an answer-first report, audits citations, and invokes one bounded repair pass only when the quality gate rejects the draft. Completed reports are chunked into the private vector index so text or voice can ask follow-up questions without searching again. Failures are typed, preserve evidence, and are retryable.
- Research Lab exposes phase, queries, sources, findings, confidence, tokens, local/API cost, errors, retry, and Markdown download.
- Deterministic voice UI actions can open the dashboard, chat, memory, graph, Research Lab, Social Studio, Career Center, tools, roadmap, missions, goals, cost/model activity, Trust Center, and settings without model inference.
- The shared dialogue router separates questions from commands, resolves follow-ups against the active research/tool context, and reads recorded model/tool provenance when the owner asks where the previous answer came from. This prevents capability descriptions from becoming accidental actions and prevents generic RAG answers from masquerading as Deep Research results.
- Social Studio uses a provider-neutral campaign record for Instagram, X, and YouTube. Instagram and X publishing are server-credentialed and approval-gated. YouTube has a server-only OAuth readiness contract; resumable upload remains a declared gap.
- `qwen3:8b` remains the resident model for conversation, voice reasoning, memory curation, and an offline Deep Research fallback. Deep Research can use server-side `gpt-5.6-terra` in `auto` mode for substantially stronger synthesis while local SearXNG still performs discovery and the browser never receives a credential. The default research budget is $0.25 per project and actual provider, model, tokens, and cost are visible. `nomic-embed-text` remains the free local 768-dimensional vector model; Ollama keeps both local models resident.

The iteration-specific acceptance table and remaining gates are in `ITERATION_5_PRODUCT_REQUIREMENTS.md`.

- `app/main.py`: API, retrieval, memory admission, graph, telemetry, search routing.
- `app/ai.py`: local/OpenAI provider abstraction, prompting, embeddings, web/market context.
- `app/db.py`: schema, indexes, truthful capability registry.
- `voice_service/service.py`: Faster-Whisper and Kokoro service.
- `app/static/app.js`, `voice_logic.js`, `ops.css`: UI, voice state machine, wake control, dashboard, knowledge map.
- `tests/e2e_voice.cjs`: repeatable local E2E suite.
