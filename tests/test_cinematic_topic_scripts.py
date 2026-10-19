import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIMITATION_MARKERS = re.compile(r"\b(но|важно|помни)\b", re.IGNORECASE)
ABSOLUTE_PROMISES = ("гарантированно быстрее", "всегда быстрее", "никогда не тормозит")


class CinematicTopicScriptsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))
        cls.topics = [item for item in data["topics"] if 61 <= item["id"] <= 65]

    def test_batch_contains_five_topics(self):
        self.assertEqual([item["id"] for item in self.topics], [61, 62, 63, 64, 65])

    def test_hooks_are_short_and_concrete(self):
        for topic in self.topics:
            with self.subTest(topic=topic["id"]):
                self.assertLessEqual(len(topic["hook_text"]), 90)
                self.assertNotEqual(topic["hook_text"].strip(), topic["title"].strip())

    def test_voiceovers_fit_short_explainer_range(self):
        for topic in self.topics:
            with self.subTest(topic=topic["id"]):
                count = len(topic["voiceover"].split())
                self.assertGreaterEqual(count, 75)
                self.assertLessEqual(count, 115)

    def test_each_voiceover_has_one_clear_limitation_turn(self):
        for topic in self.topics:
            with self.subTest(topic=topic["id"]):
                markers = LIMITATION_MARKERS.findall(topic["voiceover"])
                self.assertEqual(len(markers), 1)

    def test_voiceovers_avoid_absolute_performance_promises(self):
        for topic in self.topics:
            lowered = topic["voiceover"].lower()
            with self.subTest(topic=topic["id"]):
                self.assertFalse(any(phrase in lowered for phrase in ABSOLUTE_PROMISES))


if __name__ == "__main__":
    unittest.main()
