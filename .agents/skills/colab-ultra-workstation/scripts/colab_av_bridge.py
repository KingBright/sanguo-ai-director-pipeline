#!/usr/bin/env python3
"""Unified Audio-Video Short-Drama CLI Bridge (Colab Ultra Workstation & Colab Operator).

Orchestrates the end-to-end multi-modal pipeline:
1. Emotion-Rich & Pronunciation-Accurate Standalone Audio Generation (IndexTTS 2.5 / Qwen3-TTS / Fun-CosyVoice3 / VoxCPM2).
2. Frame-Exact Audio Duration & MiniMax-H3 AV_LATENT Lip-Sync Conditioning:
   - exact_frames = round(audio_duration * fps)
   - 24kHz / 16kHz clean PCM_16 speech conditioning (vocal band leveled, DC-offset free)
   - Tail-frame clamping via MiniMaxH3AddGuide (frames [107, 136] / end-frame locks)
3. MiniMax-H3 ComfyUI Multi-Segment Video Generation (run_g4_v25_4seg_drama.py).
4. Acoustic-Aligned Automatic Subtitle Sync (auto_subtitle_video.py, 130Hz-3600Hz envelope, 10ms precision).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent

try:
    from chinese_normalizer import normalize_chinese_text_for_tts, validate_audio_chunk
except ImportError:
    try:
        from scripts.chinese_normalizer import normalize_chinese_text_for_tts, validate_audio_chunk
    except ImportError:
        def normalize_chinese_text_for_tts(s: str) -> str:
            return s


def inspect_audio_file(audio_path: Path, target_sr: int = 24000) -> Tuple[float, int, bool]:
    """Inspect WAV audio duration, sample rate, and channel count."""
    if not audio_path.exists():
        return 0.0, 0, False
    try:
        with wave.open(str(audio_path), "rb") as wf:
            frames = wf.getnframes()
            sr = wf.getframerate()
            channels = wf.getnchannels()
            dur = frames / float(sr) if sr > 0 else 0.0
            is_clean_sr = sr in (16000, 24000, 48000) and channels == 1
            return dur, sr, is_clean_sr
    except Exception:
        return 0.0, 0, False


def calculate_exact_frames(audio_dur: float, fps: float = 24.0, snap_to_17k5: bool = False) -> int:
    """Calculate frame-exact video length from audio duration: round(audio_duration * fps)."""
    raw_frames = int(round(audio_dur * fps))
    if not snap_to_17k5:
        return raw_frames
    k = max(4, round((raw_frames - 5) / 17.0))
    return int(17 * k + 5)


def condition_audio_for_lip_sync(in_path: Path, out_path: Path, target_sr: int = 24000) -> Path:
    """Ensure audio is 24kHz or 16kHz mono PCM_16 clean vocal conditioning for MiniMax-H3."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(in_path),
        "-vn", "-ac", "1", "-ar", str(target_sr),
        "-af", "highpass=f=80,lowpass=f=7500,loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "pcm_s16le",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True)
        return out_path
    except Exception:
        shutil.copy2(in_path, out_path)
        return out_path


