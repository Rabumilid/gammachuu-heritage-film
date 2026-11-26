# Project Report: Gammachuu — An Automated Afaan Oromoo Heritage Short Film Pipeline

- **Author:** Rabuma Milisha Dugasa
- **Date:** November 26, 2026
- **Repository:** `gammachuu-heritage-film` (`make film`)
- **Deliverables:** `outputs/video/final_9x16.mp4` (`1080×1920`), `outputs/video/final_16x9.mp4` (`1920×1080`), and reproducible pipeline repository.

## 1. What We Set Out to Make and For Whom

**Gammachuu** (Afaan Oromoo for *"Joy"*) is an 87-second AI-generated heritage short film narrated in Afaan Oromoo with burned-in English subtitles and a suppressed D-minor chamber classical score. It tells a true-to-life family story of resilience: Gammachuu, an Ethiopian Oromo highland farmer, falls physically ill and can no longer plow his fields. Determined not to give up, he teaches himself to write by brass kerosene lantern light, travels to town with homemade *daabboo* bread wrapped by his wife, masters tailoring on a cast-iron treadle sewing machine, builds a thriving tailoring shop (*suuqii*), and educates his children.

The film serves two audiences:

- **Primary Audience:** Ethiopian and Oromo family members, elders, and youth watching on mobile phones (`9:16` vertical format), where authentic rural-to-urban family stories narrated in Afaan Oromoo are scarce.
- **Secondary Audience:** International peers and engineering reviewers watching the `16:9` horizontal cut with English subtitles.

To make the film reproducible rather than hand-edited, I built a deterministic studio in code (`Makefile` + Python + FFmpeg) around a schema-validated contract (`storyboard.json` + `schema/storyboard.schema.json`), with content-addressed SHA-256 caching (`outputs/.cache/`) and per-call telemetry (`runs.jsonl`).

## 2. Reflection & Learning From Our Audience and the Hardest Technical Problem

### What Our Audience Said and What Changed Because of It

Running two structured audience tests—first on an audio-only radio cut and second on the near-final dual-aspect cut—directly reshaped `storyboard.json` and the audio mix:

- **Pacing & Subtitles (User Test 1 — Radio Cut):** Three native/fluent listeners reviewed the 14-segment Afaan Oromoo narration before any images were rendered. A family elder noted that transitioning immediately from illness (`shot_04`) to night writing (`shot_05`) felt abrupt, prompting `0.4s` breathing pauses at act boundaries. An Oromo peer testing on a mobile screen observed that English subtitles over ~42 characters wrapped onto three lines, leading me to tighten all 14 `subtitle_en` captions to two concise lines inside the vertical safe area.
- **Visual Clarity, Age Continuity & Intelligibility (User Test 2 — Near-Final Cut):**
  - `shot_01` initially showed Gammachuu walking along a trail, which a family reviewer noted did not immediately read as farming; updating `shot_01` (`seed=1101`) to active tilling with a wooden *maresha* ox-plow established his agricultural livelihood in the opening three seconds.
  - `shot_02` aged Gammachuu prematurely because the adjective `"exhausted"` triggered elderly visual priors; replacing it with `"exact same 38-year-old Ethiopian Oromo man... unwell and fatigued"` (`seed=1102`) and enabling reference portrait conditioning fixed age continuity.
  - To ensure the classical cello and felt piano underscore never masked spoken Afaan Oromoo consonants on small phone speakers, I added a `-5 dB` EQ pocket at `1.8 kHz` (`Q=1.2`) alongside `8:1` sidechain ducking (`volume=0.22`) in `pipeline/assemble.py`.

### The Hardest Technical Problem: Running 5B Video Diffusion Within Kaggle T4 VRAM Limits

The hardest engineering blocker was running `Wan-AI/Wan2.2-TI2V-5B-Diffusers` on Kaggle's free Tesla T4 (`14.56 GiB` usable VRAM) alongside Python `3.13` runtime incompatibilities. Calling `pipe.enable_model_cpu_offload()` crashed with CUDA out of memory (`14.39 GiB` allocated) when the `11.4 GB` UMT5 encoder and `5B` transformer occupied GPU 0 simultaneously during `vae.encode()`.

I resolved this through three coordinated engineering changes:

