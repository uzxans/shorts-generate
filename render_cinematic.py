#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, replace
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, CompositeAudioClip, VideoClip

import render
from core.cinematic_camera import composite_rgba
from core.cinematic_frog import load_frog_assets, render_frog_cta
from core.cinematic_scenes import CinematicSceneRenderer
from core.cinematic_storyboard import APPROVED_TOPIC_60_VOICEOVER, retime_storyboard, topic_60_storyboard
from core.cinematic_storyboard import CinematicStoryboard
from core.cinematic_topics import get_storyboard, supported_topic_ids
from core.cinematic_subtitles import active_caption, build_caption_cues, render_caption
from render import FINAL_AUDIO_BITRATE, FINAL_FFMPEG_PARAMS, FINAL_VIDEO_BITRATE


ROOT = Path(__file__).resolve().parent
TEMP = ROOT / "temp"
OUTPUT = ROOT / "output"
VOICE_PATH = TEMP / "60_cinematic_voice.mp3"
META_PATH = TEMP / "60_cinematic_voice.json"
OUT_PATH = OUTPUT / "60_git-worktree-cinematic.mp4"
PREVIEW_PATH = OUTPUT / "60_git-worktree-cinematic-preview.mp4"
CONTACT_SHEET_PATH = OUTPUT / "60_git-worktree-cinematic-contact-sheet.jpg"

TOPIC_SLUGS = {
    60: "git-worktree",
    61: "react-use-suspense",
    62: "uuidv7-nodejs",
    63: "navigation-api",
    64: "typescript-6-migration",
    65: "starting-style",
}


@dataclass(frozen=True)
class ArtifactPaths:
    voice: Path
    metadata: Path
    video: Path
    preview: Path
    contact_sheet: Path


def artifact_paths(topic_id: int, slug: str | None = None) -> ArtifactPaths:
    if topic_id == 60:
        base = "60_git-worktree-cinematic"
    else:
        base = f"{topic_id}_{slug or TOPIC_SLUGS[topic_id]}-cinematic"
    return ArtifactPaths(
        voice=TEMP / f"{topic_id}_cinematic_voice.mp3",
        metadata=TEMP / f"{topic_id}_cinematic_voice.json",
        video=OUTPUT / f"{base}.mp4",
        preview=OUTPUT / f"{base}-preview.mp4",
        contact_sheet=OUTPUT / f"{base}-contact-sheet.jpg",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render cinematic programming Shorts.")
    parser.add_argument("--topic", type=int, required=True, choices=supported_topic_ids())
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--no-sfx", action="store_true")
    parser.add_argument("--contact-sheet", action="store_true")
    parser.add_argument("--preview-duration", type=float, default=None)
    return parser.parse_args(argv)


def load_topic(topic_id: int = 60) -> dict:
    data = json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))
    return next(item for item in data["topics"] if item["id"] == topic_id)


def build_cinematic_clip(
    topic_id: int = 60,
    skip_voice: bool = False,
    duration: float | None = None,
    size: tuple[int, int] = (1080, 1920),
    fps: int = 30,
    tts_meta: dict | None = None,
) -> VideoClip:
    frog_assets = load_frog_assets(ROOT / "assets" / "frog.mp4", ROOT / "assets" / "fotoavatar.png")
    board = _timed_board(topic_id, skip_voice, duration, tts_meta, cta_duration=frog_assets.duration or 4.0)
    cues = build_caption_cues(board.voiceover, tts_meta or _synthetic_meta(board.voiceover, board.duration), board.duration)
    renderer = CinematicSceneRenderer(seed=topic_id)

    def make_frame(t: float) -> np.ndarray:
        shot = _shot_at(board.shots, t)
        cta_start = board.duration - (frog_assets.duration or 4.0)
        if t >= cta_start:
            frame = render_frog_cta(frog_assets, t - cta_start)
        else:
            frame = renderer.render(shot, t)
            cue = active_caption(cues, t)
            if cue is not None:
                caption, (x, y) = render_caption(cue, t, (1080, 1920))
                frame = composite_rgba(frame, caption, x, y)

        if size != (1080, 1920):
            frame = np.array(Image.fromarray(frame).resize(size, Image.Resampling.LANCZOS), dtype=np.uint8)
        return frame

    return VideoClip(make_frame, duration=board.duration).with_fps(fps)


