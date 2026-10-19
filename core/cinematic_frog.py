from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont


W, H = 1080, 1920
ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = ROOT / "assets" / "Roboto-Bold.ttf"


@dataclass(frozen=True)
class FrogAssets:
    video_frames: tuple[np.ndarray, ...]
    avatar: np.ndarray | None
    fps: float = 24.0
    duration: float = 0.0


def load_frog_assets(video_path: Path = ROOT / "assets" / "frog.mp4", avatar_path: Path = ROOT / "assets" / "fotoavatar.png") -> FrogAssets:
    frames: list[np.ndarray] = []
    fps = 24.0
    duration = 0.0
    if video_path.exists():
        try:
            from moviepy import VideoFileClip

            clip = VideoFileClip(str(video_path))
            fps = float(clip.fps or 24.0)
            duration = float(clip.duration or 0.0)
            sample_count = max(1, int(duration * fps))
            for index in range(sample_count):
                t = min(duration - 0.001, index / fps)
                frames.append(clip.get_frame(t).astype(np.uint8))
            clip.close()
        except Exception:
            frames = []
            duration = 0.0

    avatar = None
    if avatar_path.exists():
        avatar = np.array(Image.open(avatar_path).convert("RGBA"), dtype=np.uint8)
    return FrogAssets(tuple(frames), avatar, fps, duration)


def render_frog_reaction(assets: FrogAssets, reaction: str, progress: float) -> np.ndarray | None:
    if progress < 0.0 or progress > 1.0:
        raise ValueError("reaction progress must be between 0 and 1")
    source = _source_rgba(assets, progress)
    if source is None:
        return None

    crop = _center_crop_subject(source)
    scale = 1.0 + (0.08 if reaction == "panic" else 0.05) * math.sin(math.pi * progress)
    angle = math.sin(progress * math.pi * 6.0) * 4.0 if reaction == "panic" else 0.0
    image = Image.fromarray(crop)
    size = (int(image.width * scale), int(image.height * scale))
    image = image.resize(size, Image.Resampling.LANCZOS).rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    layer = Image.new("RGBA", (360, 420), (0, 0, 0, 0))
    if reaction == "relief":
        glow = Image.new("RGBA", layer.size, (216, 180, 91, int(70 * math.sin(math.pi * progress))))
        layer.alpha_composite(glow)
    layer.alpha_composite(image, ((layer.width - image.width) // 2, (layer.height - image.height) // 2))
    return np.array(layer, dtype=np.uint8)


def render_frog_cta(assets: FrogAssets, local_t: float) -> np.ndarray:
    frame = _source_rgb(assets, local_t)
    if frame is not None:
        return _fit_on_red(frame)

    canvas = Image.new("RGB", (W, H), "#C51620")
    draw = ImageDraw.Draw(canvas)
    if assets.avatar is not None:
        avatar = Image.fromarray(assets.avatar).convert("RGBA")
        avatar.thumbnail((620, 620), Image.Resampling.LANCZOS)
        canvas.paste(avatar, ((W - avatar.width) // 2, 520), avatar)
    font = _font(94)
    label = "ПОДПИШИТЕСЬ"
    bbox = draw.textbbox((0, 0), label, font=font)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 1260), label, font=font, fill="#FFFFFF")
    return np.array(canvas, dtype=np.uint8)


def _source_rgba(assets: FrogAssets, progress: float) -> np.ndarray | None:
    if assets.video_frames:
        index = min(len(assets.video_frames) - 1, int(progress * len(assets.video_frames)))
        return np.array(Image.fromarray(assets.video_frames[index]).convert("RGBA"), dtype=np.uint8)
    return assets.avatar


def _source_rgb(assets: FrogAssets, local_t: float) -> np.ndarray | None:
    if not assets.video_frames:
        return None
    index = min(len(assets.video_frames) - 1, max(0, int(local_t * assets.fps)))
    return assets.video_frames[index]


def _fit_on_red(frame: np.ndarray) -> np.ndarray:
    canvas = Image.new("RGB", (W, H), "#C51620")
    image = Image.fromarray(frame).convert("RGB")
    image.thumbnail((W, H), Image.Resampling.LANCZOS)
    canvas.paste(image, ((W - image.width) // 2, (H - image.height) // 2))
    return np.array(canvas, dtype=np.uint8)


def _center_crop_subject(frame: np.ndarray) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGBA")
    image.thumbnail((330, 390), Image.Resampling.LANCZOS)
    return np.array(image, dtype=np.uint8)


def _font(size: int):
    try:
        return ImageFont.truetype(str(FONT_PATH), size=size)
    except OSError:
        return ImageFont.load_default()
