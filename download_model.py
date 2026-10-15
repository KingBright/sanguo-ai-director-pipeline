"""MiniMax H3 Model Downloader Helper (Supports ModelScope and HuggingFace)."""
import argparse
import sys
from pathlib import Path

def download_modelscope(target_dir: Path, model_id: str = "MiniMax/MiniMax-H3"):
    print(f"🚀 开始从 ModelScope 国内高速源下载 {model_id} 到: {target_dir}")
    from modelscope.hub.snapshot_download import snapshot_download
    path = snapshot_download(model_id, local_dir=str(target_dir))
    print(f"✅ 模型下载完成，存放于: {path}")

def download_huggingface(target_dir: Path, repo_id: str = "MiniMaxAI/MiniMax-H3", subfolder: str = "FL2VA"):
    print(f"🚀 开始从 Hugging Face 下载 {repo_id} ({subfolder} 核心组件) 到: {target_dir}")
    from huggingface_hub import snapshot_download
    path = snapshot_download(
        repo_id=repo_id,
        allow_patterns=[f"{subfolder}/*"],
        local_dir=str(target_dir),
        local_dir_use_symlinks=False
    )
    print(f"✅ 模型下载完成，存放于: {path}")

def main():
    parser = argparse.ArgumentParser(description="MiniMax H3 权重下载工具")
    parser.add_argument("--source", choices=["modelscope", "huggingface"], default="modelscope", help="下载源 (国内网络强烈推荐 modelscope)")
    parser.add_argument("--target", default="C:/Users/Liang/minimax/MiniMax-H3", help="模型存放目录")
    parser.add_argument("--quant", action="store_true", help="是否下载低显存 NF4/量化版 (约 20GB)")

    args = parser.parse_args()
    target_path = Path(args.target)
    target_path.mkdir(parents=True, exist_ok=True)

    if args.source == "modelscope":
        model_id = "MiniMax/MiniMax-H3-NF4" if args.quant else "MiniMax/MiniMax-H3"
        download_modelscope(target_path, model_id=model_id)
    else:
        download_huggingface(target_path)

if __name__ == "__main__":
    main()
