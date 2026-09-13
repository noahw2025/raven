# RAVEN

A local-first voice assistant and agent workspace for research, knowledge, software projects, career workflows, and content creation.

## Project layout

The application lives in **[`outputs/raven`](outputs/raven)**. This layout preserves the existing Docker build paths and local installation. **[`work/hermes-agent`](work/hermes-agent)** is a pinned upstream Git submodule, not a second copy of private application state.

```text
outputs/raven/        RAVEN application, Docker stack, Windows helpers, tests, docs
work/hermes-agent/   Pinned open-source Hermes dependency
```

## Clone and open

```powershell
git clone --recurse-submodules https://github.com/noahw2025/raven.git
Set-Location raven
code .
```

If already cloned without dependencies, run `git submodule update --init --recursive`.

Read the [application guide](outputs/raven/README.md) before starting. Copy `outputs/raven/.env.example` to `outputs/raven/.env`, set fresh local passwords/secrets, and configure only the providers you want to use. The local `.env` is intentionally **not** included in GitHub. Docker Desktop's Linux engine and appropriate local GPU/model setup are needed; credentials and model downloads are not supplied by this repository.

Run `outputs/raven/start-raven.ps1` from PowerShell. The application is normally available at **http://localhost:8080**. Optional Windows desktop control and ComfyUI require their local setup. Check paths such as `RAVEN_PROJECTS_ROOT` on a different computer.

## Development status

This is the current development snapshot, **not a claim that every feature is production-ready**. See [snapshot status](outputs/raven/docs/GITHUB_SNAPSHOT.md), [architecture](outputs/raven/RAVEN_SYSTEM_BLUEPRINT.md), and [readiness](outputs/raven/docs/REQUIREMENTS_AND_READINESS.md).

In particular, the new World geospatial integration is still in progress: public providers and structured controls have been tested, but globe rendering requires further security-compatible integration work. Existing local code, including that unfinished work, is preserved here.

## What is deliberately excluded

API keys, OAuth tokens, local databases/memories, model weights, Python environments, generated media, screenshots, logs, and private runtime state. GitHub backs up the source code, **not** your personal RAVEN data or configuration.

Third-party code retains its original license. See the [World notices](outputs/raven/docs/WORLD_THIRD_PARTY_NOTICES.md) and Hermes's upstream license. No license for redistributing the RAVEN-specific code is granted by this initial private snapshot.
