import os
import time
import torch
import numpy as np
import scipy.io.wavfile as wavfile
from pathlib import Path
from PIL import Image
from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline
from diffsynth.core import ModelConfig
from diffsynth.utils.data import save_video, merge_video_audio

BASE = Path(r"C:\Users\Liang\minimax\MiniMax-H3")
OUT_DIR = Path(r"c:\Users\Liang\Downloads\sanguo\assets\renders")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 65, flush=True)
    print("[START] Testing MiniMax H3 (Video + Stereo 32kHz Audio Joint Generation) on ROCm gfx1151", flush=True)
    print(f"GPU: {torch.cuda.get_device_name(0)} | VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB", flush=True)
    print("=" * 65, flush=True)

    t0 = time.time()
    model_configs = [
        ModelConfig(path=str(BASE / "diffusion_models" / "minimax_h3_fl2va_pruned_int8_convrot.safetensors")),
        ModelConfig(path=str(BASE / "text_encoders" / "qwen3vl_32b_minimax_h3_int8_convrot.safetensors")),
        ModelConfig(path=str(BASE / "vae" / "minimax_h3_video_vae_fp16.safetensors")),
        ModelConfig(path=str(BASE / "vae" / "minimax_h3_audio_vae_fp32.safetensors")),
    ]
    processor_config = ModelConfig(path=str(BASE / "processor"))

    print("[1/3] Loading MiniMax H3 Pipeline...", flush=True)
    pipe = MiniMaxH3Pipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=model_configs,
        processor_config=processor_config,
        redirect_common_files=False,
    )

    lora_path = BASE / "loras" / "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
    if lora_path.exists():
        print(f"[1.5/3] Loading 4-Step Turbo LoRA: {lora_path.name}", flush=True)
        pipe.load_lora(pipe.dit, str(lora_path), alpha=1.0)

    print(f"Model loaded in {time.time() - t0:.1f}s!", flush=True)

    prompt = (
        "Cinematic drama shot, 35mm ARRI Alexa Mini LF lens, Three Kingdoms period, "
        "Zhuge Liang standing on a misty wooden warship deck at night during heavy rain, "
        "holding a white feather fan, warm flickering lantern light reflecting on wet wood, "
        "thousands of flaming arrows flying through the dark fog in the background. "
        "Audio: heavy rainstorm, wooden ship creaking on river waves, distant war drums, "
        "and a calm, resonant young male voice speaking in Mandarin Chinese: '亮早已算定，今夜江上必有大雾。'"
    )

    # 39 frames (17*2 + 5 = 39 frames = ~1.63s at 24fps) at 512x896 with 4-step Turbo LoRA for fast verification
    t_gen = time.time()
    print("[2/3] Running Joint Video + Audio Denoising (4 steps Turbo)...", flush=True)
    video_frames, audio_tensor = pipe(
        prompt=prompt,
        negative_prompt="bad quality, blurry, distorted face, text, watermark, subtitles",
        height=512,
        width=896,
        num_frames=39,
        num_inference_steps=4,
        cfg_scale=1.0,
        flow_shift=12.0,
        audio_flow_shift=3.0,
        seed=42,
    )
    gen_elapsed = time.time() - t_gen
    print(f"[3/3] Joint Generation complete in {gen_elapsed:.1f}s! Frames: {len(video_frames)}, Audio shape: {audio_tensor.shape}", flush=True)

    video_only_path = str(OUT_DIR / "test_minimax_h3_joint_video.mp4")
    audio_wav_path = str(OUT_DIR / "test_minimax_h3_joint_audio.wav")
    final_mp4_path = str(OUT_DIR / "test_minimax_h3_joint_av.mp4")

    save_video(video_frames, video_only_path, fps=24, quality=9)

    # Save audio tensor [C, T] at 32000 Hz using scipy
    audio_np = audio_tensor.detach().cpu().float().numpy()
    if audio_np.ndim == 2:
        audio_np = audio_np.T  # [T, C]
    audio_int16 = np.clip(audio_np * 32767.0, -32768, 32767).astype(np.int16)
    wavfile.write(audio_wav_path, 32000, audio_int16)
    print(f"Saved audio wav to {audio_wav_path}", flush=True)

    # Copy video_only to final_mp4 and merge audio
    import shutil
    shutil.copyfile(video_only_path, final_mp4_path)
    merge_video_audio(final_mp4_path, audio_wav_path)
    print(f"[SUCCESS] Joint Video+Audio saved to: {final_mp4_path}", flush=True)

if __name__ == "__main__":
    main()