def mix_cinematic_audio(
    voice: AudioFileClip | None,
    duration: float,
    no_music: bool = False,
    no_sfx: bool = False,
) -> CompositeAudioClip | AudioFileClip | None:
    clips = []
    if voice is not None:
        clips.append(voice.with_volume_scaled(1.0))
    if not no_music and render.MUSIC_PATH.exists():
        music = AudioFileClip(str(render.MUSIC_PATH))
        loops = []
        cursor = 0.0
        while cursor < duration:
            take = min(music.duration, duration - cursor)
            loops.append(music.subclipped(0, take).with_start(cursor))
            cursor += take
        clips.extend(item.with_volume_scaled(0.12) for item in loops)
    sfx_path = render.ASSETS / "click.mp3"
    if not no_sfx and sfx_path.exists():
        if sfx_path.stat().st_size == 0:
            print(f"warning: optional SFX skipped: {sfx_path} is empty")
            sfx_path = None
    if not no_sfx and sfx_path is not None and sfx_path.exists():
        try:
            click = AudioFileClip(str(sfx_path)).subclipped(0, 0.16).with_volume_scaled(0.13)
        except OSError as exc:
            print(f"warning: optional SFX skipped: {exc}")
        else:
            for start in (3.0, 7.0, 10.0, 14.0, 24.0, 32.0, 38.0):
                clips.append(click.with_start(start))
    if not clips:
        return None
    if len(clips) == 1:
        return clips[0]
    return CompositeAudioClip(clips).with_duration(duration)


