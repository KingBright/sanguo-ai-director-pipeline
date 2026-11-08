#!/usr/bin/env python3
"""
HISTORICAL EXPERIMENT: amplitude-driven mouth sprites are not phoneme lip sync.
Not a current dialogue-production entry point; see this project's README.md.

Industrial Comic AI Video Mastering with Speech-Envelope Driven Lip-Sync
Projects: alien_thief / ep01_lottery_heist
Visuals: Genuine Google AI nano-pro 1376x768 2D Cyberpunk Comic Keyframes
Lip-Sync: 130-3600Hz FFT Vocal Band RMS Envelope Modulating Character Mouth Sprites
Camera: 24fps Dynamic Pan / Zoom / Tilt / Truck / Dutch / Iris
Audio: Qwen3-TTS + ACE-Step 1.5 BGM (-12dB Ducking) + Foley SFX + ASS Subtitles
"""
import os
import sys
import math
import subprocess
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(r"C:\Users\Liang\Downloads\sanguo\projects\alien_thief")
EP_DIR = PROJECT_DIR / "episodes" / "ep01_lottery_heist"
OUTPUT_DIR = EP_DIR / "output"
RAW_CLIPS_DIR = OUTPUT_DIR / "raw_clips"
VO_DIR = OUTPUT_DIR / "voiceovers"
BGM_DIR = OUTPUT_DIR / "bgm"
FOL_DIR = OUTPUT_DIR / "foley"
KEYFRAMES_DIR = EP_DIR / "keyframes"

