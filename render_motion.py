#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip, concatenate_audioclips, concatenate_videoclips

from core.motion_closure import FPS, build_closure_clip
from core.yandex_tts import synthesize_yandex_tts
from render import FINAL_AUDIO_BITRATE, FINAL_FFMPEG_PARAMS, FINAL_VIDEO_BITRATE


OUTPUT = Path("output")
TEMP = Path("temp")
MUSIC_PATH = Path("assets/music.mp3")
OUTRO_PATH = Path("assets/frog.mp4")
VOICE_VOLUME = 1.8

VOICE_TEXT = (
    "Замыкание — это память функции. "
    "Представь, что makeCounter создаёт маленькую коробку. "
    "Внутри лежит переменная count, и она не исчезает после первого вызова. "
    "Слева мы создали счётчик от нуля. "
    "Справа — второй счётчик от ста. "
    "Когда мы нажимаем плюс или минус, каждый меняет только своё число. "
    "Первый не знает про второй. "
    "Второй не трогает первый. "
    "Вот почему замыкания удобны: функция помнит своё окружение и работает с ним спокойно. "
    "Главное правило простое: каждый вызов создаёт свою память."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render calm motion explainer video")
    parser.add_argument("--topic", type=int, default=36)
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--voice")
    parser.add_argument("--speed", default="1.08")
    parser.add_argument("--music-volume", type=float, default=0.035)
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--no-outro", action="store_true")
    return parser.parse_args(argv)


def load_env_file(path: Path = Path(".env.local")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _loop_audio_to_duration(path: Path, duration: float, volume: float) -> AudioFileClip:
    source = AudioFileClip(str(path))
    if source.duration >= duration:
        return source.subclipped(0, duration).with_volume_scaled(volume)
    clips = []
    remaining = duration
    while remaining > 0:
        part = source.subclipped(0, min(source.duration, remaining))
        clips.append(part)
        remaining -= part.duration
    return concatenate_audioclips(clips).with_volume_scaled(volume)


def build_motion_audio(
    voice_path: Path,
    duration: float,
    *,
    music_volume: float,
    include_music: bool,
):
    voice = AudioFileClip(str(voice_path))
    audio_tracks = [voice.with_volume_scaled(VOICE_VOLUME)]
    if include_music and MUSIC_PATH.exists():
        audio_tracks.insert(0, _loop_audio_to_duration(MUSIC_PATH, duration, music_volume))
    if len(audio_tracks) == 1:
        return audio_tracks[0]
    return CompositeAudioClip(audio_tracks).with_duration(duration)


def build_motion_video(*, include_outro: bool = True, main_duration: float | None = None):
    clip = build_closure_clip(duration=main_duration)
    if not include_outro or not OUTRO_PATH.exists():
        return clip
    outro = VideoFileClip(str(OUTRO_PATH)).resized(height=clip.h)
    return concatenate_videoclips([clip, outro], method="compose")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.topic != 36:
        raise SystemExit("motion v2 currently supports only topic 36")

    load_env_file()
    OUTPUT.mkdir(exist_ok=True)
    TEMP.mkdir(exist_ok=True)

    if not args.skip_voice:
        voice = args.voice or os.environ.get("YANDEX_TTS_VOICE", "ermil")
        audio_path = synthesize_yandex_tts(
            VOICE_TEXT,
            TEMP / "motion_36_voice.mp3",
            voice=voice,
            speed=args.speed,
        )
        voice_audio = AudioFileClip(str(audio_path))
        clip = build_motion_video(include_outro=not args.no_outro, main_duration=voice_audio.duration)
        audio = build_motion_audio(
            audio_path,
            clip.duration,
            music_volume=args.music_volume,
            include_music=not args.no_music,
        )
        clip = clip.with_audio(audio)
    else:
        clip = build_motion_video(include_outro=not args.no_outro)

    out_path = OUTPUT / "motion_36_closure.mp4"
    clip.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate=FINAL_VIDEO_BITRATE,
        audio_bitrate=FINAL_AUDIO_BITRATE,
        preset="medium",
        ffmpeg_params=FINAL_FFMPEG_PARAMS,
        threads=4,
        logger="bar",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