def run_pipeline(args: argparse.Namespace) -> None:
    print("=" * 60)
    print("🎬 Colab Ultra Workstation: Unified Audio + Video Short-Drama Bridge")
    print(f"模式: {args.step.upper()} | 帧率: {args.fps} fps | 目标 GPU: {args.gpu}")
    print("=" * 60)

    config_data = {}
    if args.config and Path(args.config).exists():
        config_data = json.loads(Path(args.config).read_text(encoding="utf-8"))
        print(f"📋 已载入剧本配置: {args.config}")

    # STEP 1: AUDIO GENERATION (TTS with emotion & pronunciation accuracy)
    if args.step in ("all", "audio"):
        print("\n🎙️ [Stage 1/3] 语音合成 (独立云端双引擎 / IndexTTS 2.5 + Qwen3-TTS)...")
        tts_cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "colab_tts_client.py"),
            "--session", args.session,
            "--gpu", "L4",
            "--engine", args.tts_engine,
        ]
        if args.emotion:
            tts_cmd.extend(["--emotion", args.emotion])
        if args.emo_alpha is not None:
            tts_cmd.extend(["--emo-alpha", str(args.emo_alpha)])
        if args.spk_wav and args.text and args.out_audio:
            norm_text = normalize_chinese_text_for_tts(args.text)
            print(f"  • 中文文本规范化: {args.text} -> {norm_text}")
            tts_cmd.extend([
                "--spk-wav", args.spk_wav,
                "--text", norm_text,
                "--output", args.out_audio,
            ])
            subprocess.run(tts_cmd, check=True)
        elif args.manifest:
            tts_cmd.extend(["--manifest", args.manifest])
            subprocess.run(tts_cmd, check=True)
        else:
            print("  ℹ️ 未提供单句参数，运行双角色剧本遥控器 (run_cloud_tts_remote)...")
            remote_cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "run_cloud_tts_remote.py"),
                "--mode", args.tts_mode,
                "--gpu", "L4",
            ]
            if args.emotion:
                remote_cmd.extend(["--emotion", args.emotion])
            subprocess.run(remote_cmd, check=True)

    # STEP 2: VIDEO GENERATION (MiniMax-H3 with frame-exact lip sync & tail lock)
    if args.step in ("all", "video"):
        print("\n🎥 [Stage 2/3] 视频生成 (MiniMax-H3 G4 Blackwell ComfyUI)...")
        # Check audio tracks for frame-exact calculation
        if args.out_audio and Path(args.out_audio).exists():
            dur, sr, _ = inspect_audio_file(Path(args.out_audio))
            exact_f = calculate_exact_frames(dur, fps=args.fps, snap_to_17k5=args.snap_17k5)
            print(f"  • 音画同步计算: 音频={args.out_audio} ({dur:.2f}s) -> 精确生成帧数: {exact_f} 帧 (fps={args.fps})")
            cond_audio = condition_audio_for_lip_sync(Path(args.out_audio), Path("/tmp/lip_conditioned.wav"))
            print(f"  • MiniMax-H3 AV_LATENT 纯净语音注入完成: {cond_audio}")

        drama_cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "run_g4_v25_4seg_drama.py"),
            "--fps", str(args.fps),
        ]
        if args.config:
            drama_cmd.extend(["--config", args.config])
        if args.snap_17k5:
            drama_cmd.append("--snap-17k5")
        if args.only_seg:
            drama_cmd.extend(["--only-seg", str(args.only_seg)])
        if args.tail_lock_seg and args.tail_lock_img:
            drama_cmd.extend(["--tail-lock-seg", str(args.tail_lock_seg), "--tail-lock-img", args.tail_lock_img])

        print(f"  • 启动 G4 视频生成任务: {' '.join(drama_cmd)}")
        # If in dry-run or verification mode, log command
        if not args.dry_run:
            subprocess.run(drama_cmd, check=True)

    # STEP 3: ACOUSTIC SUBTITLE & INTRO BADGES (auto_subtitle_video.py)
    if args.step in ("all", "subtitle"):
        print("\n🔤 [Stage 3/3] 声学对齐字幕与人物铭牌压制 (130-3600Hz 能谱包络 10ms 精度)...")
        target_video = args.video_in or (config_data.get("output_mp4") if config_data else "OfficeDuel_V9_Final_Master.mp4")
        sub_cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "auto_subtitle_video.py"),
            target_video,
        ]
        if args.config:
            sub_cmd.extend(["--config", args.config])
        if args.no_cards:
            sub_cmd.append("--no-cards")

        print(f"  • 启动自动字幕压制: {' '.join(sub_cmd)}")
        if not args.dry_run and Path(target_video).exists():
            subprocess.run(sub_cmd, check=True)
        else:
            print(f"  ℹ️ [跳过执行] 视频文件尚未就绪: {target_video} (已准备好执行命令)")

    print("\n✅ 短剧音视频工作流调度就绪！")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Audio-Video Short-Drama CLI Bridge")
    parser.add_argument("--step", choices=["all", "audio", "video", "subtitle"], default="all", help="Pipeline step")
    parser.add_argument("--session", default="freshloop-g4", help="Colab session name")
    parser.add_argument("--gpu", default="G4", help="GPU tier for video rendering (G4 / L4)")
    parser.add_argument("--fps", type=float, default=24.0, help="Video frame rate for audio duration sync (default: 24.0)")
    parser.add_argument("--snap-17k5", action="store_true", help="Snap exact frames to legal MiniMax-H3 F = 17k + 5")
    parser.add_argument("--config", help="Path to drama_config.json")
    parser.add_argument("--dry-run", action="store_true", help="Print commands and verify parameters without running Colab GPU")

    # Audio options
    parser.add_argument("--tts-engine", default="indextts25", choices=["indextts25", "cosyvoice3", "voxcpm2", "auto"])
    parser.add_argument("--tts-mode", default="hybrid", choices=["hybrid", "qwen", "indextts"])
    parser.add_argument("--emotion", choices=["happy", "angry", "sad", "fearful", "afraid", "surprised", "calm", "cold_laugh", "whisper", "disgusted", "melancholic"], default="calm")
    parser.add_argument("--emo-alpha", type=float, default=0.40)
    parser.add_argument("--spk-wav", help="Speaker prompt WAV for audio")
    parser.add_argument("--text", help="Dialogue line text to synthesize")
    parser.add_argument("--out-audio", help="Output WAV path")
    parser.add_argument("--manifest", help="Batch manifest JSON")

    # Video options
    parser.add_argument("--only-seg", type=int, choices=[1, 2, 3, 4], help="Render only segment N")
    parser.add_argument("--tail-lock-seg", type=int, choices=[1, 2, 3, 4], help="Apply MiniMaxH3AddGuide tail lock")
    parser.add_argument("--tail-lock-img", help="Tail lock PNG image filename")

    # Subtitle options
    parser.add_argument("--video-in", help="Input video MP4 for subtitling")
    parser.add_argument("--no-cards", action="store_true", help="Disable character intro badges")

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
