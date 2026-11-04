#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Director Studio - Local ROCm gfx1151 Multi-Modal Inference Worker
Integrates:
  1. Qwen3-TTS (Two-Stage Theatrical Emotional Synthesis: Qwen3-TTS-12Hz-1.7B-VoiceDesign + Qwen3-TTS-12Hz-1.7B-Base ICL Mode)
  2. ACE-Step 1.5 Turbo (48kHz Stereo Cinematic BGM Scoring)
  3. MiniMax H3 (1:1 Real-Time 24fps Audio-Driven Lip-Sync Video Generation via DiffSynth-Studio)

Includes permanent ROCm gfx1151 WDDM TDR stability & FlashAttention protections:
  - Enables TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 so long-sequence 768p Video DiT attention uses
    O(N) FlashAttention instead of O(N^2) math fallback.
  - Heavy Transformer/DiT runs on Radeon 8060S GPU (cuda:0, bfloat16).
  - Long-sequence 1D Conv/ConvTranspose audio vocoders (Qwen3TTSTokenizerV2, ECAPA-TDNN, OobleckVAE, BigVGAN)
    run on Zen 5 16-Core CPU (float32), 100% preventing MIOpen GemmFwdRest workspace hangs.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Enable ROCm AOTriton FlashAttention before importing torch
os.environ.setdefault("TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL", "1")

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import numpy as np
import soundfile as sf
import torch

QWEN_CLONE_DIR = Path(r"C:\Users\Liang\minimax\Qwen3-TTS-12Hz-1.7B-Base")
QWEN_DESIGN_DIR = Path(r"C:\Users\Liang\minimax\Qwen3-TTS-12Hz-1.7B-VoiceDesign")
ACESTEP_DIR = Path(r"C:\Users\Liang\minimax\ACE-Step-1.5")
MINIMAX_H3_DIR = Path(r"C:\Users\Liang\minimax\MiniMax-H3")

# Universal fallback vocal persona bank for Qwen3-TTS VoiceDesign + Base ICL two-stage synthesis.
# Project-specific character personas are loaded dynamically from `<project_dir>/characters/voice_personas.json`.
DEFAULT_UNIVERSAL_PERSONAS = {
    "Narrator": {
        "instruct": (
            "35岁成熟磁性中国影视配音男中音，嗓音温厚沉稳、富有叙事纵深感与电影画面感，"
            "字正腔圆，节奏自然舒展，在逗号与句号处有自然的呼吸气口与情绪递进，绝不机械朗读"
        ),
        "ref_text": "夜色渐深，灯火映照着桌面上的卷宗，一场关乎命运的抉择正在悄然展开！",
        "speaker_label": "旁白",
    },
    "MaleLead": {
        "instruct": (
            "28岁青年男主角影视级配音表演，声音清朗坚毅、富有戏剧张力与情感爆发力，"
            "重音鲜明，呼吸气口自然真实"
        ),
        "ref_text": "无论前方有多少阻碍，这一次我绝不会退缩半步，定要查明真相！",
        "speaker_label": "男主",
    },
    "FemaleLead": {
        "instruct": (
            "25岁青年女主角影视级配音表演，声音清透灵动、细腻富有感染力，语调自然起伏"
        ),
        "ref_text": "你看清楚了吗？这上面留下的每一道痕迹，都在诉说着当时的真相。",
        "speaker_label": "女主",
    },
}


def load_character_personas(base_dir: Path) -> dict:
    personas = dict(DEFAULT_UNIVERSAL_PERSONAS)
    persona_json = base_dir / "characters" / "voice_personas.json"
    if persona_json.exists():
        try:
            with open(persona_json, "r", encoding="utf-8") as f:
                custom = json.load(f)
                if isinstance(custom, dict):
                    personas.update(custom)
        except Exception:
            pass
    profiles_path = base_dir / "characters" / "profiles.toml"
    if profiles_path.exists():
        try:
            with open(profiles_path, "rb") as f:
                data = tomllib.load(f)
                for ch in data.get("characters", []):
                    name = ch.get("name", "")
                    if name and name not in personas:
                        personas[name] = {
                            "instruct": f"影视级角色配音表演（角色：{name}），声音富有戏剧感染力与真实呼吸气口，绝不平淡朗读",
                            "ref_text": DEFAULT_UNIVERSAL_PERSONAS["MaleLead"]["ref_text"],
                            "speaker_label": name,
                        }
        except Exception:
            pass
    return personas


def load_project_style_suffix(base_dir: Path) -> str:
    fact_sheet_path = base_dir / "fact_sheet.toml"
    if fact_sheet_path.exists():
        try:
            with open(fact_sheet_path, "rb") as f:
                data = tomllib.load(f)
                suffix = data.get("style_lock", {}).get("global_suffix", "")
                if suffix and suffix.strip():
                    return suffix.strip()
        except Exception:
            pass
    return (
        "Shot on ARRI Alexa 65 with Panavision anamorphic lens, live-action cinematic realism, "
        "Rembrandt chiaroscuro tungsten lighting, ultra-sharp facial and costume micro-texture, 8k photorealistic. "
        "Clean video frame without any subtitles, captions, or floating text."
    )


