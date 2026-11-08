import time
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import torch
import soundfile as sf
import numpy as np
from pathlib import Path

BASE_DESIGN = Path(r"C:\Users\Liang\minimax\Qwen3-TTS-12Hz-1.7B-VoiceDesign")
VO_OUT_DIR = Path(r"C:\Users\Liang\Downloads\sanguo\projects\alien_thief\episodes\ep01_lottery_heist\output\voiceovers")
BGM_OUT_DIR = Path(r"C:\Users\Liang\Downloads\sanguo\projects\alien_thief\episodes\ep01_lottery_heist\output\bgm")
VO_OUT_DIR.mkdir(parents=True, exist_ok=True)
BGM_OUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE_INSTRUCTS = {
    "Kato": "粗犷、凶猛低沉的四十五岁巨魔外星赏金猎人男声，带有威严沙哑的怒吼质感和不耐烦的语气，音域低沉有力，咬字刚硬霸气。",
    "Xiaodai": "冷静、清脆平稳的二十岁年轻外星女声，毫无情绪波动的冷淡毒舌死鱼眼吐槽风格，语速均匀平缓，咬字清晰，充满轻蔑冷幽默。",
    "Libei": "年轻、尖锐慌乱的二十岁外星小弟男声，带有神经质的颤抖和搞笑破音感，极度惊恐慌张的抓狂吐槽役，语速稍快颤抖。",
    "Ximu": "尖锐滑稽、狡黠市侩的三十五岁独眼地精外星小偷男声，语调轻佻高亢上扬，充满贪财自信与死猪不怕开水烫的无赖感，得意洋洋。",
    "PinkWeirdo": "古怪离奇、一本正经的粉色外星怪咖男声，略带长颈外星人咏叹调的荒诞滑稽感，语调起伏夸张，一本正经胡说八道。",
}

SCENES = [
    {"id": "ep01_01", "speaker": "Kato", "line": "锁定目标！通缉榜倒数第一的独眼地精正在靠近彩票亭！"},
    {"id": "ep01_02", "speaker": "Xiaodai", "line": "悬赏金额两块五，耗油三千块，哥你真会理财。"},
    {"id": "ep01_03", "speaker": "Libei", "line": "西木哥！对面狙击镜反光超刺眼，咱真要抢吗？"},
    {"id": "ep01_04", "speaker": "Ximu", "line": "抢？读书人的事能叫抢吗？我这是用钛合金撬棍刮奖！"},
    {"id": "ep01_05", "speaker": "Libei", "line": "等等！你刮出来的特等奖怎么是一只机械尖叫鸡？"},
    {"id": "ep01_06", "speaker": "Ximu", "line": "赚大了！只要捏爆它的脖子，全星际雷达都得瘫痪！"},
    {"id": "ep01_07", "speaker": "PinkWeirdo", "line": "肃静！本人正式宣布，今日和平杰出个人得主是这位绿师傅！"},
    {"id": "ep01_08", "speaker": "Kato", "line": "开什么星际玩笑！他手里捏着赃物还在朝台下敬礼！"},
    {"id": "ep01_09", "speaker": "Xiaodai", "line": "警报解除。因为主办方把抓捕队长的车给当场扣了。"},
    {"id": "ep01_10", "speaker": "Libei", "line": "救命啊！通缉队长拿爆能枪坐在咱对面跟咱斗地主！"},
    {"id": "ep01_11", "speaker": "Ximu", "line": "慌什么！四个二带两王，长官，这局你输了洗碗去！"},
    {"id": "ep01_12", "speaker": "PinkWeirdo", "line": "烂柯星反扒大获全胜，感谢猫咪赞助商提供的假发！"},
]

