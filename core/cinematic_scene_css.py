from __future__ import annotations

from core.cinematic_primitives import GOLD, GREEN, panel, pill, progress_reveal, require
from core.cinematic_scene_registry import register_scene


def render_css_state_transition(context, shot, progress):
    renderer, draw = context
    start = str(require(shot.scene_data, shot.kind, "from"))
    end = str(require(shot.scene_data, shot.kind, "to"))
    panel(draw, (100, 300, 940, 1170), "CSS state transition", renderer.label_font)
    pill(draw, (150, 470, 465, 600), start, renderer.mono, "#2A2924")
    x = 500 + int(210 * progress)
    opacity_fill = int(70 + 185 * progress)
    draw.rounded_rectangle((x, 690, x + 210, 870), radius=28, fill=(62, 123, 78, opacity_fill), outline=GREEN, width=5)
    if progress > 0.5:
        pill(draw, (580, 470, 895, 600), end, renderer.mono, GREEN)
        draw.text((235, 990), "@starting-style → transition", font=renderer.ui_font, fill=GOLD)
    progress_reveal(draw, progress)


register_scene("css_state_transition", render_css_state_transition, replace=True)
