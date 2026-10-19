# Motion Explainer V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate `topic 36` motion-explainer renderer with male Yandex SpeechKit voice and calm reference-style pacing.

**Architecture:** Keep the existing `render.py` flow intact. Add a separate `render_motion.py` CLI plus focused modules for Yandex TTS, storyboard timings, and the closure-counter visual scene. The first version targets one topic only so quality can be judged before generalizing.

**Tech Stack:** Python, MoviePy, PIL, NumPy, Yandex SpeechKit HTTP API v1, FFmpeg via MoviePy.

## Global Constraints

- Do not replace or break the existing `render.py` Shorts renderer.
- First target is topic `36` from `topics.json`.
- Render target is `1080x1920`, `30fps`, `50-60s`.
- Use Yandex SpeechKit male voice, default `ermil`, speed `0.85-0.9`.
- Credentials must come from env vars: `YANDEX_API_KEY`, optional `YANDEX_FOLDER_ID`, optional `YANDEX_TTS_VOICE`.
- Visual style must use a dark grid, one central UI object, short phrases, cyan/teal highlights, and calm transitions.

---

### Task 1: Yandex SpeechKit Client

**Files:**
- Create: `core/yandex_tts.py`
- Create: `tests/test_yandex_tts.py`

**Interfaces:**
- Produces: `build_yandex_tts_request(text: str, *, voice: str = "ermil", speed: str = "0.88", emotion: str = "neutral", folder_id: str | None = None) -> tuple[str, dict[str, str], dict[str, str]]`
- Produces: `synthesize_yandex_tts(text: str, out_path: Path, *, api_key: str | None = None, folder_id: str | None = None, voice: str | None = None, speed: str = "0.88") -> Path`

- [ ] **Step 1: Write the failing request-builder test**

```python
from core.yandex_tts import build_yandex_tts_request


def test_build_yandex_tts_request_uses_male_voice_and_mp3():
    url, headers, data = build_yandex_tts_request(
        "Замыкание — это память функции.",
        voice="ermil",
        speed="0.88",
        folder_id="folder123",
    )

    assert url == "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    assert headers == {"Authorization": "Api-Key test-key"}
    assert data["text"] == "Замыкание — это память функции."
    assert data["lang"] == "ru-RU"
    assert data["voice"] == "ermil"
    assert data["speed"] == "0.88"
    assert data["emotion"] == "neutral"
    assert data["format"] == "mp3"
    assert data["folderId"] == "folder123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `YANDEX_API_KEY=test-key python3 -m unittest tests/test_yandex_tts.py`

Expected: FAIL with `ModuleNotFoundError: No module named 'core.yandex_tts'`.

- [ ] **Step 3: Implement request builder and synthesizer**

```python
from __future__ import annotations

import os
from pathlib import Path

import requests


YANDEX_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


def build_yandex_tts_request(
    text: str,
    *,
    voice: str = "ermil",
    speed: str = "0.88",
    emotion: str = "neutral",
    folder_id: str | None = None,
) -> tuple[str, dict[str, str], dict[str, str]]:
    api_key = os.environ.get("YANDEX_API_KEY", "test-key")
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "emotion": emotion,
        "speed": speed,
        "format": "mp3",
    }
    if folder_id:
        data["folderId"] = folder_id
    return YANDEX_TTS_URL, {"Authorization": f"Api-Key {api_key}"}, data


def synthesize_yandex_tts(
    text: str,
    out_path: Path,
    *,
    api_key: str | None = None,
    folder_id: str | None = None,
    voice: str | None = None,
    speed: str = "0.88",
) -> Path:
    key = api_key or os.environ.get("YANDEX_API_KEY")
    if not key:
        raise RuntimeError("YANDEX_API_KEY is required for Yandex SpeechKit TTS")
    old_key = os.environ.get("YANDEX_API_KEY")
    os.environ["YANDEX_API_KEY"] = key
    try:
        url, headers, data = build_yandex_tts_request(
            text,
            voice=voice or os.environ.get("YANDEX_TTS_VOICE", "ermil"),
            speed=speed,
            folder_id=folder_id or os.environ.get("YANDEX_FOLDER_ID"),
        )
    finally:
        if old_key is None:
            os.environ.pop("YANDEX_API_KEY", None)
        else:
            os.environ["YANDEX_API_KEY"] = old_key
    response = requests.post(url, headers=headers, data=data, timeout=120)
    response.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `YANDEX_API_KEY=test-key python3 -m unittest tests/test_yandex_tts.py`

