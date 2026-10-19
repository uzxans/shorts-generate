from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.cinematic_storyboard import Shot


SceneRenderer = Callable[[Any, Shot, float], None]
_SCENES: dict[str, SceneRenderer] = {}


def register_scene(kind: str, renderer: SceneRenderer, *, replace: bool = False) -> None:
    if kind in _SCENES and not replace:
        raise ValueError(f"cinematic scene already registered: {kind}")
    _SCENES[kind] = renderer


def render_scene(kind: str, draw: Any, shot: Shot, progress: float) -> None:
    try:
        renderer = _SCENES[kind]
    except KeyError as exc:
        raise ValueError(f"unknown cinematic scene kind: {kind}") from exc
    renderer(draw, shot, progress)


def registered_scene_kinds() -> tuple[str, ...]:
    return tuple(sorted(_SCENES))
