#!/usr/bin/env python3
"""Historical speech-resampling and mouth-deformation experiment.

Not a current dialogue-production entry point; see this project's README.md.
"""
import os
import sys
sys.path.append(r"C:\Users\Liang\minimax\.venv\Lib\site-packages")
import math
import subprocess
import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import gaussian_filter1d
from PIL import Image

FFMPEG = r"C:\Users\Liang\Workspace\.remoteplay-ffmpeg-essentials-20260925\extracted\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
FFPROBE = r"C:\Users\Liang\Workspace\.remoteplay-ffmpeg-essentials-20260925\extracted\ffmpeg-9.0.1-essentials_build\bin\ffprobe.exe"

PROJECT_DIR = r"C:\Users\Liang\Downloads\sanguo\projects\alien_thief"
EP_DIR = os.path.join(PROJECT_DIR, "episodes", "ep01_lottery_heist")
OUTPUT_DIR = os.path.join(EP_DIR, "output")
RAW_CLIPS_DIR = os.path.join(OUTPUT_DIR, "raw_clips")
VO_DIR = os.path.join(OUTPUT_DIR, "voiceovers")
BGM_DIR = os.path.join(OUTPUT_DIR, "bgm")
FOL_DIR = os.path.join(OUTPUT_DIR, "foley")

MOUTH_ROIS = {
    "ep01_01": (0.38, 0.48, 0.08, 0.06),
    "ep01_02": (0.48, 0.52, 0.06, 0.04),
    "ep01_03": (0.48, 0.54, 0.07, 0.05),
    "ep01_04": (0.46, 0.50, 0.08, 0.06),
    "ep01_05": (0.50, 0.56, 0.09, 0.07),
    "ep01_06": (0.45, 0.48, 0.08, 0.06),
    "ep01_07": (0.50, 0.40, 0.07, 0.05),
    "ep01_08": (0.48, 0.46, 0.09, 0.07),
    "ep01_09": (0.48, 0.50, 0.06, 0.04),
    "ep01_10": (0.42, 0.48, 0.08, 0.06),
    "ep01_11": (0.48, 0.48, 0.08, 0.06),
    "ep01_12": (0.46, 0.44, 0.07, 0.05),
}

def get_clip_info(p):
    res = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration:stream=nb_frames,r_frame_rate", "-of", "json", p], capture_output=True, text=True, check=True)
    import json
    data = json.loads(res.stdout)
    dur = float(data["format"]["duration"])
    return dur

def process_lip_sync(frames_arr, vo_mono, sr, mouth_roi, clip_dur):
    n_frames, H, W, _ = frames_arr.shape
    fps = 24.0
    airlock_s = 0.55
    tail_s = 0.45
    speech_start_f = int(round(airlock_s * fps))
    speech_end_f = max(speech_start_f + 1, n_frames - int(round(tail_s * fps)))
    speech_frames = speech_end_f - speech_start_f
    target_speech_dur = speech_frames / fps

    # Fit voiceover to target speech window
    in_dur = len(vo_mono) / sr
    if in_dur > 0.1:
        speed = in_dur / target_speech_dur
        speed = max(0.80, min(1.25, speed))
        new_len = int(len(vo_mono) / speed)
        fit_vo = signal.resample(vo_mono, new_len)
    else:
        fit_vo = vo_mono

    # Compute per-frame RMS
    spf = int(round(sr / fps))
    rms = np.zeros(n_frames, dtype=np.float32)
    for f_idx in range(speech_start_f, speech_end_f):
        vo_offset_f = f_idx - speech_start_f
        s_idx = vo_offset_f * spf
        e_idx = min(len(fit_vo), s_idx + spf)
        if s_idx < len(fit_vo) and e_idx > s_idx:
            chunk = fit_vo[s_idx:e_idx]
            rms[f_idx] = float(np.sqrt(np.mean(chunk ** 2)))

    # Normalize envelope
    p90 = max(0.04, float(np.percentile(rms[speech_start_f:speech_end_f], 90)))
    env = np.clip(rms / p90, 0.0, 1.0)
    env = gaussian_filter1d(env, sigma=0.8)
    env[:speech_start_f] = 0.0
    env[speech_end_f:] = 0.0

    # Apply mesh deformation on mouth ROI
    norm_cx, norm_cy, norm_w, norm_h = mouth_roi
    cx = int(norm_cx * W)
    cy = int(norm_cy * H)
    rx = int(norm_w * W * 0.75)
    ry = int(norm_h * H * 0.75)

    y1 = max(0, cy - int(ry * 1.5))
    y2 = min(H, cy + int(ry * 2.2))
    x1 = max(0, cx - int(rx * 1.5))
    x2 = min(W, cx + int(rx * 1.5))

    yy, xx = np.meshgrid(np.arange(y1, y2, dtype=np.float32), np.arange(x1, x2, dtype=np.float32), indexing="ij")
    nx = (xx - cx) / float(max(1, rx))
    ny = (yy - cy) / float(max(1, ry))
    spatial_w = np.exp(-2.2 * (nx ** 2 + ny ** 2))

    out_frames = frames_arr.copy()
    closed_patch = frames_arr[0, y1:y2, x1:x2].copy()

    for f_idx in range(n_frames):
        openness = float(env[f_idx])
        if openness < 0.08:
            # Silence airlock / pause: smoothly clamp mouth shut
            blend_w = spatial_w[:, :, None] * 0.75
            out_frames[f_idx, y1:y2, x1:x2] = (
                out_frames[f_idx, y1:y2, x1:x2] * (1.0 - blend_w) + closed_patch * blend_w
            ).astype(np.uint8)
        else:
            # Active speech: animate lower jaw & lips downward
            disp_y = (openness * 7.0 * spatial_w).astype(np.float32)
            src_y = np.clip(yy - disp_y, y1, y2 - 1).astype(int)
            out_frames[f_idx, y1:y2, x1:x2] = frames_arr[f_idx, src_y, xx.astype(int)]

    return out_frames, fit_vo

