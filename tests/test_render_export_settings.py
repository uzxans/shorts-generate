import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _constant_value(module: ast.Module, name: str):
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} constant not found")


def _write_videofile_kwargs(module: ast.Module) -> dict[str, ast.AST]:
    for node in ast.walk(module):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "write_videofile"
        ):
            return {kw.arg: kw.value for kw in node.keywords if kw.arg}
    raise AssertionError("write_videofile call not found")


class RenderExportSettingsTest(unittest.TestCase):
    def test_final_video_uses_high_quality_export_settings(self):
        module = ast.parse((ROOT / "render.py").read_text(encoding="utf-8"))

        self.assertEqual(_constant_value(module, "FINAL_VIDEO_BITRATE"), "12M")
        self.assertEqual(_constant_value(module, "FINAL_AUDIO_BITRATE"), "320k")
        self.assertEqual(
            _constant_value(module, "FINAL_FFMPEG_PARAMS"),
            [
                "-pix_fmt",
                "yuv420p",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-colorspace",
                "bt709",
                "-movflags",
                "+faststart",
            ],
        )

        kwargs = _write_videofile_kwargs(module)
        self.assertIsInstance(kwargs["bitrate"], ast.Name)
        self.assertEqual(kwargs["bitrate"].id, "FINAL_VIDEO_BITRATE")
        self.assertIsInstance(kwargs["audio_bitrate"], ast.Name)
        self.assertEqual(kwargs["audio_bitrate"].id, "FINAL_AUDIO_BITRATE")
        self.assertIsInstance(kwargs["ffmpeg_params"], ast.Name)
        self.assertEqual(kwargs["ffmpeg_params"].id, "FINAL_FFMPEG_PARAMS")


if __name__ == "__main__":
    unittest.main()
