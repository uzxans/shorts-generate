import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RemotionSceneMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / "topics.json").read_text())
        cls.topic = next(t for t in data["topics"] if t["id"] == 57)
        cls.source = (ROOT / "remotion" / "ScriptedShort.tsx").read_text()
        cls.layers = (ROOT / "remotion" / "scenes" / "LayersScene.tsx").read_text()
        cls.code = (ROOT / "remotion" / "scenes" / "CodeScene.tsx").read_text()

    def test_router_selects_semantic_components(self):
        self.assertIn("LayersScene", self.source)
        self.assertIn("CodeScene", self.source)
        self.assertIn("TakeawayScene", self.source)

    def test_scene_components_consume_topic_specific_fields(self):
        scene = next(s for s in self.topic["script_timeline"] if s["scene_type"] == "code")
        self.assertIn("scene.code", self.code)
        self.assertIn("scene.highlights", self.code)
        self.assertTrue(scene["code"].strip())
        self.assertIn("scene.voiceover", self.layers)
        self.assertIn("scene.screen_text", (ROOT / "remotion" / "scenes" / "SceneShell.tsx").read_text())
        self.assertIn("scene.points", (ROOT / "remotion" / "scenes" / "TakeawayScene.tsx").read_text())


if __name__ == "__main__":
    unittest.main()
