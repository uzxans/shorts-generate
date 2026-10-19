import unittest
import render


class DispatchTest(unittest.TestCase):
    def test_scripted_topic_is_validated_before_classic_demo_or_tts(self):
        with self.assertRaisesRegex(ValueError, 'script_timeline'):
            render.render_topic({'id': 901, 'title': 'Bad script', 'script_timeline': []}, skip_voice=True)


if __name__ == '__main__':
    unittest.main()
