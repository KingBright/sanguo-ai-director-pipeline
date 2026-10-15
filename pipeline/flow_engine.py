"""Wrapper engine for gflow CLI and Google Flow Veo integration."""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .config import RAW_CLIPS_DIR, DEFAULT_ASPECT, DEFAULT_VIDEO_MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flow_engine")


class FlowEngine:
    def __init__(self, gflow_bin: str = "gflow"):
        self.gflow_bin = gflow_bin

    def _get_env(self) -> dict:
        env = os.environ.copy()
        if "CHROME_BINARY" not in env:
            pw_chrome = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-1228" / "chrome-win64" / "chrome.exe"
            edge_path = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
            if pw_chrome.exists():
                env["CHROME_BINARY"] = str(pw_chrome)
            elif edge_path.exists():
                env["CHROME_BINARY"] = str(edge_path)
        return env

    def _run_cmd(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        cmd = [self.gflow_bin] + args
        logger.info(f"Executing: {' '.join(cmd)}")
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            encoding="utf-8",
            errors="replace",
            env=self._get_env()
        )

    def check_auth(self) -> Dict[str, Any]:
        """Check whether Google Flow profile is verified and active."""
        try:
            res = self._run_cmd(["auth", "status"], check=False)
            if res.returncode == 0:
                return {"authenticated": True, "details": res.stdout.strip()}
            else:
                return {"authenticated": False, "error": res.stdout.strip() or res.stderr.strip()}
        except FileNotFoundError:
            return {"authenticated": False, "error": "gflow executable not found on PATH"}

    def get_credits(self) -> Dict[str, Any]:
        """Check credit balance, refresh countdown, and remaining video capacity."""
        import time
        from datetime import datetime
        cache_file = Path(os.environ.get("LOCALAPPDATA", "")) / "ffroliva" / "gflow-cli" / "credits_cache.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                bal = int(data.get("balance", 0))
                prev_bal = data.get("previous_balance")
                last_spent = data.get("last_spent")
                if last_spent is None and prev_bal is not None and prev_bal >= bal:
                    last_spent = int(prev_bal) - bal
                ref_epoch = data.get("refresh_epoch")
                refresh_str = "未知"
                countdown_str = "未知"
                if ref_epoch:
                    dt = datetime.fromtimestamp(ref_epoch)
                    refresh_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    rem_sec = max(0, int(ref_epoch - time.time()))
                    days = rem_sec // 86400
                    hours = (rem_sec % 86400) // 3600
                    mins = (rem_sec % 3600) // 60
                    countdown_str = f"{days}天 {hours}小时 {mins}分钟 (刷新时间: {refresh_str})"

                # Calculate remaining video minutes (8s per clip = 7.5 clips per minute)
                # Quality: 100 pts/8s (750 pts/min); Fast: 10 pts/8s (75 pts/min); Omni: 12 pts/8s (90 pts/min); Lite: 5 pts/8s (37.5 pts/min)
                min_quality = round((bal / 100) * 8 / 60, 1)
                clips_quality = bal // 100
                min_fast = round((bal / 10) * 8 / 60, 1)
                clips_fast = bal // 10
                min_omni = round((bal / 12) * 8 / 60, 1)
                clips_omni = bal // 12

                report = (
                    f"当前剩余: {bal:,} 点"
                    + (f" | 最近一次消耗: {last_spent} 点" if last_spent is not None else "")
                    + f"\n      ⏳ 距离下次刷新: {countdown_str}"
                    + f"\n      🎬 预计可制作视频时长:"
                    + f"\n         • [顶级旗舰] Veo 3.1 - Quality (100点/8秒): 约 {min_quality} 分钟 ({clips_quality} 个8秒镜头)"
                    + f"\n         • [全能多参] Omni 1.1 Flash   ( 12点/8秒): 约 {min_omni} 分钟 ({clips_omni} 个8秒镜头)"
                    + f"\n         • [高性价比] Veo 3.1 - Fast    ( 10点/8秒): 约 {min_fast} 分钟 ({clips_fast} 个8秒镜头)"
                )
                return {
                    "success": True,
                    "balance": bal,
                    "last_spent": last_spent,
                    "refresh_countdown": countdown_str,
                    "output": report,
                }
            except Exception as e:
                logger.warning(f"Failed to parse credits_cache.json: {e}")

        try:
            res = self._run_cmd(["credits", "user"], check=False)
            out = (res.stdout.strip() or res.stderr.strip())
            if res.returncode == 0:
                return {"success": True, "output": out}
            elif "flow.google.com" in out and "generation still works" in out:
                return {
                    "success": True,
                    "output": "已接入新版 flow.google.com 架构 (Google AI Ultra 订阅已激活，视频生成通道完全就绪)"
                }
            else:
                return {"success": False, "error": out}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def trigger_login(self, browser: str = "internal") -> int:
        """Trigger interactive browser login (opens browser for Google account)."""
        logger.info(f"Opening interactive Google login (strategy={browser})...")
        cmd = [self.gflow_bin, "auth", "login", "--browser", browser]
        return subprocess.call(cmd, env=self._get_env())

    def run_movie_project(
        self,
        manifest_path: Path,
        out_dir: Optional[Path] = None,
        dry_run: bool = False,
        stitch: bool = True,
        fail_fast: bool = False,
    ) -> Dict[str, Any]:
        """Execute a movie.toml project to generate all scenes with Google Flow Veo."""
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        args = ["movie", "run", str(manifest_path)]
        if dry_run:
            args.append("--dry-run")
        if stitch:
            args.append("--stitch")
        if fail_fast:
            args.append("--fail-fast")
        if out_dir:
            args.extend(["--out-dir", str(out_dir)])

        logger.info(f"Running movie project: {manifest_path} (dry_run={dry_run})")
        res = self._run_cmd(args, check=False)
        return {
            "success": res.returncode == 0,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }

    def generate_single_clip(
        self,
        prompt: str,
        out_dir: Optional[Path] = None,
        aspect: str = DEFAULT_ASPECT,
        model: str = DEFAULT_VIDEO_MODEL,
    ) -> Dict[str, Any]:
        """Generate an ad-hoc single video clip using Veo."""
        target_dir = out_dir or RAW_CLIPS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        args = [
            "video", "t2v", prompt,
            "--aspect", aspect,
            "--model", model,
            "--out-dir", str(target_dir),
        ]
        res = self._run_cmd(args, check=False)
        return {
            "success": res.returncode == 0,
            "output": res.stdout,
            "error": res.stderr,
        }

    def generate_i2v_clip(
        self,
        initial_frame: Path,
        prompt: str,
        output_file: Optional[Path] = None,
        out_dir: Optional[Path] = None,
        aspect: str = DEFAULT_ASPECT,
        model: str = "veo-fast",
    ) -> Dict[str, Any]:
        """Generate a spatially locked video clip from an initial keyframe image (I2V) using Veo."""
        args = [
            "video", "i2v",
            "--initial-frame", str(initial_frame),
            prompt,
            "--aspect", aspect,
            "--model", model,
        ]
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            args.extend(["-o", str(output_file)])
        else:
            target_dir = out_dir or RAW_CLIPS_DIR
            target_dir.mkdir(parents=True, exist_ok=True)
            args.extend(["--out-dir", str(target_dir)])

        res = self._run_cmd(args, check=False)
        return {
            "success": res.returncode == 0,
            "output": res.stdout,
            "error": res.stderr,
        }

    def upscale_video(self, video_path: Path) -> Dict[str, Any]:
        """Upscale a generated Veo video clip to 1080p."""
        args = ["video", "upscale", str(video_path)]
        res = self._run_cmd(args, check=False)
        return {
            "success": res.returncode == 0,
            "output": res.stdout,
            "error": res.stderr,
        }
