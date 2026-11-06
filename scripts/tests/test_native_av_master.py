import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_av_master import master, inspect_clip


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'requires FFmpeg')
class NativePerformanceTests(unittest.TestCase):
    def test_nonzero_trim_preserves_the_corresponding_native_audio_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            # Sparse pulses make accidental silence trimming or audio offsets observable.
            voice = np.zeros((96000, 2), dtype=np.float32)
            voice[30000:31000] = .25
            voice[60000:61000] = -.25
            sf.write(p / 'original.wav', voice, 48000, subtype='FLOAT')
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=128x72:rate=24:duration=2', '-i', str(p/'original.wav'),
                            '-vf', 'setparams=range=limited:colorspace=bt709:color_primaries=bt709:color_trc=bt709',
                            '-c:v', 'libx264', '-qp', '0', '-c:a', 'pcm_f32le', str(p/'source.mov')], check=True)
            script = {'title': 'native timing', 'shots': [
                {'id': 'a', 'file': 'source.mov', 'first_frame': 6, 'end_frame': 30},
                {'id': 'b', 'file': 'source.mov', 'first_frame': 30, 'end_frame': 42}]}
            report = master(script, p, p/'out')
            result, rate = sf.read(p/'out/native.wav', dtype='float32', always_2d=True)
            np.testing.assert_array_equal(result, voice[12000:84000])
            self.assertEqual(rate, 48000)
            self.assertEqual(report['verified_frames'], 36)
            self.assertEqual(report['user_acceptance'], 'not_reviewed')
            self.assertTrue(all(s['audio_interval'] == s['video_interval'] for s in report['shots']))
            self.assertNotEqual(report['acceptance'], 'passed')
            with self.assertRaises(ValueError):
                inspect_clip(p/'source.mov', 40, 60)

    def test_silent_video_is_not_accepted_as_a_native_performance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'silent.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=128x72:rate=24:duration=1', str(path)], check=True)
            with self.assertRaisesRegex(ValueError, 'native dialogue audio is missing'):
                inspect_clip(path, 0, 20)


if __name__ == '__main__':
    unittest.main()
