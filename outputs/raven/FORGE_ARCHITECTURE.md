# RAVEN Forge architecture

Last verified: 2026-09-10

Forge is RAVEN's durable software-engineering workspace. It does not require Codex. RAVEN owns identity, project registration, job state, messages, events, artifacts and UI; the isolated Hermes service owns the bounded agent/tool loop.

```text
Forge UI -> authenticated RAVEN API -> PostgreSQL job controller
                                      |
                                      v
                                Hermes runtime
                                      |
                         NVIDIA / OpenRouter / Ollama
                                      |
                      file + search + terminal + todo tools
                                      |
                     approved repository mount + Git diff
```

## Runtime and providers

`AUTO` chooses the first configured provider in this order: NVIDIA NIM, OpenRouter, local Ollama. An explicit provider never silently consumes another provider. Codex appears as an optional disabled runtime until a separately authenticated, quota-aware adapter exists; Forge does not consume Codex allowance today.

Configure secrets only in `.env`:

```dotenv
NVIDIA_API_KEY=
OPENROUTER_API_KEY=
```

Optional overrides are `FORGE_NVIDIA_MODEL`, `FORGE_OPENROUTER_MODEL`, and `FORGE_LOCAL_MODEL`. Model identifiers are configuration, not assumptions of permanent availability. Provider status returned to the browser contains only booleans and model names—never keys.

## Security model

- Projects are relative paths inside `/workspace`, the repository-only Docker mount. Absolute paths, traversal, `.git`, and `.env` project roots are rejected.
- The RAVEN `.env` path is masked from the Hermes mount. Provider keys are passed to the model client and removed from the agent environment during a run.
- Hermes dangerous-command prompts are denied by default. No push, merge, broad deletion, system package changes, OS changes, or credential operations are authorized.
- Forge creates `raven/forge/<task>-<id>` only when the project is Git-backed and clean. Dirty work is preserved and reported.
- There is no automatic merge, push, or deployment.
- The UI displays concise tool outcomes, never private reasoning.

This boundary is intentionally conservative. A future approval bridge should turn a denied dangerous action into a RAVEN `approvals` record and resume only after an owner decision.

## Durable lifecycle

PostgreSQL tables `forge_projects`, `forge_jobs`, `forge_job_events`, `forge_messages`, and `forge_artifacts` retain work across refreshes and restarts. A worker dequeues jobs and calls the authenticated Hermes endpoint. Statuses include queued, inspecting, planning, running, testing, verifying, paused, blocked, completed, failed, and cancelled.

The frontend polls structured events at a short interval. Activity, plan, diff/files, tests and logs use persisted artifacts. Pause/cancel requests are durable; because the current Hermes call is one bounded process, cancellation of a running model request becomes effective at the safe boundary after it returns. Hard cooperative cancellation is a known next step.

## Engineering loop and verification

Hermes receives bounded job history, execution-mode rules, project root and the safety contract. It uses targeted file/search/terminal/todo tools, emits tool events, and returns a concise report. Forge captures the Git diff separately.

Current verification is the observed Hermes tool trace plus captured Git diff and final evidence report. Deterministic per-project success policies and parsed test summaries are not yet a universal goal judge; the Tests panel reports the evidence actually produced instead of fabricating a pass.

## API surface

- `GET/POST /api/forge/projects`
- `GET/POST /api/forge/jobs`
- `GET /api/forge/jobs/{id}`
- `GET /api/forge/jobs/{id}/events?after=<event-id>`
- `GET /api/forge/jobs/{id}/artifacts/{plan|diff|tests|log}`
- `POST /api/forge/jobs/{id}/message`
- `POST /api/forge/jobs/{id}/{pause|resume|cancel|continue}`
- `GET /api/forge/providers`

Owner routes require the RAVEN session. Hermes endpoints require the internal bearer token.

## Memory and extensions

Forge state stays in Forge tables and is not dumped into personal memory. A later curator may save a compact verified engineering lesson through RAVEN's existing admission policy. Source files, raw logs and secrets must never become memories.

Planned extensions are RAVEN approval/resume records, cooperative mid-run controls, provider-fallback checkpoints, provider model discovery, parsed test cards, repository preview, browser screenshot verification, MCP event adapters and an authenticated Sentinel remote-node adapter. No Raspberry Pi is currently claimed as connected.

## First real test

Open **Forge**, keep `Build` and choose a configured provider, then submit:

> Inspect this RAVEN repository, find one small safe improvement, create an isolated branch if the worktree is clean, implement it, run the relevant tests, and show me the diff.

Review Activity, Diff, Tests and Logs. Do not merge until the evidence is satisfactory.
