import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.utils import (
    CACHE_DIR,
    compute_hash,
    is_cached,
    load_and_validate,
    log_run,
    save_cache,
    with_retry,
)

AUDIO_DIR = ROOT / "outputs" / "audio"
TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Charon")


def measure_duration_s(audio_path: Path) -> float:
    """Return the exact duration of an audio file in seconds using ffprobe."""
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        text=True,
    ).strip()
    return float(out)


def _parse_pcm_rate(mime_type: str) -> int:
    match = re.search(r"rate=(\d+)", mime_type)
    return int(match.group(1)) if match else 24000


def _convert_to_standard_wav(src_path: Path, dst_path: Path) -> None:
    """Normalize any audio file to 44.1kHz mono 16-bit PCM WAV."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src_path),
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(dst_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def synthesize_gemini_tts(text: str, language: str, out_wav: Path, model: str = TTS_MODEL) -> dict:
    """Generate speech via Gemini TTS REST API and write normalized 44.1kHz mono WAV."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment or .env")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    prompt_text = (
        f"Read the following narration naturally and warmly in language '{language}' "
        f"at a steady documentary pace:\n\n{text}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": TTS_VOICE,
                    }
                }
            },
        },
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini TTS HTTP {exc.code}: {err_detail}") from exc

    inline_data = None
    for candidate in body.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if "inlineData" in part:
                inline_data = part["inlineData"]
                break
        if inline_data:
            break

    if not inline_data or "data" not in inline_data:
        raise RuntimeError(f"Gemini TTS response missing inlineData audio: {body}")

    mime_type = inline_data.get("mimeType", "audio/L16;codec=pcm;rate=24000")
    raw_bytes = base64.b64decode(inline_data["data"])

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_wav.with_suffix(".tmp_tts")
    try:
        if "l16" in mime_type.lower() or "pcm" in mime_type.lower():
            sample_rate = _parse_pcm_rate(mime_type)
            tmp_raw_wav = out_wav.with_suffix(".tmp_raw.wav")
            try:
                with wave.open(str(tmp_raw_wav), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(raw_bytes)
                _convert_to_standard_wav(tmp_raw_wav, out_wav)
            finally:
                tmp_raw_wav.unlink(missing_ok=True)
        else:
            tmp_path.write_bytes(raw_bytes)
            _convert_to_standard_wav(tmp_path, out_wav)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"mime_type": mime_type, "voice": TTS_VOICE}


def run_narration(force: bool = False) -> float:
    storyboard = load_and_validate()
    language = storyboard["language"]
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    total_duration = 0.0

    for shot in storyboard["shots"]:
        shot_id = shot["shot_id"]
        narration_om = shot["narration_om"]
        out_wav = AUDIO_DIR / f"{shot_id}.wav"

        payload = {
            "shot_id": shot_id,
            "narration_om": narration_om,
            "language": language,
        }
        current_hash = compute_hash(payload)
        cache_key = f"narration_{shot_id}"
        hash_file = CACHE_DIR / f"{cache_key}.sha256"

        if not force and is_cached(cache_key, current_hash, out_wav):
            dur = measure_duration_s(out_wav)
            total_duration += dur
            print(f"{shot_id}: {dur:.3f}s (cached)")
            continue

        # Preserve pre-generated audio (e.g. Addis AI split via split_narration.py)
        # when no prior cache hash exists yet for this shot.
        if not force and out_wav.exists() and out_wav.stat().st_size > 0 and not hash_file.exists():
            t0 = time.monotonic()
            save_cache(cache_key, current_hash)
            dur = measure_duration_s(out_wav)
            total_duration += dur
            log_run(
                stage="narration",
                shot_id=shot_id,
                model="addis-ai-pregenerated",
                params={"language": language, "source": out_wav.name, "duration_s": round(dur, 3)},
                seed=shot.get("seed"),
                latency_s=time.monotonic() - t0,
                cost_usd=0.0,
                status="cached_pregenerated",
            )
            print(f"{shot_id}: {dur:.3f}s (pre-generated, cached)")
            continue

        t0 = time.monotonic()
        tts_meta = with_retry(lambda: synthesize_gemini_tts(narration_om, language, out_wav))
        latency = time.monotonic() - t0
        save_cache(cache_key, current_hash)
        dur = measure_duration_s(out_wav)
        total_duration += dur

        log_run(
            stage="narration",
            shot_id=shot_id,
            model=TTS_MODEL,
            params={
                "language": language,
                "voice": tts_meta["voice"],
                "mime_type": tts_meta["mime_type"],
                "duration_s": round(dur, 3),
            },
            seed=shot.get("seed"),
            latency_s=latency,
            cost_usd=0.0,
            status="success",
        )
        print(f"{shot_id}: {dur:.3f}s (generated via {TTS_MODEL})")

    print(f"Total narration duration: {total_duration:.3f}s")
    return total_duration


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or verify per-shot narration audio.")
    parser.add_argument("--force", action="store_true", help="Regenerate all shots via Gemini TTS.")
    args = parser.parse_args()
    run_narration(force=args.force)


if __name__ == "__main__":
    main()
