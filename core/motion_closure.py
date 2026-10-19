from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip

from core.motion_storyboard import closure_storyboard, storyboard_duration


W, H, FPS = 1080, 1920, 30
BG = (9, 12, 16)
GRID = (28, 34, 42)
TEXT = (245, 247, 250)
MUTED = (112, 121, 135)
CYAN = (20, 184, 190)
GREEN = (55, 190, 145)
CARD = (22, 27, 36)
ROBOTO = "assets/Roboto-Bold.ttf"
MONO = "assets/JetBrainsMono-Bold.ttf"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _draw_grid(draw: ImageDraw.ImageDraw) -> None:
    for x in range(0, W, 80):
        draw.line((x, 0, x, H), fill=GRID, width=1)
    for y in range(0, H, 80):
        draw.line((0, y, W, y), fill=GRID, width=1)


def _active_cue(t: float):
    cues = closure_storyboard()
    for cue in cues:
        if cue.start <= t < cue.end:
            return cue
    return cues[-1]


def _draw_centered_text(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, y), text, font=font, fill=fill)


def _fit_font_size(draw: ImageDraw.ImageDraw, path: str, text: str, max_size: int, max_width: int) -> int:
    for size in range(max_size, 23, -2):
        font = _font(path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return size
    return 24


def _draw_accent_headline(draw: ImageDraw.ImageDraw, y: int, text: str, accent: str) -> None:
    font = _font(ROBOTO, _fit_font_size(draw, ROBOTO, text, 58, W - 96))
    if accent not in text:
        _draw_centered_text(draw, y, text, font, TEXT)
        return
    before, after = text.split(accent, 1)
    parts = [(before, TEXT), (accent, CYAN), (after, TEXT)]
    widths = []
    for part, _ in parts:
        bbox = draw.textbbox((0, 0), part, font=font)
        widths.append(bbox[2] - bbox[0] if part else 0)
    x = (W - sum(widths)) // 2
    for (part, fill), width in zip(parts, widths):
        if part:
            draw.text((x, y), part, font=font, fill=fill)
        x += width


def _draw_card(draw: ImageDraw.ImageDraw, x: int, y: int, title: str, value: int, active: bool = False) -> None:
    outline = CYAN if active else (58, 66, 80)
    glow = CYAN if active else CARD
    draw.rounded_rectangle((x - 8, y - 8, x + 328, y + 428), radius=34, fill=tuple(max(0, c // 3) for c in glow))
    draw.rounded_rectangle((x, y, x + 320, y + 420), radius=30, fill=CARD, outline=outline, width=3)

    title_font = _font(MONO, 30)
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text((x + (320 - (title_bbox[2] - title_bbox[0])) // 2, y + 58), title, font=title_font, fill=MUTED)

    value_font = _font(ROBOTO, 132)
    value_text = str(value)
    value_bbox = draw.textbbox((0, 0), value_text, font=value_font)
    draw.text(
        (x + (320 - (value_bbox[2] - value_bbox[0])) // 2, y + 150),
        value_text,
        font=value_font,
        fill=CYAN if active else TEXT,
    )

    for i, sign in enumerate(["-", "+"]):
        bx = x + 70 + i * 100
        by = y + 310
        draw.rounded_rectangle((bx, by, bx + 74, by + 74), radius=18, fill=(31, 39, 54))
        sign_font = _font(ROBOTO, 48)
        sign_bbox = draw.textbbox((0, 0), sign, font=sign_font)
        draw.text(
            (bx + (74 - (sign_bbox[2] - sign_bbox[0])) // 2, by + 7),
            sign,
            font=sign_font,
            fill=TEXT,
        )


def _draw_bottom_note(draw: ImageDraw.ImageDraw, t: float) -> None:
    note = "let count stays inside" if t >= 22 else "two calls, two memories"
    font = _font(MONO, 34)
    bbox = draw.textbbox((0, 0), note, font=font)
    x0 = (W - (bbox[2] - bbox[0])) // 2 - 28
    y0 = 1450
    draw.rounded_rectangle((x0, y0 - 18, x0 + (bbox[2] - bbox[0]) + 56, y0 + 58), radius=16, fill=(16, 20, 28), outline=(38, 50, 62), width=1)
    draw.text((x0 + 28, y0), note, font=font, fill=CYAN)


def _draw_code_panel(draw: ImageDraw.ImageDraw, t: float) -> None:
    if not 24 <= t <= 43:
        return

    x0, y0, x1, y1 = 115, 900, 965, 1345
    draw.rounded_rectangle((x0 - 8, y0 - 8, x1 + 8, y1 + 8), radius=26, fill=(5, 25, 30))
    draw.rounded_rectangle((x0, y0, x1, y1), radius=24, fill=(13, 18, 27), outline=(43, 178, 185), width=2)

    lines = [
        "function makeCounter(start) {",
        "  let count = start;",
        "  return function step(delta) {",
        "    count += delta;",
        "    return count;",
        "  };",
        "}",
    ]
    highlights = [
        (24, 29, 1),
        (29, 35, 2),
        (35, 40, 3),
        (40, 43, 4),
    ]
    active_line = 1
    for start, end, index in highlights:
        if start <= t < end:
            active_line = index
            break

    font = _font(MONO, 34)
    small_font = _font(MONO, 24)
    draw.text((x0 + 34, y0 + 28), "closure.js", font=small_font, fill=MUTED)
    for index, line in enumerate(lines):
        y = y0 + 78 + index * 48
        if index == active_line:
            draw.rounded_rectangle((x0 + 22, y - 8, x1 - 22, y + 42), radius=12, fill=(18, 49, 57))
        color = GREEN if index in {1, 3, 4} else (220, 226, 235)
        if "return" in line:
            color = CYAN
        draw.text((x0 + 42, y), line, font=font, fill=color)

    draw.text((x0 + 34, y1 - 58), "count is remembered between calls", font=small_font, fill=CYAN)


def render_closure_frame(t: float) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _draw_grid(draw)

    cue = _active_cue(t)
    _draw_centered_text(draw, 250, cue.label, _font(ROBOTO, 30), MUTED)
    _draw_accent_headline(draw, 320, cue.headline, cue.accent)

    phase = 0.5 + 0.5 * math.sin(t * 2.0)
    first_value = 0 if t < 34 else min(3, int((t - 34) // 3) + 1)
    second_value = 100 if t < 38 else 100 - min(2, int((t - 38) // 4) + 1)
    _draw_card(draw, 170, 660, "makeCounter(0)", first_value, active=t < 22 or phase > 0.55)
    _draw_card(draw, 590, 660, "makeCounter(100)", second_value, active=t >= 12 and phase > 0.35)
    _draw_code_panel(draw, t)
    _draw_bottom_note(draw, t)

    if t >= 46:
        _draw_centered_text(draw, 1260, "✓ independent values", _font(MONO, 36), GREEN)

    return np.array(img, dtype=np.uint8)


def build_closure_clip(duration: float | None = None) -> VideoClip:
    natural_duration = storyboard_duration(closure_storyboard())
    output_duration = duration or natural_duration
    speed = natural_duration / output_duration
    return VideoClip(lambda t: render_closure_frame(t * speed), duration=output_duration)
