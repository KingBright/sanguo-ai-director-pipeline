import os
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(r"C:\Users\Liang\minimax\ACE-Step-1.5")
ARIA2C = r"C:\Users\Liang\minimax\.venv\Scripts\aria2c.exe"

FILES = [
    ("Qwen3-Embedding-0.6B/model.safetensors", 1000000000),
    ("Qwen3-Embedding-0.6B/config.json", 100),
    ("Qwen3-Embedding-0.6B/tokenizer.json", 1000000),
    ("Qwen3-Embedding-0.6B/tokenizer_config.json", 100),
    ("Qwen3-Embedding-0.6B/vocab.json", 100000),
    ("Qwen3-Embedding-0.6B/merges.txt", 100000),
    ("acestep-v15-turbo/model.safetensors", 4000000000),
    ("acestep-v15-turbo/silence_latent.pt", 1000),
    ("vae/diffusion_pytorch_model.safetensors", 300000000),
]

def download_file(rel_path, min_size, max_retries=10):
    dest_file = BASE_DIR / rel_path
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    aria2_ctrl = dest_file.parent / (dest_file.name + ".aria2")
    url = f"https://www.modelscope.cn/models/ACE-Step/Ace-Step1.5/resolve/master/{rel_path}"

    cmd = [
        ARIA2C,
        "-x16",
        "-s16",
        "-k1M",
        "-c",
        "--file-allocation=none",
        "--disable-ipv6=true",
        "--check-certificate=false",
        "--timeout=15",
        "--connect-timeout=10",
        "--max-tries=5",
        "--retry-wait=2",
        "-d", str(dest_file.parent),
        "-o", dest_file.name,
        url
    ]

    for attempt in range(1, max_retries + 1):
        if dest_file.exists() and not aria2_ctrl.exists():
            size = dest_file.stat().st_size
            if size >= min_size:
                print(f"[SKIP] {rel_path} already downloaded ({size / (1024**2):.2f} MB)", flush=True)
                return True
        print(f"[RUN] {rel_path} -> Attempt {attempt}/{max_retries}", flush=True)
        proc = subprocess.run(cmd)
        if proc.returncode == 0 and dest_file.exists() and not aria2_ctrl.exists():
            size = dest_file.stat().st_size
            if size >= min_size:
                print(f"[DONE] {rel_path} ({size / (1024**2):.2f} MB)", flush=True)
                return True
        time.sleep(2)
    return False

if __name__ == "__main__":
    for rel_path, min_size in FILES:
        if not download_file(rel_path, min_size):
            print(f"[ERROR] Failed to download {rel_path}")
            sys.exit(1)
    print("\n[SUCCESS] All ACE-Step 1.5 Turbo files downloaded from ModelScope!")
