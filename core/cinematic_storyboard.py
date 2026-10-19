from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping


APPROVED_TOPIC_60_VOICEOVER = (
    "Ты делаешь feature, и в папке уже изменены десять файлов. "
    "В этот момент прилетает срочный hotfix. "
    "Через stash и switch ты прячешь изменения и теряешь контекст. "
    "git worktree решает иначе: создаёт рядом вторую рабочую папку из того же репозитория. "
    "Команда: git worktree add ../app-hotfix -b hotfix/login. "
    "Слева остаётся грязная feature. Справа появляется чистая ветка hotfix. "
    "История и Git-объекты общие, поэтому это не второй clone. "
    "Открываешь два терминала: feature не трогаешь, hotfix исправляешь отдельно. "
    "Важно: одну ветку нельзя открыть в двух worktree. "
    "После merge убери папку: git worktree remove ../app-hotfix."
)


@dataclass(frozen=True)
class Shot:
    id: str
    kind: str
    start: float
    end: float
    narration_start: int
    narration_end: int
    accent_words: tuple[str, ...] = ()
    camera: str = "push_in"
    sfx: str | None = None
    frog_reaction: str | None = None
    frog_start: float | None = None
    frog_end: float | None = None
    scene_data: Mapping[str, object] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class CinematicStoryboard:
    topic_id: int
    voiceover: str
    shots: tuple[Shot, ...]

    @property
    def duration(self) -> float:
        return self.shots[-1].end if self.shots else 0.0


def topic_60_storyboard() -> CinematicStoryboard:
    specs = (
        ("conflict", "conflict", 0.0, 3.0, 0, 1, ("hotfix",), "snap_focus", "alert", None),
        ("chaos", "chaos", 3.0, 8.0, 1, 3, ("stash",), "handheld", "whoosh", None),
        ("command", "terminal_command", 8.0, 14.0, 3, 5, ("worktree",), "push_in", "keys", None),
        ("split", "split_worktrees", 14.0, 24.0, 5, 6, ("feature", "hotfix"), "pan", "success", None),
        ("history", "shared_history", 24.0, 31.0, 6, 8, ("общие",), "orbit", "whoosh", None),
        ("warning", "branch_warning", 31.0, 37.0, 8, 9, ("нельзя",), "snap_focus", "warning", None),
        ("cleanup", "cleanup_cta", 37.0, 45.0, 9, 10, ("merge",), "pull_back", "bell", None),
    )
    shots = tuple(Shot(*spec) for spec in specs)
    return CinematicStoryboard(60, APPROVED_TOPIC_60_VOICEOVER, shots)


def retime_storyboard(
    storyboard: CinematicStoryboard,
    tts_meta: dict,
    cta_duration: float,
) -> CinematicStoryboard:
    sentences = tuple(tts_meta.get("sentences") or ())
    if not sentences:
        raise ValueError("TTS sentence metadata is required for cinematic retiming")

    audio_end = max(float(item["offset"]) + float(item["duration"]) for item in sentences)
    total = audio_end + float(cta_duration)
    if total < 35.0 or total > 45.0:
        raise ValueError("cinematic pilot duration must stay within 35-45 seconds")

    timed_shots: list[Shot] = []
    for index, shot in enumerate(storyboard.shots):
        if index == len(storyboard.shots) - 1:
            start = _sentence_offset(sentences, shot.narration_start, audio_end)
            end = total
        else:
            start = _sentence_offset(sentences, shot.narration_start, audio_end)
            end = _sentence_offset(sentences, shot.narration_end, audio_end)

        if end <= start:
            raise ValueError(f"shot {shot.id} has non-positive duration after retiming")

        frog_start = None
        frog_end = None
        if shot.frog_reaction:
            reaction_duration = min(0.8, max(0.4, (end - start) * 0.16))
            center = start + (end - start) * 0.82
            frog_start = max(start, center - reaction_duration / 2)
            frog_end = min(end, frog_start + reaction_duration)
            frog_start = max(start, frog_end - reaction_duration)

        timed_shots.append(
            replace(
                shot,
                start=round(start, 3),
                end=round(end, 3),
                frog_start=None if frog_start is None else round(frog_start, 3),
                frog_end=None if frog_end is None else round(frog_end, 3),
            )
        )

    return replace(storyboard, shots=tuple(timed_shots))


def _sentence_offset(sentences: tuple[dict, ...], index: int, fallback_end: float) -> float:
    if index <= 0:
        return float(sentences[0]["offset"])
    if index < len(sentences):
        return float(sentences[index]["offset"])
    return fallback_end
