import os
import time
import unittest
from pathlib import Path

from telegram_bot.cleanup import cleanup_old_files


class TelegramBotCleanupTest(unittest.TestCase):
    def test_removes_only_old_files(self):
        base = Path("/tmp") / self.id().replace(".", "_")
        old_file = base / "old.mp4"
        fresh_file = base / "fresh.mp4"
        try:
            base.mkdir(parents=True, exist_ok=True)
            old_file.write_text("old", encoding="utf-8")
            fresh_file.write_text("fresh", encoding="utf-8")
            old_time = time.time() - 3 * 24 * 60 * 60
            os.utime(old_file, (old_time, old_time))

            removed = cleanup_old_files([base], max_age_seconds=24 * 60 * 60)

            self.assertEqual(removed, 1)
            self.assertFalse(old_file.exists())
            self.assertTrue(fresh_file.exists())
        finally:
            old_file.unlink(missing_ok=True)
            fresh_file.unlink(missing_ok=True)
            base.rmdir()
