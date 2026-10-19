import unittest

from core.cinematic_subtitles import active_caption, build_caption_cues, render_caption


class CinematicSubtitleTest(unittest.TestCase):
    def setUp(self):
        self.text = "Срочный hotfix прилетел. Не прячь всё в stash."
        self.meta = {
            "words": [
                {"offset": 0.0, "duration": 0.4, "text": "Срочный"},
                {"offset": 0.4, "duration": 0.5, "text": "hotfix"},
                {"offset": 0.9, "duration": 0.6, "text": "прилетел"},
                {"offset": 1.7, "duration": 0.3, "text": "Не"},
                {"offset": 2.0, "duration": 0.5, "text": "прячь"},
                {"offset": 2.5, "duration": 0.3, "text": "всё"},
                {"offset": 2.8, "duration": 0.5, "text": "в"},
                {"offset": 3.3, "duration": 0.5, "text": "stash"},
            ]
        }

    def test_cues_use_two_to_five_words(self):
        cues = build_caption_cues(self.text, self.meta, 4.0)
        self.assertTrue(all(2 <= len(cue.words) <= 5 for cue in cues))
        self.assertEqual(
            " ".join(w.text for cue in cues for w in cue.words),
            "Срочный hotfix прилетел Не прячь всё в stash",
        )

    def test_active_word_follows_audio_time(self):
        cues = build_caption_cues(self.text, self.meta, 4.0)
        cue = active_caption(cues, 0.6)
        self.assertIsNotNone(cue)
        self.assertEqual(cue.active_word_at(0.6).text, "hotfix")

    def test_rendered_caption_stays_inside_safe_zone(self):
        cue = build_caption_cues(self.text, self.meta, 4.0)[0]
        rgba, (x, y) = render_caption(cue, 0.6, (1080, 1920))
        self.assertGreaterEqual(x, 64)
        self.assertGreaterEqual(y, 1450)
        self.assertLessEqual(x + rgba.shape[1], 920)
        self.assertLessEqual(y + rgba.shape[0], 1660)
