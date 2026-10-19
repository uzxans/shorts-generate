import unittest

from telegram_bot.domain import Plan, detect_source, validate_request, validate_uploaded_video


class TelegramBotDomainTest(unittest.TestCase):
    def test_detects_supported_sources(self):
        self.assertEqual(detect_source("https://www.youtube.com/watch?v=abc").name, "YOUTUBE")
        self.assertEqual(detect_source("https://youtu.be/abc").name, "YOUTUBE")
        self.assertEqual(detect_source("https://www.instagram.com/reel/abc/").name, "INSTAGRAM")

    def test_rejects_unsupported_sources(self):
        result = validate_request("https://example.com/video", Plan.FREE, 20)
        self.assertFalse(result.ok)
        self.assertIn("YouTube или Instagram", result.message)

    def test_free_tier_rejects_long_video_and_voice_choice(self):
        too_long = validate_request("https://youtu.be/abc", Plan.FREE, 61)
        self.assertFalse(too_long.ok)
        self.assertIn("60 секунд", too_long.message)

        voice = validate_request("https://youtu.be/abc", Plan.FREE, 20, voice="alena")
        self.assertFalse(voice.ok)
        self.assertIn("выбор голоса", voice.message)

    def test_paid_tier_allows_voice_and_rejects_over_limit(self):
        ok = validate_request("https://youtu.be/abc", Plan.PAID, 20 * 60, voice="alena")
        self.assertTrue(ok.ok)

        too_long = validate_request("https://youtu.be/abc", Plan.PAID, 20 * 60 + 1)
        self.assertFalse(too_long.ok)
        self.assertIn("20 минут", too_long.message)

    def test_uploaded_video_limits_are_3_minutes_free_and_20_minutes_paid(self):
        self.assertTrue(validate_uploaded_video(Plan.FREE, 180).ok)
        free_too_long = validate_uploaded_video(Plan.FREE, 181)
        self.assertFalse(free_too_long.ok)
        self.assertIn("3 минут", free_too_long.message)

        self.assertTrue(validate_uploaded_video(Plan.PAID, 20 * 60).ok)
        paid_too_long = validate_uploaded_video(Plan.PAID, 20 * 60 + 1)
        self.assertFalse(paid_too_long.ok)
        self.assertIn("20 минут", paid_too_long.message)