def main():
    print("=== Processing 12-Shot Lip-Sync & Acoustic Airlock Alignment ===", flush=True)
    sr = 48000
    fps = 24.0

    fitted_dialogue_clips = []
    clip_durations = []

    for i in range(1, 13):
        sc_id = f"ep01_{i:02d}"
        in_mp4 = os.path.join(RAW_CLIPS_DIR, f"{sc_id}_veo.mp4")
        dur = get_clip_info(in_mp4)
        clip_durations.append(dur)
        vo_p = os.path.join(VO_DIR, f"{sc_id}.wav")

        vo_data, vo_sr = sf.read(vo_p)
        if vo_data.ndim > 1: vo_data = vo_data[:, 0]
        if vo_sr != sr:
            vo_data = signal.resample(vo_data, int(len(vo_data) * sr / vo_sr))

        in_dur = len(vo_data) / sr
        n_frames_est = int(round(dur * fps))
        speech_frames = max(1, n_frames_est - int(round(1.0 * fps)))
        target_speech_dur = speech_frames / fps
        speed = max(0.80, min(1.25, in_dur / target_speech_dur))
        fit_vo = signal.resample(vo_data, int(len(vo_data) / speed))

        out_synced = os.path.join(RAW_CLIPS_DIR, f"{sc_id}_synced.mp4")
        if os.path.exists(out_synced) and os.path.getsize(out_synced) > 100000:
            print(f"[{i:02d}/12] Reusing existing {sc_id}_synced.mp4", flush=True)
            fitted_dialogue_clips.append((sc_id, fit_vo, dur))
            continue

        # Extract frames with ffmpeg pipe
        cmd_extract = [
            FFMPEG, "-y", "-i", in_mp4,
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-v", "error", "-"
        ]
        p_ex = subprocess.Popen(cmd_extract, stdout=subprocess.PIPE)
        raw_bytes, _ = p_ex.communicate()
        n_frames = len(raw_bytes) // (1280 * 720 * 3)
        frames_arr = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((n_frames, 720, 1280, 3))

        # Apply lip-sync & silence clamp
        mouth_roi = MOUTH_ROIS[sc_id]
        synced_arr, fit_vo = process_lip_sync(frames_arr, vo_data, sr, mouth_roi, dur)

        # Write synced video
        cmd_write = [
            FFMPEG, "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", "1280x720", "-pix_fmt", "rgb24", "-r", "24",
            "-i", "-",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
            out_synced
        ]
        p_wr = subprocess.Popen(cmd_write, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p_wr.communicate(synced_arr.tobytes())
        print(f"[{i:02d}/12] {sc_id}_synced.mp4 ready ({n_frames}f, {dur:.2f}s)", flush=True)

        fitted_dialogue_clips.append((sc_id, fit_vo, dur))
        del frames_arr, synced_arr, raw_bytes
        import gc; gc.collect()

    # Concat 12 synced clips
    concat_txt = os.path.join(OUTPUT_DIR, "concat_synced_list.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for i in range(1, 13):
            p = os.path.join(RAW_CLIPS_DIR, f"ep01_{i:02d}_synced.mp4").replace("\\", "/")
            f.write(f"file '{p}'\n")

    concat_synced_video = os.path.join(OUTPUT_DIR, "concat_synced_video.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", concat_synced_video], check=True)
    total_dur = sum(clip_durations)
    print(f"Total Video Duration: {total_dur:.2f}s", flush=True)

    # Build dialogue stem with exact clip start timestamps
    total_samples = int(total_dur * sr) + sr
    dialogue_track = np.zeros(total_samples, dtype=np.float32)

    cum_t = 0.0
    ass_events = []
    def fmt_time(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int(round((sec - int(sec)) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    import tomllib
    m_info = tomllib.load(open(os.path.join(EP_DIR, "movie.toml"), "rb"))
    sc_meta = {s["id"]: s for s in m_info["scenes"]}

    for sc_id, fit_vo, dur in fitted_dialogue_clips:
        start_s = int((cum_t + 0.55) * sr)
        end_s = min(total_samples, start_s + len(fit_vo))
        dialogue_track[start_s:end_s] += fit_vo[:end_s - start_s] * 1.35

        # Subtitle event
        sub_st = cum_t + 0.40
        sub_en = cum_t + dur - 0.30
        spk = sc_meta[sc_id].get("speaker", "Character")
        line = sc_meta[sc_id].get("line", "")
        text = f"{{\\c&H00D7FF&}}【{spk}】{{\\c&HFFFFFF&}}{line}"
        ass_events.append(f"Dialogue: 0,{fmt_time(sub_st)},{fmt_time(sub_en)},ComicSub,,0,0,0,,{text}")

        cum_t += dur

    # Save dialogue stem
    stem_p = os.path.join(OUTPUT_DIR, "stem_dialogue.wav")
    sf.write(stem_p, np.column_stack([dialogue_track, dialogue_track]), sr)
    print("-> stem_dialogue.wav generated!", flush=True)

    # Write updated ASS subtitles
    ass_header = """[Script Info]
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
Style: IntroCard,Microsoft YaHei,28,&H0000E6FF,&H000000FF,&H0010141E,&HA0000000,-1,0,0,0,100,100,0,0,1,2.5,2.0,7,45,45,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_file = os.path.join(OUTPUT_DIR, "ep01_lottery_heist.ass")
    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(ass_events) + "\n")
    print("-> ep01_lottery_heist.ass updated with exact clip timestamps!", flush=True)

    # Master final encode:
    # 0: concat_synced_video.mp4
    # 1: stem_dialogue.wav (full length)
    # 2: bgm/lottery_heist_jazz_bgm.wav with -stream_loop -1
    # 3: foley/ruin_wind_ambience.wav with -stream_loop -1
    # Filter complex:
    # [1:a]asplit=2[vo_sc][vo_mix];
    # [2:a]volume=0.38[bgm_base];
    # [bgm_base][vo_sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[ducked_bgm];
    # [3:a]volume=0.15[foley_vol];
    # [0:a]volume=0.20[veo_sfx];
    # [vo_mix][ducked_bgm][veo_sfx][foley_vol]amix=inputs=4:duration=first:dropout_transition=2:normalize=0[aout];
    # [0:v]ass=ep01_lottery_heist.ass[vout]
    fc = (
        "[1:a]asplit=2[vo_sc][vo_mix];"
        "[2:a]volume=0.38[bgm_base];"
        "[bgm_base][vo_sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[ducked_bgm];"
        "[3:a]volume=0.15[foley_vol];"
        "[4:a]volume=0.20[veo_sfx];"
        "[vo_mix][ducked_bgm][veo_sfx][foley_vol]amix=inputs=4:duration=first:dropout_transition=2:normalize=0[aout];"
        "[0:v]ass=ep01_lottery_heist.ass[vout]"
    )

    final_mp4 = os.path.join(OUTPUT_DIR, "ep01_lottery_heist_final.mp4")
    cmd_master = [
        FFMPEG, "-y",
        "-i", "concat_synced_video.mp4",
        "-i", "stem_dialogue.wav",
        "-stream_loop", "-1", "-i", "bgm/lottery_heist_jazz_bgm.wav",
        "-stream_loop", "-1", "-i", "foley/ruin_wind_ambience.wav",
        "-i", "concat_veo_video.mp4",
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        "-t", f"{total_dur:.2f}",
        "ep01_lottery_heist_final.mp4"
    ]
    print("Mastering final episode with looped BGM, sidechain ducking, and ASS subtitles...", flush=True)
    subprocess.run(cmd_master, cwd=OUTPUT_DIR, check=True)
    print("=== EPISODE 01 MASTERED SUCCESSFULLY ===", flush=True)

if __name__ == "__main__":
    main()
