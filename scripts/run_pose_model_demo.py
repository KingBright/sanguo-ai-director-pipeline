# -*- coding: utf-8 -*-
"""
POSE-DB-01 Dynamic Fashion Model Pose Showcase Generator
Uses local Strix Halo (gfx1151) MiniMax H3 (1024x576 24fps native real-time video with 768p 4-step Turbo LoRA)
+ ACE-Step 1.5 Turbo (48kHz Runway BGM via DiffSynth-Studio)
and overlays the original POSE-DB-01 mannequin cards from https://ai-pose-gallery.pages.dev/
"""
import os
import sys

# CRITICAL Strix Halo gfx1151 stability & FlashAttention flags
os.environ["TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL"] = "1"
os.environ["PYTORCH_HIP_ALLOC_CONF"] = "expandable_segments:True"
os.environ["HSA_ENABLE_SDMA"] = "0"

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import gc
import subprocess
import time
import urllib.request
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
import soundfile as sf
import torch

ROOT = Path(r"c:\Users\Liang\Downloads\sanguo")
POSE_DIR = ROOT / "assets" / "pose_db"
OUT_DIR = ROOT / "output" / "pose_demo"
FINAL_DIR = ROOT / "output" / "final_episodes"
ACESTEP_DIR = Path(r"C:\Users\Liang\minimax\ACE-Step-1.5")
MINIMAX_H3_DIR = Path(r"C:\Users\Liang\minimax\MiniMax-H3")

POSE_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)


def _get_ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def download_pose_assets():
    base = "https://ai-pose-gallery.pages.dev/"
    targets = [
        ("full_sexy_P001_front.png", "images/full_sexy/front/P001_front.png"),
        ("full_sexy_P002_front.png", "images/full_sexy/front/P002_front.png"),
        ("full_single_P017_front.png", "images/full_single/front/P017_front.png"),
        ("full_single_P018_front.png", "images/full_single/front/P018_front.png"),
        ("upper80v2_P001_front.png", "images/upper80v2/front/P001_front.png"),
        ("full_single_P001_front.png", "images/full_single/front/P001_front.png"),
    ]
    for fname, rel in targets:
        dst = POSE_DIR / fname
        if not dst.exists() or dst.stat().st_size < 1000:
            req = urllib.request.Request(base + rel, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                dst.write_bytes(r.read())
            print(f"[POSE-DB] Downloaded {fname} ({dst.stat().st_size} bytes)", flush=True)
        else:
            print(f"[POSE-DB] Cached {fname} ({dst.stat().st_size} bytes)", flush=True)


def generate_fashion_bgm(out_wav: Path, duration_sec: float = 16.0):
    if out_wav.exists() and out_wav.stat().st_size > 50000:
        print(f"[ACE-Step 1.5] Using cached BGM: {out_wav}", flush=True)
        return
    from diffsynth.core import ModelConfig
    from diffsynth.pipelines.ace_step import AceStepPipeline

    t0 = time.time()
    print("[ACE-Step 1.5] Loading AceStepPipeline (DiT=GPU bf16, OobleckVAE=Zen5 CPU fp32)...", flush=True)
    model_configs = [
        ModelConfig(path=str(ACESTEP_DIR / "acestep-v15-turbo" / "model.safetensors")),
        ModelConfig(path=str(ACESTEP_DIR / "Qwen3-Embedding-0.6B" / "model.safetensors")),
        ModelConfig(path=str(ACESTEP_DIR / "vae" / "diffusion_pytorch_model.safetensors")),
    ]
    text_tokenizer_config = ModelConfig(path=str(ACESTEP_DIR / "Qwen3-Embedding-0.6B"))
    silence_latent_config = ModelConfig(path=str(ACESTEP_DIR / "acestep-v15-turbo" / "silence_latent.pt"))

    pipe = AceStepPipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=model_configs,
        text_tokenizer_config=text_tokenizer_config,
        silence_latent_config=silence_latent_config,
    )
    # ROCm gfx1151 WDDM TDR protection: keep OobleckVAE 1D ConvTranspose on Zen 5 CPU (float32)
    pipe.vae = pipe.vae.to(device="cpu", dtype=torch.float32)
    orig_decode = pipe.vae.decode
    pipe.vae.decode = lambda z, **kw: orig_decode(z.to(device="cpu", dtype=torch.float32), **kw)
    orig_load = pipe.load_models_to_device
    pipe.load_models_to_device = lambda names: orig_load([n for n in names if n != "vae"])

    caption = (
        "Chic modern Milan fashion week runway deep house instrumental, stylish upbeat bassline, "
        "crisp electronic percussion, glossy synthesizer chords, glamorous photography studio vibe, 120 BPM"
    )
    audio_tensor = pipe(
        prompt=caption,
        lyrics="[instrumental]",
        task_type="text2music",
        duration=int(round(duration_sec)),
        bpm=120,
        keyscale="A minor",
        timesignature="4",
        vocal_language="unknown",
        num_inference_steps=8,
        cfg_scale=1.0,
        seed=2026,
    )
    audio_np = audio_tensor.detach().cpu().float().numpy()
    if audio_np.ndim == 3:
        audio_np = audio_np[0]
    if audio_np.ndim == 2:
        audio_np = audio_np.T  # [T, C]
    audio_int16 = np.clip(audio_np * 32767.0, -32768, 32767).astype(np.int16)
    wavfile.write(str(out_wav), 48000, audio_int16)
    del pipe
    gc.collect()
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    print(f"[ACE-Step 1.5] Saved runway BGM -> {out_wav} ({out_wav.stat().st_size} bytes in {time.time() - t0:.1f}s)", flush=True)


