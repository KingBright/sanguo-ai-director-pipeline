"""
Colab L4 多模型 (VoxCPM2 + Fun-CosyVoice3-0.5B + IndexTTS 2.5) 云端语音克隆统一执行器
支持：
  1. voxcpm2 (openbmb/VoxCPM2, bfloat16, Ultimate Cloning, 48kHz -> 24kHz PCM_16) [当前默认主力]
  2. cosyvoice3 (FunAudioLLM/Fun-CosyVoice3-0.5B-2512, 零样本多语种克隆 -> 24kHz PCM_16)
  3. indextts25 (IndexTeam/IndexTTS-2.5, bf16/fp16 -> 24kHz PCM_16)
  4. 广播级中文发音增强：多音字上下文词典、古汉及短剧人名专名、数字/日期/百分比/负数/金额展开
  5. 极致情绪表达：IndexTTS 2.5 8D情感向量/参考音频/文本引导解耦，CosyVoice3 Instruct/Emotion 模式
  6. 块级时长与RMS能量校验及自动重试 (防止坏块、静音截断或爆音)
  7. Google Drive 缓存恢复与归档 (/content/drive/MyDrive/FreshLoop_Colab_Cache)
"""
import json
import os
import subprocess
import threading
import time

DRIVE_CACHE_DIR = "/content/drive/MyDrive/FreshLoop_Colab_Cache"
INDEXTTS_TAR = f"{DRIVE_CACHE_DIR}/indextts25_checkpoints.tar"
VOXCPM2_TAR = f"{DRIVE_CACHE_DIR}/voxcpm2_checkpoints.tar"
COSYVOICE3_TAR = f"{DRIVE_CACHE_DIR}/cosyvoice3_checkpoints.tar"


def run_cmd_heartbeat(cmd: str, cwd: str = "/content") -> str:
    print(f"[CMD] {cmd}", flush=True)
    t0 = time.time()
    p = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    stdout_lines = []

    def reader(pipe, is_err=False):
        for line in iter(pipe.readline, ""):
            line_str = line.strip()
            if line_str:
                stdout_lines.append(line_str)
                prefix = "[ERR] " if is_err else ""
                print(f"  {prefix}{line_str}", flush=True)
        pipe.close()

    t_out = threading.Thread(target=reader, args=(p.stdout, False))
    t_err = threading.Thread(target=reader, args=(p.stderr, True))
    t_out.start()
    t_err.start()

    while p.poll() is None:
        time.sleep(15)
        elapsed = int(time.time() - t0)
        print(f"[HEARTBEAT] Command still running ({elapsed}s elapsed)...", flush=True)

    t_out.join()
    t_err.join()
    if p.returncode != 0:
        tail = "\n".join(stdout_lines[-20:])
        raise RuntimeError(f"Command failed (exit={p.returncode}): {cmd}\nTail output:\n{tail}")
    return "\n".join(stdout_lines)


