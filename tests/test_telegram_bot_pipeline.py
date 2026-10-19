from pathlib import Path
import sys
import unittest

from telegram_bot.domain import Plan
from telegram_bot.pipeline import (
    build_clip_command,
    build_download_command,
    build_localize_command,
    build_metadata_command,
    build_transcribe_command,
    yt_dlp_base_command,
    select_voice,
)


class TelegramBotPipelineTest(unittest.TestCase):
    def test_metadata_command_is_safe_and_playlist_free(self):
        cmd = build_metadata_command("https://youtu.be/abc")
        self.assertEqual(cmd[:3], [sys.executable, "-m", "yt_dlp"])
        self.assertIn("--no-playlist", cmd)
        self.assertIn("--dump-json", cmd)
        self.assertIn("--js-runtimes", cmd)
        self.assertIn("node", cmd)

    def test_ytdlp_command_uses_cookies_file_when_it_exists(self):
        cookies = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".txt")
        try:
            cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

            cmd = yt_dlp_base_command(cookies_file=cookies)

            self.assertIn("--cookies", cmd)
            self.assertIn(str(cookies), cmd)
        finally:
            cookies.unlink(missing_ok=True)

    def test_download_command_merges_to_mp4(self):
        cmd = build_download_command("https://youtu.be/abc", Path("input/%(id)s.%(ext)s"))
        self.assertIn("--merge-output-format", cmd)
        self.assertIn("mp4", cmd)
        self.assertIn("--print", cmd)

    def test_clip_command_exports_vertical_mp4(self):
        cmd = build_clip_command(Path("input/source.mp4"), Path("output/clip_1.mp4"), start_seconds=12, duration_seconds=30)

        self.assertEqual(cmd[:4], ["ffmpeg", "-y", "-ss", "12.000"])
        self.assertIn("-t", cmd)
        self.assertIn("30.000", cmd)
        self.assertIn("-vf", cmd)
        self.assertIn("pad=1080:1920", " ".join(cmd))
        self.assertEqual(cmd[-1], "output/clip_1.mp4")

    def test_voice_selection_depends_on_plan(self):
        self.assertEqual(select_voice(Plan.FREE, "alena"), "ru-RU-DmitryNeural")
        self.assertEqual(select_voice(Plan.PAID, "alena"), "alena")
        self.assertEqual(select_voice(Plan.PAID, None), "alena")

    def test_localize_command_targets_existing_pipeline(self):
        cmd = build_localize_command(Path("input/source.mp4"), Path("output/result.mp4"), Plan.PAID, "zahar")
        self.assertTrue(cmd[0].endswith("python"))
        self.assertIn("localize_video.py", cmd[1])
        self.assertIn("--input", cmd)
        self.assertIn("--output", cmd)
        self.assertIn("--voice", cmd)
        self.assertIn("zahar", cmd)
        self.assertIn("--tts-provider", cmd)
        self.assertIn("yandex", cmd)
        self.assertIn("--no-outro", cmd)

    def test_free_localize_command_uses_shorts_edge_voice(self):
        cmd = build_localize_command(Path("input/source.mp4"), Path("output/result.mp4"), Plan.FREE)

        self.assertIn("--tts-provider", cmd)
        self.assertIn("edge", cmd)
        self.assertIn("ru-RU-DmitryNeural", cmd)
        self.assertIn("--no-outro", cmd)

    def test_transcribe_command_targets_transcript_pipeline(self):
        cmd = build_transcribe_command(Path("input/source.mp4"), Path("output/transcript.txt"))

        self.assertTrue(cmd[0].endswith("python"))
        self.assertIn("transcribe_video.py", cmd[1])
        self.assertIn("--input", cmd)
        self.assertIn("input/source.mp4", cmd)
        self.assertIn("--output", cmd)
        self.assertIn("output/transcript.txt", cmd)
