from __future__ import annotations

from core.cinematic_primitives import BLUE, GOLD, GREEN, RED, arrow, panel, pill, progress_reveal, require
from core.cinematic_scene_registry import register_scene


def _context(value):
    return value[0], value[1]


def render_problem(context, shot, progress):
    renderer, draw = _context(context)
    title = str(shot.scene_data.get("title", "Проблема"))
    detail = str(shot.scene_data.get("detail", "лишняя работа"))
    panel(draw, (120, 330, 920, 1120), title, renderer.label_font)
    pill(draw, (190, 520, 850, 650), detail, renderer.ui_font, RED)
    if progress > 0.45:
        pill(draw, (250, 790, 790, 900), "пользователь ждёт", renderer.label_font, "#2A2924")
    progress_reveal(draw, progress, RED)


def _sequence(context, shot, progress, key="nodes"):
    renderer, draw = _context(context)
    nodes = tuple(require(shot.scene_data, shot.kind, key))
    panel(draw, (100, 310, 940, 1160), str(shot.scene_data.get("title", "Как это происходит")), renderer.label_font)
    count = len(nodes)
    spacing = 650 // max(1, count - 1)
    active = max(1, min(count, int(progress * count) + 1))
    for index, node in enumerate(nodes):
        x = 170 + index * spacing
        fill = GREEN if index < active else "#2A2924"
        pill(draw, (x - 75, 610, x + 130, 710), str(node), renderer.label_font, fill)
        if index and index < active:
            arrow(draw, (x - spacing + 135, 660), (x - 85, 660))
    progress_reveal(draw, progress)


def render_process_chain(context, shot, progress):
    _sequence(context, shot, progress)


def render_data_flow(context, shot, progress):
    _sequence(context, shot, progress)
    renderer, draw = _context(context)
    x = 180 + int(650 * progress)
    draw.ellipse((x, 820, x + 38, 858), fill=GOLD)


def render_code_build(context, shot, progress):
    renderer, draw = _context(context)
    lines = tuple(require(shot.scene_data, shot.kind, "lines"))
    panel(draw, (100, 300, 940, 1160), str(shot.scene_data.get("title", "Код решения")), renderer.label_font)
    shown = max(1, min(len(lines), int(progress * len(lines)) + 1))
    for index, line in enumerate(lines[:shown]):
        draw.text((150, 460 + index * 74), str(line), font=renderer.mono, fill=GOLD if index == shown - 1 else "#EEE6D8")
    progress_reveal(draw, progress)


def render_before_after(context, shot, progress):
    renderer, draw = _context(context)
    before = str(require(shot.scene_data, shot.kind, "before"))
    after = str(require(shot.scene_data, shot.kind, "after"))
    panel(draw, (100, 320, 940, 1140), "До → после", renderer.label_font)
    pill(draw, (160, 500, 460, 760), before, renderer.label_font, RED)
    arrow(draw, (485, 630), (590, 630), GOLD)
    if progress > 0.32:
        pill(draw, (610, 500, 910, 760), after, renderer.label_font, GREEN)
    progress_reveal(draw, progress)


def render_warning(context, shot, progress):
    renderer, draw = _context(context)
    panel(draw, (120, 350, 920, 1080), str(shot.scene_data.get("title", "Важно")), renderer.label_font)
    pill(draw, (175, 575, 865, 790), str(require(shot.scene_data, shot.kind, "detail")), renderer.label_font, RED)
    if progress > 0.55:
        draw.line((210, 900, 830, 900), fill=GOLD, width=8)
    progress_reveal(draw, progress, RED)


def render_resolution(context, shot, progress):
    renderer, draw = _context(context)
    panel(draw, (120, 350, 920, 1080), str(shot.scene_data.get("title", "Результат")), renderer.label_font)
    radius = 80 + int(progress * 45)
    draw.ellipse((540 - radius, 560 - radius, 540 + radius, 560 + radius), fill=GREEN, outline="#9CD9A8", width=6)
    pill(draw, (190, 800, 890, 930), str(require(shot.scene_data, shot.kind, "detail")), renderer.label_font, "#2A2924")
    progress_reveal(draw, progress, GREEN)


for _kind, _renderer in {
    "problem_ui": render_problem,
    "process_chain": render_process_chain,
    "code_build": render_code_build,
    "before_after": render_before_after,
    "data_flow": render_data_flow,
    "warning": render_warning,
    "resolution": render_resolution,
}.items():
    register_scene(_kind, _renderer, replace=True)
