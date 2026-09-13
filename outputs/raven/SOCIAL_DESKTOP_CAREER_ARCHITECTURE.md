# RAVEN Social, Desktop, and Career Architecture

Updated: 2026-08-09

## What Hermes already provides

Hermes is the execution harness beneath RAVEN, not the entire product. Its repository and current documentation provide a plugin/skill system, tool routing, long-running agent execution, channel integrations, MCP support, and desktop foundations. RAVEN adds the user-facing authority model, domain records, provider evidence, and approval workflows.

- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hermes Tool Gateway](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/tool-gateway.md)
- [Hermes skills catalog](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/skills-catalog.md)
- [Hermes desktop architecture](https://github.com/nousresearch/hermes-agent/blob/main/apps/desktop/README.md)

## Social pipeline implemented in this pass

```text
Campaign brief
  -> active text adapter (local Ollama/Qwen3 today; OpenAI interchangeable)
  -> three structured drafts + hashtags + media briefs
  -> Postgres campaign/content ledger
  -> versioned media asset (local SDXL image or Wan 2.1 video through the verified ComfyUI queue/history/artifact adapter)
  -> public HTTPS media URL
  -> explicit Trust Center approval
  -> Instagram container + publish API
  -> external media ID + immutable audit/event evidence
```

The Social Studio is functional for campaign creation and local text generation. Each call records provider, model, input/output tokens, latency, and estimated API cost. Instagram publishing code exists but remains honestly unavailable until a Professional account, approved permission, server-side token, public media URL, and the explicit server enable flag are present.

Meta's official API uses a container-then-publish flow. Media must be reachable by Meta on a public server. Content publishing is for Instagram Professional accounts and requires the relevant publish permission. See Meta's [official Instagram API collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) and [image-container request](https://www.postman.com/meta/instagram/request/23987686-f4b5a72d-a125-4080-8968-93de1a549e68).

### Server-only setup

Set these values in `outputs/raven/.env`; never put them into frontend code:

```dotenv
INSTAGRAM_API_VERSION=<version enabled for the Meta app>
INSTAGRAM_USER_ID=<professional-account-id>
INSTAGRAM_ACCESS_TOKEN=<server-side-token>
INSTAGRAM_PUBLISH_ENABLED=false
COMFYUI_URL=http://host.docker.internal:8188
```

Keep publishing disabled while verifying the connection and media workflow. Change it to `true` only after a sandbox post passes. The UI intentionally has no secret input.

For local media, [ComfyUI](https://github.com/comfyanonymous/ComfyUI) is the adapter boundary. RAVEN now binds the approved prompt node, hashes and queues the API-format workflow, monitors history, verifies an output record, and proxies the artifact to the authenticated UI. A checkpoint is not silently downloaded: model size, license, VRAM, and output quality still require owner selection and testing. Remotion remains a strong programmatic video renderer, subject to its license terms: [Remotion](https://github.com/remotion-dev/remotion).

## Desktop control design

Docker should not be given unrestricted access to the Windows host. RAVEN will use a signed, least-privilege host companion with an explicit allowlist:

1. RAVEN prepares an action such as `launch steam` or `open discord channel <guild>/<channel>`.
2. Trust Center shows the executable/URI, origin mission, reason, and reversibility.
3. The owner approves when required.
4. The Windows companion accepts only a typed allowlisted command, launches the application or deep link, and returns process/window evidence.
5. RAVEN stores the request, result, timestamp, and verification artifact.

Initial commands will be `steam.launch`, `discord.launch`, and `discord.open_channel`. Arbitrary PowerShell, shell strings, filesystem paths, and credential extraction are outside the contract.

## Career automation implemented

The Career Center is now a visible application operating system, not a blind mass-apply bot. Every job retains its source URL, description, saved questions, current research snapshot and URLs, immutable resume versions and checksums, cover letter, answer basis, fit score, gaps, approval, model usage, and submission evidence.

Working locally now:

1. Save one canonical candidate profile and complete factual career history.
2. Import a target job, its full description, source URL, and application prompts.
3. Research current company/role hiring signals through SearXNG.
4. Generate a targeted ATS-oriented Markdown resume, cover letter, fit score, strengths, gaps, and grounded prompt answers through the active model adapter.
5. Return `NEEDS USER INPUT` when the canonical profile cannot support an answer.
6. Download resume and cover-letter versions with a SHA-256 package checksum.
7. Request a target-specific decision in Trust Center.
8. Record owner-observed submission confirmation for a manually submitted application.

External automatic form submission is implemented as a typed adapter boundary but remains disabled until a supervised browser worker is connected. Configure it server-side:

```dotenv
CAREER_APPLY_URL=http://host.docker.internal:<port>/v1/apply
CAREER_APPLY_TOKEN=<server-only-token>
CAREER_APPLY_ENABLED=false
```

The adapter receives only an approved target, candidate header facts, targeted resume, cover letter, prompt answers, checksum, and approval record. RAVEN accepts success only when the adapter returns `submitted: true` plus a confirmation ID or confirmation text. A timeout, browser error, ambiguous page, or missing confirmation leaves the application unsubmitted.

Recommended open-source building blocks:

- [JobSync](https://github.com/Gsync/jobsync): best product pattern for private self-hosted tracking, Greenhouse/Lever discovery, application analytics, resume records, and MCP approvals.
- [Resume Matcher](https://github.com/srbhr/Resume-Matcher): strongest current local/provider-neutral tailoring foundation; supports Ollama, multiple cloud providers, Docker, PDF export, and cover letters.
- [ApplyPilot](https://github.com/Pickle-Pixel/ApplyPilot): useful reference for a staged autonomous application pipeline, but browser submission must be isolated and tested per site.
- [AIHawk](https://github.com/feder-cr/jobs_applier_ai_agent_aihawk): historically important reference, but its original repository is archived and third-party provider plugins were removed. It should not be the primary dependency.

Remaining implementation order:

1. Read-only Greenhouse/Lever feed discovery and deduplication.
2. Rendered PDF/DOCX resume templates in addition to the current Markdown downloads.
3. A signed browser worker for one ATS at a time, beginning with Greenhouse.
4. Screenshot/DOM confirmation capture and failure replay.
5. Follow-up reminders, interview stages, and outcome analytics.

## Provider interchangeability

Domain workflows depend on typed outputs, not a vendor SDK. Text generation uses the active RAVEN provider adapter; media uses a ComfyUI boundary; publishing uses a platform adapter; desktop uses a host-companion boundary. Each adapter reports capability, configuration state, model/provider, cost, and evidence. A connector is never labeled ready until an authenticated check succeeds.
