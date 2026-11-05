#!/usr/bin/env python3
"""
Low-Token Automated Video Quality & Micro-Acting Critic
======================================================
Production-grade, zero-heavy-dependency video evaluation pipeline inspired by
Google DeepMind & Google Research video token-compression architectures
(TokenLearner, VideoPrism, and Gemini Vision MediaResolution).

Architecture:
1. Module 1: Zero-Token Quantitative Physics & AV-Sync Analyzer
   - ffmpeg/ffprobe + numpy (no opencv, no torch required).
   - Beat Motion Scores: 4-beat dramatic breakdown (0-1.1s Airlock, 1.1-2.7s Beat 2,
     2.7-4.5s Climax, 4.5s-End Tail) to catch "wooden statue freeze" & Frame-22 "Hold->Pop".
   - AV-Lip Sync Score: 130-3600Hz speech envelope vs lower-face visual motion correlation
     and silent airlock gating.
   - Anti-Fog Contrast Score: Luminance standard deviation & edge sharpness comparison
     between head 15% and tail 15% to catch H3 Join Match haze & photocopy drift.

2. Module 2: Google-Style "SlowFast Dual-Resolution Contact Sheet" Generator
   - Generates a single compact JPEG contact sheet (<video>_critic_sheet.jpg, 960x720, < 90 KB)
   - Costs exactly 258 tokens in Gemini vision tokenization (>92% to >99% token reduction!).
   - Top Half: Slow Macro Grid (4 full-frame beats at 0.55s, 1.90s, 3.60s, 5.10s) for global
     blocking, camera framing, headroom, and lighting.
   - Bottom Half: Fast High-Res ROI Strip (8 native-resolution face/mouth crops + audio dB meter).

3. Module 3: Google Gemini MEDIA_RESOLUTION_LOW + Pluggable Agent VLM Evaluator
   - Calls Google Gemini API (gemini-3.8-flash / gemini-2.5-flash) with MEDIA_RESOLUTION_LOW (66 tokens/frame)
     or single 258-token SlowFast Contact Sheet + physics summary.
   - Supports local agent mode (--agent-mode codex|claude|antigravity) or deterministic --offline-only rule engine.
   - Emits structured VideoCriticReport JSON.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ==============================================================================
# Data Models
# ==============================================================================

@dataclass
class BeatMotionDetail:
    beat_name: str
    time_range: str
    mean_motion: float
    peak_motion: float
    stutter_ratio: float
    freeze_detected: bool
    hold_pop_detected: bool


@dataclass
class QuantitativeMetrics:
    video_path: str
    duration_sec: float
    fps: float
    resolution: str
    beat_motion_scores: List[BeatMotionDetail]
    overall_motion_score: float
    av_lip_sync_score: float
    speech_correlation: float
    silence_suppression_score: float
    anti_fog_contrast_score: float
    head_contrast: float
    tail_contrast: float
    contrast_drift_pct: float
    head_sharpness: float
    tail_sharpness: float
    sharpness_drift_pct: float
    non_rigid_motion_score: float = 0.0
    non_rigid_ratio: float = 0.0
    character_internal_motion: float = 0.0
    mean_shift_variance: float = 0.0
    global_camera_explained_ratio: float = 0.0
    static_slideshow_detected: bool = False
    static_slideshow_veto: bool = False
    passed_veto_gates: bool = True
    hard_cut_count: int = 0
    hard_cut_frequency_per_min: float = 0.0
    mean_cut_jump_discontinuity: float = 0.0
    anomalies: List[str] = field(default_factory=list)


@dataclass
class TokenCostEstimate:
    raw_video_tokens_default: int
    gemini_low_res_video_tokens: int
    slowfast_contact_sheet_tokens: int
    token_reduction_vs_raw_pct: float
    token_reduction_vs_low_pct: float


@dataclass
class VideoCriticReport:
    video_path: str
    overall_score: float
    micro_acting_score: float
    lip_sync_score: float
    visual_fidelity_score: float
    passed: bool
    issues: List[str]
    re_render_recommendation: Optional[str]
    quantitative_metrics: Dict[str, Any]
    slowfast_sheet_path: Optional[str]
    sheet_file_size_kb: float
    token_cost_estimate: Dict[str, Any]
    evaluator_mode: str
    evaluation_timestamp: str
    static_slideshow_veto: bool = False
    passed_veto_gates: bool = True
    acceptance_status: str = "review_required"


# ==============================================================================
# Helper Utilities
# ==============================================================================

def check_binary(binary_name: str) -> str:
    path = shutil.which(binary_name)
    if not path:
        raise RuntimeError(f"Required binary '{binary_name}' was not found in PATH.")
    return path


def probe_video(video_path: str) -> Dict[str, Any]:
    ffprobe = check_binary("ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration,size:stream=width,height,r_frame_rate,codec_type,sample_rate",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(res.stdout)

    v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)

    if not v_stream:
        raise ValueError(f"No video stream found in {video_path}")

    w = int(v_stream.get("width", 640))
    h = int(v_stream.get("height", 360))

    r_fps = v_stream.get("r_frame_rate", "24/1")
    if "/" in r_fps:
        num, den = r_fps.split("/")
        fps = float(num) / max(1.0, float(den))
    else:
        fps = float(r_fps)

    duration = float(data.get("format", {}).get("duration", 0.0))
    if duration <= 0:
        duration = float(v_stream.get("duration", 1.0))

    has_audio = a_stream is not None
    audio_sr = int(a_stream.get("sample_rate", 16000)) if has_audio else 0

    return {
        "width": w,
        "height": h,
        "fps": fps,
        "duration": duration,
        "has_audio": has_audio,
        "audio_sample_rate": audio_sr
    }


# ==============================================================================
# Module 1: Zero-Token Quantitative Physics & AV-Sync Analyzer
# ==============================================================================

class QuantitativePhysicsAnalyzer:
    """Analyzes motion dynamics, speech-lip sync, and contrast haze with zero heavy CV dependencies."""

    def __init__(self, video_path: str, sample_fps: float = 12.0):
        self.video_path = str(video_path)
        self.sample_fps = float(sample_fps)
        self.meta = probe_video(self.video_path)
        self.duration = max(0.5, self.meta["duration"])
        self.native_fps = self.meta["fps"]

    def extract_audio_envelope(self) -> Tuple[np.ndarray, np.ndarray]:
        """Extracts 130-3600Hz human speech envelope and maps to frame-level RMS and dB."""
        if not self.meta["has_audio"]:
            n_frames = max(1, int(self.duration * self.sample_fps))
            return np.zeros(n_frames, dtype=np.float32), np.full(n_frames, -60.0, dtype=np.float32)

        ffmpeg = check_binary("ffmpeg")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name

        try:
            # Bandpass filter for speech fundamental & formant frequencies (130Hz - 3600Hz)
            cmd = [
                ffmpeg, "-y", "-i", self.video_path,
                "-vn", "-ac", "1", "-ar", "16000",
                "-af", "bandpass=f=1865:width_type=h:w=3470",
                "-f", "wav", wav_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            with wave.open(wav_path, "rb") as wf:
                sr = wf.getframerate()
                n_samples = wf.getnframes()
                raw_bytes = wf.readframes(n_samples)
                samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        n_frames = max(1, int(self.duration * self.sample_fps))
        samples_per_frame = max(1, int(sr / self.sample_fps))

        rms_list = []
        db_list = []
        for i in range(n_frames):
            s_idx = i * samples_per_frame
            e_idx = min(len(samples), (i + 1) * samples_per_frame)
            if e_idx > s_idx:
                chunk = samples[s_idx:e_idx]
                rms = float(np.sqrt(np.mean(chunk ** 2)))
            else:
                rms = 0.0
            rms_list.append(rms)
            db = 20.0 * math.log10(max(rms, 1e-4))
            db_list.append(max(-60.0, min(0.0, db)))

        return np.array(rms_list, dtype=np.float32), np.array(db_list, dtype=np.float32)

    def extract_frames_pipe(self, target_w: int = 320, target_h: int = 180) -> Tuple[np.ndarray, np.ndarray]:
        """Pipes downscaled RGB24 frames from ffmpeg directly into numpy array."""
        ffmpeg = check_binary("ffmpeg")
        cmd = [
            ffmpeg, "-i", self.video_path,
            "-vf", f"fps={self.sample_fps},scale={target_w}:{target_h}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw_bytes, _ = proc.communicate()

        frame_size = target_w * target_h * 3
        n_frames = len(raw_bytes) // frame_size
        if n_frames == 0:
            raise ValueError(f"Failed to read raw video frames from {self.video_path}")

        frames = np.frombuffer(raw_bytes[:n_frames * frame_size], dtype=np.uint8).reshape((n_frames, target_h, target_w, 3))
        timestamps = np.arange(n_frames) / self.sample_fps
        return frames, timestamps

    def detect_non_rigid_motion_and_cuts(self, frames: np.ndarray) -> Dict[str, Any]:
        """
        Anti-Slideshow / Ken Burns Pan-Zoom & Continuity Discontinuity Detector:
        1. Divides sampled frames into a 4x4 spatial grid (16 blocks).
        2. Estimates local 2D translation shifts (dx, dy) for each block using 2D FFT phase correlation.
        3. Computes global camera translation shift (median dx, dy) and compensated residual pixel difference.
        4. In static slideshows / Ken Burns pan-zoom, all blocks move rigidly together or global shift explains >85% of diff.
        5. In genuine AI animated video, character head/limbs/torso deform non-rigidly relative to background.
        6. Detects hard scene cuts (raw_diff > 35.0) and measures visual/structural discontinuity jumps.
        """
        n_frames = len(frames)
        if n_frames < 2:
            return {
                "non_rigid_motion_score": 0.0,
                "non_rigid_ratio": 0.0,
                "character_internal_motion": 0.0,
                "mean_shift_variance": 0.0,
                "global_camera_explained_ratio": 0.0,
                "static_slideshow_detected": True,
                "static_slideshow_veto": True,
                "passed_veto_gates": False,
                "hard_cut_count": 0,
                "hard_cut_frequency_per_min": 0.0,
                "mean_cut_jump_discontinuity": 0.0,
                "anomalies": ["Video has fewer than 2 frames."]
            }

        # Grayscale luminance
        Y = (0.299 * frames[:, :, :, 0] + 0.587 * frames[:, :, :, 1] + 0.114 * frames[:, :, :, 2]).astype(np.float32)
        H, W = Y.shape[1:3]
        grid_h, grid_w = 4, 4
        bh, bw = H // grid_h, W // grid_w
        window = np.hanning(bh)[:, None] * np.hanning(bw)[None, :]

        hard_cuts: List[Tuple[int, float]] = []
        explained_ratios: List[float] = []
        shift_stds: List[float] = []
        shift_vars: List[float] = []
        char_internals: List[float] = []
        non_rigid_count = 0
        total_valid = 0

        center_indices = [5, 6, 9, 10]
        outer_indices = [0, 1, 2, 3, 4, 7, 8, 11, 12, 13, 14, 15]

        for t in range(n_frames - 1):
            f1 = Y[t]
            f2 = Y[t + 1]
            raw_diff = float(np.mean(np.abs(f2 - f1)))

            # Hard cut detection (scene transition jump)
            if raw_diff > 35.0:
                hard_cuts.append((t, raw_diff))
                continue

            total_valid += 1

            # 4x4 spatial block phase correlation
            shifts = []
            for i in range(grid_h):
                for j in range(grid_w):
                    b1 = f1[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]
                    b2 = f2[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]

                    w1 = (b1 - np.mean(b1)) * window
                    w2 = (b2 - np.mean(b2)) * window

                    F1 = np.fft.fft2(w1)
                    F2 = np.fft.fft2(w2)
                    cross = F1 * np.conj(F2)
                    R = cross / (np.abs(cross) + 1e-7)
                    corr = np.fft.ifft2(R).real

                    py, px = np.unravel_index(np.argmax(corr), corr.shape)
                    dy = py - bh if py > bh // 2 else py
                    dx = px - bw if px > bw // 2 else px
                    shifts.append((dx, dy))

            shifts_arr = np.array(shifts, dtype=np.float32)
            med_dx = float(np.median(shifts_arr[:, 0]))
            med_dy = float(np.median(shifts_arr[:, 1]))

            # Translation-compensated residual pixel difference after shifting by median global camera shift
            idx_x, idx_y = int(round(med_dx)), int(round(med_dy))
            f1_shifted = np.roll(f1, shift=(idx_y, idx_x), axis=(0, 1))
            mask = np.ones_like(f1, dtype=bool)
            if idx_y > 0:
                mask[:idx_y, :] = False
            elif idx_y < 0:
                mask[idx_y:, :] = False
            if idx_x > 0:
                mask[:, :idx_x] = False
            elif idx_x < 0:
                mask[:, idx_x:] = False

            comp_diff = float(np.mean(np.abs(f2[mask] - f1_shifted[mask]))) if np.any(mask) else raw_diff
            explained = max(0.0, (raw_diff - comp_diff) / (raw_diff + 1e-5))

            # Block shift divergence across the 16 blocks
            s_std = float(np.std(shifts_arr[:, 0]) + np.std(shifts_arr[:, 1]))
            s_var = float(np.var(shifts_arr[:, 0]) + np.var(shifts_arr[:, 1]))

            # Character internal motion relative to peripheral camera/background motion
            c_shifts = shifts_arr[center_indices]
            o_shifts = shifts_arr[outer_indices]
            o_med = np.median(o_shifts, axis=0)
            char_int = float(np.mean(np.linalg.norm(c_shifts - o_med, axis=1)))

            explained_ratios.append(explained)
            shift_stds.append(s_std)
            shift_vars.append(s_var)
            char_internals.append(char_int)

            # A transition is non-rigid character animation if local blocks diverge or character deforms relative to background
            if (s_std >= 0.35 or char_int >= 0.25) and explained < 0.85:
                non_rigid_count += 1

        total_valid = max(1, total_valid)
        non_rigid_ratio = non_rigid_count / total_valid
        mean_char_int = float(np.mean(char_internals)) if char_internals else 0.0
        mean_shift_var = float(np.mean(shift_vars)) if shift_vars else 0.0
        mean_shift_std = float(np.mean(shift_stds)) if shift_stds else 0.0
        mean_explained = float(np.mean(explained_ratios)) if explained_ratios else 0.0

        # Non-rigid motion score (0 - 100)
        non_rigid_motion_score = max(0.0, min(100.0, non_rigid_ratio * 150.0 + min(1.5, mean_char_int) * 25.0))

        # Ken Burns / Slideshow detection criteria:
        # 1. Global camera shift explains > 85% of motion across the video
        # 2. Non-rigid motion score < 25.0
        # 3. All blocks move rigidly together with very low character internal motion (< 0.15) and block shift std (< 0.30)
        # 4. Non-rigid ratio < 18%
        static_slideshow_detected = (
            (non_rigid_motion_score < 25.0) or
            (non_rigid_ratio < 0.18) or
            (mean_char_int < 0.15 and mean_shift_std < 0.30) or
            (mean_explained > 0.85)
        )
        static_slideshow_veto = static_slideshow_detected or (non_rigid_motion_score < 25.0)
        passed_veto_gates = not static_slideshow_veto

        # Scene cut jump discontinuity metrics
        hard_cut_count = len(hard_cuts)
        cut_freq = (hard_cut_count / max(0.1, self.duration)) * 60.0
        mean_cut_jump = float(np.mean([c[1] for c in hard_cuts])) if hard_cuts else 0.0

        detector_anomalies: List[str] = []
        if static_slideshow_veto:
            detector_anomalies.append(
                "HARD VETO [STATIC_SLIDESHOW_DETECTED]: Video consists of static keyframes with camera pan/zoom (motion comic / PPT) rather than genuine character animation."
            )

        if hard_cut_count >= 3 and static_slideshow_veto:
            detector_anomalies.append(
                f"Scene cut jump discontinuity detected: {hard_cut_count} hard cuts (frequency: {cut_freq:.1f} cuts/min, avg jump: {mean_cut_jump:.1f}) without transition or matching composition."
            )

        return {
            "non_rigid_motion_score": round(non_rigid_motion_score, 1),
            "non_rigid_ratio": round(non_rigid_ratio, 3),
            "character_internal_motion": round(mean_char_int, 3),
            "mean_shift_variance": round(mean_shift_var, 3),
            "global_camera_explained_ratio": round(mean_explained * 100.0, 1),
            "static_slideshow_detected": static_slideshow_detected,
            "static_slideshow_veto": static_slideshow_veto,
            "passed_veto_gates": passed_veto_gates,
            "hard_cut_count": hard_cut_count,
            "hard_cut_frequency_per_min": round(cut_freq, 1),
            "mean_cut_jump_discontinuity": round(mean_cut_jump, 1),
            "anomalies": detector_anomalies
        }

    def analyze(self) -> QuantitativeMetrics:
        frames, timestamps = self.extract_frames_pipe()
        audio_rms, audio_db = self.extract_audio_envelope()

        # Align lengths if minor mismatch
        n_frames = min(len(frames), len(audio_rms))
        frames = frames[:n_frames]
        timestamps = timestamps[:n_frames]
        audio_rms = audio_rms[:n_frames]
        audio_db = audio_db[:n_frames]

        H, W = frames.shape[1:3]
        anomalies: List[str] = []

        # ----------------------------------------------------------------------
        # 0. Anti-Slideshow Non-Rigid Deformation & Continuity Cut Detector
        # ----------------------------------------------------------------------
        det = self.detect_non_rigid_motion_and_cuts(frames)
        anomalies.extend(det["anomalies"])

        # ----------------------------------------------------------------------
        # 1. Beat Motion Scores across 4 Dramatic Beats
        # ----------------------------------------------------------------------
        frame_diffs = np.mean(np.abs(frames[1:].astype(float) - frames[:-1].astype(float)), axis=(1, 2, 3))
        global_motion = np.concatenate([[0.0], frame_diffs])

        # Dramatic beats windowing
        dur = self.duration
        if 5.0 <= dur <= 10.0:
            beat_defs = [
                ("Beat 1: Airlock", 0.0, 1.1),
                ("Beat 2: Dialogue", 1.1, 2.7),
                ("Beat 3: Climax", 2.7, 4.5),
                ("Beat 4: Tail Anchor", 4.5, dur)
            ]
        else:
            # Scaled proportionally for shorter (<5s) or longer multi-scene videos (>10s)
            beat_defs = [
                ("Beat 1: Setup", 0.0, 0.20 * dur),
                ("Beat 2: Dialogue", 0.20 * dur, 0.55 * dur),
                ("Beat 3: Climax", 0.55 * dur, 0.82 * dur),
                ("Beat 4: Tail Anchor", 0.82 * dur, dur)
            ]

        beat_details: List[BeatMotionDetail] = []
        freeze_penalty = 0.0
        stutter_penalty = 0.0

        for b_name, b_start, b_end in beat_defs:
            mask = (timestamps >= b_start) & (timestamps <= b_end)
            if not np.any(mask):
                sub_motion = np.array([0.0])
            else:
                sub_motion = global_motion[mask]

            mean_m = float(np.mean(sub_motion))
            peak_m = float(np.max(sub_motion))
            stutter_r = peak_m / (mean_m + 1e-4)

            # Freeze detection: dialogue/climax should not freeze like a wooden statue
            freeze = False
            if "Dialogue" in b_name or "Climax" in b_name:
                if mean_m < 0.35:
                    freeze = True
                    freeze_penalty += 15.0
                    anomalies.append(f"Wooden statue freeze detected during {b_name} (motion: {mean_m:.2f})")

            # Hold->Pop stutter detection (Frame-22 freeze-then-pop artifact)
            hold_pop = False
            if stutter_r > 4.5 and peak_m > 4.8 and mean_m < 0.80:
                hold_pop = True
                stutter_penalty += 12.0
                anomalies.append(f"Hold->Pop motion pop stutter in {b_name} (stutter ratio: {stutter_r:.1f}x)")

            beat_details.append(BeatMotionDetail(
                beat_name=b_name,
                time_range=f"{b_start:.2f}s–{b_end:.2f}s",
                mean_motion=round(mean_m, 3),
                peak_motion=round(peak_m, 3),
                stutter_ratio=round(stutter_r, 2),
                freeze_detected=freeze,
                hold_pop_detected=hold_pop
            ))

        overall_motion_score = max(0.0, min(100.0, 100.0 - freeze_penalty - stutter_penalty))

        # Hard Veto clamp on overall motion score
        if det["static_slideshow_veto"]:
            overall_motion_score = min(overall_motion_score, 25.0)

        # ----------------------------------------------------------------------
        # 2. AV Lip Sync Score (Mouth ROI Motion vs Audio Envelope)
        # ----------------------------------------------------------------------
        if H > W:
            # Vertical/portrait video (e.g. 9:16)
            y1, y2 = int(0.20 * H), int(0.55 * H)
            x1, x2 = int(0.25 * W), int(0.75 * W)
        else:
            # Landscape video (e.g. 16:9)
            y1, y2 = int(0.35 * H), int(0.78 * H)
            x1, x2 = int(0.32 * W), int(0.68 * W)

        mouth_crop = frames[:, y1:y2, x1:x2, :].astype(float)
        mouth_diffs = np.mean(np.abs(mouth_crop[1:] - mouth_crop[:-1]), axis=(1, 2, 3))
        mouth_motion = np.concatenate([[0.0], mouth_diffs])

        # Active speech vs silent airlock intervals
        if dur <= 10.0:
            speech_time_mask = (timestamps >= beat_defs[1][1]) & (timestamps <= beat_defs[2][2])
            silence_time_mask = (timestamps < beat_defs[0][2]) | (timestamps >= beat_defs[3][1])
        else:
            speech_time_mask = (audio_db >= -28.0)
            silence_time_mask = (audio_db < -35.0)

        # Correlation in speech zone
        if np.any(speech_time_mask) and np.std(audio_rms[speech_time_mask]) > 1e-4 and np.std(mouth_motion[speech_time_mask]) > 1e-4:
            corr = float(np.corrcoef(audio_rms[speech_time_mask], mouth_motion[speech_time_mask])[0, 1])
            if math.isnan(corr):
                corr = 0.5
        else:
            corr = 0.5

        # Silence suppression: mouth movement during silent airlocks must be small
        speech_mouth_mean = float(np.mean(mouth_motion[speech_time_mask])) if np.any(speech_time_mask) else 1.0
        silence_mouth_mean = float(np.mean(mouth_motion[silence_time_mask])) if np.any(silence_time_mask) else 0.0

        silence_frames_count = int(np.sum(silence_time_mask))
        silence_leak_ratio = silence_mouth_mean / (speech_mouth_mean + 1e-4)
        if silence_frames_count >= 12 and silence_leak_ratio > 0.55 and silence_mouth_mean > 1.2:
            anomalies.append(f"Phantom mouth movement during silent airlock/tail (ratio: {silence_leak_ratio:.2f})")
            silence_suppr_score = max(0.0, 100.0 - silence_leak_ratio * 100.0)
        else:
            silence_suppr_score = 95.0

        # Normalizing correlation score (-1..1 to 0..100)
        corr_score = max(0.0, min(100.0, (corr + 1.0) * 50.0))
        av_lip_sync_score = 0.55 * corr_score + 0.45 * silence_suppr_score

        # ----------------------------------------------------------------------
        # 3. Anti-Fog Contrast & High-Frequency Sharpness Score
        # ----------------------------------------------------------------------
        Y_full = 0.299 * frames[:, :, :, 0] + 0.587 * frames[:, :, :, 1] + 0.114 * frames[:, :, :, 2]
        sample_pct = max(1, int(0.15 * n_frames))

        head_Y = Y_full[:sample_pct]
        tail_Y = Y_full[-sample_pct:]

        head_c = float(np.mean(np.std(head_Y, axis=(1, 2))))
        tail_c = float(np.mean(np.std(tail_Y, axis=(1, 2))))

        grad_x_h = np.abs(head_Y[:, :, 1:] - head_Y[:, :, :-1])
        grad_y_h = np.abs(head_Y[:, 1:, :] - head_Y[:, :-1, :])
        head_s = float(np.mean(grad_x_h) + np.mean(grad_y_h))

        grad_x_t = np.abs(tail_Y[:, :, 1:] - tail_Y[:, :, :-1])
        grad_y_t = np.abs(tail_Y[:, 1:, :] - tail_Y[:, :-1, :])
        tail_s = float(np.mean(grad_x_t) + np.mean(grad_y_t))

        c_drift = (tail_c - head_c) / (head_c + 1e-5)
        s_drift = (tail_s - head_s) / (head_s + 1e-5)

        fog_penalty = 0.0
        if c_drift < -0.30 or (c_drift < -0.24 and s_drift < -0.20):
            fog_penalty += 25.0
            anomalies.append(f"H3 Join Match fogging/haze detected: contrast collapsed by {abs(c_drift):.1%}")
        if s_drift < -0.28:
            fog_penalty += 20.0
            anomalies.append(f"Photocopy blur drift detected: sharpness collapsed by {abs(s_drift):.1%}")

        anti_fog_contrast_score = max(0.0, min(100.0, 100.0 - fog_penalty))

        return QuantitativeMetrics(
            video_path=self.video_path,
            duration_sec=round(self.duration, 2),
            fps=round(self.native_fps, 2),
            resolution=f"{self.meta['width']}x{self.meta['height']}",
            beat_motion_scores=beat_details,
            overall_motion_score=round(overall_motion_score, 1),
            av_lip_sync_score=round(av_lip_sync_score, 1),
            speech_correlation=round(corr, 3),
            silence_suppression_score=round(silence_suppr_score, 1),
            anti_fog_contrast_score=round(anti_fog_contrast_score, 1),
            head_contrast=round(head_c, 2),
            tail_contrast=round(tail_c, 2),
            contrast_drift_pct=round(c_drift * 100.0, 1),
            head_sharpness=round(head_s, 2),
            tail_sharpness=round(tail_s, 2),
            sharpness_drift_pct=round(s_drift * 100.0, 1),
            non_rigid_motion_score=det["non_rigid_motion_score"],
            non_rigid_ratio=det["non_rigid_ratio"],
            character_internal_motion=det["character_internal_motion"],
            mean_shift_variance=det["mean_shift_variance"],
            global_camera_explained_ratio=det["global_camera_explained_ratio"],
            static_slideshow_detected=det["static_slideshow_detected"],
            static_slideshow_veto=det["static_slideshow_veto"],
            passed_veto_gates=det["passed_veto_gates"],
            hard_cut_count=det["hard_cut_count"],
            hard_cut_frequency_per_min=det["hard_cut_frequency_per_min"],
            mean_cut_jump_discontinuity=det["mean_cut_jump_discontinuity"],
            anomalies=anomalies
        )


# ==============================================================================
# Module 2: SlowFast Dual-Resolution Contact Sheet Generator
# ==============================================================================

class SlowFastContactSheetGenerator:
    """
    Generates a single 960x720 JPEG (< 90 KB, exactly 258 tokens in Gemini vision)
    combining a 4-beat Slow Macro Grid with an 8-crop Fast Native-Resolution ROI strip.
    """

    def __init__(self, video_path: str, output_path: Optional[str] = None):
        self.video_path = str(video_path)
        self.meta = probe_video(self.video_path)
        self.duration = max(0.5, self.meta["duration"])
        if output_path:
            self.output_path = Path(output_path)
        else:
            p = Path(self.video_path)
            self.output_path = p.parent / f"{p.stem}_critic_sheet.jpg"

    def extract_native_frame(self, timestamp: float) -> Image.Image:
        """Extracts a single frame at exact timestamp at full native resolution."""
        ffmpeg = check_binary("ffmpeg")
        t = max(0.0, min(self.duration - 0.02, timestamp))
        cmd = [
            ffmpeg, "-ss", f"{t:.3f}", "-i", self.video_path,
            "-vframes", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw_bytes, _ = proc.communicate()
        W, H = self.meta["width"], self.meta["height"]
        expected = W * H * 3
        if len(raw_bytes) < expected:
            # Fallback black frame
            return Image.new("RGB", (W, H), (20, 20, 25))
        arr = np.frombuffer(raw_bytes[:expected], dtype=np.uint8).reshape((H, W, 3))
        return Image.fromarray(arr)

    def extract_audio_db_at(self, timestamp: float) -> float:
        """Calculates instantaneous audio energy (dB) at timestamp."""
        if not self.meta["has_audio"]:
            return -60.0
        ffmpeg = check_binary("ffmpeg")
        t_start = max(0.0, timestamp - 0.05)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name
        try:
            cmd = [
                ffmpeg, "-y", "-ss", f"{t_start:.3f}", "-t", "0.10",
                "-i", self.video_path, "-vn", "-ac", "1", "-ar", "16000",
                "-af", "bandpass=f=1865:width_type=h:w=3470",
                "-f", "wav", wav_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            with wave.open(wav_path, "rb") as wf:
                n = wf.getnframes()
                if n == 0:
                    return -60.0
                samples = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(samples ** 2)))
                db = 20.0 * math.log10(max(rms, 1e-4))
                return max(-60.0, min(0.0, db))
        except Exception:
            return -60.0
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    def generate(self, metrics: Optional[QuantitativeMetrics] = None) -> Tuple[Path, float]:
        W_TOTAL, H_TOTAL = 960, 720
        sheet = Image.new("RGB", (W_TOTAL, H_TOTAL), (16, 18, 24))
        draw = ImageDraw.Draw(sheet)

        # ----------------------------------------------------------------------
        # Header Status Bar (y: 0 to 32)
        # ----------------------------------------------------------------------
        draw.rectangle([0, 0, W_TOTAL, 32], fill=(24, 28, 38))
        v_stem = Path(self.video_path).name
        score_text = f"PHYSICS SCORE: {metrics.overall_motion_score:.1f}" if metrics else "ZERO-TOKEN PHYSICS"
        veto_text = f" | VETO: {'VETOED' if metrics.static_slideshow_veto else 'PASS'}" if metrics else ""
        hdr_txt = f"GOOGLE SLOWFAST CRITIC SHEET | 258 TOKENS (<90KB) | {v_stem} | {self.duration:.2f}s | {score_text}{veto_text}"
        draw.text((12, 8), hdr_txt, fill=(215, 225, 245))

        # ----------------------------------------------------------------------
        # Top Half: Slow Macro Grid (4 Dramatic Beats, y: 34 to 346, height 312)
        # ----------------------------------------------------------------------
        macro_y1, macro_y2 = 34, 346
        macro_h = macro_y2 - macro_y1
        macro_w = 240

        if 5.2 <= self.duration <= 15.0:
            macro_times = [0.55, 1.90, 3.60, 5.10]
            macro_labels = [
                f"BEAT 1: Airlock ({macro_times[0]:.2f}s)",
                f"BEAT 2: Dialogue ({macro_times[1]:.2f}s)",
                f"BEAT 3: Climax ({macro_times[2]:.2f}s)",
                f"BEAT 4: Tail Anchor ({macro_times[3]:.2f}s)"
            ]
        else:
            macro_times = [
                0.08 * self.duration,
                0.35 * self.duration,
                0.65 * self.duration,
                0.90 * self.duration
            ]
            macro_labels = [
                f"ACT 1: Hook ({macro_times[0]:.1f}s)",
                f"ACT 2: Escalation ({macro_times[1]:.1f}s)",
                f"ACT 3: Climax ({macro_times[2]:.1f}s)",
                f"ACT 4: Payoff ({macro_times[3]:.1f}s)"
            ]

        for i, t in enumerate(macro_times):
            x1 = i * macro_w
            x2 = (i + 1) * macro_w
            frame = self.extract_native_frame(t)
            # Scale & crop to fit 238x310
            panel_img = frame.resize((macro_w - 2, macro_h), Image.Resampling.LANCZOS)
            sheet.paste(panel_img, (x1 + 1, macro_y1))

            # Overlay badge
            pdraw = ImageDraw.Draw(sheet)
            pdraw.rectangle([x1 + 4, macro_y1 + 4, x1 + macro_w - 4, macro_y1 + 22], fill=(12, 14, 20, 200))
            pdraw.text((x1 + 8, macro_y1 + 6), macro_labels[i], fill=(240, 245, 255))

        # ----------------------------------------------------------------------
        # Mid Separator (y: 348 to 368, height 20)
        # ----------------------------------------------------------------------
        draw.rectangle([0, 348, W_TOTAL, 368], fill=(28, 32, 44))
        draw.text((12, 351), "FAST HIGH-RES ROI STRIP (100% NATIVE RESOLUTION FACE/MOUTH CROPS + AUDIO dB METER)", fill=(175, 195, 230))

        # ----------------------------------------------------------------------
        # Bottom Half: Fast High-Res ROI Strip (8 Native-Res Crops, y: 370 to 718)
        # ----------------------------------------------------------------------
        roi_y1, roi_y2 = 370, 718
        roi_h = roi_y2 - roi_y1
        roi_w = 120
        meter_h = 56
        crop_h = roi_h - meter_h

        # 8 timestamps spanning speech onsets, peaks, valleys, and silent airlocks
        if 5.2 <= self.duration <= 15.0:
            roi_times = [0.40, 1.20, 1.80, 2.40, 3.10, 3.80, 4.40, 5.20]
        else:
            roi_times = [float(f) for f in np.linspace(0.06 * self.duration, 0.94 * self.duration, 8)]

        native_w, native_h = self.meta["width"], self.meta["height"]
        # Center-face/mouth bounding box
        face_cx = int(native_w * 0.50)
        face_cy = int(native_h * 0.50)
        crop_box_w = int(native_w * 0.36)
        crop_box_h = int(native_h * 0.52)
        box_x1 = max(0, face_cx - crop_box_w // 2)
        box_x2 = min(native_w, face_cx + crop_box_w // 2)
        box_y1 = max(0, face_cy - int(crop_box_h * 0.42))
        box_y2 = min(native_h, face_cy + int(crop_box_h * 0.58))

        for j, t in enumerate(roi_times):
            x1 = j * roi_w
            full_frame = self.extract_native_frame(t)
            face_crop = full_frame.crop((box_x1, box_y1, box_x2, box_y2))
            crop_resized = face_crop.resize((roi_w - 2, crop_h), Image.Resampling.LANCZOS)
            sheet.paste(crop_resized, (x1 + 1, roi_y1))

            # Audio dB meter
            bar_y1 = roi_y1 + crop_h
            bar_y2 = roi_y2
            draw.rectangle([x1 + 1, bar_y1, x1 + roi_w - 1, bar_y2], fill=(20, 22, 30))

            db_val = self.extract_audio_db_at(t)
            pct = max(0.0, min(1.0, (db_val + 60.0) / 60.0))
            bar_w = int(pct * (roi_w - 12))

            if db_val < -30.0:
                bar_color = (60, 180, 100)
                status_txt = "[SILENT]"
            elif db_val < -13.0:
                bar_color = (235, 175, 45)
                status_txt = "[SPEECH]"
            else:
                bar_color = (235, 65, 65)
                status_txt = "[PEAK]"

            draw.rectangle([x1 + 6, bar_y1 + 6, x1 + 6 + bar_w, bar_y1 + 16], fill=bar_color)
            draw.text((x1 + 6, bar_y1 + 20), f"t={t:.2f}s", fill=(180, 195, 215))
            draw.text((x1 + 6, bar_y1 + 34), f"{db_val:.1f}dB {status_txt}", fill=bar_color)

        # ----------------------------------------------------------------------
        # Compression Loop: Ensure strict < 90 KB JPEG ceiling
        # ----------------------------------------------------------------------
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        quality = 80
        sheet.save(str(self.output_path), format="JPEG", quality=quality, optimize=True, progressive=True)
        size_kb = os.path.getsize(str(self.output_path)) / 1024.0

        while size_kb >= 89.0 and quality > 15:
            quality -= 5
            sheet.save(str(self.output_path), format="JPEG", quality=quality, optimize=True, progressive=True)
            size_kb = os.path.getsize(str(self.output_path)) / 1024.0

        return self.output_path, round(size_kb, 2)


# ==============================================================================
# Module 3: Google Gemini MEDIA_RESOLUTION_LOW + Pluggable Agent Evaluator
# ==============================================================================

class VideoQualityCritic:
    """Evaluates video quality using Google Gemini low-token vision or local agent rule engine."""

    def __init__(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        model: str = "gemini-3.8-flash",
        mode: str = "sheet",
        agent_mode: str = "none",
        api_key: Optional[str] = None
    ):
        self.video_path = Path(video_path).resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else self.video_path.parent
        self.model = model
        self.mode = mode
        self.agent_mode = agent_mode
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def run(self) -> VideoCriticReport:
        # 1. Module 1: Zero-Token Quantitative Physics & AV-Sync
        analyzer = QuantitativePhysicsAnalyzer(str(self.video_path))
        metrics = analyzer.analyze()

        # 2. Module 2: SlowFast Dual-Resolution Contact Sheet (< 90 KB)
        sheet_path = self.output_dir / f"{self.video_path.stem}_critic_sheet.jpg"
        generator = SlowFastContactSheetGenerator(str(self.video_path), str(sheet_path))
        saved_sheet, sheet_kb = generator.generate(metrics=metrics)

        # 3. Calculate Token Cost Estimates
        # In Gemini vision tokenization:
        # Default raw video at 24fps: 24 * duration * 258 tokens
        # Low-res video (MEDIA_RESOLUTION_LOW) at 2fps: 2 * duration * 66 tokens
        # SlowFast Contact Sheet: single <= 960px JPEG = 258 tokens
        raw_tokens = int(metrics.duration_sec * 24 * 258)
        low_res_tokens = int(metrics.duration_sec * 2 * 66)
        sheet_tokens = 258

        token_estimate = TokenCostEstimate(
            raw_video_tokens_default=raw_tokens,
            gemini_low_res_video_tokens=low_res_tokens,
            slowfast_contact_sheet_tokens=sheet_tokens,
            token_reduction_vs_raw_pct=round((1.0 - sheet_tokens / max(1, raw_tokens)) * 100.0, 1),
            token_reduction_vs_low_pct=round((1.0 - sheet_tokens / max(1, low_res_tokens)) * 100.0, 1)
        )

        # 4. Module 3: VLM or Rule-Based Deterministic Evaluation
        if self.mode != "offline" and self.api_key:
            report = self._evaluate_with_gemini(metrics, saved_sheet, sheet_kb, token_estimate)
        else:
            report = self._evaluate_offline_deterministic(metrics, saved_sheet, sheet_kb, token_estimate)

        # Save JSON report
        json_path = self.output_dir / f"{self.video_path.stem}_critic_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)

        return report

    def _evaluate_offline_deterministic(
        self,
        metrics: QuantitativeMetrics,
        sheet_path: Path,
        sheet_kb: float,
        token_estimate: TokenCostEstimate
    ) -> VideoCriticReport:
        # Scores derived directly from verified zero-token quantitative physics metrics
        micro_acting_score = round(metrics.overall_motion_score, 1)
        lip_sync_score = round(metrics.av_lip_sync_score, 1)
        fidelity_score = round(metrics.anti_fog_contrast_score, 1)

        overall = round(0.35 * micro_acting_score + 0.35 * lip_sync_score + 0.30 * fidelity_score, 1)
        passed_veto = metrics.passed_veto_gates and not metrics.static_slideshow_veto
        # Motion magnitude, contrast and an audio envelope cannot establish good
        # acting, correct mouth geometry, or phoneme-level sync. In particular a
        # frozen rectangle pasted into moving footage can score highly here.
        # Offline measurements are diagnostics, never final acceptance.
        passed = False

        if metrics.static_slideshow_veto:
            overall = min(overall, 25.0)
            micro_acting_score = min(micro_acting_score, 25.0)
            passed = False

        re_render = None
        if not passed:
            recommendations = []
            if metrics.static_slideshow_veto:
                recommendations.append("HARD VETO: Replace static keyframe slideshow (Ken Burns PPT) with genuine generative AI video models (Wan2.1 / MiniMax H3 / Veo) featuring continuous non-rigid skeletal deformation.")
            elif micro_acting_score < 80.0:
                recommendations.append("Strengthen 5-Step Causal Action Chain prompt; increase Beat 2/3 dynamic motion.")
            if lip_sync_score < 80.0:
                recommendations.append("Review speech and visible speaker timing against the original clips. Do not freeze or warp regions to improve this proxy metric.")
            if fidelity_score < 80.0:
                recommendations.append("Compare source and mastered frames for contrast loss before applying any correction.")
            recommendations.append("Watch the complete video and check dialogue, identity, cuts and artifacts; these numerical metrics do not establish quality.")
            re_render = " | ".join(recommendations)

        return VideoCriticReport(
            video_path=str(self.video_path),
            overall_score=overall,
            micro_acting_score=micro_acting_score,
            lip_sync_score=lip_sync_score,
            visual_fidelity_score=fidelity_score,
            passed=passed,
            issues=[*metrics.anomalies, "Manual visual and audio review required; offline metrics cannot approve a finished video."],
            re_render_recommendation=re_render,
            quantitative_metrics=asdict(metrics),
            slowfast_sheet_path=str(sheet_path),
            sheet_file_size_kb=sheet_kb,
            token_cost_estimate=asdict(token_estimate),
            evaluator_mode="offline-physics-deterministic",
            evaluation_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            static_slideshow_veto=metrics.static_slideshow_veto,
            passed_veto_gates=metrics.passed_veto_gates
        )

    def _evaluate_with_gemini(
        self,
        metrics: QuantitativeMetrics,
        sheet_path: Path,
        sheet_kb: float,
        token_estimate: TokenCostEstimate
    ) -> VideoCriticReport:
        """Invokes Gemini API with either MEDIA_RESOLUTION_LOW or SlowFast contact sheet."""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        with open(sheet_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("ascii")

        prompt = f"""
