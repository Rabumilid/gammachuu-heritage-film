import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "outputs" / "audio"
SB_PATH = ROOT / "storyboard.json"
TS_PATH = ROOT / "timestamps.json"

candidates = list(AUDIO_DIR.glob("full_narration_raw.*"))
if not candidates:
    sys.exit("Place your Addis AI audio at outputs/audio/full_narration_raw.mp3 (or .wav)")
src = candidates[0]

# 1. Convert to clean 44.1kHz mono WAV
clean_wav = AUDIO_DIR / "_clean_full.wav"
subprocess.run(
    ["ffmpeg", "-y", "-i", str(src), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(clean_wav)],
    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

total_dur = float(subprocess.check_output([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", str(clean_wav)
]).decode().strip())

sb = json.loads(SB_PATH.read_text(encoding="utf-8"))
shots = sb["shots"]

# 2. Load manual/saved timestamps.json only if it matches the current shot count
boundaries = None
if TS_PATH.exists():
    loaded = json.loads(TS_PATH.read_text(encoding="utf-8")).get("boundaries_s", [])
    if (
        isinstance(loaded, list)
        and len(loaded) == len(shots) + 1
        and all(loaded[i] < loaded[i + 1] for i in range(len(loaded) - 1))
        and loaded[-1] <= total_dur + 0.25
    ):
        boundaries = loaded
    else:
        print(
            f"{TS_PATH.name} has {len(loaded)} boundaries for {len(shots)} shots; recomputing...",
            file=sys.stderr,
        )

if boundaries is None:
    sil = subprocess.check_output(
        ["ffmpeg", "-i", str(clean_wav), "-af", "silencedetect=noise=-32dB:d=0.22", "-f", "null", "-"],
        stderr=subprocess.STDOUT
    ).decode()
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", sil)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", sil)]
    pause_mids = [(s + e) / 2.0 for s, e in zip(starts, ends) if 0.5 < s < total_dur - 0.5]

    # Count Oromo vowel clusters (syllables) per shot for proportional timing
    weights = [max(1, len(re.findall(r"[aeiouAEIOU]+", s["narration_om"]))) for s in shots]
    total_w = sum(weights)

    boundaries = [0.0]
    cum_w = 0
    num_shots = len(shots)
    for idx, w in enumerate(weights[:-1], start=1):
        cum_w += w
        remaining = num_shots - idx
        min_t = boundaries[-1] + 1.2
        max_t = total_dur - 1.2 * remaining
        if min_t >= max_t:
            min_t = boundaries[-1] + 0.3
            max_t = total_dur - 0.3 * remaining
        target_t = min(max((cum_w / total_w) * total_dur, min_t), max_t)
        # Snap to closest real pause within +/- 2.8 seconds of target
        valid_pauses = [
            p for p in pause_mids
            if min_t <= p <= max_t and abs(p - target_t) <= 2.8
        ]
        chosen = min(valid_pauses, key=lambda p: abs(p - target_t)) if valid_pauses else target_t
        boundaries.append(round(chosen, 3))
    boundaries.append(round(total_dur, 3))

    TS_PATH.write_text(json.dumps({"boundaries_s": boundaries}, indent=2) + "\n", encoding="utf-8")
    print(f"Saved auto-snapped cut points to {TS_PATH.name} ({len(shots)} shots)")

# 3. Slice shot_01.wav .. shot_N.wav so story + AI end card <= 90.0s
end_card_dur = sb["end_card"]["duration_s"]
max_story_dur = 90.0 - end_card_dur - 0.5  # 86.5s target ceiling
tempo = round(max(1.0, total_dur / max_story_dur), 3)

# Remove stale audio chunks beyond current shot count and stale narration caches
for old_wav in AUDIO_DIR.glob("shot_*.wav"):
    m = re.match(r"shot_(\d+)\.wav$", old_wav.name)
    if m and int(m.group(1)) > len(shots):
        old_wav.unlink()
cache_dir = ROOT / "outputs" / ".cache"
if cache_dir.exists():
    for old_hash in cache_dir.glob("narration_shot_*.sha256"):
        old_hash.unlink()

srt_lines = []
cursor = 0.0

def fmt_srt(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

for idx, shot in enumerate(shots, start=1):
    s_t, e_t = boundaries[idx - 1], boundaries[idx]
    out_wav = AUDIO_DIR / f"shot_{idx:02d}.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(clean_wav),
        "-ss", f"{s_t:.3f}", "-to", f"{e_t:.3f}",
        "-af", f"atempo={tempo},apad=pad_dur=0.15",
        "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(out_wav)
    ]).decode().strip())

    shot["duration_s"] = round(dur, 2)
    srt_lines.append(f"{idx}\n{fmt_srt(cursor)} --> {fmt_srt(cursor + dur)}\n{shot['subtitle_en']}\n")
    cursor += dur
    print(f"{out_wav.name}: {shot['duration_s']}s | {shot['subtitle_en'].splitlines()[0]}")

(AUDIO_DIR / "subtitles.srt").write_text("\n".join(srt_lines), encoding="utf-8")
SB_PATH.write_text(json.dumps(sb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
clean_wav.unlink(missing_ok=True)
print(f"\nTotal story: {cursor:.2f}s + {end_card_dur}s end card = {cursor + end_card_dur:.2f}s (tempo={tempo}x)")
