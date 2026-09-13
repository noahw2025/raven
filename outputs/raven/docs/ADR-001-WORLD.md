# ADR 001: Native World intelligence

2026-09-10 — accepted for local integration.

RAVEN uses plain browser JavaScript with layered workspace routing, FastAPI, PostgreSQL/pgvector, a shared text/voice chat route, durable Research jobs, and a separate Hermes Forge worker. The existing `world.js` is the home activity illustration; it is preserved. Geospatial work uses `geospatial.js` and `/api/geo`, with page ID `world`.

God's Eye View (Bilawal Sidhu, MIT) was inspected at the checkout recorded in WORLD_ATTRIBUTION.md: map startup/stack, camera ownership, render governor, satellite propagation, public provider adapters, scene-context/voice actions, environment configuration, and data licensing. Adapt the render governor and TLE propagation approach. Rewrite provider transport behind RAVEN authentication/cache and normalized entity schemas. Retain Cesium and satellite.js, pinned to the upstream lockfile. Keep RAVEN's existing voice, model, memory, job controller and design system.

Do not embed a second application. Load Cesium only on World entry and destroy it on exit. Keep source credentials server-side. Use bundled Natural Earth imagery as the offline base; optional keyless Esri imagery retains on-screen credit. Exclude upstream proprietary 3D models, noncommercial cable data, simulated traffic, invasive person tracking, and the separate OpenAI voice stack.

Public feeds: USGS earthquakes, NASA EONET events, adsb.lol regional aircraft/public military records, CelesTrak orbital elements, Launch Library 2 events, TfL public traffic camera catalog. AISStream vessels require a server key. All feeds carry timestamps, attribution, limits and availability. SGP4 positions are predicted from orbital elements, never live telemetry. Empty coverage is not proof of no activity.

Actions are typed and validated server-side, resolved from semantic model plans through the existing provider abstraction, and applied by one browser action dispatcher. The browser contributes bounded viewport/selection identifiers; public metadata is recovered from provider caches before use. Descriptions use source evidence; Research and Memory use existing APIs. No raw scene polling data is automatically saved to memory.

Performance budgets: at most 600 rendered records per ordinary layer, bounded caches, coalesced requests, controlled polling, render-on-demand, canceled fetches on exit. Measure initialization, repeated-entry cleanup and active-scene responsiveness in Chrome.