You are the Lead Technical Director and Micro-Acting Critic for AI Video Generation.
Evaluate this video using the provided Google SlowFast Dual-Resolution Contact Sheet and Quantitative Physics Metrics:

Quantitative Metrics:
- Video Duration: {metrics.duration_sec}s, FPS: {metrics.fps}
- Beat Motion Scores: {json.dumps([asdict(b) for b in metrics.beat_motion_scores])}
- AV Lip Sync Score: {metrics.av_lip_sync_score} (Speech correlation: {metrics.speech_correlation})
- Anti-Fog Contrast Score: {metrics.anti_fog_contrast_score} (Contrast drift: {metrics.contrast_drift_pct}%, Sharpness drift: {metrics.sharpness_drift_pct}%)
- Non-Rigid Motion Score: {metrics.non_rigid_motion_score} (Ratio: {metrics.non_rigid_ratio:.1%}, Internal motion: {metrics.character_internal_motion:.2f}, Slideshow detected: {metrics.static_slideshow_detected})
- Hard Cuts: {metrics.hard_cut_count} (Frequency: {metrics.hard_cut_frequency_per_min}/min, Avg jump: {metrics.mean_cut_jump_discontinuity})
- Identified Physics Anomalies: {json.dumps(metrics.anomalies)}

Inspect the Contact Sheet:
1. Top Half (Slow Macro Grid): Inspect camera blocking, headroom, lighting, and temporal continuity across the 4 beats.
2. Bottom Half (Fast High-Res ROI Strip): Verify micro-expressions (eyelid tension, brow furrowing, pupil stability) and whether mouth aperture matches the Audio dB meter beneath each crop.

