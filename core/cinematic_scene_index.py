from __future__ import annotations

from core.cinematic_primitives import GOLD, GREEN, panel, pill, progress_reveal, require
from core.cinematic_scene_registry import register_scene


def render_timeline(context, shot, progress):
    renderer, draw = context
    events = tuple(require(shot.scene_data, shot.kind, "events"))
    panel(draw, (100, 330, 940, 1120), "Порядок во времени", renderer.label_font)
    draw.line((180, 690, 880, 690), fill="#655A37", width=6)
    visible = max(1, min(len(events), int(progress * len(events)) + 1))
    for index, event in enumerate(events[:visible]):
        x = 200 + index * (650 // max(1, len(events) - 1))
        draw.ellipse((x - 24, 666, x + 24, 714), fill=GOLD)
        draw.text((x - 55, 750), str(event), font=renderer.label_font, fill="#F7F2E8")
    progress_reveal(draw, progress)


def render_index_tree(context, shot, progress):
    renderer, draw = context
    keys = tuple(require(shot.scene_data, shot.kind, "keys"))
    mode = str(shot.scene_data.get("mode", "v4"))
    panel(draw, (100, 300, 940, 1180), f"B-tree · UUID{mode[-1]}", renderer.label_font)
    leaves = ((160, 760, 340, 900), (450, 760, 630, 900), (740, 760, 920, 900))
    for box in leaves:
        draw.rounded_rectangle(box, radius=20, fill="#222017", outline="#655A37", width=3)
    visible = max(1, min(len(keys), int(progress * len(keys)) + 1))
    for index, key in enumerate(keys[:visible]):
        leaf = (index % 3) if mode == "v4" else 2
        box = leaves[leaf]
        pill(draw, (box[0] + 10, box[1] + 18 + index * 42, box[2] - 10, box[1] + 58 + index * 42), str(key), renderer.mono, GREEN)
    label = "вставки разбросаны" if mode == "v4" else "новые вставки рядом"
    draw.text((260, 1010), label, font=renderer.ui_font, fill=GOLD)
    progress_reveal(draw, progress)


register_scene("timeline", render_timeline, replace=True)
register_scene("index_tree", render_index_tree, replace=True)
