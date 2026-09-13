# RAVEN iteration 4 — conversational intelligence and product navigation

## Evidence that triggered this pass

The recorded voice transcript showed four concrete failures: canned social replies, an incorrect bird reference, stock context leaking into an unrelated Atlanta fragment, and a weak weather answer after an explicit correction. The product roadmap also existed only as a secondary Toolchain tab, making major missing modules hard to find.

## Implemented acceptance requirements

- Qwen3 8B replaces Qwen 2.5 3B/7B for local dialogue and curation on the RTX 3060.
- Greetings and acknowledgements use a deterministic low-latency dialogue policy.
- Corrections reset the active factual domain immediately.
- Ambiguous fragments ask for clarification instead of replaying a prior stock or weather answer.
- Weather uses a direct keyless Open-Meteo forecast with location, date, timezone, units, and provenance.
- Market quotes use the read-only Yahoo chart feed with symbol and observation time.
- Weather and market values are rendered without an LLM so numbers cannot drift.
- Voice endpointing waits 1.15 seconds to tolerate ordinary thinking pauses.
- Goals & Tasks, Departments, Build Roadmap, and Privacy & Settings are first-class navigation destinations.
- Build Roadmap exposes seven modules, evidence states, definitions of done, and connector gaps.
- Knowledge Graph retains 3D/2D/list modes and uses a wider depth field with readable labels.

## Measured acceptance evidence

- Exact transcript regression sequence: passed.
- Fast social response: 16 ms server turn.
- Google quote path: 150 ms in the verified run.
- Atlanta tomorrow forecast path: 1,141 ms in the verified run.
- Local Kokoro synthesis: 662 ms in the verified run.
- API cost for these paths: $0.

## Honest production boundary

The browser application is a strong local product demonstration, not a finished cross-device autonomous operator. Native background wake, semantic audio turn detection, production connectors, checkpointed Hermes execution, external security/load review, and supervised real-world automation remain explicit roadmap gates.
