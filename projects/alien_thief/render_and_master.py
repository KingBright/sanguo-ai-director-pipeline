#!/usr/bin/env python3
"""
HISTORICAL EXPERIMENT: static-image animation and separate voiceover mastering.
Not a verified character-performance pipeline; see this project's README.md.

Master Rendering & Acoustic Mastering Pipeline for:
《外星小偷：烂柯星刮刮乐大劫案》 (alien_thief / ep01_lottery_heist)
Total Duration: 71.0s (12 Shots, 24fps, Mastered with Qwen3-TTS + ACE-Step 1.5 BGM + Foley + ASS Subtitles)
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

SHOTS = [
    {
        "id": "ep01_01", "dur": 6.0, "char": "Kato", "speaker": "卡托",
        "card": "卡托|星际赏金猎人 · 破防狂暴巨魔",
        "line": "锁定目标！通缉榜倒数第一的独眼地精正在靠近彩票亭！",
        "anchor": PROJECT_DIR / "characters" / "images" / "kato_anchor.png",
        "room": "room_ruined_overlook", "acoustic": "ruin_wind_ambience",
        "cam": "truck_right"
    },
    {
        "id": "ep01_02", "dur": 5.0, "char": "Xiaodai", "speaker": "小黛",
        "card": "小黛|首席情报分析师 · 毒舌妹妹",
        "line": "悬赏金额两块五，耗油三千块，哥你真会理财。",
        "anchor": PROJECT_DIR / "characters" / "images" / "xiaodai_anchor.png",
        "room": "room_ruined_overlook", "acoustic": "ruin_wind_ambience",
        "cam": "slow_push"
    },
    {
        "id": "ep01_03", "dur": 5.0, "char": "Libei", "speaker": "里贝",
        "card": "里贝|新手盗贼学徒 · 绝望吐槽役",
        "line": "西木哥！对面狙击镜反光超刺眼，咱真要抢吗？",
        "anchor": PROJECT_DIR / "characters" / "images" / "libei_anchor.png",
        "room": "room_ruined_overlook", "acoustic": "ruin_wind_ambience",
        "cam": "handheld_jitter"
    },
    {
        "id": "ep01_04", "dur": 7.0, "char": "Ximu", "speaker": "西木",
        "card": "西木|宇宙头号通缉犯 · 哲学强盗地精",
        "line": "抢？读书人的事能叫抢吗？我这是用钛合金撬棍刮奖！",
        "anchor": PROJECT_DIR / "characters" / "images" / "ximu_anchor.png",
        "room": "room_neon_kiosk", "acoustic": "neon_kiosk_hum",
        "cam": "dutch_push"
    },
    {
        "id": "ep01_05", "dur": 5.0, "char": "Libei", "speaker": "里贝",
        "card": "",
        "line": "等等！你刮出来的特等奖怎么是一只机械尖叫鸡？",
        "anchor": PROJECT_DIR / "characters" / "images" / "libei_anchor.png",
        "room": "room_neon_kiosk", "acoustic": "neon_kiosk_hum",
        "cam": "crash_zoom"
    },
    {
        "id": "ep01_06", "dur": 6.0, "char": "Ximu", "speaker": "西木",
        "card": "",
        "line": "赚大了！只要捏爆它的脖子，全星际雷达都得瘫痪！",
        "anchor": PROJECT_DIR / "characters" / "images" / "ximu_anchor.png",
        "room": "room_neon_kiosk", "acoustic": "neon_kiosk_hum",
        "cam": "hero_push"
    },
    {
        "id": "ep01_07", "dur": 8.0, "char": "PinkWeirdo", "speaker": "巴奇",
        "card": "巴奇|星际和平代表 · 终极荒诞怪咖",
        "line": "肃静！本人正式宣布，今日和平杰出个人得主是这位绿师傅！",
        "anchor": PROJECT_DIR / "characters" / "images" / "pinkweirdo_anchor.png",
        "room": "room_bazaar_plaza", "acoustic": "ruin_wind_ambience",
        "cam": "crane_tilt"
    },
    {
        "id": "ep01_08", "dur": 7.0, "char": "Kato", "speaker": "卡托",
        "card": "",
        "line": "开什么星际玩笑！他手里捏着赃物还在朝台下敬礼！",
        "anchor": PROJECT_DIR / "characters" / "images" / "kato_anchor.png",
        "room": "room_bazaar_plaza", "acoustic": "ruin_wind_ambience",
        "cam": "whip_pan"
    },
    {
        "id": "ep01_09", "dur": 5.0, "char": "Xiaodai", "speaker": "小黛",
        "card": "",
        "line": "警报解除。因为主办方把抓捕队长的车给当场扣了。",
        "anchor": PROJECT_DIR / "characters" / "images" / "xiaodai_anchor.png",
        "room": "room_bazaar_plaza", "acoustic": "ruin_wind_ambience",
        "cam": "static_deadpan"
    },
    {
        "id": "ep01_10", "dur": 5.0, "char": "Libei", "speaker": "里贝",
        "card": "",
        "line": "救命啊！通缉队长拿爆能枪坐在咱对面跟咱斗地主！",
        "anchor": PROJECT_DIR / "characters" / "images" / "libei_anchor.png",
        "room": "room_lanke_tavern", "acoustic": "tavern_jazz_chatter",
        "cam": "tracking_dolly"
    },
    {
        "id": "ep01_11", "dur": 6.0, "char": "Ximu", "speaker": "西木",
        "card": "",
        "line": "慌什么！四个二带两王，长官，这局你输了洗碗去！",
        "anchor": PROJECT_DIR / "characters" / "images" / "ximu_anchor.png",
        "room": "room_lanke_tavern", "acoustic": "tavern_jazz_chatter",
        "cam": "tilt_up_cat"
    },
    {
        "id": "ep01_12", "dur": 6.0, "char": "PinkWeirdo", "speaker": "巴奇",
        "card": "",
        "line": "烂柯星反扒大获全胜，感谢猫咪赞助商提供的假发！",
        "anchor": PROJECT_DIR / "characters" / "images" / "pinkweirdo_anchor.png",
        "room": "room_lanke_tavern", "acoustic": "tavern_jazz_chatter",
        "cam": "iris_pullback"
    },
]

def generate_foley_beds():
    print("🎧 Generating Acoustic Space Foley Beds & SFX...", flush=True)
    sr = 48000
    total_sec = 72
    n_samples = sr * total_sec

    # 1. Wasteland wind ambience (pink noise + slow filter sweep)
    np.random.seed(42)
    white = np.random.uniform(-1, 1, n_samples)
    b_wind = np.cumsum(white)
    b_wind = b_wind - np.mean(b_wind)
    b_wind = b_wind / (np.max(np.abs(b_wind)) + 1e-6) * 0.18
    # Add subtle howling resonance at 220Hz
    t = np.linspace(0, total_sec, n_samples)
    howl = 0.04 * np.sin(2 * np.pi * 218 * t + 0.3 * np.sin(2 * np.pi * 0.2 * t))
    wind_bed = (b_wind + howl).astype(np.float32)

    # 2. Neon Kiosk Hum (60Hz / 120Hz transformer buzz + high chirps)
    buzz = 0.08 * np.sin(2 * np.pi * 120 * t) + 0.04 * np.sin(2 * np.pi * 240 * t)
    # occasional register beeps
    beeps = np.zeros(n_samples, dtype=np.float32)
    for beep_t in [2.5, 4.0, 7.8, 10.2, 13.5, 18.0]:
        idx = int(beep_t * sr)
        if idx + 4800 < n_samples:
            beeps[idx:idx+4800] += 0.12 * np.sin(2 * np.pi * 1800 * np.linspace(0, 0.1, 4800))
    kiosk_bed = (buzz + beeps + b_wind * 0.3).astype(np.float32)

    # 3. Tavern chatter & clinking
    tavern_bed = (b_wind * 0.4 + 0.03 * np.random.normal(0, 1, n_samples)).astype(np.float32)

    def write_stereo(path, mono_data):
        st = np.column_stack([mono_data, mono_data])
        st_i16 = np.clip(st * 32767.0, -32768, 32767).astype(np.int16)
        import scipy.io.wavfile as wavfile
        wavfile.write(str(path), sr, st_i16)

    write_stereo(FOL_DIR / "ruin_wind_ambience.wav", wind_bed)
    write_stereo(FOL_DIR / "neon_kiosk_hum.wav", kiosk_bed)
    write_stereo(FOL_DIR / "tavern_jazz_chatter.wav", tavern_bed)
    print("✅ Foley beds generated!", flush=True)

def render_scene_video_clips():
    print("🎬 Rendering 12 Dynamic 24fps Scene Video Clips...", flush=True)
    fps = 24
    w, h = 1280, 720

    # Check CJK font
    font_paths = [
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc"
    ]
    font_path = None
    for p in font_paths:
        if os.path.exists(p):
            font_path = p
            break

    for idx, sc in enumerate(SHOTS, 1):
        sc_id = sc["id"]
        dur = sc["dur"]
        frames_count = int(round(dur * fps))
        anchor_path = sc["anchor"]
        cam_type = sc["cam"]

        base_anchor = Image.open(str(anchor_path)).convert("RGBA")
        raw_clip = RAW_CLIPS_DIR / f"{sc_id}_raw.mp4"

        # Temp frame directory
        frames_dir = RAW_CLIPS_DIR / f"{sc_id}_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        for f in range(frames_count):
            t_rel = f / float(frames_count)  # 0.0 to 1.0

            # Canvas
            frame = Image.new("RGBA", (w, h), (18, 22, 30, 255))

            # Dynamic camera motion matrix
            if cam_type == "truck_right":
                # Camera moves right -> elements shift left slightly, with subtle zoom
                zoom = 1.0 + 0.06 * t_rel
                pan_x = -35.0 * t_rel
                pan_y = 5.0 * math.sin(t_rel * math.pi)
            elif cam_type == "slow_push":
                zoom = 1.0 + 0.12 * t_rel
                pan_x = 0
                pan_y = -10.0 * t_rel
            elif cam_type == "handheld_jitter":
                zoom = 1.05 + 0.03 * math.sin(t_rel * 4 * math.pi)
                pan_x = 6.0 * math.sin(f * 0.8) + 3.0 * math.cos(f * 1.3)
                pan_y = 4.0 * math.cos(f * 0.9)
            elif cam_type == "dutch_push":
                zoom = 1.0 + 0.15 * t_rel
                pan_x = 20.0 * t_rel
                pan_y = -15.0 * t_rel
            elif cam_type == "crash_zoom":
                # Sudden fast snap zoom in middle
                crash = math.pow(t_rel, 0.4)
                zoom = 1.0 + 0.22 * crash
                pan_x = 0
                pan_y = -8.0 * crash
            elif cam_type == "hero_push":
                zoom = 1.0 + 0.14 * t_rel
                pan_x = 0
                pan_y = -20.0 * t_rel
            elif cam_type == "crane_tilt":
                zoom = 1.02 + 0.04 * t_rel
                pan_x = 0
                pan_y = 30.0 * (1.0 - t_rel)  # starts low, tilts up
            elif cam_type == "whip_pan":
                # Fast snap
                whip = math.sin(t_rel * math.pi * 0.5)
                zoom = 1.0 + 0.08 * t_rel
                pan_x = -50.0 * (1.0 - whip)
                pan_y = 0
            elif cam_type == "static_deadpan":
                zoom = 1.02
                pan_x = 0.5 * math.sin(f * 0.1)
                pan_y = 0
            elif cam_type == "tracking_dolly":
                zoom = 1.0 + 0.10 * t_rel
                pan_x = -25.0 * t_rel
                pan_y = 10.0 * t_rel
            elif cam_type == "tilt_up_cat":
                zoom = 1.0 + 0.08 * t_rel
                pan_x = 0
                pan_y = 25.0 * t_rel
            elif cam_type == "iris_pullback":
                zoom = 1.15 - 0.12 * t_rel  # pull back
                pan_x = 0
                pan_y = 0
            else:
                zoom = 1.05
                pan_x, pan_y = 0, 0

            # Transform base image
            nw = int(w * zoom)
            nh = int(h * zoom)
            scaled = base_anchor.resize((nw, nh), Image.Resampling.BILINEAR)
            crop_x = int((nw - w) / 2 - pan_x)
            crop_y = int((nh - h) / 2 - pan_y)
            crop_x = max(0, min(nw - w, crop_x))
            crop_y = max(0, min(nh - h, crop_y))
            transformed = scaled.crop((crop_x, crop_y, crop_x + w, crop_y + h))
            frame.paste(transformed, (0, 0))

            draw = ImageDraw.Draw(frame)

            # Dynamic Cyberpunk Comic Visual Micro-Effects
            # 1. Subtle comic halftone vignette
            # 2. Animated particles / sparks / speed lines
            if cam_type in ("hero_push", "crash_zoom"):
                # Comic speed lines radiating from center
                cx, cy = w // 2, h // 2
                for angle in range(0, 360, 24):
                    rad = math.radians(angle + (f % 5) * 4)
                    r1 = 300 + 40 * math.sin(f + angle)
                    r2 = 720
                    x1 = cx + int(r1 * math.cos(rad))
                    y1 = cy + int(r1 * math.sin(rad))
                    x2 = cx + int(r2 * math.cos(rad))
                    y2 = cy + int(r2 * math.sin(rad))
                    draw.line([(x1, y1), (x2, y2)], fill=(255, 230, 80, 110), width=2)
            elif sc["room"] == "room_ruined_overlook":
                # Dust streaks blowing across screen
                for d_i in range(12):
                    dx = int((f * 35 + d_i * 120) % (w + 200)) - 100
                    dy = int((d_i * 65 + math.sin(f * 0.1 + d_i) * 30) % h)
                    draw.line([(dx, dy), (dx + 45, dy + 12)], fill=(220, 140, 80, 80), width=1)
            elif sc["room"] == "room_neon_kiosk":
                # Flickering neon glow pulse
                glow_alpha = int(40 + 25 * math.sin(f * 0.4))
                draw.rectangle([0, 0, w, 20], fill=(0, 240, 255, glow_alpha))
            elif sc["room"] == "room_lanke_tavern":
                # Tavern atmospheric jazz sparks
                for p_i in range(8):
                    px = int((w * 0.3 + p_i * 110 + math.cos(f * 0.15 + p_i) * 40) % w)
                    py = int((h * 0.6 - (f * 3 + p_i * 40) % (h * 0.4)))
                    draw.ellipse([px, py, px + 4, py + 4], fill=(255, 180, 60, 140))

            if cam_type == "iris_pullback" and t_rel > 0.75:
                # Closing iris-out circular mask
                iris_prog = (t_rel - 0.75) / 0.25
                radius = int(w * 0.7 * (1.0 - iris_prog))
                mask = Image.new("L", (w, h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse([w//2 - radius, h//2 - radius, w//2 + radius, h//2 + radius], fill=255)
                black_bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
                frame = Image.composite(frame, black_bg, mask)
                draw = ImageDraw.Draw(frame)

            # Scene ID stamp in top right for film production watermark
            draw.rectangle([w - 180, 15, w - 15, 45], fill=(10, 15, 25, 180), outline=(0, 220, 255), width=1)
            draw.text((w - 170, 20), f"SHOT {idx:02d} | 24FPS", fill=(0, 220, 255))

            frame_rgb = frame.convert("RGB")
            frame_rgb.save(str(frames_dir / f"f_{f:05d}.jpg"), quality=92)

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
        print(f"[{idx}/12] Raw clip rendered: {raw_clip.name} ({dur}s, {frames_count}f)", flush=True)

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

        # Dialogue line (0.15s after shot start, ends 0.15s before cut)
        sub_start = sc_start + 0.15
        sub_end = sc_end - 0.15
        spk = sc["speaker"]
        line = sc["line"]

        # Speaker label + dialogue
        text = f"{{\\c&H00D7FF&}}【{spk}】{{\\c&HFFFFFF&}}{line}"
        events.append(f"Dialogue: 0,{fmt_time(sub_start)},{fmt_time(sub_end)},ComicSub,,0,0,0,,{text}")

        # Intro card if present
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

def master_final_episode(ass_path: Path):
    print("🎛️ Mastering Full >=64s Video with Sidechain Ducking, Foley & Subtitles...", flush=True)
    final_output = OUTPUT_DIR / "ep01_lottery_heist_final.mp4"
    bgm_path = BGM_DIR / "lottery_heist_jazz_bgm.wav"

    # 1. Concat video clips
    concat_list = OUTPUT_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sc in SHOTS:
            raw_clip = RAW_CLIPS_DIR / f"{sc['id']}_raw.mp4"
            f.write(f"file '{raw_clip.as_posix()}'\n")

    concat_video = OUTPUT_DIR / "concat_video.mp4"
    cmd_concat = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(concat_video)
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("✅ Concatenated video stream ready!", flush=True)

    # 2. Build Multi-Track Audio Mix
    # Assemble dialogue track on exact timeline
    timeline_sec = sum(sc["dur"] for sc in SHOTS)  # 71.0s
    print(f"Total Master Timeline Duration: {timeline_sec:.2f}s", flush=True)

    sr = 48000
    total_samples = int(timeline_sec * sr)
    dialogue_track = np.zeros(total_samples, dtype=np.float32)
    foley_track = np.zeros(total_samples, dtype=np.float32)

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
            # Resample if needed
            if vo_sr != sr:
                from scipy import signal
                vo_data = signal.resample(vo_data, int(len(vo_data) * sr / vo_sr))

            # Place at cur_t + 0.15s
            start_s = int((cur_t + 0.15) * sr)
            end_s = min(total_samples, start_s + len(vo_data))
            chunk_len = end_s - start_s
            dialogue_track[start_s:end_s] += vo_data[:chunk_len] * 1.35

        cur_t += sc_dur

    # Write full dialogue stem
    dia_stem = OUTPUT_DIR / "stem_dialogue.wav"
    dia_st = np.column_stack([dialogue_track, dialogue_track])
    dia_i16 = np.clip(dia_st * 32767.0, -32768, 32767).astype(np.int16)
    import scipy.io.wavfile as wavfile
    wavfile.write(str(dia_stem), sr, dia_i16)

    # 3. Final Multi-Track Mixdown with Sidechain Ducking and Subtitle Burn-In
    # -i concat_video (0:v)
    # -i dia_stem (1:a)
    # -i bgm_path (2:a)
    # -i ruin_wind (3:a)
    # Filter complex:
    # [2:a]volume=0.38[bgm_base];
    # [bgm_base][1:a]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[ducked_bgm];
    # [3:a]volume=0.22[foley_vol];
    # [ducked_bgm][1:a][foley_vol]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout];
    # [0:v]ass='...':fontsdir='...':format=yuv420p[vout]

    wind_path = FOL_DIR / "ruin_wind_ambience.wav"
    safe_ass = ass_path.as_posix().replace(":", "\\:")

    filter_complex = (
        f"[2:a]volume=0.38[bgm_base];"
        f"[bgm_base][1:a]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[ducked_bgm];"
        f"[3:a]volume=0.20[foley_vol];"
        f"[ducked_bgm][1:a][foley_vol]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[aout];"
        f"[0:v]ass='{safe_ass}'[vout]"
    )

    cmd_master = [
        FFMPEG, "-y",
        "-i", str(concat_video),
        "-i", str(dia_stem),
        "-i", str(bgm_path),
        "-i", str(wind_path),
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
        str(final_output)
    ]

    print("Running FFmpeg master encode...", flush=True)
    res = subprocess.run(cmd_master, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr, flush=True)
        raise RuntimeError("Mastering failed!")

    print(f"🎉 MASTERED EPISODE DELIVERED: {final_output}", flush=True)
    print(f"   Size: {final_output.stat().st_size / 1024 / 1024:.2f} MB | Duration: {timeline_sec:.1f}s", flush=True)

if __name__ == "__main__":
    generate_foley_beds()
    render_scene_video_clips()
    ass = generate_ass_subtitles()
    master_final_episode(ass)
