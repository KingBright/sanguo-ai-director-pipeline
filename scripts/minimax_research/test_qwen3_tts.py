import time
import torch
import soundfile as sf
from pathlib import Path
from qwen_tts import Qwen3TTSModel

BASE_CLONE = Path(r"C:\Users\Liang\minimax\Qwen3-TTS-12Hz-1.7B-Base")
BASE_DESIGN = Path(r"C:\Users\Liang\minimax\Qwen3-TTS-12Hz-1.7B-VoiceDesign")
VOICE_DIR = Path(r"c:\Users\Liang\Downloads\sanguo\assets\voices")
OUT_DIR = Path(r"c:\Users\Liang\Downloads\sanguo\assets\renders")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 65, flush=True)
    print("[START] Testing Qwen3-TTS (Voice Clone + Voice Design) on ROCm gfx1151", flush=True)
    print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)
    print("=" * 65, flush=True)

    # 1. Test Voice Clone from 48kHz anchor (温厚沉稳青年男声-v1.wav + 低沉沧桑中年男声-v1.wav)
    t0 = time.time()
    print("[1/2] Loading Qwen3-TTS-12Hz-1.7B-Base (Zero-Shot Voice Clone)...", flush=True)
    clone_model = Qwen3TTSModel.from_pretrained(
        str(BASE_CLONE),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    print(f"Loaded Base model in {time.time() - t0:.1f}s!", flush=True)

    ref_zhuge = str(VOICE_DIR / "温厚沉稳青年男声-v1.wav")
    ref_weiyan = str(VOICE_DIR / "磁性沧桑中年男声-v1.wav")

    t1 = time.time()
    print("Cloning Zhuge Liang voice ('温厚沉稳青年男声-v1.wav') for Northern Expedition (出师表)...", flush=True)
    wavs_zhuge, sr_zhuge = clone_model.generate_voice_clone(
        text="先帝创业未半而中道崩殂，今天下三分，益州疲弊，此诚危急存亡之秋也。今南方已定，兵甲已足，当奖率三军，北定中原！",
        language="Chinese",
        ref_audio=ref_zhuge,
        x_vector_only_mode=True,
        max_new_tokens=300,
    )
    out_zhuge = OUT_DIR / "test_qwen3_tts_clone_zhuge.wav"
    sf.write(str(out_zhuge), wavs_zhuge[0], sr_zhuge)
    print(f"[DONE] Zhuge Liang cloned speech saved ({len(wavs_zhuge[0])/sr_zhuge:.2f}s @ {sr_zhuge}Hz) in {time.time() - t1:.2f}s -> {out_zhuge}", flush=True)

    t2 = time.time()
    print("Cloning Wei Yan voice ('磁性沧桑中年男声-v1.wav') for Ziwu Valley strategy...", flush=True)
    wavs_weiyan, sr_weiyan = clone_model.generate_voice_clone(
        text="丞相！某愿得精兵五千，直出子午谷，十日之内必至长安！夏侯楙怯而无谋，闻某卒至，必弃城横走！",
        language="Chinese",
        ref_audio=ref_weiyan,
        x_vector_only_mode=True,
        max_new_tokens=300,
    )
    out_weiyan = OUT_DIR / "test_qwen3_tts_clone_weiyan.wav"
    sf.write(str(out_weiyan), wavs_weiyan[0], sr_weiyan)
    print(f"[DONE] Wei Yan cloned speech saved ({len(wavs_weiyan[0])/sr_weiyan:.2f}s @ {sr_weiyan}Hz) in {time.time() - t2:.2f}s -> {out_weiyan}", flush=True)

    del clone_model
    torch.cuda.empty_cache()

    # 2. Test Voice Design (Natural Language Emotion & Persona Control)
    t3 = time.time()
    print("[2/2] Loading Qwen3-TTS-12Hz-1.7B-VoiceDesign (Emotional Voice Design)...", flush=True)
    design_model = Qwen3TTSModel.from_pretrained(
        str(BASE_DESIGN),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    print(f"Loaded VoiceDesign model in {time.time() - t3:.1f}s!", flush=True)

    t4 = time.time()
    print("Generating Older Zhuge Liang at Wuzhang Plains with emotional VoiceDesign...", flush=True)
    wavs_design, sr_design = design_model.generate_voice_design(
        text="臣鞠躬尽瘁，死而后已。至于成败利钝，非臣之明所能逆睹也……悠悠苍天，何薄于我！",
        language="Chinese",
        instruct="苍老、悲壮而威严的五十岁古代丞相男声，声音低沉沙哑，前半段坚定沉稳，后半段带着心力交瘁的叹息与悲愤颤抖，极富影视剧感染力。",
        max_new_tokens=300,
    )
    out_design = OUT_DIR / "test_qwen3_tts_design_zhuge_wuzhang.wav"
    sf.write(str(out_design), wavs_design[0], sr_design)
    print(f"[DONE] Emotional VoiceDesign speech saved ({len(wavs_design[0])/sr_design:.2f}s @ {sr_design}Hz) in {time.time() - t4:.2f}s -> {out_design}", flush=True)

    print("\n[SUCCESS] All Qwen3-TTS Voice Clone & Voice Design tests passed!", flush=True)

if __name__ == "__main__":
    main()
