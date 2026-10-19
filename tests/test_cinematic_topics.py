import unittest

from core.cinematic_storyboard import CinematicStoryboard, Shot
from core.cinematic_topics import get_storyboard, supported_topic_ids, validate_storyboard


class CinematicTopicsTest(unittest.TestCase):
    def test_registry_keeps_pilot_and_lists_batch(self):
        self.assertEqual(supported_topic_ids(), (60, 61, 62, 63, 64, 65))
        self.assertEqual(get_storyboard(60).topic_id, 60)

    def test_registry_rejects_unknown_topic(self):
        with self.assertRaisesRegex(ValueError, "unsupported cinematic topic: 999"):
            get_storyboard(999)

    def test_validation_rejects_gap_between_shots(self):
        board = CinematicStoryboard(
            99,
            "One. Two.",
            (
                Shot("one", "conflict", 0.0, 1.0, 0, 1),
                Shot("two", "chaos", 1.5, 2.0, 1, 2),
            ),
        )
        with self.assertRaisesRegex(ValueError, "gap or overlap"):
            validate_storyboard(board)

    def test_validation_rejects_unknown_scene_kind(self):
        board = CinematicStoryboard(
            99,
            "One.",
            (Shot("one", "missing", 0.0, 1.0, 0, 1),),
        )
        with self.assertRaisesRegex(ValueError, "unknown scene kind: missing"):
            validate_storyboard(board)

    def test_batch_storyboards_cover_required_explanation_roles(self):
        required = {"problem", "cause", "mechanism", "result", "limitation"}
        for topic_id in range(61, 66):
            with self.subTest(topic=topic_id):
                board = get_storyboard(topic_id)
                roles = {shot.scene_data.get("role") for shot in board.shots}
                self.assertTrue(required.issubset(roles))
                self.assertTrue(all(shot.frog_reaction is None for shot in board.shots))
                self.assertGreaterEqual(len({shot.kind for shot in board.shots}), 3)

    def test_batch_storyboards_cover_narration_without_gaps(self):
        for topic_id in range(61, 66):
            with self.subTest(topic=topic_id):
                board = get_storyboard(topic_id)
                cursor = 0
                for shot in board.shots:
                    self.assertEqual(shot.narration_start, cursor)
                    cursor = shot.narration_end
                self.assertIn(cursor, (7, 8, 9))

    def test_each_topic_uses_its_explanatory_metaphor(self):
        expected = {
            61: {"process_chain", "data_flow"},
            62: {"index_tree", "timeline"},
            63: {"browser_navigation"},
            64: {"config_diff"},
            65: {"css_state_transition"},
        }
        for topic_id, kinds in expected.items():
            with self.subTest(topic=topic_id):
                actual = {shot.kind for shot in get_storyboard(topic_id).shots}
                self.assertTrue(kinds.issubset(actual))


if __name__ == "__main__":
    unittest.main()
