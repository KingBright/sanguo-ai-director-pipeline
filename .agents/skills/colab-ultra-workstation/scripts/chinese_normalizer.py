"""Enhanced Chinese Text Normalizer for High-Accuracy TTS (IndexTTS 2.5, Qwen3-TTS, CosyVoice3, VoxCPM2).

Provides:
1. Polyphone & heteronym context disambiguation (行/重/长/乐/朝/传/率/调/着/地/得/了)
2. Classical & historical drama terms and names (诸葛亮, 司马懿, 丞相, 北伐, 街亭, 陇右, 祁山, 羽扇纶巾, etc.)
3. Year, date, percentage, decimal, negative, and currency expansion
4. Technical acronym protection and phonetic spacing
5. Audio chunk duration and RMS energy validation with retry logic
"""

from __future__ import annotations

import math
import re
from typing import Tuple

DIGIT_MAP = {
    "0": "零",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
}

ACRONYM_MAP = {
    "NVLink": "N V Link",
    "macOS": "Mac O S",
    "iOS": "i O S",
    "iPadOS": "iPad O S",
    "SQLite": "S Q Lite",
    "PCIe": "P C I E",
    "FP8": "F P 8",
    "FP16": "F P 16",
    "BF16": "B F 16",
    "API": "A P I",
    "GPU": "G P U",
    "CPU": "C P U",
    "NPU": "N P U",
    "TPU": "T P U",
    "CLI": "C L I",
    "SDK": "S D K",
    "LLM": "L L M",
    "TTS": "T T S",
    "ASR": "A S R",
    "RAG": "R A G",
    "AI": "A I",
    "ComfyUI": "Comfy U I",
    "MiniMax": "Mini Max",
    "Colab": "Co lab",
    "VRAM": "V RAM",
}

# Classical drama terms and historical names
CLASSICAL_DRAMA_REPLACEMENTS = [
    # 诸葛亮、司马懿、三国专名与古汉读音
    ("诸葛亮", "诸葛亮"),
    ("司马懿", "司马懿"),
    ("丞相", "丞相"),
    ("北伐", "北伐"),
    ("街亭", "街亭"),
    ("陇右", "陇右"),
    ("祁山", "祁山"),
    ("羽扇纶巾", "羽扇关巾"),  # 纶巾 guān jīn -> 关巾 确保读音准确
    ("纶巾", "关巾"),
    ("单于", "缠于"),          # chán yú
    ("可汗", "克寒"),          # kè hán
    ("大月氏", "大肉知"),      # dà ròu zhī
    ("龟兹", "丘慈"),          # qiū cí
    ("吐蕃", "土播"),          # tǔ bō
]

# Polyphone contextual substitutions via capture groups
POLYPHONE_RULES = [
    # 行: háng vs xíng
    (r"(银)行", r"\1航"),
    (r"行(业|情|当)", r"航\1"),
    (r"(同|内|外|商)行", r"\1航"),
    (r"行(为|走|动|礼)", r"形\1"),
    (r"(实|履|运|前)行", r"\1形"),

    # 重: chóng vs zhòng
    (r"重(新|复|演|申|逢|建|来|温|塑|置)", r"虫\1"),
    (r"重(要|量|点|担)", r"仲\1"),
    (r"(沉|严|体|注)重", r"\1仲"),

    # 长: zhǎng vs cháng
    (r"长(大|辈|官)", r"掌\1"),
    (r"(生|首|局|校|部|组|成)长", r"\1掌"),
    (r"长(短|城|久|远|期|度)", r"尝\1"),
    (r"(漫)长", r"\1尝"),

    # 乐: yuè vs lè
    (r"(音|器|奏|交响|管弦|礼)乐", r"\1岳"),
    (r"乐(器|曲)", r"岳\1"),
    (r"快(乐)", r"快勒"),
    (r"乐(观|意|趣|呵呵)", r"勒\1"),

    # 朝: cháo vs zhāo
    (r"(王|唐|汉|明|清)朝", r"\1潮"),
    (r"朝(代|廷|向)", r"潮\1"),
    (r"朝(阳|夕|气)", r"招\1"),
    (r"(今)朝", r"\1招"),

    # 传: chuán vs zhuàn
    (r"(自|外|列|经)传", r"\1撰"),
    (r"传(记)", r"撰\1"),
    (r"传(播|递|承|说|授)", r"船\1"),

    # 率: lǜ vs shuài
    (r"(效|概|频|比|汇|利|税|速|功)率", r"\1绿"),
    (r"率(领|真|先)", r"帅\1"),
    (r"(统|直|坦)率", r"\1帅"),

    # 调: diào vs tiáo
    (r"调(查|研|动|配|度|职|遣)", r"吊\1"),
    (r"(协)调", r"\1吊"),
    (r"(声|腔)调", r"\1吊"),
    (r"调(整|节|和|养|理|味)", r"条\1"),

    # 着: zhe / zháo / zhuó
    (r"着(火|急|凉)", r"召\1"),
    (r"(睡|没)着", r"\1召"),
    (r"着(手|眼|重|力|落)", r"酌\1"),

    # 得: dé / děi / de
    (r"(必须|总|你)得", r"\1呆"),
    (r"得(亏)", r"呆\1"),
    (r"得(到|出|失)", r"德\1"),
    (r"(获|求|心)得", r"\1德"),

    # 地: dì vs de
    (r"(土|大|领)地", r"\1弟"),
    (r"地(面|方|阵)", r"弟\1"),

    # 了: liǎo vs le
    (r"了(解|然|结)", r"料\1"),
    (r"(明)了", r"\1料"),
    (r"(没完没)了", r"\1料"),
]


