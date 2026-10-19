import unittest

from tools.hyperframes_demo import build_hyperframes_index


class HyperframesDemoTest(unittest.TestCase):
    def test_wraps_demo_html_as_timed_composition(self):
        html = build_hyperframes_index("<!doctype html><button>Run</button>", 1080, 760, 3.0)

        self.assertIn('data-composition-id="demo"', html)
        self.assertIn('data-width="1080"', html)
        self.assertIn('data-height="760"', html)
        self.assertIn('data-duration="3"', html)
        self.assertIn('id="demo"', html)
        self.assertIn('data-start="0"', html)
        self.assertIn("<button>Run</button>", html)
        self.assertIn("width: 1080px", html)
        self.assertIn("height: 760px", html)
        self.assertIn("window.__timelines.demo", html)


if __name__ == "__main__":
    unittest.main()