def generate_voiceovers():
    print("=" * 70, flush=True)
    print("🎤 [STEP 1/2] Generating Multi-Role Character Dialogue Audio via Qwen3-TTS...", flush=True)
    print("=" * 70, flush=True)

    from qwen_tts import Qwen3TTSModel

    t0 = time.time()
    design_model = Qwen3TTSModel.from_pretrained(
        str(BASE_DESIGN),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    print(f"Loaded Qwen3-TTS VoiceDesign in {time.time() - t0:.1f}s!", flush=True)

    for idx, sc in enumerate(SCENES, 1):
        sc_id = sc["id"]
        speaker = sc["speaker"]
        line = sc["line"]
        instruct = VOICE_INSTRUCTS.get(speaker, "幽默诙谐的动画角色配音，富有喜剧表现力。")
        out_wav = VO_OUT_DIR / f"{sc_id}.wav"

        t_shot = time.time()
        print(f"[{idx}/12] Generating VO for {sc_id} ({speaker}): \"{line}\"...", flush=True)
        wavs, sr = design_model.generate_voice_design(
            text=line,
            language="Chinese",
            instruct=instruct,
            max_new_tokens=300,
        )
        audio = wavs[0]
        # Normalize audio peak
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.92
        sf.write(str(out_wav), audio, sr)
        dur = len(audio) / sr
        print(f"   -> Saved: {out_wav.name} ({dur:.2f}s, {sr}Hz) in {time.time() - t_shot:.2f}s", flush=True)

    del design_model
    torch.cuda.empty_cache()
    print("✅ All 12 character voiceovers successfully generated!", flush=True)

def generate_bgm():
    print("=" * 70, flush=True)
    print("🎷 [STEP 2/2] Generating Quirky Interstellar Jazz-Funk Comedy BGM via ACE-Step 1.5...", flush=True)
    print("=" * 70, flush=True)

    import scipy.io.wavfile as wavfile
    from diffsynth.pipelines.ace_step import AceStepPipeline
    from diffsynth.core import ModelConfig

    BASE = Path(r"C:\Users\Liang\minimax\ACE-Step-1.5")
    model_configs = [
        ModelConfig(path=str(BASE / "acestep-v15-turbo" / "model.safetensors")),
        ModelConfig(path=str(BASE / "Qwen3-Embedding-0.6B" / "model.safetensors")),
        ModelConfig(path=str(BASE / "vae" / "diffusion_pytorch_model.safetensors")),
    ]
    text_tokenizer_config = ModelConfig(path=str(BASE / "Qwen3-Embedding-0.6B"))
    silence_latent_config = ModelConfig(path=str(BASE / "acestep-v15-turbo" / "silence_latent.pt"))

    t0 = time.time()
    pipe = AceStepPipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=model_configs,
        text_tokenizer_config=text_tokenizer_config,
        silence_latent_config=silence_latent_config,
    )
    # CPU VAE decode for ROCm stability
    pipe.vae = pipe.vae.to(device="cpu", dtype=torch.float32)
    orig_decode = pipe.vae.decode
    pipe.vae.decode = lambda z, **kw: orig_decode(z.to(device="cpu", dtype=torch.float32), **kw)
    orig_load = pipe.load_models_to_device
    pipe.load_models_to_device = lambda names: orig_load([n for n in names if n != "vae"])
    print(f"Loaded ACE-Step Pipeline in {time.time() - t0:.1f}s!", flush=True)

    bgm_prompt = (
        "quirky upbeat interstellar jazz-funk heist comedy soundtrack, bouncy walking bassline, "
        "playful muted brass trumpet stabs, funky wah-wah guitar, witty xylophone accents, "
        "tight swinging drums, groovy cartoon caper vibe, fast-paced comedic rhythm, "
        "Rick and Morty galactic adventure energy, instrumental score, pristine 48kHz stereo"
    )

    print("Generating 70-second 48kHz stereo BGM track (8 steps Turbo)...", flush=True)
    t_gen = time.time()
    audio_tensor = pipe(
        prompt=bgm_prompt,
        lyrics="[instrumental]",
        task_type="text2music",
        duration=70,
        bpm=118,
        keyscale="F major",
        timesignature="4",
        vocal_language="unknown",
        num_inference_steps=8,
        cfg_scale=1.0,
        seed=2026,
    )
    print(f"BGM generated in {time.time() - t_gen:.2f}s! Audio shape: {audio_tensor.shape}", flush=True)

    out_wav = BGM_OUT_DIR / "lottery_heist_jazz_bgm.wav"
    audio_np = audio_tensor.detach().cpu().float().numpy()
    if audio_np.ndim == 3:
        audio_np = audio_np[0]
    if audio_np.ndim == 2:
        audio_np = audio_np.T  # [T, C]
    audio_int16 = np.clip(audio_np * 32767.0, -32768, 32767).astype(np.int16)
    wavfile.write(str(out_wav), 48000, audio_int16)
    print(f"✅ Saved 48kHz BGM to: {out_wav} (Duration: {len(audio_int16)/48000:.2f}s)", flush=True)

if __name__ == "__main__":
    generate_voiceovers()
    generate_bgm()
