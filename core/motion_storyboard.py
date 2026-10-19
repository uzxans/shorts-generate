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
