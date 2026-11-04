# -*- coding: utf-8 -*-
"""
Organic Multi-Anchor Gravure & High-Fashion Model Video Showcase
Integrates:
  1. POSE-DB-01 Gravure/Allure Category (`全身1人・セクシー系` P001, P002, P003, P016, P026, P047, P053)
  2. Multi-Keyframe Trajectory Anchoring (`keyframes=[start, mid, end]`, `keyframe_indices=[0, 36, -1]`)
     encoded on Zen 5 CPU (float32) for 100% NaN-free conditioning on Strix Halo (gfx1151)
  3. Reference Identity Locking (`references=[{"type": "image", ...}]`)
  4. MiniMax H3 (1024x576 @ 24fps real-time 1.0x speed, 4-step 768p Turbo LoRA)
  5. ACE-Step 1.5 Turbo (Sultry R&B / Fashion Lounge 48kHz Stereo Soundtrack)
"""
import gc
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ["TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL"] = "1"
os.environ["PYTORCH_HIP_ALLOC_CONF"] = "expandable_segments:True"
os.environ["HSA_ENABLE_SDMA"] = "0"

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import scipy.io.wavfile as wavfile
import soundfile as sf
import torch
from PIL import Image

ROOT = Path(r"c:\Users\Liang\Downloads\sanguo")
POSE_DIR = ROOT / "assets" / "pose_db"
OUT_DIR = ROOT / "output" / "pose_gravure"
ANCHOR_DIR = OUT_DIR / "anchors"
FINAL_DIR = ROOT / "output" / "final_episodes"
ACESTEP_DIR = Path(r"C:\Users\Liang\minimax\ACE-Step-1.5")
MINIMAX_H3_DIR = Path(r"C:\Users\Liang\minimax\MiniMax-H3")

OUT_DIR.mkdir(parents=True, exist_ok=True)
ANCHOR_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)


def _get_ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def generate_sultry_bgm(out_wav: Path, duration_sec: float = 16.0):
    if out_wav.exists() and out_wav.stat().st_size > 50000:
        print(f"[ACE-Step 1.5] Using cached sultry BGM: {out_wav}", flush=True)
        return
    from diffsynth.core import ModelConfig
    from diffsynth.pipelines.ace_step import AceStepPipeline

    t0 = time.time()
    print("[ACE-Step 1.5] Generating sultry R&B / luxury fashion lounge soundtrack...", flush=True)
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
    pipe.vae = pipe.vae.to(device="cpu", dtype=torch.float32)
    orig_decode = pipe.vae.decode
    pipe.vae.decode = lambda z, **kw: orig_decode(z.to(device="cpu", dtype=torch.float32), **kw)
    orig_load = pipe.load_models_to_device
    pipe.load_models_to_device = lambda names: orig_load([n for n in names if n != "vae"])

    caption = (
        "Sultry sensual modern R&B slow jam and luxury fashion lounge beat, deep velvety sub-bass, "
        "warm Rhodes electric piano chords, crisp finger snaps, seductive late-night penthouse atmosphere, 96 BPM"
    )
    audio_tensor = pipe(
        prompt=caption,
        lyrics="[instrumental]",
        task_type="text2music",
        duration=int(round(duration_sec)),
        bpm=96,
        keyscale="F# minor",
        timesignature="4",
        vocal_language="unknown",
        num_inference_steps=8,
        cfg_scale=1.0,
        seed=888,
    )
    audio_np = audio_tensor.detach().cpu().float().numpy()
    if audio_np.ndim == 3:
        audio_np = audio_np[0]
    if audio_np.ndim == 2:
        audio_np = audio_np.T
    audio_int16 = np.clip(audio_np * 32767.0, -32768, 32767).astype(np.int16)
    wavfile.write(str(out_wav), 48000, audio_int16)
    del pipe
    gc.collect()
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    print(f"[ACE-Step 1.5] Saved sultry BGM -> {out_wav} ({out_wav.stat().st_size} bytes in {time.time() - t0:.1f}s)", flush=True)


