# RAVEN

RAVEN is a Dockerized, local-first personal intelligence environment: private text and voice conversation, selective hybrid semantic/lexical memory, PostgreSQL/pgvector RAG, live web research, a three-dimensional knowledge map, mission state, approvals, audit, and exact token/latency/cost insight.

Start with the canonical [documentation map](docs/README.md), [current project status](docs/PROJECT_STATUS_2026-09-03.md), [requirements/readiness matrix](docs/REQUIREMENTS_AND_READINESS.md), and [testing/security runbook](docs/TESTING_SECURITY.md). The detailed architecture, models, APIs, memory decision flow, and database map remain in [RAVEN_SYSTEM_BLUEPRINT.md](RAVEN_SYSTEM_BLUEPRINT.md).

## Run on Windows

Docker supplies Python 3.11 for RAVEN and Python 3.12 for the isolated voice service; no host Python install is required.

```powershell
cd outputs\raven
.\start-raven.ps1
docker compose ps
```

`start-raven.ps1` is the canonical launcher. It starts ComfyUI and the authenticated
Windows desktop companion first, writes the bridge configuration, and only then
starts Docker. `docker compose up` alone cannot create a Windows host process from
inside a Linux container. See `comfyui/README.md` for the installed image and video workflows.

Spotify opens, exact searches, and Windows next/previous media controls work through the authenticated desktop companion. For confirmed exact-track playback, pause/resume, volume, and now-playing, create a Spotify developer app with `http://127.0.0.1:8766/callback` as its redirect URI and run `.\setup-spotify.ps1`. The helper performs the owner authorization locally, stores the client secret and refresh token only in the server environment, and never sends either value to the RAVEN frontend. Spotify's Player API requires an active Premium device.

Open <http://localhost:8080> in Chrome. The single-owner localhost build opens directly without an entry passkey. Set `RAVEN_REQUIRE_LOGIN=true` only if you intentionally want to restore the password screen.

To open in VS Code from the repository root:

```powershell
code outputs\raven
```

## Forge engineering workspace

**Forge** is the persistent RAVEN → Hermes software-engineering workspace. It can register a repository-relative project, create durable jobs, select local/OpenRouter/NVIDIA execution, expose structured progress, preserve messages across refreshes, and capture plans, logs, tests and Git diffs. Codex is optional and is not used by the default path.

Put `OPENROUTER_API_KEY` and/or `NVIDIA_API_KEY` only in `.env`; leave `.env.example` blank and committed as documentation. Restart with `./start-raven.ps1`, open **Forge**, and choose an available provider. See [FORGE_ARCHITECTURE.md](FORGE_ARCHITECTURE.md) for the security boundary, current limitations and first end-to-end test.

## Local stack

- Text/deep reasoning, spoken replies, and memory curation: Ollama `qwen3:8b` on the local GPU
- Deterministic dialogue/tool policy: zero-token greetings, clarification, weather, and market rendering
- Embeddings: local `nomic-embed-text`, 768 dimensions
- RAG database: PostgreSQL 16 + pgvector HNSW cosine indexes + PostgreSQL full-text ranking, fused 76/24 for semantic meaning and exact terms
- Speech-to-text: Faster-Whisper `base.en`, CPU int8
- Text-to-speech: Kokoro ONNX 82M, `af_heart`
- Search: self-hosted SearXNG plus a read-only point-in-time market quote route
- Deep research model chain: configured free OpenRouter model, optional NVIDIA NIM
  endpoint, then local Ollama; provider failures and truncation never authorize a paid route
- Wake phrase: **ARISE**, browser-active and local-only when armed
- Social content: provider-neutral local campaign strategy/captions with a Postgres evidence ledger
- Media adapter: ComfyUI workflow queue/history/artifact adapter with server-side workflow hashing and visible generation gates
- Publishing adapter: approval-gated Instagram Professional API with server-only credentials
- Career Center: current hiring research, targeted resume and cover-letter generation, grounded application answers, approvals, downloads, and submission evidence

All of these local model paths have $0 API charges. Electricity and hardware time remain real costs. OpenAI is an optional backend fallback; its key never reaches browser code.

## Voice behavior

RAVEN automatically arms **ARISE** when the page loads and microphone permission has already been granted. Say “ARISE” and RAVEN answers, “Good day, Noah. What can I help you with today?” The first browser permission still requires one click on ARISE because browsers do not permit sites to bypass microphone approval. Adaptive room-noise calibration uses a patient 2.1–2.6 second endpoint window so natural pauses do not end the turn prematurely. Kokoro renders at 1.27x speed, trims trailing silence to about 70 ms, and prefetches sentence audio while preserving playback order. Speaking over output or pressing **Interrupt** immediately returns to listening. Ending a conversation returns to ARISE listening unless you switch ARISE off.

ARISE is not yet an OS-level always-on wake service. That requires a trained custom wake model and a native tray/home gateway.

## Security

- Secrets are Docker environment variables and are never compiled into `app/static`.
- The site binds to `127.0.0.1`; PostgreSQL has no host port.
- The default single-owner localhost mode has no entry passkey. Optional login mode uses HttpOnly, SameSite=Strict cookies.
- Retrieval is owner-filtered before vector ranking and clipped by chunk/character limits.
- Raw uploads and microphone audio are not retained.
- External writes require explicit approval; brokerage execution remains blocked.
- Social access tokens remain server-side; the Social Studio contains no credential input fields.
- Career browser-adapter credentials remain server-side; automatic submission is disabled until a supervised adapter is explicitly configured and enabled.

## Hermes and MCP

The Hermes page lists the tools actually enabled in the isolated worker. Its live
test executes `web_search`. MCP servers are supplied server-side through
`HERMES_MCP_SERVERS_JSON`; each configured connection exposes a **Test handshake +
discover tools** action that performs MCP `initialize` and `tools/list`. A server is
never labelled connected merely because it appears in configuration. Keep MCP
authentication values in separate environment variables referenced by `header_env`.
For the first bearer-authenticated server, use `header_env` set to
`HERMES_MCP_AUTH_TOKEN`; Docker passes that variable only to the Hermes worker.

Do not expose port 8080 beyond localhost without TLS, a real identity provider, rate limiting, encrypted backups, and a reverse proxy.

## Tests

```powershell
docker compose ps
node tests\e2e_voice.cjs
node tests\security_connectedness.cjs
node tests\e2e_career.cjs
node tests\e2e_research.cjs
```

The E2E suite verifies authentication, local model identity, token/latency telemetry, Kokoro audio, ARISE phrase logic, interruption thresholds, live web data, and graph metadata. Real-room microphone, speaker echo, false-wake, and long-session tests must still be performed on the owner's Chrome/device combination.

## Data persistence

PostgreSQL data stays in the named Docker volume. `docker compose down` stops services without deleting it. Do not use `docker compose down -v` unless permanent deletion is explicitly intended.
