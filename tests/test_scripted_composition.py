import unittest
from html.parser import HTMLParser

from core.scripted_timeline import validate_timeline
from core.scripted_composition import build_html
from tests.test_scripted_timeline import topic


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.items = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


class CompositionTest(unittest.TestCase):
    def test_places_full_speed_outro_after_script_not_inside_it(self):
        page = Elements(build_html(validate_timeline(topic()), []))
        videos = [a for t, a in page.items if t == "video"]
        self.assertEqual(len(videos), 1)
        self.assertEqual(float(videos[0]["data-start"]), 10)
        self.assertAlmostEqual(float(videos[0]["data-duration"]), 4.041667)
        self.assertNotIn("loop", videos[0])
        self.assertNotIn("data-playback-rate", videos[0])

    def test_text_is_not_executed_as_markup(self):
        data = topic()
        data["script_timeline"][0]["screen_text"] = '<script>alert("x")</script>'
        html = build_html(validate_timeline(data), [])
        page = Elements(html)
        scripts = [a for t, a in page.items if t == "script"]
        self.assertEqual(len(scripts), 3)  # local gsap, data, local timeline
        self.assertIn("&lt;script&gt;", html)

    def test_only_requested_audio_is_placed(self):
        board = validate_timeline(topic())
        silent = Elements(build_html(board, [], include_audio=False))
        voiced = Elements(build_html(board, [], include_audio=True))
        self.assertFalse(any(t == "audio" for t, a in silent.items))
        self.assertEqual({a["id"] for t, a in voiced.items if t == "audio"}, {"narration", "soundtrack"})


if __name__ == "__main__":
    unittest.main()