def render_multi_anchor_gravure_shots(bgm_wav: Path):
    from diffsynth.core import ModelConfig
    from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline
    from diffsynth.utils.data import save_video

    a1 = Image.open(ANCHOR_DIR / "anchor_01_P001_scurve.png").convert("RGB")
    a2 = Image.open(ANCHOR_DIR / "anchor_02_P002_arch_hair.png").convert("RGB")
    a3 = Image.open(ANCHOR_DIR / "anchor_03_P003_lookback.png").convert("RGB")
    a4 = Image.open(ANCHOR_DIR / "anchor_04_P016_sidesit.png").convert("RGB")
    a5 = Image.open(ANCHOR_DIR / "anchor_05_P026_sidesit_hair.png").convert("RGB")
    a6 = Image.open(ANCHOR_DIR / "anchor_06_P053_recline.png").convert("RGB")

    model_identity = (
        "Photorealistic 4K live-action luxury gravure fashion film, 24fps real-time fluid motion, "
        "a breathtakingly beautiful 23-year-old East Asian female supermodel with a delicate V-shaped face, "
        "sultry expressive almond eyes, glossy coral-red lips, silky long dark-brown wavy hair, "
        "hourglass figure, radiant fair porcelain skin with warm golden rim light sheen, "
        "wearing a form-fitting burgundy-red silk satin slip dress with thin spaghetti straps and high side slit, "
        "inside a dimly-lit warm golden-hour penthouse studio with a cream velvet lounge sofa and dreamy bokeh lights, "
        "shot on Sony Venice 85mm f/1.4 master prime lens. "
    )

    shots = [
        {
            "id": "gravure_shot01_standing_3anchors",
            "title": "镜头1 [三锚点连续变姿]：S字挺胯(P001) → 反弓撩发(P002) → 回眸挺臀(P003)",
            "keyframes": [a1, a2, a3],
            "keyframe_indices": [0, 36, -1],
            "pose_cards": [
                POSE_DIR / "full_sexy_P001_front.png",
                POSE_DIR / "full_sexy_P002_front.png",
                POSE_DIR / "full_sexy_P003_front.png",
            ],
            "seed": 501,
            "prompt": (
                model_identity
                + "Medium-full shot. The alluring female model starts in a seductive S-curve standing pose with one hand on her hip and one hand on her head, "
                "then smoothly arches her back and raises both arms to sweep up her long glossy wavy dark-brown hair, "
                "and finally turns 3/4 around to look back over her shoulder with a captivating sultry gaze while accentuating her waist and hip curve."
            ),
        },
        {
            "id": "gravure_shot02_velvet_sidesit_anchors",
            "title": "镜头2 [首尾双锚点过渡]：美人鱼侧坐曲线(P016) → 挺胸双手撩发(P026)",
            "keyframes": [a4, a5],
            "keyframe_indices": [0, -1],
            "pose_cards": [
                POSE_DIR / "full_sexy_P016_front.png",
                POSE_DIR / "full_sexy_P026_front.png",
            ],
            "seed": 502,
            "prompt": (
                model_identity
                + "Medium-full shot on a cream velvet lounge sofa. The gorgeous female model sits in an alluring mermaid side-sit pose propping one hand on the velvet sofa, "
                "then gracefully lifts both arms behind her head to sweep up her long wavy hair while arching her back and chest softly toward the camera with a seductive smile."
            ),
        },
        {
            "id": "gravure_shot03_velvet_recline_anchors",
            "title": "镜头3 [跨姿态运镜过渡]：天鹅绒侧坐撩发(P026) → 侧卧托腮抬膝诱惑姿态(P053)",
            "keyframes": [a5, a6],
            "keyframe_indices": [0, -1],
            "pose_cards": [
                POSE_DIR / "full_sexy_P026_front.png",
                POSE_DIR / "full_sexy_P053_front.png",
            ],
            "seed": 503,
            "prompt": (
                model_identity
                + "Medium-full camera tracking shot on the cream velvet bed. The stunning female model lowers herself gracefully onto her side on the velvet lounge bed, "
                "propping her head on her left hand, raising her right knee seductively with her right hand resting on her knee, gazing intimately into the lens."
            ),
        },
        {
            "id": "gravure_shot04_ref_closeup_allure",
            "title": "镜头4 [身份锚定+推轨特写]：俯身扶膝深邃凝视(P004) → 俯卧托腮翘腿眨眼(P047)",
            "keyframes": [a6],
            "keyframe_indices": [0],
            "pose_cards": [
                POSE_DIR / "full_sexy_P047_front.png",
            ],
            "seed": 504,
            "prompt": (
                model_identity
                + "Slow cinematic push-in close-up shot on the cream velvet bed. Starting from her side-reclining pose, the breathtaking model rolls smoothly onto her stomach, "
                "cups her cheeks playfully in both hands with elbows propped on the velvet cushion, kicks her slender calves up behind her, and gives an irresistible sultry wink and kiss toward the camera."
            ),
        },
    ]

    if all((OUT_DIR / f"{s['id']}.mp4").exists() and (OUT_DIR / f"{s['id']}.mp4").stat().st_size > 150000 for s in shots):
        print("[MiniMax H3] All 4 gravure multi-anchor shots cached! Skipping model load.", flush=True)
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
        "bad anatomy, text, watermark, subtitles, slow motion, static image"
    )

    bgm_np, bgm_sr = sf.read(str(bgm_wav), dtype="float32")
    render_w, render_h, n_frames, fps = 1024, 576, 73, 24
    clip_dur = n_frames / float(fps)

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

        print(
            f"[MiniMax H3] Rendering {s['id']} | anchors={s['keyframe_indices']} @ {render_w}x{render_h}, {n_frames}f (24fps)...",
            flush=True,
        )
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
            keyframes=s["keyframes"],
            keyframe_indices=s["keyframe_indices"],
            retake_audio=retake_audio_tensor,
            retake_audio_sample_rate=bgm_sr,
            seconds_regions_to_retake=[],
            seed=s["seed"],
        )
        arr = np.array([np.array(f) for f in video_frames[:5]])
        print(f"  -> Frame check mean={arr.mean():.1f}, max={arr.max()} ({time.time() - t_s:.1f}s)", flush=True)
        if arr.mean() < 5.0 or arr.max() == 0:
            raise RuntimeError(f"Black/NaN frame detected in {s['id']} (mean={arr.mean():.1f}, max={arr.max()})!")
        save_video(video_frames, str(out_mp4), fps=fps, quality=9)
        rendered_clips.append((s, out_mp4))
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    del pipe
    gc.collect()
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    return rendered_clips