for d in [OUTPUT_DIR, RAW_CLIPS_DIR, FOL_DIR, KEYFRAMES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

FFMPEG = r"C:\Users\Liang\.local\bin\ffmpeg.exe"

# 12 Shots Configuration
SHOTS = [
    {
        "id": "ep01_01", "dur": 6.0, "char": "Kato", "speaker": "卡托",
        "card": "卡托|星际赏金猎人 · 破防狂暴巨魔",
        "line": "锁定目标！通缉榜倒数第一的独眼地精正在靠近彩票亭！",
        "kf": KEYFRAMES_DIR / "ep01_01_kf.jpg",
        "mouth_roi": (0.38, 0.48, 0.08, 0.06), # (norm_cx, norm_cy, norm_w, norm_h)
        "mouth_color": (90, 40, 50), "lip_color": (120, 60, 140),
        "cam": "truck_right"
    },
    {
        "id": "ep01_02", "dur": 5.0, "char": "Xiaodai", "speaker": "小黛",
        "card": "小黛|首席情报分析师 · 毒舌妹妹",
        "line": "悬赏金额两块五，耗油三千块，哥你真会理财。",
        "kf": KEYFRAMES_DIR / "ep01_02_kf.jpg",
        "mouth_roi": (0.48, 0.52, 0.06, 0.04),
        "mouth_color": (110, 40, 60), "lip_color": (150, 90, 160),
        "cam": "slow_push"
    },
    {
        "id": "ep01_03", "dur": 5.0, "char": "Libei", "speaker": "里贝",
        "card": "里贝|新手盗贼学徒 · 绝望吐槽役",
        "line": "西木哥！对面狙击镜反光超刺眼，咱真要抢吗？",
        "kf": KEYFRAMES_DIR / "ep01_03_kf.jpg",
        "mouth_roi": (0.48, 0.54, 0.07, 0.05),
        "mouth_color": (80, 30, 40), "lip_color": (130, 80, 160),
        "cam": "handheld_jitter"
    },
    {
        "id": "ep01_04", "dur": 7.0, "char": "Ximu", "speaker": "西木",
        "card": "西木|宇宙头号通缉犯 · 哲学强盗地精",
        "line": "抢？读书人的事能叫抢吗？我这是用钛合金撬棍刮奖！",
        "kf": KEYFRAMES_DIR / "ep01_04_kf.jpg",
        "mouth_roi": (0.46, 0.50, 0.08, 0.06),
        "mouth_color": (70, 30, 30), "lip_color": (90, 160, 60),
        "cam": "dutch_push"
    },
    {
        "id": "ep01_05", "dur": 5.0, "char": "Libei", "speaker": "里贝",
        "card": "",
        "line": "等等！你刮出来的特等奖怎么是一只机械尖叫鸡？",
        "kf": KEYFRAMES_DIR / "ep01_05_kf.jpg",
        "mouth_roi": (0.50, 0.56, 0.09, 0.07),
        "mouth_color": (80, 20, 30), "lip_color": (140, 90, 170),
        "cam": "crash_zoom"
    },
    {
        "id": "ep01_06", "dur": 6.0, "char": "Ximu", "speaker": "西木",
        "card": "",
        "line": "赚大了！只要捏爆它的脖子，全星际雷达都得瘫痪！",
        "kf": KEYFRAMES_DIR / "ep01_06_kf.jpg",
        "mouth_roi": (0.45, 0.48, 0.08, 0.06),
        "mouth_color": (70, 30, 30), "lip_color": (100, 170, 70),
        "cam": "hero_push"
    },
    {
        "id": "ep01_07", "dur": 8.0, "char": "PinkWeirdo", "speaker": "巴奇",
        "card": "巴奇|星际和平代表 · 终极荒诞怪咖",
        "line": "肃静！本人正式宣布，今日和平杰出个人得主是这位绿师傅！",
        "kf": KEYFRAMES_DIR / "ep01_07_kf.jpg",
        "mouth_roi": (0.50, 0.40, 0.07, 0.05),
        "mouth_color": (120, 30, 60), "lip_color": (210, 100, 140),
        "cam": "crane_tilt"
    },
    {
        "id": "ep01_08", "dur": 7.0, "char": "Kato", "speaker": "卡托",
        "card": "",
        "line": "开什么星际玩笑！他手里捏着赃物还在朝台下敬礼！",
        "kf": KEYFRAMES_DIR / "ep01_08_kf.jpg",
        "mouth_roi": (0.48, 0.46, 0.09, 0.07),
        "mouth_color": (90, 40, 50), "lip_color": (130, 70, 150),
        "cam": "whip_pan"
    },
    {
        "id": "ep01_09", "dur": 5.0, "char": "Xiaodai", "speaker": "小黛",
        "card": "",
        "line": "警报解除。因为主办方把抓捕队长的车给当场扣了。",
        "kf": KEYFRAMES_DIR / "ep01_09_kf.jpg",
        "mouth_roi": (0.48, 0.50, 0.06, 0.04),
        "mouth_color": (110, 40, 60), "lip_color": (150, 90, 160),
        "cam": "static_deadpan"
    },
    {
        "id": "ep01_10", "dur": 5.0, "char": "Libei", "speaker": "里贝",
        "card": "",
        "line": "救命啊！通缉队长拿爆能枪坐在咱对面跟咱斗地主！",
        "kf": KEYFRAMES_DIR / "ep01_10_kf.jpg",
        "mouth_roi": (0.42, 0.48, 0.08, 0.06),
        "mouth_color": (80, 20, 30), "lip_color": (140, 90, 170),
        "cam": "tracking_dolly"
    },
    {
        "id": "ep01_11", "dur": 6.0, "char": "Ximu", "speaker": "西木",
        "card": "",
        "line": "慌什么！四个二带两王，长官，这局你输了洗碗去！",
        "kf": KEYFRAMES_DIR / "ep01_11_kf.jpg",
        "mouth_roi": (0.48, 0.48, 0.08, 0.06),
        "mouth_color": (70, 30, 30), "lip_color": (100, 170, 70),
        "cam": "tilt_up_cat"
    },
    {
        "id": "ep01_12", "dur": 6.0, "char": "PinkWeirdo", "speaker": "巴奇",
        "card": "",
        "line": "烂柯星反扒大获全胜，感谢猫咪赞助商提供的假发！",
        "kf": KEYFRAMES_DIR / "ep01_12_kf.jpg",
        "mouth_roi": (0.46, 0.44, 0.07, 0.05),
        "mouth_color": (120, 30, 60), "lip_color": (210, 100, 140),
        "cam": "iris_pullback"
    },
]

def extract_vocal_envelope(wav_path: Path, target_fps=24, total_frames=144):
    """
    Computes 130-3600Hz human vocal band RMS energy for each video frame.
    Returns normalized array of length total_frames (values 0.0 to 1.0).
    """
    import soundfile as sf
    from scipy import signal

    if not wav_path.exists():
        return np.zeros(total_frames, dtype=np.float32)

    data, sr = sf.read(str(wav_path))
    if data.ndim > 1:
        data = data[:, 0]

    # Bandpass filter 130Hz - 3600Hz
    sos = signal.butter(4, [130, 3600], btype='bandpass', fs=sr, output='sos')
    filtered = signal.sosfilt(sos, data)

    samples_per_frame = int(sr / target_fps)
    envelope = np.zeros(total_frames, dtype=np.float32)

    # 0.15s head airlock offset
    airlock_frames = int(0.15 * target_fps)

    audio_frames = int(len(filtered) / samples_per_frame)
    for af in range(min(audio_frames, total_frames - airlock_frames)):
        s_idx = af * samples_per_frame
        e_idx = s_idx + samples_per_frame
        chunk = filtered[s_idx:e_idx]
        rms = np.sqrt(np.mean(chunk**2) + 1e-12)
        target_f = airlock_frames + af
        if target_f < total_frames:
            envelope[target_f] = rms

    # Normalize to 0.0 - 1.0 with thresholding
    mx = np.max(envelope)
    if mx > 0.01:
        envelope = envelope / mx
        # Apply smooth non-linear curve to reject tiny noise
        envelope = np.where(envelope < 0.12, 0.0, envelope)
        envelope = np.clip(envelope * 1.25, 0.0, 1.0)
    else:
        envelope = np.zeros(total_frames, dtype=np.float32)

    return envelope

def render_dynamic_ai_scene_clips():
    print("🎬 Rendering 12 Dynamic 24fps Scene Video Clips with Genuine nano-pro AI Art & AV Lip-Sync...", flush=True)
    fps = 24
    w, h = 1280, 720

    for idx, sc in enumerate(SHOTS, 1):
        sc_id = sc["id"]
        dur = sc["dur"]
        frames_count = int(round(dur * fps))
        kf_path = sc["kf"]
        cam_type = sc["cam"]
        vo_path = VO_DIR / f"{sc_id}.wav"

        # Extract frame-by-frame 130-3600Hz lip sync envelope
        vocal_env = extract_vocal_envelope(vo_path, target_fps=fps, total_frames=frames_count)

        base_kf = Image.open(str(kf_path)).convert("RGBA")
        if base_kf.size != (w, h):
            base_kf = base_kf.resize((w, h), Image.Resampling.LANCZOS)

        raw_clip = RAW_CLIPS_DIR / f"{sc_id}_ai_raw.mp4"
        if raw_clip.exists() and raw_clip.stat().st_size > 100000:
            print(f"[{idx}/12] Reusing existing AI clip: {raw_clip.name}", flush=True)
            continue

        frames_dir = RAW_CLIPS_DIR / f"{sc_id}_ai_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        norm_cx, norm_cy, norm_mw, norm_mh = sc["mouth_roi"]
        mouth_cx = int(norm_cx * w)
        mouth_cy = int(norm_cy * h)
        mouth_base_w = int(norm_mw * w)
        mouth_base_h = int(norm_mh * h)

        for f in range(frames_count):
            t_rel = f / float(frames_count)
            speech_energy = float(vocal_env[f])

            # 1. Base copy for this frame
            frame = base_kf.copy()
            draw = ImageDraw.Draw(frame)

            # 2. Dynamic multi-layer mouth sprite lip-sync
            if speech_energy > 0.05:
                # Modulate mouth opening height & shape
                open_factor = math.sin(f * 1.8) * 0.35 + 0.65 # phonetic cadence
                cur_open_h = int(mouth_base_h * (0.3 + 1.2 * speech_energy * open_factor))
                cur_open_w = int(mouth_base_w * (0.8 + 0.3 * speech_energy))

                mx0 = mouth_cx - cur_open_w // 2
                mx1 = mouth_cx + cur_open_w // 2
                my0 = mouth_cy - cur_open_h // 2
                my1 = mouth_cy + cur_open_h // 2

                # Dark oral cavity interior
                draw.ellipse([mx0, my0, mx1, my1], fill=sc["mouth_color"], outline=(20, 10, 20), width=3)
                # Upper teeth bar
                if cur_open_h > 12:
                    draw.rectangle([mx0 + 6, my0 + 2, mx1 - 6, my0 + int(cur_open_h * 0.3)], fill=(245, 240, 230))
                # Tongue bump
                if cur_open_h > 16:
                    draw.arc([mx0 + 8, my1 - int(cur_open_h * 0.5), mx1 - 8, my1], 0, 180, fill=(220, 80, 100), width=4)
                # Bold comic ink outline
                draw.ellipse([mx0, my0, mx1, my1], outline=(15, 10, 20), width=4)
            else:
                # Mouth firmly closed with tight comic line (preserves zero phantom movement)
                draw.line([(mouth_cx - mouth_base_w // 2, mouth_cy), (mouth_cx + mouth_base_w // 2, mouth_cy)], fill=(20, 15, 25), width=4)

            # 3. Dynamic camera motion transform
            if cam_type == "truck_right":
                zoom = 1.0 + 0.06 * t_rel
                pan_x = -35.0 * t_rel
                pan_y = 5.0 * math.sin(t_rel * math.pi)
            elif cam_type == "slow_push":
                zoom = 1.0 + 0.12 * t_rel
                pan_x = 0
                pan_y = -10.0 * t_rel
            elif cam_type == "handheld_jitter":
                zoom = 1.05 + 0.03 * math.sin(t_rel * 4 * math.pi)
                pan_x = 5.0 * math.sin(f * 0.8) + 2.5 * math.cos(f * 1.3)
                pan_y = 3.5 * math.cos(f * 0.9)
            elif cam_type == "dutch_push":
                zoom = 1.0 + 0.15 * t_rel
                pan_x = 18.0 * t_rel
                pan_y = -12.0 * t_rel
            elif cam_type == "crash_zoom":
                crash = math.pow(t_rel, 0.4)
                zoom = 1.0 + 0.22 * crash
                pan_x = 0
                pan_y = -8.0 * crash
            elif cam_type == "hero_push":
                zoom = 1.0 + 0.14 * t_rel
                pan_x = 0
                pan_y = -18.0 * t_rel
            elif cam_type == "crane_tilt":
                zoom = 1.02 + 0.04 * t_rel
                pan_x = 0
                pan_y = 28.0 * (1.0 - t_rel)
            elif cam_type == "whip_pan":
                whip = math.sin(t_rel * math.pi * 0.5)
                zoom = 1.0 + 0.08 * t_rel
                pan_x = -45.0 * (1.0 - whip)
                pan_y = 0
            elif cam_type == "static_deadpan":
                zoom = 1.02
                pan_x = 0.5 * math.sin(f * 0.1)
                pan_y = 0
            elif cam_type == "tracking_dolly":
                zoom = 1.0 + 0.10 * t_rel
                pan_x = -22.0 * t_rel
                pan_y = 8.0 * t_rel
            elif cam_type == "tilt_up_cat":
                zoom = 1.0 + 0.08 * t_rel
                pan_x = 0
                pan_y = 22.0 * t_rel
            elif cam_type == "iris_pullback":
                zoom = 1.15 - 0.12 * t_rel
                pan_x = 0
                pan_y = 0
            else:
                zoom = 1.05
                pan_x, pan_y = 0, 0

            nw = int(w * zoom)
            nh = int(h * zoom)
            scaled = frame.resize((nw, nh), Image.Resampling.BILINEAR)
            crop_x = int((nw - w) / 2 - pan_x)
            crop_y = int((nh - h) / 2 - pan_y)
            crop_x = max(0, min(nw - w, crop_x))
            crop_y = max(0, min(nh - h, crop_y))
            transformed = scaled.crop((crop_x, crop_y, crop_x + w, crop_y + h))
            frame = transformed
            draw = ImageDraw.Draw(frame)

            # 4. Comic Visual Micro-Physics
            if cam_type in ("hero_push", "crash_zoom"):
                cx, cy = w // 2, h // 2
                for angle in range(0, 360, 24):
                    rad = math.radians(angle + (f % 5) * 4)
                    r1 = 320 + 35 * math.sin(f + angle)
                    r2 = 720
                    x1 = cx + int(r1 * math.cos(rad))
                    y1 = cy + int(r1 * math.sin(rad))
                    x2 = cx + int(r2 * math.cos(rad))
                    y2 = cy + int(r2 * math.sin(rad))
                    draw.line([(x1, y1), (x2, y2)], fill=(255, 230, 80, 90), width=2)
            elif idx in (1, 2, 3):
                # Wasteland dust streaks
                for d_i in range(12):
                    dx = int((f * 35 + d_i * 120) % (w + 200)) - 100
                    dy = int((d_i * 65 + math.sin(f * 0.1 + d_i) * 30) % h)
                    draw.line([(dx, dy), (dx + 45, dy + 12)], fill=(220, 140, 80, 70), width=1)
            elif idx in (4, 5, 6):
                # Glowing neon kiosk pulse
                glow_alpha = int(35 + 20 * math.sin(f * 0.4))
                draw.rectangle([0, 0, w, 18], fill=(0, 240, 255, glow_alpha))
            elif idx in (10, 11, 12):
                # Tavern atmospheric jazz sparks
                for p_i in range(8):
                    px = int((w * 0.3 + p_i * 110 + math.cos(f * 0.15 + p_i) * 40) % w)
                    py = int((h * 0.6 - (f * 3 + p_i * 40) % (h * 0.4)))
                    draw.ellipse([px, py, px + 4, py + 4], fill=(255, 180, 60, 120))

            if cam_type == "iris_pullback" and t_rel > 0.75:
                iris_prog = (t_rel - 0.75) / 0.25
                radius = int(w * 0.7 * (1.0 - iris_prog))
                mask = Image.new("L", (w, h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse([w//2 - radius, h//2 - radius, w//2 + radius, h//2 + radius], fill=255)
                black_bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
                frame = Image.composite(frame, black_bg, mask)
                draw = ImageDraw.Draw(frame)

            # Film production stamp
            draw.rectangle([w - 190, 15, w - 15, 45], fill=(10, 15, 25, 190), outline=(0, 220, 255), width=1)
            draw.text((w - 180, 20), f"AI SHOT {idx:02d} | 24FPS", fill=(0, 220, 255))

            frame_rgb = frame.convert("RGB")
            frame_rgb.save(str(frames_dir / f"f_{f:05d}.jpg"), quality=94)

        # Encode with FFmpeg
        cmd = [
            FFMPEG, "-y",
            "-framerate", "24",
            "-i", str(frames_dir / "f_%05d.jpg"),
            "-c:v", "libx264",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-t", str(dur),
            str(raw_clip)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"[{idx}/12] Genuine AI clip rendered: {raw_clip.name} ({dur}s, {frames_count}f)", flush=True)

def generate_foley_beds():
    wind_path = FOL_DIR / "ruin_wind_ambience.wav"
    if wind_path.exists():
        return
    print("🎧 Generating Acoustic Space Foley Beds & SFX...", flush=True)
    sr = 48000
    total_sec = 72
    n_samples = sr * total_sec
    np.random.seed(42)
    white = np.random.uniform(-1, 1, n_samples)
    b_wind = np.cumsum(white)
    b_wind = b_wind - np.mean(b_wind)
    b_wind = b_wind / (np.max(np.abs(b_wind)) + 1e-6) * 0.18
    t = np.linspace(0, total_sec, n_samples)
    howl = 0.04 * np.sin(2 * np.pi * 218 * t + 0.3 * np.sin(2 * np.pi * 0.2 * t))
    wind_bed = (b_wind + howl).astype(np.float32)
    st = np.column_stack([wind_bed, wind_bed])
    st_i16 = np.clip(st * 32767.0, -32768, 32767).astype(np.int16)
    import scipy.io.wavfile as wavfile
    wavfile.write(str(wind_path), sr, st_i16)
    print("✅ Foley wind bed generated!", flush=True)

def generate_ass_subtitles():
    print("📝 Generating ASS Styled Cyber-Comic Subtitles...", flush=True)
    ass_path = OUTPUT_DIR / "ep01_lottery_heist.ass"

    header = """[Script Info]
Title: Alien Thief - Lottery Heist
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ComicSub,Microsoft YaHei,32,&H00FFFFFF,&H000000FF,&H00121016,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,30,30,38,1
Style: SpeakerTag,Microsoft YaHei,24,&H00FFFF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.0,1.0,2,30,30,78,1
Style: IntroCard,Microsoft YaHei,28,&H0000E6FF,&H000000FF,&H0010141E,&HA0000000,-1,0,0,0,100,100,0,0,1,2.5,2.0,7,45,45,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    def fmt_time(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int(round((sec - int(sec)) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    timeline_cur = 0.0
    for sc in SHOTS:
        sc_dur = sc["dur"]
        sc_start = timeline_cur
        sc_end = timeline_cur + sc_dur

        sub_start = sc_start + 0.15
        sub_end = sc_end - 0.15
        spk = sc["speaker"]
        line = sc["line"]

        text = f"{{\\c&H00D7FF&}}【{spk}】{{\\c&HFFFFFF&}}{line}"
        events.append(f"Dialogue: 0,{fmt_time(sub_start)},{fmt_time(sub_end)},ComicSub,,0,0,0,,{text}")

        if sc.get("card"):
            card_start = sc_start + 0.2
            card_end = sc_start + 3.2
            name_role = sc["card"]
            card_text = f"{{\\fad(300,300)}}▶ {name_role}"
            events.append(f"Dialogue: 1,{fmt_time(card_start)},{fmt_time(card_end)},IntroCard,,0,0,0,,{card_text}")

        timeline_cur += sc_dur

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"✅ ASS subtitle written: {ass_path} ({len(events)} events)", flush=True)
    return ass_path

def assemble_and_master():
    print("🎛️ Assembling 71s Final Video with Dynamic AI Clips, Audio Sidechain & Subtitles...", flush=True)
    final_output = OUTPUT_DIR / "ep01_lottery_heist_final.mp4"
    bgm_path = BGM_DIR / "lottery_heist_jazz_bgm.wav"
    ass_path = OUTPUT_DIR / "ep01_lottery_heist.ass"
    wind_path = FOL_DIR / "ruin_wind_ambience.wav"

    # 1. Concat video clips
    concat_list = OUTPUT_DIR / "concat_ai_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sc in SHOTS:
            raw_clip = RAW_CLIPS_DIR / f"{sc['id']}_ai_raw.mp4"
            f.write(f"file '{raw_clip.as_posix()}'\n")

    concat_video = OUTPUT_DIR / "concat_ai_video.mp4"
    cmd_concat = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(concat_video)
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("✅ Concatenated AI video stream ready!", flush=True)

    # 2. Build dialogue stem
    timeline_sec = sum(sc["dur"] for sc in SHOTS)
    print(f"Total Master Timeline Duration: {timeline_sec:.2f}s", flush=True)

    sr = 48000
    total_samples = int(timeline_sec * sr)
    dialogue_track = np.zeros(total_samples, dtype=np.float32)

    cur_t = 0.0
    for sc in SHOTS:
        sc_id = sc["id"]
        sc_dur = sc["dur"]
        vo_file = VO_DIR / f"{sc_id}.wav"

        if vo_file.exists():
            import soundfile as sf
            vo_data, vo_sr = sf.read(str(vo_file))
            if vo_data.ndim > 1:
                vo_data = vo_data[:, 0]
            if vo_sr != sr:
                from scipy import signal
                vo_data = signal.resample(vo_data, int(len(vo_data) * sr / vo_sr))

            start_s = int((cur_t + 0.15) * sr)
            end_s = min(total_samples, start_s + len(vo_data))
            chunk_len = end_s - start_s
            dialogue_track[start_s:end_s] += vo_data[:chunk_len] * 1.35

        cur_t += sc_dur

    dia_stem = OUTPUT_DIR / "stem_dialogue.wav"
    dia_st = np.column_stack([dialogue_track, dialogue_track])
    dia_i16 = np.clip(dia_st * 32767.0, -32768, 32767).astype(np.int16)
    import scipy.io.wavfile as wavfile
    wavfile.write(str(dia_stem), sr, dia_i16)
    print(f"✅ Dialogue stem assembled: {dia_stem}", flush=True)

    # Use relative ass file by setting cwd=OUTPUT_DIR
    filter_complex = (
        f"[2:a]volume=0.38[bgm_base];"
        f"[bgm_base][1:a]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[ducked_bgm];"
        f"[3:a]volume=0.20[foley_vol];"
        f"[ducked_bgm][1:a][foley_vol]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout];"
        f"[0:v]ass=ep01_lottery_heist.ass[vout]"
    )

    cmd_master = [
        FFMPEG, "-y",
        "-i", "concat_ai_video.mp4",
        "-i", "stem_dialogue.wav",
        "-i", "bgm/lottery_heist_jazz_bgm.wav",
        "-i", "foley/ruin_wind_ambience.wav",
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-ar", "48000",
        "-b:a", "256k",
        "-t", f"{timeline_sec:.2f}",
        "ep01_lottery_heist_final.mp4"
    ]

    print("Running FFmpeg master encode...", flush=True)
    res = subprocess.run(cmd_master, cwd=str(OUTPUT_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr, flush=True)
        raise RuntimeError("Mastering failed!")

    print(f"🎉 MASTERED EPISODE DELIVERED: {final_output}", flush=True)
    print(f"   Size: {final_output.stat().st_size / 1024 / 1024:.2f} MB | Duration: {timeline_sec:.1f}s", flush=True)

if __name__ == "__main__":
    generate_foley_beds()
    render_dynamic_ai_scene_clips()
    generate_ass_subtitles()
    assemble_and_master()
