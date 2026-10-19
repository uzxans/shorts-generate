import unittest

from core.cinematic_storyboard import (
    APPROVED_TOPIC_60_VOICEOVER,
    Shot,
    retime_storyboard,
    topic_60_storyboard,
)


class CinematicStoryboardTest(unittest.TestCase):
    def test_shot_carries_scene_specific_data(self):
        shot = Shot(
            "x",
            "process_chain",
            0,
            1,
            0,
            1,
            scene_data={"nodes": ("render", "fetch")},
        )
        self.assertEqual(shot.scene_data["nodes"], ("render", "fetch"))

    def test_topic_60_has_seven_ordered_shots(self):
        board = topic_60_storyboard()
        self.assertEqual(len(board.shots), 7)
        self.assertEqual(board.shots[0].kind, "conflict")
        self.assertEqual(board.shots[-1].kind, "cleanup_cta")
        self.assertTrue(all(a.end <= b.start for a, b in zip(board.shots, board.shots[1:])))
        self.assertEqual(board.voiceover, APPROVED_TOPIC_60_VOICEOVER)

    def test_topic_60_has_no_inline_frog_reactions(self):
        board = topic_60_storyboard()
        self.assertTrue(all(shot.frog_reaction is None for shot in board.shots))

    def test_retime_uses_audio_end_and_reserves_cta(self):
        board = topic_60_storyboard()
        meta = {
            "sentences": [
                {"offset": 0.0, "duration": 3.0, "text": "a"},
                {"offset": 3.0, "duration": 2.0, "text": "b"},
                {"offset": 5.0, "duration": 5.0, "text": "c"},
                {"offset": 10.0, "duration": 3.0, "text": "d"},
                {"offset": 13.0, "duration": 2.0, "text": "e"},
                {"offset": 15.0, "duration": 6.0, "text": "f"},
                {"offset": 21.0, "duration": 4.0, "text": "g"},
                {"offset": 25.0, "duration": 3.0, "text": "h"},
                {"offset": 28.0, "duration": 2.0, "text": "i"},
                {"offset": 30.0, "duration": 2.0, "text": "j"},
            ]
        }
        timed = retime_storyboard(board, meta, cta_duration=4.0)
        self.assertAlmostEqual(timed.shots[-1].end, 36.0)
        self.assertTrue(all(shot.duration > 0 for shot in timed.shots))
        self.assertTrue(all(a.end <= b.start for a, b in zip(timed.shots, timed.shots[1:])))

    def test_retime_rejects_audio_outside_pilot_range(self):
        board = topic_60_storyboard()
        meta = {"sentences": [{"offset": 0.0, "duration": 50.0, "text": "too long"}]}
        with self.assertRaisesRegex(ValueError, "35-45"):
            retime_storyboard(board, meta, cta_duration=4.0)
