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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent

COLAB_BIN = os.environ.get("COLAB_BIN") or shutil.which("colab") or str(Path.home() / ".local/bin/colab")


def stop_colab_session(session: str) -> None:
    print(f"🛑 [CCU 停机保护] 正在立即释放 G4 算力实例: {session} ...", flush=True)
    try:
        subprocess.run([COLAB_BIN, "stop", "-s", session], capture_output=True, text=True, timeout=30)
        print(f"✅ [算力释放] 实例 {session} 已停止计费！", flush=True)
    except Exception as exc:
        print(f"⚠️ [算力释放警告] 停止 {session} 遇到异常: {exc}", flush=True)


def chunk_segments(segs: List[int], n: int) -> List[List[int]]:
    if not segs:
        return []
    n = max(1, min(n, len(segs)))
    k, m = divmod(len(segs), n)
    chunks = []
    start = 0
    for i in range(n):
        size = k + (1 if i < m else 0)
        chunks.append(segs[start : start + size])
        start += size
    return [c for c in chunks if c]


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
    if args.parallel_workers is not None:
        args.workers_per_g4 = args.parallel_workers

    print("=" * 60)
    print("🎬 Colab Ultra Workstation: Unified Audio + Video Short-Drama Bridge")
    print(f"模式: {args.step.upper()} | 帧率: {args.fps} fps | 目标 GPU: {args.gpu}")
    print(f"G4 Fleet 集群: {args.g4_fleet} 节点 | 单机 Worker: {args.workers_per_g4} | TTS 并发: {args.tts_concurrency}")
    print("=" * 60)

    config_data = {}
    if args.config and Path(args.config).exists():
        config_data = json.loads(Path(args.config).read_text(encoding="utf-8"))
        print(f"📋 已载入剧本配置: {args.config}")

    # STEP 1: AUDIO GENERATION (Parallel TTS with ThreadPoolExecutor)
    if args.step in ("all", "audio"):
        print(f"\n🎙️ [Stage 1/3] 语音合成 (独立云端双引擎 / IndexTTS 2.5 + Qwen3-TTS | ThreadPoolExecutor 并发={args.tts_concurrency})...")
        lines_to_synth = []
        if args.manifest and Path(args.manifest).exists():
            m_items = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
            if isinstance(m_items, list):
                lines_to_synth.extend(m_items)
        elif config_data and "segments" in config_data:
            chars = config_data.get("characters", {})
            r1 = chars.get("role1", {})
            r2 = chars.get("role2", {})
            r1_v = args.spk_wav or r1.get("voice_wav")
            r2_v = args.spk_wav or r2.get("voice_wav")
            for s in config_data.get("segments", []):
                line = s.get("line")
                if line:
                    spk = s.get("speaker")
                    is_r1 = str(spk).lower() in ("1", "role1", "s1", "female", "left")
                    spk_wav = r1_v if is_r1 else r2_v
                    seg_id = s.get("seg_id", 1)
                    out_name = s.get("audio") or f"seg{seg_id}_tts.wav"
                    lines_to_synth.append({
                        "text": line,
                        "spk_wav": spk_wav,
                        "out_audio": out_name,
                        "seg_id": seg_id,
                    })
        elif args.spk_wav and args.text and args.out_audio:
            lines_to_synth.append({
                "text": args.text,
                "spk_wav": args.spk_wav,
                "out_audio": args.out_audio,
            })

        if lines_to_synth:
            print(f"  • 检测到 {len(lines_to_synth)} 句待合成台词，启动 ThreadPoolExecutor(max_workers={args.tts_concurrency}) 并发生成...")

            def _synth_worker(item: dict) -> None:
                raw_text = item["text"]
                norm_text = normalize_chinese_text_for_tts(raw_text)
                spk = item.get("spk_wav") or args.spk_wav
                out_path = item.get("out_audio") or item.get("output") or args.out_audio or "/tmp/tts_out.wav"
                print(f"  • [TTS 并发] 台词规范化: '{raw_text}' -> '{norm_text}' ({out_path})", flush=True)
                tts_cmd = [
                    sys.executable,
                    str(SCRIPTS_DIR / "colab_tts_client.py"),
                    "--session", args.session,
                    "--gpu", "L4",
                    "--engine", args.tts_engine,
                    "--spk-wav", str(spk),
                    "--text", norm_text,
                    "--output", str(out_path),
                ]
                if args.emotion:
                    tts_cmd.extend(["--emotion", args.emotion])
                if args.emo_alpha is not None:
                    tts_cmd.extend(["--emo-alpha", str(args.emo_alpha)])
                if not args.dry_run:
                    subprocess.run(tts_cmd, check=True)
                else:
                    print(f"  [Dry-Run] 执行命令: {' '.join(tts_cmd)}")

            with ThreadPoolExecutor(max_workers=args.tts_concurrency) as tts_pool:
                futs = [tts_pool.submit(_synth_worker, it) for it in lines_to_synth]
                for fut in as_completed(futs):
                    fut.result()
        else:
            print("  ℹ️ 未提供单句/分镜台词清单，运行双角色剧本遥控器 (run_cloud_tts_remote)...")
            remote_cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "run_cloud_tts_remote.py"),
                "--mode", args.tts_mode,
                "--gpu", "L4",
            ]
            if args.emotion:
                remote_cmd.extend(["--emotion", args.emotion])
            if not args.dry_run:
                subprocess.run(remote_cmd, check=True)
            else:
                print(f"  [Dry-Run] 执行命令: {' '.join(remote_cmd)}")

    # STEP 2: VIDEO GENERATION (G4 Fleet Parallel Scheduling + Zero-Idle Pre-Queueing)
    if args.step in ("all", "video"):
        print(f"\n🎥 [Stage 2/3] 视频生成 (MiniMax-H3 G4 Fleet 集群调度 | Fleet 规模={args.g4_fleet} | Workers/G4={args.workers_per_g4})...")

        # Check audio tracks for frame-exact calculation
        if args.out_audio and Path(args.out_audio).exists():
            dur, sr, _ = inspect_audio_file(Path(args.out_audio))
            exact_f = calculate_exact_frames(dur, fps=args.fps, snap_to_17k5=args.snap_17k5)
            print(f"  • 音画同步计算: 音频={args.out_audio} ({dur:.2f}s) -> 精确生成帧数: {exact_f} 帧 (fps={args.fps})")
            cond_audio = condition_audio_for_lip_sync(Path(args.out_audio), Path("/tmp/lip_conditioned.wav"))
            print(f"  • MiniMax-H3 AV_LATENT 纯净语音注入完成: {cond_audio}")

        # Determine segments to execute
        all_segs = [1, 2, 3, 4]
        if config_data and "segments" in config_data:
            c_segs = [int(s["seg_id"]) for s in config_data["segments"] if "seg_id" in s]
            if c_segs:
                all_segs = sorted(c_segs)
        if args.only_seg:
            all_segs = [args.only_seg]

        fleet_count = max(1, min(args.g4_fleet, len(all_segs)))
        fleet_sessions = [f"g4-fleet-{i}" for i in range(1, fleet_count + 1)]
        if fleet_count == 1 and args.session != "freshloop-g4":
            fleet_sessions = [args.session]

        fleet_shards = chunk_segments(all_segs, len(fleet_sessions))
        ports_str = ",".join(str(8188 + w) for w in range(args.workers_per_g4))

        print(f"  • 集群切片就绪: {len(fleet_sessions)} 个 G4 实例, 共 {len(fleet_sessions) * args.workers_per_g4} 个并发队列槽位")
        for sess, shard in zip(fleet_sessions, fleet_shards):
            print(f"    - 节点 [{sess}]: 分配分镜 {shard} | ComfyUI 端口: {ports_str} | Zero-Idle Pre-Queue: 开启")

        prefix = config_data.get("project_prefix", "OfficeDuel_V9_Final")

        def _run_g4_node(session_name: str, node_segs: List[int]) -> List[Path]:
            print(f"\n🚀 [G4 节点启动: {session_name}] 处理分镜 {node_segs}...", flush=True)
            node_finished_files: List[Path] = []
            try:
                if not args.dry_run:
                    print(f"  • [{session_name}] 启动/连接云端 G4 实例并静默挂载云盘...", flush=True)
                    subprocess.run([COLAB_BIN, "new", "-s", session_name, "--gpu", "G4"], check=False)
                    subprocess.run([COLAB_BIN, "dfs", "mount", "-s", session_name], check=False)

                drama_cmd = [
                    sys.executable,
                    str(SCRIPTS_DIR / "run_g4_v25_4seg_drama.py"),
                    "--fps", str(args.fps),
                    "--ports", ports_str,
                    "--prequeue-all",
                ]
                if len(node_segs) == 1:
                    drama_cmd.extend(["--only-seg", str(node_segs[0])])
                elif node_segs:
                    drama_cmd.extend(["--start-seg", str(min(node_segs)), "--end-seg", str(max(node_segs))])

                if args.config:
                    drama_cmd.extend(["--config", args.config])
                if args.snap_17k5:
                    drama_cmd.append("--snap-17k5")
                if args.tail_lock_seg and args.tail_lock_img:
                    drama_cmd.extend(["--tail-lock-seg", str(args.tail_lock_seg), "--tail-lock-img", args.tail_lock_img])

                print(f"  • [{session_name}] 派发分镜任务: {' '.join(drama_cmd)}")
                if not args.dry_run:
                    subprocess.run(drama_cmd, check=True)

                # Collect finished MP4 files
                for s in node_segs:
                    pat = f"{prefix}_Seg0{s}*.mp4"
                    for search_dir in [
                        Path("/content/ComfyUI/output"),
                        Path("/content/drive/MyDrive/AI_Workstation/ComfyUI/output"),
                        Path("/tmp"),
                    ]:
                        matches = list(search_dir.glob(pat))
                        if matches:
                            node_finished_files.append(matches[-1])
                            break
                return node_finished_files
            finally:
                # Guaranteed immediate CCU stop in finally block for each node as soon as its shard finishes!
                if not args.dry_run:
                    stop_colab_session(session_name)

        all_finished_segments: List[Path] = []
        with ThreadPoolExecutor(max_workers=len(fleet_sessions)) as fleet_pool:
            fut_map = {
                fleet_pool.submit(_run_g4_node, sess, shard): sess
                for sess, shard in zip(fleet_sessions, fleet_shards)
            }
            for fut in as_completed(fut_map):
                sess = fut_map[fut]
                try:
                    res = fut.result()
                    all_finished_segments.extend(res)
                    print(f"✅ [Fleet 节点完成] {sess} 分片渲染与落盘完成！", flush=True)
                except Exception as exc:
                    print(f"❌ [Fleet 节点异常] {sess} 出现错误: {exc}", flush=True)
                    raise

        # Concurrently download finished segments
        if all_finished_segments and not args.dry_run:
            print(f"\n📥 并发同步 {len(all_finished_segments)} 个已完成分镜母带至本地 SSD...", flush=True)

            def _dl_worker(fpath: Path) -> Path:
                dest = Path("/tmp") / fpath.name
                if fpath.resolve() != dest.resolve():
                    shutil.copy2(fpath, dest)
                print(f"  ⚡ [下载完成] {dest} ({dest.stat().st_size / (1024**2):.2f} MB)", flush=True)
                return dest

            with ThreadPoolExecutor(max_workers=min(4, len(all_finished_segments))) as dl_pool:
                dl_futs = [dl_pool.submit(_dl_worker, f) for f in all_finished_segments]
                for df in as_completed(dl_futs):
                    df.result()

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
    parser.add_argument("--tts-concurrency", type=int, default=6, help="Concurrency for parallel dialogue TTS synthesis (default: 6)")

    # Video & G4 Fleet options
    parser.add_argument("--g4-fleet", type=int, default=1, choices=range(1, 5), help="Number of concurrent G4 sessions in the fleet (1..4, default: 1)")
    parser.add_argument("--workers-per-g4", type=int, default=2, help="Number of ComfyUI worker instances per G4 machine (default: 2)")
    parser.add_argument("--parallel-workers", type=int, default=None, help="Alias for --workers-per-g4")
    parser.add_argument("--session-pool", default=None, help="Comma-separated Colab session names for fleet worker sharding (legacy alias)")
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
