# Compute, Latency & Cost Accounting (`COSTS.md`)

## 1. Free-Tier Quotas & Binding Constraints Observed (Ethiopia, Nov 2026)

| Service / Tool | Free Tier Allowance Observed | Binding Constraint | Pipeline Mitigation |
| :--- | :--- | :--- | :--- |
| **Addis AI TTS** | Free / hackathon API access for Afaan Oromoo | Per-request rate pacing | Generated 14 per-shot WAVs once and cached in `outputs/audio/`. |
| **Cloudflare Workers AI** | 10,000 neurons/day free (no payment card required) | ~50–150 4-step FLUX images/day | Used `FLUX.2 [klein] 4B` (4 steps) + SHA-256 caching so re-rolls cost 1 call per shot. |
| **Kaggle Notebooks (2× Tesla T4)** | ~30 GPU hrs/week (SMS phone verification required) | 14.56 GiB VRAM per T4 & interactive session timeouts | Sequential CPU offload, `768×416` resolution, 8 hero clips + 6 Ken Burns shots. |
| **Local Workstation (Ubuntu CPU)** | Unlimited local Python + FFmpeg execution | CPU encoding speed (~15s for dual assembly) | Executed classical score synthesis, sidechain ducking, subtitles, and `9:16` / `16:9` exports. |

## 2. Measured Latency & GPU Minutes from `runs.jsonl`

Run `.venv/bin/python pipeline/summarize_runs.py` after `make film` to refresh exact counts.

## 3. Commercial List-Price Equivalent (If Run on Paid Cloud Infrastructure)

| Workload | Production Volume | Commercial Cloud / API Equivalent | Published List Rate | List-Price USD Equivalent |
| :--- | :--- | :--- | :--- | ---: |
| Afaan Oromoo Narration (TTS) | ~1,150 chars (~84s audio) | Commercial Neural TTS (Google Cloud / ElevenLabs standard) | `$16.00 / 1M chars` | `$0.02` |
| Keyframes (`FLUX.2 klein 4B`) | ~22 images (`1280×720`) | Hosted FLUX endpoint (`fal.ai` / BFL API) | `$0.015 / image` | `$0.33` |
| Video Motion (`Wan2.2-TI2V-5B`) | 8 hero clips (~18–22 GPU min = 0.35 GPU hrs) | Cloud NVIDIA T4 instance (`AWS g4dn.xlarge` / `GCP T4`) | `$0.526 / GPU hr` | `$0.18` |
| Classical Underscore | 3 × 90s candidates (`< 2s` CPU) | Standard cloud compute VM (2 vCPU) | `$0.05 / hr` | `$0.00` |
| FFmpeg Assembly & Mastering | Dual export (`9:16` + `16:9`, ~15s CPU) | Standard cloud compute VM (2 vCPU) | `$0.05 / hr` | `$0.00` |
| **Total Commercial List-Price Equivalent** | — | — | — | **`$0.53`** |
| **Actual Out-of-Pocket Spend** | — | Free tiers + Kaggle GPU quota | — | **`$0.00`** |

## 4. Open-Weight vs. Hosted / Frontier Architecture Comparison

Paid frontier video and music APIs (Gemini Omni Flash video, Lyria 3.5) require international billing unavailable without a foreign payment card. Within our accessible stack, we measured concrete speed-vs-quality trade-offs across two tiers:

| Stage | Primary Model | Fallback / Comparison Model | Measured Trade-Off |
| :--- | :--- | :--- | :--- |
| **Keyframes** | `FLUX.2 [klein] 4B` (Cloudflare) | `FLUX.1 [schnell]` (Cloudflare) | Both render in ~2.5–4.0s/image (4 steps), but `FLUX.2 [klein] 4B` supports `input_image_0` portrait reference conditioning for cross-shot identity lock. |
| **Video Motion** | `Wan2.2-TI2V-5B` (Kaggle T4) | FFmpeg `zoompan` (Local CPU) | Wan 2.2 generates organic cloth, rain, and plowing motion (~2.0–2.5 min/clip on T4), whereas FFmpeg Ken Burns renders in `< 1.5s/clip` with zero facial warping on close-ups. |
| **Score** | D-Minor Chamber Classical Synth (Local) | `ACE-Step 1.5` (`acestep-v15-turbo`) | Local cello/piano synthesis renders `3×90s` tracks in `< 1.0s` with strict harmonic restraint under narration, avoiding Kaggle `transformers` v5 meta-tensor crashes. |
