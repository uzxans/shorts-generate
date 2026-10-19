import json
import tempfile
import unittest
from pathlib import Path

from tools.remotion_board import prepare_remotion_project


class RemotionDispatchTests(unittest.TestCase):
    def test_prepare_project_writes_digest_board_and_media_paths(self):
        topic = json.loads(Path("topics.json").read_text())["topics"]
        topic = next(t for t in topic if t["id"] == 57)
        board = dict(topic, duration=59.0, outro_start=55.0)
        with tempfile.TemporaryDirectory() as tmp:
            project = prepare_remotion_project(board, topic, Path(tmp), skip_voice=True)
            data = json.loads((project / "board.json").read_text())
            self.assertEqual(data["id"], 57)
            self.assertIn("digest", data)
            self.assertFalse(data["includeAudio"])
            self.assertTrue((project / "props.json").is_file())
            self.assertTrue((project / "remotion-entry.json").is_file())


if __name__ == "__main__":
    unittest.main()