def make_pose_strip_png(pose_cards: list[Path], out_png: Path):
    """Combine 1-3 POSE-DB mannequin cards horizontally into a clean PiP reference badge."""
    cards = [Image.open(p).convert("RGB").resize((135, 180), Image.LANCZOS) for p in pose_cards]
    pad = 6
    total_w = len(cards) * 135 + (len(cards) + 1) * pad
    total_h = 180 + 2 * pad
    canvas = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    for i, c in enumerate(cards):
        canvas.paste(c, (pad + i * (135 + pad), pad))
    canvas.save(out_png)
    return out_png


def master_gravure_showcase(rendered_clips, bgm_wav: Path):
    ffmpeg_exe = _get_ffmpeg_exe()
    norm_clips = []
    for idx, (s, raw_mp4) in enumerate(rendered_clips):
        norm_mp4 = OUT_DIR / f"norm_{s['id']}.mp4"
        strip_png = OUT_DIR / f"strip_{s['id']}.png"
        make_pose_strip_png(s["pose_cards"], strip_png)

        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(raw_mp4),
            "-i", str(strip_png),
            "-filter_complex",
            (
                "[0:v]scale=1280:720:flags=lanczos,unsharp=5:5:0.8:5:5:0.0,fps=24,format=yuv420p[base];"
                "[base][1:v]overlay=W-w-24:H-h-24,format=yuv420p[vout]"
            ),
            "-map", "[vout]",
            "-an",
            "-c:v", "libx264", "-preset", "fast", "-crf", "15",
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

    ass_path = OUT_DIR / "gravure_labels.ass"
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
        "Style: Tag,Microsoft YaHei,28,&H00FFFFFF,&H0000FFFF,&H55000000,&H99000000,-1,0,0,0,100,100,1,0,3,10,0,7,26,26,24,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        "Dialogue: 0,0:00:00.05,0:00:03.00,Tag,,0,0,0,,镜头1 [首/中/尾三锚点 0→36→72]：S字挺胯(P001) → 反弓撩发(P002) → 回眸挺臀(P003)",
        "Dialogue: 0,0:00:03.05,0:00:06.05,Tag,,0,0,0,,镜头2 [首尾双锚点 0→72]：天鹅绒美人鱼侧坐(P016) → 挺胸双手撩发(P026)",
        "Dialogue: 0,0:00:06.10,0:00:09.10,Tag,,0,0,0,,镜头3 [跨姿态运镜 0→72]：侧坐撩发(P026) → 侧卧托腮抬膝诱惑姿态(P053)",
        "Dialogue: 0,0:00:09.15,0:00:12.15,Tag,,0,0,0,,镜头4 [首帧锚定+推轨特写]：侧卧诱惑(P053) → 俯卧托腮翘小腿眨眼(P047)",
    ]
    ass_path.write_text("\n".join(ass_lines), encoding="utf-8-sig")

    final_mp4 = FINAL_DIR / "pose_db_gravure_multi_anchor_master.mp4"
    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    cmd_master = [
        ffmpeg_exe, "-y",
        "-i", str(joined_mp4),
        "-i", str(bgm_wav),
        "-filter_complex",
        (
            f"[0:v]ass='{ass_escaped}'[vout];"
            "[1:a]aresample=48000,afade=t=in:st=0:d=0.4,afade=t=out:st=11.0:d=1.1,volume=0.88[aout]"
        ),
        "-map", "[vout]",
        "-map", "[aout]",
        "-shortest",
        "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(final_mp4),
    ]
    res2 = subprocess.run(cmd_master, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res2.returncode != 0:
        raise RuntimeError(f"FFmpeg master failed ({res2.returncode}):\n{res2.stderr[-800:]}")
    print(f"[MASTER] Completed -> {final_mp4} ({final_mp4.stat().st_size} bytes)", flush=True)
    return final_mp4


if __name__ == "__main__":
    bgm_wav = OUT_DIR / "sultry_lounge_bgm.wav"
    generate_sultry_bgm(bgm_wav, duration_sec=16.0)
    clips = render_multi_anchor_gravure_shots(bgm_wav)
    final_mp4 = master_gravure_showcase(clips, bgm_wav)

    ffmpeg_exe = _get_ffmpeg_exe()
    for idx, t_sec in enumerate([0.4, 1.5, 2.8, 4.5, 7.5, 10.6], start=1):
        jpg = OUT_DIR / f"verify_gravure_{idx}.jpg"
        subprocess.run(
            [ffmpeg_exe, "-y", "-ss", str(t_sec), "-i", str(final_mp4), "-frames:v", "1", "-q:v", "2", str(jpg)],
            check=True,
            capture_output=True,
        )
        print(f"[VERIFY] Extracted {jpg.name} (t={t_sec}s)", flush=True)