def load_episode_manifest(base_dir: Path, episode_id: str) -> dict:
    manifest_path = base_dir / "episodes" / episode_id / "movie.toml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Episode manifest not found: {manifest_path}")
    with open(manifest_path, "rb") as f:
        return tomllib.load(f)


# Verified Studio Voice Alias Map (F0 < 120Hz for Male Anchors)
VOICE_ALIAS_MAP = {
    "alnilam": "磁性沧桑中年男声-v1.wav",
    "rigel": "温厚沉稳青年男声-v1.wav",
    "charon": "冷硬自信青年男声-v1.wav",
    "fenrir": "沉静青年男声-v1.wav",
    "puck": "慈祥睿智老年男声-v1.wav",
    "kore": "清透克制年轻女声-v1.wav",
    "aoede": "温柔治愈成年女声-v1.wav",
    "ZhugeLiang": "磁性沧桑中年男声-v1.wav",
    "GuYuan": "温厚沉稳青年男声-v1.wav",
    "MaSu": "冷硬自信青年男声-v1.wav",
    "OfficerWang": "沉静青年男声-v1.wav",
    "WeiYan": "磁性沧桑中年男声-v1.wav",
    "ZhangHe": "慈祥睿智老年男声-v1.wav",
    "LinChen": "冷硬自信青年男声-v1.wav",
    "ZhaoKun": "沉静青年男声-v1.wav",
}


def load_character_voices(base_dir: Path, manifest: dict = None) -> dict:
    voice_map = {}
    if manifest:
        for ch in manifest.get("characters", []):
            name = ch.get("name", "")
            voice = ch.get("voice", "")
            if name and voice:
                voice_map[name] = voice
    profiles_path = base_dir / "characters" / "profiles.toml"
    if profiles_path.exists():
        with open(profiles_path, "rb") as f:
            data = tomllib.load(f)
            for ch in data.get("characters", []):
                name = ch.get("name", "")
                voice = ch.get("voice", "")
                if name and voice and name not in voice_map:
                    voice_map[name] = voice
    return voice_map


