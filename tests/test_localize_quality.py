import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import localize_video


class LocalizeQualityTest(unittest.TestCase):
    def test_transcribe_can_force_english_or_auto_detect_language(self):
        calls = []

        class FakeModel:
            def transcribe(self, audio_path, **kwargs):
                calls.append((audio_path, kwargs))
                return {"text": "тест", "segments": []}

        fake_whisper = SimpleNamespace(load_model=lambda model_name: FakeModel())

        with patch.dict("sys.modules", {"whisper": fake_whisper}):
            localize_video.transcribe(Path("/tmp/audio.wav"), "tiny", Path("/tmp/transcript-en.json"))
            localize_video.transcribe(Path("/tmp/audio.wav"), "tiny", Path("/tmp/transcript-auto.json"), language=None)

        self.assertEqual(calls[0][1]["language"], "en")
        self.assertNotIn("language", calls[1][1])

    def test_translation_prompt_targets_voiceover_quality(self):
        prompt = localize_video.build_deepseek_translation_prompt(
            [
                {"text": "This chart screams 400%, it's four.", "duration": 2.4},
                {"text": "The axis never started at zero.", "duration": 1.7},
            ]
        )

        self.assertIn("voice-over", prompt)
        self.assertIn("natural spoken Russian", prompt)
        self.assertIn("same JSON array length", prompt)
        self.assertIn("concise enough to fit", prompt)
        self.assertIn("target 2.4s", prompt)
        self.assertIn("max", prompt)

    def test_natural_timing_limits_speed_changes(self):
        # 3 seconds of generated speech should not be crushed into a 1 second source slot.
        self.assertAlmostEqual(localize_video.natural_timing_target(3.0, 1.0), 3.0 / 1.18, places=3)
        # Very short generated speech should not be stretched too far either.
        self.assertAlmostEqual(localize_video.natural_timing_target(1.0, 3.0), 1.0 / 0.88, places=3)
        self.assertEqual(localize_video.natural_timing_target(2.0, 2.1), 2.1)

    def test_scheduled_segments_do_not_overlap(self):
        scheduled = localize_video.schedule_segment_paths(
            [
                ("/tmp/a.wav", 0, 2500),
                ("/tmp/b.wav", 1000, 1500),
                ("/tmp/c.wav", 2600, 1000),
            ],
            min_gap_ms=120,
        )

        self.assertEqual(scheduled[0], ("/tmp/a.wav", 0))
        self.assertEqual(scheduled[1], ("/tmp/b.wav", 2620))
        self.assertEqual(scheduled[2], ("/tmp/c.wav", 4240))

    def test_short_transcript_segments_are_merged_for_natural_voiceover(self):
        merged = localize_video.merge_transcript_segments_for_voiceover(
            [
                {"id": 1, "start": 0.0, "end": 1.4, "text": "This chart screams 400%."},
                {"id": 2, "start": 1.55, "end": 2.4, "text": "It is four."},
                {"id": 3, "start": 4.0, "end": 5.0, "text": "The axis never started at zero."},
            ]
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["start"], 0.0)
        self.assertEqual(merged[0]["end"], 2.4)
        self.assertEqual(merged[0]["text"], "This chart screams 400%. It is four.")
        self.assertEqual(merged[1]["text"], "The axis never started at zero.")

    def test_voiceover_merge_keeps_long_chunks_separate(self):
        merged = localize_video.merge_transcript_segments_for_voiceover(
            [
                {"id": 1, "start": 0.0, "end": 4.8, "text": "A long idea already fills this chunk."},
                {"id": 2, "start": 4.95, "end": 6.2, "text": "Next idea should not be forced into it."},
            ],
            max_chunk_duration=5.0,
        )

        self.assertEqual(len(merged), 2)
