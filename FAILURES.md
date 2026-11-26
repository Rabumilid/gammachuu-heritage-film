# Failure Journal & Engineering Resolutions (`FAILURES.md`)

Seven real technical blockers encountered during development, diagnostic root causes, and permanent engineering resolutions.

## Failure 1: Cloudflare Workers AI JPEG-in-PNG MIME Mismatch
- **Where:** `pipeline/keyframes.py` & FFmpeg contact-sheet generation.
- **What Broke:** `ffmpeg -pattern_type glob -i "outputs/images/shot_*.png" -vf "tile=7x2" contact_sheet.png` failed with `Could not find codec parameters for stream 0 (Video: png, none): unspecified size`.
- **Root Cause:** Cloudflare Workers AI returned JPEG-encoded bytes inside responses saved with `.png` filenames; FFmpeg's `image2` PNG demuxer rejected the mismatched header.
- **What Was Tried & What Fixed It:** Added `_to_png_bytes()` in `pipeline/keyframes.py` using `PIL.Image.open(io.BytesIO(raw_bytes)).convert("RGB")` to normalize every response into a true `1280×720` RGB PNG before saving, plus built-in Pillow contact-sheet stitching.

## Failure 2: Multi-View Reference Sheet Layout Bleed in FLUX.2 [klein] 4B
- **Where:** `pipeline/keyframes.py` (Phase 2 initial keyframe generation).
- **What Broke:** Passing a 3-panel grey studio character turnaround (`input_image_0`) on every shot caused wide scenes (`shot_01`, `shot_10`, `shot_13`) to render with grey studio backgrounds instead of Ethiopian farms and tailoring workshops.
- **Root Cause:** FLUX.2 [klein] 4B unifies generation and image editing; conditioning every prompt on a multi-panel grey studio image anchored spatial layout too strongly.
- **What Was Tried & What Fixed It:** Replaced the 3-panel turnaround with a single contextual outdoor portrait (`ref_gammachuu_sheet.png`) and restricted `input_image_0` conditioning strictly to portrait shots (`PORTRAIT_CONDITIONED_SHOTS = {"shot_02", "shot_04", "shot_06", "shot_12"}`).

## Failure 3: Age-Bias Drift on `shot_02`
- **Where:** `storyboard.json` (`shot_02`).
- **What Broke:** Gammachuu appeared ~65 years old in `shot_02` despite appearing 38 in `shot_01` and `shot_04`.
- **Root Cause:** Using the word `"exhausted"` in an unconditioned medium shot activated age-related priors in the diffusion model.
- **What Was Tried & What Fixed It:** Rewrote `shot_02` (`seed=1102`) to specify `"exact same 38-year-old Ethiopian Oromo man with short black curly hair and neatly trimmed short beard... unwell and fatigued"` and enabled portrait reference conditioning on `shot_02`.

## Failure 4: ACE-Step 1.5 Python Version Rejection on Kaggle (`3.13.16`)
- **Where:** Kaggle Notebook Cell 1 (`pip install -e ./ACE-Step-1.5`).
- **What Broke:** Installation failed with `ERROR: Package 'ace-step' requires a different Python: 3.13.16 not in '<3.13,>=3.11'`, halting notebook execution.
- **Root Cause:** Kaggle's container runtime upgraded to Python `3.13.16`, while ACE-Step 1.5's `pyproject.toml` pins `<3.13` and `torch==2.10.0+cu128`.
- **What Was Tried & What Fixed It:** Installed runtime dependencies (`loguru`, `einops`, `vector-quantize-pytorch`, `toml`, `diskcache`, `numba`) directly and installed ACE-Step 1.5 with `pip install --no-deps --ignore-requires-python -e /kaggle/working/ACE-Step-1.5` so it reused Kaggle's CUDA PyTorch.

## Failure 5: Missing `ftfy` Tokenizer Dependency & `32×32` Patch Alignment in Wan 2.2
- **Where:** Kaggle Notebook Cell 2 (`WanImageToVideoPipeline`).
- **What Broke:** `WanImageToVideoPipeline` raised `NameError: name 'ftfy' is not defined` inside UMT5 prompt cleaning after a session reset, and logged a patch-alignment adjustment warning on `432×768`.
- **Root Cause:** `ftfy`, `sentencepiece`, and `protobuf` are absent from Kaggle's base image, and Wan 2.2's transformer patchifier requires height and width divisible by `32`.
- **What Was Tried & What Fixed It:** Installed `ftfy sentencepiece protobuf` in Cell 2, patched `wan_i2v_mod.ftfy = ftfy` in memory, and standardized draft dimensions to `768×416` (`24×32` by `13×32`).

## Failure 6: CUDA Out-of-Memory (`14.56 GiB` T4 Limit) on `Wan2.2-TI2V-5B`
- **Where:** Kaggle Notebook Cell 2 (`pipe.enable_model_cpu_offload()`).
- **What Broke:** `torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 108.00 MiB. GPU 0 has a total capacity of 14.56 GiB of which 14.81 MiB is free` during `vae.encode()`.
- **Root Cause:** `enable_model_cpu_offload()` moves full submodules (`11.4 GB` UMT5 encoder + `5B` DiT) onto GPU 0 simultaneously, leaving insufficient headroom for the `float32` 3D VAE.
- **What Was Tried & What Fixed It:** Switched to `pipe.enable_sequential_cpu_offload()`, loaded the VAE in `torch.float16` with `enable_tiling()` and `enable_slicing()`, set `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, and generated 33 frames (20 steps) across 8 hero shots with deterministic FFmpeg Ken Burns fallback for the remaining 6 shots.

## Failure 7: ACE-Step 1.5 `transformers` v5 Meta-Tensor `ResidualFSQ` Crash & LM Caption Drift
- **Where:** Kaggle Notebook Cell 3 (`AceStepHandler.initialize_service`).
- **What Broke:** `AutoModel.from_pretrained()` failed with `RuntimeError: Tensor.item() cannot be called on meta tensors` inside `vector_quantize_pytorch/residual_fsq.py`, and `thinking=True` rewrote the restrained underscore caption into a `76 BPM` acoustic guitar piece.
- **Root Cause:** `transformers` v5 defaults to `low_cpu_mem_usage=True`, instantiating `ResidualFSQ` on a meta device before asserting `(levels_tensor > 1).all()`.
- **What Was Tried & What Fixed It:** To protect the submission schedule after securing all Wan 2.2 video clips, built a deterministic D-minor (`68 BPM`) chamber-classical synthesizer (warm solo cello + sparse felt piano) generating 3 seeded candidates (`880201–880203`) directly into `outputs/kaggle_import/audio/` with full telemetry logging in `runs.jsonl`.
