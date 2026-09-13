# RAVEN project status and implementation handoff

Status date: 2026-09-03.

## Executive state

RAVEN is a capable local-first assistant foundation, not yet a production-proven autonomous operator. The current pass materially improved voice pacing, memory selectivity, capability self-knowledge, desktop and Spotify command truthfulness, job discovery, research depth, and navigation clarity. The full-product readiness score remains **38/50 (76%)** because external accounts, consequential actions, long-duration reliability, and independent security/load validation remain real gates.

The full local stack is online and healthy at `http://localhost:8080`. Docker Desktop, PostgreSQL/pgvector, Ollama, SearXNG, RAVEN, the local voice service, ComfyUI, and the authenticated Windows desktop companion were started and exercised on 2026-09-03. `start-raven.ps1` now treats an offline Docker probe as recoverable, launches Docker Desktop, waits for the Linux engine, and then builds the stack.

## Implemented in this pass

| Area | Current implementation | Verified evidence |
|---|---|---|
| Voice | Patient 2.1–2.6 s adaptive endpointing; Kokoro 1.27x; approximately 70 ms tail trim; parallel sentence generation with ordered playback; shared text/voice router; one-sentence default with a hard two-sentence/44-word tool-response ceiling | Voice E2E passed local STT, TTS, ARISE, date/current-data tools, continuity, YouTube, weather, market, and telemetry |
| Capability awareness | Every model turn receives the database capability manifest and must distinguish `ready`, `setup_required`, and `blocked` | Tool dialogue and media-command routing tests |
| Spotify/desktop | Robust voice grammar, bounded two-to-four-step execution, exact-search fallback, Windows transport controls, official OAuth playback with automatic device selection, server-only credential storage, verified YouTube dispatch to Chrome, and process-verified Apex launch through Steam | Spotify OAuth and exact-track playback are live: Spotify confirmed “Good Morning” by Kanye West on the active device in 1.04 seconds; the strict host and multi-step E2E suites passed |
| Memory | Durable first-person language gate before LLM curation; tighter confidence, utility, durability, specificity, and importance thresholds; graph edit/delete controls | Core unit and refinement E2E passed transient rejection and graph mutation controls |
| Deep Research | Plan, parallel retrieval, evidence cards, gap/contradiction analysis, evidence-led second-stage queries, answer-first synthesis, citation audit/repair, citation-coverage repair, quality gate, and follow-up RAG | Live acceptance passed with 20 sources, 8 findings, 16,618 input tokens, 4,295 output tokens, audited quality, and a grounded follow-up |
| Career | Public LinkedIn job-detail discovery kept separate from official Greenhouse, Lever, and Ashby searches; strict job-link filtering; deduplication; normalized company/title; role-fit and freshness ordering | Career normalization unit passed; supervised external submission remains disabled |
| Product UI | Consolidated navigation; clearer Career subtabs; clickable memory editor/delete form; accurate voice timing and model telemetry | Refinement E2E passed |

## Verified test evidence

### Shared voice/text command chains

- Deployed up to eight ordered media/desktop/navigation commands per request. More than eight executes nothing and asks for a smaller batch.
- Supports `and`, `then`, `and then`, `after that`, `also`, commas, semicolons and sentence boundaries before command verbs; polite prefixes are normalized before splitting. Quoted titles and ordinary artist-name conjunctions remain intact.
- Discord commands inherit app context inside a chain: `open Discord and join general channel`. Only configured aliases dispatch channel links. Opening a link does not prove voice-channel membership, and RAVEN now explicitly avoids that claim.
- Unsupported later steps are reported rather than silently discarded. Voice summaries retain later-step failures instead of truncating after the first two sentences.
- 606 unit tests passed: 28 existing checks and 578 new command-variation/edge-case checks. Ten live text/voice requests verified equal execution summaries for Spotify, missing Discord aliases, page navigation, unsupported steps, and the maximum-step guard.
- Strict synthetic audio acceptance passed: “Open Spotify and then play Whitsand Bay by Metronomy” traversed TTS → STT → voice router → Windows app open → Spotify play → current-track readback → spoken response. Both opening and playback succeeded; execution took 1,266 ms.
- Restarted the Windows companion after a test correctly detected it offline. Automatic companion persistence and real-room microphone testing remain separate reliability gates.

### Voice recovery follow-up