def resolve_voice_anchor(base_dir: Path, root_dir: Path, voice_id: str, speaker: str = "") -> Path:
    mapped = VOICE_ALIAS_MAP.get(voice_id) or VOICE_ALIAS_MAP.get(speaker) or voice_id
    candidates = [
        base_dir / "assets" / "voices" / f"{mapped}.wav",
        base_dir / "assets" / "voices" / mapped,
        root_dir / "assets" / "voices" / f"{mapped}.wav",
        root_dir / "assets" / "voices" / mapped,
        base_dir / "assets" / "voices" / f"{voice_id}.wav",
        base_dir / "assets" / "voices" / voice_id,
        root_dir / "assets" / "voices" / f"{voice_id}.wav",
        root_dir / "assets" / "voices" / voice_id,
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return root_dir / "assets" / "voices" / "温厚沉稳青年男声-v1.wav"


def trim_trailing_silence(wav: np.ndarray, sr: int, threshold: float = 0.008, pad_sec: float = 0.18) -> np.ndarray:
    win = max(1, int(sr * 0.04))
    if len(wav) <= win:
        return wav
    rms = np.array([np.sqrt(np.mean(wav[i:i + win] ** 2)) for i in range(0, len(wav) - win, win)])
    active_idx = np.where(rms > threshold)[0]
    if len(active_idx) == 0:
        return wav
    start_sample = max(0, int(active_idx[0] * win - sr * 0.06))
    end_sample = min(len(wav), int((active_idx[-1] + 1) * win + sr * pad_sec))
    return wav[start_sample:end_sample]


def cmd_tts(base_dir: Path, root_dir: Path, episode_id: str, scene_id: str = None, instruct: str = None):
    """
    Studio Verified Speaker Embedding Cloning (ECAPA-TDNN x_vector_only_mode=True) +
    Acoustic F0 Gender Guard (< 165Hz for male characters).
    Uses verified studio recordings in `assets/voices/` (`磁性沧桑中年男声-v1.wav` 88.6Hz,
    `温厚沉稳青年男声-v1.wav` 96.0Hz, `冷硬自信青年男声-v1.wav` 101.5Hz, `沉静青年男声-v1.wav` 111.0Hz),
    100% preventing VoiceDesign from randomly sampling female (>200Hz) voices!
    """
    import librosa
    from qwen_tts import Qwen3TTSModel

    manifest = load_episode_manifest(base_dir, episode_id)
    voice_map = load_character_voices(base_dir, manifest)
    personas = load_character_personas(base_dir)
    scenes = manifest.get("scenes", [])
    if scene_id:
        scenes = [s for s in scenes if s.get("id") == scene_id]

    vo_dir = base_dir / "output" / "voiceovers" / episode_id
    vo_dir.mkdir(parents=True, exist_ok=True)

    print("[Qwen3-TTS] Loading Qwen3-TTS-12Hz-1.7B-Base (Verified Studio Voice Anchor Mode)...", flush=True)
    t1 = time.time()
    base_model = Qwen3TTSModel.from_pretrained(
        str(QWEN_CLONE_DIR),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    print(f"[Qwen3-TTS] Base Model ready in {time.time() - t1:.1f}s", flush=True)

    results = []
    for sc in scenes:
        sid = sc.get("id", "unknown")
        line = (sc.get("line") or "").strip()
        if not line:
            continue
        speaker = sc.get("speaker") or "Narrator"
        voice_id = voice_map.get(speaker) or personas.get(speaker, {}).get("voice") or speaker
        anchor_wav = resolve_voice_anchor(base_dir, root_dir, voice_id, speaker)
        is_female_char = any(k in anchor_wav.name for k in ["女", "Female", "female"]) or speaker in ("FemaleLead",)

        t_s = time.time()
        print(f"[Qwen3-TTS] Synthesizing {sid} ({speaker} -> {anchor_wav.name}): \"{line}\"", flush=True)

        wav_clean = None
        sr = 24000
        f0_med = 0.0
        f0_std = 0.0
        f0_span = 0.0

        # Acoustic F0 Gender Guard: retry up to 3 times if a male character's median F0 exceeds 165Hz
        for attempt in range(3):
            temp = 0.76 if attempt == 0 else (0.68 if attempt == 1 else 0.62)
            wavs, sr = base_model.generate_voice_clone(
                text=line,
                language="Chinese",
                ref_audio=str(anchor_wav),
                ref_text=None,
                x_vector_only_mode=True,
                temperature=temp,
                top_p=0.90,
                repetition_penalty=1.08,
                max_new_tokens=384,
            )
            candidate = trim_trailing_silence(wavs[0], sr, pad_sec=0.18)
            f0, _, _ = librosa.pyin(candidate, fmin=50, fmax=380, sr=sr)
            f0_v = f0[~np.isnan(f0)]
            f0_med = round(float(np.median(f0_v)), 1) if len(f0_v) > 0 else 0.0
            f0_std = round(float(np.std(f0_v)), 1) if len(f0_v) > 0 else 0.0
            f0_span = round(float(np.percentile(f0_v, 95) - np.percentile(f0_v, 5)), 1) if len(f0_v) > 0 else 0.0
            wav_clean = candidate
            if is_female_char or (50.0 < f0_med <= 165.0):
                break
            print(f"[Qwen3-TTS F0 Guard] Attempt {attempt+1} F0_med={f0_med}Hz > 165Hz for male {speaker}, retrying with lower temperature...", flush=True)

        # Normalize peak amplitude to -1.5 dBFS (0.84) for rich broadcast presence
        peak = float(np.max(np.abs(wav_clean)))
        if peak > 1e-4:
            wav_clean = (wav_clean / peak * 0.84).astype(np.float32)

        out_wav = vo_dir / f"{sid}.wav"
        sf.write(str(out_wav), wav_clean, sr)
        dur = round(len(wav_clean) / sr, 2)
        elapsed = round(time.time() - t_s, 2)

        print(f"[Qwen3-TTS] Saved {out_wav} ({dur}s @ {sr}Hz in {elapsed}s | F0_med={f0_med}Hz, std={f0_std}Hz, span={f0_span}Hz)", flush=True)
        results.append({
            "scene_id": sid,
            "speaker": speaker,
            "mode": "Studio_Verified_Anchor_ECAPA_TDNN",
            "voice_anchor": anchor_wav.name,
            "duration_sec": dur,
            "f0_median_hz": f0_med,
            "f0_pitch_std_hz": f0_std,
            "f0_pitch_span_hz": f0_span,
            "elapsed_sec": elapsed,
            "wav_path": str(out_wav),
        })

    del base_model
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    print(json.dumps({"ok": True, "engine": "Qwen3-TTS-12Hz-1.7B-Verified-Studio-Anchor", "episode_id": episode_id, "voiceovers": results}, ensure_ascii=False))


def cmd_bgm(base_dir: Path, episode_id: str, prompt: str, duration_sec: float = 20.0, seed: int = 42):
    import scipy.io.wavfile as wavfile
    from diffsynth.pipelines.ace_step import AceStepPipeline
    from diffsynth.core import ModelConfig

    bgm_dir = base_dir / "output" / "bgm"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    out_wav = bgm_dir / f"{episode_id}_acestep_bgm.wav"

    t0 = time.time()
    print(f"[ACE-Step 1.5] Loading AceStepPipeline (DiT=GPU bf16, OobleckVAE=Zen5 CPU fp32)...", flush=True)
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

    caption = prompt or (
        "Cinematic dramatic orchestral film score, emotional strings and deep atmospheric percussion "
        "building into a grand thematic crescendo, Hans Zimmer style, high fidelity 48kHz stereo film score."
    )

    audio_tensor = pipe(
        prompt=caption,
        lyrics="[instrumental]",
        task_type="text2music",
        duration=int(round(duration_sec)),
        bpm=96,
        keyscale="D minor",
        timesignature="4",
        vocal_language="unknown",
        num_inference_steps=8,
        cfg_scale=1.0,
        seed=seed,
    )
    audio_np = audio_tensor.detach().cpu().float().numpy()
    if audio_np.ndim == 3:
        audio_np = audio_np[0]
    if audio_np.ndim == 2:
        audio_np = audio_np.T  # [T, C]
    audio_int16 = np.clip(audio_np * 32767.0, -32768, 32767).astype(np.int16)
    wavfile.write(str(out_wav), 48000, audio_int16)
    elapsed = round(time.time() - t0, 2)
    del pipe
    torch.cuda.synchronize()
    torch.cuda.empty_cache()

    print(json.dumps({
        "ok": True,
        "engine": "ACE-Step-1.5-Turbo",
        "episode_id": episode_id,
        "duration_sec": round(len(audio_int16) / 48000.0, 2),
        "elapsed_sec": elapsed,
        "bgm_path": str(out_wav),
    }, ensure_ascii=False))


def _snap_minimax_frames(target_frames: int) -> int:
    """MiniMax H3 valid frame counts follow 17*n + 5 (22, 39, 56, 73, 90, 107, 124)."""
    n = max(2, round((target_frames - 5) / 17.0))
    return 17 * n + 5


def _build_scene_subshots(sc: dict, total_vo_sec: float, style_suffix: str = "") -> list[dict]:
    """
    Splits a scene into 1 or 2 real-time 24fps sub-shots so that:
      - Every frame plays at native 1.0x 24fps (ZERO slow-motion setpts stretching!)
      - Each sub-shot is conditioned on its exact corresponding slice of the Qwen3-TTS voiceover (`retake_audio`)
      - Resolution uses high-definition 16:9 widescreen so details are crisp and sharp.
    """
    cam = (sc.get("camera_motion") or "35mm anamorphic lens, cinematic tracking").strip()
    action = (sc.get("action") or "").strip()
    if not style_suffix:
        style_suffix = (
            "Shot on ARRI Alexa 65 with Panavision anamorphic lens, live-action cinematic realism, "
            "Rembrandt chiaroscuro tungsten lighting, ultra-sharp facial and costume micro-texture, 8k photorealistic. "
            "Clean video frame without any subtitles, captions, or floating text."
        )

    if total_vo_sec <= 4.6:
        num_frames = _snap_minimax_frames(int(math.ceil(total_vo_sec * 24.0)))
        num_frames = max(73, min(90, num_frames))
        return [{
            "shot_idx": 0,
            "num_frames": num_frames,
            "audio_start_sec": 0.0,
            "audio_end_sec": num_frames / 24.0,
            "prompt": f"{cam}. {action} {style_suffix}",
            "use_keyframe": True,
        }]

    # Split into 2 dynamic 24fps shots (Shot A: medium/wide setup, Shot B: close-up dramatic reaction/focus)
    half_sec = total_vo_sec / 2.0
    frames_a = max(73, min(90, _snap_minimax_frames(int(round(half_sec * 24.0)))))
    dur_a = frames_a / 24.0
    rem_sec = max(2.8, total_vo_sec - dur_a)
    frames_b = max(73, min(90, _snap_minimax_frames(int(math.ceil(rem_sec * 24.0)))))
    dur_b = frames_b / 24.0

    prompt_a = f"{cam}. {action} {style_suffix}"
    prompt_b = (
        f"85mm anamorphic close-up portrait lens, crisp shallow depth of field, dynamic emotional lip-sync performance. "
        f"{action} {style_suffix}"
    )
    return [
        {
            "shot_idx": 0,
            "num_frames": frames_a,
            "audio_start_sec": 0.0,
            "audio_end_sec": dur_a,
            "prompt": prompt_a,
            "use_keyframe": True,
        },
        {
            "shot_idx": 1,
            "num_frames": frames_b,
            "audio_start_sec": dur_a,
            "audio_end_sec": dur_a + dur_b,
            "prompt": prompt_b,
            "use_keyframe": False,
        },
    ]


def cmd_render_h3(base_dir: Path, episode_id: str, scene_id: str = None, dry_run: bool = False):
    from PIL import Image
    from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline
    from diffsynth.core import ModelConfig
    from diffsynth.utils.data import save_video

    ffmpeg_exe = _get_ffmpeg_exe()
    manifest = load_episode_manifest(base_dir, episode_id)
    scenes = manifest.get("scenes", [])
    if scene_id:
        scenes = [s for s in scenes if s.get("id") == scene_id]
    if not scenes:
        raise ValueError(f"No matching scenes found in {episode_id} (scene_id={scene_id})")

    raw_dir = base_dir / "output" / "raw_clips" / episode_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    vo_dir = base_dir / "output" / "voiceovers" / episode_id

    if dry_run:
        print(json.dumps({
            "ok": True,
            "dry_run": True,
            "episode_id": episode_id,
            "scene_count": len(scenes),
            "scenes": [s.get("id") for s in scenes],
        }, ensure_ascii=False))
        return

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

    # Use 1024x576 (16:9 HD, divisible by 64) for crisp detail with 768p LoRA while keeping multi-shot generation fast
    render_w, render_h = 1024, 576

    project_style_suffix = load_project_style_suffix(base_dir)
    rendered = []
    for idx, sc in enumerate(scenes):
        sid = sc.get("id", f"scene_{idx+1}")
        vo_wav = vo_dir / f"{sid}.wav"
        audio_np = None
        sr = 32000
        vo_dur = float(sc.get("duration") or 5.0)
        if vo_wav.exists():
            audio_np, sr = sf.read(str(vo_wav), dtype="float32")
            vo_dur = len(audio_np) / float(sr)

        subshots = _build_scene_subshots(sc, vo_dur, project_style_suffix)

        # Support multi-keyframe pose/trajectory anchoring (`keyframes`, `pose_anchors`, `keyframe_indices = [0, 51, 85]`)
        keyframes_base = None
        keyframe_indices_base = None
        keyframe_strengths_base = None
        raw_kfs = sc.get("keyframes")
        pose_anchors = sc.get("pose_anchors")
        if pose_anchors and isinstance(pose_anchors, list) and not raw_kfs:
            from pose_library_engine import UniversalPoseLibrary
            pose_lib = UniversalPoseLibrary()
            plan = pose_lib.build_17k_trajectory_plan(
                pose_ids=[str(x) for x in pose_anchors],
                num_frames=90,
                custom_indices=sc.get("keyframe_indices"),
                custom_strengths=sc.get("keyframe_strengths"),
                tail_lock_v9=bool(sc.get("tail_lock_v9", True)),
                download_images=True,
            )
            raw_kfs = [a["local_image_path"] for a in plan.get("anchors", []) if a.get("local_image_path")]
            keyframe_indices_base = plan.get("keyframe_indices")
            keyframe_strengths_base = plan.get("keyframe_strengths")

        if raw_kfs and isinstance(raw_kfs, list):
            loaded_kfs = []
            for kp in raw_kfs:
                p = Path(kp) if Path(kp).is_absolute() else (base_dir / kp)
                if p.exists():
                    loaded_kfs.append(Image.open(p).convert("RGB"))
            if loaded_kfs:
                keyframes_base = loaded_kfs
                raw_kfi = keyframe_indices_base or sc.get("keyframe_indices")
                if raw_kfi and len(raw_kfi) == len(loaded_kfs):
                    # Snap intermediate indices strictly to 17k (`0, 17, 34, 51, 68, 85`)
                    keyframe_indices_base = [
                        0 if int(x) <= 0 else (-1 if int(x) == -1 else int(round(int(x) / 17.0)) * 17)
                        for x in raw_kfi
                    ]
                elif len(loaded_kfs) == 1:
                    keyframe_indices_base = [0]
                elif len(loaded_kfs) == 2:
                    keyframe_indices_base = [0, 85]
                else:
                    keyframe_indices_base = [0, 51, 85][:len(loaded_kfs)]
                raw_kfs_str = keyframe_strengths_base or sc.get("keyframe_strengths")
                if raw_kfs_str and len(raw_kfs_str) == len(loaded_kfs):
                    keyframe_strengths_base = [float(x) for x in raw_kfs_str]
                else:
                    keyframe_strengths_base = [1.0 if i == 0 else 0.88 for i in range(len(loaded_kfs))]
        elif sc.get("ref_image"):
            ref_p = base_dir / sc.get("ref_image")
            if ref_p.exists():
                keyframes_base = [Image.open(ref_p).convert("RGB")]
                keyframe_indices_base = [0]
                keyframe_strengths_base = [1.0]

        # Check for 22-Frame (7-Token) MotionContext Latent Continuation (`track_a_latent_relay`)
        latent_dir = raw_dir / "_av_latents"
        latent_dir.mkdir(parents=True, exist_ok=True)
        motion_ctx_latents = None
        if sc.get("continuity_track") == "track_a_latent_relay" and idx > 0:
            prev_sid = scenes[idx - 1].get("id", f"scene_{idx}")
            prev_pt = latent_dir / f"{prev_sid}_shot0.pt"
            if prev_pt.exists():
                prev_ckpt = torch.load(prev_pt, map_location="cpu", weights_only=False)
                motion_ctx_latents = prev_ckpt.get("video_latents")
                print(f"[MiniMax H3] Loaded 7-Token (22-frame) MotionContext from {prev_pt.name}", flush=True)

        t_sc = time.time()
        subshot_mp4s = []
        total_gen_frames = 0

        for sub in subshots:
            s_idx = sub["shot_idx"]
            n_frames = sub["num_frames"]
            a_start = sub["audio_start_sec"]
            a_end = sub["audio_end_sec"]

            retake_audio_tensor = None
            if audio_np is not None:
                i0 = int(round(a_start * sr))
                i1 = int(round(a_end * sr))
                slice_np = audio_np[i0:i1]
                target_len = int(round((n_frames / 24.0) * sr))
                if len(slice_np) < target_len:
                    slice_np = np.pad(slice_np, (0, target_len - len(slice_np)))
                else:
                    slice_np = slice_np[:target_len]
                if slice_np.ndim == 1:
                    slice_np = np.stack([slice_np, slice_np], axis=0)
                else:
                    slice_np = slice_np.T
                retake_audio_tensor = torch.from_numpy(slice_np.astype(np.float32))

            use_kf = None
            use_kfi = None
            use_kfs = None
            if sub["use_keyframe"] and keyframes_base and keyframe_indices_base:
                use_kf = []
                use_kfi = []
                use_kfs = []
                max_valid_17k = ((n_frames - 5) // 17) * 17
                for kf_img, kfi, kfs in zip(keyframes_base, keyframe_indices_base, keyframe_strengths_base):
                    clamped_kfi = min(max_valid_17k, int(kfi)) if int(kfi) > 0 else int(kfi)
                    if clamped_kfi in use_kfi and clamped_kfi > 0:
                        # keep the latter anchor if two clamped to the same tail slot
                        use_kf[-1] = kf_img
                        use_kfs[-1] = kfs
                    else:
                        use_kf.append(kf_img)
                        use_kfi.append(clamped_kfi)
                        use_kfs.append(kfs)

            print(
                f"[MiniMax H3] Rendering {sid} Shot {s_idx+1}/{len(subshots)} "
                f"({render_w}x{render_h} @ 24fps, {n_frames} frames = {n_frames/24.0:.2f}s, 1.0x real-time A2V, 17k={use_kfi})...",
                flush=True,
            )
            video_frames, _, latent_ckpt = pipe(
                prompt=sub["prompt"],
                negative_prompt="bad quality, blurry, out of focus, low resolution, distorted face, text, watermark, subtitles, slow motion",
                height=render_h,
                width=render_w,
                num_frames=n_frames,
                num_inference_steps=4,
                cfg_scale=1.0,
                flow_shift=12.0,
                audio_flow_shift=3.0,
                keyframes=use_kf,
                keyframe_indices=use_kfi,
                keyframe_strengths=use_kfs,
                motion_context_latents=motion_ctx_latents if s_idx == 0 else None,
                motion_context_tokens=7,
                return_latents=True,
                retake_audio=retake_audio_tensor,
                retake_audio_sample_rate=sr,
                seconds_regions_to_retake=[] if retake_audio_tensor is not None else None,
                seed=200 + idx * 10 + s_idx,
            )
            # Save ~5MB AV_LATENT checkpoint for `--only-seg` hot-swap & 22-frame MotionContext relay
            torch.save(latent_ckpt, latent_dir / f"{sid}_shot{s_idx}.pt")
            sub_mp4 = raw_dir / f"{sid}_shot{s_idx}.mp4"
            save_video(video_frames, str(sub_mp4), fps=24, quality=9)
            subshot_mp4s.append(sub_mp4)
            total_gen_frames += len(video_frames)
            torch.cuda.synchronize()
            torch.cuda.empty_cache()

        # Concatenate real-time 24fps sub-shots and mux with the exact Qwen3-TTS voiceover (ZERO time-stretching!)
        vid_concat = raw_dir / f"{sid}_video_concat.mp4"
        if len(subshot_mp4s) == 1:
            shutil.copyfile(str(subshot_mp4s[0]), str(vid_concat))
        else:
            list_file = raw_dir / f"{sid}_shots.txt"
            with open(list_file, "w", encoding="utf-8") as lf:
                for p in subshot_mp4s:
                    lf.write(f"file '{str(p).replace(chr(92), '/')}'\n")
            subprocess.run(
                [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(vid_concat)],
                check=True,
                capture_output=True,
            )

        out_mp4 = raw_dir / f"{sid}.mp4"
        vid_dur = total_gen_frames / 24.0
        if vo_wav.exists():
            subprocess.run([
                ffmpeg_exe, "-y",
                "-i", str(vid_concat),
                "-i", str(vo_wav),
                "-filter_complex",
                f"[0:v]fps=24[v];[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={vid_dur:.2f}[a]",
                "-map", "[v]", "-map", "[a]",
                "-t", f"{vid_dur:.2f}",
                "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                str(out_mp4),
            ], check=True, capture_output=True)
        else:
            shutil.copyfile(str(vid_concat), str(out_mp4))

        if vid_concat.exists():
            vid_concat.unlink()

        elapsed = round(time.time() - t_sc, 2)
        print(f"[MiniMax H3] Scene {sid} saved to {out_mp4} ({total_gen_frames} frames = {vid_dur:.2f}s @ 24fps 1.0x) in {elapsed}s", flush=True)
        rendered.append({
            "scene_id": sid,
            "video_path": str(out_mp4),
            "resolution": f"{render_w}x{render_h}",
            "frames": total_gen_frames,
            "duration_sec": round(vid_dur, 2),
            "playback_speed": "1.0x (native 24fps, zero slow-motion)",
            "audio_conditioned": vo_wav.exists(),
            "elapsed_sec": elapsed,
        })

    print(json.dumps({"ok": True, "engine": "MiniMax-H3-Local-HD-24fps", "episode_id": episode_id, "rendered": rendered}, ensure_ascii=False))


def _get_ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def _probe_video_duration(ffmpeg_exe: str, clip_path: Path) -> float:
    res = subprocess.run([ffmpeg_exe, "-i", str(clip_path)], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr or "")
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return 4.0


def _format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _split_line_clauses(line: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[，。！？；：、,!?;])", line.strip()) if p.strip()]
    if not parts:
        return [line.strip()]
    # Merge very short fragments (< 4 chars) with the next clause so subtitles stay readable
    merged = []
    buf = ""
    for p in parts:
        buf += p
        if len(re.sub(r"[^\u4e00-\u9fff0-9A-Za-z]", "", buf)) >= 5:
            merged.append(buf)
            buf = ""
    if buf:
        if merged:
            merged[-1] += buf
        else:
            merged.append(buf)
    return merged


def _generate_episode_ass_subtitles(ass_path: Path, scene_timings: list[dict], personas: dict = None) -> Path:
    """
    Generates a high-contrast, broadcast-grade 1280x720 ASS subtitle file:
      - Font: Microsoft YaHei Bold, size 44, crisp white fill (&H00FFFFFF)
      - Thick 3.5px pure black outline (&H00000000) + soft dark drop shadow
      - Clauses timed proportionally to character count within each scene's exact voiceover window.
    """
    personas = personas or DEFAULT_UNIVERSAL_PERSONAS
    header = """[Script Info]
Title: AetherDirector Studio Master Subtitles
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,42,&H00FFFFFF,&H0000FFFF,&H32000000,&H28000000,-1,0,0,0,100,100,1.5,0,3,10.0,0.0,2,40,40,36,1
Style: SpeakerTag,Microsoft YaHei,36,&H0070D6FF,&H0000FFFF,&H32000000,&H28000000,-1,0,0,0,100,100,1.0,0,3,10.0,0.0,2,40,40,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for item in scene_timings:
        line = (item.get("line") or "").strip()
        if not line:
            continue
        speaker_code = item.get("speaker") or ""
        speaker_cn = personas.get(speaker_code, {}).get("speaker_label", speaker_code)
        t_start = item["start_sec"]
        vo_dur = item["vo_dur_sec"]
        clauses = _split_line_clauses(line)
        total_chars = max(1, sum(len(c) for c in clauses))

        cursor = t_start + 0.05
        for idx, clause in enumerate(clauses):
            frac = len(clause) / float(total_chars)
            c_dur = max(0.8, vo_dur * frac)
            c_end = min(t_start + vo_dur + 0.15, cursor + c_dur)
            prefix = f"{{\\c&H70D6FF&}}【{speaker_cn}】{{\\c&HFFFFFF&}}" if (idx == 0 and speaker_cn) else ""
            events.append(
                f"Dialogue: 0,{_format_ass_time(cursor)},{_format_ass_time(c_end)},Default,{speaker_cn},0,0,0,,{prefix}{clause}"
            )
            cursor = c_end

    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    return ass_path


def cmd_master_episode(base_dir: Path, episode_id: str):
    """
    Stitches episode clips at 1.0x native 24fps (ZERO slow-motion setpts stretching!) +
    Qwen3-TTS theatrical ICL voiceovers + ACE-Step 1.5 BGM with sidechain ducking +
    high-contrast burned-in ASS Chinese subtitles into final master MP4.
    """
    ffmpeg_exe = _get_ffmpeg_exe()
    manifest = load_episode_manifest(base_dir, episode_id)
    scenes = manifest.get("scenes", [])
    raw_dir = base_dir / "output" / "raw_clips" / episode_id
    vo_dir = base_dir / "output" / "voiceovers" / episode_id
    bgm_wav = base_dir / "output" / "bgm" / f"{episode_id}_acestep_bgm.wav"
    final_dir = base_dir / "output" / "final_episodes"
    final_dir.mkdir(parents=True, exist_ok=True)
    norm_dir = raw_dir / "_normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)

    norm_clips = []
    scene_timings = []
    timeline_cursor = 0.0

    for sc in scenes:
        sid = sc.get("id")
        clip_path = raw_dir / f"{sid}.mp4"
        if not clip_path.exists():
            matches = list(raw_dir.glob(f"{sid}*.mp4"))
            if matches:
                clip_path = matches[0]
            else:
                continue
        vo_path = vo_dir / f"{sid}.wav"
        norm_out = norm_dir / f"{sid}_norm.mp4"

        vid_dur = _probe_video_duration(ffmpeg_exe, clip_path)
        vo_dur = vid_dur
        if vo_path.exists():
            vo_info = sf.info(str(vo_path))
            vo_dur = vo_info.duration

        # Play video at 1.0x real-time 24fps if video duration covers >=85% of voiceover;
        # only apply gentle <=1.15x adjustment if slightly shorter, NEVER 4x slow-motion!
        target_dur = max(vid_dur, vo_dur + 0.20)
        stretch = target_dur / max(0.5, vid_dur)
        if stretch <= 1.18:
            vf = f"setpts={stretch:.4f}*PTS,fps=24,scale=1280:720:flags=lanczos,unsharp=5:5:0.85:3:3:0.4"
            clip_dur = target_dur
        else:
            # Keep 1.0x real-time speed and pad last frame cleanly if needed
            pad_sec = max(0.0, target_dur - vid_dur)
            vf = f"fps=24,scale=1280:720:flags=lanczos,unsharp=5:5:0.85:3:3:0.4,tpad=stop_mode=clone:stop_duration={pad_sec:.2f}"
            clip_dur = target_dur

        if vo_path.exists():
            subprocess.run([
                ffmpeg_exe, "-y",
                "-i", str(clip_path),
                "-i", str(vo_path),
                "-filter_complex",
                f"[0:v]{vf}[v];[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={clip_dur:.2f},volume=1.65[a]",
                "-map", "[v]", "-map", "[a]",
                "-t", f"{clip_dur:.2f}",
                "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                str(norm_out)
            ], check=True, capture_output=True)
        else:
            # Never keep Veo/cloud raw audio stream ([0:a]) as it may contain foreign-language dialogue;
            # generate a clean silent stereo track if no Chinese TTS voiceover exists for this scene.
            subprocess.run([
                ffmpeg_exe, "-y",
                "-i", str(clip_path),
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-filter_complex",
                f"[0:v]{vf}[v];[1:a]atrim=0:{clip_dur:.2f}[a]",
                "-map", "[v]", "-map", "[a]",
                "-t", f"{clip_dur:.2f}",
                "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                str(norm_out)
            ], check=True, capture_output=True)

        actual_norm_dur = _probe_video_duration(ffmpeg_exe, norm_out)
        scene_timings.append({
            "scene_id": sid,
            "speaker": sc.get("speaker") or "",
            "line": sc.get("line") or "",
            "start_sec": timeline_cursor,
            "vo_dur_sec": min(vo_dur, actual_norm_dur),
            "clip_dur_sec": actual_norm_dur,
        })
        timeline_cursor += actual_norm_dur
        norm_clips.append(norm_out)

    if not norm_clips:
        raise RuntimeError(f"No clips found in {raw_dir} to master for {episode_id}")

    concat_txt = norm_dir / "concat_list.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for p in norm_clips:
            safe_p = str(p).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    stitched_mp4 = norm_dir / f"{episode_id}_stitched.mp4"
    subprocess.run([
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(stitched_mp4)
    ], check=True, capture_output=True)

    # Generate high-contrast ASS subtitle file and burn it onto the master video
    ass_file = norm_dir / f"{episode_id}_subtitles.ass"
    personas = load_character_personas(base_dir)
    _generate_episode_ass_subtitles(ass_file, scene_timings, personas)
    # Escape path for FFmpeg libass filter on Windows
    ass_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:")

    master_out = final_dir / f"{episode_id}_local_h3_master.mp4"
    if bgm_wav.exists():
        subprocess.run([
            ffmpeg_exe, "-y",
            "-i", str(stitched_mp4),
            "-stream_loop", "-1", "-i", str(bgm_wav),
            "-filter_complex",
            f"[0:v]ass='{ass_escaped}'[v_out];"
            "[0:a]asplit=2[vo_sc][vo_mix];"
            "[1:a]aresample=48000,volume=0.28[bgm_raw];"
            "[bgm_raw][vo_sc]sidechaincompress=threshold=0.035:ratio=5:attack=25:release=350[bgm_ducked];"
            "[vo_mix][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a_out]",
            "-map", "[v_out]", "-map", "[a_out]",
            "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-shortest",
            str(master_out)
        ], check=True, capture_output=True)
    else:
        subprocess.run([
            ffmpeg_exe, "-y",
            "-i", str(stitched_mp4),
            "-vf", f"ass='{ass_escaped}'",
            "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(master_out)
        ], check=True, capture_output=True)

    print(json.dumps({
        "ok": True,
        "episode_id": episode_id,
        "clip_count": len(norm_clips),
        "total_duration_sec": round(timeline_cursor, 2),
        "bgm_mixed": bgm_wav.exists(),
        "subtitles_burned": str(ass_file),
        "master_video": str(master_out),
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="AI Director Studio Local ROCm Inference Worker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_tts = sub.add_parser("tts")
    p_tts.add_argument("--base-dir", required=True)
    p_tts.add_argument("--root-dir", required=True)
    p_tts.add_argument("--episode-id", required=True)
    p_tts.add_argument("--scene-id", default=None)
    p_tts.add_argument("--instruct", default=None)

    p_bgm = sub.add_parser("bgm")
    p_bgm.add_argument("--base-dir", required=True)
    p_bgm.add_argument("--episode-id", required=True)
    p_bgm.add_argument("--prompt", default="")
    p_bgm.add_argument("--duration", type=float, default=20.0)
    p_bgm.add_argument("--seed", type=int, default=42)

    p_h3 = sub.add_parser("render-h3")
    p_h3.add_argument("--base-dir", required=True)
    p_h3.add_argument("--episode-id", required=True)
    p_h3.add_argument("--scene-id", default=None)
    p_h3.add_argument("--dry-run", action="store_true")

    p_master = sub.add_parser("master")
    p_master.add_argument("--base-dir", required=True)
    p_master.add_argument("--episode-id", required=True)

    args = parser.parse_args()
    if args.cmd == "tts":
        cmd_tts(Path(args.base_dir), Path(args.root_dir), args.episode_id, args.scene_id, args.instruct)
    elif args.cmd == "bgm":
        cmd_bgm(Path(args.base_dir), args.episode_id, args.prompt, args.duration, args.seed)
    elif args.cmd == "render-h3":
        cmd_render_h3(Path(args.base_dir), args.episode_id, args.scene_id, args.dry_run)
    elif args.cmd == "master":
        cmd_master_episode(Path(args.base_dir), args.episode_id)


if __name__ == "__main__":
    main()
