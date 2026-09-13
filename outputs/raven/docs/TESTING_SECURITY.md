# RAVEN testing and security

## Threat boundary

RAVEN is a single-owner localhost application. PostgreSQL has no host port; the web service binds to `127.0.0.1`; application and voice containers run non-root, read-only, without Linux capabilities; API secrets stay in the server container and are never returned by tool endpoints. This is not an authorization to expose port 8080 to a LAN or the public internet.

Browser protections include same-origin mutation checks, optional HttpOnly/SameSite login, login throttling, CSP, clickjacking denial, MIME sniffing prevention, no-referrer policy, bounded browser permissions, no-store API responses, and HSTS when HTTPS is actually used. The application trusts forwarded headers only from localhost.

Agent protections include explicit command shapes, fixed desktop allowlists, bounded context, target-specific expiring approvals, cost budgets, durable audit events, and fail-closed behavior when a consequential workflow has no typed executor. A registry label such as “connected” never authorizes a generic LLM to simulate a write.

## Verification commands

```powershell
cd outputs\raven
docker compose up -d --build
docker compose ps
docker compose exec -T -e PYTHONPATH=/app raven pytest -q -p no:cacheprovider
$node="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
& $node tests\security_connectedness.cjs
& $node tests\e2e_voice.cjs
& $node tests\e2e_tool_dialogue.cjs
& $node tests\e2e_media_commands.cjs
& $node tests\e2e_hybrid_memory.cjs
& $node tests\e2e_comfyui_media.cjs
& $node tests\e2e_career.cjs
& $node tests\e2e_research.cjs
```

The security/connectedness suite verifies response headers, cross-origin mutation rejection, static path traversal rejection, a secret-free tool API, local voice/deep-research registry health, and a real voice-routed mission whose consequential social step remains approval-gated. The research acceptance test requires live sources, explainable quality tiers, citations, findings, and non-zero local synthesis tokens; an extractive fallback alone does not pass.

The ComfyUI acceptance suite is intentionally separate because it performs real
GPU work. It generates one SDXL PNG and one Wan WebM through RAVEN, polls the
audited queue, retrieves both through the authenticated artifact proxy, and
checks their media types and non-empty bytes.

## Latest acceptance record — 2026-09-03

The full local acceptance pass completed successfully after the startup probe was corrected and Docker Desktop was restarted:

- Containerized unit suite: 28 passed.
- Security/connectedness: headers, origin guard, traversal guard, secret-free tool API, and approval-gated voice mission passed.
- Voice: Faster-Whisper, Kokoro, ARISE, dialogue continuity, current date, provenance, YouTube, weather, market, Deep Research creation, and graph metadata passed.
- Tool dialogue, media commands, UI refinement, Career, and hybrid-memory suites passed.
- Desktop/media regression: exact transcript variants (`OpenSpotify`, track requests without “on Spotify,” negative playback corrections, trailing `open Steam`, YouTube question-shaped commands, retry language, and a bounded three-step command) passed. Companion v1.4 verified Chrome dispatch only to an internally constructed YouTube URL and the live `r5apex_dx12.exe` process; Spotify exact-search and Windows next/previous controls passed without allowing an unverified playback claim.
- Deep Research: 20 sources, 8 findings, audited citation quality, 16,618 input tokens, 4,295 output tokens, and a grounded 952-character follow-up passed using local `qwen3:8b` at $0 API cost.
- ComfyUI: a 504,103-byte SDXL PNG and 69,217-byte Wan 2.1 WebM passed queue, generation, proxy retrieval, media-type, and non-empty artifact verification.

The first research run correctly failed its quality gate because a detailed eight-source report cited only three distinct sources. Synthesis now requires explicit evidence diversity and adds one bounded evidence-coverage repair pass; a clean rerun passed. The research harness can also resume an existing project by setting `RAVEN_RESEARCH_PROJECT_ID`, avoiding duplicate work after a client-side timeout.

## Production acceptance still required

Before any non-local deployment: complete an OWASP ASVS 5.0 review, scan images and dependencies, move production secrets to Docker/host secret mounts, enable TLS and real identity, encrypt and restore-test backups, define retention, run concurrent load and restart/chaos tests, and conduct a real-device Chrome microphone matrix. External adapters need sandbox tests for approval expiry, duplicate suppression/idempotency, partial failure, provider rate limits, confirmation evidence, and revocation.
