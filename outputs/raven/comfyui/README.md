# RAVEN local ComfyUI media engine

ComfyUI 0.34.0 is installed in `.runtime/comfyui` using the official NVIDIA
portable distribution. `start-comfyui.ps1` starts it on port 8188 with CUDA,
low-VRAM scheduling, local-only models, and paid API nodes disabled.

Installed and acceptance-tested workflows:

- `comfyui-image-workflow.json`: SDXL 1.0, 768 x 768 PNG.
- `comfyui-video-workflow.json`: Wan 2.1 T2V 1.3B, 512 x 288, 17-frame VP9 WebM.

Run the complete stack from PowerShell with:

```powershell
Set-Location "C:\Users\ark73\Documents\Codex\2026-08-04\https-github-com-nousresearch-hermes-agent\outputs\raven"
.\start-raven.ps1
```

The first video after startup is slower because the UMT5 encoder and Wan model
must be loaded from disk. Close GPU-heavy games before generating media.

## Adapter contract

RAVEN mounts this directory read-only at `/config`. It chooses the image or
video API workflow based on the asset brief generated in Social Studio.

The workflow must contain a text-encoding node whose ID and text input match:

- `COMFYUI_IMAGE_PROMPT_NODE_ID` or `COMFYUI_VIDEO_PROMPT_NODE_ID` (both `6`)
- `COMFYUI_PROMPT_INPUT` (default `text`)

RAVEN substitutes only that bounded prompt field, hashes the complete workflow,
queues it through `POST /prompt`, monitors `/history/{prompt_id}`, and proxies the
verified artifact through an authenticated RAVEN endpoint. Model checkpoints stay
inside ComfyUI and are never uploaded to RAVEN or exposed in the browser.

`COMFYUI_URL=http://host.docker.internal:8188` is configured server-side. The UI
reports image and video workflow readiness separately and never fabricates an
artifact.
