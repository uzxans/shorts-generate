from __future__ import annotations

from dataclasses import dataclass
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = ROOT / "assets" / "Roboto-Bold.ttf"
SAFE_X0, SAFE_X1 = 64, 920
SAFE_Y0, SAFE_Y1 = 1450, 1660
ACTIVE = "#D8B45B"
WHITE = "#F7F2E8"


@dataclass(frozen=True)
class CaptionWord:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    words: tuple[CaptionWord, ...]

    def active_word_at(self, t: float) -> CaptionWord | None:
        return next((word for word in self.words if word.start <= t < word.end), None)


def build_caption_cues(display_text: str, tts_meta: dict, video_duration: float) -> tuple[CaptionCue, ...]:
    display_tokens = _display_tokens(display_text)
    timed_words = _metadata_words(display_tokens, tts_meta, video_duration)
    cues: list[CaptionCue] = []
    bucket: list[CaptionWord] = []

    for word in timed_words:
        bucket.append(word)
        source = word.text
        should_break = len(bucket) >= 5 or (len(bucket) >= 2 and source[-1:] in ".?!:;—-")
        if should_break:
            cues.append(_cue_from_words(bucket))
            bucket = []

    if bucket:
        if cues and len(bucket) == 1 and len(cues[-1].words) < 5:
            merged = tuple(cues[-1].words + tuple(bucket))
            cues[-1] = CaptionCue(merged[0].start, merged[-1].end, merged)
        else:
            cues.append(_cue_from_words(bucket))

    return tuple(cues)


def active_caption(cues: tuple[CaptionCue, ...], t: float) -> CaptionCue | None:
    return next((cue for cue in cues if cue.start <= t < cue.end), None)


def render_caption(cue: CaptionCue, t: float, frame_size: tuple[int, int]) -> tuple[np.ndarray, tuple[int, int]]:
    max_w = SAFE_X1 - SAFE_X0
    pad_x, pad_y = 30, 20
    font_size = 54
    while font_size >= 20:
        font = _font(font_size)
        active_font = _font(round(font_size * _pulse_scale(cue, t)))
        w, h, parts = _measure_parts(cue, t, font, active_font)
        if w + pad_x * 2 <= max_w:
            break
        font_size -= 2

    image = Image.new("RGBA", (w + pad_x * 2, h + pad_y * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=28, fill=(5, 5, 4, 196))
    cursor_x = pad_x
    baseline_y = pad_y
    for text, part_font, fill, part_w in parts:
        draw.text((cursor_x, baseline_y), text, font=part_font, fill=fill)
        cursor_x += part_w

    x = SAFE_X0 + max(0, (max_w - image.width) // 2)
    y = SAFE_Y0 + max(0, (SAFE_Y1 - SAFE_Y0 - image.height) // 2)
    x = min(x, SAFE_X1 - image.width)
    y = min(y, SAFE_Y1 - image.height)
    return np.array(image, dtype=np.uint8), (x, y)


def _display_tokens(text: str) -> list[str]:
    return [match.group(0).strip(".,!?;:") for match in re.finditer(r"[^\s]+", text) if match.group(0).strip(".,!?;:")]


def _metadata_words(display_tokens: list[str], tts_meta: dict, video_duration: float) -> tuple[CaptionWord, ...]:
    raw_words = tts_meta.get("words") or []
    if raw_words:
        result = []
        for display, raw in zip(display_tokens, raw_words):
            start = float(raw["offset"])
            result.append(CaptionWord(display, start, start + float(raw["duration"])))
        return tuple(result)

    weights = [max(1, len(word.strip(".,!?—:;"))) for word in display_tokens]
    total_weight = sum(weights) or 1
    cursor = 0.0
    words = []
    for word, weight in zip(display_tokens, weights):
        duration = float(video_duration) * weight / total_weight
        words.append(CaptionWord(word, cursor, cursor + duration))
        cursor += duration
    return tuple(words)


def _cue_from_words(words: list[CaptionWord]) -> CaptionCue:
    packed = tuple(words)
    return CaptionCue(packed[0].start, packed[-1].end, packed)


def _pulse_scale(cue: CaptionCue, t: float) -> float:
    active = cue.active_word_at(t)
    if not active:
        return 1.0
    span = max(0.001, active.end - active.start)
    phase = min(1.0, max(0.0, (t - active.start) / span))
    return 1.0 + 0.08 * math.sin(math.pi * phase)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), size=size)
    except OSError:
        return ImageFont.load_default()


def _measure_parts(cue: CaptionCue, t: float, font, active_font):
    active = cue.active_word_at(t)
    parts = []
    width = 0
    height = 0
    for index, word in enumerate(cue.words):
        text = word.text + (" " if index < len(cue.words) - 1 else "")
        is_active = active == word
        part_font = active_font if is_active else font
        bbox = part_font.getbbox(text)
        part_w = bbox[2] - bbox[0]
        part_h = bbox[3] - bbox[1]
        width += part_w
        height = max(height, part_h)
        parts.append((text, part_font, ACTIVE if is_active else WHITE, part_w))
    return width, max(1, height), parts
