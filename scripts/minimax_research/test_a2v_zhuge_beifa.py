import time
import torch
import numpy as np
import soundfile as sf
import scipy.io.wavfile as wavfile
from pathlib import Path
from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline
from diffsynth.core import ModelConfig
from diffsynth.utils.data import save_video, merge_video_audio

BASE = Path(r"C:\Users\Liang\minimax\MiniMax-H3")
OUT_DIR = Path(r"c:\Users\Liang\Downloads\sanguo\assets\renders")

def main():
    print("=" * 65, flush=True)
    print("[START] Testing Audio-Driven Video (A2V) with MiniMax H3 + Qwen3-TTS Voiceover", flush=True)
    print("=" * 65, flush=True)

    tts_wav = OUT_DIR / "test_qwen3_tts_clone_zhuge.wav"
    if not tts_wav.exists():
        raise FileNotFoundError(f"Missing TTS wav: {tts_wav}")

    audio_np, sr = sf.read(str(tts_wav), dtype="float32")
    # Slice to first 3.0s so we only encode the active window needed for 39 frames (1.625s)
    max_samples = int(sr * 3.0)
    audio_np = audio_np[:max_samples]
    if audio_np.ndim == 1:
        audio_np = np.stack([audio_np, audio_np], axis=0)  # [2, T]
    else:
        audio_np = audio_np.T  # [C, T]
    retake_audio_tensor = torch.from_numpy(audio_np)

    t0 = time.time()
    model_configs = [
        ModelConfig(path=str(BASE / "diffusion_models" / "minimax_h3_fl2va_pruned_int8_convrot.safetensors")),
        ModelConfig(path=str(BASE / "text_encoders" / "qwen3vl_32b_minimax_h3_int8_convrot.safetensors")),
        ModelConfig(path=str(BASE / "vae" / "minimax_h3_video_vae_fp16.safetensors")),
        ModelConfig(path=str(BASE / "vae" / "minimax_h3_audio_vae_fp32.safetensors")),
    ]
    processor_config = ModelConfig(path=str(BASE / "processor"))

    pipe = MiniMaxH3Pipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=model_configs,
        processor_config=processor_config,
        redirect_common_files=False,
    )
    lora_path = BASE / "loras" / "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
    if lora_path.exists():
        pipe.load_lora(pipe.dit, str(lora_path), alpha=1.0)
    print(f"Loaded MiniMax H3 in {time.time() - t0:.1f}s!", flush=True)

    prompt = (
        "Cinematic live-action historical drama, 35mm ARRI Alexa Mini LF, Three Kingdoms Northern Expedition, "
        "medium close-up of Zhuge Liang in formal Prime Minister robes standing inside the Shu military command tent, "
        "warm candlelight illuminating his solemn face, holding a bamboo scroll (Chu Shi Biao), "
        "speaking passionately with natural lip-sync and subtle head movements, generals listening in background."
    )

    # 39 frames (~1.625s at 24fps, 17*2+5=39) locked to the first 1.625s of Qwen3-TTS cloned speech!
    t_gen = time.time()
    print("Running Audio-Conditioned Video Generation (39 frames, 4 steps Turbo, locked to Qwen3-TTS audio)...", flush=True)
    video_frames, audio_out = pipe(
        prompt=prompt,
        negative_prompt="bad quality, blurry, distorted face, text, watermark, subtitles, static mouth",
        height=512,
        width=896,
        num_frames=39,
        num_inference_steps=4,
        cfg_scale=1.0,
        flow_shift=12.0,
        audio_flow_shift=3.0,
        retake_audio=retake_audio_tensor,
        retake_audio_sample_rate=sr,
        seconds_regions_to_retake=[],  # Empty list = keep 100% of Qwen3-TTS audio latents fixed as condition!
        seed=108,
    )
    print(f"Audio-Driven Video generated in {time.time() - t_gen:.1f}s!", flush=True)

    vid_path = str(OUT_DIR / "test_a2v_zhuge_beifa_video.mp4")
    aud_path = str(OUT_DIR / "test_a2v_zhuge_beifa_audio.wav")
    final_path = str(OUT_DIR / "test_a2v_zhuge_beifa_av.mp4")

    save_video(video_frames, vid_path, fps=24, quality=9)
    # Trim original high-res TTS audio to match video duration (56/24 = 2.333s)
    n_samples = int(sr * (len(video_frames) / 24.0))
    sf.write(aud_path, audio_np[:, :n_samples].T, sr)

    import shutil
    shutil.copyfile(vid_path, final_path)
    merge_video_audio(final_path, aud_path)
    print(f"[SUCCESS] Audio-Driven Video + Qwen3-TTS Cloned Speech saved to: {final_path}", flush=True)

if __name__ == "__main__":
    main()