def render_contact_sheet(topic_id: int = 60, path: Path | None = None, tts_meta: dict | None = None) -> Path:
    paths = artifact_paths(topic_id)
    path = path or paths.contact_sheet
    frog_assets = load_frog_assets(ROOT / "assets" / "frog.mp4", ROOT / "assets" / "fotoavatar.png")
    board = _timed_board(topic_id, skip_voice=True, tts_meta=tts_meta, cta_duration=frog_assets.duration or 4.0)
    clip = build_cinematic_clip(topic_id=topic_id, skip_voice=True, tts_meta=tts_meta)
    thumbs = []
    font = _font(22)
    for shot in board.shots:
        t = (shot.start + shot.end) / 2
        thumb = Image.fromarray(clip.get_frame(t)).resize((216, 384), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(thumb)
        draw.rectangle((0, 0, 216, 34), fill=(0, 0, 0))
        draw.text((8, 7), f"{shot.id} {t:.1f}s", font=font, fill=(255, 242, 185))
        thumbs.append(thumb)
    rows = (len(thumbs) + 1) // 2
    sheet = Image.new("RGB", (216 * 2, 384 * rows), "#10100E")
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % 2) * 216, (index // 2) * 384))
    path.parent.mkdir(exist_ok=True)
    sheet.save(path, quality=92)
    clip.close()
    return path


def render_topic_60(args: argparse.Namespace) -> Path:
    return render_topic(args)


def render_topic(args: argparse.Namespace) -> Path:
    TEMP.mkdir(exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    board = get_storyboard(args.topic)
    paths = artifact_paths(args.topic)
    voice = None
    meta = None
    if not args.skip_voice:
        meta = _load_or_generate_voice(board, paths)
        voice = AudioFileClip(str(paths.voice))
    duration = args.preview_duration
    clip = build_cinematic_clip(topic_id=args.topic, skip_voice=args.skip_voice, duration=duration, tts_meta=meta)
    if duration is not None:
        clip = clip.subclipped(0, min(duration, clip.duration))
    audio = mix_cinematic_audio(voice, clip.duration, args.no_music, args.no_sfx)
    if audio is not None:
        clip = clip.with_audio(audio)
    out_path = paths.preview if args.preview_duration else paths.video
    clip.write_videofile(
        str(out_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        bitrate=FINAL_VIDEO_BITRATE,
        audio_bitrate=FINAL_AUDIO_BITRATE,
        preset="medium",
        ffmpeg_params=FINAL_FFMPEG_PARAMS,
        threads=4,
        logger="bar",
    )
    if args.contact_sheet:
        render_contact_sheet(topic_id=args.topic, tts_meta=meta)
    clip.close()
    return out_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    render_topic(args)
    return 0


def _timed_board(topic_id: int, skip_voice: bool, duration: float | None = None, tts_meta: dict | None = None, cta_duration: float = 4.0):
    board = get_storyboard(topic_id)
    if skip_voice:
        total = duration or 40.0
        scale = total / board.duration
        shots = tuple(replace(shot, start=shot.start * scale, end=shot.end * scale) for shot in board.shots)
        return replace(board, shots=shots)
    return retime_storyboard(board, tts_meta or _synthetic_meta(40.0), cta_duration=cta_duration)


def _synthetic_meta(text_or_duration, duration: float | None = None) -> dict:
    if duration is None:
        text = APPROVED_TOPIC_60_VOICEOVER
        duration = float(text_or_duration)
    else:
        text = str(text_or_duration)
    words = text.split()
    per = duration / max(1, len(words))
    return {"words": [{"offset": i * per, "duration": per * 0.9, "text": word} for i, word in enumerate(words)]}


def voice_cache_matches(meta: dict, board: CinematicStoryboard) -> bool:
    return meta.get("topic_id", 60 if board.topic_id == 60 else None) == board.topic_id and meta.get("voiceover") == board.voiceover


def _load_or_generate_voice(board: CinematicStoryboard | None = None, paths: ArtifactPaths | None = None) -> dict:
    board = board or topic_60_storyboard()
    paths = paths or artifact_paths(board.topic_id)
    if paths.voice.exists() and paths.metadata.exists():
        cached = json.loads(paths.metadata.read_text(encoding="utf-8"))
        if voice_cache_matches(cached, board) and voice_fits_pilot_range(cached, cta_duration=4.0):
            return cached
        print("warning: cached cinematic voice is stale or too long; regenerating at +25% rate")
    meta = asyncio.run(_tts_async(board.voiceover, paths.voice, rate="+25%"))
    retry_rate = retry_rate_for_voice(meta, cta_duration=4.0)
    if retry_rate is not None:
        print(f"warning: generated voice is too long; regenerating once at {retry_rate} rate")
        meta = asyncio.run(_tts_async(board.voiceover, paths.voice, rate=retry_rate))
    if not voice_fits_pilot_range(meta, cta_duration=4.0):
        raise ValueError("generated cinematic voice does not fit the 35-45 second range")
    meta["topic_id"] = board.topic_id
    meta["voiceover"] = board.voiceover
    paths.metadata.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def voice_fits_pilot_range(meta: dict, cta_duration: float) -> bool:
    sentences = meta.get("sentences") or []
    if not sentences:
        return False
    audio_end = max(float(item["offset"]) + float(item["duration"]) for item in sentences)
    total = audio_end + cta_duration
    return 35.0 <= total <= 45.0


def retry_rate_for_voice(meta: dict, cta_duration: float) -> str | None:
    sentences = meta.get("sentences") or []
    if not sentences:
        return None
    audio_end = max(float(item["offset"]) + float(item["duration"]) for item in sentences)
    return "+32%" if audio_end + float(cta_duration) > 45.0 else None


async def _tts_async(text: str, out_path: Path, rate: str) -> dict:
    communicate = edge_tts.Communicate(text, render.VOICE, rate=rate)
    chunks: list[bytes] = []
    sentences: list[dict] = []
    words: list[dict] = []
    async for event in communicate.stream():
        if event["type"] == "audio":
            chunks.append(event["data"])
        elif event["type"] == "SentenceBoundary":
            sentences.append({"offset": event["offset"] / 1e7, "duration": event["duration"] / 1e7, "text": event["text"]})
        elif event["type"] == "WordBoundary":
            words.append({"offset": event["offset"] / 1e7, "duration": event["duration"] / 1e7, "text": event["text"]})
    out_path.write_bytes(b"".join(chunks))
    return {"sentences": sentences, "words": words}


def _shot_at(shots, t: float):
    return next((shot for shot in shots if shot.start <= t < shot.end), shots[-1])


def _font(size: int):
    try:
        return ImageFont.truetype(str(ROOT / "assets" / "Roboto-Bold.ttf"), size=size)
    except OSError:
        return ImageFont.load_default()


if __name__ == "__main__":
    raise SystemExit(main())