Expected: PASS.

### Task 2: Storyboard and Timing Model

**Files:**
- Create: `core/motion_storyboard.py`
- Create: `tests/test_motion_storyboard.py`

**Interfaces:**
- Produces: `MotionCue` dataclass with `start: float`, `end: float`, `label: str`, `headline: str`, `accent: str`
- Produces: `closure_storyboard() -> list[MotionCue]`
- Produces: `storyboard_duration(cues: list[MotionCue]) -> float`

- [ ] **Step 1: Write failing storyboard test**

```python
from core.motion_storyboard import closure_storyboard, storyboard_duration


def test_closure_storyboard_is_calm_and_reference_like():
    cues = closure_storyboard()

    assert len(cues) == 6
    assert storyboard_duration(cues) == 55.0
    assert cues[0].headline == "Замыкание — это память функции."
    assert cues[-1].headline == "Каждый вызов создает свою память."
    assert all(cue.end > cue.start for cue in cues)
    assert all((cue.end - cue.start) >= 4.0 for cue in cues)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_motion_storyboard.py`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement storyboard module**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotionCue:
    start: float
    end: float
    label: str
    headline: str
    accent: str


def closure_storyboard() -> list[MotionCue]:
    return [
        MotionCue(0.0, 4.0, "CLOSURE", "Замыкание — это память функции.", "память"),
        MotionCue(4.0, 12.0, "FIRST COUNTER", "Первый вызов получает свой count.", "свой count"),
        MotionCue(12.0, 22.0, "SECOND COUNTER", "Второй вызов не трогает первый.", "не трогает"),
        MotionCue(22.0, 34.0, "INSIDE SCOPE", "Переменная живет внутри функции.", "внутри"),
        MotionCue(34.0, 46.0, "INDEPENDENT", "Жми кнопки — числа независимы.", "независимы"),
        MotionCue(46.0, 55.0, "MEMORY", "Каждый вызов создает свою память.", "свою память"),
    ]


def storyboard_duration(cues: list[MotionCue]) -> float:
    return max(cue.end for cue in cues) if cues else 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_motion_storyboard.py`

Expected: PASS.

### Task 3: Closure Motion Scene Renderer

**Files:**
- Create: `core/motion_closure.py`
- Create: `tests/test_motion_closure.py`

**Interfaces:**
- Consumes: `closure_storyboard()`, `storyboard_duration()`
- Produces: `render_closure_frame(t: float) -> np.ndarray`
- Produces: `build_closure_clip() -> moviepy.VideoClip`

- [ ] **Step 1: Write failing frame-shape test**

```python
import numpy as np

from core.motion_closure import render_closure_frame


def test_render_closure_frame_returns_vertical_rgb_frame():
    frame = render_closure_frame(16.0)

    assert isinstance(frame, np.ndarray)
    assert frame.shape == (1920, 1080, 3)
    assert frame.dtype == np.uint8
    assert frame.mean() > 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m unittest tests/test_motion_closure.py`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement first visual renderer**

Implement `core/motion_closure.py` using PIL drawing helpers:

```python
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


def _draw_centered_text(draw, y: int, text: str, font, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, y), text, font=font, fill=fill)


