import argparse
import base64
import hashlib
import io
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from PIL import Image
from pipeline.utils import (
    ROOT,
    compute_hash,
    is_cached,
    load_and_validate,
    log_run,
    save_cache,
    with_retry,
)

IMAGE_DIR = ROOT / "outputs" / "images"
PRIMARY_MODEL = os.getenv("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")
FALLBACK_MODEL = "@cf/black-forest-labs/flux-1-schnell"
# Only pass input_image_0 on close-up portraits so wide/prop shots (farm, sewing machine) keep full scene framing
PORTRAIT_CONDITIONED_SHOTS = {"shot_02", "shot_04", "shot_06", "shot_12"}


def _cf_credentials() -> tuple[str, str]:
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or "paste_your" in account_id or "your_" in account_id:
        raise RuntimeError("Missing CLOUDFLARE_ACCOUNT_ID in .env")
    if not api_token or "paste_your" in api_token or "your_" in api_token:
        raise RuntimeError("Missing CLOUDFLARE_API_TOKEN in .env")
    return account_id, api_token


def _to_png_bytes(raw_bytes: bytes, width: int = 1280, height: int = 720) -> bytes:
    with Image.open(io.BytesIO(raw_bytes)) as im:
        rgb = im.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        rgb.save(buf, format="PNG")
        return buf.getvalue()


def _parse_cf_response(resp: requests.Response) -> bytes:
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("image/"):
        return resp.content
    data = resp.json()
    b64 = data.get("result", {}).get("image")
    if not b64:
        raise RuntimeError(f"Unexpected Cloudflare payload: {str(data)[:250]}")
    return base64.b64decode(b64)


def _invoke_model(
    model: str,
    prompt: str,
    seed: int,
    width: int,
    height: int,
    ref_image: Path | None = None,
) -> bytes:
    account_id, api_token = _cf_credentials()
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {api_token}"}

    def _call() -> bytes:
        if "flux-2" in model:
            form_data = {
                "prompt": (None, prompt),
                "seed": (None, str(seed)),
                "width": (None, str(width)),
                "height": (None, str(height)),
            }
            if ref_image and ref_image.exists():
                form_data["input_image_0"] = (
                    ref_image.name,
                    ref_image.read_bytes(),
                    "image/png",
                )
            resp = requests.post(url, headers=headers, files=form_data, timeout=90)
        else:
            payload = {"prompt": prompt, "seed": seed, "steps": 4}
            resp = requests.post(url, headers=headers, json=payload, timeout=90)

        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:250]}")
        return _to_png_bytes(_parse_cf_response(resp), width, height)

    return with_retry(_call, retries=3, backoff=2.0)


def generate_image(
    prompt: str,
    seed: int,
    width: int = 1280,
    height: int = 720,
    ref_image: Path | None = None,
) -> tuple[bytes, str, dict]:
    try:
        img_bytes = _invoke_model(PRIMARY_MODEL, prompt, seed, width, height, ref_image)
        return img_bytes, PRIMARY_MODEL, {
            "width": width,
            "height": height,
            "conditioned": bool(ref_image and ref_image.exists()),
        }
    except Exception as primary_err:
        print(f"  [WARN] {PRIMARY_MODEL} failed ({primary_err}); switching to {FALLBACK_MODEL}")
        img_bytes = _invoke_model(FALLBACK_MODEL, prompt, seed, width, height, None)
        return img_bytes, FALLBACK_MODEL, {
            "width": width,
            "height": height,
            "fallback_from": PRIMARY_MODEL,
        }


def build_ref_prompt(sb: dict) -> str:
    return (
        f"Medium close-up golden reference portrait of {sb['character_sheet']['description']}, "
        f"wearing a white handwoven Ethiopian gabi cotton shawl over a collared shirt, "
        f"standing outdoors in warm Ethiopian highland sunlight. {sb['style_block']}"
    )


def build_contact_sheet(shots: list[dict]) -> None:
    tiles = []
    for shot in shots:
        p = IMAGE_DIR / f"{shot['shot_id']}.png"
        if p.exists():
            with Image.open(p) as im:
                tiles.append(im.convert("RGB").resize((320, 180), Image.Resampling.LANCZOS))
    if not tiles:
        return
    cols = 7
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 320, rows * 180), (18, 18, 18))
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % cols) * 320, (idx // cols) * 180))
    sheet.save(IMAGE_DIR / "contact_sheet.png", format="PNG")
    print(f"Updated {IMAGE_DIR / 'contact_sheet.png'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref-candidates", type=int, default=0)
    args = parser.parse_args()
    sb = load_and_validate()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    ref_prompt = build_ref_prompt(sb)
    base_seed = int(sb["character_sheet"]["seed"])

    if args.ref_candidates > 0:
        for i in range(args.ref_candidates):
            seed = base_seed + i
            out_path = IMAGE_DIR / f"ref_candidate_{i + 1}.png"
            t0 = time.perf_counter()
            img_bytes, model_used, params = generate_image(ref_prompt, seed)
            latency = time.perf_counter() - t0
            out_path.write_bytes(img_bytes)
            log_run("reference_candidate", f"ref_{i + 1}", model_used, params, seed, latency, 0.0)
            print(f"[CANDIDATE]  {out_path.name} (seed={seed}, {latency:.2f}s, {model_used})")
        return

    ref_path = ROOT / sb["character_sheet"]["reference_image"]
    ref_hash = compute_hash({"prompt": ref_prompt, "seed": base_seed, "style_block": sb["style_block"]})

    if is_cached("character_reference_sheet", ref_hash, ref_path):
        print(f"[CACHE HIT]  {ref_path.name}")
    else:
        t0 = time.perf_counter()
        img_bytes, model_used, params = generate_image(ref_prompt, base_seed)
        latency = time.perf_counter() - t0
        ref_path.write_bytes(img_bytes)
        save_cache("character_reference_sheet", ref_hash)
        log_run("reference_sheet", "ref_sheet", model_used, params, base_seed, latency, 0.0)
        print(f"[GENERATED]  {ref_path.name} ({latency:.2f}s, {model_used})")

    ref_sha = hashlib.sha256(ref_path.read_bytes()).hexdigest()

    for shot in sb["shots"]:
        sid = shot["shot_id"]
        out_png = IMAGE_DIR / f"{sid}.png"
        use_ref = ref_path if sid in PORTRAIT_CONDITIONED_SHOTS else None
        full_prompt = f"{shot['image_prompt']} {sb['style_block']}"
        shot_hash = compute_hash({
            "shot_id": sid,
            "prompt": full_prompt,
            "seed": shot["seed"],
            "conditioned": bool(use_ref),
            "ref_sha256": ref_sha if use_ref else "none",
        })

        if is_cached(f"keyframe_{sid}", shot_hash, out_png):
            print(f"[CACHE HIT]  {sid}.png")
            continue

        t0 = time.perf_counter()
        img_bytes, model_used, params = generate_image(
            full_prompt, int(shot["seed"]), ref_image=use_ref
        )
        latency = time.perf_counter() - t0
        out_png.write_bytes(img_bytes)
        save_cache(f"keyframe_{sid}", shot_hash)
        log_run("keyframes", sid, model_used, params, int(shot["seed"]), latency, 0.0)
        print(f"[GENERATED]  {sid}.png ({latency:.2f}s, {model_used}, conditioned={bool(use_ref)})")

    build_contact_sheet(sb["shots"])


if __name__ == "__main__":
    main()
