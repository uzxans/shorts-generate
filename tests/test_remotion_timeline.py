import unittest

from tools.remotion_board import to_remotion_captions, validate_remotion_timeline


class RemotionTimelineTests(unittest.TestCase):
    def test_word_cue_converts_to_caption_milliseconds(self):
        result = to_remotion_captions([{"start": 1.25, "end": 1.8, "words": [{"text": "Слой", "start": 1.25, "end": 1.8}]}])
        self.assertEqual(result, [{"text": "Слой", "startMs": 1250, "endMs": 1800, "timestampMs": 1250, "confidence": 1}])

    def test_caption_outside_board_is_rejected(self):
        board = {"duration": 5, "script_timeline": [{"start": 0, "end": 5}]}
        with self.assertRaises(ValueError):
            validate_remotion_timeline(board, [{"start": 4.5, "end": 5.5, "words": []}])


if __name__ == "__main__":
    unittest.main()