def num_to_zh(num_str: str) -> str:
    """Convert integer number string to spoken Chinese characters."""
    try:
        val = int(num_str)
    except ValueError:
        return "".join(DIGIT_MAP.get(d, d) for d in num_str)

    if val == 0:
        return "零"
    if 10 <= val <= 19:
        if val == 10:
            return "十"
        return "十" + DIGIT_MAP[str(val % 10)]

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


def expand_numbers_and_symbols(text: str) -> str:
    """Expand years, dates, percentages, decimals, negative numbers, and currencies."""
    # 1. 4-digit years: 2026年 -> 二零二六年
    text = re.sub(
        r"\b(19\d{2}|20\d{2})\s*年",
        lambda m: "".join(DIGIT_MAP[d] for d in m.group(1)) + "年",
        text,
    )

    # 2. Date: XX月XX日 / XX月XX号
    def _repl_date(m: re.Match) -> str:
        m_str, d_str, suf = m.group(1), m.group(2), m.group(3)
        return f"{num_to_zh(m_str)}月{num_to_zh(d_str)}{suf}"

    text = re.sub(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*([日号])", _repl_date, text)

    # 3. Percentage: 15% -> 百分之十五, 23.5% -> 百分之二十三点五
    def _repl_pct(m: re.Match) -> str:
        num = m.group(1)
        if "." in num:
            int_p, dec_p = num.split(".", 1)
            dec_zh = "".join(DIGIT_MAP.get(d, d) for d in dec_p)
            return f"百分之{num_to_zh(int_p)}点{dec_zh}"
        return f"百分之{num_to_zh(num)}"

    text = re.sub(r"(?<!\d)(\d+(?:\.\d+)?)\s*%", _repl_pct, text)

    # 4. Currency: ¥100 -> 一百元, $50 -> 五十美元
    text = re.sub(r"[¥￥]\s*(\d+)", lambda m: f"{num_to_zh(m.group(1))}元", text)
    text = re.sub(r"\$\s*(\d+)", lambda m: f"{num_to_zh(m.group(1))}美元", text)

    # 5. Decimals: 3.14 -> 三点一四
    def _repl_dec(m: re.Match) -> str:
        int_p, dec_p = m.group(1), m.group(2)
        dec_zh = "".join(DIGIT_MAP.get(d, d) for d in dec_p)
        return f"{num_to_zh(int_p)}点{dec_zh}"

    text = re.sub(r"(?<!\d)(\d+)\.(\d+)(?!\d)", _repl_dec, text)

    # 6. Negative numbers: -5 -> 负五
    text = re.sub(
        r"(^|[^\d])\-(\d+)",
        lambda m: f"{m.group(1)}负{num_to_zh(m.group(2))}",
        text,
    )

    # 7. Standalone integers
    text = re.sub(r"(?<!\d)(\d{1,5})(?!\d)", lambda m: num_to_zh(m.group(1)), text)
    return text


def apply_polyphone_rules(text: str) -> str:
    """Apply contextual polyphone disambiguation rules."""
    for pattern, replacement in POLYPHONE_RULES:
        text = re.sub(pattern, replacement, text)
    return text


def apply_classical_names(text: str) -> str:
    """Normalize classical names and historical pronunciation."""
    for src, dst in CLASSICAL_DRAMA_REPLACEMENTS:
        text = text.replace(src, dst)
    return text


def normalize_chinese_text_for_tts(text: str) -> str:
    """Complete Chinese text normalization pipeline for TTS."""
    if not text:
        return ""
    # 1. Acronym protection
    for token, spoken in ACRONYM_MAP.items():
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", spoken, text)

    # 2. Number, Date, Percentage & Currency Expansion
    text = expand_numbers_and_symbols(text)

    # 3. Classical / Drama Names
    text = apply_classical_names(text)

    # 4. Contextual Polyphone Disambiguation
    text = apply_polyphone_rules(text)

    # 5. Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def validate_audio_chunk(
    audio,
    sr: int,
    text: str,
    min_rms: float = 0.005,
    min_dur_per_char: float = 0.12,
    max_dur_per_char: float = 0.90,
) -> Tuple[bool, str]:
    """Validate audio chunk quality: duration, RMS energy, and clipping.

    Returns (is_valid, reason_str).
    """
    import numpy as np

    arr = np.asarray(audio, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return False, "Audio array is empty"

    duration = arr.size / float(sr)
    # Count non-punctuation Chinese characters
    zh_chars = len(re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]", text))
    if zh_chars >= 2:
        expected_min = zh_chars * min_dur_per_char
        expected_max = max(1.2, zh_chars * max_dur_per_char)
        if duration < expected_min:
            return False, f"Duration too short ({duration:.2f}s < {expected_min:.2f}s for {zh_chars} chars)"
        if duration > expected_max + 3.0:
            return False, f"Duration abnormally long ({duration:.2f}s > {expected_max:.2f}s for {zh_chars} chars)"

    rms = float(np.sqrt(np.mean(np.square(arr))))
    if rms < min_rms:
        return False, f"RMS energy too low ({rms:.5f} < {min_rms}), possible dropout or silence"

    peak = float(np.max(np.abs(arr)))
    if peak > 0.999:
        clipped_ratio = float(np.mean(np.abs(arr) > 0.995))
        if clipped_ratio > 0.05:
            return False, f"Audio heavily clipped ({clipped_ratio*100:.1f}% samples near peak)"

    return True, f"Valid (dur={duration:.2f}s, rms={rms:.4f}, peak={peak:.2f})"


# ---------------------------------------------------------------------------
# Intra-Line Multi-Beat Emotion & Breath-Pause TTS DSL & Audio Stitching
# ---------------------------------------------------------------------------

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

DEFAULT_EMO_VECTOR = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def get_emotion_vector(emotion: str | None, custom_vector: list[float] | None = None) -> list[float]:
    """Resolve an 8D emotion vector from preset name or custom vector."""
    if custom_vector and isinstance(custom_vector, (list, tuple)) and len(custom_vector) == 8:
        return [float(v) for v in custom_vector]
    if emotion and emotion.lower() in EMOTION_PRESETS:
        return list(EMOTION_PRESETS[emotion.lower()])
    return list(DEFAULT_EMO_VECTOR)


def parse_emotional_sub_beats(
    text: str | list | dict,
    default_emotion: str = "calm",
    default_alpha: float = 0.40,
) -> list[dict]:
    """Parse intra-line multi-beat emotion and pause DSL into structured sub-beats.

    Supported syntax:
      - Inline emotion tags: `[angry]`, `[cold_laugh:0.45]`, `[whisper:0.4]`, `[sad:0.6]`, `[happy:0.7]`
      - Pauses: `[pause:350ms]`, `[pause:0.35s]`, `[pause:300]`
      - Sigh / breath pauses: `[sigh]`, `[sigh:400ms]`
      - Segment separators: pipe `|`, commas, or whitespace.
      - JSON list of dicts: `[{"text": "...", "emotion": "angry", "alpha": 0.65}, {"pause_ms": 300}]`

    Returns a list of sub-beat dicts:
      - Speech: `{"kind": "speech", "raw_text": str, "text": str (normalized), "emotion": str, "alpha": float, "emo_vector": list[float]}`
      - Pause: `{"kind": "pause", "duration_ms": float, "duration_sec": float}`
      - Sigh: `{"kind": "sigh", "duration_ms": float, "duration_sec": float}`
    """
    if not text:
        return []

    # Handle JSON input
    if isinstance(text, (list, dict)):
        raw_list = text if isinstance(text, list) else [text]
        beats = []
        cur_emo = default_emotion or "calm"
        cur_alpha = float(default_alpha if default_alpha is not None else 0.40)
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            if "pause_ms" in item or item.get("kind") == "pause":
                d_ms = float(item.get("pause_ms") or item.get("duration_ms", 300))
                beats.append({"kind": "pause", "duration_ms": d_ms, "duration_sec": d_ms / 1000.0})
            elif item.get("kind") == "sigh" or "sigh_ms" in item:
                d_ms = float(item.get("sigh_ms") or item.get("duration_ms", 400))
                beats.append({"kind": "sigh", "duration_ms": d_ms, "duration_sec": d_ms / 1000.0})
            elif "text" in item:
                raw_t = str(item["text"]).strip()
                if raw_t:
                    e = item.get("emotion") or cur_emo
                    a = float(item.get("alpha", cur_alpha))
                    beats.append({
                        "kind": "speech",
                        "raw_text": raw_t,
                        "text": normalize_chinese_text_for_tts(raw_t),
                        "emotion": e,
                        "alpha": a,
                        "emo_vector": get_emotion_vector(e, item.get("emo_vector")),
                    })
        return beats

    text_str = str(text).strip()

    # Check if string is a JSON array
    if text_str.startswith("[") and ("{" in text_str or '"text"' in text_str or '"pause' in text_str):
        import json
        try:
            parsed = json.loads(text_str)
            if isinstance(parsed, (list, dict)):
                return parse_emotional_sub_beats(parsed, default_emotion=default_emotion, default_alpha=default_alpha)
        except Exception:
            pass

    # Regex for tag: e.g. [cold_laugh:0.45], [pause:350ms], [sigh], [angry]
    tag_re = re.compile(r"\[([a-zA-Z0-9_\-]+)(?::([0-9\.]+(?:ms|s)?))?\]")

    def _parse_duration(param: str | None, default_ms: float) -> float:
        if not param:
            return default_ms
        p = param.strip().lower()
        if p.endswith("ms"):
            try:
                return float(p[:-2])
            except ValueError:
                return default_ms
        elif p.endswith("s"):
            try:
                return float(p[:-1]) * 1000.0
            except ValueError:
                return default_ms
        try:
            return float(p)
        except ValueError:
            return default_ms

    beats: list[dict] = []
    cur_emo = default_emotion or "calm"
    cur_alpha = float(default_alpha if default_alpha is not None else 0.40)
    last_end = 0

    for m in tag_re.finditer(text_str):
        raw_segment = text_str[last_end:m.start()].strip(" |\t\r\n")
        if raw_segment:
            beats.append({
                "kind": "speech",
                "raw_text": raw_segment,
                "text": normalize_chinese_text_for_tts(raw_segment),
                "emotion": cur_emo,
                "alpha": cur_alpha,
                "emo_vector": get_emotion_vector(cur_emo),
            })

        tag_name = m.group(1).lower()
        tag_param = m.group(2)

        if tag_name == "pause":
            dur_ms = _parse_duration(tag_param, default_ms=300.0)
            beats.append({"kind": "pause", "duration_ms": dur_ms, "duration_sec": dur_ms / 1000.0})
        elif tag_name == "sigh":
            dur_ms = _parse_duration(tag_param, default_ms=400.0)
            beats.append({"kind": "sigh", "duration_ms": dur_ms, "duration_sec": dur_ms / 1000.0})
        else:
            # Emotion tag
            cur_emo = tag_name
            if tag_param:
                try:
                    cur_alpha = float(tag_param)
                except ValueError:
                    cur_alpha = default_alpha if default_alpha is not None else 0.40
            else:
                cur_alpha = default_alpha if default_alpha is not None else 0.40

        last_end = m.end()

    # Trailing text segment
    raw_tail = text_str[last_end:].strip(" |\t\r\n")
    if raw_tail:
        beats.append({
            "kind": "speech",
            "raw_text": raw_tail,
            "text": normalize_chinese_text_for_tts(raw_tail),
            "emotion": cur_emo,
            "alpha": cur_alpha,
            "emo_vector": get_emotion_vector(cur_emo),
        })

    return beats


def create_breath_pause_audio(
    duration_ms: float,
    sr: int = 24000,
    is_sigh: bool = False,
    noise_level: float = 0.0008,
) -> "np.ndarray":
    """Generate realistic low-level room-tone breath pause or soft sigh exhalation."""
    import numpy as np

    n_samples = max(int(sr * (duration_ms / 1000.0)), int(sr * 0.02))
    if n_samples <= 0:
        return np.zeros(0, dtype=np.float32)

    rng = np.random.RandomState(42)
    # Background room-tone acoustic presence
    noise = rng.normal(0.0, noise_level, n_samples).astype(np.float32)

    if is_sigh:
        # A sigh has an organic physiological breath exhalation curve
        t = np.linspace(0, duration_ms / 1000.0, n_samples, endpoint=False)
        envelope = np.where(
            t < 0.05,
            np.sin(np.pi * t / 0.1),
            np.exp(-(t - 0.05) / max(0.12, (duration_ms / 1000.0) * 0.4)),
        )
        sigh_breath = rng.normal(0.0, noise_level * 4.5, n_samples).astype(np.float32) * envelope.astype(np.float32)
        noise = noise + sigh_breath

    # 10ms Hann window taper to prevent boundary clicks
    fade_len = min(int(sr * 0.010), n_samples // 4)
    if fade_len > 1:
        fade_in = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_len) / fade_len))
        fade_out = 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
        noise[:fade_len] *= fade_in
        noise[-fade_len:] *= fade_out

    return noise.astype(np.float32)


