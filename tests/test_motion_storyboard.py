import unittest

from core.motion_storyboard import closure_storyboard, storyboard_duration


class MotionStoryboardTest(unittest.TestCase):
    def test_closure_storyboard_is_calm_and_reference_like(self):
        cues = closure_storyboard()

        self.assertEqual(len(cues), 6)
        self.assertEqual(storyboard_duration(cues), 55.0)
        self.assertEqual(cues[0].headline, "Замыкание — это память функции.")
        self.assertEqual(cues[-1].headline, "Каждый вызов создает свою память.")
        self.assertTrue(all(cue.end > cue.start for cue in cues))
        self.assertTrue(all((cue.end - cue.start) >= 4.0 for cue in cues))


if __name__ == "__main__":
    unittest.main()
