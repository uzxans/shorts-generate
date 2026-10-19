from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core.cinematic_camera import camera_transform
from core.cinematic_scene_registry import register_scene, render_scene
from core.cinematic_storyboard import Shot


W, H = 1080, 1920
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
CONTENT_BOUNDS = (96, 190, 900, 1320)


class CinematicSceneRenderer:
    def __init__(self, seed: int = 60):
        self.seed = seed
        self.ui_font = _font(ASSETS / "Roboto-Bold.ttf", 42)
        self.label_font = _font(ASSETS / "Roboto-Bold.ttf", 30)
        self.mono = _font(ASSETS / "JetBrainsMono-Regular.ttf", 30)
        self.mono_bold = _font(ASSETS / "JetBrainsMono-Bold.ttf", 34)
        self._backdrop = self._build_backdrop()

    def render(self, shot: Shot, t: float) -> np.ndarray:
        image = Image.fromarray(self._backdrop.copy())
        draw = ImageDraw.Draw(image, "RGBA")
        progress = _progress(shot, t)
        render_scene(shot.kind, (self, draw), shot, progress)
        frame = np.array(image, dtype=np.uint8)
        return self._apply_camera(frame, shot, progress)

    def content_bounds(self, shot: Shot) -> tuple[int, int, int, int]:
        return CONTENT_BOUNDS

    def explanation_markers(self, shot: Shot) -> tuple[str, ...]:
        markers = {
            "conflict": ("feature грязная", "hotfix срочно"),
            "chaos": ("stash прячет контекст", "switch ломает поток"),
            "terminal_command": ("команда создаёт папку", "новая ветка hotfix"),
            "split_worktrees": ("feature не трогаем", "hotfix отдельно"),
            "shared_history": ("один .git", "не второй clone"),
            "branch_warning": ("одна ветка один worktree",),
            "cleanup_cta": ("remove после merge",),
        }
        return markers.get(shot.kind, ())

    def _build_backdrop(self) -> np.ndarray:
        base = np.zeros((H, W, 3), dtype=np.uint8)
        base[:, :] = (16, 16, 14)
        yy, xx = np.mgrid[0:H, 0:W]
        glow = np.exp(-(((xx - 760) / 520) ** 2 + ((yy - 340) / 700) ** 2))
        base = np.clip(base + glow[..., None] * np.array([72, 52, 18]), 0, 255)
        rng = np.random.default_rng(self.seed)
        noise = rng.normal(0, 3, base.shape)
        base = np.clip(base + noise, 0, 255)
        dist = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        vignette = np.clip(1.0 - dist * 0.36, 0.58, 1.0)
        base = np.clip(base * vignette[..., None], 0, 255)
        return base.astype(np.uint8)

    def _render_conflict(self, draw: ImageDraw.ImageDraw, p: float) -> None:
        _window(draw, (120, 300, 900, 1220), "app-feature / login.py")
        lines = ["def login(user):", "    token = request_token(user)", "    # TODO: broken feature", "    return token"]
        _code(draw, (160, 410), lines, self.mono)
        _pill(draw, (185, 1010, 565, 1090), "feature грязная", "#A84D42", self.label_font)
        _pill(draw, (250, 210, 840, 300), "СРОЧНЫЙ HOTFIX", "#D8B45B", self.ui_font, text="#18130A")
        if p > 0.55:
            _arrow(draw, (720, 280), (720, 440), "#D8B45B")
            _pill(draw, (180, 1120, 760, 1195), "hotfix нужен, feature не готова", "#A84D42", self.label_font)

    def _render_chaos(self, draw: ImageDraw.ImageDraw, p: float) -> None:
        _window(draw, (135, 350, 880, 1130), "classic flow")
        tokens = ("git stash", "git switch main", "install again", "switch back")
        for i, token in enumerate(tokens):
            dx = int(np.sin(p * 5 + i) * 55)
            dy = int(np.cos(p * 4 + i) * 40)
            x = 190 + (i % 2) * 315 + dx
            y = 460 + (i // 2) * 230 + dy
            _pill(draw, (x, y, x + 270, y + 84), token, "#2A2924", self.label_font)
            if p > 0.35 + i * 0.08:
                _arrow(draw, (x + 135, y + 84), (520, 905), "#655A37")
        _pill(draw, (210, 930, 830, 1025), "много шагов до одного фикса", "#A84D42", self.label_font)

    def _render_terminal_command(self, draw: ImageDraw.ImageDraw, p: float) -> None:
        _terminal(draw, (115, 455, 915, 1040), "one command")
        chunks = ["git worktree add", "../app-hotfix", "-b hotfix/login"]
        shown = max(1, min(3, int(p * 4)))
        command = " ".join(chunks[:shown])
        _code(draw, (160, 590), [f"$ {command}"], self.mono_bold, accent="git worktree")
        _folder_icon(draw, (245, 1120), "app-feature", "#2C6F9E", self.label_font)
        if p > 0.38:
            _arrow(draw, (465, 1175), (590, 1175), "#D8B45B")
            _folder_icon(draw, (610, 1120), "app-hotfix", "#3E7B4E", self.label_font)
        if p > 0.7:
            _code(draw, (160, 720), ["Preparing worktree", "HEAD is now at hotfix/login"], self.mono)
            _pill(draw, (210, 900, 820, 990), "Git создал папку рядом", "#3E7B4E", self.label_font)

    def _render_split_worktrees(self, draw: ImageDraw.ImageDraw, p: float) -> None:
        _folder(draw, (115, 420, 475, 930), "app-feature", "feature/login", "#2C6F9E", self.label_font, self.mono)
        _folder(draw, (555, 420, 915, 930), "app-hotfix", "hotfix/login", "#3E7B4E", self.label_font, self.mono)
        _line(draw, (475, 660), (555, 660), "#655A37", 4)
        _pill(draw, (145, 970, 500, 1055), "feature не трогаем", "#2C6F9E", self.label_font)
        _pill(draw, (535, 970, 900, 1055), "hotfix отдельно", "#3E7B4E", self.label_font)
        _pill(draw, (165, 1130, 860, 1225), "две рабочие папки, один репозиторий", "#D8B45B", self.label_font, text="#18130A")
        if p > 0.55:
            _arrow(draw, (295, 1060), (295, 1130), "#2C6F9E")
            _arrow(draw, (725, 1060), (725, 1130), "#3E7B4E")

    def _render_shared_history(self, draw: ImageDraw.ImageDraw, p: float) -> None:
        _window(draw, (130, 330, 890, 1140), "shared .git objects")
        _folder_icon(draw, (180, 525), "feature", "#2C6F9E", self.label_font)
        _folder_icon(draw, (650, 525), "hotfix", "#3E7B4E", self.label_font)
        _pill(draw, (370, 610, 675, 695), "один .git", "#D8B45B", self.ui_font, text="#18130A")
        _arrow(draw, (360, 625), (430, 655), "#655A37")
        _arrow(draw, (650, 625), (610, 655), "#655A37")
        nodes = [(260, 840), (410, 740), (560, 840), (710, 720)]
        for a, b in zip(nodes, nodes[1:]):
            _line(draw, a, b, "#655A37", 4)
        count = max(1, int(1 + p * len(nodes)))
        for x, y in nodes[:count]:
            draw.ellipse((x - 25, y - 25, x + 25, y + 25), fill="#D8B45B", outline="#FFF2B9", width=3)
        _pill(draw, (205, 1010, 820, 1095), "это не второй тяжёлый clone", "#2A2924", self.label_font)

    def _render_branch_warning(self, draw: ImageDraw.ImageDraw, p: float) -> None:
        _terminal(draw, (115, 430, 915, 1110), "branch guard")
        _code(draw, (160, 560), ["$ git worktree add ../x hotfix/login"], self.mono)
        red = "#C75C4A" if p < 0.6 else "#A84D42"
        _code(draw, (160, 710), ["fatal: 'hotfix/login' is already checked out", "одна ветка - один worktree"], self.mono_bold, accent="fatal")
        _pill(draw, (190, 955, 830, 1040), "одна ветка - один worktree", red, self.label_font)

    def _render_cleanup(self, draw: ImageDraw.ImageDraw, p: float) -> None:
        _terminal(draw, (115, 460, 915, 1060), "cleanup")
        _code(draw, (160, 590), ["$ git worktree remove ../app-hotfix"], self.mono_bold, accent="git worktree")
        _folder_icon(draw, (600, 760), "app-hotfix", "#3E7B4E", self.label_font)
        if p > 0.45:
            _line(draw, (600, 840), (880, 980), "#A84D42", 8)
            _line(draw, (880, 840), (600, 980), "#A84D42", 8)
            _pill(draw, (220, 815, 805, 900), "remove после merge", "#3E7B4E", self.label_font)
        _pill(draw, (185, 1040, 880, 1130), "feature осталась на месте", "#D8B45B", self.label_font, text="#18130A")

    def _apply_camera(self, frame: np.ndarray, shot: Shot, progress: float) -> np.ndarray:
        if shot.camera == "pan":
            return camera_transform(frame, progress, 1.0, 1.04, (540, 960), (585, 940))
        if shot.camera == "pull_back":
            return camera_transform(frame, progress, 1.06, 1.0, (540, 930), (540, 960))
        if shot.camera == "snap_focus":
            return camera_transform(frame, min(1.0, progress * 2.0), 1.0, 1.06, (540, 960), (540, 900))
        return camera_transform(frame, progress, 1.0, 1.05, (540, 960), (560, 930))


_SCENE_METHODS = {
    "conflict": "_render_conflict",
    "chaos": "_render_chaos",
    "terminal_command": "_render_terminal_command",
    "split_worktrees": "_render_split_worktrees",
    "shared_history": "_render_shared_history",
    "branch_warning": "_render_branch_warning",
    "cleanup_cta": "_render_cleanup",
}


def _render_bound_method(context, shot: Shot, progress: float) -> None:
    renderer, draw = context
    method = getattr(renderer, _SCENE_METHODS[shot.kind])
    method(draw, progress)


for _kind in _SCENE_METHODS:
    register_scene(_kind, _render_bound_method, replace=True)


# Imports register reusable scene families without coupling them to the frame facade.
from core import cinematic_scene_browser as _cinematic_scene_browser  # noqa: E402,F401
from core import cinematic_scene_config as _cinematic_scene_config  # noqa: E402,F401
from core import cinematic_scene_css as _cinematic_scene_css  # noqa: E402,F401
from core import cinematic_scene_flow as _cinematic_scene_flow  # noqa: E402,F401
from core import cinematic_scene_index as _cinematic_scene_index  # noqa: E402,F401


def _progress(shot: Shot, t: float) -> float:
    return min(1.0, max(0.0, (t - shot.start) / max(0.001, shot.duration)))


def _font(path: Path, size: int):
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError:
        return ImageFont.load_default()


def _window(draw, box, title):
    draw.rounded_rectangle(box, radius=28, fill="#171713", outline="#3A3527", width=3)
    draw.rounded_rectangle((box[0], box[1], box[2], box[1] + 74), radius=28, fill="#222017")
    draw.text((box[0] + 34, box[1] + 22), title, font=_font(ASSETS / "Roboto-Bold.ttf", 28), fill="#DAD4C7")


def _terminal(draw, box, title):
    _window(draw, box, title)
    for i, color in enumerate(("#C75C4A", "#D8B45B", "#3E7B4E")):
        draw.ellipse((box[0] + 32 + i * 34, box[1] + 26, box[0] + 50 + i * 34, box[1] + 44), fill=color)


def _code(draw, xy, lines, font, accent: str | None = None):
    x, y = xy
    for line in lines:
        fill = "#D8B45B" if accent and accent in line else "#EEE6D8"
        draw.text((x, y), line, font=font, fill=fill)
        y += 54


def _pill(draw, box, label, fill, font, text="#F7F2E8"):
    draw.rounded_rectangle(box, radius=26, fill=fill, outline="#F4E6B5" if fill == "#D8B45B" else None)
    bbox = draw.textbbox((0, 0), label, font=font)
    x = box[0] + ((box[2] - box[0]) - (bbox[2] - bbox[0])) // 2
    y = box[1] + ((box[3] - box[1]) - (bbox[3] - bbox[1])) // 2 - 2
    draw.text((x, y), label, font=font, fill=text)


def _folder(draw, box, name, branch, color, label_font, mono):
    draw.rounded_rectangle(box, radius=26, fill="#171713", outline="#3A3527", width=3)
    draw.rounded_rectangle((box[0] + 34, box[1] - 34, box[0] + 205, box[1] + 38), radius=18, fill="#252219")
    draw.text((box[0] + 34, box[1] + 56), name, font=label_font, fill="#F7F2E8")
    _pill(draw, (box[0] + 34, box[1] + 128, box[2] - 34, box[1] + 205), branch, color, label_font)
    draw.text((box[0] + 42, box[1] + 285), "$ npm test", font=mono, fill="#D8B45B")
    draw.text((box[0] + 42, box[1] + 350), "ready", font=mono, fill="#9CD9A8")


def _line(draw, a, b, color, width):
    draw.line((a[0], a[1], b[0], b[1]), fill=color, width=width)


def _arrow(draw, a, b, color):
    draw.line((a[0], a[1], b[0], b[1]), fill=color, width=6)
    vx = b[0] - a[0]
    vy = b[1] - a[1]
    length = max(1.0, (vx * vx + vy * vy) ** 0.5)
    ux, uy = vx / length, vy / length
    left = (b[0] - ux * 26 - uy * 13, b[1] - uy * 26 + ux * 13)
    right = (b[0] - ux * 26 + uy * 13, b[1] - uy * 26 - ux * 13)
    draw.polygon((b, left, right), fill=color)


def _folder_icon(draw, xy, name, color, font):
    x, y = xy
    draw.rounded_rectangle((x, y + 28, x + 235, y + 145), radius=18, fill="#171713", outline=color, width=4)
    draw.rounded_rectangle((x + 20, y, x + 135, y + 58), radius=14, fill="#252219", outline=color, width=3)
    draw.text((x + 22, y + 70), name, font=font, fill="#F7F2E8")
