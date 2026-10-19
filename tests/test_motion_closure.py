import unittest

import numpy as np

from core.motion_closure import render_closure_frame
from core.motion_closure import _fit_font_size, _font, ROBOTO, W
from PIL import Image, ImageDraw


class MotionClosureTest(unittest.TestCase):
    def test_render_closure_frame_returns_vertical_rgb_frame(self):
        frame = render_closure_frame(16.0)

        self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(frame.shape, (1920, 1080, 3))
        self.assertEqual(frame.dtype, np.uint8)
        self.assertGreater(frame.mean(), 5)

    def test_headline_font_size_fits_vertical_canvas(self):
        image = Image.new("RGB", (W, 1920))
        draw = ImageDraw.Draw(image)
        text = "Каждый вызов создает свою память."

        size = _fit_font_size(draw, ROBOTO, text, 58, W - 96)
        bbox = draw.textbbox((0, 0), text, font=_font(ROBOTO, size))

        self.assertLessEqual(bbox[2] - bbox[0], W - 96)

    def test_code_scene_contains_code_panel_pixels(self):
        frame = render_closure_frame(31.0)

        code_region = frame[880:1360, 120:960, :]
        green_pixels = (
            (code_region[:, :, 1] > 150)
            & (code_region[:, :, 0] < 120)
            & (code_region[:, :, 2] < 180)
        )

        self.assertGreater(int(green_pixels.sum()), 500)


if __name__ == "__main__":
    unittest.main()
