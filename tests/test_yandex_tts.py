import unittest

from core.yandex_tts import build_yandex_tts_request


class YandexTtsTest(unittest.TestCase):
    def test_build_yandex_tts_request_uses_male_voice_and_mp3(self):
        url, headers, data = build_yandex_tts_request(
            "Замыкание — это память функции.",
            voice="ermil",
            speed="0.88",
            folder_id="folder123",
        )

        self.assertEqual(url, "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize")
        self.assertEqual(headers, {"Authorization": "Api-Key test-key"})
        self.assertEqual(data["text"], "Замыкание — это память функции.")
        self.assertEqual(data["lang"], "ru-RU")
        self.assertEqual(data["voice"], "ermil")
        self.assertEqual(data["speed"], "0.88")
        self.assertEqual(data["emotion"], "neutral")
        self.assertEqual(data["format"], "mp3")
        self.assertEqual(data["folderId"], "folder123")


if __name__ == "__main__":
    unittest.main()
