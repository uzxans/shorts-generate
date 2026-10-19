import math
import numpy as np
from PIL import Image, ImageDraw
from moviepy import (
    TextClip,
    ColorClip,
    ImageClip,
    ImageSequenceClip,
    VideoClip,
    VideoFileClip,
    CompositeVideoClip,
)

from core.code_render import render_progressive_frames

FONT = "assets/Montserrat-Medium.ttf"
W, H = 1080, 1920
BG_COLOR = (15, 16, 14)
SUB_BG = (220, 30, 30)


def _to_rgb_array(img):
    return np.array(img.convert("RGB"))


# Frame 1: title on top + small demo preview at bottom
def hook_scene(hook_text, demo_path, duration):
    bg = ColorClip(size=(W, H), color=BG_COLOR, duration=duration)

    title = TextClip(
        font=FONT,
        text=hook_text,
        font_size=78,
        color="cyan",
        method="caption",
        size=(960, None),
        text_align="center",
        stroke_color="black",
        stroke_width=4,
        interline=12,
    ).with_duration(duration)

    title_top = 120
    title_bottom = title_top + title.h

    preview_w = 620
    preview = (
        VideoFileClip(demo_path)
        .with_duration(duration)
        .resized(width=preview_w)
    )
    pw, ph = preview.size

    gap = 60
    preview_top = max(title_bottom + gap, H - ph - 120)
    if preview_top + ph > H - 80:
        preview_top = H - ph - 80

    title = title.with_position(("center", title_top))
    preview = preview.with_position(((W - pw) // 2, preview_top))

    return CompositeVideoClip([bg, title, preview], size=(W, H)).with_duration(duration)


# Frame 2: line-by-line code typing
def code_typing_scene(code, language, duration):
    bg = ColorClip(size=(W, H), color=BG_COLOR, duration=duration)

    pil_frames = render_progressive_frames(code, language, max_width=1000)
    frames = [_to_rgb_array(f) for f in pil_frames]
    fps = max(len(frames) / duration, 1.0)

    code_clip = ImageSequenceClip(frames, fps=fps).with_duration(duration)
    cw, ch = code_clip.size
    code_clip = code_clip.with_position(((W - cw) // 2, (H - ch) // 2))

    return CompositeVideoClip([bg, code_clip], size=(W, H)).with_duration(duration)


# Frame 3: full-screen rendered demo
def demo_scene(demo_path, duration):
    demo = VideoFileClip(demo_path).with_duration(duration)
    return CompositeVideoClip([demo], size=(W, H)).with_duration(duration)


# Frame 4: animated subscribe + bell
def subscribe_scene(duration):
    bg = ColorClip(size=(W, H), color=SUB_BG, duration=duration)

    subscribe_text = (
        TextClip(
            font=FONT,
            text="ПОДПИШИСЬ",
            font_size=104,
            color="white",
            method="caption",
            size=(960, None),
            text_align="center",
            stroke_color="black",
            stroke_width=5,
        )
        .with_duration(duration)
        .with_position(("center", 360))
    )

    tomorrow_text = (
        TextClip(
            font=FONT,
            text="Новый ролик\nзавтра!",
            font_size=58,
            color="white",
            method="caption",
            size=(960, None),
            text_align="center",
            stroke_color="black",
            stroke_width=3,
            interline=10,
        )
        .with_duration(duration)
        .with_position(("center", 1530))
    )

    bell_clip = _bell_clip(duration)
    bw, bh = bell_clip.size
    bell_clip = bell_clip.with_position(((W - bw) // 2, 800))

    return CompositeVideoClip(
        [bg, subscribe_text, bell_clip, tomorrow_text],
        size=(W, H),
    ).with_duration(duration)


def _draw_bell(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size
    # body
    draw.ellipse([s * 0.18, s * 0.22, s * 0.82, s * 0.82], fill="#facc15", outline="#0b0b0b", width=10)
    # top mount
    draw.rectangle([s * 0.45, s * 0.08, s * 0.55, s * 0.22], fill="#0b0b0b")
    draw.ellipse([s * 0.4, s * 0.04, s * 0.6, s * 0.16], fill="#0b0b0b")
    # clapper
    draw.ellipse([s * 0.43, s * 0.84, s * 0.57, s * 0.96], fill="#0b0b0b")
    # highlight
    draw.ellipse([s * 0.28, s * 0.3, s * 0.4, s * 0.42], fill="#fff8c2")
    return img


def _bell_clip(duration, size=420):
    bell = _draw_bell(size)
    canvas_size = int(size * 1.4)
    fps = 30
    n_frames = int(fps * duration)
    bg_color = SUB_BG

    frames = []
    for i in range(n_frames):
        t = i / fps
        # quick triple-shake at start, then settle
        angle = 25 * math.sin(t * 8) * math.exp(-0.5 * t)
        rotated = bell.rotate(angle, resample=Image.BICUBIC)
        rw, rh = rotated.size
        canvas = Image.new("RGB", (canvas_size, canvas_size), bg_color)
        offset = ((canvas_size - rw) // 2, (canvas_size - rh) // 2)
        canvas.paste(rotated, offset, rotated.split()[3])
        frames.append(np.array(canvas))

    return ImageSequenceClip(frames, fps=fps).with_duration(duration)
