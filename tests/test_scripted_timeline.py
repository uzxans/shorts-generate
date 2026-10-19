import copy
import unittest

from core.scripted_timeline import validate_timeline, voice_cache_key, fit_voice


def topic():
    return {"id": 901, "title": "Test", "script_timeline": [
        {"start": 0, "end": 5, "scene_type": "title", "screen_text": "Тест",
         "voiceover": "Покажем, как это работает.", "animation": {"preset": "reveal"},
         "transition_out": {"type": "slide", "duration": 0.5}},
        {"start": 5, "end": 10, "scene_type": "tilt_card", "screen_text": "Наклон",
         "voiceover": "Наведение наклоняет карточку.", "animation": {"preset": "hover_tilt"}}
    ]}


class TimelineTest(unittest.TestCase):
    def test_keeps_seconds_and_adds_full_outro(self):
        board = validate_timeline(topic(), outro_duration=4.041667, max_duration=60)
        self.assertEqual(board["script_timeline"][1]["start"], 5)
        self.assertAlmostEqual(board["duration"], 14.041667)
        self.assertEqual(board["outro_start"], 10)

    def test_rejects_gaps_overlaps_nonfinite_and_unknown_effects(self):
        for key, value in [("start", 6), ("start", 4), ("end", float("nan")),
                           ("scene_type", "magic")]:
            with self.subTest(key=key, value=value):
                data = topic()
                data["script_timeline"][1][key] = value
                with self.assertRaises(ValueError):
                    validate_timeline(data)
        data = topic()
        data["script_timeline"][0]["animation"]["preset"] = "anything"
        with self.assertRaisesRegex(ValueError, "preset"):
            validate_timeline(data)

    def test_rejects_incomplete_speech_and_too_long_transition(self):
        for update in [{"voiceover": "Раньше было..."},
                       {"transition_out": {"type": "slide", "duration": 9}}]:
            data = topic()
            data["script_timeline"][0].update(update)
            with self.assertRaises(ValueError):
                validate_timeline(data)

    def test_budget_never_compresses_script(self):
        with self.assertRaisesRegex(ValueError, "max-duration"):
            validate_timeline(topic(), max_duration=12)

    def test_rejects_unsafe_id_and_nontext_scene_payload(self):
        data = topic()
        data['id'] = '../../outside'
        with self.assertRaisesRegex(ValueError, 'id'):
            validate_timeline(data)
        data = topic()
        data['script_timeline'][0].update(scene_type='code', animation={'preset':'code_focus'}, code=12)
        with self.assertRaisesRegex(ValueError, 'code'):
            validate_timeline(data)

    def test_normalization_does_not_mutate_source(self):
        data = topic()
        original = copy.deepcopy(data)
        validate_timeline(data)
        self.assertEqual(data, original)

    def test_voice_cache_is_content_and_settings_sensitive(self):
        key = voice_cache_key("Привет", "Dmitry", "+5%")
        for args in [("Пока", "Dmitry", "+5%"), ("Привет", "Anna", "+5%"),
                     ("Привет", "Dmitry", "+10%")]:
            self.assertNotEqual(key, voice_cache_key(*args))

    def test_speech_overrun_is_rejected_not_cut(self):
        self.assertEqual(fit_voice(3, 5), 1)
        self.assertGreater(fit_voice(5.1, 5), 1)
        with self.assertRaisesRegex(ValueError, "озвуч"):
            fit_voice(7, 5)


if __name__ == "__main__":
    unittest.main()
