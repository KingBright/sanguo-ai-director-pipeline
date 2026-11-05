#!/usr/bin/env python3
"""Master intact video frames, natural-duration speech, and a real music stem.

This never warps picture geometry or changes video speed. Known color matrices
are explicitly normalized to BT.709 before lossless editing and frame checks.
Each dialogue must fit its shot with a reaction pause, or mastering stops. Keep
the emitted timing/source manifest and separate SRT/stems for manual acceptance.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf

RATE = 48000


def run(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace")[-3000:])
    return p.stdout


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def video_info(path):
    stream = next(s for s in probe(path)["streams"] if s["codec_type"] == "video")
    fps = float(Fraction(stream["r_frame_rate"]))
    frames = int(stream["nb_frames"])
    duration = frames / fps
    signature = tuple(stream.get(k) for k in ("codec_name", "width", "height", "pix_fmt", "r_frame_rate", "time_base", "color_space", "color_range", "color_transfer", "color_primaries"))
    return duration, frames, signature


def check_timing(text, speech_duration, start, video_duration, max_rate=5.5, tail=.4):
    if not all(math.isfinite(x) for x in (speech_duration, start, video_duration)):
        raise ValueError("Non-finite timing")
    if speech_duration <= 0 or start < 0 or start + speech_duration + tail > video_duration:
        raise ValueError(f"Speech does not fit: {start:.2f}s + {speech_duration:.2f}s + {tail:.2f}s > {video_duration:.2f}s. Shorten text or render a longer shot; never accelerate speech.")
    chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    rate = chars / speech_duration
    if max_rate is not None and rate > max_rate:
        raise ValueError(f"Dialogue is too fast ({rate:.2f} chars/s > {max_rate}). Regenerate a slower delivery.")
    return rate


def normalized_speech(path):
    raw = run(["ffmpeg", "-v", "error", "-i", str(path), "-af",
               "loudnorm=I=-18:TP=-2:LRA=7,aresample=48000", "-ac", "2", "-f", "f32le", "-"])
    audio = np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
    active = np.flatnonzero(np.max(np.abs(audio), axis=1) > .003)
    if not len(active):
        raise ValueError(f"Silent speech: {path}")
    # Trim only outer silence, keeping 80 ms before and 150 ms after articulation.
    first = max(0, int(active[0]) - int(.08 * RATE))
    last = min(len(audio), int(active[-1]) + int(.15 * RATE) + 1)
    return audio[first:last], first / RATE, (len(audio) - last) / RATE


def srt_time(t):
    ms = round(t * 1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_hashes(path):
    data = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-an",
                "-vsync", "0", "-f", "framemd5", "-"]).decode()
    return [line.rsplit(",", 1)[-1].strip() for line in data.splitlines() if line and not line.startswith("#")]


def plan_story(manifest, raw_dir, audio_dir, coverage_dir):
    """Let performed dialogue and reactions determine the picture timeline.

    Long speech can cross into a listener shot. Trim whole native frames only;
    if coverage runs out, require more footage rather than changing performance.
    """
    if coverage_dir.exists():
        raise FileExistsError(coverage_dir)
    coverage_dir.mkdir(parents=True)
    used, hashes, shots, canonical = {}, {}, [], {}
    fps = None

    def normalize_color(source):
        if source in canonical:
            return canonical[source]
        stream = next(s for s in probe(source)["streams"] if s["codec_type"] == "video")
        matrix = stream.get("color_space")
        color_range = stream.get("color_range")
        if matrix not in ("bt709", "smpte170m", "bt470bg") or color_range not in ("tv", "pc"):
            raise ValueError(f"{source.name}: unknown color metadata; explicitly identify it before editing")
        if stream.get("color_transfer") not in ("bt709", "smpte170m", "iec61966-2-1") or stream.get("color_primaries") not in ("bt709", "smpte170m", "bt470bg"):
            raise ValueError(f"{source.name}: unknown transfer/primaries; explicitly identify them before editing")
        target = coverage_dir / f"canonical_{len(canonical)}.mp4"
        # Whole-frame color conversion, never spatial deformation or interpolation.
        conversion = "colorspace=all=bt709:range=tv:format=yuv420p"
        run(["ffmpeg", "-v", "error", "-i", str(source), "-vf", conversion, "-an",
             "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", str(target)])
        if video_info(source)[:2] != video_info(target)[:2]:
            raise RuntimeError(f"{source.name}: normalization changed frame count or timing")
        canonical[source] = (target, conversion)
        return target, conversion

    def take(video_name, wanted, pieces, expected, start_frame=None):
        nonlocal fps
        source = (raw_dir / video_name).resolve()
        path, conversion = normalize_color(source)
        _, count, sig = video_info(path)
        native_fps = float(Fraction(sig[4]))
        if fps is not None and native_fps != fps:
            raise ValueError("Mixed native frame rates need an explicit editing decision")
        fps = native_fps
        first = used.get(video_name, 0) if start_frame is None else int(start_frame)
        if not 0 <= first < count:
            raise ValueError(f"{video_name}: invalid reaction start frame {first}")
        length = min(count - first, wanted)
        if length <= 0:
            return 0
        last = first + length
        used[video_name] = max(used.get(video_name, 0), last)
        if path not in hashes:
            hashes[path] = frame_hashes(path)
        expected.extend(hashes[path][first:last])
        segment = coverage_dir / f"segment_{sum(used.values())}_{len(pieces)}.mp4"
        run(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
             f"trim=start_frame={first}:end_frame={last},setpts=PTS-STARTPTS",
             "-an", "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(segment)])
        pieces.append({"path": segment, "source": str(source), "source_sha256": sha(source),
                       "color_reference": str(path), "color_conversion": conversion,
                       "first_frame": first, "end_frame": last})
        return length

    for line in manifest["dialogue"]:
        audio, _, _ = normalized_speech(audio_dir / f"{line['id']}.wav")
        before, after = line.get("before", .25), line.get("after", .4)
        duration = before + len(audio) / RATE + after
        first_path = raw_dir / line["coverage"][0]
        native_fps = float(Fraction(video_info(first_path)[2][4]))
        required = math.ceil(duration * native_fps)
        reaction_frames = round(after * native_fps) if line.get("reaction_video") else 0
        remaining = required - reaction_frames
        pieces, expected = [], []
        for video_name in line["coverage"]:
            remaining -= take(video_name, remaining, pieces, expected)
            if remaining == 0:
                break
        if remaining:
            raise ValueError(f"{line['id']}: performance needs {remaining/native_fps:.2f}s more coverage. Render a reaction/continuation shot.")
        if reaction_frames and take(line["reaction_video"], reaction_frames, pieces, expected, line.get("reaction_start_frame")) != reaction_frames:
            raise ValueError(f"{line['id']}: reaction coverage is too short")
        concat = coverage_dir / f"{line['id']}.ffconcat"
        concat.write_text("ffconcat version 1.0\n" + "".join("file '" + str(x["path"].resolve()).replace("\\", "/").replace("'", "'\\''") + "'\n" for x in pieces), encoding="utf-8")
        beat_path = coverage_dir / f"{line['id']}.mp4"
        run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-an", "-c:v", "copy", str(beat_path)])
        if frame_hashes(beat_path) != expected:
            raise RuntimeError(f"{line['id']}: edited frames differ from source; reject output")
        shots.append({**line, "video": beat_path.name, "start": before,
                      "source_segments": [{k:v for k,v in x.items() if k != "path"} for x in pieces]})
    planned = {**manifest, "shots": shots}
    (coverage_dir / "edit_plan.json").write_text(json.dumps(planned, ensure_ascii=False, indent=2), encoding="utf-8")
    return planned


def master(manifest, raw_dir, audio_dir, music, output):
    if output.exists():
        raise FileExistsError(f"Output must be a new directory: {output}")
    shots = manifest["shots"]
    if not shots:
        raise ValueError("No shots")
    plans, cursor, signature = [], 0., None
    for shot in shots:
        video = (raw_dir / shot.get("video", f"{shot['id']}.mp4")).resolve()
        voice = (audio_dir / f"{shot['id']}.wav").resolve()
        duration, frames, sig = video_info(video)
        if signature is not None and sig != signature:
            raise ValueError(f"Incompatible video streams: {video.name}. Normalize explicitly before mastering.")
        signature = sig
        audio, head_trim, tail_trim = normalized_speech(voice)
        start = float(shot.get("start", .45))
        rate = check_timing(shot["text"], len(audio) / RATE, start, duration,
                            max_rate=shot.get("max_chars_per_second"), tail=shot.get("after", .4))
        plans.append({"shot": shot, "video": video, "voice": voice, "audio": audio,
                      "duration": duration, "frames": frames, "start": start, "offset": cursor,
                      "chars_per_second": rate, "head_trim": head_trim, "tail_trim": tail_trim})
        cursor += duration
    music_duration = float(probe(music)["format"]["duration"])
    if music_duration < cursor:
        raise ValueError(f"Music is too short ({music_duration:.2f}s < {cursor:.2f}s); choose a complete cue.")

    output.mkdir(parents=True)
    dialogue = np.zeros((round(cursor * RATE), 2), dtype=np.float32)
    metadata, captions = [], []
    for index, p in enumerate(plans):
        start = p["offset"] + p["start"]
        at = round(start * RATE)
        end = at + len(p["audio"])
        dialogue[at:end] = p["audio"]
        shot = p["shot"]
        captions.append(f"{index+1}\n{srt_time(start)} --> {srt_time(end/RATE)}\n{shot['text']}\n")
        metadata.append({"id": shot["id"], "speaker": shot["speaker"], "text": shot["text"],
                         "video": str(p["video"]), "video_sha256": sha(p["video"]),
                         "voice_sha256": sha(p["voice"]), "frames": p["frames"],
                         "shot_start": p["offset"], "shot_duration": p["duration"],
                         "speech_start": start, "speech_end": end / RATE,
                         "chars_per_second": p["chars_per_second"], "speed": 1.,
                         "requested_delivery": shot.get("delivery", ""),
                         "source_segments": shot.get("source_segments", []),
                         "outer_silence_trim": [p["head_trim"], p["tail_trim"]]})
    sf.write(output / "dialogue.wav", dialogue, RATE, subtype="PCM_24")
    (output / "dialogue.srt").write_text("\n".join(captions), encoding="utf-8")

    concat = output / "picture.ffconcat"
    def quote(p):
        return str(p).replace("\\", "/").replace("'", "'\\''")
    concat.write_text("ffconcat version 1.0\n" + "".join(f"file '{quote(p['video'])}'\n" for p in plans), encoding="utf-8")
    run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-map", "0:v:0", "-an", "-c:v", "copy", str(output / "picture.mp4")])
    # A separate normalized cue; ducking follows dialogue, without a synthetic tone.
    run(["ffmpeg", "-v", "error", "-i", str(music), "-t", str(cursor), "-af",
         f"loudnorm=I=-27:TP=-4:LRA=9,aresample=48000,afade=t=in:d=0.6,afade=t=out:st={max(0,cursor-2.5)}:d=2.5",
         "-ac", "2", "-c:a", "pcm_s24le", str(output / "music.wav")])
    # Story-specific music rests. These are dramaturgical choices in the script,
    # separate from ordinary dialogue ducking.
    bed, bed_rate = sf.read(output / "music.wav")
    for p in plans:
        gain = p["shot"].get("music_gain", 1.)
        if gain != 1.:
            lo, hi = round(p["offset"] * bed_rate), round((p["offset"] + p["duration"]) * bed_rate)
            envelope = np.full(hi-lo, gain)
            ramp = min(round(.08*bed_rate), len(envelope)//2)
            if ramp:
                envelope[:ramp] = np.linspace(1., gain, ramp)
                envelope[-ramp:] = np.linspace(gain, 1., ramp)
            bed[lo:hi] *= envelope[:len(bed[lo:hi]), None]
    sf.write(output / "music.wav", bed, bed_rate, subtype="PCM_24")
    run(["ffmpeg", "-v", "error", "-i", str(output / "dialogue.wav"), "-i", str(output / "music.wav"),
         "-filter_complex", "[0:a]asplit=2[side][voice];[1:a][side]sidechaincompress=threshold=0.03:ratio=4:attack=15:release=220[bed];[voice][bed]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89:level=false:latency=true[mix]",
         "-map", "[mix]", "-c:a", "pcm_s24le", str(output / "mix.wav")])
    run(["ffmpeg", "-v", "error", "-i", str(output / "picture.mp4"), "-i", str(output / "mix.wav"),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-ar", "48000", "-movflags", "+faststart", str(output / "final.mp4")])
    source_hashes = [h for p in plans for h in frame_hashes(p["video"])]
    if source_hashes != frame_hashes(output / "final.mp4"):
        raise RuntimeError("Decoded output frames differ from source frames. Do not accept this master.")
    report = {"title": manifest["title"], "duration": cursor, "shots": metadata,
              "music": str(music), "music_sha256": sha(music), "video_processing": "stream_copy",
              "decoded_source_frame_match": True, "verified_frames": len(source_hashes),
              "frame_comparison_basis": "intact native frames after declared BT.709 color normalization",
              "speech_speed": 1., "acceptance": "manual_video_and_audio_review_required",
              "limitations": ["Post-dubbed animation is not verified phoneme-level lip sync.",
                              "Source model identity/geometry must be inspected shot by shot."]}
    (output / "master_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"video": str(output / "final.mp4"), "duration": cursor, "shots": len(shots)}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--raw-dir", type=Path, required=True)
    p.add_argument("--audio-dir", type=Path, required=True)
    p.add_argument("--music", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error(f"Output must be a new directory: {a.output}")
    manifest = json.loads(a.manifest.read_text(encoding="utf-8"))
    raw_dir = a.raw_dir
    if "dialogue" in manifest:
        coverage = a.output.with_name(a.output.name + "-coverage")
        manifest = plan_story(manifest, a.raw_dir, a.audio_dir, coverage)
        raw_dir = coverage
    master(manifest, raw_dir, a.audio_dir, a.music, a.output)


if __name__ == "__main__":
    main()
