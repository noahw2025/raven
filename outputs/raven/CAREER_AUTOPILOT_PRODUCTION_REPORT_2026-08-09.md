# RAVEN Career Autopilot — Production Research and Delivery Report

Date: 2026-08-09

## Outcome

RAVEN now supports the complete applicant preparation pipeline: official ATS-feed discovery, normalization, stable deduplication, explainable profile-fit scoring, current company/role research, fact-bound resume tailoring, cover letters, application-question abstention, immutable versions, real PDF/DOCX downloads, per-job approval, idempotent adapter execution, and submission evidence.

External submission is intentionally **setup required**, not falsely marked complete. Applicant-side Greenhouse, Lever, Ashby, and LinkedIn submission APIs are not general public APIs: they require employer/ATS partner credentials. RAVEN therefore uses a supervised Chrome adapter contract for applicant-side forms and will not claim an application succeeded without confirmation evidence. CAPTCHA, MFA, demographic choices, legal attestations, and missing facts require owner takeover.

## Primary-source and open-source research

| System | Useful pattern | RAVEN decision |
|---|---|---|
| Reactive Resume | Self-hosting, structured versions, PDF/JSON/DOCX portability | Keep a canonical private profile and immutable targeted versions |
| OpenResume | ATS-oriented, parser-friendly resume layout | Render conservative single-column PDF/DOCX artifacts |
| Resume Matcher | Resume/job comparison and keyword evidence | Show deterministic fit rationale before model tailoring |
| AIHawk | Browser-driven application workflow and provider adapters | Retain the workflow pattern, not the archived/provider-removed package |
| JobSpy | Multi-board discovery | Optional research input only; scrapers are too fragile for the primary production path |
| Greenhouse Job Board API | Public GET job feed; authenticated employer-side application POST | Use public feed; never request employer keys from an applicant |
| Lever Postings API | Public postings; employer key required for programmatic apply; custom questions unavailable | Use public feed and hosted applicant form |
| Ashby Public Job Posting API | Public listed jobs, locations, compensation and apply URLs | Use public feed and hosted applicant form |
| LinkedIn Apply Connect | Restricted, certified ATS partner workflow | Discover public links only; no authenticated-account scraping |
| Playwright | Actionability checks and deterministic browser control | Required behavior for the external supervised adapter |

## Architecture

1. A user adds official Greenhouse, Lever, or Ashby tenant slugs.
2. RAVEN fetches public JSON feeds server-side, strips markup, normalizes fields, and creates a stable SHA-256 fingerprint.
3. Duplicate jobs collapse by source URL or fingerprint.
4. A deterministic scorer compares canonical skills/preferences with the description. The UI exposes matched skills, missing profile skills, and score components.
5. Tailoring reads the canonical resume as the only allowed source of candidate claims. Web results may inform employer context but cannot create candidate facts.
6. Unknown application answers become `NEEDS USER INPUT`; approval is blocked until resolved.
7. Every generated resume is an immutable version with model, token, cost, source, and checksum evidence.
8. RAVEN renders ATS-oriented PDF and DOCX files locally.
9. One target-specific approval authorizes one application ledger entry. The adapter receives the approved target, candidate defaults, PDF bytes, answers, checksum, expiry, and an idempotency key.
10. `submitted` requires a confirmation ID or confirmation text. Failed attempts remain unsubmitted and preserve an error/attempt counter.

## Security and authority boundaries

- API keys and adapter bearer tokens remain server-side and are never returned to the browser.
- Public job discovery does not use LinkedIn session cookies or bypass authentication.
- No application is sent merely because it has a high fit score.
- Resume claims are constrained to the canonical profile; gaps remain visible.
- Protected demographic questions and legal attestations are not inferred.
- One application ledger per job plus a stable fingerprint prevents duplicate submission.
- External writes require explicit, unexpired, target-specific approval.
- Status cannot become `submitted` without evidence.

## Three critique and improvement passes

### Pass 1 — Discovery truth

Replaced manual-only job entry with public official ATS feeds, normalized records, source provenance, stable fingerprints, deterministic scoring, and a bounded public-index supplement. A test exposed case-sensitive remote matching; it was corrected and regression-tested.

### Pass 2 — Application factuality and portability

Kept the canonical resume as the sole candidate-fact source, blocked unresolved questions from approval, added immutable checksums, and produced real PDF/DOCX artifacts instead of markdown-only downloads.

### Pass 3 — Submission safety and recoverability

Added apply URLs, stable idempotency keys, attempt counts, last-error state, server-rendered PDF payloads, exact target authority, and richer evidence fields. Automatic status transitions remain impossible without confirmation.

## Acceptance scorecard

| Requirement | Score | Evidence |
|---|---:|---|
| Official job discovery | 10/10 | Greenhouse, Lever, Ashby connectors; live Ashby test returned 58 jobs |
| Job normalization/deduplication | 10/10 | Stable fingerprint and unique database indexes |
| Explainable matching | 10/10 | Deterministic fit score and visible rationale |
| Current hiring research | 9/10 | SearXNG/public fallback with source snapshot; source quality still varies |
| Truthful targeted resume | 10/10 | Canonical-fact prompt, abstention, version/checksum ledger |
| PDF/DOCX artifacts | 10/10 | Binary signatures validated in tests |
| Application-question handling | 9/10 | Answers/basis persisted; unresolved facts block approval; user editing UI is the next refinement |
| Approval and duplicate controls | 10/10 | Target-specific approval, one ledger per job, idempotency key |
| Applicant-side browser submission | 7/10 | Typed adapter contract and evidence enforcement complete; host adapter/account setup still required |
| Auditability and UI insight | 10/10 | Sources, searches, scores, models, tokens, costs, versions, attempts, and evidence exposed |

Overall deployed software readiness: **9.5/10 for discovery and preparation**. External submission readiness is **7/10 until the supervised Chrome adapter is configured and validated against the owner's chosen ATS/account sessions**. This is an external setup dependency, not an API-key or model limitation.

## Verification performed

- Container build succeeded on Python 3.11.13.
- Unit suite: 17/17 passed.
- Full RAVEN E2E: passed (chat, date, provenance, Deep Research, voice, STT/TTS, web, graph).
- Career API E2E: passed; approval policy and secret-free response verified.
- Live read-only Ashby API test: 58 jobs returned and normalized with a valid fingerprint.
- Service health: `http://localhost:8080/api/health` returned 200 from a healthy container.

## Required owner setup before real submission

1. Complete the canonical profile and application defaults in Career Center.
2. Add the ATS tenant slugs for target employers and run discovery.
3. Review generated materials and fill every `NEEDS USER INPUT` answer.
4. Configure `CAREER_APPLY_URL`, `CAREER_APPLY_TOKEN`, and `CAREER_APPLY_ENABLED=true` for the supervised Chrome adapter.
5. Validate one non-destructive form inspection, then one real approved application, including CAPTCHA/MFA takeover and confirmation capture.

