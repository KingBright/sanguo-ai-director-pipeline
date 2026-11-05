import sys
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from clean_master import check_timing, srt_time, plan_story, master, frame_hashes, sha
from video_quality_critic import QuantitativeMetrics, TokenCostEstimate, VideoQualityCritic


class TimingTests(unittest.TestCase):
    def test_natural_short_line_leaves_reaction_time(self):
        self.assertEqual(check_timing("你好世界", 2, .45, 6), 2)

    def test_long_speech_is_rejected_instead_of_truncated(self):
        with self.assertRaisesRegex(ValueError, "does not fit"):
            check_timing("你好世界", 5.2, .45, 6)

    def test_old_two_second_rapid_dialogue_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "too fast"):
            check_timing("独眼地精和蛙帽小贼正在彩票亭前鬼祟徘徊", 2.15, .5, 6)

    def test_non_finite_timeline_is_rejected(self):
        with self.assertRaises(ValueError):
            check_timing("你好", float("nan"), .45, 6)

    def test_subtitle_rounding_carries_to_next_minute(self):
        self.assertEqual(srt_time(59.9999), "00:01:00,000")


class CriticBoundaryTests(unittest.TestCase):
    def test_perfect_proxy_scores_cannot_approve_video(self):
        metrics = QuantitativeMetrics(
            video_path="clip.mp4", duration_sec=6, fps=24, resolution="1280x720",
            beat_motion_scores=[], overall_motion_score=100, av_lip_sync_score=100,
            speech_correlation=1, silence_suppression_score=100, anti_fog_contrast_score=100,
            head_contrast=50, tail_contrast=50, contrast_drift_pct=0,
            head_sharpness=50, tail_sharpness=50, sharpness_drift_pct=0,
        )
        critic = object.__new__(VideoQualityCritic)
        critic.video_path = Path("clip.mp4")
        report = critic._evaluate_offline_deterministic(metrics, Path("sheet.jpg"), 10,
                                                       TokenCostEstimate(1, 1, 1, 0, 0))
        self.assertEqual(report.overall_score, 100)
        self.assertFalse(report.passed)
        self.assertEqual(report.acceptance_status, "review_required")
        self.assertTrue(any("Manual" in issue for issue in report.issues))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
class MediaIntegrationTests(unittest.TestCase):
    def test_mixed_color_coverage_is_explicitly_normalized_without_frame_changes(self):
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            raw, voice = p / "raw", p / "voice"
            raw.mkdir()
            voice.mkdir()
            original = {}
            for name, matrix in [("a", "bt709"), ("b", "smpte170m")]:
                clip = raw / f"{name}.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                                "testsrc2=size=128x72:rate=24:duration=2", "-vf",
                                f"setparams=range=limited:colorspace={matrix}:color_primaries=bt709:color_trc={'bt709' if name == 'a' else 'iec61966-2-1'}",
                                "-c:v", "libx264", "-qp", "0",
                                "-colorspace", matrix, "-color_range", "tv", "-color_primaries", "bt709",
                                "-color_trc", "bt709" if name == "a" else "iec61966-2-1", str(clip)], check=True)
                original[clip] = sha(clip)
            t = np.arange(24000 * 3) / 24000
            sf.write(voice / "line.wav", .15 * np.sin(2 * np.pi * 230 * t), 24000)
            t = np.arange(24000 * 5) / 24000
            sf.write(p / "music.wav", .03 * np.sin(2 * np.pi * 110 * t), 24000)
            script = {"title": "Test", "dialogue": [{"id": "line", "speaker": "A", "text": "测试对白",
                       "before": .1, "after": .2, "coverage": ["a.mp4", "b.mp4"]}]}
            plan = plan_story(script, raw, voice, p / "coverage")
            segments = plan["shots"][0]["source_segments"]
            self.assertEqual(len(segments), 2)  # One performance spans two camera views.
            self.assertIn("colorspace=all=bt709", segments[1]["color_conversion"])
            expected = [h for s in segments for h in frame_hashes(Path(s["color_reference"]))[s["first_frame"]:s["end_frame"]]]
            master(plan, p / "coverage", voice, p / "music.wav", p / "master")
            self.assertEqual(frame_hashes(p / "master/final.mp4"), expected)
            self.assertTrue(all(sha(path) == digest for path, digest in original.items()))
            report = json.loads((p / "master/master_report.json").read_text())
            self.assertEqual(report["speech_speed"], 1.)


if __name__ == "__main__":
    unittest.main()
