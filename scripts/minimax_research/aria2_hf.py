import os
import sys
import subprocess
import requests

def download_hf_file(hf_url, dest_path, max_connections=16):
    dest_path = os.path.abspath(dest_path)
    dest_dir = os.path.dirname(dest_path)
    dest_file = os.path.basename(dest_path)
    os.makedirs(dest_dir, exist_ok=True)
    
    print(f"Resolving redirect for: {hf_url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.head(hf_url, headers=headers, allow_redirects=True, timeout=20)
    r.raise_for_status()
    final_url = r.url
    size_gb = int(r.headers.get("content-length", 0)) / (1024**3)
    print(f"Final URL: {final_url.split('?')[0]}")
    print(f"File size: {size_gb:.2f} GB -> {dest_path}")
    
    aria2c_exe = r"C:\Users\Liang\minimax\.venv\Scripts\aria2c.exe"
    if not os.path.exists(aria2c_exe):
        aria2c_exe = "aria2c"
        
    cmd = [
        aria2c_exe,
        f"-x{max_connections}",
        f"-s{max_connections}",
        "-k1M",
        "-c",
        "--file-allocation=none",
        "--retry-wait=3",
        "-m0",
        "-d", dest_dir,
        "-o", dest_file,
        final_url
    ]
    print(f"Running aria2c with {max_connections} connections...")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise RuntimeError(f"aria2c failed with return code {res.returncode}")
    print(f"\n[OK] Successfully downloaded: {dest_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python aria2_hf.py <hf_url> <dest_path> [connections]")
        sys.exit(1)
    url = sys.argv[1]
    dest = sys.argv[2]
    conn = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    download_hf_file(url, dest, conn)
