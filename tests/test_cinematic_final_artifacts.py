import json
import subprocess
import unittest

from render_cinematic import ROOT, artifact_paths


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class CinematicFinalArtifactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frog_duration = float(probe(ROOT / "assets" / "frog.mp4")["format"]["duration"])

    def test_all_final_batch_videos_have_publishable_streams_and_duration(self):
        for topic_id in range(61, 66):
            with self.subTest(topic=topic_id):
                paths = artifact_paths(topic_id)
                self.assertTrue(paths.video.exists(), paths.video)
                self.assertTrue(paths.voice.exists(), paths.voice)
                self.assertTrue(paths.metadata.exists(), paths.metadata)

                media = probe(paths.video)
                video = next(stream for stream in media["streams"] if stream["codec_type"] == "video")
                audio = next(stream for stream in media["streams"] if stream["codec_type"] == "audio")
                self.assertEqual(video["codec_name"], "h264")
                self.assertEqual(audio["codec_name"], "aac")
                self.assertEqual((video["width"], video["height"]), (1080, 1920))
                self.assertEqual(video["r_frame_rate"], "30/1")
                self.assertEqual(video["pix_fmt"], "yuv420p")
                self.assertEqual(video.get("color_space"), "bt709")

                voice_duration = float(probe(paths.voice)["format"]["duration"])
                final_duration = float(media["format"]["duration"])
                self.assertAlmostEqual(final_duration, voice_duration + self.frog_duration, delta=0.35)
                self.assertGreaterEqual(final_duration, 35.0)
                self.assertLessEqual(final_duration, 45.0)

                metadata = json.loads(paths.metadata.read_text(encoding="utf-8"))
                self.assertEqual(metadata["topic_id"], topic_id)
                self.assertTrue(metadata["sentences"])
                self.assertTrue(metadata["words"])


if __name__ == "__main__":
    unittest.main()
