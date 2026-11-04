import os
import sys
import time
import subprocess
from pathlib import Path

ARIA2C = r"C:\Users\Liang\minimax\.venv\Scripts\aria2c.exe"

MODELS = [
    ("Qwen/Qwen3-TTS-12Hz-1.7B-Base", Path(r"C:\Users\Liang\minimax\Qwen3-TTS-12Hz-1.7B-Base")),
    ("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", Path(r"C:\Users\Liang\minimax\Qwen3-TTS-12Hz-1.7B-VoiceDesign")),
]

FILES = [
    ("config.json", 100),
    ("configuration.json", 10),
    ("generation_config.json", 50),
    ("merges.txt", 100000),
    ("model.safetensors", 3500000000),
    ("preprocessor_config.json", 50),
    ("tokenizer_config.json", 100),
    ("vocab.json", 100000),
    ("speech_tokenizer/config.json", 100),
    ("speech_tokenizer/configuration.json", 10),
    ("speech_tokenizer/model.safetensors", 600000000),
    ("speech_tokenizer/preprocessor_config.json", 50),
]

def download_file(repo_id, base_dir, rel_path, min_size, max_retries=10):
    dest_file = base_dir / rel_path
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    aria2_ctrl = dest_file.parent / (dest_file.name + ".aria2")
    url = f"https://www.modelscope.cn/models/{repo_id}/resolve/master/{rel_path}"

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
                print(f"[SKIP] {repo_id}/{rel_path} already downloaded ({size / (1024**2):.2f} MB)", flush=True)
                return True
        print(f"[RUN] {repo_id}/{rel_path} -> Attempt {attempt}/{max_retries}", flush=True)
        proc = subprocess.run(cmd)
        if proc.returncode == 0 and dest_file.exists() and not aria2_ctrl.exists():
            size = dest_file.stat().st_size
            if size >= min_size:
                print(f"[DONE] {repo_id}/{rel_path} ({size / (1024**2):.2f} MB)", flush=True)
                return True
        time.sleep(2)
    return False

if __name__ == "__main__":
    import shutil
    for repo_id, base_dir in MODELS:
        for rel_path, min_size in FILES:
            # Share speech_tokenizer between Base and VoiceDesign to save 650MB download time!
            if rel_path.startswith("speech_tokenizer/") and repo_id.endswith("VoiceDesign"):
                src = MODELS[0][1] / rel_path
                dst = base_dir / rel_path
                if src.exists() and not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    print(f"[COPY] Reused {rel_path} from Base", flush=True)
                    continue
            if not download_file(repo_id, base_dir, rel_path, min_size):
                print(f"[ERROR] Failed {repo_id}/{rel_path}")
                sys.exit(1)
    print("\n[SUCCESS] All Qwen3-TTS Base + VoiceDesign models downloaded!")
