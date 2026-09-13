# RAVEN iteration 5 — current intelligence and voice-operated tools

Status date: 2026-08-09. “Complete” means implemented and verified in the local Docker build. Authenticated third-party execution remains setup-dependent and is never represented as complete without provider evidence.

## Pass 1 — conversation correctness and survival

| Requirement | Implementation and evidence | Score |
|---|---|---:|
| Accurate current date/time | Deterministic `America/New_York` server clock; live voice request returned current year with zero model tokens | 10/10 |
| Honest source provenance | Each turn records actual tool/search/source/model/token context; live “are you searching?” test correctly said no | 10/10 |
| Current factual tools | Weather, market, and SearXNG precede generation; live market 146 ms, weather 1.16 s, three web results | 10/10 |
| Voice continuity | Missing voice conversation ID resumes the latest six-hour session; browser ID persists in session storage; exact-ID test passed | 10/10 |
| Noise rejection | STT confidence/no-speech probability plus duration/frame gate; positive-speech and cup-clink-like negative tests pass | 9/10 |
| Recoverable failures | Failed turns return to listening instead of closing; real-room endurance test remains | 8/10 |

## Pass 2 — persistent Deep Research and voice tool control

| Requirement | Implementation and evidence | Score |
|---|---|---:|
| Multi-query research | Persistent plan/search/fetch/synthesize/verify worker and project API | 9/10 |
| Research evidence | Query/source/finding/event/token/cost/error/report ledgers; Research Lab and Markdown export | 9/10 |
| Fetch security | DNS/IP SSRF rejection, redirect revalidation, HTTP(S)/HTML-only bounded extraction | 9/10 |
| Failure transparency | Typed errors and transactional retry; first Qwen3 timeout retained and fixed with a fast model/fallback plan | 9/10 |
| Voice-operated UI | Deterministic commands cover chat, memory, graph, research, social, career, tools, roadmap, missions, tasks, cost, trust, and settings | 9/10 |
| Consequential actions | Research executes directly; publishing and job submission require explicit approval | 8/10 |

## Pass 3 — campaigns, connectors, UX, and architecture clarity

| Requirement | Implementation and evidence | Score |
|---|---|---:|
| Research Lab UX | Project orbit, phases, query/source panes, report, confidence, tokens, cost, retry | 8/10 |
| Instagram | Local drafts, public-media contract, server-only token, verify/approve/publish evidence; credentials still needed | 8/10 |
| X | Cross-platform drafts, 280-char bound, server-only OAuth, approval-gated `POST /2/tweets`; credentials still needed | 8/10 |
| YouTube | OAuth/server-secret readiness and metadata contract; resumable upload pending | 6/10 |
| Career | Canonical profile, job research, targeted resume/CV/answers, checksum, approval and proof | 9/10 |
| Model interchangeability | Qwen2.5 3B structured worker; Ollama/OpenAI adapter selection and telemetry | 9/10 |
| Secret isolation | Credentials are server environment values; frontend receives readiness booleans only | 10/10 |

## Next production gates

1. Install/enable Chrome and the ChatGPT browser extension, then run exact-browser visual and microphone QA.
2. Run a 60-minute real-room voice soak with echo, cup/keyboard noise, interruptions, long pauses, and ARISE false-accept/false-reject counts.
3. Configure Instagram Professional credentials server-side and publish one sandbox post through approval, retaining Meta’s media ID.
4. Configure X OAuth user context and publish one sandbox post through approval, retaining its post ID.
5. Implement YouTube OAuth refresh plus resumable `videos.insert`, quota reporting, retries/idempotency, and upload evidence.
6. Add provider analytics ingestion and a bounded experiment loop; never claim campaign improvement without measured data.
7. Connect the supervised career browser adapter and retain ATS confirmation; do not bypass CAPTCHAs, site rules, or attestations.

## Verification

```powershell
docker compose up -d --build
docker compose run --rm --no-deps -e PYTHONPATH=/app -e RAVEN_ADMIN_PASSWORD=test-password -e RAVEN_JWT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx -v "${PWD}/tests:/app/tests:ro" raven pytest tests/test_core.py -q -p no:cacheprovider
node tests/e2e_voice.cjs
```
