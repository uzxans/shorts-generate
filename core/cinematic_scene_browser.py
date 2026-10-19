from __future__ import annotations

from core.cinematic_primitives import GOLD, GREEN, RED, panel, pill, progress_reveal, require
from core.cinematic_scene_registry import register_scene


def render_browser_navigation(context, shot, progress):
    renderer, draw = context
    states = tuple(require(shot.scene_data, shot.kind, "states"))
    url = str(require(shot.scene_data, shot.kind, "url"))
    panel(draw, (90, 280, 950, 1190), "Browser", renderer.label_font)
    pill(draw, (145, 390, 895, 475), url, renderer.mono, "#2A2924")
    visible = max(1, min(len(states), int(progress * len(states)) + 1))
    for index, state in enumerate(states):
        fill = GREEN if index < visible else "#2A2924"
        pill(draw, (150, 560 + index * 145, 890, 660 + index * 145), str(state), renderer.label_font, fill)
    if progress > 0.55 and len(states) > 1:
        draw.line((170, 595, 870, 625), fill=RED, width=7)
        draw.text((650, 675), "abort", font=renderer.label_font, fill=GOLD)
    progress_reveal(draw, progress)


register_scene("browser_navigation", render_browser_navigation, replace=True)
