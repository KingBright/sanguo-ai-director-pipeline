import time
import torch
import numpy as np
import scipy.io.wavfile as wavfile
from pathlib import Path
from diffsynth.pipelines.ace_step import AceStepPipeline
from diffsynth.core import ModelConfig

BASE = Path(r"C:\Users\Liang\minimax\ACE-Step-1.5")
OUT_DIR = Path(r"c:\Users\Liang\Downloads\sanguo\assets\renders")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 65, flush=True)
    print("[START] Testing ACE-Step 1.5 Turbo (48kHz Stereo BGM Generation) on ROCm gfx1151", flush=True)
    print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)
    print("=" * 65, flush=True)

    t0 = time.time()
    model_configs = [
        ModelConfig(path=str(BASE / "acestep-v15-turbo" / "model.safetensors")),
        ModelConfig(path=str(BASE / "Qwen3-Embedding-0.6B" / "model.safetensors")),
        ModelConfig(path=str(BASE / "vae" / "diffusion_pytorch_model.safetensors")),
    ]
    text_tokenizer_config = ModelConfig(path=str(BASE / "Qwen3-Embedding-0.6B"))
    silence_latent_config = ModelConfig(path=str(BASE / "acestep-v15-turbo" / "silence_latent.pt"))

    print("[1/2] Loading AceStepPipeline...", flush=True)
    pipe = AceStepPipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=model_configs,
        text_tokenizer_config=text_tokenizer_config,
        silence_latent_config=silence_latent_config,
    )
    # On ROCm gfx1151, Oobleck VAE ConvTranspose1d uses huge MIOpen workspace; run VAE decode in fp32 on CPU (takes <0.3s on Zen 5 16-core!)
    pipe.vae = pipe.vae.to(device="cpu", dtype=torch.float32)
    orig_decode = pipe.vae.decode
    pipe.vae.decode = lambda z, **kw: orig_decode(z.to(device="cpu", dtype=torch.float32), **kw)
    if "vae" in pipe.model_Names if hasattr(pipe, "model_Names") else []:
        pass
    orig_load = pipe.load_models_to_device
    def safe_load(names):
        orig_load([n for n in names if n != "vae"])
    pipe.load_models_to_device = safe_load

    print(f"Loaded in {time.time() - t0:.1f}s!", flush=True)

    prompt = (
        "epic Chinese historical war soundtrack, Three Kingdoms cinematic orchestral score, "
        "deep taiko war drums, tense guqin and pipa strings, low brass, dark atmospheric tension, "
        "misty river battle at night, instrumental film score, high fidelity 48kHz"
    )

    t_gen = time.time()
    print("[2/2] Generating 20s 48kHz Stereo BGM (8 steps Turbo)...", flush=True)
    audio_tensor = pipe(
        prompt=prompt,
        lyrics="[instrumental]",
        task_type="text2music",
        duration=20,
        bpm=96,
        keyscale="D minor",
        timesignature="4",
        vocal_language="unknown",
        num_inference_steps=8,
        cfg_scale=1.0,
        seed=42,
    )
    gen_elapsed = time.time() - t_gen
    print(f"Generated 20s 48kHz stereo music in {gen_elapsed:.2f}s! Audio shape: {audio_tensor.shape}", flush=True)

    out_wav = OUT_DIR / "test_ace_step15_bgm.wav"
    audio_np = audio_tensor.detach().cpu().float().numpy()
    if audio_np.ndim == 3:
        audio_np = audio_np[0]
    if audio_np.ndim == 2:
        audio_np = audio_np.T  # [T, C]
    audio_int16 = np.clip(audio_np * 32767.0, -32768, 32767).astype(np.int16)
    wavfile.write(str(out_wav), 48000, audio_int16)
    print(f"[SUCCESS] Saved 48kHz BGM to: {out_wav}", flush=True)

if __name__ == "__main__":
    main()