def main():
    if not os.path.exists("/content/tts_jobs.json"):
        raise RuntimeError("No /content/tts_jobs.json found!")

    with open("/content/tts_jobs.json", "r", encoding="utf-8") as f:
        job_spec = json.load(f)

    if isinstance(job_spec, list):
        engine = (job_spec[0].get("engine") if job_spec else "voxcpm2") or "voxcpm2"
    else:
        engine = job_spec.get("engine", "voxcpm2")

    engine = engine.strip().lower()
    print(f"[CLOUD-TTS] Selected engine: {engine}", flush=True)

    # Common Chinese Normalizer & Quality Check Logic
    COMMON_UTILITY_CODE = r'''
DIGIT_MAP = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}

ACRONYM_MAP = {
    "NVLink": "N V Link", "macOS": "Mac O S", "iOS": "i O S", "iPadOS": "iPad O S",
    "SQLite": "S Q Lite", "PCIe": "P C I E", "FP8": "F P 8", "FP16": "F P 16",
    "BF16": "B F 16", "API": "A P I", "GPU": "G P U", "CPU": "C P U",
    "NPU": "N P U", "TPU": "T P U", "CLI": "C L I", "SDK": "S D K",
    "LLM": "L L M", "TTS": "T T S", "ASR": "A S R", "RAG": "R A G",
    "AI": "A I", "ComfyUI": "Comfy U I", "MiniMax": "Mini Max", "Colab": "Co lab",
}

CLASSICAL_DRAMA_MAP = [
    ("诸葛亮", "诸葛亮"), ("司马懿", "司马懿"), ("丞相", "丞相"), ("北伐", "北伐"),
    ("街亭", "街亭"), ("陇右", "陇右"), ("祁山", "祁山"),
    ("羽扇纶巾", "羽扇关巾"), ("纶巾", "关巾"),
    ("单于", "缠于"), ("可汗", "克寒"), ("大月氏", "大肉知"), ("龟兹", "丘慈"), ("吐蕃", "土播"),
]

POLYPHONE_RULES = [
    (r"(银)行", r"\1航"), (r"行(业|情|当)", r"航\1"), (r"(同|内|外|商)行", r"\1航"),
    (r"行(为|走|动|礼)", r"形\1"), (r"(实|履|运|前)行", r"\1形"),
    (r"重(新|复|演|申|逢|建|来|温|塑|置)", r"虫\1"), (r"重(要|量|点|担)", r"仲\1"), (r"(沉|严|体|注)重", r"\1仲"),
    (r"长(大|辈|官)", r"掌\1"), (r"(生|首|局|校|部|组|成)长", r"\1掌"),
    (r"长(短|城|久|远|期|度)", r"尝\1"), (r"(漫)长", r"\1尝"),
    (r"(音|器|奏|交响|管弦|礼)乐", r"\1岳"), (r"乐(器|曲)", r"岳\1"), (r"快(乐)", r"快勒"), (r"乐(观|意|趣|呵呵)", r"勒\1"),
    (r"(王|唐|汉|明|清)朝", r"\1潮"), (r"朝(代|廷|向)", r"潮\1"), (r"朝(阳|夕|气)", r"招\1"), (r"(今)朝", r"\1招"),
    (r"(自|外|列|经)传", r"\1撰"), (r"传(记)", r"撰\1"), (r"传(播|递|承|说|授)", r"船\1"),
    (r"(效|概|频|比|汇|利|税|速|功)率", r"\1绿"), (r"率(领|真|先)", r"帅\1"), (r"(统|直|坦)率", r"\1帅"),
    (r"调(查|研|动|配|度|职|遣)", r"吊\1"), (r"(协)调", r"\1吊"), (r"(声|腔)调", r"\1吊"), (r"调(整|节|和|养|理|味)", r"条\1"),
    (r"着(火|急|凉)", r"召\1"), (r"(睡|没)着", r"\1召"), (r"着(手|眼|重|力|落)", r"酌\1"),
    (r"(必须|总|你)得", r"\1呆"), (r"得(亏)", r"呆\1"), (r"得(到|出|失)", r"德\1"), (r"(获|求|心)得", r"\1德"),
    (r"(土|大|领)地", r"\1弟"), (r"地(面|方|阵)", r"弟\1"),
    (r"了(解|然|结)", r"料\1"), (r"(明)了", r"\1料"), (r"(没完没)了", r"\1料"),
]

def num_to_zh(num_str: str) -> str:
    try:
        val = int(num_str)
    except ValueError:
        return "".join(DIGIT_MAP.get(d, d) for d in num_str)
    if val == 0:
        return "零"
    if 10 <= val <= 19:
        return "十" if val == 10 else "十" + DIGIT_MAP[str(val % 10)]
    s = str(val)
    n = len(s)
    if n > 5:
        return "".join(DIGIT_MAP.get(d, d) for d in s)
    unit_map = ["", "十", "百", "千", "万"]
    res = ""
    zero = False
    for i, ch in enumerate(s):
        d = int(ch)
        u_idx = n - 1 - i
        if d != 0:
            if zero:
                res += "零"
                zero = False
            res += DIGIT_MAP[ch] + unit_map[u_idx]
        else:
            zero = True
    return res.rstrip("零")

def normalize_chinese_text_for_tts(text: str) -> str:
    if not text:
        return ""
    for token, spoken in ACRONYM_MAP.items():
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", spoken, text)
    text = re.sub(r"\b(19\d{2}|20\d{2})\s*年", lambda m: "".join(DIGIT_MAP[d] for d in m.group(1)) + "年", text)
    def _repl_date(m):
        return f"{num_to_zh(m.group(1))}月{num_to_zh(m.group(2))}{m.group(3)}"
    text = re.sub(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*([日号])", _repl_date, text)
    def _repl_pct(m):
        num = m.group(1)
        if "." in num:
            int_p, dec_p = num.split(".", 1)
            dec_zh = "".join(DIGIT_MAP.get(d, d) for d in dec_p)
            return f"百分之{num_to_zh(int_p)}点{dec_zh}"
        return f"百分之{num_to_zh(num)}"
    text = re.sub(r"(?<!\d)(\d+(?:\.\d+)?)\s*%", _repl_pct, text)
    text = re.sub(r"[¥￥]\s*(\d+)", lambda m: f"{num_to_zh(m.group(1))}元", text)
    text = re.sub(r"\$\s*(\d+)", lambda m: f"{num_to_zh(m.group(1))}美元", text)
    def _repl_dec(m):
        int_p, dec_p = m.group(1), m.group(2)
        dec_zh = "".join(DIGIT_MAP.get(d, d) for d in dec_p)
        return f"{num_to_zh(int_p)}点{dec_zh}"
    text = re.sub(r"(?<!\d)(\d+)\.(\d+)(?!\d)", _repl_dec, text)
    text = re.sub(r"(^|[\s，。！？、；：（])\-(\d+)", lambda m: f"{m.group(1)}负{num_to_zh(m.group(2))}", text)
    text = re.sub(r"(?<!\d)(\d{1,5})(?!\d)", lambda m: num_to_zh(m.group(1)), text)
    for src, dst in CLASSICAL_DRAMA_MAP:
        text = text.replace(src, dst)
    for pat, rep in POLYPHONE_RULES:
        text = re.sub(pat, rep, text)
    return re.sub(r"\s+", " ", text).strip()

def validate_audio_chunk(audio, sr: int, text: str, min_rms: float = 0.005, min_dur_per_char: float = 0.12):
    arr = np.asarray(audio, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return False, "Empty audio"
    duration = arr.size / float(sr)
    zh_chars = len(re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]", text))
    if zh_chars >= 2:
        expected_min = zh_chars * min_dur_per_char
        if duration < expected_min:
            return False, f"Duration too short ({duration:.2f}s < {expected_min:.2f}s)"
    rms = float(np.sqrt(np.mean(np.square(arr))))
    if rms < min_rms:
        return False, f"RMS energy too low ({rms:.5f} < {min_rms})"
    peak = float(np.max(np.abs(arr)))
    if peak > 0.999:
        if float(np.mean(np.abs(arr) > 0.995)) > 0.05:
            return False, "Audio clipped"
    return True, f"OK (dur={duration:.2f}s, rms={rms:.4f})"
'''

    if engine == "voxcpm2":
        check_voxcpm = subprocess.run(
            ["python3", "-c", "import voxcpm, soundfile, scipy"],
            capture_output=True,
        )
        if check_voxcpm.returncode != 0:
            run_cmd_heartbeat("pip install -q voxcpm soundfile scipy huggingface_hub")

        voxcpm_dir = "/content/voxcpm2_checkpoints"
        if not os.path.exists(f"{voxcpm_dir}/model.safetensors"):
            if os.path.exists(VOXCPM2_TAR):
                print("[CACHE] Restoring VoxCPM2 checkpoints from Google Drive...", flush=True)
                os.makedirs(voxcpm_dir, exist_ok=True)
                run_cmd_heartbeat(f"tar -xf '{VOXCPM2_TAR}' -C '{voxcpm_dir}'")
            else:
                dl_cmd = (
                    "python3 -c \""
                    "from huggingface_hub import snapshot_download; "
                    f"snapshot_download(repo_id='openbmb/VoxCPM2', local_dir='{voxcpm_dir}')"
                    "\""
                )
                print("[CACHE] Downloading VoxCPM2 from HuggingFace...", flush=True)
                run_cmd_heartbeat(dl_cmd)
                os.makedirs(DRIVE_CACHE_DIR, exist_ok=True)
                print("[CACHE] Archiving VoxCPM2 checkpoints to Google Drive...", flush=True)
                run_cmd_heartbeat(f"tar -cf '{VOXCPM2_TAR}' -C '{voxcpm_dir}' .")

        voxcpm_worker = r'''
import hashlib
import json
import math
import os
import re
import time
import wave
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from voxcpm import VoxCPM

TARGET_SR = 24000
MAX_CHUNK_CHARS = 150
DEFAULT_PROMPT_TEXT = "Hello 大家好，这里是 Fresh Loop 新闻速度，我们将给你带来最新鲜的新闻资讯。"
''' + COMMON_UTILITY_CODE + r'''
def split_sentences(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    text = normalize_chinese_text_for_tts(re.sub(r"\s+", " ", text).strip())
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;\n])", text)
    chunks = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current = f"{current} {part}".strip() if current else part
        else:
            if current:
                chunks.append(current)
            if len(part) <= max_chars:
                current = part
            else:
                subparts = re.split(r"(?<=[，,、：:])", part)
                subcur = ""
                for sp in subparts:
                    sp = sp.strip()
                    if not sp:
                        continue
                    if len(subcur) + len(sp) <= max_chars:
                        subcur = f"{subcur}{sp}"
                    else:
                        if subcur:
                            chunks.append(subcur)
                        subcur = sp
                current = subcur
    if current:
        chunks.append(current)
    return chunks

def postprocess_chunk(audio: np.ndarray, orig_sr: int, target_sr: int = TARGET_SR) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    if audio.size == 0:
        return audio
    audio = audio - float(np.mean(audio))
    if orig_sr != target_sr:
        g = math.gcd(int(orig_sr), int(target_sr))
        audio = resample_poly(audio, int(target_sr) // g, int(orig_sr) // g).astype(np.float32)
    fade_in = min(int(0.015 * target_sr), audio.size // 4)
    fade_out = min(int(0.025 * target_sr), audio.size // 4)
    if fade_in > 0:
        curve = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_in, dtype=np.float32)))
        audio[:fade_in] *= curve
    if fade_out > 0:
        curve = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_out, dtype=np.float32)))
        audio[-fade_out:] *= curve
    return audio

def normalize_segment_loudness(audio: np.ndarray, target_rms: float = 0.085, max_peak: float = 0.891) -> np.ndarray:
    if audio.size == 0:
        return audio
    rms = float(np.sqrt(np.mean(np.square(audio))))
    if rms > 1e-4:
        gain = min(target_rms / rms, 4.0)
        audio = audio * gain
    peak = float(np.max(np.abs(audio)))
    if peak > max_peak:
        audio = audio * (max_peak / peak)
    return np.clip(audio, -1.0, 1.0).astype(np.float32)

def write_parts_if_large(out_path: str, chunk_size_bytes: int = 500 * 1024) -> None:
    if not os.path.exists(out_path):
        return
    with open(out_path, "rb") as f:
        data = f.read()
    total_size = len(data)
    num_parts = (total_size + chunk_size_bytes - 1) // chunk_size_bytes
    if num_parts > 1:
        for idx in range(num_parts):
            chunk = data[idx * chunk_size_bytes : (idx + 1) * chunk_size_bytes]
            with open(f"{out_path}.part{idx}", "wb") as pf:
                pf.write(chunk)
        with open(f"{out_path}.parts", "w", encoding="utf-8") as mf:
            mf.write(f"{num_parts}\n")
    sha_val = hashlib.sha256(data).hexdigest()
    with open(f"{out_path}.sha", "w", encoding="utf-8") as sf_f:
        sf_f.write(f"{sha_val}\n")

with open("/content/tts_jobs.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

jobs = raw if isinstance(raw, list) else raw.get("items", [])
t0 = time.time()
try:
    model = VoxCPM.from_pretrained("/content/voxcpm2_checkpoints", load_denoiser=False, optimize=False)
except TypeError:
    model = VoxCPM.from_pretrained("/content/voxcpm2_checkpoints", load_denoiser=False)
orig_sr = getattr(model, "sample_rate", 48000)
load_seconds = round(time.time() - t0, 2)

results = {"engine": "voxcpm2", "load_seconds": load_seconds, "items": []}

for job in jobs:
    ts = time.time()
    out_path = job["output_path"]
    spk_wav = job["spk_audio_prompt"]
    prompt_text = job.get("prompt_text") or DEFAULT_PROMPT_TEXT
    chunks = split_sentences(job["text"])
    if not chunks:
        raise RuntimeError(f"Empty text for job {job.get('id')}")

    chunk_wavs = []
    pause = np.zeros(int(0.10 * TARGET_SR), dtype=np.float32)
    for c_idx, chunk in enumerate(chunks):
        best_proc = None
        for attempt in range(3):
            try:
                wav = model.generate(
                    text=chunk,
                    prompt_wav_path=spk_wav,
                    prompt_text=prompt_text,
                    reference_wav_path=spk_wav,
                    cfg_value=float(job.get("prosody_weight") or job.get("cfg_value", 2.0)),
                    inference_timesteps=int(job.get("inference_timesteps", 10)),
                )
                proc = postprocess_chunk(wav, orig_sr, TARGET_SR)
                is_valid, reason = validate_audio_chunk(proc, TARGET_SR, chunk)
                if is_valid or attempt == 2:
                    best_proc = proc
                    break
                else:
                    print(f"[RETRY] VoxCPM2 chunk {c_idx+1} attempt {attempt+1} warning: {reason}. Retrying...", flush=True)
            except Exception as e:
                if attempt == 2 and best_proc is None:
                    raise
                print(f"[RETRY] VoxCPM2 chunk {c_idx+1} attempt {attempt+1} exception: {e}", flush=True)

        if best_proc is not None:
            chunk_wavs.append(best_proc)
        if c_idx + 1 < len(chunks):
            chunk_wavs.append(pause)

    full_audio = normalize_segment_loudness(np.concatenate(chunk_wavs))
    sf.write(out_path, full_audio, TARGET_SR, subtype="PCM_16")
    write_parts_if_large(out_path)
    elapsed = time.time() - ts
    audio_secs = full_audio.size / float(TARGET_SR)
    results["items"].append({
        "id": job.get("id", out_path),
        "output_path": out_path,
        "chunks": len(chunks),
        "generation_seconds": round(elapsed, 2),
        "audio_seconds": round(audio_secs, 2),
        "rtf": round(elapsed / max(audio_secs, 1e-6), 3),
        "sample_rate": TARGET_SR,
    })

with open("/content/tts_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("TTS_RESULTS_JSON:" + json.dumps(results, ensure_ascii=False), flush=True)
'''
        with open("/content/run_voxcpm2_jobs.py", "w", encoding="utf-8") as f:
            f.write(voxcpm_worker)
        run_cmd_heartbeat("python3 /content/run_voxcpm2_jobs.py")

    elif engine in ("cosyvoice3", "cosyvoice"):
        cosy_repo_dir = "/content/CosyVoice"
        if not os.path.exists(f"{cosy_repo_dir}/.git"):
            run_cmd_heartbeat("git clone --depth 1 https://github.com/FunAudioLLM/CosyVoice.git /content/CosyVoice")
            run_cmd_heartbeat("pip install -q -r /content/CosyVoice/requirements.txt")

        cosy_model_dir = "/content/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B"
        if not os.path.exists(f"{cosy_model_dir}/cosyvoice3.yaml") and not os.path.exists(f"{cosy_model_dir}/model.safetensors"):
            if os.path.exists(COSYVOICE3_TAR):
                print("[CACHE] Restoring CosyVoice3 checkpoints from Google Drive...", flush=True)
                os.makedirs(cosy_model_dir, exist_ok=True)
                run_cmd_heartbeat(f"tar -xf '{COSYVOICE3_TAR}' -C '{cosy_model_dir}'")
            else:
                dl_cmd = (
                    "python3 -c \""
                    "from huggingface_hub import snapshot_download; "
                    f"snapshot_download(repo_id='FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='{cosy_model_dir}')"
                    "\""
                )
                print("[CACHE] Downloading CosyVoice3 from HuggingFace...", flush=True)
                run_cmd_heartbeat(dl_cmd)
                os.makedirs(DRIVE_CACHE_DIR, exist_ok=True)
                print("[CACHE] Archiving CosyVoice3 checkpoints to Google Drive...", flush=True)
                run_cmd_heartbeat(f"tar -cf '{COSYVOICE3_TAR}' -C '{cosy_model_dir}' .")

        cosyvoice_worker = r'''
import hashlib
import json
import math
import os
import re
import sys
import time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, "/content/CosyVoice")
from cosyvoice.cli.cosyvoice import AutoModel

TARGET_SR = 24000
MAX_CHUNK_CHARS = 160
DEFAULT_PROMPT_TEXT = "Hello 大家好，这里是 Fresh Loop 新闻速度，我们将给你带来最新鲜的新闻资讯。"
''' + COMMON_UTILITY_CODE + r'''
def split_sentences(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    text = normalize_chinese_text_for_tts(re.sub(r"\s+", " ", text).strip())
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;\n])", text)
    chunks = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current = f"{current} {part}".strip() if current else part
        else:
            if current:
                chunks.append(current)
            if len(part) <= max_chars:
                current = part
            else:
                subparts = re.split(r"(?<=[，,、：:])", part)
                subcur = ""
                for sp in subparts:
                    sp = sp.strip()
                    if not sp:
                        continue
                    if len(subcur) + len(sp) <= max_chars:
                        subcur = f"{subcur}{sp}"
                    else:
                        if subcur:
                            chunks.append(subcur)
                        subcur = sp
                current = subcur
    if current:
        chunks.append(current)
    return chunks

def postprocess_chunk(audio: np.ndarray, orig_sr: int, target_sr: int = TARGET_SR) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    if audio.size == 0:
        return audio
    audio = audio - float(np.mean(audio))
    if orig_sr != target_sr:
        g = math.gcd(int(orig_sr), int(target_sr))
        audio = resample_poly(audio, int(target_sr) // g, int(orig_sr) // g).astype(np.float32)
    fade_in = min(int(0.015 * target_sr), audio.size // 4)
    fade_out = min(int(0.025 * target_sr), audio.size // 4)
    if fade_in > 0:
        curve = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_in, dtype=np.float32)))
        audio[:fade_in] *= curve
    if fade_out > 0:
        curve = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_out, dtype=np.float32)))
        audio[-fade_out:] *= curve
    return audio

def normalize_segment_loudness(audio: np.ndarray, target_rms: float = 0.085, max_peak: float = 0.891) -> np.ndarray:
    if audio.size == 0:
        return audio
    rms = float(np.sqrt(np.mean(np.square(audio))))
    if rms > 1e-4:
        gain = min(target_rms / rms, 4.0)
        audio = audio * gain
    peak = float(np.max(np.abs(audio)))
    if peak > max_peak:
        audio = audio * (max_peak / peak)
    return np.clip(audio, -1.0, 1.0).astype(np.float32)

t0 = time.time()
cosyvoice = AutoModel(model_dir="/content/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B")
orig_sr = int(getattr(cosyvoice, "sample_rate", 24000))
load_seconds = round(time.time() - t0, 2)

with open("/content/tts_jobs.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

jobs = raw if isinstance(raw, list) else raw.get("items", [])
results = {"engine": "cosyvoice3", "load_seconds": load_seconds, "items": []}

INSTRUCT_MAP = {
    "angry": "用极其愤怒、严厉质问的语气说",
    "sad": "用悲伤、哽咽低沉的语气说",
    "happy": "用高兴、欢快兴奋的语气说",
    "fearful": "用惊恐、害怕颤抖的语气说",
    "afraid": "用害怕颤抖的语气说",
    "surprised": "用惊讶、难以置信的语气说",
    "calm": "用沉着、冷静平缓的语气说",
    "cold_laugh": "用冷酷、讥讽冷笑的语气说",
    "whisper": "用极轻的耳语、压低声线轻声说",
}

for job in jobs:
    ts = time.time()
    out_path = job["output_path"]
    spk_wav = job["spk_audio_prompt"]
    raw_prompt = (job.get("prompt_text") or DEFAULT_PROMPT_TEXT).strip()
    if "<|endofprompt|>" not in raw_prompt:
        formatted_prompt = f"You are a helpful assistant.<|endofprompt|>{raw_prompt}"
    else:
        formatted_prompt = raw_prompt

    instruct_text = job.get("instruct_text", "")
    emotion = job.get("emotion", "")
    if emotion and not instruct_text:
        instruct_text = INSTRUCT_MAP.get(emotion, "")

    chunks = split_sentences(job["text"])
    if not chunks:
        raise RuntimeError(f"Empty text for job {job.get('id')}")

    chunk_wavs = []
    pause = np.zeros(int(0.08 * TARGET_SR), dtype=np.float32)
    for c_idx, chunk in enumerate(chunks):
        best_proc = None
        for attempt in range(3):
            try:
                sub_wavs = []
                if instruct_text and hasattr(cosyvoice, "inference_instruct"):
                    generator = cosyvoice.inference_instruct(chunk, instruct_text, spk_wav, stream=False)
                else:
                    if emotion in ("whisper", "angry", "happy", "sad"):
                        chunk_to_infer = f"<|{emotion}|>{chunk}" if not chunk.startswith("<|") else chunk
                    else:
                        chunk_to_infer = chunk
                    generator = cosyvoice.inference_zero_shot(chunk_to_infer, formatted_prompt, spk_wav, stream=False)

                for out_dict in generator:
                    tensor_wav = out_dict["tts_speech"].detach().cpu().numpy().reshape(-1)
                    sub_wavs.append(tensor_wav)

                if sub_wavs:
                    combined_sub = np.concatenate(sub_wavs)
                    proc = postprocess_chunk(combined_sub, orig_sr, TARGET_SR)
                    is_valid, reason = validate_audio_chunk(proc, TARGET_SR, chunk)
                    if is_valid or attempt == 2:
                        best_proc = proc
                        break
                    else:
                        print(f"[RETRY] CosyVoice3 chunk {c_idx+1} attempt {attempt+1} warning: {reason}. Retrying...", flush=True)
            except Exception as exc:
                if attempt == 2 and best_proc is None:
                    raise
                print(f"[RETRY] CosyVoice3 chunk {c_idx+1} attempt {attempt+1} exception: {exc}", flush=True)

        if best_proc is not None:
            chunk_wavs.append(best_proc)
        if c_idx + 1 < len(chunks):
            chunk_wavs.append(pause)

    full_audio = normalize_segment_loudness(np.concatenate(chunk_wavs))
    sf.write(out_path, full_audio, TARGET_SR, subtype="PCM_16")
    elapsed = time.time() - ts
    audio_secs = full_audio.size / float(TARGET_SR)
    results["items"].append({
        "id": job.get("id", out_path),
        "output_path": out_path,
        "chunks": len(chunks),
        "generation_seconds": round(elapsed, 2),
        "audio_seconds": round(audio_secs, 2),
        "rtf": round(elapsed / max(audio_secs, 1e-6), 3),
        "sample_rate": TARGET_SR,
    })

with open("/content/tts_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("TTS_RESULTS_JSON:" + json.dumps(results, ensure_ascii=False), flush=True)
'''
        with open("/content/CosyVoice/run_cosyvoice3_jobs.py", "w", encoding="utf-8") as f:
            f.write(cosyvoice_worker)
        run_cmd_heartbeat("python3 /content/CosyVoice/run_cosyvoice3_jobs.py", cwd="/content/CosyVoice")

    else:
        # IndexTTS 2.5 path
        if not os.path.exists("/content/index-tts/.git"):
            run_cmd_heartbeat("git clone --depth 1 https://github.com/index-tts/index-tts.git /content/index-tts")

        if not os.path.exists("/content/index-tts/.venv/bin/python"):
            run_cmd_heartbeat("/usr/local/bin/uv sync --python 3.11", cwd="/content/index-tts")

        if not os.path.exists("/content/index-tts/checkpoints/config.yaml"):
            if os.path.exists(INDEXTTS_TAR):
                print("[CACHE] Restoring IndexTTS-2.5 checkpoints from Google Drive...", flush=True)
                os.makedirs("/content/index-tts/checkpoints", exist_ok=True)
                run_cmd_heartbeat(f"tar -xf '{INDEXTTS_TAR}' -C /content/index-tts/checkpoints")
            else:
                dl_cmd = (
                    "/content/index-tts/.venv/bin/python -c \""
                    "from huggingface_hub import snapshot_download; "
                    "snapshot_download(repo_id='IndexTeam/IndexTTS-2', local_dir='/content/index-tts/checkpoints')\""
                )
                print("[CACHE] Downloading IndexTTS-2.5 from HuggingFace...", flush=True)
                run_cmd_heartbeat(dl_cmd)
                os.makedirs(DRIVE_CACHE_DIR, exist_ok=True)
                print("[CACHE] Archiving IndexTTS-2.5 checkpoints to Google Drive...", flush=True)
                run_cmd_heartbeat(f"tar -cf '{INDEXTTS_TAR}' -C /content/index-tts/checkpoints .")

        indextts_worker = r'''
import hashlib
import json
import math
import os
import re
import sys
import time
import wave
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, "/content/index-tts")
from indextts.infer_v2_5 import IndexTTS2

TARGET_SR = 24000
MAX_CHUNK_CHARS = 160
''' + COMMON_UTILITY_CODE + r'''
def split_sentences(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    text = normalize_chinese_text_for_tts(re.sub(r"\s+", " ", text).strip())
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;\n])", text)
    chunks = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current = f"{current} {part}".strip() if current else part
        else:
            if current:
                chunks.append(current)
            if len(part) <= max_chars:
                current = part
            else:
                subparts = re.split(r"(?<=[，,、：:])", part)
                subcur = ""
                for sp in subparts:
                    sp = sp.strip()
                    if not sp:
                        continue
                    if len(subcur) + len(sp) <= max_chars:
                        subcur = f"{subcur}{sp}"
                    else:
                        if subcur:
                            chunks.append(subcur)
                        subcur = sp
                current = subcur
    if current:
        chunks.append(current)
    return chunks

def postprocess_chunk(audio: np.ndarray, orig_sr: int, target_sr: int = TARGET_SR) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    if audio.size == 0:
        return audio
    audio = audio - float(np.mean(audio))
    if orig_sr != target_sr:
        g = math.gcd(int(orig_sr), int(target_sr))
        audio = resample_poly(audio, int(target_sr) // g, int(orig_sr) // g).astype(np.float32)
    fade_in = min(int(0.015 * target_sr), audio.size // 4)
    fade_out = min(int(0.025 * target_sr), audio.size // 4)
    if fade_in > 0:
        curve = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_in, dtype=np.float32)))
        audio[:fade_in] *= curve
    if fade_out > 0:
        curve = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_out, dtype=np.float32)))
        audio[-fade_out:] *= curve
    return audio

def normalize_segment_loudness(audio: np.ndarray, target_rms: float = 0.085, max_peak: float = 0.891) -> np.ndarray:
    if audio.size == 0:
        return audio
    rms = float(np.sqrt(np.mean(np.square(audio))))
    if rms > 1e-4:
        gain = min(target_rms / rms, 4.0)
        audio = audio * gain
    peak = float(np.max(np.abs(audio)))
    if peak > max_peak:
        audio = audio * (max_peak / peak)
    return np.clip(audio, -1.0, 1.0).astype(np.float32)

EMOTION_PRESETS = {
    "happy": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "angry": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "sad": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "fearful": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    "afraid": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    "disgusted": [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    "melancholic": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
    "surprised": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
    "calm": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    "cold_laugh": [0.15, 0.45, 0.0, 0.0, 0.40, 0.0, 0.0, 0.20],
    "whisper": [0.0, 0.0, 0.15, 0.0, 0.0, 0.25, 0.0, 0.85],
}

t0 = time.time()
tts = IndexTTS2(
    cfg_path="/content/index-tts/checkpoints/config.yaml",
    model_dir="/content/index-tts/checkpoints",
    use_bf16=True,
)
load_seconds = round(time.time() - t0, 2)

with open("/content/tts_jobs.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

jobs = raw if isinstance(raw, list) else raw.get("items", [])
results = {"engine": "indextts25", "load_seconds": load_seconds, "items": []}

for job in jobs:
    ts = time.time()
    out_path = job["output_path"]
    spk_wav = job["spk_audio_prompt"]

    emo_vec = None
    if job.get("emotion") in EMOTION_PRESETS:
        emo_vec = EMOTION_PRESETS[job["emotion"]]
    elif job.get("emo_vector"):
        try:
            emo_vec = json.loads(job["emo_vector"]) if isinstance(job["emo_vector"], str) else job["emo_vector"]
        except Exception:
            emo_vec = None

    emo_alpha = float(job.get("emo_alpha", 0.40)) if job.get("emo_alpha") is not None else 0.40
    emo_audio = job.get("emo_audio")
    emo_text = job.get("emo_text")

    chunks = split_sentences(job["text"])
    if not chunks:
        raise RuntimeError(f"Empty text for job {job.get('id')}")

    chunk_wavs = []
    pause = np.zeros(int(0.08 * TARGET_SR), dtype=np.float32)
    tmp_chunk_path = "/content/_tmp_indextts_chunk.wav"

    for c_idx, chunk in enumerate(chunks):
        best_proc = None
        for attempt in range(3):
            infer_kwargs = {
                "spk_audio_prompt": spk_wav,
                "text": chunk,
                "lang": job.get("lang", "ZH"),
                "output_path": tmp_chunk_path,
                "verbose": False,
            }
            if emo_audio and os.path.exists(emo_audio):
                infer_kwargs["emo_audio_prompt"] = emo_audio
            if emo_vec is not None:
                infer_kwargs["emo_vector"] = emo_vec
            if emo_alpha is not None:
                infer_kwargs["emo_alpha"] = emo_alpha
            if emo_text:
                infer_kwargs["emo_text"] = emo_text

            try:
                tts.infer(**infer_kwargs)
                wav_data, sr = sf.read(tmp_chunk_path, dtype="float32")
                proc = postprocess_chunk(wav_data, sr, TARGET_SR)
                is_valid, reason = validate_audio_chunk(proc, TARGET_SR, chunk)
                if is_valid or attempt == 2:
                    best_proc = proc
                    break
                else:
                    print(f"[RETRY] IndexTTS2.5 chunk {c_idx+1} attempt {attempt+1} warning: {reason}. Retrying...", flush=True)
            except Exception as exc:
                if attempt == 2 and best_proc is None:
                    raise
                print(f"[RETRY] IndexTTS2.5 chunk {c_idx+1} attempt {attempt+1} exception: {exc}. Retrying...", flush=True)

        if best_proc is not None:
            chunk_wavs.append(best_proc)
        if c_idx + 1 < len(chunks):
            chunk_wavs.append(pause)

    full_audio = normalize_segment_loudness(np.concatenate(chunk_wavs))
    sf.write(out_path, full_audio, TARGET_SR, subtype="PCM_16")
    elapsed = time.time() - ts
    audio_secs = full_audio.size / float(TARGET_SR)
    results["items"].append({
        "id": job.get("id", out_path),
        "output_path": out_path,
        "chunks": len(chunks),
        "generation_seconds": round(elapsed, 2),
        "audio_seconds": round(audio_secs, 2),
        "rtf": round(elapsed / max(audio_secs, 1e-6), 3),
        "sample_rate": TARGET_SR,
        "emotion": job.get("emotion"),
        "emo_alpha": emo_alpha,
    })

with open("/content/tts_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("TTS_RESULTS_JSON:" + json.dumps(results, ensure_ascii=False), flush=True)
'''
        with open("/content/index-tts/run_indextts25_jobs.py", "w", encoding="utf-8") as f:
            f.write(indextts_worker)
        run_cmd_heartbeat("/content/index-tts/.venv/bin/python /content/index-tts/run_indextts25_jobs.py", cwd="/content/index-tts")


if __name__ == "__main__":
    main()
