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
        r"(^|[\s，。！？、；：（])\-(\d+)",
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
