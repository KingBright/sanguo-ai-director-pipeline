import os
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(r"C:\Users\Liang\minimax\MiniMax-H3")
ARIA2C = r"C:\Users\Liang\minimax\.venv\Scripts\aria2c.exe"
PROXY = "http://127.0.0.1:7890"

TASKS = [
    {
        "name": "FL2VA DiT Pruned INT8 (19.53GB)",
        "url": "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        "dir": BASE_DIR / "diffusion_models",
        "file": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        "min_size": 20000000000
    },
    {
        "name": "Qwen3-VL 32B INT8 Text Encoder (25.28GB)",
        "url": "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
        "dir": BASE_DIR / "text_encoders",
        "file": "qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
        "min_size": 26000000000
    }
]

def download_file(item, max_retries=100):
    item["dir"].mkdir(parents=True, exist_ok=True)
    dest_file = item["dir"] / item["file"]
    aria2_ctrl = item["dir"] / (item["file"] + ".aria2")

    cmd = [
        ARIA2C,
        f"--all-proxy={PROXY}",
        "-x16",
        "-s16",
        "-k1M",
        "-c",
        "--file-allocation=none",
        "--disable-ipv6=true",
        "--check-certificate=false",
        "--lowest-speed-limit=10K",
        "--timeout=15",
        "--connect-timeout=10",
        "--max-tries=5",
        "--retry-wait=3",
        "-d", str(item["dir"]),
        "-o", item["file"],
        item["url"]
    ]

    for attempt in range(1, max_retries + 1):
        if dest_file.exists() and not aria2_ctrl.exists():
            size = dest_file.stat().st_size
            if size >= item["min_size"]:
                print(f"[SKIP] {item['name']} already complete ({size / (1024**3):.2f} GB).", flush=True)
                return True

        print(f"[RUN] {item['name']} -> Attempt {attempt}/{max_retries}", flush=True)
        proc = subprocess.run(cmd)
        if proc.returncode == 0 and dest_file.exists() and not aria2_ctrl.exists():
            size = dest_file.stat().st_size
            if size >= item["min_size"]:
                print(f"[DONE] {item['name']} successfully downloaded and verified ({size / (1024**3):.2f} GB)!\n", flush=True)
                return True
        print(f"[WARN] Transfer interrupted or presigned URL expired (code {proc.returncode}). Refreshing URL in 2s...", flush=True)
        time.sleep(2)
    return False

def main():
    print("=" * 65, flush=True)
    print("MiniMax H3 High-Speed Direct Downloader (via Proxy 7890)", flush=True)
    print(f"Target Directory: {BASE_DIR}", flush=True)
    print("=" * 65, flush=True)

    for item in TASKS:
        ok = download_file(item)
        if not ok:
            print(f"[ERROR] Failed downloading {item['name']}", flush=True)
            sys.exit(1)

    print("\n🎉 [ALL COMPLETE] All MiniMax H3 weights downloaded and verified successfully!", flush=True)

if __name__ == "__main__":
    main()