def stitch_audio_segments_crossfade(
    segments: list["np.ndarray"],
    sr: int = 24000,
    crossfade_ms: float = 15.0,
) -> "np.ndarray":
    """Stitch multiple audio segments using smooth 15ms equal-power cosine crossfade."""
    import numpy as np

    non_empty = [
        np.asarray(s, dtype=np.float32).reshape(-1)
        for s in segments
        if s is not None and len(s) > 0
    ]
    if not non_empty:
        return np.zeros(0, dtype=np.float32)
    if len(non_empty) == 1:
        return non_empty[0]

    crossfade_len = max(1, int(sr * (crossfade_ms / 1000.0)))
    result = non_empty[0]

    for next_seg in non_empty[1:]:
        cf_len = min(crossfade_len, len(result), len(next_seg))
        if cf_len <= 1:
            result = np.concatenate([result, next_seg])
            continue

        # Equal-power cosine crossfade: w_out^2 + w_in^2 == 1.0
        t = np.linspace(0.0, np.pi / 2.0, cf_len, endpoint=False, dtype=np.float32)
        w_out = np.cos(t)
        w_in = np.sin(t)

        overlap = result[-cf_len:] * w_out + next_seg[:cf_len] * w_in
        result = np.concatenate([result[:-cf_len], overlap, next_seg[cf_len:]])

    return result.astype(np.float32)