- Fixed manual voice startup leaving ARISE capture running, duplicate microphone requests during startup, suspended AudioContext startup, interruption promises that never settled, stale session callbacks, and noise-floor calibration learning immediate speech as background noise.
- Nine local voice lifecycle checks cover playback completion/pause/error, immediate-speech calibration, noise rejection, duplicate starts, and cancelled microphone acquisition. These are mocked lifecycle tests, not room-acoustic acceptance.
- `node tests/e2e_voice_spotify.cjs` passed synthetic speech through real local TTS, STT, voice-channel chat, Spotify playback, current-track readback, and response TTS. STT returned “Whitson Bay by Matronomy”; Spotify confirmed “Whitsand Bay” by Metronomy was playing. Tool execution took 1,344 ms.
- Spotify title corrections now reach the executor; playback complaints no longer falsely report missing authorization. Liked Songs-only searches explicitly report the unavailable library integration rather than silently playing an unrelated catalog result. Liked Songs integration is still incomplete.
- Physical microphone, speaker echo, and Chrome barge-in testing remain unverified. Stop the old voice session and hard-refresh Chrome before testing the updated browser code.

- Core unit suite: 28 passed.
- Refinement E2E: voice speed, transient-memory rejection, graph edit/delete, and refined navigation passed.
- Media-command E2E: Spotify truthful fallback and transport grammar, ChatGPT, Discord, Apex, alias guard, YouTube discovery, verified YouTube-to-Chrome dispatch, and a three-step command passed.
- Voice E2E: local STT/TTS, ARISE, dialogue continuity, current date, source provenance, Deep Research creation, YouTube, weather, market, web results, and graph metadata passed.
- JavaScript syntax and Python compilation passed for changed files.
- Security/connectedness, Career, hybrid-memory, tool-dialogue, and real ComfyUI image/video suites passed.
- ComfyUI produced and verified a 504,103-byte SDXL PNG and a 69,217-byte Wan 2.1 WebM through RAVEN's artifact proxy.

Real microphone/speaker behavior still requires the owner's Chrome device test; browser automation could not access Chrome because the ChatGPT browser extension was unavailable. Long-duration voice soak, echo/noise/false-wake testing, concurrent load, restart recovery, and external provider sandboxes remain production gates.

## Honest setup state

| Connector | State | What is needed |
|---|---|---|
| Windows desktop bridge | Configured in environment | Keep companion running; add managed startup and token rotation before production |
| Spotify confirmed playback | Connected and live-verified | Keep the owner authorization valid and Spotify available on at least one Premium playback device; RAVEN automatically targets an available non-restricted device when none is active |
| Career submission | Not configured | Supervised browser adapter and per-application approval/confirmation evidence |
| Instagram/X/YouTube publishing | Setup required | Owner OAuth, provider review/policy acceptance, sandbox publish and analytics verification |
| Hermes worker | Setup required | Authenticated typed executor, idempotency, restart recovery, and audit evidence |
| Chrome automated acceptance | Blocked in this session | Install/enable the ChatGPT browser extension under Settings → Computer use, then rerun the visible UI/device acceptance |

Arbitrary desktop control is intentionally not a goal: RAVEN accepts only typed, allowlisted actions and rejects arbitrary paths and shell commands.

## Architecture decisions from current research

- Deep Research follows the planner/executor/synthesizer pattern used by [LangChain Open Deep Research](https://github.com/langchain-ai/open_deep_research) and [GPT Researcher](https://github.com/assafelovic/gpt-researcher), including bounded parallel collection and a reflection-driven follow-up pass.
- Voice turn handling follows the separation used by [Silero VAD](https://github.com/snakers4/silero-vad) and [LiveKit Agents](https://github.com/livekit/agents): speech detection, turn completion, interruption, transcription, reasoning, and synthesis are observable stages rather than one opaque request.
- Spotify playback uses the official [Start/Resume Playback API](https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback); RAVEN does not say a track is playing until Spotify confirms the write.
- Career discovery borrows the provider-normalization concept from [JobSpy](https://github.com/speedyapply/JobSpy), while avoiding authenticated LinkedIn scraping and keeping submission behind supervision.

## Next implementation sequence

### Completed follow-on: voice/background tool connections

See [VOICE_BACKGROUND_TOOLS.md](VOICE_BACKGROUND_TOOLS.md) for the implemented command catalog, queue architecture, safety boundaries and live evidence. Voice/text now launch real Career search and application preparation, Deep Research, Content drafts and saved-post ComfyUI tasks through persisted background jobs. Missions displays their saved state and evidence. Verified live: 12 saved job matches, three content drafts, a completed research report with 26 sources/10 findings, and synthetic-audio result discussion. Submission/publishing account setup and physical-microphone acceptance remain outstanding; this is not a claim of universal autonomous task completion.

1. Finish live acceptance after Docker engine startup: research, security, Career, memory, and ComfyUI suites.
2. Add Spotify token revocation/reconnection UX and repeat playback verification after a full host restart.
3. Run Chrome microphone, echo, false-wake, pause, and barge-in tests with the browser extension available.
4. Pilot one supervised Career application adapter with immutable resume/answer/submission evidence.
5. Connect one social sandbox from generation through approval, publishing, and analytics before adding another provider.
6. Add restart recovery, idempotency, load/soak, dependency scanning, encrypted backups, and an independent security review.
