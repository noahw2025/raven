# RAVEN Iteration 2 — Observability, Knowledge, and Integration Readiness

This document refines the stack-agnostic product requirements into testable product behavior. Status is based on the running local build, never planned appearance.

## Delivered in this iteration

### 1. Capability operations

- The Toolchain has distinct Capabilities, Build Roadmap, Model + Cost, Memory Engine, and Web Intelligence views.
- A capability is `ready` only when callable. Missing credentials or gateways remain `setup_required` or `unavailable`.
- Each phase exposes its completed foundation and next implementation work.

Acceptance: a user can answer “what works, what is blocked, and what should we build next?” without reading source code.

### 2. Model and cost observability

- Text and Realtime response usage are persisted in PostgreSQL `model_usage` records.
- Each record includes provider, model, purpose, channel, text/audio token counts, approximate cost, and a privacy-safe context manifest.
- Voice cost is calculated from provider-returned usage, not call duration or a fabricated flat estimate.
- Costs are explicitly approximate because provider pricing can change and invoices remain authoritative.

Acceptance: after a model turn, Model + Cost shows what category of data left the device, model identity, token counts, and estimated cost. Secrets and hidden prompts never reach the browser.

### 3. Explainable memory

- Curator confidence and embedding similarity are separate concepts in both architecture and UI.
- Curator confidence comes from a structured LLM extraction that must cite an exact quote and mark the memory explicit.
- Admission requires confidence >= 0.72; sensitive or confidence < 0.86 records require review.
- `text-embedding-3-small` produces 1,536-dimensional vectors stored only in PostgreSQL/pgvector.
- Cosine similarity chooses bounded context and identifies semantic duplicates; it does not determine whether a statement is true.

Acceptance: the user can determine why a memory exists, where it came from, whether it is reviewed, and how it was retrieved.

### 4. Cognitive constellation

- The Knowledge Graph is rendered from canonical database objects, not demo fixtures.
- Node type, importance, and confidence have distinct visual encodings.
- Stored relations are canonical links. Vector-derived semantic links are labeled as embedding inference.
- Search, type filters, pan, zoom, selection, evidence inspection, and two-hop local expansion remain functional.

Acceptance: an empty relationship set looks empty; similarity links are never presented as verified facts.

### 5. Current web intelligence

- Research missions can call the OpenAI Responses API `web_search` tool.
- Research output and mission steps persist in PostgreSQL for reuse and audit.
- Durable memory remains selective; a web result is not silently promoted into personal memory.
- Direct Realtime voice tool orchestration, citation normalization, cache freshness policy, and scheduled monitoring remain explicit next work.

## Integration contract

Every new plugin or gateway must provide:

1. Server-side secret configuration; never browser-delivered credentials.
2. Authenticated health check and truthful status.
3. Separate read/write scopes.
4. Declared data sent to the service.
5. Consequential-action approval policy.
6. Idempotency and retry behavior.
7. Audit events with target, origin mission, result, and error.
8. Revocation and token-rotation instructions.
9. Cost or quota telemetry where available.
10. A real end-to-end test before `ready` status.

## Forward implementation sequence

| Priority | Capability | Current state | Production exit criterion |
|---:|---|---|---|
| P0 | Voice + text usage ledger | Functional | Reconcile sampled records against provider invoices |
| P0 | Citation normalization | Next | Every research claim opens its exact source |
| P0 | Mission checkpoints | Foundation | Restart-safe, idempotent recovery tests pass |
| P1 | Hermes worker | Setup required | Auth, sandbox, progress, cancellation, and artifact handoff verified |
| P1 | Research cache | Next | Query/source hash, freshness TTL, invalidation, and citation preservation |
| P1 | Voice research handoff | Next | Voice starts a durable research mission and receives progress without blocking the call |
| P1 | Email/calendar | Setup required | Read-only first; writes gated and audited |
| P2 | Home Assistant | Setup required | Dedicated allowlisted gateway and high-impact confirmation |
| P2 | Social operations | Setup required | Brand/account isolation, draft approval, rate limits, and rollback plan |
| P3 | Brokerage | Blocked | Paper trading and supervised controls before any live-order pathway |

## Honest completeness

The local production MVP now covers the core conversation, memory, knowledge, visibility, approvals, audit, research, and durable-run foundations. It is not a completed autonomous home/business operator. External accounts, native desktop control, Home Assistant, social publishing, and Hermes execution require their real connectors and security verification before they can be marked ready.
