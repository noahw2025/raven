# GitHub development snapshot

Prepared 2026-09-12 for `noahw2025/raven`, private by default.

## Included

- Current RAVEN source, Docker definitions, Windows helpers, application documentation, and tests.
- The existing `outputs/raven` layout, so Docker's repository-relative paths remain intact.
- Hermes pinned as the `work/hermes-agent` Git submodule at `36cb5ae5530a75def7df3195e49b7a4aa2add482`.
- In-progress World integration and external Forge-project work. These are not represented as completed acceptance gates.

## Current World verification

Before the GitHub publication request, 1,056 existing Python regression tests passed; 17 new geospatial tests separately passed. Real public feeds responded for aircraft, satellites, earthquakes, natural events, London cameras, launches, and a regional public military feed (zero tracks in that test region). AIS requires credentials. Text and transcribed-voice requests both produced typed layer actions in the normal chat route.

Browser acceptance is **not yet passing**: the Cesium distribution's WebAssembly and inline-worker requirements conflict with the application's existing browser security policy. A broader policy relaxation was blocked by deployment review and is not part of this snapshot. Continue with a security-compatible engine build or obtain explicit approval for a carefully scoped exception; do not silently weaken the whole application's policy. The globe rendered markers but not the Earth surface in that failed test. A screenshot containing a canvas is not sufficient evidence that rendering works.

World research handoff has unit coverage for creating a real durable project; full browser handoff, complete cleanup/performance validation, and live microphone acceptance remain outstanding. Do not claim the microphone was tested by the transcribed-voice API checks.

## Not a data backup

The working `.env`, local databases, conversation/memory records, provider credentials, screenshots, model downloads and environments remain on the original computer. They must be configured or backed up separately and securely. On another computer, review the local Windows paths before running startup scripts.

## Next engineering step

Resume the World integration from `docs/ADR-001-WORLD.md` and `tests/e2e_geospatial.cjs`; do not restart the project or replace RAVEN's voice stack. The public provider implementation is `app/geospatial.py`; the native view is `app/static/geospatial.mjs`.
