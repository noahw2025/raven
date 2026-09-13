# Local media model manifest

Validated on 2026-09-02 with ComfyUI 0.34.0, Python 3.13.14,
PyTorch 2.13.0+cu130, and an NVIDIA RTX 3060 12 GB.

| Purpose | Model | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Image | `sd_xl_base_1.0.safetensors` | 6,938,078,334 | `31E35C80FC4829D14F90153F4C74CD59C90B779F6AFE05A74CD6120B893F7E5B` |
| Video diffusion | `wan2.1_t2v_1.3B_fp16.safetensors` | 2,838,303,560 | `BE531024CD9018CB5B48C40CFBB6A6191645B1C792EB8BF4F8C1C6E10F924DC5` |
| Video text encoder | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6,735,906,897 | `C3355D30191F1F066B26D93FBA017AE9809DCE6C627DDA5F6A66EAA651204F68` |
| Video VAE | `wan_2.1_vae.safetensors` | 253,815,318 | `2FC39D31359A4B0A64F55876D8FF7FA8D780956AE2CB13463B0223E15148976B` |

The runtime and model directory is intentionally excluded from source control.
All generation is local and ComfyUI is launched with paid API nodes disabled.
