import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from h3_performance import frame_budget, guidance_scale

class PerformanceBudgetTests(unittest.TestCase):
    def test_backend_alignment_never_truncates_natural_speech_or_reaction(self):
        for samples in (1, 78720, 90240, 328001):
            for rate in (24000, 32000, 44100):
                frames=frame_budget(samples,rate,.3,.8)
                self.assertEqual((frames-5)%17,0)
                needed=(samples+round(.3*rate)+round(.8*rate))/rate
                self.assertGreaterEqual(frames/24,needed)
                self.assertLess(frames/24-needed,17/24+1e-9)
    def test_invalid_pauses_cannot_create_invalid_audio_padding(self):
        for before,after in [(-1,.2),(float('nan'),.2),(.2,float('inf'))]:
            with self.assertRaises(ValueError):frame_budget(1000,24000,before,after)

    def test_guidance_is_explicit_and_rejects_invalid_values(self):
        self.assertEqual(guidance_scale(),1.)
        self.assertEqual(guidance_scale(2),2.)
        for value in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):guidance_scale(value)

if __name__=='__main__':unittest.main()
