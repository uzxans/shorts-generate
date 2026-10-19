"""Bridge helpers shared by the Python storyboard builder and Remotion."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def to_remotion_captions(cues):
    result = []
    for cue in cues:
        for word in cue.get("words", []):
            start = round(float(word["start"]) * 1000)
            end = round(float(word["end"]) * 1000)
            result.append({"text": str(word["text"]), "startMs": start, "endMs": end,
                           "timestampMs": start, "confidence": 1})
    return result


def validate_remotion_timeline(board, captions):
    duration = float(board["duration"])
    scenes = board.get("script_timeline", [])
    previous = 0.0
    for scene in scenes:
        start, end = float(scene["start"]), float(scene["end"])
        if start < previous - 1e-6 or end <= start or end > duration + 1e-6:
            raise ValueError(f"invalid scene interval: {start}–{end}")
        previous = end
    for cue in captions:
        start, end = float(cue["start"]), float(cue["end"])
        if start < -1e-6 or end < start or end > duration + 1e-6:
            raise ValueError(f"caption outside board: {start}–{end}")
    return True


def prepare_remotion_project(board, topic, project, skip_voice=False):
    project = Path(project)
    project.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(topic, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    public = project / "public"
    public.mkdir(exist_ok=True)
    payload = dict(board)
    payload["digest"] = digest
    payload["includeAudio"] = not skip_voice
    if (public / "narration.wav").is_file():
        payload["narrationSrc"] = f"scripted/{digest}/narration.wav"
    if (public / "soundtrack.wav").is_file():
        payload["soundtrackSrc"] = f"scripted/{digest}/soundtrack.wav"
    (project / "board.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    props = {"board": payload, "includeAudio": payload["includeAudio"],
             "narrationSrc": payload.get("narrationSrc"), "soundtrackSrc": payload.get("soundtrackSrc")}
    (project / "props.json").write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "remotion-entry.json").write_text(json.dumps({"composition": "ScriptedShort", "digest": digest}, indent=2), encoding="utf-8")
    return project
