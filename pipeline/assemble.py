import argparse
import math
import re
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.utils import ROOT, load_and_validate, log_run

AUDIO_DIR = ROOT / "outputs" / "audio"
IMAGE_DIR = ROOT / "outputs" / "images"
VIDEO_DIR = ROOT / "outputs" / "video"
CACHE_DIR = ROOT / "outputs" / ".cache"

FONT_SANS = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf"


def get_duration(media_path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ]
    ).decode().strip()
    return float(out)


def fmt_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _srt_ts_to_ass(ts: str) -> str:
    # Convert HH:MM:SS,mmm -> H:MM:SS.cc
    h, m, rest = ts.strip().split(":")
    s, ms = rest.split(",")
    cs = int(round(int(ms) / 10.0))
    if cs >= 100:
        cs = 99
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"


def _escape_ass_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\r\n", "\n")
        .replace("\n", r"\N")
    )


def _srt_to_ass(
    srt_path: Path,
    ass_path: Path,
    width: int,
    height: int,
    font_size: int,
    margin_v: int,
) -> Path:
    raw = srt_path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\r?\n\r?\n+", raw)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1,2,54,54,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for block in blocks:
        parts = [ln for ln in block.splitlines() if ln.strip()]
        if len(parts) < 2:
            continue
        time_idx = 1 if "-->" in parts[1] else 0
        if "-->" not in parts[time_idx]:
            continue
        start_str, end_str = [p.strip() for p in parts[time_idx].split("-->")]
        caption = "\n".join(parts[time_idx + 1 :])
        lines.append(
            f"Dialogue: 0,{_srt_ts_to_ass(start_str)},{_srt_ts_to_ass(end_str)},"
            f"Default,,0,0,0,,{_escape_ass_text(caption)}\n"
        )
    ass_path.write_text("".join(lines), encoding="utf-8")
    return ass_path


def build_synced_audio_and_srt(shots: list[dict], regen_srt: bool = False) -> tuple[Path, Path, float]:
    concat_list = CACHE_DIR / "audio_concat.txt"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    srt_entries = []
    cursor = 0.0

    for idx, shot in enumerate(shots, start=1):
        wav = AUDIO_DIR / f"{shot['shot_id']}.wav"
        if not wav.exists():
            raise FileNotFoundError(f"Missing audio file: {wav}")
        dur = get_duration(wav)
        lines.append(f"file '{wav.resolve()}'")
        srt_entries.append(
            f"{idx}\n{fmt_srt_time(cursor)} --> {fmt_srt_time(cursor + dur)}\n{shot['subtitle_en']}\n"
        )
        cursor += dur

    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    merged_wav = CACHE_DIR / "merged_narration.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(merged_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    srt_path = AUDIO_DIR / "subtitles.srt"
    if regen_srt or not srt_path.exists() or srt_path.stat().st_size == 0:
        srt_path.write_text("\n".join(srt_entries), encoding="utf-8")
    else:
        print(f"Using existing subtitles: {srt_path.relative_to(ROOT)}")
    return merged_wav, srt_path, get_duration(merged_wav)


def render_radio_cut(sb: dict, regen_srt: bool = False) -> None:
    t0 = time.perf_counter()
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    merged_wav, srt_path, total_dur = build_synced_audio_and_srt(sb["shots"], regen_srt=regen_srt)
    out_mp4 = VIDEO_DIR / "radio_cut.mp4"
    ass_path = _srt_to_ass(
        srt_path,
        CACHE_DIR / "radio_cut.ass",
        width=1080,
        height=1920,
        font_size=46,
        margin_v=110,
    )

    ambient_expr = (
        "0.025*sin(2*PI*146.83*t)+0.018*sin(2*PI*220.00*t)+0.014*sin(2*PI*293.66*t)"
    )
    sub_filter = f"subtitles={ass_path.relative_to(ROOT)}"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=1080x1920:r=24:d={total_dur:.3f}",
            "-i",
            str(merged_wav),
            "-f",
            "lavfi",
            "-i",
            f"aevalsrc={ambient_expr}:s=44100:d={total_dur:.3f}",
            "-filter_complex",
            f"[0:v]{sub_filter}[v];[1:a]aresample=44100[vo];[2:a]aresample=44100[bg];"
            "[vo][bg]amix=inputs=2:duration=first:weights=1 0.35[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(out_mp4),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    latency = time.perf_counter() - t0
    log_run(
        stage="assemble_radio_cut",
        shot_id="all",
        model="ffmpeg",
        params={"duration_s": round(total_dur, 2), "resolution": "1080x1920"},
        seed=None,
        latency_s=latency,
        cost_usd=0.0,
    )
    print(f"Radio cut ready: {out_mp4} ({total_dur:.2f}s, rendered in {latency:.2f}s)")