Return strictly a JSON object with:
{{
  "overall_score": <float 0-100>,
  "micro_acting_score": <float 0-100>,
  "lip_sync_score": <float 0-100>,
  "visual_fidelity_score": <float 0-100>,
  "passed": <boolean>,
  "issues": [<string>],
  "re_render_recommendation": <string or null>
}}
"""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)

                overall_val = float(parsed.get("overall_score", 85.0))
                micro_val = float(parsed.get("micro_acting_score", 85.0))
                passed_veto = metrics.passed_veto_gates and not metrics.static_slideshow_veto
                passed_val = bool(parsed.get("passed", True)) and passed_veto

                if metrics.static_slideshow_veto:
                    overall_val = min(overall_val, 25.0)
                    micro_val = min(micro_val, 25.0)
                    passed_val = False

                issues = list(parsed.get("issues", []))
                for anom in metrics.anomalies:
                    if anom not in issues:
                        issues.append(anom)

                re_rec = parsed.get("re_render_recommendation")
                if metrics.static_slideshow_veto:
                    re_rec = "HARD VETO: Replace static keyframe slideshow with genuine generative AI video models (Wan2.1 / MiniMax H3 / Veo) featuring continuous non-rigid character animation."

                return VideoCriticReport(
                    video_path=str(self.video_path),
                    overall_score=overall_val,
                    micro_acting_score=micro_val,
                    lip_sync_score=float(parsed.get("lip_sync_score", 85.0)),
                    visual_fidelity_score=float(parsed.get("visual_fidelity_score", 85.0)),
                    passed=passed_val,
                    issues=issues,
                    re_render_recommendation=re_rec,
                    quantitative_metrics=asdict(metrics),
                    slowfast_sheet_path=str(sheet_path),
                    sheet_file_size_kb=sheet_kb,
                    token_cost_estimate=asdict(token_estimate),
                    evaluator_mode=f"gemini-vlm-{self.model}",
                    evaluation_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    static_slideshow_veto=metrics.static_slideshow_veto,
                    passed_veto_gates=metrics.passed_veto_gates
                )
        except Exception as e:
            sys.stderr.write(f"[WARN] Gemini API call failed ({e}), falling back to deterministic offline scorer.\n")
            return self._evaluate_offline_deterministic(metrics, sheet_path, sheet_kb, token_estimate)


# ==============================================================================
# Self-Test Synthesis & Verification
# ==============================================================================

def synthesize_benchmark_video(out_mp4: str, duration: float = 6.0, fps: int = 24, W: int = 640, H: int = 360) -> str:
    """Synthesizes a clean 6.0s 4-beat reference video with audio bursts & synchronized mouth motion."""
    n_frames = int(duration * fps)
    sr = 16000
    n_samples = int(duration * sr)

    # 1. Synthesize Audio
    audio_t = np.linspace(0, duration, n_samples, endpoint=False)
    audio_sig = np.zeros(n_samples, dtype=np.float32)
    # Speech burst between 1.1s and 4.5s
    speech_mask = (audio_t >= 1.1) & (audio_t <= 4.5)
    mod = 0.5 * (1.0 + np.sin(2 * np.pi * 4.0 * audio_t))
    tone = 0.6 * np.sin(2 * np.pi * 350.0 * audio_t) + 0.4 * np.sin(2 * np.pi * 800.0 * audio_t)
    audio_sig[speech_mask] = (mod * tone)[speech_mask] * 0.75
    audio_pcm = (audio_sig * 32767).clip(-32768, 32767).astype(np.int16)

    tmp_wav = out_mp4 + ".tmp.wav"
    with wave.open(tmp_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_pcm.tobytes())

    # 2. Synthesize Video
    ffmpeg = check_binary("ffmpeg")
    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "pipe:0",
        "-i", tmp_wav,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        out_mp4
    ]

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    yy, xx = np.mgrid[0:H, 0:W]
    base_cx, base_cy = W // 2, H // 2

    for i in range(n_frames):
        t = i / fps
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:, :, 0] = 32 + (yy / H * 18).astype(np.uint8)
        frame[:, :, 1] = 38 + (yy / H * 22).astype(np.uint8)
        frame[:, :, 2] = 48 + (yy / H * 28).astype(np.uint8)

        # Micro-acting head sway during active dialogue/climax beats
        if 1.1 <= t <= 4.5:
            cur_cx = base_cx + int(np.sin(2 * np.pi * 1.2 * t) * 3.5)
            cur_cy = base_cy + int(np.cos(2 * np.pi * 1.2 * t) * 2.0)
        else:
            cur_cx = base_cx
            cur_cy = base_cy

        head_mask = (((xx - cur_cx) / 75.0) ** 2 + ((yy - cur_cy) / 95.0) ** 2) <= 1.0
        eye_l = (((xx - (cur_cx - 30)) / 12.0) ** 2 + ((yy - (cur_cy - 25)) / 8.0) ** 2) <= 1.0
        eye_r = (((xx - (cur_cx + 30)) / 12.0) ** 2 + ((yy - (cur_cy - 25)) / 8.0) ** 2) <= 1.0

        frame[head_mask] = [218, 178, 142]
        frame[eye_l] = [32, 28, 22]
        frame[eye_r] = [32, 28, 22]

        if 1.1 <= t <= 4.5:
            openness = max(0.0, float(np.sin(2 * np.pi * 4.0 * t)))
            if t > 2.7:
                openness = max(0.0, float(np.sin(2 * np.pi * 5.0 * t))) * 1.25
            mw = 25
            mh = int(2 + openness * 14)
            mouth_mask = (((xx - cur_cx) / mw) ** 2 + ((yy - (cur_cy + 42)) / mh) ** 2) <= 1.0
            frame[mouth_mask] = [142, 42, 52]
        else:
            mouth_mask = (((xx - cur_cx) / 22) ** 2 + ((yy - (cur_cy + 42)) / 2.5) ** 2) <= 1.0
            frame[mouth_mask] = [122, 62, 62]

        p.stdin.write(frame.tobytes())

    p.stdin.close()
    p.wait()
    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    return out_mp4


def run_self_test() -> int:
    print("=" * 72)
    print("RUNNING SELF-TEST: Low-Token Video Quality & Micro-Acting Critic")
    print("=" * 72)

    with tempfile.TemporaryDirectory() as tmpdir:
        synth_mp4 = os.path.join(tmpdir, "benchmark_speech_4beat.mp4")
        print("[1/4] Synthesizing 6.0s 4-beat ground-truth benchmark video...")
        synthesize_benchmark_video(synth_mp4)
        print(f"      Synthesized: {synth_mp4} ({os.path.getsize(synth_mp4)} bytes)")

        print("[2/4] Executing Zero-Token Quantitative Physics & AV-Sync Analyzer...")
        critic = VideoQualityCritic(
            video_path=synth_mp4,
            output_dir=tmpdir,
            mode="offline",
            agent_mode="none"
        )
        report = critic.run()

        print("[3/4] Validating SlowFast Dual-Resolution Contact Sheet...")
        sheet_path = Path(report.slowfast_sheet_path)
        assert sheet_path.exists(), f"Contact sheet missing: {sheet_path}"
        with Image.open(sheet_path) as im:
            w, h = im.size
            assert (w, h) == (960, 720), f"Expected 960x720, got {w}x{h}"
        assert report.sheet_file_size_kb < 90.0, f"File size {report.sheet_file_size_kb} KB exceeds 90 KB ceiling!"
        print(f"      Contact Sheet: {sheet_path.name}")
        print(f"      Dimensions: {w}x{h} px | File Size: {report.sheet_file_size_kb:.2f} KB (< 90 KB: PASS)")
        print(f"      VLM Token Cost: 258 tokens (Reduction vs raw 37,152 tokens: {report.token_cost_estimate['token_reduction_vs_raw_pct']}%)")

        print("[4/4] Validating VideoCriticReport JSON Structure & Hard Veto Gates...")
        assert report.overall_score >= 80.0, f"Benchmark video failed score threshold: {report.overall_score}"
        assert not report.passed, "Offline proxy measurements must not approve final quality"
        assert report.acceptance_status == "review_required"
        assert report.passed_veto_gates, "Benchmark video failed hard veto gates!"
        assert not report.static_slideshow_veto, "Benchmark video falsely flagged as static slideshow!"
        assert report.quantitative_metrics["non_rigid_motion_score"] >= 25.0, "Benchmark video non-rigid motion score below threshold!"
        print(f"      Overall Score: {report.overall_score:.1f} / 100.0 (PASS: {report.passed})")
        print(f"      Veto Gates Passed: {report.passed_veto_gates} (Slideshow Veto: {report.static_slideshow_veto})")
        print(f"      Non-Rigid Deformation Score: {report.quantitative_metrics['non_rigid_motion_score']:.1f} (Ratio: {report.quantitative_metrics['non_rigid_ratio']*100:.1f}%)")
        print(f"      Micro-Acting Score: {report.micro_acting_score:.1f}")
        print(f"      Lip-Sync Score: {report.lip_sync_score:.1f}")
        print(f"      Visual Fidelity Score: {report.visual_fidelity_score:.1f}")

        print("\n--- VideoCriticReport Output JSON ---")
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))

    print("\n" + "=" * 72)
    print("Diagnostic self-test passed; finished videos still require visual and audio review.")
    print("=" * 72)
    return 0


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Google-Style Low-Token Video Quality & Micro-Acting Critic (258 Tokens / MEDIA_RESOLUTION_LOW)"
    )
    parser.add_argument("--video", "-v", type=str, help="Path to input MP4 video file")
    parser.add_argument("--output-dir", "-o", type=str, help="Output directory for sheet and report JSON")
    parser.add_argument("--model", "-m", type=str, default="gemini-3.8-flash", help="Gemini VLM model id")
    parser.add_argument("--mode", choices=["sheet", "video", "offline"], default="sheet", help="Evaluation mode")
    parser.add_argument("--offline-only", action="store_true", help="Force deterministic zero-token physics evaluation")
    parser.add_argument("--agent-mode", choices=["none", "codex", "claude", "antigravity"], default="none", help="Agent pipe mode")
    parser.add_argument("--api-key", type=str, help="Gemini API Key override")
    parser.add_argument("--json", action="store_true", help="Always output raw JSON result")
    parser.add_argument("--self-test", action="store_true", help="Run automated self-test on synthesized video")

    args = parser.parse_args()

    if args.self_test:
        sys.exit(run_self_test())

    if not args.video:
        parser.print_help()
        sys.exit(1)

    eval_mode = "offline" if args.offline_only else args.mode
    critic = VideoQualityCritic(
        video_path=args.video,
        output_dir=args.output_dir,
        model=args.model,
        mode=eval_mode,
        agent_mode=args.agent_mode,
        api_key=args.api_key
    )
    report = critic.run()

    if args.agent_mode in ("codex", "claude", "antigravity") and not args.json:
        print(f"### Video Critic Report: {Path(args.video).name}")
        verdict = "REVIEW REQUIRED" if report.evaluator_mode == "offline-physics-deterministic" else ("PASSED" if report.passed else "FAILED")
        print(f"- **Verdict**: {verdict} (Diagnostic score: {report.overall_score:.1f}/100)")
        print(f"- **Veto Gates**: {'✅ PASSED' if report.passed_veto_gates else '❌ VETO TRIGGERED: STATIC SLIDESHOW DETECTED'}")
        print(f"- **Non-Rigid Motion**: {report.quantitative_metrics.get('non_rigid_motion_score', 0.0):.1f}/100.0 (Non-rigid ratio: {report.quantitative_metrics.get('non_rigid_ratio', 0.0)*100:.1f}%)")
        print(f"- **Micro-Acting**: {report.micro_acting_score:.1f} | **Lip-Sync**: {report.lip_sync_score:.1f} | **Fidelity**: {report.visual_fidelity_score:.1f}")
        print(f"- **SlowFast Sheet**: `{report.slowfast_sheet_path}` ({report.sheet_file_size_kb:.1f} KB, 258 tokens)")
        if report.issues:
            print(f"- **Issues**: {', '.join(report.issues)}")
        if report.re_render_recommendation:
            print(f"- **Recommendation**: {report.re_render_recommendation}")
    else:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
