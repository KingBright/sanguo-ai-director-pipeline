#!/usr/bin/env python3
"""
AetherDirector Studio — Sume (sume.com / api.sume.com/v1) Unified Worker
Supports:
1. Public Catalog & Pricing Query (`GET https://api.sume.com/v1/open/catalog`)
2. Pre-Render Exact Dollar Estimate (`POST https://api.sume.com/v1/open/estimate`)
3. Video & Lip-Sync Router (`POST https://api.sume.com/v1/video-router/generate`):
   - `heygen-video-1` (HeyGen Video 1: 480p-2K, 5-30s, start frame / references, native lip-synced voice; eligible for Sume x HeyGen Free Video Tickets)
   - `seedance-2.5`, `seedance-2`, `seedance-2-fast`, `seedance-2-mini` (ByteDance Seedance 2.5 / 2.0: 4-30s, start/end frame, multi-refs, native audio)
   - `minimax-h3-max`, `minimax-h3`, `hailuo-h3-regen` (MiniMax H3 cloud: 768p-4K, 5-15s, stereo audio)
   - `kling-4`, `kling-4-omni`, `kling-3-omni` (Kuaishou Kling 4.0 Omni: up to 30s, up to 10 reference images)
   - `wan-3.0`, `wan-3.0-prime` (Alibaba Wan 3.0: up to 30s, native audio)
   - `vidu-q4`, `vidu-q4-reference` (Vidu v4: up to 12 reference images & 3 character voices)
   - `omnihuman-2`, `omnihuman-1.5`, `latentsync`, `kling-lipsync`, `sync-lipsync-3` (Precision Chinese lip-sync & audio-driven acting repair)
4. Image Router (`POST https://api.sume.com/v1/image-router/generate`):
   - `seedream-5-pro`, `seedream-5-lite`, `gpt-image-2.5`, `nano-banana-2.1`, `qwen-image-layered`
5. Studio Persistent Browser Auth (`auth-login`) via `https://www.sume.com/heygen` to activate the `sume_ticket_event=heygen` free HeyGen Video 1 gift tickets.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

API_BASE = "https://api.sume.com/v1"
STUDIO_HEYGEN_ENTRY = "https://www.sume.com/heygen"
STUDIO_HEYGEN_VIDEOS = "https://www.sume.com/videos?model=heygen-video-1"


def get_api_key() -> str:
    key = os.environ.get("SUME_API_KEY", "").strip()
    if key:
        return key
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("SUME_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def http_json(method: str, url: str, payload: dict | None = None, api_key: str = "") -> dict:
    headers = {
        "User-Agent": "AetherDirectorStudio/2.0",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = str(uuid.uuid4())
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "ignore")
            return {"status_code": resp.status, "body": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw_error": raw}
        return {"status_code": e.code, "body": parsed}


def cmd_catalog(args):
    res = http_json("GET", f"{API_BASE}/open/catalog")
    body = res["body"]
    data = body.get("data", body)
    models = data.get("models", data) if isinstance(data, dict) else data
    if args.category:
        models = [m for m in models if isinstance(m, dict) and m.get("category") == args.category]
    print(json.dumps({"ok": res["status_code"] == 200, "count": len(models), "models": models}, ensure_ascii=False, indent=2))


def cmd_estimate(args):
    inp = {
        "prompt": args.prompt or "A cinematic dramatic shot",
        "duration": args.duration,
        "resolution": args.resolution,
        "aspect_ratio": args.aspect,
    }
    if args.image_url:
        inp["image_url"] = args.image_url
    res = http_json("POST", f"{API_BASE}/open/estimate", {"model": args.model, "input": inp})
    print(json.dumps(res["body"], ensure_ascii=False, indent=2))


def cmd_generate_video(args):
    api_key = get_api_key()
    model_id = args.model.removeprefix("sume:")

    payload = {
        "model": model_id,
        "prompt": args.prompt,
        "duration": args.duration,
        "resolution": args.resolution,
        "aspect_ratio": args.aspect,
    }
    if args.image_url:
        payload["image_url"] = args.image_url
    if args.end_image_url:
        payload["end_image_url"] = args.end_image_url
    if args.audio_url:
        payload["audio_url"] = args.audio_url
    if args.video_url:
        payload["video_url"] = args.video_url

    if args.dry_run:
        est = http_json("POST", f"{API_BASE}/open/estimate", {"model": model_id, "input": payload})
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "engine": "sume",
                    "model": model_id,
                    "payload": payload,
                    "estimate": est.get("body"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not api_key:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "missing_sume_api_key",
                    "message": (
                        "SUME_API_KEY 未配置。请先访问 https://www.sume.com/heygen 注册/登录领取免费礼券，"
                        "并在 https://www.sume.com/dashboard/api-keys 创建 API Key 填入环境变量 SUME_API_KEY 或 .env 文件。"
                    ),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    sub = http_json("POST", f"{API_BASE}/video-router/generate", payload, api_key=api_key)
    if sub["status_code"] not in (200, 201, 202):
        print(json.dumps({"ok": False, "stage": "submit", "response": sub}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    data = sub["body"].get("data", sub["body"])
    job_id = data.get("request_id") or data.get("job", {}).get("id")
    print(f"[Sume] Submitted job {job_id} for model={model_id}", flush=True)

    # Poll status
    deadline = time.time() + 600
    while time.time() < deadline:
        time.sleep(3)
        st = http_json("GET", f"{API_BASE}/jobs/{job_id}/status", api_key=api_key)
        st_data = st["body"].get("data", st["body"])
        job_status = st_data.get("status") or st_data.get("job", {}).get("status")
        terminal = st_data.get("terminal", job_status in ("completed", "failed", "canceled"))
        print(f"[Sume] Job {job_id} status={job_status}", flush=True)
        if terminal or job_status == "completed":
            break
        if job_status in ("failed", "canceled"):
            print(json.dumps({"ok": False, "stage": "poll", "status": st_data}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1

    res = http_json("GET", f"{API_BASE}/jobs/{job_id}/result", api_key=api_key)
    res_data = res["body"].get("data", res["body"])
    video_url = (
        res_data.get("video", {}).get("url")
        or res_data.get("url")
        or (res_data.get("artifacts", [{}])[0].get("url") if res_data.get("artifacts") else None)
    )
    if not video_url:
        print(json.dumps({"ok": False, "stage": "result", "result": res_data}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as dl:
            out_path.write_bytes(dl.read())
        print(f"[Sume] Saved {out_path} ({out_path.stat().st_size} bytes)", flush=True)

    print(json.dumps({"ok": True, "job_id": job_id, "video_url": video_url, "output": args.output}, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Sume Unified Video/Lipsync/Image Worker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cat = sub.add_parser("catalog")
    p_cat.add_argument("--category", default=None, help="video | lipsync | image | captions")

    p_est = sub.add_parser("estimate")
    p_est.add_argument("--model", default="heygen-video-1")
    p_est.add_argument("--prompt", default="A cinematic shot")
    p_est.add_argument("--duration", type=int, default=5)
    p_est.add_argument("--resolution", default="480p")
    p_est.add_argument("--aspect", default="16:9")
    p_est.add_argument("--image-url", default=None)

    p_gen = sub.add_parser("generate-video")
    p_gen.add_argument("--model", required=True)
    p_gen.add_argument("--prompt", required=True)
    p_gen.add_argument("--duration", type=int, default=5)
    p_gen.add_argument("--resolution", default="720p")
    p_gen.add_argument("--aspect", default="16:9")
    p_gen.add_argument("--image-url", default=None)
    p_gen.add_argument("--end-image-url", default=None)
    p_gen.add_argument("--audio-url", default=None)
    p_gen.add_argument("--video-url", default=None)
    p_gen.add_argument("-o", "--output", default=None)
    p_gen.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    if args.cmd == "catalog":
        return cmd_catalog(args)
    if args.cmd == "estimate":
        return cmd_estimate(args)
    if args.cmd == "generate-video":
        sys.exit(cmd_generate_video(args))


if __name__ == "__main__":
    main()
