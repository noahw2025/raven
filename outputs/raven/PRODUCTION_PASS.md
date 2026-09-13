# RAVEN Production Interaction Pass

## Five production pillars

### 1. Natural realtime voice

The old browser speech-recognition/TTS loop was replaced with native speech-to-speech over WebRTC. The backend brokers the SDP exchange so the OpenAI key never reaches JavaScript. The session uses semantic VAD with low eagerness, far-field noise reduction, transcription, and automatic response interruption. Voice and text write to the same canonical conversation timeline. Completed voice turns enter the same memory-formation pipeline as text.

Reference: OpenAI Realtime API documents native audio, WebRTC, semantic VAD, noise reduction, and automatic interruption: <https://platform.openai.com/docs/api-reference/realtime>

### 2. Selective semantic memory

Every completed turn is evaluated by a conservative structured-output curator. It stores only durable preferences, facts, relationships, goals, commitments, decisions, standing instructions, and corrections. It rejects secrets, filler, transient requests, assistant-generated claims, and speculation. Candidates receive kind, importance, confidence, sensitivity, rationale, tags, source message, review state, and an embedding.

Semantic nearest-neighbor comparison consolidates a candidate into an existing memory above a high similarity threshold. Retrieval uses embeddings, provenance, exclusion/archive controls, hard context limits, and usage tracking. HNSW indexes support growth; user filters remain inside SQL.

References: pgvector indexing/filtering guidance: <https://github.com/pgvector/pgvector>; PostgreSQL Row Security: <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>

### 3. Inspectable data and knowledge

Memory Vault is a record-level database explorer: totals, review queue, types, confidence, provenance, rationale, tags, use count, last use, correction, exclusion, and permanent deletion. Knowledge Graph is a separate global/local graph with search, type filters, pan, zoom, focus, confidence opacity, importance sizing, edge types, and context inspection.

This follows Obsidian's useful distinction: the global graph visualizes the whole vault, while local graph depth reveals the neighborhood of the active record. Reference: <https://obsidian.md/help/plugins/graph>

### 4. Durable autonomous missions

Mission Control provides templates for research, social campaigns, market research, and general work. Each run has objective, department, autonomy level, budget, durable status, ordered steps, tool assignment, output, errors, timestamps, and append-only event history. A background worker claims work transactionally and resumes after container restart.

Consequential steps become explicit approvals. Approval does not override reality: if a connector is unavailable, the approved step becomes blocked and records why; it never simulates success. This mirrors the durable-workflow principle that event history is the source of truth and external side effects are recorded activities. Reference: <https://docs.temporal.io/workflows>

### 5. Operational command experience

The redesigned Command Nexus shows actual cognitive state, model, active missions, memory/review counts, authority queue, recorded spend, mission telemetry, notifications, and tool gaps. Toolchain distinguishes `ready`, `unavailable`, and policy-`blocked` capabilities with risk and approval requirements. Trust Center centralizes approvals and makes the live-trading prohibition visible.

## Demonstrable flows

1. Open Talk to RAVEN and choose **Start Voice**. Speak naturally, pause, interrupt, and switch to text. Reopen the same conversation later.
2. Say a durable preference or goal. Open Memory Vault to see the extracted record, provenance, rationale, confidence, and review state. Correct or exclude it and ask again.
3. Open Knowledge Graph, focus the memory, inspect it, and switch to its two-hop local neighborhood.
4. Launch a Deep Research mission with a small budget. Watch persistent steps and event history progress; refresh or restart the app and see state preserved.
5. Launch Social Campaign. RAVEN can research and prepare concepts/assets, then stops at the social connector approval. Because no authenticated social connector exists, approval produces an honest blocked state rather than fake account creation.

## Production boundary

“Production scale” here applies to the five implemented product foundations: persistent schema, secured server-side credentials, indexed retrieval, durable execution state, restart recovery, budgets, approvals, audit, and responsive operational UX. Horizontal worker scaling, a dedicated Temporal cluster, multi-user identity/RLS roles, TLS ingress, encrypted backups, observability export, and authenticated third-party connectors remain deployment work.

Unattended live-money trading is intentionally not implemented. Brokerage execution must begin with paper trading, explicit account permissions, position/loss limits, order confirmation, audit, and emergency stop. Social account creation and posting require platform-approved APIs and authenticated accounts; RAVEN will not bypass platform controls.
