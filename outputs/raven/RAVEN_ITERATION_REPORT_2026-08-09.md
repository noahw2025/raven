# RAVEN production iteration — 2026-08-09

## Outcome

This pass converts the supplied transcript into explicit product acceptance tests. RAVEN must not clip ordinary thinking pauses, navigate because a noun happened to appear in conversation, deny a capability already present in the database, claim an application launched without host evidence, or make the user wait for long research inside a voice turn.

## Architecture at this checkpoint

- UI: server-served HTML/CSS/JavaScript with a persistent docked voice link and inspectable tool, model, memory, research, career, mission, trust, and system views.
- API: FastAPI. Secrets are read only from server environment variables and are not returned to the browser.
- Durable state: PostgreSQL 16 with pgvector for conversations, memory decisions, documents/chunks, knowledge relations, research jobs, model usage, application packages, approvals, and audit events.
- Interactive reasoning: local Ollama/Qwen by default, with an optional OpenAI fallback. Current date/time is injected from the server.
- Retrieval: local nomic-embed-text vectors. Memory confidence is an admission score; cosine similarity is a separate retrieval score.
- Voice: Chrome microphone capture → adaptive client VAD → Faster-Whisper → bounded chat/tool routing → Qwen → sentence-streamed Kokoro. Raw audio is not retained.
- Current web data: SearXNG for general search, Open-Meteo for weather, and a point-in-time market quote adapter.
- Deep Research: persistent asynchronous plan → multi-query search → source extraction → synthesis → evidence audit → notification → report indexed back into pgvector.
- Long-running actions: the RAVEN mission ledger owns budgets, approvals, checkpoints, and evidence. Hermes remains a typed authenticated worker adapter.
- Windows applications: a separate authenticated host companion accepts only `steam`, `discord`, `chrome`, `epic`, and `apex`. It rejects paths, shell text, and arbitrary arguments.

## Five-pass requirement scorecard

Scores are evidence-based: 5 means implemented and covered by a direct test; 4 means functional with a real-world configuration or hardware check remaining; 3 means a working foundation; lower scores are not presented as complete.

| Requirement | Before | After | Evidence / remaining gate |
|---|---:|---:|---|
| Natural voice pause handling | 2/5 | 5/5 | Adaptive 2.1–2.6s silence window, 45s max turn, pure-function tests |
| User interruption / barge-in | 3/5 | 5/5 | 550ms playback grace and eight sustained speech frames; manual mic test still validates each room/device |
| Correct UI navigation | 2/5 | 5/5 | Explicit command grammar; transcript regression rejects incidental “tooling” language |
| Honest Resume Creator awareness | 2/5 | 5/5 | Direct answer reads the real capability contract; Career Center already produces versioned packages |
| Current UI awareness | 1/5 | 5/5 | Browser sends only the current page ID; server renders a truthful page label |
| Tool and integration clarity | 3/5 | 5/5 | Clickable architecture panel: runtime, models, flow, setup, voice commands, milestones, secret check |
| Agentic Deep Research | 3/5 | 4/5 | Durable phases, source ledger, events, completion handoff, report-to-RAG indexing; collaborative plan approval is next |
| Voice starts/reads research | 3/5 | 5/5 | Voice starts jobs and deterministically reports latest status/result without model guessing |
| Hermes harness integration | 3/5 | 3/5 | Mission/approval contract exists; an authenticated Hermes deployment URL/token is still required |
| Steam/Discord/Chrome/Epic/Apex launch | 1/5 | 4/5 | Secure host bridge and voice routing complete; enable it and verify installed apps on this Windows host |
| Arbitrary desktop control | 0/5 | 0/5 | Deliberately blocked; it would violate the allowlist security boundary |
| External Discord bot actions | 1/5 | 2/5 | Opening Discord is supported; server/channel actions require Discord OAuth/bot authorization and scoped commands |

## Improved requirements for the next iteration

1. Replace browser energy heuristics with streaming Silero VAD/ONNX probabilities and keep the adaptive semantic pause policy above it.
2. Record turn metrics: first-speech, end-of-speech, STT, first-token, first-audio, false-end recovery, and interruption precision.
3. Add a “continue my thought” recovery gesture and replayable, consented audio fixtures to the voice evaluation suite; never retain live microphone audio by default.
4. Add Deep Research plan review/approval for high-depth projects, gap-driven follow-up queries, source-quality rules by domain, contradiction clustering, and report follow-up threads.
5. Run the Windows host companion as a least-privilege scheduled task; sign the package; add token rotation, per-app policy toggles, and health evidence to Tools.
6. Connect Hermes only through typed task schemas with idempotency keys, bounded workspace scopes, retry/checkpoint evidence, and revocable credentials.
7. Connect Discord separately through OAuth/bot scopes. Opening the client and performing server actions must remain distinct capabilities.

## One-time local setup gates

- Desktop bridge: set the same 32+ character value in host `RAVEN_DESKTOP_BRIDGE_TOKEN` and Docker `DESKTOP_BRIDGE_TOKEN`, set `DESKTOP_BRIDGE_ENABLED=true`, run `start-desktop-bridge.ps1`, then restart RAVEN.
- Hermes: configure `HERMES_URL` and `HERMES_TOKEN` only after the worker is deployed and authenticated.
- Discord server actions: create a Discord application/bot, choose the minimum scopes, and add a separate connector. Never place its token in the frontend.

No API key, access token, password, or bearer secret belongs in this document or the browser.
