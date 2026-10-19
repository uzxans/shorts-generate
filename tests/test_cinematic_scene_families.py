import unittest

import numpy as np

from core.cinematic_scenes import CinematicSceneRenderer
from core.cinematic_storyboard import Shot


CASES = {
    "problem_ui": {"title": "Проблема", "detail": "лишний запрос"},
    "process_chain": {"nodes": ("render", "effect", "fetch")},
    "code_build": {"lines": ("const data = use(promise);", "return data;")},
    "before_after": {"before": "waterfall", "after": "parallel"},
    "data_flow": {"nodes": ("server", "Promise", "Suspense")},
    "timeline": {"events": ("t1", "t2", "t3")},
    "index_tree": {"mode": "v7", "keys": ("019a…", "019b…")},
    "browser_navigation": {"url": "/profile", "states": ("navigate", "intercept", "render")},
    "config_diff": {"before": "types: []", "after": 'types: ["node"]'},
    "css_state_transition": {"from": "opacity: 0", "to": "opacity: 1"},
    "warning": {"title": "Важно", "detail": "одна граница"},
    "resolution": {"title": "Готово", "detail": "результат понятен"},
}


class CinematicSceneFamiliesTest(unittest.TestCase):
    def setUp(self):
        self.renderer = CinematicSceneRenderer(seed=61)

    def test_every_scene_family_changes_visibly_over_time(self):
        for kind, data in CASES.items():
            with self.subTest(kind=kind):
                shot = Shot("sample", kind, 0.0, 1.0, 0, 1, scene_data=data)
                early = self.renderer.render(shot, 0.1)
                late = self.renderer.render(shot, 0.9)
                self.assertEqual(early.shape, (1920, 1080, 3))
                difference = np.abs(early.astype(int) - late.astype(int)).mean()
                self.assertGreater(difference, 1.0)

    def test_index_tree_requires_keys(self):
        shot = Shot("bad", "index_tree", 0.0, 1.0, 0, 1, scene_data={"mode": "v7"})
        with self.assertRaisesRegex(ValueError, "index_tree requires scene_data.keys"):
            self.renderer.render(shot, 0.5)


if __name__ == "__main__":
    unittest.main()