def ken_burns_clip(img_path: Path, dur: float, preset: str, out_clip: Path) -> None:
    """Render a jitter-free 1280x720 24fps Ken Burns clip via 4x subpixel oversampling."""
    frames = max(24, math.ceil(dur * 24))
    denom = max(1, frames - 1)
    if preset == "zoom_out_slow":
        zp = (
            f"zoompan=z='1.06-0.06*(on/{denom})':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps=24"
        )
    elif preset == "pan_right_slow":
        zp = (
            f"zoompan=z='1.06':"
            f"x='(iw-iw/zoom)*(0.15+0.70*(on/{denom}))':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps=24"
        )
    elif preset == "pan_left_slow":
        zp = (
            f"zoompan=z='1.06':"
            f"x='(iw-iw/zoom)*(0.85-0.70*(on/{denom}))':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps=24"
        )
    else:
        zp = (
            f"zoompan=z='1.0+0.06*(on/{denom})':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps=24"
        )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(img_path),
            "-vf",
            f"scale=5120:2880:force_original_aspect_ratio=increase:flags=bicubic,crop=5120:2880,{zp}",
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            str(out_clip),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _write_end_card_clip(
    out_clip: Path,
    w: int,
    h: int,
    end_dur: float,
    backdrop_img: Path | None,
) -> None:
    """Render a cinematic inspirational ending slide with movie-style sliding credit."""
    is_vertical = h > w
    kicker_sz = 30 if is_vertical else 26
    quote_sz = 50 if is_vertical else 46
    credit_sz = 36 if is_vertical else 32
    subcredit_sz = 26 if is_vertical else 24

    quote_lines = (
        ["One choice, quiet patience,", "and unbroken hope can", "transform generations."]
        if is_vertical
        else ["One choice, quiet patience, and unbroken hope", "can transform an entire generation."]
    )

    kicker_y = int(h * (0.28 if is_vertical else 0.21))
    quote_start_y = int(h * (0.34 if is_vertical else 0.30))
    quote_step = int(quote_sz * 1.38)
    rule_y = quote_start_y + len(quote_lines) * quote_step + int(h * 0.03)
    rule_w = int(w * (0.42 if is_vertical else 0.28))
    rule_x = (w - rule_w) // 2

    # Movie-style sliding text: rises smoothly from bottom edge up to rest below the gold rule
    slide_start_y = h + 40
    slide_end_y = rule_y + int(h * 0.06)
    slide_dist = slide_start_y - slide_end_y
    slide_dur = min(1.85, end_dur * 0.62)
    # Cubic ease-out expression: p = min(1, t/slide_dur); y = slide_start_y - slide_dist * (1 - pow(1-p, 3))
    slide_y_expr = (
        f"{slide_start_y}-{slide_dist}*(1-pow(1-min(1\\,t/{slide_dur:.2f})\\,3))"
    )
    subcredit_offset = int(credit_sz * 1.6)
    subcredit_y_expr = f"({slide_y_expr})+{subcredit_offset}"

    quote_alpha = "if(lt(t\\,0.45)\\,t/0.45\\,1)"
    credit_alpha = "if(lt(t\\,0.25)\\,t/0.25\\,1)"

    filters: list[str] = []
    if backdrop_img and backdrop_img.exists():
        filters.append(
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"gblur=sigma=22,eq=brightness=-0.40:saturation=0.70,vignette=PI/3.5"
        )
    else:
        filters.append("format=yuv420p")

    # Warm gold divider rule
    filters.append(
        f"drawbox=x={rule_x}:y={rule_y}:w={rule_w}:h=3:color=#E6B85C@0.85:t=fill"
    )
    # Kicker
    filters.append(
        f"drawtext=fontfile={FONT_SANS_BOLD}:text='MURTOO TOKKO  ·  ONE DECISION':"
        f"fontcolor=#E6B85C:fontsize={kicker_sz}:x=(w-text_w)/2:y={kicker_y}:alpha='{quote_alpha}'"
    )
    # Inspirational quote lines
    for i, line in enumerate(quote_lines):
        escaped = line.replace("'", r"\'").replace(":", r"\:")
        ly = quote_start_y + i * quote_step
        filters.append(
            f"drawtext=fontfile={FONT_SERIF_BOLD}:text='{escaped}':"
            f"fontcolor=#FFFDF7:fontsize={quote_sz}:shadowcolor=black@0.7:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y={ly}:alpha='{quote_alpha}'"
        )

    # Movie-style upward sliding credits
    filters.append(
        f"drawtext=fontfile={FONT_SANS_BOLD}:text='Prepared by Rabuma with AI':"
        f"fontcolor=white:fontsize={credit_sz}:shadowcolor=black@0.7:shadowx=2:shadowy=2:"
        f"x=(w-text_w)/2:y='{slide_y_expr}':alpha='{credit_alpha}'"
    )
    filters.append(
        f"drawtext=fontfile={FONT_SANS}:text='Story of Gammachuu  ·  Narrated in Afaan Oromoo':"
        f"fontcolor=#D6CFC2:fontsize={subcredit_sz}:shadowcolor=black@0.7:shadowx=1:shadowy=1:"
        f"x=(w-text_w)/2:y='{subcredit_y_expr}':alpha='{credit_alpha}'"
    )

    fade_out_st = max(0.0, end_dur - 0.5)
    filters.append(f"fade=t=in:st=0:d=0.45,fade=t=out:st={fade_out_st:.2f}:d=0.50")

    vf = ",".join(filters)
    if backdrop_img and backdrop_img.exists():
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(backdrop_img),
            "-t",
            f"{end_dur:.3f}",
            "-vf",
            vf,
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_clip),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x100E0C:s={w}x{h}:r=24:d={end_dur:.3f}",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_clip),
        ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_full_film(sb: dict, regen_srt: bool = False) -> None:
    t0 = time.perf_counter()
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    merged_wav, srt_path, story_dur = build_synced_audio_and_srt(sb["shots"], regen_srt=regen_srt)

    # Build normalized 1280x720 24fps intermediate clips for every shot
    clip_entries = []
    for shot in sb["shots"]:
        sid = shot["shot_id"]
        dur = get_duration(AUDIO_DIR / f"{sid}.wav")
        raw_vid = VIDEO_DIR / f"{sid}.mp4"
        img_file = IMAGE_DIR / f"{sid}.png"
        norm_clip = CACHE_DIR / f"norm_{sid}.mp4"

        if raw_vid.exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(raw_vid),
                    "-t",
                    f"{dur:.3f}",
                    "-vf",
                    "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=24",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(norm_clip),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif img_file.exists():
            ken_burns_clip(img_file, dur, shot["ken_burns_preset"], norm_clip)
        else:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=0x141414:s=1280x720:r=24:d={dur:.3f}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(norm_clip),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        clip_entries.append(f"file '{norm_clip.resolve()}'")

    vid_list = CACHE_DIR / "video_concat.txt"
    vid_list.write_text("\n".join(clip_entries) + "\n", encoding="utf-8")
    silent_story = CACHE_DIR / "story_silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(vid_list),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(silent_story),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Mix voice + ducked background score.wav (or soft ambient fallback)
    score_wav = AUDIO_DIR / "score.wav"
    mixed_audio = CACHE_DIR / "mixed_story.wav"
    end_dur = float(sb["end_card"]["duration_s"])
    end_audio = CACHE_DIR / "endcard_audio.wav"

    if score_wav.exists():
        music_eq = (
            "aresample=44100,highpass=f=60,"
            "equalizer=f=320:t=q:w=1.0:g=5,equalizer=f=850:t=q:w=0.9:g=6,"
            "acompressor=threshold=-24dB:ratio=3:attack=20:release=250:makeup=4"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(merged_wav),
                "-stream_loop",
                "-1",
                "-i",
                str(score_wav),
                "-filter_complex",
                "[0:a]aresample=44100,aformat=channel_layouts=stereo,asplit=2[vo][sc];"
                f"[1:a]{music_eq},atrim=0:{story_dur:.3f},volume=0.78[mus];"
                "[mus][sc]sidechaincompress=threshold=0.14:ratio=1.6:attack=200:release=500[ducked];"
                "[vo][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[out]",
                "-map",
                "[out]",
                "-ar",
                "44100",
                "-ac",
                "2",
                str(mixed_audio),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Continue score warmly into the end card (sampled before tail fade) and fade out smoothly
        score_dur = get_duration(score_wav)
        end_start = max(0.0, min(74.0, score_dur - end_dur - 5.0))
        fade_st = max(0.0, end_dur - 1.2)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{end_start:.3f}",
                "-t",
                f"{end_dur:.3f}",
                "-i",
                str(score_wav),
                "-af",
                f"{music_eq},volume=1.05,afade=t=in:st=0:d=0.35,afade=t=out:st={fade_st:.2f}:d=1.20",
                "-ar",
                "44100",
                "-ac",
                "2",
                str(end_audio),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        ambient_expr = "0.02*sin(2*PI*146.83*t)+0.015*sin(2*PI*220*t)"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(merged_wav),
                "-f",
                "lavfi",
                "-i",
                f"aevalsrc={ambient_expr}:s=44100:d={story_dur:.3f}",
                "-filter_complex",
                "[0:a]aresample=44100[vo];[1:a]aresample=44100[bg];[vo][bg]amix=inputs=2:duration=first[out]",
                "-map",
                "[out]",
                "-ar",
                "44100",
                "-ac",
                "2",
                str(mixed_audio),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={end_dur:.3f}",
                "-ar",
                "44100",
                "-ac",
                "2",
                str(end_audio),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    last_shot_img = IMAGE_DIR / f"{sb['shots'][-1]['shot_id']}.png"
    backdrop_img = last_shot_img if last_shot_img.exists() else None

    targets = [
        ("final_9x16.mp4", 1080, 1920, "scale=-2:1920,crop=1080:1920", 46, 110),
        ("final_16x9.mp4", 1920, 1080, "scale=1920:1080", 42, 55),
    ]

    for fname, w, h, crop_vf, font_sz, margin_v in targets:
        out_path = VIDEO_DIR / fname
        ass_path = _srt_to_ass(
            srt_path,
            CACHE_DIR / f"{fname}.ass",
            width=w,
            height=h,
            font_size=font_sz,
            margin_v=margin_v,
        )
        end_clip = CACHE_DIR / f"endcard_{w}x{h}.mp4"
        _write_end_card_clip(end_clip, w, h, end_dur, backdrop_img)

        sub_vf = f"subtitles={ass_path.relative_to(ROOT)}"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(silent_story),
                "-i",
                str(mixed_audio),
                "-i",
                str(end_clip),
                "-i",
                str(end_audio),
                "-filter_complex",
                f"[0:v]{crop_vf},{sub_vf},setsar=1[v_story];"
                "[2:v]setsar=1[v_end];"
                "[v_story][1:a][v_end][3:a]concat=n=2:v=1:a=1[v_all][a_raw];"
                "[a_raw]loudnorm=I=-14:TP=-1.0:LRA=11,aresample=44100[a_all]",
                "-map",
                "[v_all]",
                "-map",
                "[a_all]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "24",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(out_path),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Exported {out_path} ({get_duration(out_path):.2f}s)")

    latency = time.perf_counter() - t0
    log_run(
        stage="assemble_final",
        shot_id="all",
        model="ffmpeg",
        params={
            "formats": ["9:16", "16:9"],
            "loudness_target_lufs": -14,
            "score": score_wav.name if score_wav.exists() else "ambient_fallback",
        },
        seed=None,
        latency_s=latency,
        cost_usd=0.0,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radio-cut", action="store_true")
    parser.add_argument(
        "--regen-srt",
        action="store_true",
        help="Overwrite outputs/audio/subtitles.srt from storyboard.json and shot WAV durations.",
    )
    args = parser.parse_args()
    sb = load_and_validate()
    if args.radio_cut:
        render_radio_cut(sb, regen_srt=args.regen_srt)
    else:
        render_full_film(sb, regen_srt=args.regen_srt)


if __name__ == "__main__":
    main()
