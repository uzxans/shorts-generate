#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from localize_video import extract_audio, transcribe


ROOT = Path(__file__).resolve().parent


def transcript_text(result: dict) -> str:
    segments = result.get("segments") or []
    lines: list[str] = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment.get("start", 0) or 0)
        end = float(segment.get("end", 0) or 0)
        lines.append(f"[{start:06.1f}-{end:06.1f}] {text}")
    return "\n".join(lines).strip() or str(result.get("text", "")).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe a video into a text file.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--whisper-model", default=os.environ.get("WHISPER_MODEL", "tiny"))
    parser.add_argument(
        "--language",
        default=os.environ.get("TRANSCRIPT_LANGUAGE", "auto"),
        help="Spoken language code, for example ru or en. Use auto to let Whisper detect it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    workdir = (args.workdir or (ROOT / "temp" / f"transcribe_{input_path.stem}")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    source_wav = workdir / "source_48k_stereo.wav"
    transcript_json = workdir / "transcript.json"
    extract_audio(input_path, source_wav)
    language = None if str(args.language).lower() == "auto" else str(args.language)
    result = transcribe(source_wav, args.whisper_model, transcript_json, language=language)
    args.output.write_text(transcript_text(result), encoding="utf-8")

    print(json.dumps({"output": str(args.output), "json": str(transcript_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