1. Replacing `enable_model_cpu_offload()` with layer-by-layer `enable_sequential_cpu_offload()`, loading the VAE in `float16` with tiling and slicing enabled, and aligning dimensions to `768×416` (exact `32×32` transformer patch multiples) at `33` frames and `20` steps.
2. Splitting the 14-shot timeline into 8 high-action hero clips generated via Wan 2.2 on Kaggle and 6 close-up/intimate shots animated via deterministic FFmpeg `zoompan` (Ken Burns) in `pipeline/shots.py`, fitting comfortably inside free weekly GPU quotas while keeping local single-shot regeneration fast.
3. Importing Kaggle's `export_bundle` (`video/` and `kaggle_runs.jsonl`) directly into `outputs/kaggle_import/` and merging telemetry into `runs.jsonl`.

## 3. Suggested Practices Tested Honestly

### Practice That Beat My Instinct: Narration-First "Radio Cut" + Strict JSON Schema Contract

My instinct was to generate keyframes and video clips first and fit the narration to the visuals afterward. Following the suggested practice—recording and timing all 14 Afaan Oromoo narration WAVs first (`narration.py`), locking their exact `ffprobe` durations into `storyboard.json`, and enforcing the `<= 90.0s` total runtime via JSON Schema before generating any images—prevented wasted GPU rendering. Every video clip automatically trimmed or looped to match spoken delivery, and SHA-256 caching meant regenerating a single shot took seconds without touching the rest of the timeline.

### Practice That Did Not Work as Suggested: Multi-View Character Reference Sheet on Every Shot

The guide recommends generating a multi-view grey studio character turnaround sheet (`ref_gammachuu_sheet.png`) and conditioning every shot on it. On Cloudflare's distilled `FLUX.2 [klein] 4B`—which unifies generation and image editing in 4 steps—passing a 3-panel grey studio turnaround via `input_image_0` caused wide scenes (`shot_01`, `shot_10`, `shot_13`) to inherit grey studio backgrounds and erase the Ethiopian farms and cast-iron sewing machine.

I adapted the practice by replacing the 3-panel studio grid with a single contextual outdoor portrait and restricting `input_image_0` conditioning strictly to close-up portrait shots (`shot_02`, `shot_04`, `shot_06`, `shot_12`), while front-loading concrete Ethiopian cultural nouns in the first 15 words of unconditioned wide/prop shots. This achieved both facial consistency and rich environmental storytelling.

## 4. Curiosity Beyond the Floor ("Raising the Ceiling")

- **Low-Resource African Language Pipeline (Afaan Oromoo):** Rather than defaulting to English voiceover, I built the pipeline around Afaan Oromoo, auditing cultural pronunciation (*Gammachuu*, *daabboo*, *gabi*, *shaayii*) with native speakers and designing a frequency-pocket EQ (`-5 dB` at `1.8 kHz`) + `8:1` sidechain ducking chain tailored to preserve vocal clarity on mobile devices.
- **Cross-Provider Telemetry & Deterministic Score Fallback:** When `ACE-Step 1.5` hit a `transformers` v5 meta-tensor `ResidualFSQ` initialization crash on Kaggle's Python `3.13` runtime, I engineered a deterministic D-minor (`68 BPM`) chamber classical synthesizer (warm solo cello + sparse felt piano) that generated 3 seeded candidates (`880201–880203`) in `< 1.0s` and integrated both Kaggle and local JSONL telemetry into `pipeline/summarize_runs.py`.

## 5. What I Would Build Next

- **Lightweight Character LoRA:** Train a rank-16 FLUX LoRA on 12 curated portraits of Gammachuu so wide establishing shots (`shot_01`, `shot_13`, `shot_14`) maintain the same facial lock as conditioned close-ups without studio layout bleed.
- **Mobile Family Storyteller Web App (`Gradio` / `Hugging Face Space`):** Wrap `storyboard.json` generation and `make film` in a simple web interface where Ethiopian elders can speak a family story in Afaan Oromoo or Amharic on their phone and automatically receive a subtitled heritage short film.
- **Blind Preference Benchmark:** Conduct a 5-person blind preference evaluation comparing our `$0.00` open-weight pipeline (`Wan 2.2` + local chamber score) against paid frontier video and music models.