def render_model_pose_shots(bgm_wav: Path):
    from diffsynth.core import ModelConfig
    from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline
    from diffsynth.utils.data import save_video

    # Consistent model appearance anchor across all 4 pose transitions
    model_identity = (
        "Photorealistic 4K live-action high-fashion commercial video, 24fps real-time natural motion, "
        "a stunning 22-year-old East Asian female supermodel with a delicate symmetrical V-shaped face, "
        "radiant fair skin, expressive dark almond eyes, glossy long wavy dark-brown hair, "
        "wearing an elegant fitted off-shoulder white silk blouse and high-waisted tailored black flared trousers, "
        "inside a luxury Milan fashion photography studio with warm golden rim lighting, softbox key light, and creamy bokeh background, "
        "shot on Sony Venice 85mm f/1.4 master prime lens, ultra-sharp facial features and fabric texture. "
    )

    shots = [
        {
            "id": "shot01_scurve_hips",
            "pose_code": "POSE-DB #001 (S字立ち) → #018 (両手を腰に)",
            "pose_img": POSE_DIR / "full_single_P018_front.png",
            "seed": 101,
            "prompt": (
                model_identity
                + "Medium full shot, front eye-level angle. The beautiful female model stands in a confident S-curve runway pose, "
                "smoothly shifts her weight onto her left hip, places both hands gracefully on her waist, "
                "tilts her chin slightly up, and gives a captivating confident smile directly into the camera lens as studio strobe lights softly flash."
            ),
        },
        {
            "id": "shot02_lookback_hair",
            "pose_code": "POSE-DB #017 (肩越しに振り向く) → #002 (髪をかき上げる)",
            "pose_img": POSE_DIR / "full_single_P017_front.png",
            "seed": 202,
            "prompt": (
                model_identity
                + "Medium shot, three-quarter profile angle. The stunning female model turns gracefully and looks back over her shoulder at the camera "
                "with charming expressive eyes, then slowly raises both hands to sweep up her glossy long wavy dark-brown hair behind her neck, "
                "arching her back slightly in an elegant model pose."
            ),
        },
        {
            "id": "shot03_upper_heart_wink",
            "pose_code": "POSE-DB Upper #001 (胸の前で両手ハート・小顔ポーズ)",
            "pose_img": POSE_DIR / "upper80v2_P001_front.png",
            "seed": 303,
            "prompt": (
                model_identity
                + "Medium close-up portrait shot, eye-level 85mm f/1.4 shallow depth of field. "
                "The gorgeous female model playfully tilts her head toward the camera, brings both hands up in front of her chest to form a cute finger heart gesture, "
                "and gives a sweet radiant smile and playful wink to the lens, her long wavy hair swaying gently in the studio breeze."
            ),
        },
        {
            "id": "shot04_seated_orbit",
            "pose_code": "POSE-DB #001 (仰け反り座り・片膝立て) × 5-Angle Orbit",
            "pose_img": POSE_DIR / "full_single_P001_front.png",
            "seed": 404,
            "prompt": (
                model_identity
                + "Medium full shot, smooth cinematic camera orbit from slightly low angle to front angle. "
                "The elegant female model sits gracefully on a minimalist white studio cube, leaning slightly back on one hand with one knee raised, "
                "smoothly crossing her long legs and adjusting her collar while gazing into the camera with high-fashion poise."
            ),
        },
    ]

    if all((OUT_DIR / f"{s['id']}.mp4").exists() and (OUT_DIR / f"{s['id']}.mp4").stat().st_size > 150000 for s in shots):
        print("[MiniMax H3] All 4 shots already cached! Skipping model load.", flush=True)
        return [(s, OUT_DIR / f"{s['id']}.mp4") for s in shots]

    t0 = time.time()
    print("[MiniMax H3] Loading INT8 DiT + Qwen3VL-32B TextEncoder + VideoVAE + CPU AudioVAE + 768p Turbo LoRA...", flush=True)
    model_configs = [
        ModelConfig(path=str(MINIMAX_H3_DIR / "diffusion_models" / "minimax_h3_fl2va_pruned_int8_convrot.safetensors")),
        ModelConfig(path=str(MINIMAX_H3_DIR / "text_encoders" / "qwen3vl_32b_minimax_h3_int8_convrot.safetensors")),
        ModelConfig(path=str(MINIMAX_H3_DIR / "vae" / "minimax_h3_video_vae_fp16.safetensors")),
        ModelConfig(path=str(MINIMAX_H3_DIR / "vae" / "minimax_h3_audio_vae_fp32.safetensors")),
    ]
    processor_config = ModelConfig(path=str(MINIMAX_H3_DIR / "processor"))

    pipe = MiniMaxH3Pipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=model_configs,
        processor_config=processor_config,
        redirect_common_files=False,
    )
    lora_path = MINIMAX_H3_DIR / "loras" / "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
    if lora_path.exists():
        pipe.load_lora(pipe.dit, str(lora_path), alpha=1.0)
    print(f"[MiniMax H3] Pipeline loaded in {time.time() - t0:.1f}s!", flush=True)

    negative_prompt = (
        "bad quality, blurry, out of focus, low resolution, distorted face, deformed hands, extra fingers, "
        "text, watermark, subtitles, slow motion, static image"
    )

    bgm_np, bgm_sr = sf.read(str(bgm_wav), dtype="float32")
    render_w, render_h, n_frames, fps = 1024, 576, 73, 24
    clip_dur = n_frames / float(fps)  # 3.0416s

    rendered_clips = []
    for idx, s in enumerate(shots):
        out_mp4 = OUT_DIR / f"{s['id']}.mp4"
        if out_mp4.exists() and out_mp4.stat().st_size > 150000:
            print(f"[MiniMax H3] Using cached {out_mp4.name}", flush=True)
            rendered_clips.append((s, out_mp4))
            continue

        i0 = int(round(idx * clip_dur * bgm_sr))
        i1 = int(round((idx + 1) * clip_dur * bgm_sr))
        slice_np = bgm_np[i0:i1]
        target_len = int(round(clip_dur * bgm_sr))
        if len(slice_np) < target_len:
            pad_width = ((0, target_len - len(slice_np)), (0, 0)) if slice_np.ndim == 2 else (0, target_len - len(slice_np))
            slice_np = np.pad(slice_np, pad_width)
        else:
            slice_np = slice_np[:target_len]
        if slice_np.ndim == 1:
            slice_np = np.stack([slice_np, slice_np], axis=0)
        else:
            slice_np = slice_np.T
        retake_audio_tensor = torch.from_numpy(slice_np.astype(np.float32))

        print(f"[MiniMax H3] Rendering {s['id']} ({s['pose_code']}) @ {render_w}x{render_h}, {n_frames}f (24fps)...", flush=True)
        t_s = time.time()
        video_frames, _ = pipe(
            prompt=s["prompt"],
            negative_prompt=negative_prompt,
            height=render_h,
            width=render_w,
            num_frames=n_frames,
            num_inference_steps=4,
            cfg_scale=1.0,
            flow_shift=12.0,
            audio_flow_shift=3.0,
            keyframes=None,  # Pure T2VA/A2V so we never trigger MIOpen 3D-Conv encode_video NaN on gfx1151
            keyframe_indices=None,
            retake_audio=retake_audio_tensor,
            retake_audio_sample_rate=bgm_sr,
            seconds_regions_to_retake=[],
            seed=s["seed"],
        )
        arr = np.array([np.array(f) for f in video_frames[:5]])
        print(f"  -> Frame check mean={arr.mean():.1f}, max={arr.max()} ({time.time() - t_s:.1f}s)", flush=True)
        save_video(video_frames, str(out_mp4), fps=fps, quality=9)
        rendered_clips.append((s, out_mp4))
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    del pipe
    gc.collect()
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    return rendered_clips


