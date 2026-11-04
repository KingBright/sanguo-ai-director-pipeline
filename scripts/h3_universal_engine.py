#!/usr/bin/env python3
"""
Universal MiniMax-H3 v2.5 / V9 Industrial Video Engine
======================================================
General-purpose, multi-genre AI video & drama engine built on the extreme technical
standards of `MiniMax-H3 v2.5 / V9` and `POSE-DB-01` (1,439 poses):

1. `17k + 5` Golden Frame Contract (`39, 90, 141, 192` zero-audio-overhang frames)
   & `$17k$` Keyframe Phase Alignment (`0, 17, 34, 51, 68, 85, 102, 136, 170`).
2. Official `Ref2VA` 6-Block Prompt Protocol:
   - `subject_definitions:` (`<Picture 1>`, `<Picture 2>`, `<Audio 1>`)
   - `summary: [reference generation + audio reference]`
   - `retention_analysis:` (180-degree south-side axis lock, hand chirality, lens/lighting)
   - `detailed_description:` (`1.1s` Silent Preparatory Airlock, 5-Step Causal Action Chain,
     `<d>[Mandarin]...</d>`, `T8mars` Emotion Decoupling, `1.3s` Silent Closed-Mouth Tail Anchor,
     positive stationary head-lock phrasing, single 3D camera directive)
   - `overall_soundscape:`
   - `non_diegetic_music:`
3. `Speech-Active Gating` (only mount `<Audio 1>` for the character who actually speaks)
   & `Self-Anchor Voice` (`32kHz stereo` extraction/conditioning).
4. `V8_8sLock` + `V9_TailLock` Dual-End Latent Clamp (`[68, 85]` for 90f or `[107, 136]` for 141f).
5. `22-Frame (7-Token)` Zero-Phase `MotionContext` Latent Continuation + Manual Anti-Fog `JoinMatch`
   (`strength=0.35, min_excess=2.5, match_spread=False, match_detail=False`) + `5MB AV_LATENT`
   Checkpoint Hot-Swap (`--only-seg N`).
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import torch
from PIL import Image

try:
    from pose_library_engine import (
        UniversalPoseLibrary,
        snap_golden_frames,
        snap_keyframe_index_17k,
        frame_idx_to_h3_token_idx,
    )
except ImportError:
    from scripts.pose_library_engine import (
        UniversalPoseLibrary,
        snap_golden_frames,
        snap_keyframe_index_17k,
        frame_idx_to_h3_token_idx,
    )

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass
class SubjectReference:
    label: str  # e.g. "<Picture 1>", "<Picture 2>", "<Audio 1>"
    ref_type: str  # "image", "audio", "video", "video_audio"
    name: str
    description: str
    path: str
    is_active_speaker: bool = False


@dataclass
class UniversalShotSpec:
    shot_id: str
    genre: str = "universal_drama"  # modern_drama | fashion_gravure | action_kinetic | digital_human_koubo | historical_epic
    continuity_track: str = "track_b_hard_cut"  # "track_a_latent_relay" (22f MotionContext) or "track_b_hard_cut"
    num_frames: int = 90
    width: int = 1280
    height: int = 720
    # Subject & Voice conditioning
    subjects: List[SubjectReference] = field(default_factory=list)
    active_speaker_name: str = ""
    active_speaker_voice_wav: str = ""
    dialogue_lang: str = "Mandarin"
    dialogue_text: str = ""
    emotion_mode: str = "natural"  # "natural" | "t8mars_explosive" | "t8mars_fury" | "t8mars_weeping" | "restrained_cold"
    # Spatial & Physical Blocking
    spatial_topology: str = "The camera remains strictly on the south side of the 180-degree axis line."
    preparatory_airlock_desc: str = "For the first 1.1 seconds, the subject remains still with lips naturally closed, establishing eye contact and spatial presence."
    causal_action_chain: str = ""
    tail_anchor_desc: str = "For the final 1.3 seconds, after the last syllable completes, the subject's lips close naturally and the posture settles into a composed, stationary hold."
    hand_chirality_lock: str = ""
    head_orientation_lock: str = "with head held completely level and stationary"
    camera_directive: str = "The camera holds a steady 50mm medium-close framing with a subtle slow push-in."
    overall_soundscape: str = "Clean indoor room tone with natural fabric rustle and clear close-mic vocal resonance."
    non_diegetic_music: str = "None. Pure diegetic soundscape without background music."
    # Pose & 17k Trajectory Anchors
    pose_ids: List[str] = field(default_factory=list)
    keyframe_image_paths: List[str] = field(default_factory=list)
    keyframe_indices: List[int] = field(default_factory=list)
    keyframe_strengths: List[float] = field(default_factory=list)
    enable_v9_tail_lock: bool = True
    character_card: str = ""  # Optional "Name|Role Title" for staggered glassmorphic intro card


def compile_ref2va_6block_prompt(spec: UniversalShotSpec) -> Dict:
    """
    Compiles a `UniversalShotSpec` into the official MiniMax-H3 `Ref2VA` 6-Block Prompt Protocol
    with `Speech-Active Gating`, `T8mars` Emotion Decoupling, `1.1s` Silent Preparatory Airlock,
    `1.3s` Silent Closed-Mouth Tail Anchor, and Positive Stationary Head-Lock Phrasing.
    """
    pic_counter = 0
    aud_counter = 0
    subject_lines: List[str] = []
    retention_items: List[str] = []
    mounted_references: List[Dict] = []

    # 1. Mount visual subjects (`<Picture 1>`, `<Picture 2>`, ...)
    for subj in spec.subjects:
        if subj.ref_type == "image":
            pic_counter += 1
            tag = f"<Picture {pic_counter}>"
            subject_lines.append(
                f"- {tag}: Visual identity and spatial reference for {subj.name} ({subj.description})."
            )
            retention_items.append(
                f"Preserve the exact facial bone structure, skin micro-texture, hairstyle, and wardrobe materials of {subj.name} from {tag} without morphing multiple views into separate people."
            )
            mounted_references.append({"type": "image", "path": subj.path, "tag": tag, "name": subj.name})

    # 2. Speech-Active Gating: ONLY mount `<Audio 1>` if there is active spoken dialogue in this shot
    has_speech = bool(spec.dialogue_text.strip() and spec.active_speaker_voice_wav.strip())
    audio_tag = ""
    if has_speech:
        aud_counter += 1
        audio_tag = f"<Audio {aud_counter}>"
        speaker_label = spec.active_speaker_name or "the speaking subject"
        if spec.emotion_mode.startswith("t8mars"):
            subject_lines.append(
                f"- {audio_tag}: Vocal identity timbre anchor for {speaker_label} (preserving ONLY the fundamental vocal identity from {audio_tag} while breaking away from its calm baseline tone)."
            )
        else:
            subject_lines.append(
                f"- {audio_tag}: Vocal identity and acoustic timbre reference for {speaker_label}."
            )
        mounted_references.append(
            {
                "type": "audio",
                "path": spec.active_speaker_voice_wav,
                "tag": audio_tag,
                "name": speaker_label,
            }
        )

    if not subject_lines:
        subject_lines.append("- Primary cinematic scene generated with physical and optical realism.")

    # 3. Summary header
    if has_speech and pic_counter > 0:
        summary_line = "[reference generation + audio reference] Joint audio-visual cinema shot with frame-accurate lip synchronization and locked 3D spatial continuity."
    elif pic_counter > 0:
        summary_line = "[reference generation] Visually anchored cinema shot with locked subject identity and diegetic environmental acoustics."
    else:
        summary_line = "[text to audio-video generation] Photorealistic cinema shot with synchronized diegetic soundscape."

    # 4. Retention Analysis (180-degree south-side lock, hand chirality, anti-head-drift)
    retention_items.append(spec.spatial_topology)
    if spec.hand_chirality_lock.strip():
        retention_items.append(spec.hand_chirality_lock.strip())
    retention_items.append(
        f"Maintain stable facial geometry {spec.head_orientation_lock}, with zero subtitle overlays or watermarks."
    )

    # 5. Detailed Description (Airlock -> Action + <d>Dialogue</d> -> Tail Anchor -> Single Camera Directive)
    emotion_clause = ""
    if spec.emotion_mode == "t8mars_explosive" and audio_tag:
        emotion_clause = (
            f" Speaking with explosive dramatic projection (+8dB vocal surge), preserving ONLY the vocal identity from {audio_tag} "
            f"while breaking away from its calm tone—urgent, commanding, not calm, not restrained: "
        )
    elif spec.emotion_mode == "t8mars_fury" and audio_tag:
        emotion_clause = (
            f" Delivering the line with fierce, chest-resonant authority, preserving ONLY the vocal identity from {audio_tag} "
            f"while breaking away from its calm tone—piercing, forceful, not calm, not whispered: "
        )
    elif spec.emotion_mode == "t8mars_weeping" and audio_tag:
        emotion_clause = (
            f" Speaking with trembling emotional intensity and choked resonance, preserving ONLY the vocal identity from {audio_tag}: "
        )
    elif has_speech and audio_tag:
        emotion_clause = f" Speaking in the exact vocal timbre of {audio_tag} with crisp, natural lip articulation: "

    dialogue_block = ""
    if spec.dialogue_text.strip():
        clean_line = spec.dialogue_text.strip()
        dialogue_block = f"{emotion_clause}<d>[{spec.dialogue_lang}] {clean_line}</d> "

    # Incorporate pose trajectory hints if provided
    pose_hint_str = ""
    if spec.pose_ids:
        lib = UniversalPoseLibrary()
        hints = []
        for pid in spec.pose_ids:
            if pid in lib.by_id:
                hints.append(lib.build_english_pose_hint(lib.by_id[pid]))
        if hints:
            pose_hint_str = " Physical pose trajectory transitions smoothly through: " + " -> ".join(hints) + "."

    detailed_parts = [
        spec.preparatory_airlock_desc.strip(),
        spec.causal_action_chain.strip(),
        pose_hint_str.strip(),
        dialogue_block.strip(),
        spec.tail_anchor_desc.strip(),
        spec.camera_directive.strip(),
    ]
    detailed_body = " ".join([p for p in detailed_parts if p])

    prompt_text = (
        "subject_definitions:\n"
        + "\n".join(subject_lines)
        + "\n\n"
        + f"summary: {summary_line}\n\n"
        + "retention_analysis:\n"
        + "\n".join(f"- {r}" for r in retention_items)
        + "\n\n"
        + f"detailed_description:\n{detailed_body}\n\n"
        + f"overall_soundscape: {spec.overall_soundscape.strip()}\n\n"
        + f"non_diegetic_music: {spec.non_diegetic_music.strip()}"
    )

    golden_frames = snap_golden_frames(spec.num_frames, zero_overhang=True)
    snapped_kf_indices = [snap_keyframe_index_17k(idx, golden_frames) for idx in spec.keyframe_indices]

    return {
        "shot_id": spec.shot_id,
        "genre": spec.genre,
        "continuity_track": spec.continuity_track,
        "golden_frames": golden_frames,
        "duration_sec": round(golden_frames / 24.0, 3),
        "speech_active_gated": has_speech,
        "mounted_references": mounted_references,
        "keyframe_indices_17k": snapped_kf_indices,
        "keyframe_strengths": spec.keyframe_strengths,
        "prompt": prompt_text,
    }


def ensure_self_anchor_voice_32k_stereo(
    input_media_path: Union[str, Path],
    output_wav_path: Optional[Union[str, Path]] = None,
    max_duration_sec: float = 6.0,
) -> Path:
    """
    Extracts or converts any reference voice WAV/MP4 into MiniMax-H3's native
    `32kHz Stereo PCM_S16LE` Self-Anchor Voice format (`pipe.audio_vae.sample_rate == 32000`).
    """
    src = Path(input_media_path)
    if not src.exists():
        raise FileNotFoundError(f"Audio source not found: {src}")
    dst = Path(output_wav_path) if output_wav_path else src.with_name(f"{src.stem}_32k_stereo.wav")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-t", f"{max_duration_sec:.2f}",
        "-vn",
        "-ac", "2",
        "-ar", "32000",
        "-c:a", "pcm_s16le",
        str(dst),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dst


def manual_anti_fog_join_match(
    prev_tail_frames: List[Image.Image],
    curr_frames: List[Image.Image],
    overlap_frames: int = 22,
    strength: float = 0.35,
    min_excess: float = 2.5,
    match_spread: bool = False,
    match_detail: bool = False,
) -> List[Image.Image]:
    """
    Implements the Whitepaper §5.2 Manual Anti-Fog `JoinMatch` (`MiniMaxH3JoinMatch` v2.5):
    - Prevents the grey contrast fog caused by `auto` spread/detail matching across segments.
    - Uses `strength=0.35`, `min_excess=2.5`, `match_spread=False`, `match_detail=False`
      and a cosine cross-fade over the 22-frame (`7-token`) MotionContext overlap window.
    """
    if not prev_tail_frames or not curr_frames:
        return curr_frames

    k = min(overlap_frames, len(prev_tail_frames), len(curr_frames))
    if k <= 0:
        return curr_frames

    ref_arr = np.stack([np.asarray(f.convert("RGB"), dtype=np.float32) for f in prev_tail_frames[-k:]], axis=0)
    cur_head_arr = np.stack([np.asarray(f.convert("RGB"), dtype=np.float32) for f in curr_frames[:k]], axis=0)

    # Compute per-channel mean shift only when drift exceeds `min_excess` (2.5 / 255 levels)
    ref_mean = ref_arr.mean(axis=(0, 1, 2), keepdims=True)  # [1, 1, 1, 3]
    cur_mean = cur_head_arr.mean(axis=(0, 1, 2), keepdims=True)
    diff = ref_mean - cur_mean
    excess_mask = np.abs(diff) > float(min_excess)
    delta = np.where(excess_mask, diff * float(strength), 0.0)

    # Optional spread matching (kept False by default per Anti-Fog rule)
    scale = np.ones_like(delta)
    if match_spread:
        ref_std = ref_arr.std(axis=(0, 1, 2), keepdims=True) + 1e-5
        cur_std = cur_head_arr.std(axis=(0, 1, 2), keepdims=True) + 1e-5
        scale = 1.0 + float(strength) * ((ref_std / cur_std) - 1.0)

    corrected: List[Image.Image] = []
    total = len(curr_frames)
    for idx, frame in enumerate(curr_frames):
        arr = np.asarray(frame.convert("RGB"), dtype=np.float32)
        # Decay color offset smoothly across the segment
        decay = max(0.25, 1.0 - 0.5 * (idx / max(1.0, float(total - 1))))
        arr_corr = (arr - cur_mean.squeeze(0)) * scale.squeeze(0) + cur_mean.squeeze(0) + delta.squeeze(0) * decay
        if idx < k:
            # Smooth cosine blend in the 22-frame overlap zone
            alpha = 0.5 * (1.0 - math.cos(math.pi * float(idx + 1) / float(k + 1)))
            arr_corr = (1.0 - alpha) * ref_arr[idx] + alpha * arr_corr
        arr_corr = np.clip(arr_corr, 0.0, 255.0).astype(np.uint8)
        corrected.append(Image.fromarray(arr_corr))

    return corrected


def save_av_latent_checkpoint(
    checkpoint_path: Union[str, Path],
    video_latents: torch.Tensor,
    audio_latents: torch.Tensor,
    meta: Optional[Dict] = None,
) -> Path:
    """
    Saves a ~5MB `AV_LATENT` `.pt` checkpoint (`video_latents` + `audio_latents` + metadata)
    so multi-segment workflows can hot-swap and re-render a single segment (`--only-seg N`)
    in ~90 seconds without re-running upstream segments.
    """
    p = Path(checkpoint_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "video_latents": video_latents.detach().cpu().to(torch.bfloat16),
        "audio_latents": audio_latents.detach().cpu().to(torch.bfloat16),
        "meta": meta or {},
    }
    torch.save(payload, p)
    return p


def load_av_latent_checkpoint(checkpoint_path: Union[str, Path]) -> Dict:
    """Loads a saved `AV_LATENT` `.pt` checkpoint for `MotionContext` or `--only-seg N` hot-swap."""
    p = Path(checkpoint_path)
    if not p.exists():
        raise FileNotFoundError(f"AV_LATENT checkpoint not found: {p}")
    return torch.load(p, map_location="cpu", weights_only=False)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Quick self-test of the Universal H3 v2.5 6-Block Compiler across two different genres
    modern_spec = UniversalShotSpec(
        shot_id="modern_legal_ep01_s02",
        genre="modern_drama",
        continuity_track="track_a_latent_relay",
        num_frames=90,
        subjects=[
            SubjectReference(
                label="<Picture 1>",
                ref_type="image",
                name="Lin Wei",
                description="32-year-old female corporate litigator in a charcoal tailored blazer",
                path="assets/characters/lin_wei_turnaround.png",
                is_active_speaker=True,
            )
        ],
        active_speaker_name="Lin Wei",
        active_speaker_voice_wav="assets/voices/冷静知性成年女声-v1.wav",
        dialogue_lang="Mandarin",
        dialogue_text="这份并购协议的第三条，从一开始就是个陷阱。",
        emotion_mode="t8mars_explosive",
        causal_action_chain="Remaining seated with comfortable headroom above her crown, Lin Wei leans her upper torso forward 15 degrees and taps the contract folder with her right index finger.",
        hand_chirality_lock="Her left hand rests flat on the mahogany table while her right index finger taps the document.",
        head_orientation_lock="with head held completely level and stationary in a 90-degree side profile",
        camera_directive="The camera holds a steady 85mm medium-close profile framing with shallow depth of field.",
        pose_ids=["full_single_P011_front", "full_single_P004_diag", "full_single_P011_diag"],
        keyframe_indices=[0, 51, 85],
        keyframe_strengths=[1.0, 0.88, 0.90],
        character_card="林薇|首席并购律师",
    )
    compiled = compile_ref2va_6block_prompt(modern_spec)
    print(json.dumps(compiled, ensure_ascii=False, indent=2))
