import unittest

from core.cinematic_scene_registry import (
    registered_scene_kinds,
    register_scene,
    render_scene,
)
from core.cinematic_storyboard import Shot


class CinematicSceneRegistryTest(unittest.TestCase):
    def test_registry_dispatches_scene_by_kind(self):
        calls = []
        register_scene(
            "unit_scene",
            lambda draw, shot, progress: calls.append((shot.id, progress)),
            replace=True,
        )
        shot = Shot("sample", "unit_scene", 0.0, 1.0, 0, 1)
        render_scene("unit_scene", object(), shot, 0.25)
        self.assertEqual(calls, [("sample", 0.25)])
        self.assertIn("unit_scene", registered_scene_kinds())

    def test_unknown_scene_has_actionable_error(self):
        shot = Shot("sample", "missing", 0.0, 1.0, 0, 1)
        with self.assertRaisesRegex(ValueError, "unknown cinematic scene kind: missing"):
            render_scene("missing", object(), shot, 0.5)

    def test_duplicate_registration_is_rejected(self):
        register_scene("duplicate", lambda draw, shot, progress: None, replace=True)
        with self.assertRaisesRegex(ValueError, "already registered: duplicate"):
            register_scene("duplicate", lambda draw, shot, progress: None)


if __name__ == "__main__":
    unittest.main()
