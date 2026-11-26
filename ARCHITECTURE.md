# System Architecture (`ARCHITECTURE.md`)

## 1. Pipeline DAG & Stage Boundaries

The studio is implemented as a deterministic Directed Acyclic Graph (DAG) orchestrated by `Makefile` around a single JSON contract (`storyboard.json`). Each stage reads `storyboard.json`, validates schema invariants, checks content-addressed SHA-256 cache markers in `outputs/.cache/`, executes only invalidated work, logs telemetry to `runs.jsonl`, and writes standardized files for downstream stages.

```text
                        +------------------------+
                        |    storyboard.json     |
                        | (14 shots, seeds, cues)|
                        +-----------+------------+
                                    |
                     [schema/storyboard.schema.json]
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
        v                           v                           v
+---------------+          +----------------+          +----------------+
|  Addis AI TTS |          | Cloudflare AI  |          | Chamber Synth  |
| (Afaan Oromoo)|          | FLUX.2 klein 4B|          | (D minor, 68BPM|
+-------+-------+          +--------+-------+          |  3 candidates) |
        |                           |                  +--------+-------+
        v                           v                           |
outputs/audio/              outputs/images/                     |
shot_01..14.wav             ref_gammachuu_sheet.png             |
(44.1kHz mono)              shot_01..14.png (1280x720)          |
        |                           |                           |
        |               +-----------+-----------+               |
        |               |                       |               |
        |               v                       v               |
        |      +----------------+      +----------------+       |
        |      | Wan 2.2 TI2V-5B|      | FFmpeg Ken     |       |
        |      | (8 Hero Shots, |      | Burns Fallback |       |
        |      | Kaggle T4 FP16)|      | (6 Shots)      |       |
        |      +--------+-------+      +--------+-------+       |
        |               |                       |               |
        |               +-----------+-----------+               |
        |                           |                           |
        |                           v                           |
        |                   outputs/video/                      |
        |                   shot_01..14.mp4                     |
        |                           |                           |
        +---------------------------+---------------------------+
                                    |
                                    v
                       +------------------------+
                       |  pipeline/assemble.py  |
                       | - Speech EQ (-5dB@1.8k)|
                       | - Sidechain Duck (8:1) |
                       | - Loudnorm (-14 LUFS)  |
                       | - Subtitles + 3s Card  |
                       +-----------+------------+
                                   |
                   +---------------+---------------+
                   |                               |
                   v                               v
      outputs/video/final_9x16.mp4    outputs/video/final_16x9.mp4
         (1080x1920, <= 90.0s)           (1920x1080, <= 90.0s)
```

## 2. Schema Contract & Invariants (`schema/storyboard.schema.json`)

`pipeline/utils.py:load_and_validate()` validates `storyboard.json` before any stage runs:

- **Required Top-Level Keys:** `title`, `language`, `character_sheet`, `style_block`, `music`, `end_card`, and `shots`.
- **Required Per-Shot Keys:** `shot_id`, `duration_s`, `narration_om`, `subtitle_en`, `image_prompt`, `motion_prompt`, `ken_burns_preset`, and `seed`.
- **Hard Runtime Invariant:** $\sum_{i=1}^{14} \text{duration\_s}_i + \text{end\_card.duration\_s} \le 90.0\text{s}$.

## 3. Content-Addressed SHA-256 Caching (`outputs/.cache/`)

Every stage computes a canonical JSON SHA-256 digest over all upstream dependencies:

- **Reference Portrait (`character_reference_sheet`):** `sha256(ref_prompt, seed, style_block)`
- **Keyframes (`keyframe_shot_XX`):** `sha256(shot_id, full_prompt, seed, conditioned, ref_sha256)`
- **Video Clips (`shot_video_shot_XX`):** `sha256(shot_id, exact_wav_duration_s, motion_prompt, ken_burns_preset, seed, keyframe_sha256, kaggle_clip_sha256)`
- **Music Score (`music_score`):** `sha256(music_cfg, selected_candidate, candidate_wav_sha256)`

When an output file exists and its `.sha256` marker matches, the stage logs `[CACHE HIT]` and skips execution. Changing a single shot's `seed`, `image_prompt`, or `narration_om` invalidates only that shot's downstream artifacts and re-runs final assembly.

## 4. Resilience, Retries & Graceful Degradation

- **Exponential Backoff (`pipeline/utils.py:with_retry`):** External REST calls retry up to 3 times (`2.0s`, `4.0s`, `8.0s` backoff) on transient HTTP `429`/`5xx` or network timeouts.
- **Image Model Fallback & Format Normalization (`pipeline/keyframes.py`):** Calls `@cf/black-forest-labs/flux-2-klein-4b` first and falls back automatically to `@cf/black-forest-labs/flux-1-schnell`. `_to_png_bytes()` decodes raw responses via Pillow and saves uniform `1280×720` RGB PNGs to prevent MIME mismatches.
- **Hybrid Cloud + Local Motion (`pipeline/shots.py`):** Imports `Wan-AI/Wan2.2-TI2V-5B-Diffusers` MP4 clips from `outputs/kaggle_import/video/` for the 8 high-action hero beats and renders deterministic FFmpeg `zoompan` clips for the remaining 6 shots (and for offline single-shot demo runs).
- **Audio Mastering Chain (`pipeline/assemble.py`):**
  1. Concatenates the 14 per-shot `44.1 kHz` mono WAV stems into a continuous narration stem (`highpass=f=85`).
  2. Attenuates the classical score (`volume=0.22`), cuts `-5 dB` at `1800 Hz` (`Q=1.2`) to open an acoustic pocket for speech intelligibility, and applies `2.0s` fade-in / `3.0s` fade-out.
  3. Ducks the score under narration via `sidechaincompress=threshold=0.015:ratio=8:attack=200:release=1600`.
  4. Normalizes final stereo loudness to `-14 LUFS` (`I=-14:TP=-1.5:LRA=11`) and appends a `3.0`-second AI disclosure card.
- **Secret Hygiene & Telemetry:** Credentials remain strictly in `.env` (excluded via `.gitignore`). Every model call appends a structured JSON record (`timestamp`, `stage`, `shot_id`, `model`, `params`, `seed`, `latency_s`, `gpu_minutes`, `cost_usd`, `status`) to `runs.jsonl`.
