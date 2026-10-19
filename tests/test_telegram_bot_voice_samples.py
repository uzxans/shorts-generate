import unittest
from pathlib import Path

from telegram_bot.voice_samples import get_or_create_yandex_voice_sample, voice_label, voice_sample_path


class FakeResponse:
    def __init__(self, status_code=200, content=b"0" * 512, text=""):
        self.status_code = status_code
        self.content = content
        self.text = text


class TelegramBotVoiceSamplesTest(unittest.TestCase):
    def test_labels_match_yandex_speechkit_voice_names(self):
        self.assertEqual(voice_label("alena"), "Alena")
        self.assertEqual(voice_label("zahar"), "Zahar")
        self.assertEqual(voice_label("unknown"), "unknown")

    def test_yandex_voice_sample_is_created_and_cached(self):
        cache_dir = Path("/tmp") / self.id().replace(".", "_")
        calls = []

        def fake_post(url, *, headers, data, timeout):
            calls.append((url, headers, data, timeout))
            return FakeResponse(content=b"voice-sample" * 64)

        try:
            first = get_or_create_yandex_voice_sample(
                cache_dir,
                "zahar",
                env={"YANDEX_API_KEY": "key", "YANDEX_FOLDER_ID": "folder"},
                post=fake_post,
            )
            second = get_or_create_yandex_voice_sample(
                cache_dir,
                "zahar",
                env={"YANDEX_API_KEY": "key", "YANDEX_FOLDER_ID": "folder"},
                post=fake_post,
            )

            self.assertEqual(first, voice_sample_path(cache_dir, "zahar"))
            self.assertEqual(second, first)
            self.assertEqual(len(calls), 1)
            url, headers, data, timeout = calls[0]
            self.assertEqual(url, "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize")
            self.assertEqual(headers, {"Authorization": "Api-Key key"})
            self.assertEqual(data["voice"], "zahar")
            self.assertEqual(data["folderId"], "folder")
            self.assertEqual(data["format"], "oggopus")
            self.assertEqual(timeout, 60)
        finally:
            for child in cache_dir.glob("*"):
                child.unlink()
            cache_dir.rmdir()

    def test_yandex_voice_sample_requires_credentials(self):
        with self.assertRaisesRegex(RuntimeError, "YANDEX_API_KEY"):
            get_or_create_yandex_voice_sample(Path("/tmp/voice-samples"), "alena", env={}, post=lambda **_: None)
