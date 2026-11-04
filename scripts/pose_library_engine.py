#!/usr/bin/env python3
"""
Universal Pose Library & Trajectory Anchor Engine (POSE-DB-01 + H3 v2.5 17k Alignment)
=======================================================================================
Integrates the complete 1,439-pose library from https://ai-pose-gallery.pages.dev/
(`assets/pose_db/pose_catalog_1439.json`) into our universal AI video production system:
1. Covers all 4 universal pose systems (`全身1人・標準系`, `全身1人・セクシー系`, `上半身1人`, `2人絡み`)
   and 5 synchronized camera angles (`front`, `side`, `diag`, `low`, `high`) to solve the
   `<Picture 1>` Pose Attraction & Profile Re-Anchoring problem across any genre.
2. Multilingual semantic search (Chinese / English / Japanese) + genre & shot presets
   (Modern Office/Legal Drama, High-Fashion/Gravure Model Showcase, Romance/Two-Person
   Interaction, Action/Martial Arts/Dance V3 ProSeam, Digital Human Explainer, Historical Epic).
3. Automatic on-demand image fetching from `https://ai-pose-gallery.pages.dev/img/<id>.png`
   with Cloudflare-compatible `User-Agent: Mozilla/5.0` and local caching.
4. Mathematical `17k` Keyframe Phase Alignment (`0, 17, 34, 51, 68, 85, 102, 136, 170`)
   and per-anchor `strength` schedule (`1.0` at start, `0.85~0.90` at intermediate `17k`,
   `0.90` at `V9_TailLock` `[107, 136]` or `-1`).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT_DIR = Path(__file__).resolve().parent.parent
POSE_DB_DIR = ROOT_DIR / "assets" / "pose_db"
CATALOG_JSON_PATH = POSE_DB_DIR / "pose_catalog_1439.json"
PRESETS_JSON_PATH = POSE_DB_DIR / "universal_pose_presets.json"
BASE_URL = "https://ai-pose-gallery.pages.dev"

# Valid 17k + 5 Golden Frames and Zero-Audio-Overhang Golden Frames (24fps / 40Hz Audio LCM)
GOLDEN_FRAMES_17K_PLUS_5 = [22, 39, 56, 73, 90, 107, 124, 141, 158, 175, 192, 209, 226, 243]
ZERO_OVERHANG_GOLDEN_FRAMES = [39, 90, 141, 192, 243]

# Valid 17k Keyframe Phase Indices (land strictly on 1-Frame Token 5k in MiniMax-H3)
VALID_17K_INDICES = [0, 17, 34, 51, 68, 85, 102, 119, 136, 153, 170, 187, 204, 221, 238]

# Angle normalization map (Japanese <-> English <-> Chinese)
ANGLE_ALIASES: Dict[str, str] = {
    "front": "正面",
    "正面": "正面",
    "frontal": "正面",
    "eye-level": "正面",
    "high": "上から",
    "上から": "上から",
    "俯拍": "上から",
    "high-angle": "上から",
    "low": "下から",
    "下から": "下から",
    "仰拍": "下から",
    "low-angle": "下から",
    "side": "横",
    "横": "横",
    "侧脸": "横",
    "侧面": "横",
    "profile": "横",
    "90-degree": "横",
    "diag": "斜め",
    "斜め": "斜め",
    "斜侧": "斜め",
    "3/4": "斜め",
    "three-quarter": "斜め",
}

ANGLE_TO_SUFFIX: Dict[str, str] = {
    "正面": "front",
    "上から": "high",
    "下から": "low",
    "横": "side",
    "斜め": "diag",
}

SYSTEM_ALIASES: Dict[str, str] = {
    "standard": "全身1人・標準系",
    "full_single": "全身1人・標準系",
    "标准": "全身1人・標準系",
    "全身标准": "全身1人・標準系",
    "sexy": "全身1人・セクシー系",
    "full_sexy": "全身1人・セクシー系",
    "gravure": "全身1人・セクシー系",
    "fashion": "全身1人・セクシー系",
    "性感": "全身1人・セクシー系",
    "模特": "全身1人・セクシー系",
    "upper": "上半身1人",
    "upper_single": "上半身1人",
    "closeup": "上半身1人",
    "koubo": "上半身1人",
    "上半身": "上半身1人",
    "特写": "上半身1人",
    "口播": "上半身1人",
    "pair": "2人絡み",
    "two_person": "2人絡み",
    "couple": "2人絡み",
    "duel": "2人絡み",
    "双人": "2人絡み",
    "对手戏": "2人絡み",
}

# Multilingual keyword expansion (Chinese / English -> Japanese catalog terms)
SEMANTIC_KEYWORD_MAP: Dict[str, List[str]] = {
    # Postures & Actions
    "stand": ["立ち", "仁王立ち", "ポーズ"],
    "站": ["立ち", "仁王立ち"],
    "站立": ["立ち", "仁王立ち"],
    "sit": ["座り", "椅子", "あぐら", "正座", "体育座り"],
    "坐": ["座り", "椅子", "あぐら", "正座"],
    "椅子": ["椅子"],
    "chair": ["椅子"],
    "kneel": ["膝立ち", "正座", "片膝"],
    "跪": ["膝立ち", "正座", "片膝"],
    "单膝跪": ["片膝"],
    "lie": ["寝", "仰向け", "うつ伏せ", "横向き寝", "寝そべり"],
    "躺": ["寝", "仰向け", "うつ伏せ", "横向き寝"],
    "卧": ["寝", "横向き寝"],
    "crouch": ["しゃがみ"],
    "蹲": ["しゃがみ"],
    "lean": ["前かがみ", "反らし", "壁", "寄りかかる"],
    "前倾": ["前かがみ"],
    "后仰": ["反らし", "背中を反らし"],
    "arch": ["反らし", "背中を反らし", "S字"],
    "s-curve": ["S字"],
    "s型": ["S字"],
    "曲线": ["S字", "突き出す"],
    "turn": ["振り返る", "ひねり", "見返り"],
    "回头": ["振り返る", "見返り"],
    "回眸": ["振り返る", "見返り"],
    "扭腰": ["ひねり", "S字"],
    "hair": ["髪", "かき上げる", "ツインテール"],
    "撩发": ["髪", "かき上げる"],
    "cross_arms": ["腕組み"],
    "抱臂": ["腕組み"],
    "双手叉腰": ["腰に手", "仁王立ち"],
    "point": ["指差し", "手を伸ばす"],
    "指": ["指差し"],
    "fighting": ["ファイティング", "構え", "パンチ", "キック"],
    "格斗": ["ファイティング", "構え", "パンチ", "キック"],
    "武打": ["ファイティング", "構え", "パンチ", "キック"],
    "kick": ["キック", "片足上げ"],
    "踢": ["キック", "片足上げ"],
    "hug": ["抱き", "ハグ", "密着"],
    "拥抱": ["抱き", "ハグ", "密着"],
    "back_to_back": ["背中合わせ"],
    "背靠背": ["背中合わせ"],
    "face_to_face": ["向かい合い", "見つめ合う"],
    "对视": ["向かい合い", "見つめ合う"],
    "对峙": ["向かい合い", "背中合わせ", "腕組み"],
    "think": ["考える", "顎に手", "頬杖"],
    "思考": ["考える", "顎に手", "頬杖"],
    "托腮": ["頬杖", "顎に手"],
    "wave": ["手を振る", "ピース"],
    "招手": ["手を振る"],
    "pray": ["祈り", "合掌", "手を合わせる"],
    "拱手": ["合掌", "手を合わせる", "祈り"],
}


# Universal Multi-Genre Trajectory Presets (Works across ALL video genres)
UNIVERSAL_GENRE_PRESETS: Dict[str, Dict] = {
    "modern_drama_confrontation": {
        "name": "现代都市/律政/职场双人对峙 (Track A/B 180°轴线锁定)",
        "genre": "modern_drama",
        "description": "适用于现代职场、律政谈判、悬疑审讯、情感对峙。包含 90° 正侧脸特写锚点与双人同框锚点，自动匹配 H3 180度南侧轴线与静止头部锁定。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "pair60_P001_front", "frame_idx": 0, "strength": 1.0, "role": "双人面对面建置 (Master Two-Shot)"},
            {"pose_id": "upper80v2_P005_side", "frame_idx": 51, "strength": 0.88, "role": "90°正侧脸冷静发问 (Profile Lock)"},
            {"pose_id": "upper80v2_P012_front", "frame_idx": 85, "strength": 0.90, "role": "正面微表情收束定格 (Silent Tail Anchor)"},
        ],
    },
    "modern_seated_table_slam": {
        "name": "室内坐姿拍桌/决断 (遵守防越顶裁头耦合律)",
        "genre": "modern_drama",
        "description": "适用于董事会、审讯室、书房、中军帐坐姿决断。全程保持坐姿前倾 (Remaining Seated Forward Lean) 配合充足头顶留白，杜绝固定中景内起立裁头。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "full_single_P011_front", "frame_idx": 0, "strength": 1.0, "role": "沉稳端坐凝视 (1.1s Silent Airlock)"},
            {"pose_id": "full_single_P004_diag", "frame_idx": 51, "strength": 0.88, "role": "上半身前倾撑案决断 (Seated Lean-In)"},
            {"pose_id": "full_single_P011_diag", "frame_idx": 85, "strength": 0.90, "role": "余韵定格闭口收尾 (1.3s Silent Tail)"},
        ],
    },
    "fashion_gravure_s_curve_flow": {
        "name": "时尚写真/车展/模特多锚点流转 (S曲线 -> 仰头撩发 -> 回眸)",
        "genre": "fashion_gravure",
        "description": "适用于时尚大片、写真模特、电商服装展示。在 17k 相位点 (0 -> 51 -> 85) 平滑流转三套经典高张力姿态，零残影、零手部崩坏。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "full_sexy_P001_front", "frame_idx": 0, "strength": 1.0, "role": "S型曲线叉腰立姿 (Start Anchor)"},
            {"pose_id": "full_sexy_P002_diag", "frame_idx": 51, "strength": 0.86, "role": "反身仰头双手撩发 (Mid 17k Anchor)"},
            {"pose_id": "full_sexy_P003_side", "frame_idx": 85, "strength": 0.90, "role": "侧身回眸凝视镜头 (Tail 17k Anchor)"},
        ],
    },
    "fashion_gravure_recline_allure": {
        "name": "时尚居家/沙发/地毯慵懒卧姿流转 (斜坐 -> 托腮俯卧 -> 侧卧)",
        "genre": "fashion_gravure",
        "description": "适用于高级感室内写真、护肤品/家居广告、氛围感短片。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "full_sexy_P026_front", "frame_idx": 0, "strength": 1.0, "role": "美人鱼斜坐姿态 (Start Anchor)"},
            {"pose_id": "full_sexy_P064_diag", "frame_idx": 51, "strength": 0.86, "role": "俯卧双手托腮微翘双腿 (Mid 17k Anchor)"},
            {"pose_id": "full_sexy_P068_front", "frame_idx": 85, "strength": 0.90, "role": "优雅侧卧舒展收尾 (Tail 17k Anchor)"},
        ],
    },
    "action_martial_proseam_valley": {
        "name": "动作/武术/街舞 V3 ProSeam 动能波谷流转 (起势 -> 爆发 -> 蹬开分离)",
        "genre": "action_kinetic",
        "description": "遵循 V3 ProSeam 动能波谷法则：在分段尾帧强制进入物理分离或招式定格 (Kinetic Valley)，为下一段提供干净物理初速度。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "full_single_P035_diag", "frame_idx": 0, "strength": 1.0, "role": "格斗戒备起势 (Combat Guard)"},
            {"pose_id": "full_single_P038_side", "frame_idx": 51, "strength": 0.85, "role": "正蹬/出拳爆发顶点 (Strike Impact)"},
            {"pose_id": "full_single_P036_low", "frame_idx": 85, "strength": 0.90, "role": "拉开距离沉身定格 (Kinetic Valley Separation)"},
        ],
    },
    "digital_human_explainer_koubo": {
        "name": "数字人口播/财经科技解说/带货主播 (自然手势链)",
        "genre": "digital_human_koubo",
        "description": "适用于小林说式财经科技解说、产品评测、知识口播。采用上半身特写系姿态，手势随语义关键帧自然展开与收拢。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "upper80v2_P001_front", "frame_idx": 0, "strength": 1.0, "role": "正面自信开场眼神锁定"},
            {"pose_id": "upper80v2_P008_diag", "frame_idx": 51, "strength": 0.85, "role": "单手展开强调核心论点"},
            {"pose_id": "upper80v2_P003_front", "frame_idx": 85, "strength": 0.90, "role": "双手微收从容定格收尾"},
        ],
    },
    "historical_epic_command_oath": {
        "name": "历史权谋/古装剧将相决断与军令 (Historical Epic Command Preset)",
        "genre": "historical_epic",
        "description": "适用于历史正剧、古装权谋、中军帐授令与大将请战场景。结合低机位英雄仰拍与17k关键帧锚定。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "full_single_P001_low", "frame_idx": 0, "strength": 1.0, "role": "统帅威严负手立姿 (Low-Angle Heroic Start)"},
            {"pose_id": "full_single_P022_diag", "frame_idx": 51, "strength": 0.88, "role": "单膝跪地抱拳请命 / 挥袖授令 (Mid 17k Anchor)"},
            {"pose_id": "full_single_P002_front", "frame_idx": 85, "strength": 0.90, "role": "目光如炬定格收束 (V9 TailLock Anchor)"},
        ],
    },
    "romance_couple_interaction": {
        "name": "情感剧/偶像剧双人亲密互动与背靠背张力",
        "genre": "romance_drama",
        "description": "适用于情感短剧、MV、双人宿命感同框，直接调用 POSE-DB `2人絡み` 双人姿态系。",
        "recommended_frames": 90,
        "anchors": [
            {"pose_id": "pair60_P005_diag", "frame_idx": 0, "strength": 1.0, "role": "双人宿命感同框"},
            {"pose_id": "pair60_P002_front", "frame_idx": 51, "strength": 0.86, "role": "缓慢靠近四目相对"},
            {"pose_id": "pair60_P008_side", "frame_idx": 85, "strength": 0.90, "role": "近距离侧颜凝视定格"},
        ],
    },
}


@dataclass
class PoseAnchorSpec:
    pose_id: str
    system: str
    pose_number: str
    category: str
    pose_name_ja: str
    angle_ja: str
    angle_code: str
    frame_idx: int
    token_idx: int
    strength: float
    local_image_path: str
    remote_url: str
    prompt_hint_en: str


def snap_golden_frames(target_frames: int, zero_overhang: bool = True) -> int:
    """
    Snap frame count to MiniMax-H3 `17k + 5` Golden Frame contract.
    When `zero_overhang=True`, snaps to `{39, 90, 141, 192, 243}` where
    24fps video and 40Hz audio VAE tokens achieve exact integer LCM (zero audio overhang).
    """
    candidates = ZERO_OVERHANG_GOLDEN_FRAMES if zero_overhang else GOLDEN_FRAMES_17K_PLUS_5
    best = min(candidates, key=lambda x: abs(x - target_frames))
    return best


def snap_keyframe_index_17k(frame_idx: int, num_frames: int = 90) -> int:
    """
    Snap any keyframe index onto the nearest valid `17k` phase-aligned frame index
    (`0, 17, 34, 51, 68, 85, 102, 136, 170`) within `[0, num_frames - 1]`.
    Why: MiniMax-H3 video VAE compresses every 17 frames into 5 tokens `(1, 4, 4, 4, 4)`.
    Only `frame_idx = 17k` lands on `Token 5k` (the 1-Frame lossless anchor slot).
    """
    if frame_idx <= 0:
        return 0
    if frame_idx == -1:
        # Largest 17k strictly inside num_frames
        valid = [idx for idx in VALID_17K_INDICES if idx < num_frames]
        return valid[-1] if valid else 0
    valid = [idx for idx in VALID_17K_INDICES if idx < num_frames]
    if not valid:
        return 0
    return min(valid, key=lambda x: abs(x - frame_idx))


def frame_idx_to_h3_token_idx(frame_idx: int) -> int:
    """Convert a `17k` frame index into its exact MiniMax-H3 `5k` latent token index."""
    k = max(0, int(round(frame_idx / 17.0)))
    return k * 5


class UniversalPoseLibrary:
    def __init__(self, catalog_path: Path = CATALOG_JSON_PATH):
        self.catalog_path = catalog_path
        self.entries: List[Dict] = []
        self.by_id: Dict[str, Dict] = {}
        self.by_system_and_pnum: Dict[Tuple[str, str], List[Dict]] = {}
        self._load()

    def _load(self) -> None:
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Pose catalog not found: {self.catalog_path}")
        self.entries = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        for item in self.entries:
            pid = item["id"]
            self.by_id[pid] = item
            key = (item.get("系統", ""), item.get("ポーズ番号", ""))
            self.by_system_and_pnum.setdefault(key, []).append(item)

        # Save universal presets file if not already written or outdated
        PRESETS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        PRESETS_JSON_PATH.write_text(
            json.dumps(UNIVERSAL_GENRE_PRESETS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def stats(self) -> Dict:
        systems: Dict[str, int] = {}
        categories: Dict[str, int] = {}
        angles: Dict[str, int] = {}
        for item in self.entries:
            systems[item["系統"]] = systems.get(item["系統"], 0) + 1
            cat_key = f"{item['系統']}::{item['分類']}"
            categories[cat_key] = categories.get(cat_key, 0) + 1
            angles[item["アングル"]] = angles.get(item["アングル"], 0) + 1
        return {
            "total_poses": len(self.entries),
            "systems": systems,
            "angles": angles,
            "category_count": len(categories),
            "universal_genre_presets": list(UNIVERSAL_GENRE_PRESETS.keys()),
        }

    def get_pose_in_angle(self, pose_id: str, target_angle: str) -> Optional[Dict]:
        """
        Given any pose_id (e.g. `full_single_P015_front`) and a desired camera angle
        (`front`, `side`, `diag`, `low`, `high`), returns the synchronized pose entry
        for that exact angle to solve `<Picture 1>` Pose Attraction / Profile Re-Anchoring.
        """
        base = self.by_id.get(pose_id)
        if not base:
            return None
        norm_angle_ja = ANGLE_ALIASES.get(target_angle.lower().strip(), target_angle)
        siblings = self.by_system_and_pnum.get((base["系統"], base["ポーズ番号"]), [])
        for sib in siblings:
            if sib["アングル"] == norm_angle_ja:
                return sib
        return base

    def search(
        self,
        query: str = "",
        system: Optional[str] = None,
        angle: Optional[str] = None,
        limit: int = 15,
    ) -> List[Dict]:
        """
        Multilingual semantic search across all 1,439 poses.
        Supports Chinese, English, and Japanese queries + system & angle filters.
        """
        norm_sys = SYSTEM_ALIASES.get(system.lower().strip(), system) if system else None
        norm_angle = ANGLE_ALIASES.get(angle.lower().strip(), angle) if angle else None

        # Expand query tokens into Japanese keywords
        q_lower = query.lower().strip()
        expanded_terms: List[str] = []
        if q_lower:
            expanded_terms.append(q_lower)
            for k, ja_list in SEMANTIC_KEYWORD_MAP.items():
                if k in q_lower:
                    expanded_terms.extend(ja_list)
            for token in q_lower.replace(",", " ").split():
                if token in SEMANTIC_KEYWORD_MAP:
                    expanded_terms.extend(SEMANTIC_KEYWORD_MAP[token])
                else:
                    expanded_terms.append(token)

        scored: List[Tuple[int, Dict]] = []
        for item in self.entries:
            if norm_sys and item["系統"] != norm_sys:
                continue
            if norm_angle and item["アングル"] != norm_angle:
                continue

            if not expanded_terms:
                scored.append((1, item))
                continue

            haystack = f"{item['id']} {item['系統']} {item['分類']} {item['ポーズ名']} {item['アングル']}".lower()
            score = 0
            for term in expanded_terms:
                if term.lower() in haystack:
                    score += 3 if term in item["ポーズ名"] else 1
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: (-x[0], x[1]["id"]))
        return [item for _, item in scored[:limit]]

    def ensure_pose_image(self, pose_id: str, prefer_thumb: bool = False) -> Path:
        """
        Ensure the pose reference PNG/JPG is downloaded locally in `assets/pose_db/`.
        Uses `User-Agent: Mozilla/5.0` to pass Cloudflare checks on `ai-pose-gallery.pages.dev`.
        """
        item = self.by_id.get(pose_id)
        if not item:
            # Fallback fuzzy match by prefix
            matches = [v for k, v in self.by_id.items() if k.startswith(pose_id)]
            if not matches:
                raise KeyError(f"Unknown pose_id '{pose_id}' in catalog (1,439 poses).")
            item = matches[0]
            pose_id = item["id"]

        rel_path = item["サムネ"] if prefer_thumb else item["原寸"]
        local_flat = POSE_DB_DIR / Path(rel_path).name
        local_nested = POSE_DB_DIR / rel_path

        if local_flat.exists() and local_flat.stat().st_size > 1024:
            return local_flat
        if local_nested.exists() and local_nested.stat().st_size > 1024:
            return local_nested

        local_flat.parent.mkdir(parents=True, exist_ok=True)
        url = f"{BASE_URL}/{rel_path.lstrip('/')}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": f"{BASE_URL}/",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        local_flat.write_bytes(data)
        return local_flat

    @staticmethod
    def build_english_pose_hint(item: Dict) -> str:
        """Translate Japanese pose metadata into a concise English physical blocking directive."""
        angle_map = {
            "正面": "eye-level frontal framing",
            "上から": "high-angle overhead framing",
            "下から": "heroic low-angle framing",
            "横": "strict 90-degree side profile framing",
            "斜め": "three-quarter diagonal framing",
        }
        cat_map = {
            "立ち": "standing posture",
            "座り": "seated posture on floor/cushion",
            "椅子": "seated posture on chair",
            "しゃがみ": "crouching posture",
            "前かがみ": "forward-leaning posture with comfortable headroom",
            "反らし": "arched-back posture",
            "ひねり": "torso-twist posture",
            "膝立ち": "kneeling posture",
            "寝": "reclining posture",
            "仰向け": "supine reclining posture",
            "うつ伏せ": "prone reclining posture",
            "横向き寝": "side-reclining posture",
            "2人立ち": "two-person standing interaction",
            "2人座り": "two-person seated interaction",
            "2人寝": "two-person reclining interaction",
        }
        angle_en = angle_map.get(item.get("アングル", ""), "cinematic framing")
        cat_en = cat_map.get(item.get("分類", ""), "structured physical posture")
        return f"{cat_en} ({item.get('ポーズ名', '')}, {angle_en})"

    def build_17k_trajectory_plan(
        self,
        pose_ids: List[str],
        num_frames: int = 90,
        custom_indices: Optional[List[int]] = None,
        custom_strengths: Optional[List[float]] = None,
        tail_lock_v9: bool = False,
        download_images: bool = True,
    ) -> Dict:
        """
        Maps 1, 2, or 3+ pose IDs from `POSE-DB-01` onto exact `17k` phase-aligned frame indices
        (`0, 17, 34, 51, 68, 85, 102, 136, 170`) with optimal per-keyframe conditioning strengths.
        """
        golden_frames = snap_golden_frames(num_frames, zero_overhang=True)
        n = len(pose_ids)
        if n == 0:
            return {"num_frames": golden_frames, "anchors": []}

        # Default 17k distribution across `golden_frames`
        valid_slots = [idx for idx in VALID_17K_INDICES if idx < golden_frames]
        if custom_indices and len(custom_indices) == n:
            snapped_indices = [snap_keyframe_index_17k(idx, golden_frames) for idx in custom_indices]
        else:
            if n == 1:
                snapped_indices = [0]
            elif n == 2:
                snapped_indices = [0, valid_slots[-1]]
            else:
                # Evenly pick from valid 17k slots: start (0), intermediate 17k(s), and tail 17k
                step = (len(valid_slots) - 1) / float(n - 1)
                snapped_indices = [valid_slots[int(round(i * step))] for i in range(n)]

        if custom_strengths and len(custom_strengths) == n:
            strengths = [float(s) for s in custom_strengths]
        else:
            strengths = []
            for i in range(n):
                if i == 0:
                    strengths.append(1.0)
                elif i == n - 1:
                    strengths.append(0.90 if tail_lock_v9 else 0.88)
                else:
                    strengths.append(0.85)

        anchors: List[PoseAnchorSpec] = []
        for pose_id, f_idx, strength in zip(pose_ids, snapped_indices, strengths):
            item = self.by_id.get(pose_id)
            if not item:
                matches = [v for k, v in self.by_id.items() if k.startswith(pose_id)]
                if not matches:
                    raise KeyError(f"Pose ID '{pose_id}' not found in POSE-DB-01")
                item = matches[0]
            local_path = str(self.ensure_pose_image(item["id"])) if download_images else ""
            angle_code = ANGLE_TO_SUFFIX.get(item["アングル"], "front")
            anchors.append(
                PoseAnchorSpec(
                    pose_id=item["id"],
                    system=item["系統"],
                    pose_number=item["ポーズ番号"],
                    category=item["分類"],
                    pose_name_ja=item["ポーズ名"],
                    angle_ja=item["アングル"],
                    angle_code=angle_code,
                    frame_idx=f_idx,
                    token_idx=frame_idx_to_h3_token_idx(f_idx),
                    strength=strength,
                    local_image_path=local_path,
                    remote_url=f"{BASE_URL}/{item['原寸']}",
                    prompt_hint_en=self.build_english_pose_hint(item),
                )
            )

        # Optional V9 Dual-End TailLock (`[107, 136]` for 141f or `[68, 85]` for 90f)
        v9_clamp_frames = []
        if tail_lock_v9 and len(valid_slots) >= 2:
            v9_clamp_frames = [valid_slots[-2], valid_slots[-1]]

        return {
            "num_frames": golden_frames,
            "duration_sec": round(golden_frames / 24.0, 3),
            "zero_audio_overhang": golden_frames in ZERO_OVERHANG_GOLDEN_FRAMES,
            "tail_lock_v9_frames": v9_clamp_frames,
            "keyframe_indices": [a.frame_idx for a in anchors],
            "keyframe_token_indices": [a.token_idx for a in anchors],
            "keyframe_strengths": [a.strength for a in anchors],
            "anchors": [asdict(a) for a in anchors],
        }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Universal Pose Library & 17k Trajectory Anchor Engine")
    parser.add_argument("--stats", action="store_true", help="Print catalog statistics and universal presets")
    parser.add_argument("--query", type=str, default="", help="Multilingual semantic search query")
    parser.add_argument("--system", type=str, default=None, help="Filter by system: standard | sexy | upper | pair")
    parser.add_argument("--angle", type=str, default=None, help="Filter by angle: front | side | diag | low | high")
    parser.add_argument("--preset", type=str, default=None, help="Build 17k trajectory plan from a universal genre preset")
    parser.add_argument("--poses", type=str, nargs="*", help="Build 17k trajectory plan from explicit pose IDs")
    parser.add_argument("--frames", type=int, default=90, help="Target frame count (auto-snapped to golden frames)")
    parser.add_argument("--limit", type=int, default=10, help="Max search results")
    args = parser.parse_args()

    lib = UniversalPoseLibrary()

    if args.stats:
        print(json.dumps(lib.stats(), ensure_ascii=False, indent=2))
        return

    if args.preset:
        preset = UNIVERSAL_GENRE_PRESETS.get(args.preset)
        if not preset:
            raise ValueError(f"Unknown preset '{args.preset}'. Available: {list(UNIVERSAL_GENRE_PRESETS.keys())}")
        pose_ids = [a["pose_id"] for a in preset["anchors"]]
        indices = [a["frame_idx"] for a in preset["anchors"]]
        strengths = [a["strength"] for a in preset["anchors"]]
        plan = lib.build_17k_trajectory_plan(
            pose_ids=pose_ids,
            num_frames=preset.get("recommended_frames", args.frames),
            custom_indices=indices,
            custom_strengths=strengths,
            tail_lock_v9=True,
            download_images=True,
        )
        plan["preset_meta"] = preset
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    if args.poses:
        plan = lib.build_17k_trajectory_plan(
            pose_ids=args.poses,
            num_frames=args.frames,
            tail_lock_v9=True,
            download_images=True,
        )
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    results = lib.search(query=args.query, system=args.system, angle=args.angle, limit=args.limit)
    print(json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