def _draw_card(draw, x, y, title, value, active=False):
    outline = CYAN if active else (58, 66, 80)
    glow = CYAN if active else CARD
    draw.rounded_rectangle((x - 8, y - 8, x + 328, y + 428), radius=34, fill=tuple(max(0, c // 3) for c in glow))
    draw.rounded_rectangle((x, y, x + 320, y + 420), radius=30, fill=CARD, outline=outline, width=3)
    _draw_centered_text(draw, y + 54, title, _font(MONO, 32), MUTED)
    value_font = _font(ROBOTO, 132)
    bbox = draw.textbbox((0, 0), str(value), font=value_font)
    draw.text((x + (320 - (bbox[2] - bbox[0])) // 2, y + 150), str(value), font=value_font, fill=CYAN if active else TEXT)
    for i, sign in enumerate(["−", "+"]):
        bx = x + 70 + i * 100
        by = y + 310
        draw.rounded_rectangle((bx, by, bx + 74, by + 74), radius=18, fill=(31, 39, 54))
        _draw_centered_text(draw, by + 10, sign, _font(ROBOTO, 48), TEXT)


def render_closure_frame(t: float) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _draw_grid(draw)
    cue = _active_cue(t)
    _draw_centered_text(draw, 250, cue.label, _font(ROBOTO, 30), MUTED)
    _draw_centered_text(draw, 320, cue.headline, _font(ROBOTO, 58), TEXT)
    phase = 0.5 + 0.5 * math.sin(t * 2.0)
    first_value = 0 if t < 34 else min(3, int((t - 34) // 3) + 1)
    second_value = 100 if t < 38 else 100 - min(2, int((t - 38) // 4) + 1)
    _draw_card(draw, 170, 660, "makeCounter(0)", first_value, active=t < 22 or phase > 0.55)
    _draw_card(draw, 590, 660, "makeCounter(100)", second_value, active=t >= 12 and phase > 0.35)
    note = "let count stays inside" if t >= 22 else "two calls, two memories"
    _draw_centered_text(draw, 1450, note, _font(MONO, 34), CYAN)
    return np.array(img, dtype=np.uint8)


def build_closure_clip() -> VideoClip:
    return VideoClip(render_closure_frame, duration=storyboard_duration(closure_storyboard()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m unittest tests/test_motion_closure.py`

Expected: PASS.

### Task 4: Motion Renderer CLI and Smoke Render

**Files:**
- Create: `render_motion.py`
- Create: `tests/test_render_motion_cli.py`

**Interfaces:**
- Consumes: `build_closure_clip()`
- Consumes: `synthesize_yandex_tts()`
- Produces CLI: `venv/bin/python render_motion.py --topic 36 --skip-voice`
- Produces output: `output/motion_36_closure.mp4`

- [ ] **Step 1: Write failing CLI argument test**

```python
import render_motion


def test_parse_args_defaults_to_topic_36_and_allows_skip_voice():
    args = render_motion.parse_args(["--skip-voice"])

    assert args.topic == 36
    assert args.skip_voice is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m unittest tests/test_render_motion_cli.py`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement CLI**

Create `render_motion.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from moviepy import AudioFileClip

from core.motion_closure import FPS, build_closure_clip
from core.yandex_tts import synthesize_yandex_tts
from render import FINAL_AUDIO_BITRATE, FINAL_FFMPEG_PARAMS, FINAL_VIDEO_BITRATE


OUTPUT = Path("output")
TEMP = Path("temp")


VOICE_TEXT = (
    "Замыкание — это память функции. "
    "Первый вызов получает свой count. "
    "Второй вызов не трогает первый. "
    "Переменная живет внутри функции. "
    "Жми кнопки — числа независимы. "
    "Каждый вызов создает свою память."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render calm motion explainer video")
    parser.add_argument("--topic", type=int, default=36)
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--voice", default="ermil")
    parser.add_argument("--speed", default="0.88")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.topic != 36:
        raise SystemExit("motion v2 currently supports only topic 36")
    OUTPUT.mkdir(exist_ok=True)
    TEMP.mkdir(exist_ok=True)
    clip = build_closure_clip()
    if not args.skip_voice:
        audio_path = synthesize_yandex_tts(
            VOICE_TEXT,
            TEMP / "motion_36_voice.mp3",
            voice=args.voice,
            speed=args.speed,
        )
        clip = clip.with_audio(AudioFileClip(str(audio_path)))
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
```

- [ ] **Step 4: Run CLI test**

Run: `venv/bin/python -m unittest tests/test_render_motion_cli.py`

Expected: PASS.

- [ ] **Step 5: Smoke-render without Yandex credentials**

Run: `venv/bin/python render_motion.py --topic 36 --skip-voice`

Expected: creates `output/motion_36_closure.mp4`.

- [ ] **Step 6: Smoke-render with Yandex credentials**

Run: `YANDEX_API_KEY=... venv/bin/python render_motion.py --topic 36 --voice ermil --speed 0.88`

Expected: creates `output/motion_36_closure.mp4` with male Yandex voice.

## Self-Review

- Spec coverage: Yandex TTS, male voice, calm pacing, separate renderer, topic `36`, and reference-like visuals are covered.
- Placeholder scan: no placeholder tasks remain; smoke command with real key intentionally uses `...` because credentials must not be written into docs.
- Type consistency: function names match across tasks: `build_yandex_tts_request`, `synthesize_yandex_tts`, `closure_storyboard`, `storyboard_duration`, `render_closure_frame`, `build_closure_clip`.
