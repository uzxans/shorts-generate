import unittest

import numpy as np

from core.cinematic_camera import camera_transform, composite_rgba, ease_in_out


class CinematicCameraTest(unittest.TestCase):
    def test_easing_has_stable_endpoints(self):
        self.assertEqual(ease_in_out(0.0), 0.0)
        self.assertEqual(ease_in_out(1.0), 1.0)
        self.assertAlmostEqual(ease_in_out(0.5), 0.5)

    def test_camera_transform_preserves_frame_shape(self):
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
        out = camera_transform(frame, 0.5, 1.0, 1.08, (540, 960), (600, 900))
        self.assertEqual(out.shape, frame.shape)

    def test_rgba_composite_clips_at_edges(self):
        base = np.zeros((100, 100, 3), dtype=np.uint8)
        overlay = np.full((40, 40, 4), 255, dtype=np.uint8)
        out = composite_rgba(base, overlay, 80, 80)
        self.assertEqual(out.shape, base.shape)
        self.assertTrue(out[99, 99].all())
