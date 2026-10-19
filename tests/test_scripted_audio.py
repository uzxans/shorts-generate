import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from core.scripted_audio import align_segment, caption_groups


class AudioTest(unittest.TestCase):
    def test_pcm_slot_has_exact_sample_count(self):
        with tempfile.TemporaryDirectory() as td:
            source, out = Path(td)/"tone.wav", Path(td)/"aligned.wav"
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',str(source)],check=True)
            align_segment(source, out, 1, 2.5)
            with wave.open(str(out)) as wav:
                self.assertEqual(wav.getnframes(), 110250)
                self.assertEqual(wav.getframerate(), 44100)
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.readframes(4410), bytes(8820))

    def test_caption_times_follow_voice_speed_and_scene_offset(self):
        cues = caption_groups([{'text':'Один','start':0,'end':.6},
                               {'text':'два','start':.6,'end':1.2}], start=10, speed=1.1)
        self.assertAlmostEqual(cues[0]['start'], 10.12)
        self.assertAlmostEqual(cues[0]['words'][1]['start'], 10.12+.6/1.1)
        self.assertAlmostEqual(cues[0]['end'], 10.12+1.2/1.1)


if __name__ == '__main__':
    unittest.main()
