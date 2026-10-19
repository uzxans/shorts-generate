from __future__ import annotations

import numpy as np
from PIL import Image


def ease_in_out(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def camera_transform(
    frame: np.ndarray,
    progress: float,
    start_scale: float,
    end_scale: float,
    start_center: tuple[float, float],
    end_center: tuple[float, float],
) -> np.ndarray:
    if frame.ndim != 3:
        raise ValueError("camera_transform expects an RGB or RGBA frame")

    height, width = frame.shape[:2]
    eased = ease_in_out(progress)
    scale = start_scale + (end_scale - start_scale) * eased
    center_x = start_center[0] + (end_center[0] - start_center[0]) * eased
    center_y = start_center[1] + (end_center[1] - start_center[1]) * eased

    scaled_w = max(width, int(round(width * scale)))
    scaled_h = max(height, int(round(height * scale)))
    image = Image.fromarray(frame)
    scaled = image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    crop_x0 = int(round(center_x * scale - width / 2))
    crop_y0 = int(round(center_y * scale - height / 2))
    crop_x0 = min(max(0, crop_x0), scaled_w - width)
    crop_y0 = min(max(0, crop_y0), scaled_h - height)
    cropped = scaled.crop((crop_x0, crop_y0, crop_x0 + width, crop_y0 + height))
    return np.array(cropped, dtype=frame.dtype)


def composite_rgba(base: np.ndarray, overlay: np.ndarray, x: int, y: int) -> np.ndarray:
    if overlay.ndim != 3 or overlay.shape[2] != 4:
        raise ValueError("overlay must be RGBA")
    if base.ndim != 3 or base.shape[2] != 3:
        raise ValueError("base must be RGB")

    result = base.copy()
    base_h, base_w = result.shape[:2]
    over_h, over_w = overlay.shape[:2]

    dst_x0 = max(0, x)
    dst_y0 = max(0, y)
    dst_x1 = min(base_w, x + over_w)
    dst_y1 = min(base_h, y + over_h)
    if dst_x0 >= dst_x1 or dst_y0 >= dst_y1:
        return result

    src_x0 = dst_x0 - x
    src_y0 = dst_y0 - y
    src_x1 = src_x0 + (dst_x1 - dst_x0)
    src_y1 = src_y0 + (dst_y1 - dst_y0)

    source = overlay[src_y0:src_y1, src_x0:src_x1].astype(np.float32)
    target = result[dst_y0:dst_y1, dst_x0:dst_x1].astype(np.float32)
    alpha = source[:, :, 3:4] / 255.0
    blended = source[:, :, :3] * alpha + target * (1.0 - alpha)
    result[dst_y0:dst_y1, dst_x0:dst_x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return result
