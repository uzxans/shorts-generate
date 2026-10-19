#!/usr/bin/env python3
"""Generate 1080x1920 YouTube Shorts from topics.json.

Usage:
    python3 render.py --topic 1
    python3 render.py --topics 1,2,3
    python3 render.py --all
    python3 render.py --topic 1 --skip-voice
    python3 render.py --topic 1 --max-duration 0
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

import edge_tts
from moviepy import AudioFileClip, CompositeAudioClip, VideoClip, VideoFileClip

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

W, H = 1080, 1920
FPS = 30
FINAL_VIDEO_BITRATE = "12M"
FINAL_AUDIO_BITRATE = "320k"
FINAL_FFMPEG_PARAMS = [
    "-pix_fmt",
    "yuv420p",
    "-color_primaries",
    "bt709",
    "-color_trc",
    "bt709",
    "-colorspace",
    "bt709",
    "-movflags",
    "+faststart",
]

# Default target for YouTube Shorts. Set SHORTS_MAX_DURATION=0 or pass
# --max-duration 0 to disable duration scaling entirely.
DEFAULT_MAX_DURATION = float(os.environ.get("SHORTS_MAX_DURATION", "60"))
TAIL_PAD = 1.2  # extra seconds after voice ends (so CTA doesn't end abruptly)

MUSIC_VOLUME = 0.18
VOICE_VOLUME = 1.0

ROOT = Path(__file__).resolve().parent
TOPICS_JSON = ROOT / "topics.json"
TEMP = ROOT / "temp"
OUTPUT = ROOT / "output"
ASSETS = ROOT / "assets"
TEMP.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

MUSIC_PATH = ASSETS / "music.mp3"
AVATAR_PATH = ASSETS / "fotoavatar.png"
CTA_VIDEO_PATH = ASSETS / "frog.mp4"

ROBOTO_BOLD_PATH = ASSETS / "Roboto-Bold.ttf"
ROBOTO_BOLD_URL = "https://github.com/googlefonts/roboto-3-classic/raw/main/fonts/ttf/Roboto-Bold.ttf"
MONTSERRAT_BOLD_FALLBACK = ASSETS / "Montserrat" / "Montserrat-Bold.ttf"
MONO_FONT_PATH = ASSETS / "JetBrainsMono-Regular.ttf"
MONO_FONT_URL = "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Regular.ttf"
MONO_BOLD_PATH = ASSETS / "JetBrainsMono-Bold.ttf"
MONO_BOLD_URL = "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Bold.ttf"

VOICE = "ru-RU-DmitryNeural"


from dataclasses import dataclass


THEMES = [
    {
        "name": "cyan_lime",
        "bg0": "#061115",
        "bg1": "#10181f",
        "accent": "#22d3ee",
        "accent2": "#a3e635",
        "panel": "#0d1820",
        "panel2": "#132635",
        "text": "#f8fafc",
        "muted": "#9fb6c3",
    },
    {
        "name": "rose_amber",
        "bg0": "#170b12",
        "bg1": "#21140e",
        "accent": "#fb7185",
        "accent2": "#fbbf24",
        "panel": "#211018",
        "panel2": "#322015",
        "text": "#fff7ed",
        "muted": "#f0b9a4",
    },
    {
        "name": "mint_blue",
        "bg0": "#07130f",
        "bg1": "#0b1726",
        "accent": "#34d399",
        "accent2": "#60a5fa",
        "panel": "#0b1b17",
        "panel2": "#102238",
        "text": "#f0fdf4",
        "muted": "#a7c9bc",
    },
    {
        "name": "gold_ink",
        "bg0": "#11100a",
        "bg1": "#151b24",
        "accent": "#facc15",
        "accent2": "#38bdf8",
        "panel": "#19170f",
        "panel2": "#17202b",
        "text": "#fffdea",
        "muted": "#c9c3a2",
    },
]


@dataclass
class Durations:
    total: float
    hook: float
    code_demo: float
    keypoints: float
    cta: float
    typing_interval: float
    keypoint_slide: float

    @property
    def hook_end(self) -> float:
        return self.hook

    @property
    def code_end(self) -> float:
        return self.hook + self.code_demo

    @property
    def kp_end(self) -> float:
        return self.hook + self.code_demo + self.keypoints


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


_WORD_RE = re.compile(r"[\w]+", re.UNICODE)


def count_words(s: str) -> int:
    return len(_WORD_RE.findall(s))


def assign_sentences_to_scenes(sentences: list[str]) -> tuple[list[int], list[int], list[int], list[int]]:
    """Map sentence indices → (hook, code+demo, keypoints, cta).

    Heuristic: 1st sentence is the hook, last is the CTA; the one before the
    CTA is treated as a keypoint summary if there are at least 4 sentences;
    everything in between explains the code.
    """
    n = len(sentences)
    if n == 0:
        return [], [], [], []
    if n == 1:
        return [0], [], [], []
    if n == 2:
        return [0], [], [], [1]
    if n == 3:
        return [0], [1], [], [2]
    if n == 4:
        return [0], [1], [2], [3]
    return [0], list(range(1, n - 2)), [n - 2], [n - 1]


# ----------------------------------------------------------------------------
# LLM-based scene assignment (DeepSeek or Anthropic) with heuristic fallback
# ----------------------------------------------------------------------------

_SCENE_PROMPT = """Раздели предложения voiceover'а для YouTube Shorts на 4 сцены.

Сцены:
- "hook" — вступление, цепляющий вопрос/обещание ("Хочешь...?", "За 60 секунд...")
- "code" — объяснение кода, как и что работает
- "keypoints" — короткое summary, что важно запомнить, варианты применения
- "cta" — призыв подписаться/лайкнуть/сохранить

Предложения (нумерация от 0):
{numbered}

Правила:
- Каждый индекс попадает РОВНО в одну сцену.
- Любая сцена может быть пустой массив.
- Последнее предложение почти всегда — cta.
- Первое предложение почти всегда — hook.
- Возвращай СТРОГО JSON без комментариев.

Формат:
{{"hook": [0], "code": [1, 2, 3], "keypoints": [4], "cta": [5]}}"""


def _scene_prompt(sentences: list[str]) -> str:
    numbered = "\n".join(f"{i}: {s}" for i, s in enumerate(sentences))
    return _SCENE_PROMPT.format(numbered=numbered)


def _parse_scene_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    out = {}
    for key in ("hook", "code", "keypoints", "cta"):
        v = obj.get(key, [])
        if isinstance(v, list) and all(isinstance(x, int) for x in v):
            out[key] = v
        else:
            out[key] = []
    return out


def _llm_deepseek(prompt: str, api_key: str) -> str:
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты возвращаешь только валидный JSON, без пояснений."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _llm_anthropic(prompt: str, api_key: str) -> str:
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    r.raise_for_status()
    parts = r.json().get("content", [])
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text")


_PHONETIC_PROMPT = """Перепиши текст для русской озвучки edge-tts (голос ru-RU-DmitryNeural).
Замени все английские слова, термины и аббревиатуры на их РУССКОЕ фонетическое написание,
чтобы синтезатор произнёс их естественно по-русски. Голос русский, английские буквы он читает плохо.

