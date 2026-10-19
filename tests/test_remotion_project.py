import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RemotionProjectTests(unittest.TestCase):
    def test_remotion_dependencies_and_entrypoint_exist(self):
        package = json.loads((ROOT / "package.json").read_text())
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        for name in ("remotion", "@remotion/cli", "react", "react-dom", "@remotion/media", "@remotion/captions", "mediabunny", "zod"):
            self.assertIn(name, deps)
        self.assertTrue((ROOT / "remotion" / "index.ts").is_file())
        self.assertTrue((ROOT / "remotion" / "Root.tsx").is_file())


if __name__ == "__main__":
    unittest.main()
