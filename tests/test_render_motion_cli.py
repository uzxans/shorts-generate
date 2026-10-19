import unittest
import os
import tempfile
from pathlib import Path

import render_motion


class RenderMotionCliTest(unittest.TestCase):
    def test_parse_args_defaults_to_topic_36_and_allows_skip_voice(self):
        args = render_motion.parse_args(["--skip-voice"])

        self.assertEqual(args.topic, 36)
        self.assertTrue(args.skip_voice)
        self.assertEqual(args.speed, "1.08")
        self.assertEqual(args.music_volume, 0.035)
        self.assertFalse(args.no_music)

    def test_load_env_file_sets_missing_values_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env.local"
            env_path.write_text(
                "YANDEX_API_KEY=file-key\nYANDEX_TTS_VOICE=ermil\n",
                encoding="utf-8",
            )
            old_key = os.environ.get("YANDEX_API_KEY")
            old_voice = os.environ.get("YANDEX_TTS_VOICE")
            try:
                os.environ["YANDEX_API_KEY"] = "existing-key"
                os.environ.pop("YANDEX_TTS_VOICE", None)

                render_motion.load_env_file(env_path)

                self.assertEqual(os.environ["YANDEX_API_KEY"], "existing-key")
                self.assertEqual(os.environ["YANDEX_TTS_VOICE"], "ermil")
            finally:
                if old_key is None:
                    os.environ.pop("YANDEX_API_KEY", None)
                else:
                    os.environ["YANDEX_API_KEY"] = old_key
                if old_voice is None:
                    os.environ.pop("YANDEX_TTS_VOICE", None)
                else:
                    os.environ["YANDEX_TTS_VOICE"] = old_voice

    def test_build_motion_audio_mixes_voice_and_music_by_default(self):
        audio = render_motion.build_motion_audio(
            Path("temp/motion_36_voice.mp3"),
            12.0,
            music_volume=0.10,
            include_music=True,
        )

        self.assertAlmostEqual(audio.duration, 12.0, places=1)

    def test_build_motion_video_can_append_subscribe_outro(self):
        without_outro = render_motion.build_motion_video(include_outro=False)
        with_outro = render_motion.build_motion_video(include_outro=True)

        self.assertGreater(with_outro.duration, without_outro.duration + 3.0)

    def test_build_motion_video_can_match_voice_duration_before_outro(self):
        without_outro = render_motion.build_motion_video(include_outro=False, main_duration=35.33)
        with_outro = render_motion.build_motion_video(include_outro=True, main_duration=35.33)

        self.assertAlmostEqual(without_outro.duration, 35.33, places=2)
        self.assertGreater(with_outro.duration, 39.0)
        self.assertLess(with_outro.duration, 40.0)


if __name__ == "__main__":
    unittest.main()