Правила:
- Аббревиатуры по буквам: CSS → "си-эс-эс", JS → "джей-эс", HTML → "эйч-ти-эм-эль",
  API → "эй-пи-ай", JSON → "джейсон", URL → "ю-эр-эл", DOM → "дом", SSL → "эс-эс-эл"
- Свойства и термины транслитерация: hover → "ховер", flexbox → "флексбокс",
  box-shadow → "бокс-шэдоу", padding → "паддинг", margin → "маржин",
  background → "бэкграунд", const → "конст", let → "лет", function → "функшн",
  transition → "транзишн", grid → "грид", animation → "анимэйшн", keyframes → "киф­реймс",
  z-index → "зи-индекс"
- Числа и единицы оставлять цифрами с русскими словами: "8 строк", "10 пикселей"
- Пунктуация (точка, запятая, тире, вопрос) — без изменений
- Количество предложений и порядок слов СТРОГО сохрани
- Никаких пояснений, кавычек, markdown — верни ОДНУ строку текста готовую для синтеза

Текст:
{text}"""


def llm_phonetic_voiceover(text: str) -> tuple[str | None, str]:
    """Use the LLM to rewrite English/code terms in Russian phonetics.

    Returns (cleaned_text or None, provider_label).
    """
    prompt = _PHONETIC_PROMPT.format(text=text)
    ds = os.environ.get("DEEPSEEK_API_KEY")
    if ds:
        try:
            content = _llm_deepseek_text(prompt, ds)
            return _strip_wrapping(content), "deepseek"
        except Exception as e:
            print(f"   ⚠️  DeepSeek phonetic failed ({e.__class__.__name__}): {e}")
    an = os.environ.get("ANTHROPIC_API_KEY")
    if an:
        try:
            content = _llm_anthropic(prompt, an)
            return _strip_wrapping(content), "anthropic"
        except Exception as e:
            print(f"   ⚠️  Anthropic phonetic failed: {e}")
    return None, "skip"


def _strip_wrapping(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\s*|\s*```$", "", s, flags=re.MULTILINE).strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("«") and s.endswith("»")):
        s = s[1:-1].strip()
    return s


def _llm_deepseek_text(prompt: str, api_key: str) -> str:
    """DeepSeek call expecting plain text (not JSON)."""
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты возвращаешь только результат без пояснений."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def llm_assign_scenes(sentences: list[str]) -> tuple[dict | None, str]:
    """Returns (scene_assignment dict or None, provider_label)."""
    if not sentences:
        return None, "skip"
    prompt = _scene_prompt(sentences)
    ds = os.environ.get("DEEPSEEK_API_KEY")
    if ds:
        try:
            return _parse_scene_json(_llm_deepseek(prompt, ds)), "deepseek"
        except Exception as e:
            print(f"   ⚠️  DeepSeek failed ({e.__class__.__name__}: {e}); trying next…")
    an = os.environ.get("ANTHROPIC_API_KEY")
    if an:
        try:
            return _parse_scene_json(_llm_anthropic(prompt, an)), "anthropic"
        except Exception as e:
            print(f"   ⚠️  Anthropic failed ({e.__class__.__name__}: {e}); falling back to heuristic")
    return None, "heuristic"


def compute_durations_from_audio(
    tts_meta: dict,
    voiceover_text: str,
    n_keypoints: int,
    n_code_lines: int,
    scene_assignment: dict | None = None,
    max_duration: float | None = DEFAULT_MAX_DURATION,
) -> Durations:
    sentences = split_sentences(voiceover_text)
    sent_meta: list[dict] = tts_meta.get("sentences", [])
    if scene_assignment:
        hook_g = scene_assignment.get("hook", [])
        code_g = scene_assignment.get("code", [])
        kp_g = scene_assignment.get("keypoints", [])
        cta_g = scene_assignment.get("cta", [])
    else:
        hook_g, code_g, kp_g, cta_g = assign_sentences_to_scenes(sentences)

    audio_total = (sent_meta[-1]["offset"] + sent_meta[-1]["duration"]) if sent_meta else 25.0

    groups_in_order = [hook_g, code_g, kp_g, cta_g]

    def transition_after(group_idx: int) -> float | None:
        """Time at which the NEXT non-empty group's first sentence begins.

        Using the next sentence's start (instead of this group's last end) makes
        scene cuts land at the same instant the new audio begins, eliminating
        the small TTS inter-sentence gap that caused video to lag the audio.
        """
        for i in range(group_idx + 1, len(groups_in_order)):
            g = groups_in_order[i]
            if g and sent_meta:
                return float(sent_meta[g[0]]["offset"])
        return None

    def end_time(group: list[int]) -> float | None:
        if not group or not sent_meta:
            return None
        sent_i = min(group[-1], len(sent_meta) - 1)
        s = sent_meta[sent_i]
        return float(s["offset"] + s["duration"])

    h_end = transition_after(0) or end_time(hook_g) or 2.0
    c_end = transition_after(1) or end_time(code_g) or h_end
    k_end = transition_after(2) or end_time(kp_g) or c_end
    final_audio_end = end_time(cta_g) if cta_g else audio_total

    # Strict audio-aligned scene boundaries. If a scene has no audio assigned
    # (because the voiceover has too few sentences), fall back to a tiny visible
    # minimum so the scene still appears.
    hook = h_end
    code_demo = max(c_end - h_end, 4.0)
    keypoints = max(k_end - c_end, 2.5)
    cta = max(final_audio_end - k_end, 2.0) + TAIL_PAD

    total_dur = hook + code_demo + keypoints + cta

    if max_duration and max_duration > 0 and total_dur > max_duration:
        scale = max_duration / total_dur
        hook *= scale
        code_demo *= scale
        keypoints *= scale
        cta *= scale
        total_dur = max_duration

    typing_interval = max(0.4, min(1.3, (code_demo - 1.0) / max(n_code_lines, 1)))
    keypoint_slide = keypoints / max(n_keypoints, 1)
    return Durations(total_dur, hook, code_demo, keypoints, cta, typing_interval, keypoint_slide)


def compute_durations_no_audio(n_keypoints: int, n_code_lines: int) -> Durations:
    hook, code_demo, keypoints, cta = 2.5, 22.0, 6.0, 4.0
    total = hook + code_demo + keypoints + cta
    typing_interval = max(0.5, min(1.4, (code_demo - 2.0) / max(n_code_lines, 1)))
    return Durations(total, hook, code_demo, keypoints, cta, typing_interval, keypoints / max(n_keypoints, 1))

# ----------------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------------

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def pick_theme(topic: dict) -> dict:
    key = f"{topic.get('language', '')}:{topic.get('id', 0)}:{topic.get('title', '')}"
    idx = sum(ord(c) for c in key) % len(THEMES)
    return THEMES[idx]


def blend_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def make_backdrop(theme: dict, *, grid: bool = True) -> np.ndarray:
    c0 = np.array(hex_to_rgb(theme["bg0"]), dtype=np.float32)
    c1 = np.array(hex_to_rgb(theme["bg1"]), dtype=np.float32)
    accent = np.array(hex_to_rgb(theme["accent"]), dtype=np.float32)
    accent2 = np.array(hex_to_rgb(theme["accent2"]), dtype=np.float32)

    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    base = c0 * (1 - y) + c1 * y
    base = np.broadcast_to(base, (H, W, 3)).copy()

    beam = np.clip(1 - np.abs((x * 1.35 + y * 0.75) - 0.78) / 0.22, 0, 1) ** 2
    base += beam * accent.reshape(1, 1, 3) * 0.22
    beam2 = np.clip(1 - np.abs((x * 0.9 - y * 0.95) + 0.28) / 0.18, 0, 1) ** 2
    base += beam2 * accent2.reshape(1, 1, 3) * 0.16

    if grid:
        grid_mask = np.zeros((H, W), dtype=np.float32)
        grid_mask[::80, :] = 1.0
        grid_mask[:, ::80] = 1.0
        base += grid_mask[:, :, None] * 18

    rng = np.random.default_rng(42)
    noise = rng.normal(0, 3.0, (H, W, 1)).astype(np.float32)
    base += noise
    return np.clip(base, 0, 255).astype(np.uint8)


def draw_soft_rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)
    if outline:
        draw.rounded_rectangle(box, radius=radius, outline=outline, width=width)


def add_glow_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    glow: str,
    *,
    anchor: str | None = None,
    stroke_width: int = 0,
) -> None:
    x, y = xy
    for r, alpha in ((10, 70), (5, 95), (2, 140)):
        color = hex_to_rgb(glow) + (alpha,)
        draw.text((x, y), text, font=font, fill=color, anchor=anchor, stroke_width=r, stroke_fill=color)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor, stroke_width=stroke_width, stroke_fill="#061115")


def decorate_demo_frames(frames: list[np.ndarray], w: int, h: int, theme: dict) -> list[np.ndarray]:
    decorated: list[np.ndarray] = []
    accent = hex_to_rgb(theme["accent"])
    accent2 = hex_to_rgb(theme["accent2"])
    bg = make_backdrop(theme, grid=False)
    bg_small = Image.fromarray(bg).resize((w, h), Image.LANCZOS)
    for arr in frames:
        frame = Image.fromarray(arr).convert("RGB").resize((w - 34, h - 34), Image.LANCZOS)
        canvas = bg_small.copy().convert("RGBA")
        shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        sd.rounded_rectangle([18, 20, w - 16, h - 10], radius=44, fill=(0, 0, 0, 120))
        sd.rounded_rectangle([14, 14, w - 20, h - 18], radius=42, fill=accent + (28,), outline=accent2 + (120,), width=3)
        canvas.alpha_composite(shade)
        mask = Image.new("L", frame.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, frame.size[0] - 1, frame.size[1] - 1], radius=32, fill=255)
        canvas.paste(frame, (17, 17), mask)
        decorated.append(np.array(canvas.convert("RGB")))
    return decorated


_VIGNETTE_CACHE: np.ndarray | None = None


def cinematic_grade(base: np.ndarray, t: float, theme: dict) -> np.ndarray:
    global _VIGNETTE_CACHE
    out = base.astype(np.float32)
    if _VIGNETTE_CACHE is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dx = (xx - W / 2) / (W / 2)
        dy = (yy - H / 2) / (H / 2)
        dist = np.sqrt(dx * dx + dy * dy)
        _VIGNETTE_CACHE = np.clip((dist - 0.36) / 0.76, 0, 1)[:, :, None]
    out *= 1 - _VIGNETTE_CACHE * 0.34

    x = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    pos = (t * 0.08) % 1.6 - 0.3
    sweep = np.clip(1 - np.abs((x + y * 0.22) - pos) / 0.06, 0, 1) ** 2
    out += sweep * np.array(hex_to_rgb(theme["accent"]), dtype=np.float32).reshape(1, 1, 3) * 0.28
    return np.clip(out, 0, 255).astype(np.uint8)


def ensure_font(path: Path, url: str, fallback: Path | None = None) -> Path:
    if path.exists():
        return path
    print(f"   ⬇️  downloading {path.name}…")
    try:
        r = requests.get(url, timeout=120, allow_redirects=True)
        r.raise_for_status()
        path.write_bytes(r.content)
        return path
    except Exception as e:
        if fallback and fallback.exists():
            print(f"   ⚠️  download failed ({e.__class__.__name__}); using fallback {fallback.name}")
            path.write_bytes(fallback.read_bytes())
            return path
        raise


def transliterate(s: str) -> str:
    table = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    return "".join(table.get(c, c) for c in s.lower())


def slugify(title: str) -> str:
    # First word usually carries the topic ("CSS-кнопка", "Gradient-текст") —
    # later words like "с", "за 60 секунд" are filler and bloat the filename.
    first = title.split()[0] if title.strip() else "video"
    s = transliterate(first)
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "video"


def vertical_gradient(w: int, h: int, c0, c1) -> np.ndarray:
    t = np.linspace(0, 1, h, dtype=np.float32).reshape(h, 1, 1)
    c0 = np.array(c0, dtype=np.float32).reshape(1, 1, 3)
    c1 = np.array(c1, dtype=np.float32).reshape(1, 1, 3)
    col = c0 * (1 - t) + c1 * t
    return np.ascontiguousarray(np.broadcast_to(col, (h, w, 3)).astype(np.uint8))


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=font) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def paste_rgba_on_rgb(base: np.ndarray, overlay_rgba: np.ndarray, x: int, y: int) -> np.ndarray:
    """Alpha-composite an RGBA overlay onto an RGB base array (in place is fine)."""
    bh, bw, _ = base.shape
    oh, ow, _ = overlay_rgba.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + ow, bw), min(y + oh, bh)
    if x0 >= x1 or y0 >= y1:
        return base
    ox0, oy0 = x0 - x, y0 - y
    ox1, oy1 = ox0 + (x1 - x0), oy0 + (y1 - y0)

    region = base[y0:y1, x0:x1].astype(np.float32)
    over = overlay_rgba[oy0:oy1, ox0:ox1]
    a = over[:, :, 3:4].astype(np.float32) / 255.0
    rgb = over[:, :, :3].astype(np.float32)
    out = region * (1 - a) + rgb * a
    base[y0:y1, x0:x1] = np.clip(out, 0, 255).astype(np.uint8)
    return base


# ----------------------------------------------------------------------------
# Syntax highlighting
# ----------------------------------------------------------------------------

CSS_COLORS = {
    "property": "#9cdcfe",
    "value": "#ce9178",
    "selector": "#d7ba7d",
    "punct": "#ffd700",
    "comment": "#6a9955",
    "default": "#d4d4d4",
}

JS_COLORS = {
    "keyword": "#c586c0",
    "string": "#ce9178",
    "function": "#dcdcaa",
    "comment": "#6a9955",
    "number": "#b5cea8",
    "default": "#d4d4d4",
    "punct": "#ffd700",
}

JS_KEYWORDS = {
    "const", "let", "var", "function", "return", "if", "else", "for", "while",
    "do", "switch", "case", "break", "continue", "new", "class", "extends",
    "this", "super", "import", "export", "from", "as", "async", "await",
    "try", "catch", "finally", "throw", "typeof", "instanceof", "in", "of",
    "true", "false", "null", "undefined", "void",
}


def tokenize_css_line(line: str) -> list[tuple[str, str]]:
    if re.match(r"\s*/\*.*?\*/\s*$", line):
        return [(line, CSS_COLORS["comment"])]
    if line.strip() == "}":
        return [(line, CSS_COLORS["punct"])]
    if "{" in line and ":" not in line.split("{")[0]:
        before, sep, after = line.partition("{")
        out: list[tuple[str, str]] = []
        if before:
            out.append((before, CSS_COLORS["selector"]))
        out.append((sep, CSS_COLORS["punct"]))
        if after:
            out.append((after, CSS_COLORS["default"]))
        return out
    m = re.match(r"(\s*)([\w-]+)(\s*:\s*)(.*?)(;?\s*)$", line)
    if m:
        ws, prop, colon, val, end = m.groups()
        out = []
        if ws:
            out.append((ws, CSS_COLORS["default"]))
        out.append((prop, CSS_COLORS["property"]))
        out.append((colon, CSS_COLORS["punct"]))
        out.append((val, CSS_COLORS["value"]))
        if end:
            out.append((end, CSS_COLORS["punct"]))
        return out
    return [(line, CSS_COLORS["default"])]


_JS_PATTERN = re.compile(
    r"(\s+)|"
    r"(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|"
    r"(//.*$)|"
    r"(/\*.*?\*/)|"
    r"(\b\d+(?:\.\d+)?\b)|"
    r"(\b[A-Za-z_$][A-Za-z0-9_$]*)(?=\s*\()|"
    r"(\b[A-Za-z_$][A-Za-z0-9_$]*\b)|"
    r"([{}()\[\];,.:?<>=+\-*/%&|!^~])|"
    r"(.)",
    re.DOTALL,
)


def tokenize_js_line(line: str) -> list[tuple[str, str]]:
    if line.lstrip().startswith("//"):
        return [(line, JS_COLORS["comment"])]
    out: list[tuple[str, str]] = []
    for m in _JS_PATTERN.finditer(line):
        ws, s, cm, bcm, num, fn, ident, p, other = m.groups()
        if ws is not None:
            out.append((ws, JS_COLORS["default"]))
        elif s is not None:
            out.append((s, JS_COLORS["string"]))
        elif cm is not None:
            out.append((cm, JS_COLORS["comment"]))
        elif bcm is not None:
            out.append((bcm, JS_COLORS["comment"]))
        elif num is not None:
            out.append((num, JS_COLORS["number"]))
        elif fn is not None:
            out.append((fn, JS_COLORS["function"]))
        elif ident is not None:
            color = JS_COLORS["keyword"] if ident in JS_KEYWORDS else JS_COLORS["default"]
            out.append((ident, color))
        elif p is not None:
            out.append((p, JS_COLORS["punct"]))
        elif other is not None:
            out.append((other, JS_COLORS["default"]))
    return out


def tokenize_line(line: str, language: str) -> list[tuple[str, str]]:
    if language in ("js", "javascript"):
        return tokenize_js_line(line)
    return tokenize_css_line(line)


# ----------------------------------------------------------------------------
# Code panel
# ----------------------------------------------------------------------------

def render_code_panel(
    code: str,
    language: str,
    w: int,
    h: int,
    n_visible_lines: int,
    theme: dict,
    fontsize: int = 32,
) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    panel = hex_to_rgb(theme["panel"])
    panel2 = hex_to_rgb(theme["panel2"])
    accent = hex_to_rgb(theme["accent"])
    accent2 = hex_to_rgb(theme["accent2"])
    draw.rounded_rectangle([0, 12, w - 1, h - 1], radius=36, fill=(0, 0, 0, 120))
    draw.rounded_rectangle([0, 0, w - 1, h - 14], radius=36, fill=panel + (246,), outline=accent + (155,), width=2)

    title_h = 78
    draw.rounded_rectangle([0, 0, w - 1, title_h], radius=36, fill=panel2 + (255,))
    draw.rectangle([0, title_h - 34, w - 1, title_h], fill=panel2 + (255,))
    draw.line([0, title_h, w, title_h], fill=accent2 + (130,), width=2)
    cy = title_h // 2
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        cx = 30 + i * 32
        draw.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=hex_to_rgb(c))
    title = "style.css" if language == "css" else "script.js"
    title_font = ImageFont.truetype(str(MONO_BOLD_PATH), 26)
    tw = draw.textlength(title, font=title_font)
    draw.text(((w - tw) // 2, (title_h - 30) // 2), title, font=title_font, fill=theme["muted"])

    mono = ImageFont.truetype(str(MONO_FONT_PATH), fontsize)
    line_h = int(fontsize * 1.45)
    pad_x, pad_y = 60, title_h + 26

    lines = code.split("\n")
    visible = lines[:n_visible_lines]
    for i, line in enumerate(visible):
        ln = f"{i + 1:>2}"
        draw.text((pad_x - 50, pad_y + i * line_h), ln, font=mono, fill="#5a5a5a")
        x = pad_x
        for text, color in tokenize_line(line, language):
            draw.text((x, pad_y + i * line_h), text, font=mono, fill=hex_to_rgb(color))
            x += int(draw.textlength(text, font=mono))

    cursor_i = min(n_visible_lines - 1, len(lines) - 1)
    if cursor_i >= 0:
        cx = pad_x + 8
        cy2 = pad_y + cursor_i * line_h + line_h - 7
        draw.rectangle([cx, cy2, min(w - 48, cx + 26), cy2 + 4], fill=accent)

    return img.convert("RGB")


# ----------------------------------------------------------------------------
# Voiceover (edge-tts)
# ----------------------------------------------------------------------------

async def _tts_async(text: str, out_path: Path) -> dict:
    com = edge_tts.Communicate(text, VOICE)
    chunks: list[bytes] = []
    sentences: list[dict] = []
    words: list[dict] = []
    async for event in com.stream():
        t = event["type"]
        if t == "audio":
            chunks.append(event["data"])
        elif t == "SentenceBoundary":
            sentences.append({
                "offset": event["offset"] / 1e7,
                "duration": event["duration"] / 1e7,
                "text": event["text"],
            })
        elif t == "WordBoundary":
            words.append({
                "offset": event["offset"] / 1e7,
                "duration": event["duration"] / 1e7,
                "text": event["text"],
            })
    out_path.write_bytes(b"".join(chunks))
    return {"sentences": sentences, "words": words}


def generate_voiceover(text: str, out_path: Path) -> dict:
    return asyncio.run(_tts_async(text, out_path))


def build_final_audio(voice: AudioFileClip | None, video_dur: float) -> AudioFileClip | None:
    """Mix voiceover with looping background music. Returns None if no audio at all."""
    music_clip = None
    if MUSIC_PATH.exists():
        m = AudioFileClip(str(MUSIC_PATH))
        if m.duration >= video_dur:
            music_clip = m.subclipped(0, video_dur).with_volume_scaled(MUSIC_VOLUME)
        else:
            # Loop the track to cover the full video
            loops = []
            t = 0.0
            while t < video_dur:
                take = min(m.duration, video_dur - t)
                loops.append(m.subclipped(0, take))
                t += take
            from moviepy import concatenate_audioclips
            music_clip = concatenate_audioclips(loops).with_volume_scaled(MUSIC_VOLUME)

    if voice is None and music_clip is None:
        return None
    if voice is None:
        return music_clip
    if music_clip is None:
        return voice.with_volume_scaled(VOICE_VOLUME)
    return CompositeAudioClip([music_clip, voice.with_volume_scaled(VOICE_VOLUME)])


# ----------------------------------------------------------------------------
# Subtitle splitting / timing
# ----------------------------------------------------------------------------

_PHRASE_SPLIT = re.compile(r"(?<=[\.\!\?,;:—])\s+")


def split_into_phrases(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    parts = _PHRASE_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def estimate_phrase_durations(phrases: list[str], total: float) -> list[float]:
    lens = [max(1, len(p)) for p in phrases]
    s = sum(lens)
    return [total * (l / s) for l in lens]


# ----------------------------------------------------------------------------
# Scene asset builders (PIL → np.ndarray)
# ----------------------------------------------------------------------------

def build_hook_overlay(hook_text: str, theme: dict) -> np.ndarray:
    """RGBA overlay: dark gradient at top + hook text. Painted over the demo bg
    in the hook scene so the viewer immediately sees the working result."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    accent = hex_to_rgb(theme["accent"])
    accent2 = hex_to_rgb(theme["accent2"])

    # Top dark gradient for text legibility against the demo.
    fade_h = 760
    tg = np.zeros((fade_h, W, 4), dtype=np.uint8)
    for y in range(fade_h):
        a = int(((1 - y / fade_h) ** 1.5) * 230)
        tg[y, :, 3] = a
    grad_top = Image.fromarray(tg, mode="RGBA")
    img.paste(grad_top, (0, 0), grad_top)

    # Bottom subtle vignette so result still pops without overpowering text.
    bot_h = 220
    bg = np.zeros((bot_h, W, 4), dtype=np.uint8)
    for y in range(bot_h):
        a = int((y / bot_h) * 130)
        bg[y, :, 3] = a
    grad_bot = Image.fromarray(bg, mode="RGBA")
    img.paste(grad_bot, (0, H - bot_h), grad_bot)

    draw = ImageDraw.Draw(img)
    eyebrow_font = ImageFont.truetype(str(ROBOTO_BOLD_PATH), 34)
    pill = "SHORTS LAB"
    pill_w = int(draw.textlength(pill, font=eyebrow_font) + 54)
    draw.rounded_rectangle([54, 72, 54 + pill_w, 126], radius=27, fill=accent + (220,), outline=accent2 + (210,), width=2)
    draw.text((81, 83), pill, font=eyebrow_font, fill="#061115")

    lines = hook_text.split("\n")
    font_size = 100
    while font_size > 62:
        font = ImageFont.truetype(str(ROBOTO_BOLD_PATH), font_size)
        if all(draw.textlength(line, font=font) <= W - 110 for line in lines):
            break
        font_size -= 4
    line_h = int(font_size * 1.18)
    total_h = line_h * len(lines)
    y0 = 170  # near the top so the demo body stays visible
    for i, line in enumerate(lines):
        tw = draw.textlength(line, font=font)
        add_glow_text(
            draw,
            ((W - tw) // 2, y0 + i * line_h),
            line,
            font,
            "white",
            theme["accent"],
            stroke_width=3,
        )

    # Bottom hint label so the viewer expects code next.
    hint_font = ImageFont.truetype(str(ROBOTO_BOLD_PATH), 38)
    hint = "Сейчас покажу как →"
    hw = draw.textlength(hint, font=hint_font)
    draw.rounded_rectangle([(W - hw) // 2 - 30, H - 152, (W + hw) // 2 + 30, H - 88], radius=32, fill=(0, 0, 0, 145), outline=accent + (190,), width=2)
    draw.text(((W - hw) // 2, H - 140), hint, font=hint_font, fill="white")

    return np.array(img)


# Layout for the code+demo scene. Reserves 1730..1880 for subtitles so they
# never sit on top of the demo block.
CODE_X = 40
CODE_Y = 60
CODE_W = W - 80
CODE_H = int(H * 0.45)            # ends at y=924
LABEL_Y = CODE_Y + CODE_H + 30    # y=954
DEMO_X = 50
DEMO_Y = LABEL_Y + 60             # y=1014
DEMO_W = W - 100                  # 980
DEMO_H = 1690 - DEMO_Y            # ends at y=1690 (clear of subtitles below)


def build_code_canvases(topic: dict, theme: dict) -> list[np.ndarray]:
    """Full-screen backgrounds: code panel + label drawn; demo region left empty."""
    code = topic["code"]
    language = topic.get("language", "css")
    n_lines = len(code.split("\n"))

    bg_base = Image.fromarray(make_backdrop(theme))
    bd = ImageDraw.Draw(bg_base)
    label_font = ImageFont.truetype(str(ROBOTO_BOLD_PATH), 38)
    bd.rounded_rectangle([50, LABEL_Y - 8, 290, LABEL_Y + 48], radius=28, fill=hex_to_rgb(theme["accent"]))
    bd.text((78, LABEL_Y), "Результат", font=label_font, fill="#061115")
    bd.text((310, LABEL_Y), "живой preview", font=ImageFont.truetype(str(ROBOTO_BOLD_PATH), 30), fill=theme["muted"])
    bg_base_arr = np.array(bg_base)

    canvases: list[np.ndarray] = []
    for k in range(1, n_lines + 1):
        canvas = bg_base_arr.copy()
        panel = render_code_panel(code, language, CODE_W, CODE_H, k, theme)
        canvas[CODE_Y:CODE_Y + CODE_H, CODE_X:CODE_X + CODE_W] = np.array(panel)
        canvases.append(canvas)
    return canvases


def draw_check_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=(34, 197, 94, 255))
    p1 = (size * 0.22, size * 0.52)
    p2 = (size * 0.43, size * 0.72)
    p3 = (size * 0.78, size * 0.30)
    draw.line([p1, p2], fill="white", width=int(size * 0.13))
    draw.line([p2, p3], fill="white", width=int(size * 0.13))
    return img


def build_keypoint_image(text: str, idx: int, total: int, theme: dict) -> np.ndarray:
    bg = make_backdrop(theme).copy()

    # Draw text into RGBA overlay so we can position
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype(str(ROBOTO_BOLD_PATH), 66)
    small = ImageFont.truetype(str(ROBOTO_BOLD_PATH), 34)

    icon_size = 96
    icon = draw_check_icon(icon_size)

    max_w = W - 220
    lines = wrap_text(text, font, max_w, draw)
    line_h = 84
    total_h = line_h * len(lines)
    card_x0, card_y0, card_x1, card_y1 = 80, 520, W - 80, 1320
    draw.rounded_rectangle([card_x0 + 14, card_y0 + 20, card_x1 + 14, card_y1 + 20], radius=52, fill=(0, 0, 0, 115))
    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=52,
        fill=hex_to_rgb(theme["panel"]) + (235,),
        outline=hex_to_rgb(theme["accent"]) + (190,),
        width=3,
    )
    badge = f"{idx + 1:02d}/{total:02d}"
    draw.rounded_rectangle([card_x0 + 44, card_y0 + 42, card_x0 + 190, card_y0 + 96], radius=27, fill=hex_to_rgb(theme["accent"]) + (230,))
    draw.text((card_x0 + 70, card_y0 + 50), badge, font=small, fill="#061115")

    y0 = card_y0 + (card_y1 - card_y0 - total_h) // 2 + 34
    for i, ln in enumerate(lines):
        tw = draw.textlength(ln, font=font)
        add_glow_text(draw, ((W - tw) // 2, y0 + i * line_h), ln, font, "white", theme["accent2"], stroke_width=2)

    # Icon above text
    icon_y = y0 - icon_size - 46
    icon_x = (W - icon_size) // 2
    overlay.paste(icon, (icon_x, icon_y), icon)

    paste_rgba_on_rgb(bg, np.array(overlay), 0, 0)
    return bg


def build_cta_frames() -> tuple[list[np.ndarray], float]:
    """Final-scene frames. Prefer a CTA video (frog.mp4); fall back to avatar PNG.

    Returns (frames_full_screen, fps). For a single image the list has one
    element and fps=1 (compose_frame just freezes it).
    """
    bg_color = hex_to_rgb("#0a0a0a")
    if CTA_VIDEO_PATH.exists():
        clip = VideoFileClip(str(CTA_VIDEO_PATH))
        fps = float(clip.fps) if clip.fps else 24.0
        frames: list[np.ndarray] = []
        for frame in clip.iter_frames(fps=fps, dtype="uint8"):
            pil = Image.fromarray(frame)
            frames.append(np.array(fit_into_box(pil, W, H, bg_color)))
        clip.close()
        return frames, fps
    if AVATAR_PATH.exists():
        img = Image.open(AVATAR_PATH).convert("RGB")
        return [np.array(fit_into_box(img, W, H, bg_color))], 1.0
    return [np.full((H, W, 3), bg_color, dtype=np.uint8)], 1.0


# ----------------------------------------------------------------------------
# Subtitles
# ----------------------------------------------------------------------------

SUB_TOP = 1730   # demo block ends at y=1690; subtitles live in 1730..1880
SUB_BOTTOM = 1880


def build_subtitle_overlay(text: str) -> tuple[np.ndarray, int, int]:
    """Return RGBA overlay + (x, y) where to place it on screen."""
    font = ImageFont.truetype(str(ROBOTO_BOLD_PATH), 38)
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    max_w = W - 160
    lines = wrap_text(text, font, max_w, d)
    # Cap to 2 lines so the box stays inside the subtitle strip.
    if len(lines) > 2:
        lines = lines[:2]
        # add ellipsis to last line if it was truncated
        last = lines[-1]
        while d.textlength(last + "…", font=font) > max_w and " " in last:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = last + "…"
    line_h = 50
    pad_x, pad_y = 28, 18
    text_w = max(d.textlength(ln, font=font) for ln in lines) if lines else 100
    box_w = int(min(max_w, text_w) + pad_x * 2)
    box_h = int(line_h * len(lines) + pad_y * 2)

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, box_w, box_h], radius=22, fill=(0, 0, 0, 175))
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=font)
        draw.text(((box_w - tw) / 2, pad_y + i * line_h), ln, font=font, fill="white")

    x = (W - box_w) // 2
    # Anchor inside the dedicated subtitle strip; if the box happens to be
    # taller, push it up so it never invades the demo zone.
    y = SUB_TOP + max(0, (SUB_BOTTOM - SUB_TOP - box_h) // 2)
    if y + box_h > SUB_BOTTOM:
        y = SUB_BOTTOM - box_h
    return np.array(img), x, y


def build_subtitle_track(voiceover_text: str, audio_dur: float) -> list[tuple[float, float, np.ndarray, int, int]]:
    phrases = split_into_phrases(voiceover_text)
    if not phrases:
        return []
    durs = estimate_phrase_durations(phrases, audio_dur)
    track: list[tuple[float, float, np.ndarray, int, int]] = []
    t = 0.0
    for phrase, d in zip(phrases, durs):
        rgba, x, y = build_subtitle_overlay(phrase)
        track.append((t, t + d, rgba, x, y))
        t += d
    return track


def build_subtitle_track_from_audio(
    voiceover_text: str,
    tts_meta: dict,
    video_dur: float,
) -> list[tuple[float, float, np.ndarray, int, int]]:
    """Time subtitles using sentence boundaries (and word boundaries when present).

    For each sentence, split into shorter phrases by , : ; — and distribute
    the sentence's audio span across phrases proportionally to char count.
    """
    sent_meta = tts_meta.get("sentences", [])
    if not sent_meta:
        return []

    sentences = split_sentences(voiceover_text)
    track: list[tuple[float, float, np.ndarray, int, int]] = []
    for i, sentence in enumerate(sentences):
        if i >= len(sent_meta):
            break
        s_start = float(sent_meta[i]["offset"])
        s_end = s_start + float(sent_meta[i]["duration"])
        if s_start >= video_dur:
            break
        # split sentence into phrases by inner punctuation
        phrases = [p for p in re.split(r"(?<=[,;:—])\s+", sentence) if p.strip()]
        if not phrases:
            phrases = [sentence]
        lens = [max(1, len(p)) for p in phrases]
        total_l = sum(lens)
        cur = s_start
        for phrase, l in zip(phrases, lens):
            d = (s_end - s_start) * (l / total_l)
            start, end = cur, min(cur + d, video_dur)
            cur = end
            if start >= video_dur:
                break
            rgba, x, y = build_subtitle_overlay(phrase.strip())
            track.append((start, end, rgba, x, y))
            if end >= video_dur:
                break
    return track


# ----------------------------------------------------------------------------
# Frame composition
# ----------------------------------------------------------------------------

def compose_frame(
    t: float,
    durs: Durations,
    hook_overlay: np.ndarray,
    hook_demo_frames: list[np.ndarray],
    demo_fps: float,
    code_canvases: list[np.ndarray],
    demo_frames: list[np.ndarray],
    keypoint_imgs: list[np.ndarray],
    kp_gradient: np.ndarray,
    cta_frames: list[np.ndarray],
    cta_fps: float,
    subtitle_track: list[tuple[float, float, np.ndarray, int, int]],
    bg_black: np.ndarray,
    theme: dict,
) -> np.ndarray:
    if t < durs.hook_end:
        # Background = looping demo (the result the viewer wants to build).
        if hook_demo_frames and len(hook_demo_frames) > 1:
            df_idx = int(t * demo_fps) % len(hook_demo_frames)
        else:
            df_idx = 0
        base = hook_demo_frames[df_idx].copy() if hook_demo_frames else bg_black.copy()

        # Hook text + dark gradients overlaid; fade in over 0.4s.
        fade = 0.4
        amul = min(1.0, t / fade) if fade > 0 else 1.0
        a = (hook_overlay[:, :, 3:4].astype(np.float32) * amul) / 255.0
        rgb = hook_overlay[:, :, :3].astype(np.float32)
        base_f = base.astype(np.float32) * (1 - a) + rgb * a
        base = np.clip(base_f, 0, 255).astype(np.uint8)
    elif t < durs.code_end:
        local = t - durs.hook_end
        idx = min(int(local / durs.typing_interval), len(code_canvases) - 1)
        base = code_canvases[idx].copy()
        if demo_frames:
            df_idx = int(local * demo_fps) % len(demo_frames) if len(demo_frames) > 1 else 0
            base[DEMO_Y:DEMO_Y + DEMO_H, DEMO_X:DEMO_X + DEMO_W] = demo_frames[df_idx]
    elif t < durs.kp_end:
        local = t - durs.code_end
        idx = min(int(local / durs.keypoint_slide), len(keypoint_imgs) - 1)
        slide_local = local - idx * durs.keypoint_slide
        if slide_local < 0.4:
            shift = int((1 - slide_local / 0.4) * 180)
            base = kp_gradient.copy()
            src = keypoint_imgs[idx]
            if shift < H:
                base[shift:H] = src[0:H - shift]
        else:
            base = keypoint_imgs[idx].copy()
    else:
        # CTA scene: looping cinematic clip (frog.mp4), no text/glow.
        local = t - durs.kp_end
        if len(cta_frames) > 1:
            idx = int(local * cta_fps) % len(cta_frames)
        else:
            idx = 0
        base = cta_frames[idx].copy()

    # Subtitles overlay (only during voiceover window)
    for start, end, rgba, x, y in subtitle_track:
        if start <= t < end:
            paste_rgba_on_rgb(base, rgba, x, y)
            break

    return cinematic_grade(base, t, theme)


# ----------------------------------------------------------------------------
# Topic pipeline
# ----------------------------------------------------------------------------

def detect_demo_mode(topic: dict) -> str | None:
    """Returns 'hover', 'passive', or None depending on what the demo needs."""
    blob = (topic.get("code", "") + "\n" + topic.get("demo_html", "")).lower()
    if ":hover" in blob:
        return "hover"
    if "@keyframes" in blob or "animation:" in blob or "animation ":
        # animation:/@keyframes triggers passive recording
        if "@keyframes" in blob or "animation:" in blob:
            return "passive"
    if "transition" in blob:
        # transitions usually need an interaction to fire
        return "hover"
    return None


def render_demo_asset(topic: dict, out_dir: Path, tid: int) -> tuple[Path, str]:
    """Render either a PNG (no animation) or an MP4 (animated/hover) demo.

    Returns (path, mode) where mode ∈ {'png', 'video'}.
    """
    mode = detect_demo_mode(topic)
    html_b64 = base64.b64encode(topic["demo_html"].encode("utf-8")).decode("ascii")
    if mode is None:
        out = out_dir / f"{tid}_demo.png"
        if not out.exists():
            subprocess.run(
                ["node", str(ROOT / "render_demo.js"), html_b64, str(out), "1080", "760"],
                cwd=str(ROOT), check=True,
            )
        return out, "png"

    out = out_dir / f"{tid}_demo.mp4"
    if not out.exists():
        cmd = [
            "node", str(ROOT / "render_demo.js"),
            html_b64, str(out), "1080", "760",
            "--video", "--duration", "3.0",
            "--fps", str(FPS),
            "--crf", "16",
            "--preset", "medium",
        ]
        if mode == "hover":
            cmd += ["--interactive", "hover"]
        subprocess.run(cmd, cwd=str(ROOT), check=True)
    return out, "video"


def fit_into_box(img: Image.Image, box_w: int, box_h: int, bg: tuple[int, int, int]) -> Image.Image:
    iw, ih = img.size
    scale = min(box_w / iw, box_h / ih)
    new_w, new_h = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (box_w, box_h), bg)
    canvas.paste(resized, ((box_w - new_w) // 2, (box_h - new_h) // 2))
    return canvas


def decode_demo_raw(demo_path: Path) -> tuple[list[Image.Image], float]:
    """Decode demo source to a list of PIL frames (native size). PNG → 1 frame."""
    if demo_path.suffix.lower() == ".png":
        return [Image.open(demo_path).convert("RGB")], 1.0
    clip = VideoFileClip(str(demo_path))
    fps = float(clip.fps) if clip.fps else 24.0
    frames = [Image.fromarray(f.copy()) for f in clip.iter_frames(fps=fps, dtype="uint8")]
    clip.close()
    return frames, fps


def resize_demo_to_box(raw: list[Image.Image], target_w: int, target_h: int) -> list[np.ndarray]:
    bg = hex_to_rgb("#0a0a0a")
    return [np.array(fit_into_box(img, target_w, target_h, bg)) for img in raw]


def render_topic(
    topic: dict,
    skip_voice: bool = False,
    use_llm: bool = True,
    max_duration: float | None = DEFAULT_MAX_DURATION,
) -> Path:
    if "script_timeline" in topic:
        from render_scripted import render_scripted_topic
        return render_scripted_topic(topic, skip_voice=skip_voice, max_duration=max_duration)
    tid = topic["id"]
    title = topic["title"]
    slug = slugify(title)
    theme = pick_theme(topic)
    print(f"\n🚀 [{tid}] {title}")

    ensure_font(ROBOTO_BOLD_PATH, ROBOTO_BOLD_URL, fallback=MONTSERRAT_BOLD_FALLBACK)
    ensure_font(MONO_FONT_PATH, MONO_FONT_URL)
    ensure_font(MONO_BOLD_PATH, MONO_BOLD_URL)

    demo_path, demo_kind = render_demo_asset(topic, TEMP, tid)
    print(f"   🖼️  demo: {demo_path.name} ({demo_kind}, mode={detect_demo_mode(topic) or 'static'})")

    # Phonetic cleanup of English terms — TTS reads "CSS" as «си-эс-эс», not "це-эс-эс".
    voice_text = topic["voiceover"]
    if not skip_voice and use_llm:
        clean_path = TEMP / f"{tid}_voice_clean.txt"
        if clean_path.exists():
            voice_text = clean_path.read_text(encoding="utf-8")
            print(f"   🔤  phonetic voiceover: cached")
        else:
            cleaned, provider = llm_phonetic_voiceover(topic["voiceover"])
            if cleaned:
                voice_text = cleaned
                clean_path.write_text(cleaned, encoding="utf-8")
                print(f"   🔤  phonetic voiceover via {provider}")

    voice_path = TEMP / f"{tid}_voice.mp3"
    meta_path = TEMP / f"{tid}_voice.json"
    tts_meta: dict = {}
    if not skip_voice:
        if not voice_path.exists() or not meta_path.exists():
            print("   🎙️  generating voiceover (edge-tts) + sentence boundaries…")
            tts_meta = generate_voiceover(voice_text, voice_path)
            meta_path.write_text(json.dumps(tts_meta, ensure_ascii=False))
        else:
            tts_meta = json.loads(meta_path.read_text())

    keypoints = [p.strip() for p in topic["key_points"].split("\n") if p.strip()]
    if not keypoints:
        keypoints = [topic.get("title", "")]
    n_lines = len(topic["code"].split("\n"))

    # Sanity check: phonetic rewrite must keep the same sentence count, otherwise
    # subtitles for the original text won't line up with TTS sentence offsets.
    if voice_text != topic["voiceover"]:
        if len(split_sentences(voice_text)) != len(split_sentences(topic["voiceover"])):
            print("   ⚠️  phonetic changed sentence count; reverting to original for sync safety")
            voice_text = topic["voiceover"]

    scene_assignment: dict | None = None
    if use_llm and tts_meta and tts_meta.get("sentences"):
        scenes_path = TEMP / f"{tid}_scenes.json"
        if scenes_path.exists():
            scene_assignment = json.loads(scenes_path.read_text())
            print(f"   🤖  scene assignment: cached {scenes_path.name}")
        else:
            sentences_split = split_sentences(voice_text)
            scene_assignment, provider = llm_assign_scenes(sentences_split)
            if scene_assignment is not None:
                scenes_path.write_text(json.dumps(scene_assignment, ensure_ascii=False))
                print(f"   🤖  scene assignment via {provider}: {scene_assignment}")
            else:
                print(f"   🤖  no LLM available ({provider}); using positional heuristic")

    if tts_meta and tts_meta.get("sentences"):
        durs = compute_durations_from_audio(
            tts_meta, voice_text, len(keypoints), n_lines, scene_assignment, max_duration
        )
    else:
        durs = compute_durations_no_audio(len(keypoints), n_lines)
    max_label = "off" if not max_duration or max_duration <= 0 else f"{max_duration:.0f}s"
    print(f"   ⏱  total={durs.total:.1f}s  max={max_label}  hook={durs.hook:.1f}  code={durs.code_demo:.1f}  kp={durs.keypoints:.1f}  cta={durs.cta:.1f}  type-step={durs.typing_interval:.2f}")

    audio = None
    if not skip_voice and voice_path.exists():
        audio = AudioFileClip(str(voice_path))
        if audio.duration > durs.total:
            audio = audio.subclipped(0, durs.total)

    print("   🎨  pre-rendering scene assets…")
    raw_demo, demo_fps = decode_demo_raw(demo_path)
    demo_frames = decorate_demo_frames(resize_demo_to_box(raw_demo, DEMO_W, DEMO_H), DEMO_W, DEMO_H, theme)
    hook_demo_frames = resize_demo_to_box(raw_demo, W, H)                  # for hook bg
    hook_overlay = build_hook_overlay(topic["hook_text"], theme)
    code_canvases = build_code_canvases(topic, theme)
    keypoint_imgs = [build_keypoint_image(p, i, len(keypoints), theme) for i, p in enumerate(keypoints)]
    cta_frames, cta_fps = build_cta_frames()
    bg_black = make_backdrop(theme)
    kp_gradient = make_backdrop(theme)

    subtitle_track: list[tuple[float, float, np.ndarray, int, int]] = []
    if tts_meta and tts_meta.get("sentences"):
        subtitle_track = build_subtitle_track_from_audio(topic["voiceover"], tts_meta, durs.total)
    elif audio is not None:
        subtitle_track = build_subtitle_track(topic["voiceover"], float(audio.duration))

    def make_frame(t: float) -> np.ndarray:
        return compose_frame(
            t, durs, hook_overlay, hook_demo_frames, demo_fps,
            code_canvases, demo_frames,
            keypoint_imgs, kp_gradient, cta_frames, cta_fps,
            subtitle_track, bg_black, theme,
        )

    final = VideoClip(make_frame, duration=durs.total)
    final_audio = build_final_audio(audio, durs.total)
    if final_audio is not None:
        final = final.with_audio(final_audio)

    out_path = OUTPUT / f"{tid}_{slug}.mp4"
    print(f"   💾  encoding → {out_path.relative_to(ROOT)}")
    final.write_videofile(
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
    print(f"   ✅  done: {out_path}")
    return out_path


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def parse_topic_ids(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Render YouTube Shorts from topics.json")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--topic", type=int, help="render single topic by id")
    g.add_argument("--topics", type=parse_topic_ids, help="comma-separated ids: 1,2,3")
    g.add_argument("--all", action="store_true", help="render every topic")
    parser.add_argument("--skip-voice", action="store_true", help="skip TTS voiceover (silent video)")
    parser.add_argument("--no-llm", action="store_true", help="skip LLM scene analysis, use positional heuristic")
    parser.add_argument("--validate-script", action="store_true", help="validate scripted topics without TTS/render")
    parser.add_argument("--build-only", action="store_true", help="prepare scripted project and audio without MP4 encoding")
    parser.add_argument(
        "--max-duration",
        type=float,
        default=DEFAULT_MAX_DURATION,
        help="max rendered duration in seconds; use 0 to disable scaling (default: env SHORTS_MAX_DURATION or 60)",
    )
    args = parser.parse_args()

    with open(TOPICS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    all_topics = data["topics"]

    if args.all:
        targets = all_topics
    elif args.topic is not None:
        targets = [t for t in all_topics if t["id"] == args.topic]
    else:
        targets = [t for t in all_topics if t["id"] in args.topics]

    if not targets:
        print("❌ no matching topics", file=sys.stderr)
        return 1

    for topic in targets:
        if args.validate_script or args.build_only:
            if "script_timeline" not in topic:
                parser.error(f"Тема {topic['id']} не содержит script_timeline")
            from render_scripted import render_scripted_topic
            render_scripted_topic(topic, skip_voice=args.skip_voice, max_duration=args.max_duration,
                                  validate_only=args.validate_script, build_only=args.build_only)
            continue
        render_topic(
            topic,
            skip_voice=args.skip_voice,
            use_llm=not args.no_llm,
            max_duration=args.max_duration,
        )

    if not (args.validate_script or args.build_only):
        print(f"\n🎉 rendered {len(targets)} video(s) → {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
