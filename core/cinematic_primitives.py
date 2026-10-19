from __future__ import annotations

from PIL import ImageDraw


GOLD = "#D8B45B"
CREAM = "#F7F2E8"
MUTED = "#8D877A"
PANEL = "#171713"
RED = "#A84D42"
GREEN = "#3E7B4E"
BLUE = "#2C6F9E"


def panel(draw: ImageDraw.ImageDraw, box, title: str, font) -> None:
    draw.rounded_rectangle(box, radius=28, fill=PANEL, outline="#3A3527", width=3)
    draw.rounded_rectangle((box[0], box[1], box[2], box[1] + 74), radius=28, fill="#222017")
    draw.text((box[0] + 30, box[1] + 20), title, font=font, fill="#DAD4C7")


def centered_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill=CREAM) -> None:
    bounds = draw.textbbox((0, 0), text, font=font)
    x = box[0] + ((box[2] - box[0]) - (bounds[2] - bounds[0])) // 2
    y = box[1] + ((box[3] - box[1]) - (bounds[3] - bounds[1])) // 2
    draw.text((x, y), text, font=font, fill=fill)


def pill(draw: ImageDraw.ImageDraw, box, text: str, font, fill=PANEL, text_fill=CREAM) -> None:
    draw.rounded_rectangle(box, radius=24, fill=fill, outline="#4B4536", width=2)
    centered_text(draw, box, text, font, text_fill)


def arrow(draw: ImageDraw.ImageDraw, start, end, fill=GOLD, width: int = 6) -> None:
    draw.line((*start, *end), fill=fill, width=width)
    x, y = end
    draw.polygon(((x, y), (x - 22, y - 13), (x - 22, y + 13)), fill=fill)


def progress_reveal(draw: ImageDraw.ImageDraw, progress: float, color=GOLD) -> None:
    width = int(820 * max(0.0, min(1.0, progress)))
    draw.rounded_rectangle((130, 1270, 950, 1290), radius=10, fill="#28261F")
    if width:
        draw.rounded_rectangle((130, 1270, 130 + width, 1290), radius=10, fill=color)


def require(data, kind: str, key: str):
    value = data.get(key)
    if value is None or value == () or value == [] or value == "":
        raise ValueError(f"scene {kind} requires scene_data.{key}")
    return value
