from __future__ import annotations

import json
from pathlib import Path

from core.cinematic_storyboard import CinematicStoryboard, Shot


ROOT = Path(__file__).resolve().parents[1]


def topic_voiceover(topic_id: int) -> str:
    data = json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))
    return next(item["voiceover"] for item in data["topics"] if item["id"] == topic_id)


def board(topic_id: int, specs: tuple[tuple, ...]) -> CinematicStoryboard:
    shots = tuple(
        Shot(
            id=spec[0],
            kind=spec[1],
            start=spec[2],
            end=spec[3],
            narration_start=spec[4],
            narration_end=spec[5],
            accent_words=tuple(spec[6]),
            camera=spec[7],
            scene_data=spec[8],
        )
        for spec in specs
    )
    return CinematicStoryboard(topic_id, topic_voiceover(topic_id), shots)
