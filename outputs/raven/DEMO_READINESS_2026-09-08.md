# RAVEN demo readiness — September 8, 2026

This is an evidence-based handoff, not a claim that every roadmap feature is production complete.

## Implemented and checked

- Docker web app, database, search, voice and isolated Hermes worker are running.
- Windows desktop companion v1.8 reconnected with the project Python; launcher no longer depends on Python being on PATH or restarts the voice container.
- Voice navigation fixes cover polite prefixes, Knowledge/Work, graph camera vs memory filtering, “for me, please”, and selected transcription variants. Incomplete research topics ask for clarification instead of queuing filler.
- UI actions are awaited in order. Old voice responses cannot apply stale UI actions. A late Research refresh cannot overwrite another workspace.
- Streaming voice allows one active tab, bounds idle audio pre-roll, and gives unfinished fallback phrases more pause time. Human interruption and accuracy acceptance remain necessary.
- Speech-speed commands change browser playback speed; runtime-model questions use actual configured components.
- Context drawer is hidden until used and closes completely. Conversation history scrolls inside its own pane.
- Mint/violet dashboard with central animated RAVEN core; consistent theme across workspaces. Career feed setup is optional/collapsed; invalid historical search leads remain preserved but cannot generate applications.
- Job-detail URL validation rejects company-board listings, generic search pages, unrelated sites and lookalike hostnames. Existing records were not deleted.
- Research report citations open their attached sources. Existing report downloads and source ledger remain available.
- Content now supports direct image/video prompts without a campaign-writing model. Voice examples: “Generate an image of a futuristic city”; “Generate a video of clouds.” These use saved background jobs and the same ComfyUI artifact verification path.
- Real direct-image acceptance test created asset `b66c7f44-f595-4b8e-8f48-f64a36efaaa1`: 774,402-byte PNG returned through RAVEN. ComfyUI logged 23.84 seconds. This is a retained demo draft, not published content.

## Tests and limits of the evidence

- 985 Python regression tests passed in 2.16 seconds.
- Ten live API voice/UI routing checks passed, including semantic Spotify memory selection.
- JavaScript syntax checks passed.
- Synthetic audio sent at real-time speed produced the complete “open Spotify and play Good Morning…” intent through Parakeet/Whisper. The artist remained “can i west” in raw ASR. Known entity correction handles that spelling, but this is not proof of general recognition accuracy. The measured 6.56-second wall time includes the utterance; it is NOT response latency after speech ends.
- Browser inspection confirmed the redesigned dashboard and drawer open/close behavior.
- Hermes live registry exposes only web_search and web_extract. A real Smithsonian search returned evidence. No shell, desktop, publishing or job-submission tools are exposed through this worker.
- Video generation, real microphone barge-in, Spotify playback/closing and multi-turn correction still need a new end-to-end acceptance session. A healthy companion is not proof every app action works.

## Required setup: OpenRouter

From this folder, run `./setup-openrouter.ps1` in PowerShell. Enter the key in the hidden prompt, never in chat or frontend fields. The script writes the server `.env` and restarts only RAVEN and Hermes.

Research, career/content structured generation and Hermes use `openrouter/free` or an explicitly configured `:free` model. Voice remains local. Free quotas and availability vary. Missing keys/provider failures stop the heavy task instead of silently using the local voice GPU. Remote prompts include research inputs and, for career generation, candidate/job information.

At handoff the key was absent. Thus remote synthesis, research answer quality, and targeted resume generation with this new provider have NOT passed live acceptance. Do not present them as verified.

## Architecture

Browser microphone → Silero + Parakeet EOU → selective Whisper verification → shared typed voice/text router → verified tool result or bounded Qwen response → Kokoro audio.

Heavy research/career/content text → server-side OpenRouter. Hermes runs separately in a non-root, read-only container with research-only tools, no host mounts and authenticated internal access. ComfyUI runs locally on localhost and is accessed via the backend; media is served through the owner-scoped artifact proxy. PostgreSQL/pgvector stores user-scoped memory, jobs, reports and evidence.

## Remaining production gates

1. Supply OpenRouter key; verify quota errors, factual cited reports and truthful resume packages end to end.
2. Human recordings: incomplete sentences, barge-in, background jobs, repeated corrections, noisy-room input; measure p50/p95 end-of-speech latency and exact action accuracy.
3. Verify video rendering and resource contention on the RTX 3060. Media workloads can still compete with voice on the same GPU.
4. Connect and test application-submission credentials, real employer workflows, Instagram/X authorization and public media hosting. YouTube upload adapter remains incomplete. No automatic submission or publishing is claimed.
5. Test cancellation of running research/media work and richer follow-up references. These are not complete yet.
6. Review remaining hard-coded readiness/roadmap claims and replace them with active checks. Existing milestone percentages are not certification.

Do not describe the entire system as production-certified or fully autonomous until these gates pass.
