import unittest

import numpy as np

from core.cinematic_scenes import CinematicSceneRenderer
from core.cinematic_storyboard import topic_60_storyboard


class CinematicSceneRendererTest(unittest.TestCase):
    def setUp(self):
        self.renderer = CinematicSceneRenderer(seed=60)
        self.board = topic_60_storyboard()

    def test_every_scene_returns_full_rgb_frame(self):
        for shot in self.board.shots:
            frame = self.renderer.render(shot, (shot.start + shot.end) / 2)
            self.assertEqual(frame.shape, (1920, 1080, 3))
            self.assertEqual(frame.dtype, np.uint8)

    def test_scene_rendering_is_deterministic(self):
        shot = self.board.shots[2]
        a = self.renderer.render(shot, shot.start + 1.0)
        b = self.renderer.render(shot, shot.start + 1.0)
        self.assertTrue(np.array_equal(a, b))

    def test_explainer_scenes_visibly_change_over_time(self):
        for shot in (self.board.shots[2], self.board.shots[3], self.board.shots[4]):
            early = self.renderer.render(shot, shot.start + shot.duration * 0.15)
            late = self.renderer.render(shot, shot.start + shot.duration * 0.85)
            self.assertGreater(np.abs(early.astype(int) - late.astype(int)).mean(), 4.0)

    def test_primary_content_stays_inside_safe_zone(self):
        for shot in self.board.shots[:-1]:
            x0, y0, x1, y1 = self.renderer.content_bounds(shot)
            self.assertGreaterEqual(x0, 64)
            self.assertGreaterEqual(y0, 120)
            self.assertLessEqual(x1, 920)
            self.assertLessEqual(y1, 1400)

    def test_scenes_expose_explanation_markers(self):
        markers = {shot.kind: self.renderer.explanation_markers(shot) for shot in self.board.shots}
        self.assertIn("feature не трогаем", markers["split_worktrees"])
        self.assertIn("hotfix отдельно", markers["split_worktrees"])
        self.assertIn("один .git", markers["shared_history"])
        self.assertIn("не второй clone", markers["shared_history"])
        self.assertIn("remove после merge", markers["cleanup_cta"])
