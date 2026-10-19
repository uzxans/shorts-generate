from __future__ import annotations

from core.cinematic_primitives import GOLD, GREEN, RED, panel, pill, progress_reveal, require
from core.cinematic_scene_registry import register_scene


def render_config_diff(context, shot, progress):
    renderer, draw = context
    before = str(require(shot.scene_data, shot.kind, "before"))
    after = str(require(shot.scene_data, shot.kind, "after"))
    panel(draw, (100, 300, 940, 1170), "tsconfig.json", renderer.label_font)
    pill(draw, (150, 470, 900, 590), f"− {before}", renderer.mono, RED)
    if progress > 0.32:
        pill(draw, (150, 650, 900, 770), f"+ {after}", renderer.mono, GREEN)
    if progress > 0.68:
        pill(draw, (210, 880, 840, 990), "diagnostic исправлен", renderer.label_font, "#2A2924", GOLD)
    progress_reveal(draw, progress)


register_scene("config_diff", render_config_diff, replace=True)
