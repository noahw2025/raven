# RAVEN requirements scorecard — three-pass audit

> Historical snapshot. The canonical current status is [docs/REQUIREMENTS_AND_READINESS.md](docs/REQUIREMENTS_AND_READINESS.md); executable tests and current runtime evidence supersede this earlier score.

Scale: 0 absent, 1 design only, 2 foundation, 3 functional, 4 locally verified and polished, 5 production-ready for the stated scope. Scores are intentionally not inflated when external accounts, native clients, hardware, or independent security/load evaluation are still required.

| # | Requirement area | Pass 1 | Pass 2 | Pass 3 | Evidence / remaining gate |
|---:|---|---:|---:|---:|---|
| 1 | Product pitch | 4 | 5 | 5 | Coherent local-first intelligence environment |
| 2 | Core promise | 4 | 5 | 5 | Voice/text/memory/research/tasks unified |
| 3 | Identity | 3 | 4 | 4 | One RAVEN persona; deeper long-term style adaptation remains |
| 4 | Relationship model | 3 | 4 | 4 | Durable preferences/goals; proactive relationship cadence is partial |
| 5 | Conversation model | 3 | 4 | 4 | Adaptive 2.1–2.6 s endpointing, 1.27x Kokoro, ordered sentence prefetch, barge-in |
| 6 | Wake word | 1 | 3 | 3 | ARISE works browser-active; native always-on model not yet trained |
| 7 | Memory | 3 | 5 | 5 | Purpose gates, decision ledger, review/edit/delete/provenance |
| 8 | Knowledge handling | 3 | 4 | 4 | Local RAG, bounded chunks, live search; more source QA needed |
| 9 | Neural/knowledge map | 2 | 3 | 4 | Perspective 3D/2D/list, vector/model insight, active memories |
| 10 | UI philosophy | 3 | 4 | 5 | Polished responsive command UI with real state only |
| 11 | Command center | 3 | 4 | 4 | Live state/token/cost/latency/mission/memory panels |
| 12 | Research department | 3 | 4 | 4 | SearXNG + quote verification; scheduled source QA is next |
| 13 | Sales department | 2 | 3 | 3 | Draft/research foundation; CRM/email connectors absent |
| 14 | Social department | 1 | 2 | 2 | Architecture only; authenticated publishing absent |
| 15 | Daily operations | 2 | 3 | 4 | Goals/tasks/runs/notifications; calendar/email absent |
| 16 | Desktop/home control | 1 | 2 | 4 | Authenticated loopback gateway, fixed allowlist, arbitrary shell rejected; owner OAuth/aliases remain |
| 17 | Goals/tasks/long work | 3 | 4 | 4 | Durable runs/steps/events; idempotent checkpoints next |
| 18 | Departments/multi-agent | 2 | 3 | 3 | Capability scopes exist; full specialist orchestration partial |
| 19 | Autonomy model | 3 | 4 | 4 | Levels, budgets, status, cancellation, approvals |
| 20 | Approval model | 3 | 4 | 4 | Target/reason/data/reversibility/expiry/audit |
| 21 | Integrations | 1 | 2 | 3 | Executable local adapters and truthful setup states; consequential provider accounts remain disconnected |
| 22 | Agent runtime | 3 | 4 | 4 | Durable built-in runner; Hermes gateway not authenticated |
| 23 | Personality/presence | 3 | 4 | 4 | Stable warm/direct voice; richer adaptation remains |
| 24 | Proactivity | 2 | 3 | 3 | Notifications and missions; scheduler/monitoring partial |
| 25 | Privacy/security | 4 | 5 | 5 | Server-only secrets, localhost, internal DB, bounded RAG |
| 26 | Cost intelligence | 3 | 5 | 5 | Local $0 stack, per-call tokens/cost/latency/context manifest |
| 27 | Reliability | 3 | 4 | 4 | Health checks and E2E; soak/load/chaos testing remains |
| 28 | Cross-device | 1 | 2 | 2 | Responsive web only; sync/native mobile absent |
| 29 | Demo journeys | 3 | 4 | 4 | Core voice/memory/search/graph journeys work locally |
| 30 | Success criteria | 3 | 4 | 4 | Core measurable; external autonomous outcomes not yet proven |
| 31 | Non-negotiables | 3 | 4 | 5 | Core safety, truth, memory, cost, approvals satisfied |
| 32 | Deferred scope honesty | 4 | 5 | 5 | Missing connectors and native wake are plainly marked |
| 33 | Final vision | 3 | 4 | 4 | Strong local foundation; not yet finished external operator |

Pass totals: **Pass 1: 89/165**, **Pass 2: 119/165**, **Pass 3: 131/165 (79.4%)**. This historical product-requirement audit uses a different denominator from the canonical ten-area readiness matrix. Reaching 165/165 requires real third-party accounts, native always-on wake software, hardware integration, real-room evaluation, load/security review, and supervised deployment; claiming those locally would violate RAVEN's honest-state requirement.

## Iteration evidence

1. Evidence pass: persisted memory decisions, model timing/tokens, current-data test, graph metadata.
2. Voice pass: ARISE, adaptive turns, sentence-first Kokoro, barge-in/Interrupt, measured local E2E.
3. Product pass: cognitive dashboard reactor, 3D graph modes, Memory Vault ledger, corrected architecture and truthful roadmap.
