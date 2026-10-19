import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MotionCommandTest(unittest.TestCase):
    def run_motion(self, *args):
        return subprocess.run(
            [str(ROOT / "motion"), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_help_mentions_motion_and_classic_usage(self):
        result = self.run_motion("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("motion 36", result.stdout)
        self.assertIn("motion 31", result.stdout)

    def test_topic_36_dry_run_uses_motion_renderer(self):
        result = self.run_motion("36", "--dry-run", "--speed", "1.15")

        self.assertEqual(result.returncode, 0)
        self.assertIn("render_motion.py --topic 36 --speed 1.15", result.stdout)

    def test_other_topic_dry_run_uses_classic_renderer(self):
        result = self.run_motion("31", "--dry-run", "--max-duration", "45")

        self.assertEqual(result.returncode, 0)
        self.assertIn("render.py --topic 31 --max-duration 45", result.stdout)

    def test_topic_flag_dry_run_uses_classic_renderer(self):
        result = self.run_motion("--topic", "37", "--dry-run")

        self.assertEqual(result.returncode, 0)
        self.assertIn("render.py --topic 37", result.stdout)

    def test_comma_topics_dry_run_uses_classic_renderer(self):
        result = self.run_motion("31,32", "--dry-run")

        self.assertEqual(result.returncode, 0)
        self.assertIn("render.py --topics 31,32", result.stdout)


if __name__ == "__main__":
    unittest.main()
