# RAVEN documentation map

This directory is the canonical entry point for current engineering status. Historical iteration reports remain at the project root as immutable decision records; they are not the live source of truth.

## Current documents

- [GitHub snapshot status](GITHUB_SNAPSHOT.md): current publication scope, unfinished World integration, and excluded private data.
- [World integration decision](ADR-001-WORLD.md) and [third-party notices](WORLD_THIRD_PARTY_NOTICES.md).
- [Current rebuild state](IMPLEMENTATION_STATE.md): September 8 rebuild, live verification evidence, and explicit remaining gaps. Start here.
- [Forge architecture](../FORGE_ARCHITECTURE.md): engineering workspace, Hermes/provider flow, job lifecycle, security boundary, setup and known limitations.

- [Project status and implementation handoff](PROJECT_STATUS_2026-09-03.md): the current executive state, verified capabilities, gaps, and recommended next tooling sequence.
- [Requirements and readiness](REQUIREMENTS_AND_READINESS.md): requirement-by-requirement status, verified scope, and external gates.
- [Testing and security](TESTING_SECURITY.md): security model, test commands, acceptance evidence, and remaining production checks.
- [System blueprint](../RAVEN_SYSTEM_BLUEPRINT.md): architecture, models, APIs, memory flow, and data model.
- [Career production report](../CAREER_AUTOPILOT_PRODUCTION_REPORT_2026-08-09.md): job discovery, resume generation, approvals, and submission boundary.
- [Social/desktop/career architecture](../SOCIAL_DESKTOP_CAREER_ARCHITECTURE.md): external connector contracts and setup.

## Historical records

`ITERATION_2_PRODUCT_REQUIREMENTS.md` through `ITERATION_5_PRODUCT_REQUIREMENTS.md`, `PRODUCTION_PASS.md`, and dated iteration reports describe earlier passes. Where they conflict with current runtime behavior, the current documents and executable tests win.
