import ast
import json
import unittest
from pathlib import Path

from core.cinematic_storyboard import APPROVED_TOPIC_60_VOICEOVER


class CinematicRenderTest(unittest.TestCase):
    def test_topic_60_uses_approved_voiceover(self):
        data = json.loads(Path("topics.json").read_text(encoding="utf-8"))
        topic = next(item for item in data["topics"] if item["id"] == 60)
        self.assertEqual(topic["voiceover"], APPROVED_TOPIC_60_VOICEOVER)


class CinematicCliTest(unittest.TestCase):
    def test_cli_accepts_supported_batch_topics(self):
        from render_cinematic import parse_args

        self.assertEqual(parse_args(["--topic", "60", "--skip-voice"]).topic, 60)
        self.assertEqual(parse_args(["--topic", "65", "--skip-voice"]).topic, 65)
        with self.assertRaises(SystemExit):
            parse_args(["--topic", "59"])

    def test_paths_are_topic_specific_and_keep_pilot_name(self):
        from render_cinematic import artifact_paths

        paths = artifact_paths(61, "react-use-suspense")
        self.assertEqual(paths.video.name, "61_react-use-suspense-cinematic.mp4")
        self.assertEqual(paths.voice.name, "61_cinematic_voice.mp3")
        self.assertEqual(
            paths.contact_sheet.name,
            "61_react-use-suspense-cinematic-contact-sheet.jpg",
        )
        self.assertEqual(artifact_paths(60, "ignored").video.name, "60_git-worktree-cinematic.mp4")

    def test_export_reuses_high_quality_settings(self):
        module = ast.parse(Path("render_cinematic.py").read_text(encoding="utf-8"))
        source = ast.unparse(module)
        self.assertIn("FINAL_VIDEO_BITRATE", source)
        self.assertIn("FINAL_AUDIO_BITRATE", source)
        self.assertIn("FINAL_FFMPEG_PARAMS", source)
        self.assertNotIn("render_frog_reaction", source)

    def test_short_silent_preview_renders(self):
        from render_cinematic import build_cinematic_clip

        clip = build_cinematic_clip(skip_voice=True, duration=1.0, size=(270, 480), fps=10)
        frame = clip.get_frame(0.5)
        self.assertEqual(frame.shape, (480, 270, 3))
        clip.close()

    def test_batch_topic_short_silent_preview_changes(self):
        import numpy as np

        from render_cinematic import build_cinematic_clip

        clip = build_cinematic_clip(
            topic_id=61,
            skip_voice=True,
            duration=1.0,
            size=(216, 384),
            fps=6,
        )
        early = clip.get_frame(0.1)
        late = clip.get_frame(0.9)
        self.assertEqual(early.shape, (384, 216, 3))
        self.assertGreater(np.abs(early.astype(int) - late.astype(int)).mean(), 0.2)
        clip.close()

    def test_voice_cache_matches_topic_and_exact_copy(self):
        from core.cinematic_topics import get_storyboard
        from render_cinematic import voice_cache_matches

        board = get_storyboard(61)
        self.assertTrue(
            voice_cache_matches(
                {"topic_id": 61, "voiceover": board.voiceover},
                board,
            )
        )
        self.assertFalse(
            voice_cache_matches(
                {"topic_id": 62, "voiceover": board.voiceover},
                board,
            )
        )

    def test_invalid_optional_sfx_is_ignored(self):
        from render_cinematic import mix_cinematic_audio

        audio = mix_cinematic_audio(None, 1.0, no_music=True, no_sfx=False)
        self.assertIsNone(audio)

    def test_voice_cache_is_rejected_when_too_long_for_cta(self):
        from render_cinematic import voice_fits_pilot_range

        meta = {"sentences": [{"offset": 0.0, "duration": 49.0, "text": "slow"}]}
        self.assertFalse(voice_fits_pilot_range(meta, cta_duration=4.0))

    def test_long_new_voice_retries_once_with_bounded_faster_rate(self):
        from render_cinematic import retry_rate_for_voice

        too_long = {"sentences": [{"offset": 0.0, "duration": 42.7, "text": "slow"}]}
        in_range = {"sentences": [{"offset": 0.0, "duration": 39.8, "text": "ok"}]}
        self.assertEqual(retry_rate_for_voice(too_long, cta_duration=4.041667), "+32%")
        self.assertIsNone(retry_rate_for_voice(in_range, cta_duration=4.041667))
