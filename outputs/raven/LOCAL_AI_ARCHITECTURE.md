# RAVEN local AI architecture

Updated: 2026-09-05. This is the implemented architecture, not a future proposal.

```text
Chrome microphone (PCM16 at 16 kHz)
  -> localhost-only WebSocket
  -> Silero VAD 6.2
  -> NVIDIA Parakeet Realtime EOU 120M (16 ms frames / 80 ms chunks)
  -> accumulated transcript + EOU probability
  -> Whisper large-v3-turbo verification for action or uncertain turns
  -> contextual entity correction
  -> shared deterministic text/voice command router
  -> typed tool execution with result verification
  -> concise response
  -> sentence-streamed Kokoro 82M speech with barge-in
```

All four voice components run locally in the GPU-backed `voice` container. Voice audio and API credentials are not sent to the browser or a cloud model. Ports 8080 and 8090 bind to loopback, and the WebSocket accepts only RAVEN's localhost origins.

Parakeet produces live partials and learned EOU/EOB tokens. Silero provides acoustic speech-start and a silence fallback. Action-bearing or uncertain turns receive a second Whisper decode; narrow corrections handle known entities such as apps and artists. The final transcript enters exactly the same router and safety policy as text, and deterministic commands use no Qwen tokens.

Verified on 2026-09-05:

- Parakeet, Silero, Whisper Turbo, and Kokoro report ready on the RTX 3060.
- A synthetic multi-step command produced 15 live partials and a complete final transcript.
- The action turn activated Whisper verification and contextual entity correction in the shared router.
- The existing routing, memory, research, and tool suite passes: 969 tests.
- Both the RAVEN app and voice containers are healthy.

Conversation correction pass (2026-09-05): routine reversible commands bypass Whisper when Parakeet has a confident EOU; suspicious entities and consequential actions still receive verification. Parakeet partial text now activates a 600 ms silence fallback when acoustic VAD misses speech onset. Local-Qwen timeout plus exhausted OpenAI quota returns a recoverable spoken busy response instead of terminating the voice link. Observed Spotify punctuation/name/follow-up variants and natural Research Lab requests are covered by deterministic tests.

Physical microphone acceptance remains a host prerequisite. Chrome `NotFoundError` / “No microphone found” means Windows did not expose an active capture endpoint; this occurs before RAVEN receives audio and cannot be repaired inside its read-only Docker container.

Text and deep work use local Qwen behind provider-neutral boundaries. Embeddings use local `nomic-embed-text` at 768 dimensions. All inference paths are replaceable and cost $0 in API fees.
