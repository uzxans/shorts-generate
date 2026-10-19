import json
import subprocess
import unittest
from pathlib import Path

from PIL import Image

from core.cinematic_topics import get_storyboard
from render_cinematic import artifact_paths


class CinematicPreviewArtifactsTest(unittest.TestCase):
    def test_all_batch_previews_and_contact_sheets_are_valid(self):
        for topic_id in range(61, 66):
            with self.subTest(topic=topic_id):
                paths = artifact_paths(topic_id)
                self.assertTrue(paths.preview.exists(), paths.preview)
                self.assertTrue(paths.contact_sheet.exists(), paths.contact_sheet)

                probe = subprocess.run(
                    [
                        "ffprobe",
                        "-v", "error",
                        "-show_streams",
                        "-show_format",
                        "-of", "json",
                        str(paths.preview),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                media = json.loads(probe.stdout)
                video = next(stream for stream in media["streams"] if stream["codec_type"] == "video")
                self.assertEqual((video["width"], video["height"]), (1080, 1920))
                self.assertEqual(video["r_frame_rate"], "30/1")
                self.assertFalse(any(stream["codec_type"] == "audio" for stream in media["streams"]))
                self.assertGreater(float(media["format"]["duration"]), 0.0)

                with Image.open(paths.contact_sheet) as sheet:
                    self.assertGreater(sheet.width, 0)
                    expected_rows = (len(get_storyboard(topic_id).shots) + 1) // 2
                    self.assertEqual(sheet.size, (432, expected_rows * 384))


if __name__ == "__main__":
    unittest.main()
