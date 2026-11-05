#!/usr/bin/env python3
"""Create a repeatable synthetic cast, then render unhurried dialogue with Qwen3.

Requires the existing qwen-tts/torch/soundfile environment and local VoiceDesign
and Base weights. No downloads, duration fitting, pitch shifts or reference voices
from real people. Outputs retain their natural sample rate and duration.
"""
import argparse
import gc
import hashlib
import json
import random
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def render(manifest, destination, model_root, device):
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    destination.mkdir(parents=True, exist_ok=True)
    lines = manifest.get("dialogue", manifest.get("shots", []))
    if not lines:
        raise ValueError("No dialogue to perform")
    # Editing coverage or music must not invalidate already performed dialogue.
    config_hash = digest({"cast": manifest["cast"], "lines": [
        {k: line.get(k) for k in ("id", "speaker", "text", "delivery")} for line in lines
    ]})
    marker = destination / "manifest.sha256"
    if marker.exists() and marker.read_text().strip() != config_hash:
        raise ValueError("This output directory belongs to a different script. Use a new directory.")
    marker.write_text(config_hash + "\n")
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32

    def load(kind):
        path = model_root / f"Qwen3-TTS-12Hz-1.7B-{kind}"
        if not (path / "config.json").is_file():
            raise FileNotFoundError(path)
        return Qwen3TTSModel.from_pretrained(str(path), device_map=device, dtype=dtype)

    def seed(value):
        random.seed(value)
        np.random.seed(value)
        torch.manual_seed(value)

    def write(path, samples, rate):
        samples = np.asarray(samples)
        if samples.ndim != 1 or not np.isfinite(samples).all() or len(samples) < rate * .3:
            raise ValueError(f"Invalid generated speech: {path.name}")
        # Peak safety only. Never change sample count to fit a shot.
        peak = float(np.max(np.abs(samples)))
        if peak < .005:
            raise ValueError(f"Silent speech: {path.name}")
        sf.write(path, samples * min(1., .95 / peak), rate, subtype="PCM_16")

    anchors = destination / "cast"
    anchors.mkdir(exist_ok=True)
    missing = [key for key in manifest["cast"] if not (anchors / f"{key}.wav").exists()]
    if missing:
        model = load("VoiceDesign")
        for key in missing:
            role = manifest["cast"][key]
            seed(role["seed"])
            waves, rate = model.generate_voice_design(
                text=role["reference_text"], language="Chinese", instruct=role["voice"],
                max_new_tokens=1024,
            )
            write(anchors / f"{key}.wav", waves[0], rate)
            print(f"CAST {key}: {len(waves[0])/rate:.2f}s", flush=True)
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    model = load("Base")
    prompts = {}
    for key, role in manifest["cast"].items():
        prompts[key] = model.create_voice_clone_prompt(
            ref_audio=str(anchors / f"{key}.wav"), ref_text=role["reference_text"],
            x_vector_only_mode=False,
        )
    report = []
    for index, shot in enumerate(lines):
        path = destination / f"{shot['id']}.wav"
        if not path.exists():
            seed(manifest["cast"][shot["speaker"]]["seed"] + index + 100)
            waves, rate = model.generate_voice_clone(
                text=shot["text"], language="Chinese", voice_clone_prompt=prompts[shot["speaker"]],
                max_new_tokens=1024, temperature=.7,
            )
            write(path, waves[0], rate)
        samples, rate = sf.read(path)
        duration = len(samples) / rate
        chars = sum("\u4e00" <= c <= "\u9fff" for c in shot["text"])
        record = {"id": shot["id"], "speaker": shot["speaker"], "text": shot["text"],
                  "requested_delivery": shot.get("delivery", ""),
                  "acting_control": "synthetic_voice_reference_and_text_punctuation",
                  "duration": duration, "chars_per_second": chars / duration,
                  "sample_rate": rate, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        report.append(record)
        print(f"LINE {shot['id']} {shot['speaker']}: {duration:.2f}s, {chars/duration:.2f} chars/s", flush=True)
        (destination / "speech_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--model-root", type=Path, required=True)
    p.add_argument("--device", default="cuda:0")
    args = p.parse_args()
    render(json.loads(args.manifest.read_text(encoding="utf-8")), args.output, args.model_root, args.device)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