def master_showcase_video(rendered_clips, bgm_wav: Path):
    ffmpeg_exe = _get_ffmpeg_exe()
    norm_clips = []
    for idx, (s, raw_mp4) in enumerate(rendered_clips):
        norm_mp4 = OUT_DIR / f"norm_{s['id']}.mp4"
        pose_png = s["pose_img"]
        # Overlay the POSE-DB-01 mannequin card in bottom-right corner (180x225 with white border)
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(raw_mp4),
            "-i", str(pose_png),
            "-filter_complex",
            (
                "[0:v]scale=1280:720:flags=lanczos,unsharp=5:5:0.8:5:5:0.0,fps=24,format=yuv420p[base];"
                "[1:v]scale=176:220:flags=lanczos,pad=184:228:4:4:color=white[pip];"
                "[base][pip]overlay=W-w-28:H-h-28,format=yuv420p[vout]"
            ),
            "-map", "[vout]",
            "-an",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16",
            str(norm_mp4),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg overlay failed ({res.returncode}):\n{res.stderr[-800:]}")
        norm_clips.append((s, norm_mp4))

    concat_txt = OUT_DIR / "concat.txt"
    concat_txt.write_text(
        "\n".join([f"file '{p.resolve().as_posix()}'" for _, p in norm_clips]),
        encoding="utf-8",
    )
    joined_mp4 = OUT_DIR / "joined_silent.mp4"
    subprocess.run(
        [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(joined_mp4)],
        check=True,
        capture_output=True,
    )

    ass_path = OUT_DIR / "pose_labels.ass"
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Tag,Microsoft YaHei,30,&H00FFFFFF,&H0000FFFF,&H55000000,&H99000000,-1,0,0,0,100,100,1,0,3,10,0,7,28,28,26,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        "Dialogue: 0,0:00:00.05,0:00:03.00,Tag,,0,0,0,,POSE-DB-01 实验 · 动作1：S字站姿 → 双手叉腰 (P001→P018)",
        "Dialogue: 0,0:00:03.05,0:00:06.05,Tag,,0,0,0,,POSE-DB-01 实验 · 动作2：回眸一笑 → 双手撩发 (P017→P002)",
        "Dialogue: 0,0:00:06.10,0:00:09.10,Tag,,0,0,0,,POSE-DB-01 实验 · 动作3：上半身特写 · 胸前比心眨眼 (Upper-P001)",
        "Dialogue: 0,0:00:09.15,0:00:12.15,Tag,,0,0,0,,POSE-DB-01 实验 · 动作4：单膝立坐姿 × 镜头环绕 (Full-P001)",
    ]
    ass_path.write_text("\n".join(ass_lines), encoding="utf-8-sig")

    final_mp4 = FINAL_DIR / "pose_db_model_showcase_master.mp4"
    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    cmd_master = [
        ffmpeg_exe, "-y",
        "-i", str(joined_mp4),
        "-i", str(bgm_wav),
        "-filter_complex",
        (
            f"[0:v]ass='{ass_escaped}'[vout];"
            "[1:a]aresample=48000,afade=t=in:st=0:d=0.4,afade=t=out:st=11.0:d=1.1,volume=0.85[aout]"
        ),
        "-map", "[vout]",
        "-map", "[aout]",
        "-shortest",
        "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(final_mp4),
    ]
    res2 = subprocess.run(cmd_master, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res2.returncode != 0:
        raise RuntimeError(f"FFmpeg master failed ({res2.returncode}):\n{res2.stderr[-800:]}")
    print(f"[MASTER] Completed -> {final_mp4} ({final_mp4.stat().st_size} bytes)", flush=True)
    return final_mp4


if __name__ == "__main__":
    download_pose_assets()
    bgm_wav = OUT_DIR / "fashion_runway_bgm.wav"
    generate_fashion_bgm(bgm_wav, duration_sec=16.0)
    clips = render_model_pose_shots(bgm_wav)
    final_mp4 = master_showcase_video(clips, bgm_wav)

    ffmpeg_exe = _get_ffmpeg_exe()
    for idx, t_sec in enumerate([1.5, 4.5, 7.5, 10.5], start=1):
        jpg = OUT_DIR / f"verify_shot{idx}.jpg"
        subprocess.run(
            [ffmpeg_exe, "-y", "-ss", str(t_sec), "-i", str(final_mp4), "-frames:v", "1", "-q:v", "2", str(jpg)],
            check=True,
            capture_output=True,
        )
        print(f"[VERIFY] Extracted {jpg.name}", flush=True)
