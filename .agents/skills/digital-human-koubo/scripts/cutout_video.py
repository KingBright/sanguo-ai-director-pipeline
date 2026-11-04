#!/usr/bin/env python3
"""Cross-platform GPU-accelerated replacement for cutout_video.py on Windows/Linux (AMD ROCm gfx1151 / CUDA / CPU) and macOS.
Replaces macOS-only `personmask.swift` with PyTorch GPU DeepLabV3-MobileNetV3 person segmentation when not on Darwin,
while preserving 100% CLI flag and output compatibility (`<output>.webm` VP9+alpha and `<output>_mask.mp4`).
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
import numpy as np

a = sys.argv[1:]
if len(a) < 2:
    sys.exit(__doc__)
src, dst = Path(a[0]), Path(a[1])
opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
feather, smooth, grow, shrink = (
    opt("--feather", 1.5),
    int(opt("--smooth", 3)),
    int(opt("--grow", 0)),
    int(opt("--shrink", 1)),
)
t0, t1 = opt("--from", 0.0), opt("--to", 0.0)
seek = (["-ss", f"{t0:.3f}"] if t0 > 0 else []) + (["-to", f"{t1:.3f}"] if t1 > 0 else [])
HERE = Path(__file__).resolve().parent

import re

err_out = subprocess.run(
    ["ffmpeg", "-i", str(src)],
    capture_output=True,
    text=True,
).stderr
m_res = re.search(r"Stream #0:\d+.*Video:.*?, (\d{2,5})x(\d{2,5})", err_out)
m_fps = re.search(r"(\d+(?:\.\d+)?)\s+fps", err_out)
if not m_res:
    sys.exit(f"无法读取视频分辨率: {src}")
W, H = int(m_res.group(1)), int(m_res.group(2))
fps = m_fps.group(1) if m_fps else "30"
mask = dst.with_name(dst.stem + "_mask.mp4")

vf = ",".join(
    f
    for f in [
        f"tmix=frames={smooth}" if smooth > 1 else "",
        *(["dilation"] * grow),
        *(["erosion"] * shrink),
        f"gblur=sigma={feather}" if feather > 0 else "",
        "format=gray",
    ]
    if f
)

if platform.system() == "Darwin":
    PM = HERE / "bin/personmask"
    if not PM.exists():
        sw = HERE / "personmask.swift"
        if not sw.exists():
            sys.exit("找不到 personmask.swift")
        PM.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", "-swift-version", "5", str(sw), "-o", str(PM)], check=True)
    dec = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", *seek, "-i", str(src), "-f", "rawvideo", "-pix_fmt", "bgra", "-"],
        stdout=subprocess.PIPE,
    )
    pm = subprocess.Popen([str(PM), str(W), str(H), "person"], stdin=dec.stdout, stdout=subprocess.PIPE)
    enc = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-s",
            f"{W}x{H}",
            "-r",
            fps,
            "-i",
            "-",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-crf",
            "12",
            "-pix_fmt",
            "yuv420p",
            str(mask),
        ],
        stdin=pm.stdout,
    )
    dec.wait()
    pm.wait()
    if enc.returncode or not mask.exists():
        sys.exit("遮罩生成失败")
else:
    # GPU-accelerated PyTorch person segmentation (AMD ROCm gfx1151 / CUDA / CPU)
    import torch
    import torch.nn.functional as F
    from torchvision.models.segmentation import (
        deeplabv3_mobilenet_v3_large,
        DeepLabV3_MobileNet_V3_Large_Weights,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    weights = DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT
    seg_model = deeplabv3_mobilenet_v3_large(weights=weights).to(device).eval()
    PERSON_CLASS = 15  # VOC person class index

    dec = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", *seek, "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    enc = subprocess.Popen(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-s",
            f"{W}x{H}",
            "-r",
            fps,
            "-i",
            "-",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-crf",
            "12",
            "-pix_fmt",
            "yuv420p",
            str(mask),
        ],
        stdin=subprocess.PIPE,
    )

    frame_bytes = W * H * 3
    mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)

    with torch.no_grad():
        while True:
            buf = dec.stdout.read(frame_bytes) if dec.stdout else b""
            if len(buf) < frame_bytes:
                break
            arr = np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 3)
            x = torch.from_numpy(arr.copy()).to(device=device, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0
            # Resize to 520 short side for fast GPU inference
            scale = 520.0 / min(H, W)
            ih, iw = int(round(H * scale)), int(round(W * scale))
            x_in = (F.interpolate(x, size=(ih, iw), mode="bilinear", align_corners=False) - mean) / std
            logits = seg_model(x_in)["out"]
            probs = torch.softmax(logits, dim=1)[:, PERSON_CLASS : PERSON_CLASS + 1]
            alpha = F.interpolate(probs, size=(H, W), mode="bilinear", align_corners=False)[0, 0]
            gray = (alpha.clamp(0.0, 1.0) * 255.0).byte().cpu().numpy()
            if enc.stdin:
                enc.stdin.write(gray.tobytes())

    if enc.stdin:
        enc.stdin.close()
    dec.wait()
    enc.wait()
    if enc.returncode or not mask.exists():
        sys.exit("遮罩生成失败")

# 2) 原视频 + 遮罩 → alphamerge → 透明视频
codec = (
    ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-row-mt", "1", "-auto-alt-ref", "0"]
    if dst.suffix == ".webm"
    else ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
)
subprocess.run(
    [
        "ffmpeg",
        "-loglevel",
        "error",
        "-y",
        *seek,
        "-i",
        str(src),
        "-i",
        str(mask),
        "-filter_complex",
        "[1:v]format=gray,scale=%d:%d[m];[0:v][m]alphamerge" % (W, H),
        "-an",
        *codec,
        str(dst),
    ],
    check=True,
)
cov = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", str(mask), "-vf", "fps=1,scale=64:-2,format=gray", "-f", "rawvideo", "-"],
    capture_output=True,
).stdout
frac = sum(1 for b in cov if b > 128) / max(1, len(cov))
print(f"OK: {dst} ({W}x{H}, person area ~{frac:.0%})  mask: {mask}")
if frac > 0.6:
    print(f"WARN: person occupies {frac:.0%}, consider medium shot for TextBehind.")
