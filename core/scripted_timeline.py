"""Explicit, deterministic scene grammar; prose is never guessed into animation."""
from __future__ import annotations

import copy
import hashlib
import json
import math

PRESETS = {
    "title": {"reveal"}, "code": {"code_focus"},
    "perspective": {"depth"}, "tilt_card": {"hover_tilt", "axes"},
    "gradient": {"angle_spin"}, "bento": {"expand", "jump"},
    "spotlight": {"follow", "float"}, "skeleton": {"crossfade", "jump"},
    "takeaway": {"checklist"},
}
TRANSITIONS = {"slide", "crossfade", "zoom", "cut"}


def number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field}: требуется конечное число секунд")
    return float(value)


def validate_timeline(topic, outro_duration=4.041667, max_duration=60):
    if type(topic.get('id')) is not int or topic['id'] < 1:
        raise ValueError('id: требуется положительное целое число')
    if not isinstance(topic.get('title'), str) or not topic['title'].strip():
        raise ValueError('title: требуется название темы')
    board = copy.deepcopy(topic)
    scenes = board.get("script_timeline")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("script_timeline: требуется непустой список сцен")
    end = 0.0
    for i, scene in enumerate(scenes):
        label = f"Тема {topic.get('id')}, сцена {i + 1}"
        if not isinstance(scene, dict):
            raise ValueError(f"{label}: требуется объект")
        start = number(scene.get("start"), label + ".start")
        stop = number(scene.get("end"), label + ".end")
        if abs(start - end) > 1e-6 or stop - start < 1:
            raise ValueError(f"{label}: сцены должны идти подряд от 0, без разрывов/пересечений, минимум 1с")
        kind = scene.get("scene_type")
        if kind not in PRESETS:
            raise ValueError(f"{label}: неизвестный scene_type {kind!r}; доступны {', '.join(PRESETS)}")
        animation = scene.get("animation", {})
        if not isinstance(animation, dict) or animation.get("preset") not in PRESETS[kind]:
            raise ValueError(f"{label}: animation.preset должен быть одним из {sorted(PRESETS[kind])}")
        allowed = {"preset", "rotate_x", "rotate_y", "perspective", "cycles"}
        if set(animation) - allowed:
            raise ValueError(f"{label}: неизвестные animation-параметры {set(animation) - allowed}")
        for key, lo, hi in [("rotate_x", -45, 45), ("rotate_y", -45, 45),
                            ("perspective", 300, 3000), ("cycles", 1, 6)]:
            if key in animation and not lo <= number(animation[key], key) <= hi:
                raise ValueError(f"{label}: {key} должен быть от {lo} до {hi}")
        text = scene.get("voiceover")
        if not isinstance(text, str) or not text.strip() or "..." in text or "…" in text:
            raise ValueError(f"{label}: voiceover должен содержать полную реплику без многоточий")
        if not isinstance(scene.get("screen_text"), str) or not scene["screen_text"].strip():
            raise ValueError(f"{label}: нужен screen_text")
        if kind == "code":
            code = scene.get("code", topic.get("code"))
            if not isinstance(code, str) or not code.strip():
                raise ValueError(f"{label}: нужен непустой текст code")
        if 'points' in scene and (not isinstance(scene['points'], list) or
                not scene['points'] or not all(isinstance(p, str) and p.strip() for p in scene['points'])):
            raise ValueError(f"{label}: points — непустой список строк")
        tr = scene.setdefault("transition_out", {"type": "crossfade", "duration": 0.5})
        if not isinstance(tr, dict) or tr.get("type") not in TRANSITIONS:
            raise ValueError(f"{label}: неизвестный transition_out.type")
        duration = number(tr.get("duration", 0), label + ".transition.duration")
        if duration < 0 or duration > min(1.5, (stop - start) / 2):
            raise ValueError(f"{label}: слишком длинный переход")
        tr["duration"] = duration
        scene["start"], scene["end"] = start, stop
        end = stop
    outro_duration = number(outro_duration, "outro_duration")
    if outro_duration <= 0:
        raise ValueError("outro_duration должен быть положительным")
    board["outro_start"] = end
    board["duration"] = end + outro_duration
    if max_duration is not None:
        number(max_duration, "max-duration")
    if max_duration and max_duration > 0 and board["duration"] > max_duration + 1e-6:
        raise ValueError(f"Сценарий с заставкой: {board['duration']:.2f}с, больше --max-duration {max_duration}. "
                         "Исправьте тайминг или задайте --max-duration 0; сценарий не сжимается.")
    return board


def voice_cache_key(text, voice, rate):
    return hashlib.sha256(json.dumps([text, voice, rate, "WordBoundary"], ensure_ascii=False).encode()).hexdigest()[:24]


def fit_voice(duration, slot):
    """Reserve lead/tail room; never exceed a modest 1.12x post-TTS adjustment."""
    available = slot - 0.3
    if available <= 0:
        raise ValueError("Недостаточно времени для озвучки")
    speed = max(1.0, duration / available)
    if speed > 1.12:
        raise ValueError(f"Текст озвучки ({duration:.2f}с) не помещается в сцену {slot:.2f}с. "
                         "Сократите реплику или увеличьте end; речь не будет обрезана.")
    return speed
