import unittest
from pathlib import Path

from core.cinematic_frog import load_frog_assets, render_frog_cta, render_frog_reaction


class CinematicFrogTest(unittest.TestCase):
    def test_existing_video_produces_full_size_cta(self):
        assets = load_frog_assets(Path("assets/frog.mp4"), Path("assets/fotoavatar.png"))
        frame = render_frog_cta(assets, 0.5)
        self.assertEqual(frame.shape, (1920, 1080, 3))

    def test_reaction_progress_is_limited_to_zero_one(self):
        assets = load_frog_assets(Path("assets/frog.mp4"), Path("assets/fotoavatar.png"))
        with self.assertRaises(ValueError):
            render_frog_reaction(assets, "panic", 1.1)

    def test_missing_video_falls_back_to_avatar(self):
        assets = load_frog_assets(Path("/tmp/missing-frog.mp4"), Path("assets/fotoavatar.png"))
        frame = render_frog_cta(assets, 0.5)
        self.assertEqual(frame.shape, (1920, 1080, 3))