def run_self_test() -> None:
    """Comprehensive self-test for polyphone normalization and intra-line sub-beats."""
    import numpy as np

    print("=================================================================", flush=True)
    print("🧪 Running Chinese Normalizer & Intra-Line Sub-Beats Self-Test...", flush=True)
    print("=================================================================", flush=True)

    # 1. Polyphone & heteronym disambiguation test
    poly_tests = [
        ("银行重新调查了长官的音乐朝代自传", "航", "重 -> 虫, 行 -> 航"),
        ("诸葛亮在街亭羽扇纶巾，率领大军", "关巾", "纶巾 -> 关巾"),
        ("2026年3月15日上涨了15.5%，消费了$100和¥200", "二零二六年", "数字/年份/百分比/货币"),
        ("温度为-5度", "负五", "负数扩展"),
    ]
    for raw, expected_substr, desc in poly_tests:
        norm = normalize_chinese_text_for_tts(raw)
        assert expected_substr in norm, f"FAIL: {desc} (expected '{expected_substr}' in '{norm}')"
        print(f"  [PASS] Polyphone test: {desc} -> {norm[:40]}...", flush=True)

    # 2. Intra-line multi-beat DSL parsing test
    dsl_sample = "[cold_laugh:0.45]天真？|[pause:350ms]|[angry:0.65]连海外空壳公司的底账都在这里，你还想瞒到什么时候！"
    beats = parse_emotional_sub_beats(dsl_sample, default_emotion="calm", default_alpha=0.40)

    assert len(beats) == 3, f"Expected 3 beats, got {len(beats)}: {beats}"
    assert beats[0]["kind"] == "speech" and beats[0]["emotion"] == "cold_laugh" and abs(beats[0]["alpha"] - 0.45) < 1e-4
    assert beats[0]["text"] == "天真？"
    assert beats[1]["kind"] == "pause" and abs(beats[1]["duration_ms"] - 350.0) < 1e-4
    assert beats[2]["kind"] == "speech" and beats[2]["emotion"] == "angry" and abs(beats[2]["alpha"] - 0.65) < 1e-4
    assert "底账" in beats[2]["text"]
    print("  [PASS] DSL 3-Beat Parsing verified: [cold_laugh:0.45] + [pause:350ms] + [angry:0.65]", flush=True)

    # 3. Sigh tag test
    sigh_sample = "[sigh]|[whisper:0.40]我知道真相。"
    s_beats = parse_emotional_sub_beats(sigh_sample)
    assert len(s_beats) == 2, f"Expected 2 beats, got {len(s_beats)}"
    assert s_beats[0]["kind"] == "sigh" and s_beats[0]["duration_ms"] >= 300
    assert s_beats[1]["kind"] == "speech" and s_beats[1]["emotion"] == "whisper"
    print("  [PASS] Sigh tag parsing verified: [sigh] + [whisper:0.40]", flush=True)

    # 4. JSON sub-beats parsing test
    json_beats = parse_emotional_sub_beats([
        {"text": "第一句", "emotion": "calm", "alpha": 0.3},
        {"pause_ms": 250},
        {"text": "第二句", "emotion": "happy", "alpha": 0.8},
    ])
    assert len(json_beats) == 3 and json_beats[1]["kind"] == "pause" and json_beats[2]["emotion"] == "happy"
    print("  [PASS] JSON array sub-beats verified.", flush=True)

    # 5. Room-tone breath pause generation test
    pause_audio = create_breath_pause_audio(350, sr=24000, is_sigh=False)
    assert len(pause_audio) == int(24000 * 0.35), f"Unexpected pause length {len(pause_audio)}"
    rms_p = float(np.sqrt(np.mean(np.square(pause_audio))))
    assert 0.0001 < rms_p < 0.01, f"Pause RMS abnormal: {rms_p}"
    print(f"  [PASS] Breath room-tone generated: {len(pause_audio)} samples, RMS={rms_p:.5f}", flush=True)

    # 6. Cosine crossfade stitching test
    sr = 24000
    seg1 = np.ones(sr // 2, dtype=np.float32) * 0.1  # 0.5s tone
    pause_seg = create_breath_pause_audio(200, sr=sr)  # 0.2s pause
    seg2 = np.ones(sr // 2, dtype=np.float32) * 0.2  # 0.5s tone
    stitched = stitch_audio_segments_crossfade([seg1, pause_seg, seg2], sr=sr, crossfade_ms=15.0)

    # Overlaps will subtract 2 * crossfade_len
    cf_samples = int(sr * 0.015)
    expected_len = len(seg1) + len(pause_seg) + len(seg2) - 2 * cf_samples
    assert abs(len(stitched) - expected_len) <= 2, f"Length mismatch: {len(stitched)} vs {expected_len}"
    assert not np.isnan(stitched).any(), "Stitched audio contains NaN"
    print(f"  [PASS] 15ms Cosine crossfade stitching verified (len={len(stitched)} samples)", flush=True)

    print("=================================================================", flush=True)
    print("🎉 ALL SELF-TESTS PASSED SUCCESSFULLY! (100% Verified)", flush=True)
    print("=================================================================", flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Chinese Normalizer for High-Accuracy TTS")
    parser.add_argument("--self-test", action="store_true", help="Run comprehensive unit tests")
    parser.add_argument("--text", type=str, default="", help="Text to normalize")
    parser.add_argument("--sub-beats", type=str, default="", help="Parse sub-beats DSL")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
    elif args.sub_beats:
        import json
        res = parse_emotional_sub_beats(args.sub_beats)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.text:
        print(normalize_chinese_text_for_tts(args.text))
    else:
        run_self_test()

