#!/usr/bin/env python3
"""Edit native audio/video performances together; never replace their dialogue.

Manifest: title, shots[{id, file, first_frame, end_frame, text, review}].
Frame interval is half open. All clips must share resolution and constant fps.
Output is always a candidate, never automatically a creatively approved film.
"""
import argparse
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf

from clean_master import run, probe, sha, frame_hashes

RATE = 48000


def inspect_clip(path, first, end):
    streams = probe(path)["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    a = next((s for s in streams if s["codec_type"] == "audio"), None)
    if a is None:
        raise ValueError(f"{path}: native dialogue audio is missing")
    fps = Fraction(v["r_frame_rate"])
    if fps != Fraction(v["avg_frame_rate"]):
        raise ValueError(f"{path}: variable frame rate requires an explicit conform")
    if type(first) is not int or type(end) is not int or not 0 <= first < end <= int(v["nb_frames"]):
        raise ValueError(f"{path}: invalid frame interval")
    if abs(float(a.get("start_time", 0)) - float(v.get("start_time", 0))) > .001:
        raise ValueError(f"{path}: nonaligned source stream starts require an explicit correction")
    if float(a.get("duration", 0)) + .001 < end / float(fps):
        raise ValueError(f"{path}: audio does not cover the selected picture interval")
    if (v.get("color_space") not in ("bt709", "smpte170m", "bt470bg")
        or v.get("color_range") not in ("tv", "pc")
        or v.get("color_transfer") not in ("bt709", "smpte170m", "iec61966-2-1")
        or v.get("color_primaries") not in ("bt709", "smpte170m", "bt470bg")):
        raise ValueError(f"{path}: unknown color metadata")
    # Integer samples per frame prevents accumulating fractional trim errors.
    if (RATE / fps).denominator != 1:
        raise ValueError("Frame rate has fractional samples at 48 kHz; explicit audio conform required")
    return fps, (v["width"], v["height"])


def master(manifest, raw_dir, output, music=None):
    if output.exists():
        raise FileExistsError(output)
    if not manifest.get("shots"):
        raise ValueError("No shots")
    prepared = []
    signature = None
    for shot in manifest["shots"]:
        source = (raw_dir / shot["file"]).resolve()
        fps, size = inspect_clip(source, shot["first_frame"], shot["end_frame"])
        if signature is not None and signature != (fps, size):
            raise ValueError("Mixed frame rates or sizes; choose matching source footage")
        signature = fps, size
        prepared.append((shot, source))
    output.mkdir(parents=True)
    parts, voices, hashes, records = [], [], [], []
    cursor = 0
    for index, (shot, source) in enumerate(prepared):
        first, end = shot["first_frame"], shot["end_frame"]
        start_s, end_s = first / float(fps), end / float(fps)
        segment = output / f"picture_{index:02}.mp4"
        conversion = "colorspace=all=bt709:range=tv:format=yuv420p"
        run(["ffmpeg", "-v", "error", "-i", str(source), "-vf",
             f"{conversion},trim=start_frame={first}:end_frame={end},setpts=PTS-STARTPTS",
             "-an", "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", str(segment)])
        # Decode native audio from time zero, then cut on exactly the same frame clock.
        # No silence trimming, time stretching, per-line replacement, or independent offsets.
        pcm = np.frombuffer(run(["ffmpeg", "-v", "error", "-i", str(source), "-map", "0:a:0",
                                "-ar", str(RATE), "-ac", "2", "-f", "f32le", "-"]), dtype="<f4").reshape(-1, 2)
        lo, hi = int(first * RATE / fps), int(end * RATE / fps)
        if len(pcm) < hi:
            raise ValueError(f"{source}: decoded native audio is too short")
        voices.append(pcm[lo:hi].copy())
        parts.append(segment)
        segment_hashes = frame_hashes(segment)
        if len(segment_hashes) != end - first:
            raise RuntimeError("Source frame count changed")
        hashes.extend(segment_hashes)
        records.append({**shot, "source": str(source), "source_sha256": sha(source),
                        "offset": cursor, "duration": end_s-start_s,
                        "audio_interval": [start_s, end_s], "video_interval": [start_s, end_s],
                        "color_conversion": conversion, "audio_replaced": False})
        cursor += end_s-start_s
    listing = output / "concat.txt"
    listing.write_text("\n".join(f"file '{p.name}'" for p in parts), encoding="utf-8")
    run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c", "copy", str(output / "picture.mp4")])
    voice = np.concatenate(voices)
    sf.write(output / "native.wav", voice, RATE, subtype="FLOAT")
    mix = output / "native.wav"
    if music:
        # Deliberately quiet bed, with short ramps at the boundaries and ducking for speech.
        run(["ffmpeg", "-v", "error", "-i", str(output / "native.wav"), "-i", str(music),
             "-filter_complex",
             f"[0:a]asplit=2[v][s];[1:a]atrim=duration={cursor},apad=whole_dur={cursor},"
             f"loudnorm=I=-32:TP=-5:LRA=7,aresample=48000,afade=t=in:d=0.3,"
             f"afade=t=out:st={max(0,cursor-.8)}:d=0.8[m];"
             "[m][s]sidechaincompress=threshold=0.03:ratio=5:attack=10:release=200[b];"
             "[v][b]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89:level=false:latency=true[out]",
             "-map", "[out]", "-c:a", "pcm_f32le", str(output / "mix.wav")])
        mix = output / "mix.wav"
    run(["ffmpeg", "-v", "error", "-i", str(output / "picture.mp4"), "-i", str(mix),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(output / "master.mp4")])
    if frame_hashes(output / "master.mp4") != hashes:
        raise RuntimeError("Master differs from declared full-frame segments")
    recovered, rate = sf.read(output / "native.wav", dtype="float32", always_2d=True)
    if rate != RATE or not np.array_equal(voice, recovered):
        raise RuntimeError("Native performance PCM was changed")
    report = {"title": manifest["title"], "duration": cursor, "shots": records,
              "audio_mode": "native_joint_generation", "speed": 1,
              "verified_frames": len(hashes), "native_pcm_preserved": True,
              "music": str(music) if music else None, "music_sha256": sha(music) if music else None,
              "acceptance": "candidate_requires_story_and_performance_review",
              "user_acceptance": "not_reviewed",
              "limits": ["Preserved native timing is not proof that the model articulated correctly.",
                         "Source mouth motion, acting, voice continuity and narrative must be reviewed."]}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--raw-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--music", type=Path)
    a = p.parse_args()
    r = master(json.loads(a.manifest.read_text(encoding="utf-8")), a.raw_dir, a.output, a.music)
    print(json.dumps({"video": str(a.output / "master.mp4"), "duration": r["duration"]}))
