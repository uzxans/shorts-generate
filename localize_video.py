#!/usr/bin/env python3
"""
Video localization pipeline:
  - extract 48 kHz stereo source audio
  - transcribe English speech with Whisper word timestamps
  - translate segments to Russian
  - synthesize Russian voice-over via Yandex SpeechKit
  - create Russian SRT
  - mux H.264/AAC MP4 and optionally append an outro with a fade
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional.
    load_dotenv = None


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTRO = ROOT / "assets" / "frog.mp4"

if load_dotenv:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    printable = " ".join(shlex.quote(x) for x in cmd)
    print(f"$ {printable}")
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def ffprobe_json(path: Path) -> dict[str, Any]:
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
    ).stdout
    return json.loads(out)


def duration(path: Path) -> float:
    data = ffprobe_json(path)
    return float(data["format"]["duration"])


def video_stream(path: Path) -> dict[str, Any]:
    for stream in ffprobe_json(path).get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    raise RuntimeError(f"No video stream found in {path}")


def has_audio(path: Path) -> bool:
    return any(s.get("codec_type") == "audio" for s in ffprobe_json(path).get("streams", []))


def fps_value(rate: str) -> float:
    if "/" in rate:
        n, d = rate.split("/", 1)
        return float(n) / float(d)
    return float(rate)


def atempo_filter(factor: float) -> str:
    parts: list[float] = []
    factor = max(0.25, min(4.0, factor))
    while factor > 2.0:
        parts.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        parts.append(0.5)
        factor /= 0.5
    parts.append(factor)
    return ",".join(f"atempo={p:.6f}" for p in parts)


def auth_headers() -> dict[str, str]:
    iam = os.environ.get("YANDEX_IAM_TOKEN")
    api_key = os.environ.get("YANDEX_API_KEY") or os.environ.get("SPEECHKIT_API_KEY")
    if iam:
        return {"Authorization": f"Bearer {iam}"}
    if api_key:
        return {"Authorization": f"Api-Key {api_key}"}
    raise RuntimeError("Set YANDEX_IAM_TOKEN or YANDEX_API_KEY/SPEECHKIT_API_KEY in environment.")


def yandex_folder_id() -> str:
    folder_id = os.environ.get("YANDEX_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("Set YANDEX_FOLDER_ID in environment.")
    return folder_id


def extract_audio(input_path: Path, out_wav: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ]
    )


def transcribe(audio_wav: Path, model_name: str, out_json: Path, *, language: str | None = "en") -> dict[str, Any]:
    import whisper

    model = whisper.load_model(model_name)
    options: dict[str, Any] = {
        "task": "transcribe",
        "word_timestamps": True,
        "verbose": False,
    }
    if language:
        options["language"] = language
    result = model.transcribe(str(audio_wav), **options)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _plain_texts(texts: list[Any]) -> list[str]:
    return [str(item.get("text", "") if isinstance(item, dict) else item) for item in texts]


def translate_yandex(texts: list[Any]) -> list[str]:
    url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
    headers = auth_headers()
    headers["Content-Type"] = "application/json"
    payload = {
        "folderId": yandex_folder_id(),
        "texts": _plain_texts(texts),
        "sourceLanguageCode": "en",
        "targetLanguageCode": "ru",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Yandex Translate failed: {resp.status_code} {resp.text[:500]}")
    data = resp.json()
    return [item["text"] for item in data.get("translations", [])]


def deepseek_api_key() -> str | None:
    return os.environ.get("DEEPSEEK_API_KEY")


def _prompt_item_text(item: Any) -> str:
    if isinstance(item, dict):
        text = str(item.get("text", "")).strip()
        duration = float(item.get("duration", 0) or 0)
        max_chars = max(12, int(duration * 13)) if duration > 0 else 80
        return f"{text} [target {duration:.1f}s, max {max_chars} Russian chars]"
    return str(item).strip()


def build_deepseek_translation_prompt(texts: list[Any]) -> str:
    numbered = "\n".join(f"{idx + 1}. {_prompt_item_text(text)}" for idx, text in enumerate(texts))
    return (
        "Translate these English transcript segments into Russian for a short-form video voice-over.\n"
        "Goal: natural spoken Russian that keeps the original meaning, intent, emotion, and teaching point.\n"
        "Do not translate word-by-word. Adapt idioms and chart/design terms so a Russian viewer instantly understands them.\n"
        "Keep each line concise enough to fit the original timing and max character hint; prefer short punchy spoken phrases over long literary text.\n"
        "If a literal translation is too long, replace words with shorter natural Russian equivalents while preserving the meaning.\n"
        "If the source phrase is split across two segments, keep the Russian continuation natural across segments.\n"
        "Return ONLY a JSON array of strings with the same JSON array length and order. No markdown.\n\n"
        f"{numbered}"
    )


def translate_deepseek(texts: list[Any]) -> list[str]:
    api_key = deepseek_api_key()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set.")

    prompt = build_deepseek_translation_prompt(texts)
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior English-to-Russian audiovisual translator and dubbing editor. "
                        "You write concise, natural spoken Russian for voice-over, preserving meaning over literal wording."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        },
        timeout=120,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"DeepSeek translation failed: {resp.status_code} {resp.text[:500]}")

    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    translated = json.loads(content)
    if not isinstance(translated, list) or not all(isinstance(item, str) for item in translated):
        raise RuntimeError("DeepSeek returned non-list translation.")
    return translated


def translate_batch(texts: list[Any], provider: str) -> list[str]:
    if provider == "deepseek":
        return translate_deepseek(texts)
    if provider == "yandex":
        return translate_yandex(texts)
    if deepseek_api_key():
        try:
            return translate_deepseek(texts)
        except Exception as exc:
            print(f"   ⚠️  DeepSeek translate failed, trying Yandex: {exc}")
    return translate_yandex(texts)


def _join_segment_text(left: str, right: str) -> str:
    left = left.strip()
    right = right.strip()
    if not left:
        return right
    if not right:
        return left
    if left[-1] in ".!?…":
        return f"{left} {right}"
    return f"{left}. {right}"


def merge_transcript_segments_for_voiceover(
    segments: list[dict[str, Any]],
    *,
    max_gap: float = 0.35,
    max_chunk_duration: float = 5.5,
    max_chunk_chars: int = 260,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment["start"])
        end = float(segment["end"])
        if current is None:
            current = dict(segment)
            current["start"] = start
            current["end"] = end
            current["text"] = text
            continue

        gap = start - float(current["end"])
        chunk_duration = end - float(current["start"])
        joined_text = _join_segment_text(str(current.get("text", "")), text)
        can_merge = (
            gap <= max_gap
            and chunk_duration <= max_chunk_duration
            and len(joined_text) <= max_chunk_chars
        )
        if not can_merge:
            merged.append(current)
            current = dict(segment)
            current["start"] = start
            current["end"] = end
            current["text"] = text
            continue

        current["end"] = end
        current["text"] = joined_text
        current_words = list(current.get("words") or [])
        current_words.extend(segment.get("words") or [])
        if current_words:
            current["words"] = current_words

    if current is not None:
        merged.append(current)
    return merged


def translate_segments(segments: list[dict[str, Any]], out_json: Path, provider: str) -> list[dict[str, Any]]:
    texts = [s.get("text", "").strip() for s in segments]
    translated: list[str] = []
    chunk_size = 20 if provider in {"auto", "deepseek"} else 40
    for idx in range(0, len(texts), chunk_size):
        chunk_segments = segments[idx : idx + chunk_size]
        timed_texts = [
            {
                "text": s.get("text", "").strip(),
                "duration": max(0.1, float(s["end"]) - float(s["start"])),
            }
            for s in chunk_segments
        ]
        translated.extend(translate_batch(timed_texts, provider))
    if len(translated) != len(texts):
        raise RuntimeError("Translator returned a different number of segments.")
    ru_segments = []
    for segment, ru in zip(segments, translated):
        item = {
            "id": segment.get("id"),
            "start": float(segment["start"]),
            "end": float(segment["end"]),
            "source": segment.get("text", "").strip(),
            "text": ru.strip(),
            "words": segment.get("words", []),
        }
        ru_segments.append(item)
    out_json.write_text(json.dumps(ru_segments, ensure_ascii=False, indent=2), encoding="utf-8")
    return ru_segments


def synth_yandex(text: str, raw_path: Path, voice: str, speed: float) -> None:
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "folderId": yandex_folder_id(),
        "format": "lpcm",
        "sampleRateHertz": "48000",
        "speed": f"{speed:.2f}",
    }
    resp = requests.post(url, headers=auth_headers(), data=data, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"Yandex SpeechKit failed: {resp.status_code} {resp.text[:500]}")
    raw_path.write_bytes(resp.content)
    if raw_path.stat().st_size < 200:
        raise RuntimeError(f"Yandex SpeechKit returned too little audio for: {text[:80]}")


def raw_lpcm_to_wav(raw_path: Path, wav_path: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-i",
            str(raw_path),
            "-ar",
            "48000",
            "-ac",
            "2",
            str(wav_path),
        ]
    )


def natural_timing_target(actual: float, target: float, *, max_speedup: float = 1.18, max_slowdown: float = 0.88) -> float:
    actual = max(actual, 0.01)
    target = max(target, 0.05)
    fastest_natural_target = actual / max_speedup
    slowest_natural_target = actual / max_slowdown
    return max(fastest_natural_target, min(target, slowest_natural_target))


def fit_segment_timing(src_wav: Path, dst_wav: Path, target: float) -> None:
    actual = max(duration(src_wav), 0.01)
    if target <= 0.05:
        target = actual
    target = natural_timing_target(actual, target)
    factor = actual / target
    if 0.95 <= factor <= 1.08:
        run(["ffmpeg", "-y", "-i", str(src_wav), "-ar", "48000", "-ac", "2", str(dst_wav)])
        return
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src_wav),
            "-filter:a",
            f"{atempo_filter(factor)},aresample=48000",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(dst_wav),
        ]
    )


def synth_say(text: str, wav_path: Path, voice: str, speed: float) -> None:
    aiff_path = wav_path.with_suffix(".aiff")
    rate = str(max(120, min(210, int(round(175 * speed)))))
    run(["say", "-v", voice, "-r", rate, "-o", str(aiff_path), text])
    run(["ffmpeg", "-y", "-i", str(aiff_path), "-ar", "48000", "-ac", "2", str(wav_path)])


def piper_model_paths(voice: str) -> tuple[Path, Path]:
    if os.environ.get("PIPER_MODEL"):
        model = Path(os.environ["PIPER_MODEL"])
    else:
        model = ROOT / "models" / "piper" / f"ru_RU-{voice}-medium.onnx"
    config = Path(os.environ.get("PIPER_CONFIG", str(model) + ".json"))
    if not model.exists():
        raise RuntimeError(
            f"Piper model not found: {model}. Download a Russian Piper voice model or set PIPER_MODEL."
        )
    if not config.exists():
        raise RuntimeError(f"Piper config not found: {config}. Set PIPER_CONFIG if it lives elsewhere.")
    return model, config


def synth_piper(text: str, wav_path: Path, voice: str, speed: float) -> None:
    model, config = piper_model_paths(voice)
    text_path = wav_path.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    length_scale = max(0.82, min(1.22, 1.0 / max(0.6, min(1.4, speed))))
    run(
        [
            sys.executable,
            "-m",
            "piper",
            "-m",
            str(model),
            "-c",
            str(config),
            "-i",
            str(text_path),
            "-f",
            str(wav_path),
            "--length-scale",
            f"{length_scale:.3f}",
            "--sentence-silence",
            "0.12",
        ]
    )
    if duration(wav_path) <= 0.05:
        raise RuntimeError(f"Piper returned empty audio for: {text[:80]}")


def synth_edge(text: str, wav_path: Path, voice: str, speed: float) -> None:
    import asyncio
    import edge_tts

    mp3_path = wav_path.with_suffix(".mp3")
    rate_pct = int(round((speed - 1.0) * 100))
    rate = f"{rate_pct:+d}%"

    async def _run() -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(str(mp3_path))

    asyncio.run(_run())
    run(["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "48000", "-ac", "2", str(wav_path)])
    if duration(wav_path) <= 0.05:
        raise RuntimeError(f"edge-tts returned empty audio for: {text[:80]}")


def schedule_segment_paths(items: list[tuple[Any, int, int]], *, min_gap_ms: int = 80) -> list[tuple[Any, int]]:
    scheduled: list[tuple[Any, int]] = []
    next_start = 0
    for path, requested_start, duration_ms in items:
        start = max(int(requested_start), next_start)
        scheduled.append((path, start))
        next_start = start + int(duration_ms) + min_gap_ms
    return scheduled


def synthesize_voice_track(
    segments: list[dict[str, Any]],
    total_duration: float,
    workdir: Path,
    voice: str,
    speed: float,
    tts_provider: str,
) -> Path:
    segment_paths: list[tuple[Path, int, int]] = []
    seg_dir = workdir / "tts_segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    for idx, segment in enumerate(segments):
        text = segment["text"].strip()
        if not text:
            continue
        raw = seg_dir / f"{idx:04d}.raw"
        wav = seg_dir / f"{idx:04d}.wav"
        fitted = seg_dir / f"{idx:04d}_fit.wav"
        print(f"TTS {idx + 1}/{len(segments)}: {text[:70]}")
        if tts_provider == "edge":
            synth_edge(text, wav, voice, speed)
        elif tts_provider == "piper":
            synth_piper(text, wav, voice, speed)
        elif tts_provider == "say":
            synth_say(text, wav, voice, speed)
        else:
            synth_yandex(text, raw, voice, speed)
            raw_lpcm_to_wav(raw, wav)
        target = max(0.2, float(segment["end"]) - float(segment["start"]))
        fit_segment_timing(wav, fitted, target)
        fitted_ms = int(round(duration(fitted) * 1000))
        segment_paths.append((fitted, int(round(float(segment["start"]) * 1000)), fitted_ms))
        time.sleep(0.15)

    if not segment_paths:
        raise RuntimeError("No translated segments to synthesize.")

    out_wav = workdir / "ru_voice_48k_stereo_lufs16.wav"
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-t", f"{total_duration:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    scheduled_paths = schedule_segment_paths(segment_paths)
    for path, _ in scheduled_paths:
        cmd.extend(["-i", str(path)])

    filters = ["[0:a]volume=0[base]"]
    mix_inputs = ["[base]"]
    for idx, (_, delay_ms) in enumerate(scheduled_paths, start=1):
        filters.append(f"[{idx}:a]adelay={delay_ms}:all=1[a{idx}]")
        mix_inputs.append(f"[a{idx}]")
    filters.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]"
    )
    cmd.extend(["-filter_complex", ";".join(filters), "-map", "[aout]", "-c:a", "pcm_s16le", str(out_wav)])
    run(cmd)
    return out_wav


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[dict[str, Any]], path: Path) -> None:
    blocks = []
    for idx, segment in enumerate(segments, start=1):
        blocks.append(
            f"{idx}\n{srt_time(segment['start'])} --> {srt_time(segment['end'])}\n{segment['text'].strip()}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")


def make_full_audio(main_voice: Path, outro: Path | None, fade: float, out_audio: Path) -> None:
    if not outro:
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(main_voice),
                "-ar",
                "48000",
                "-ac",
                "2",
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                str(out_audio),
            ]
        )
        return

    if has_audio(outro):
        outro_audio = str(outro)
    else:
        outro_audio = f"anullsrc=r=48000:cl=stereo:d={duration(outro):.3f}"

    cmd = ["ffmpeg", "-y", "-i", str(main_voice)]
    if has_audio(outro):
        cmd.extend(["-i", str(outro)])
    else:
        cmd.extend(["-f", "lavfi", "-i", outro_audio])
    cmd.extend(
        [
            "-filter_complex",
            f"[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];"
            f"[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
            f"[a0][a1]acrossfade=d={fade:.3f}:c1=tri:c2=tri,"
            "loudnorm=I=-16:TP=-1.5:LRA=11[aout]",
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(out_audio),
        ]
    )
    run(cmd)


def escape_subtitle_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_video(input_path: Path, audio_path: Path, outro: Path | None, srt: Path | None, output_path: Path, fade: float) -> None:
    main = video_stream(input_path)
    width = int(main["width"])
    height = int(main["height"])
    fps = fps_value(main.get("avg_frame_rate") or main.get("r_frame_rate") or "30/1")
    main_dur = duration(input_path)
    bitrate = "40M" if height >= 2160 or width >= 3840 else "10M"

    vf_main = f"setsar=1,fps={fps:.6f},format=yuv420p"
    if srt:
        vf_main += f",subtitles='{escape_subtitle_path(srt)}'"

    if outro:
        offset = max(0.0, main_dur - fade)
        filter_complex = (
            f"[0:v]{vf_main},setpts=PTS-STARTPTS[v0];"
            f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps={fps:.6f},format=yuv420p,setpts=PTS-STARTPTS[v1];"
            f"[v0][v1]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f},"
            "format=yuv420p[v]"
        )
        cmd = ["ffmpeg", "-y", "-i", str(input_path), "-i", str(outro), "-i", str(audio_path)]
    else:
        filter_complex = f"[0:v]{vf_main},format=yuv420p[v]"
        cmd = ["ffmpeg", "-y", "-i", str(input_path), "-i", str(audio_path)]

    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            f"{2 if outro else 1}:a",
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-level:v",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-b:v",
            bitrate,
            "-maxrate",
            bitrate,
            "-bufsize",
            str(int(bitrate[:-1]) * 2) + "M",
            "-r",
            f"{fps:.6f}",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]
    )
    run(cmd)


def qc_report(output_path: Path, audio_path: Path, path: Path) -> None:
    data = ffprobe_json(output_path)
    audio_dur = duration(audio_path)
    video_dur = float(data["format"]["duration"])
    vol = run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(audio_path), "-af", "volumedetect", "-f", "null", "-"],
        capture=True,
    ).stderr
    report = {
        "output": str(output_path),
        "duration_video": video_dur,
        "duration_audio": audio_dur,
        "duration_delta_sec": round(abs(video_dur - audio_dur), 3),
        "streams": data.get("streams", []),
        "volumedetect": "\n".join(line.strip() for line in vol.splitlines() if "mean_volume" in line or "max_volume" in line),
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Localize an English video into Russian with voice-over.")
    parser.add_argument("--input", required=True, type=Path, help="Source video path.")
    parser.add_argument("--outro", type=Path, default=DEFAULT_OUTRO if DEFAULT_OUTRO.exists() else None, help="Outro video path.")
    parser.add_argument("--output", type=Path, help="Final MP4 path.")
    parser.add_argument("--workdir", type=Path, help="Intermediate artifacts directory.")
    parser.add_argument("--whisper-model", default=os.environ.get("WHISPER_MODEL", "medium"), help="Whisper model name.")
    parser.add_argument("--voice", default=os.environ.get("YANDEX_TTS_VOICE", "ermil"), help="Yandex voice, e.g. ermil, zahar, oksana, jane.")
    parser.add_argument("--speed", type=float, default=float(os.environ.get("YANDEX_TTS_SPEED", "1.0")), help="SpeechKit speed.")
    parser.add_argument(
        "--tts-provider",
        choices=["yandex", "edge", "piper", "say"],
        default=os.environ.get("VIDEO_TTS_PROVIDER", "yandex"),
        help="TTS provider. Use 'say' for free local macOS Russian voice-over.",
    )
    parser.add_argument(
        "--translator",
        choices=["auto", "deepseek", "yandex"],
        default=os.environ.get("VIDEO_TRANSLATOR", "auto"),
        help="Translation provider. auto prefers DeepSeek when DEEPSEEK_API_KEY is set.",
    )
    parser.add_argument("--fade", type=float, default=0.75, help="Outro fade duration in seconds.")
    parser.add_argument("--no-outro", action="store_true", help="Do not append the outro video.")
    parser.add_argument("--burn-subs", action="store_true", help="Burn Russian subtitles into the video.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    stem = input_path.stem
    workdir = (args.workdir or (ROOT / "temp" / f"localize_{stem}")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    output_path = (args.output or (ROOT / "output" / f"{stem}_ru_localized.mp4")).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_wav = workdir / "source_48k_stereo.wav"
    transcript_json = workdir / "transcript_en_word_timestamps.json"
    translation_json = workdir / "translation_ru_segments.json"
    srt_path = output_path.with_suffix(".ru.srt")
    full_audio = workdir / "final_audio_48k_lufs16.wav"
    qc_path = output_path.with_suffix(".qc.json")

    extract_audio(input_path, source_wav)
    transcript = transcribe(source_wav, args.whisper_model, transcript_json)
    voiceover_segments = merge_transcript_segments_for_voiceover(transcript["segments"])
    ru_segments = translate_segments(voiceover_segments, translation_json, args.translator)
    write_srt(ru_segments, srt_path)
    voice_track = synthesize_voice_track(ru_segments, duration(input_path), workdir, args.voice, args.speed, args.tts_provider)

    outro = None if args.no_outro else (args.outro.resolve() if args.outro else None)
    if outro and not outro.exists():
        raise FileNotFoundError(outro)
    make_full_audio(voice_track, outro, args.fade, full_audio)
    render_video(input_path, full_audio, outro, srt_path if args.burn_subs else None, output_path, args.fade)
    qc_report(output_path, full_audio, qc_path)

    print("\nArtifacts:")
    print(f"  final:       {output_path}")
    print(f"  srt:         {srt_path}")
    print(f"  transcript:  {transcript_json}")
    print(f"  translation: {translation_json}")
    print(f"  qc:          {qc_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
