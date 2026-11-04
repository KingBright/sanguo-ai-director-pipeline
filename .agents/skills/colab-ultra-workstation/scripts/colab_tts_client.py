#!/usr/bin/env python3
"""
Unified Google Colab L4 Multi-Model (VoxCPM2 + Fun-CosyVoice3-0.5B + IndexTTS 2.5) TTS Orchestrator.
Supports:
  1. Single-item CLI (--engine voxcpm2|cosyvoice3|indextts25|auto --spk-wav ... --text ... --output ...)
  2. Batch manifest CLI (--manifest jobs.json)
  3. Cortex VoiceWorker job mode (--cortex-request request.json)
  4. Multi-process queue lock with warm session handoff + guaranteed `colab stop` when queue drains.
"""
from __future__ import annotations
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

REAL_HOME = Path("/Users/jinliang") if Path("/Users/jinliang").exists() else Path.home()
REPO_ROOT = Path("/Users/jinliang/workspace/hacker-s-news")
TRACE_LOG = REPO_ROOT / ".task-work/colab_tts_trace.log"
COLAB_BIN = os.environ.get("COLAB_BIN") or shutil.which("colab") or str(REAL_HOME / ".local/bin/colab")
RUNNER_SCRIPT = str(Path(__file__).resolve().parents[1] / "examples/cloud_tts_runner.py")
DEFAULT_PROXY = os.environ.get("COLAB_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or "http://127.0.0.1:8228"
DEFAULT_PROMPT_TEXT = "Hello 大家好，这里是 Fresh Loop 新闻速度，我们将给你带来最新鲜的新闻资讯。"
CACHE_ROOT = Path(os.environ.get("CORTEX_DATA_DIR", str(REAL_HOME / ".freshloop"))) / "cache"
LOCK_FILE = CACHE_ROOT / "colab-tts.lock"
QUEUE_DIR = CACHE_ROOT / "colab-queue"


def log_trace(msg: str) -> None:
    print(msg, flush=True)
    try:
        TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(TRACE_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def colab_env(proxy: str) -> dict:
    env = os.environ.copy()
    env["HOME"] = str(REAL_HOME)
    env["PATH"] = f"{REAL_HOME / '.local/bin'}:/opt/homebrew/bin:/usr/local/bin:" + env.get("PATH", "")
    if proxy:
        env["http_proxy"] = proxy
        env["https_proxy"] = proxy
    return env


def run_colab(args_list: list[str], proxy: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [COLAB_BIN] + args_list
    log_trace(f"[colab-tts] $ {' '.join(cmd)}")
    timeout_sec = 2520 if "exec" in args_list else (150 if "download" in args_list else 180)
    try:
        res = subprocess.run(cmd, env=colab_env(proxy), text=True, capture_output=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        log_trace(f"[stderr] colab command timed out after {timeout_sec}s: {' '.join(cmd)}")
        if check:
            raise RuntimeError(f"COLAB_TTS[timeout] colab command timed out after {timeout_sec}s: {' '.join(cmd)}") from None
        return subprocess.CompletedProcess(cmd, 124, stdout=exc.stdout or "", stderr=exc.stderr or "timed out")
    if res.stdout:
        log_trace(res.stdout.strip())
    if res.stderr:
        log_trace(f"[stderr] {res.stderr.strip()}")
    if check and res.returncode != 0:
        combined = f"{res.stdout or ''}\n{res.stderr or ''}".lower()
        quota_markers = (
            "compute unit",
            "out of compute",
            "quota",
            "insufficient balance",
            "resource exhausted",
            "gpu unavailable",
            "cannot connect to gpu",
            "usage limit",
            "too many sessions",
        )
        tag = "COLAB_TTS[quota]" if any(m in combined for m in quota_markers) else "COLAB_TTS[error]"
        raise RuntimeError(f"{tag} colab command failed (exit={res.returncode}): {' '.join(cmd)}\n{res.stderr}")
    return res


def select_engine(requested: str, job_id: str = "", voice_kind: str = "") -> str:
    req = (requested or "auto").strip().lower()
    if req in ("cosyvoice3", "cosyvoice", "colab_cosyvoice3", "fun-cosyvoice3"):
        return "cosyvoice3"
    if req in ("indextts25", "indextts", "colab_indextts25") and os.environ.get("ALLOW_INDEXTTS25") == "1":
        return "indextts25"
    # Default all requests (including legacy cortex indextts25 requests) to voxcpm2
    # due to superior Chinese-English bilingual pronunciation accuracy.
    return "voxcpm2"


def has_waiting_peers() -> bool:
    if not QUEUE_DIR.exists():
        return False
    now = time.time()
    for p in QUEUE_DIR.glob("*.waiting"):
        try:
            if now - p.stat().st_mtime > 1800:
                p.unlink(missing_ok=True)
                continue
            pid = int(p.stem)
            if pid == os.getpid():
                continue
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, FileNotFoundError):
            p.unlink(missing_ok=True)
        except PermissionError:
            return True
    return False


def ensure_session(session: str, gpu: str, proxy: str) -> None:
    for attempt in range(3):
        ls_res = run_colab(["ls"], proxy, check=False)
        if session in (ls_res.stdout or ""):
            log_trace(f"[colab-tts] Reusing active Colab session '{session}'")
            return
        if ls_res.returncode != 0 and ("No active" not in (ls_res.stdout or "") and "No active" not in (ls_res.stderr or "")):
            time.sleep(3)
            continue
        break
    run_colab(["new", "-s", session, "--gpu", gpu], proxy, check=True)


def strip_file_uri(path_str: str) -> str:
    if path_str.startswith("file://"):
        return path_str[len("file://") :]
    return path_str


def validate_wav_file(path: Path) -> tuple[int, int, float]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.getnframes()
        if channels != 1 or sampwidth != 2 or rate <= 0:
            raise ValueError(f"Unsupported WAV format in {path}: ch={channels}, width={sampwidth}, sr={rate}")
        dur = frames / float(rate)
        if dur < 0.4:
            raise ValueError(f"WAV too short ({dur:.2f}s) in {path}")
        return rate, frames, dur


def stitch_wavs_to_mp3(wav_paths: list[Path], output_mp3: Path, silence_ms: int = 250) -> int:
    if not wav_paths:
        raise ValueError("No WAV files to stitch")
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav_file:
        combined_wav = Path(tmp_wav_file.name)

    try:
        target_rate = None
        total_frames = 0
        with wave.open(str(combined_wav), "wb") as out_wf:
            for idx, wp in enumerate(wav_paths):
                with wave.open(str(wp), "rb") as in_wf:
                    rate = in_wf.getframerate()
                    if target_rate is None:
                        target_rate = rate
                        out_wf.setnchannels(1)
                        out_wf.setsampwidth(2)
                        out_wf.setframerate(target_rate)
                    elif rate != target_rate:
                        raise ValueError(f"Sample rate mismatch: {rate} != {target_rate}")
                    if idx > 0 and silence_ms > 0:
                        sil_frames = int(target_rate * (silence_ms / 1000.0))
                        out_wf.writeframes(b"\x00\x00" * sil_frames)
                        total_frames += sil_frames
                    frames = in_wf.getnframes()
                    out_wf.writeframes(in_wf.readframes(frames))
                    total_frames += frames

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(combined_wav),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(output_mp3),
        ]
        subprocess.run(cmd, env=colab_env(""), check=True)
        duration_sec = int((total_frames + target_rate - 1) // target_rate)
        return max(duration_sec, 1)
    finally:
        combined_wav.unlink(missing_ok=True)



def download_wav_possibly_chunked(session: str, remote_path: str, temp_dl: Path, proxy: str) -> None:
    mp3_remote = f"{remote_path}.mp3"
    mp3_parts_meta = temp_dl.with_suffix(".mp3.parts")
    mp3_parts_meta.unlink(missing_ok=True)
    res_mp3 = run_colab(["download", "-s", session, f"{mp3_remote}.parts", str(mp3_parts_meta)], proxy, check=False)
    if res_mp3.returncode == 0 and mp3_parts_meta.exists():
        try:
            num_mp3_parts = int(mp3_parts_meta.read_text(encoding="utf-8").strip())
        except Exception:
            num_mp3_parts = 0
        mp3_parts_meta.unlink(missing_ok=True)
        if num_mp3_parts > 0:
            log_trace(f"[colab-tts] Downloading compressed {mp3_remote} in {num_mp3_parts} fast 500KB chunks...")
            assembled_mp3 = bytearray()
            part_files = []
            for i in range(num_mp3_parts):
                pf = temp_dl.with_suffix(f".mp3.part{i}")
                part_files.append(pf)
                if pf.exists() and pf.stat().st_size > 0:
                    assembled_mp3.extend(pf.read_bytes())
                    continue
                for p_att in range(1, 5):
                    try:
                        run_colab(["download", "-s", session, f"{mp3_remote}.part{i}", str(pf)], proxy, check=True)
                        if pf.exists() and pf.stat().st_size > 0:
                            break
                    except Exception as exc:
                        pf.unlink(missing_ok=True)
                        if p_att >= 4:
                            raise
                        time.sleep(2)
                assembled_mp3.extend(pf.read_bytes())
            tmp_mp3 = temp_dl.with_suffix(".dl.mp3")
            tmp_mp3.write_bytes(bytes(assembled_mp3))
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(tmp_mp3), "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(temp_dl)],
                env=colab_env(""),
                check=True,
            )
            tmp_mp3.unlink(missing_ok=True)
            for pf in part_files:
                pf.unlink(missing_ok=True)
            return

    parts_meta = temp_dl.with_suffix(".parts")
    parts_meta.unlink(missing_ok=True)
    res = run_colab(["download", "-s", session, f"{remote_path}.parts", str(parts_meta)], proxy, check=False)
    if res.returncode == 0 and parts_meta.exists():
        try:
            num_parts = int(parts_meta.read_text(encoding="utf-8").strip())
        except Exception:
            num_parts = 1
        parts_meta.unlink(missing_ok=True)
        if num_parts > 1:
            log_trace(f"[colab-tts] Downloading {remote_path} in {num_parts} chunks...")
            assembled = bytearray()
            part_files = []
            for i in range(num_parts):
                part_file = temp_dl.with_suffix(f".part{i}")
                part_files.append(part_file)
                if part_file.exists() and part_file.stat().st_size > 0:
                    assembled.extend(part_file.read_bytes())
                    continue
                for p_attempt in range(1, 5):
                    try:
                        run_colab(["download", "-s", session, f"{remote_path}.part{i}", str(part_file)], proxy, check=True)
                        if part_file.exists() and part_file.stat().st_size > 0:
                            break
                    except Exception as exc:
                        part_file.unlink(missing_ok=True)
                        if p_attempt >= 4:
                            raise
                        time.sleep(2)
                assembled.extend(part_file.read_bytes())
            temp_dl.write_bytes(bytes(assembled))
            for pf in part_files:
                pf.unlink(missing_ok=True)
            return
    run_colab(["download", "-s", session, remote_path, str(temp_dl)], proxy, check=True)

def run_colab_exec_watching_sha(session: str, runner_script: str, expected_shas: list[str], proxy: str, timeout_sec: int = 2400) -> None:
    cmd = [COLAB_BIN, "exec", "-s", session, "-f", runner_script, "--timeout", str(timeout_sec)]
    log_trace(f"[colab-tts] $ {' '.join(cmd)} (watching for {len(expected_shas)} .sha markers)")
    proc = subprocess.Popen(cmd, env=colab_env(proxy), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t0 = time.monotonic()
    last_ls = t0
    while proc.poll() is None:
        now = time.monotonic()
        if now - t0 > timeout_sec + 60:
            proc.kill()
            raise RuntimeError(f"COLAB_TTS[timeout] colab exec exceeded {timeout_sec}s")
        if now - t0 > 30 and now - last_ls >= 20:
            last_ls = now
            ls_out = run_colab(["ls"], proxy, check=False).stdout or ""
            if all(sha_name in ls_out for sha_name in expected_shas):
                log_trace("[colab-tts] Detected all .wav.sha markers on Colab via REST ls; terminating exec watcher and proceeding to download.")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
                return
        time.sleep(2)
    out, err = proc.communicate()
    if out:
        log_trace(out.strip())
    if err:
        log_trace(f"[stderr] {err.strip()}")
    ls_out = ""
    for _ in range(3):
        r_ls = run_colab(["ls"], proxy, check=False)
        if r_ls.returncode == 0:
            ls_out = r_ls.stdout or ""
            break
        time.sleep(2)
    if all(sha_name in ls_out for sha_name in expected_shas):
        return
    raise RuntimeError(f"COLAB_TTS[error] colab exec finished without all .sha markers (exit={proc.returncode}): {err}")


def execute_remote_batch(
    session: str,
    gpu: str,
    proxy: str,
    engine: str,
    batch_items: list[dict],
) -> None:
    if not batch_items:
        return
    ensure_session(session, gpu, proxy)

    uploaded_spks: dict[str, str] = {}
    remote_items = []
    for idx, item in enumerate(batch_items):
        local_spk = str(Path(strip_file_uri(item["spk_wav"])).resolve())
        if local_spk not in uploaded_spks:
            remote_spk = f"/content/spk_{len(uploaded_spks)}_{Path(local_spk).name}"
            uploaded_spks[local_spk] = remote_spk

        # Support optional emotional reference audio upload
        remote_emo = ""
        if item.get("emo_audio"):
            local_emo = str(Path(strip_file_uri(item["emo_audio"])).resolve())
            if local_emo not in uploaded_spks:
                remote_emo = f"/content/emo_{len(uploaded_spks)}_{Path(local_emo).name}"
                uploaded_spks[local_emo] = remote_emo
            else:
                remote_emo = uploaded_spks[local_emo]

        remote_out = item.get("remote_out") or f"/content/out_{idx}_{item['id']}.wav"
        remote_items.append(
            {
                "id": item["id"],
                "engine": engine,
                "spk_audio_prompt": uploaded_spks[local_spk],
                "prompt_text": item.get("prompt_text") or DEFAULT_PROMPT_TEXT,
                "text": item["text"],
                "output_path": remote_out,
                "_local_output": str(Path(item["output_wav"]).resolve()),
                "emo_audio": remote_emo,
                "emo_alpha": item.get("emo_alpha", 0.40),
                "emo_vector": item.get("emo_vector"),
                "emo_text": item.get("emo_text"),
                "emotion": item.get("emotion"),
                "instruct_text": item.get("instruct_text"),
                "temperature": item.get("temperature"),
                "top_p": item.get("top_p"),
                "speed_ratio": item.get("speed_ratio"),
                "prosody_weight": item.get("prosody_weight"),
            }
        )

    payload = {
        "engine": engine,
        "items": [
            {
                "id": r["id"],
                "engine": engine,
                "spk_audio_prompt": r["spk_audio_prompt"],
                "prompt_text": r["prompt_text"],
                "text": r["text"],
                "output_path": r["output_path"],
                "emo_audio": r.get("emo_audio", ""),
                "emo_alpha": r.get("emo_alpha", 0.40),
                "emo_vector": r.get("emo_vector"),
                "emo_text": r.get("emo_text"),
                "emotion": r.get("emotion"),
                "instruct_text": r.get("instruct_text"),
                "temperature": r.get("temperature"),
                "top_p": r.get("top_p"),
                "speed_ratio": r.get("speed_ratio"),
                "prosody_weight": r.get("prosody_weight"),
            }
            for r in remote_items
        ],
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(payload, tf, ensure_ascii=False, indent=2)
        temp_jobs_path = tf.name

    for attempt in range(1, 4):
        try:
            ensure_session(session, gpu, proxy)
            ls_before = ""
            for _ in range(3):
                r_ls = run_colab(["ls"], proxy, check=False)
                if r_ls.returncode == 0:
                    ls_before = r_ls.stdout or ""
                    break
                time.sleep(2)
            for local_spk, remote_spk in uploaded_spks.items():
                if Path(remote_spk).name not in ls_before:
                    for up_att in range(3):
                        r_up = run_colab(["upload", "-s", session, local_spk, remote_spk], proxy, check=False)
                        if r_up.returncode == 0:
                            break
                        time.sleep(2)
            all_sha_ready = all(
                (f"{Path(r['output_path']).name}.sha" in ls_before and f"{Path(r['output_path']).name}.mp3.parts" in ls_before)
                for r in remote_items
            )
            if not all_sha_ready:
                run_colab(["upload", "-s", session, temp_jobs_path, "/content/tts_jobs.json"], proxy)
                expected_shas = [f"{Path(r['output_path']).name}.sha" for r in remote_items]
                run_colab_exec_watching_sha(session, RUNNER_SCRIPT, expected_shas, proxy, timeout_sec=2400)
            else:
                log_trace("[colab-tts] All .wav.sha outputs already present on Colab; skipping colab exec and proceeding to download.")
            for r in remote_items:
                local_out = Path(r["_local_output"])
                if local_out.exists():
                    try:
                        validate_wav_file(local_out)
                        continue
                    except Exception:
                        local_out.unlink(missing_ok=True)
                local_out.parent.mkdir(parents=True, exist_ok=True)
                temp_dl = local_out.with_suffix(f".{os.getpid()}.tmp.wav")
                for dl_attempt in range(1, 4):
                    try:
                        download_wav_possibly_chunked(session, r["output_path"], temp_dl, proxy)
                        validate_wav_file(temp_dl)
                        temp_dl.replace(local_out)
                        log_trace(f"[colab-tts] Verified & saved WAV -> {local_out}")
                        break
                    except Exception as dl_exc:
                        temp_dl.unlink(missing_ok=True)
                        if dl_attempt >= 3:
                            raise
                        log_trace(f"[colab-tts] Download retry {dl_attempt}/3 for {r['output_path']} ({dl_exc})...")
                        time.sleep(3)
            break
        except Exception as exc:
            if attempt >= 3:
                os.unlink(temp_jobs_path) if os.path.exists(temp_jobs_path) else None
                raise
            log_trace(f"[colab-tts] Remote batch attempt {attempt}/3 failed ({exc}); retrying in 5s...")
            time.sleep(5)
    if os.path.exists(temp_jobs_path):
        os.unlink(temp_jobs_path)


def resolve_host(hosts: list[dict], category: str | None, default_voice: str, default_prompt: str) -> tuple[str, str, str]:
    if category:
        for h in hosts:
            if category in (h.get("categories") or []):
                return (
                    h.get("name", "host"),
                    h["voice"],
                    h.get("prompt_text") or default_prompt,
                )
        raise RuntimeError(f"No configured host for category '{category}'")
    if hosts:
        h = hosts[0]
        return (
            h.get("name", "lead"),
            h["voice"],
            h.get("prompt_text") or default_prompt,
        )
    return ("default", default_voice, default_prompt)


def maybe_run_cosyvoice3_comparison(session: str, gpu: str, proxy: str, default_voice: str, default_prompt: str) -> None:
    morning_dir = REPO_ROOT / ".task-work/agent-runs/2026-10-15/morning"
    if not morning_dir.exists():
        return
    cosy_mp3 = morning_dir / "cosyvoice3_bilingual_sample.mp3"
    vox_mp3 = morning_dir / "voxcpm2_bilingual_sample.mp3"
    report_file = morning_dir / "tts_comparison_report.json"
    if cosy_mp3.exists() and vox_mp3.exists() and report_file.exists():
        return

    sample_text = (
        "Hello 大家好，今天我们评测 Formlabs 最新推出的 Form Studio 1 光固化 3D 打印机，"
        "它放弃了 Raspberry Pi Compute Module，改用 Arm SoM 核心板，并免费开放了 Open Material Mode。"
    )
    try:
        log_trace("[colab-tts] Running VoxCPM2 vs CosyVoice 3.0 bilingual comparison on Colab L4...")
        vox_wav = morning_dir / "voxcpm2_bilingual_sample.wav"
        cosy_wav = morning_dir / "cosyvoice3_bilingual_sample.wav"

        t0 = time.time()
        execute_remote_batch(
            session,
            gpu,
            proxy,
            "voxcpm2",
            [{"id": "cmp_vox", "spk_wav": default_voice, "prompt_text": default_prompt, "text": sample_text, "output_wav": str(vox_wav)}],
        )
        vox_elapsed = round(time.time() - t0, 2)
        vox_dur = stitch_wavs_to_mp3([vox_wav], vox_mp3, silence_ms=0)

        t1 = time.time()
        execute_remote_batch(
            session,
            gpu,
            proxy,
            "cosyvoice3",
            [{"id": "cmp_cosy", "spk_wav": default_voice, "prompt_text": default_prompt, "text": sample_text, "output_wav": str(cosy_wav)}],
        )
        cosy_elapsed = round(time.time() - t1, 2)
        cosy_dur = stitch_wavs_to_mp3([cosy_wav], cosy_mp3, silence_ms=0)

        report_file.write_text(
            json.dumps(
                {
                    "sample_text": sample_text,
                    "voxcpm2": {
                        "mp3_path": str(vox_mp3),
                        "duration_sec": vox_dur,
                        "total_elapsed_sec": vox_elapsed,
                    },
                    "cosyvoice3": {
                        "mp3_path": str(cosy_mp3),
                        "duration_sec": cosy_dur,
                        "total_elapsed_sec": cosy_elapsed,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        log_trace(f"[colab-tts] Saved VoxCPM2 vs CosyVoice3 comparison -> {report_file}")
    except Exception as exc:
        log_trace(f"[colab-tts] CosyVoice3 comparison warning (non-blocking): {exc}")


def handle_cortex_request(req_path: Path, session: str, gpu: str, proxy: str) -> int:
    try:
        gem_skill = REAL_HOME / ".gemini/config/skills/colab-operator"
        if gem_skill.exists():
            shutil.copy2(Path(__file__).resolve(), gem_skill / "scripts/colab_tts_client.py")
            shutil.copy2(Path(RUNNER_SCRIPT).resolve(), gem_skill / "examples/cloud_tts_runner.py")
    except Exception:
        pass

    req = json.loads(req_path.read_text(encoding="utf-8"))
    job_id = req.get("job_id", "job")
    voice_kind = req.get("voice_kind", "reading_article")
    engine = select_engine(req.get("engine", "auto"), job_id=job_id, voice_kind=voice_kind)
    log_trace(f"[colab-tts] Starting handle_cortex_request job={job_id} kind={voice_kind} engine={engine}")
    fallback_voice = REPO_ROOT / "audio/vivian.wav"
    default_voice = req.get("default_voice") or (
        str(fallback_voice) if fallback_voice.exists() else "/Users/jinliang/workspace/hacker-s-news/audio/vivian.wav"
    )
    default_prompt = req.get("default_prompt_text") or DEFAULT_PROMPT_TEXT
    output_mp3 = Path(req["output_mp3"])
    output_meta = Path(req["output_meta"])
    seg_cache_dir = Path(req.get("segment_cache_dir") or output_mp3.parent / "segments")
    seg_cache_dir.mkdir(parents=True, exist_ok=True)

    if voice_kind == "radio_program":
        plan = json.loads(req["text"])
        segments = plan.get("segments") or []
        if len(segments) < 3 or len(segments) > 32:
            raise RuntimeError(f"Invalid radio_program segment count: {len(segments)}")
        hosts = req.get("hosts") or []
        ordered_wavs: list[Path] = []
        pending_batch: list[dict] = []

        for idx, seg in enumerate(segments):
            cat = seg.get("category")
            text = (seg.get("text") or "").strip()
            if not text:
                raise RuntimeError(f"Empty radio_program segment at index {idx}")
            host_name, host_voice, host_prompt = resolve_host(hosts, cat, default_voice, default_prompt)
            ref_bytes = Path(strip_file_uri(host_voice)).read_bytes()
            ref_hash = hashlib.sha256(ref_bytes).hexdigest()
            cache_key = hashlib.sha256(
                f"colab:{engine}\n{host_voice}\n{host_prompt}\n{ref_hash}\n{text}".encode("utf-8")
            ).hexdigest()
            seg_wav = seg_cache_dir / f"{cache_key}.wav"
            ordered_wavs.append(seg_wav)

            if seg_wav.exists():
                try:
                    validate_wav_file(seg_wav)
                    log_trace(f"[colab-tts] Segment {idx + 1}/{len(segments)} ({host_name}) hit local cache")
                    continue
                except Exception:
                    seg_wav.unlink(missing_ok=True)

            pending_batch.append(
                {
                    "id": f"seg_{idx:02d}",
                    "remote_out": f"/content/out_{idx}_seg_{idx:02d}.wav",
                    "spk_wav": host_voice,
                    "prompt_text": host_prompt,
                    "text": text,
                    "output_wav": str(seg_wav),
                }
            )

        if pending_batch:
            log_trace(f"[colab-tts] Synthesizing {len(pending_batch)}/{len(segments)} radio segments on Colab L4 ({engine})...")
            execute_remote_batch(session, gpu, proxy, engine, pending_batch)

        duration_sec = stitch_wavs_to_mp3(ordered_wavs, output_mp3, silence_ms=250)
    else:
        text = (req.get("text") or "").strip()
        if not text:
            raise RuntimeError("Empty text for TTS job")
        hosts = req.get("hosts") or []
        _, lead_voice, lead_prompt = resolve_host(hosts, None, default_voice, default_prompt)
        cache_key = hashlib.sha256(f"colab:{engine}\n{lead_voice}\n{lead_prompt}\n{text}".encode("utf-8")).hexdigest()
        article_wav = seg_cache_dir / f"{cache_key}.wav"
        need_synth = True
        if article_wav.exists():
            try:
                validate_wav_file(article_wav)
                need_synth = False
            except Exception:
                article_wav.unlink(missing_ok=True)
        if need_synth:
            execute_remote_batch(
                session,
                gpu,
                proxy,
                engine,
                [
                    {
                        "id": "article",
                        "spk_wav": lead_voice,
                        "prompt_text": lead_prompt,
                        "text": text,
                        "output_wav": str(article_wav),
                    }
                ],
            )
        duration_sec = stitch_wavs_to_mp3([article_wav], output_mp3, silence_ms=0)

    meta = {
        "job_id": job_id,
        "engine": engine,
        "provider": f"colab_{engine}",
        "duration_seconds": duration_sec,
        "sample_rate": 24000,
    }
    output_meta.parent.mkdir(parents=True, exist_ok=True)
    output_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log_trace(f"[colab-tts] Completed job={job_id} provider=colab_{engine} duration={duration_sec}s")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Colab L4 Multi-Model TTS Client (VoxCPM2 + CosyVoice3 + IndexTTS 2.5)")
    parser.add_argument("--session", default="freshloop-tts-l4", help="Colab session name")
    parser.add_argument("--gpu", default="L4", help="Colab GPU type (L4, A100, T4)")
    parser.add_argument("--proxy", default=DEFAULT_PROXY, help="Local HTTP/HTTPS proxy URL")
    parser.add_argument("--engine", default="auto", help="voxcpm2 | cosyvoice3 | indextts25 | auto")
    parser.add_argument("--voice-kind", default="reading_article", help="radio_program | reading_article | curated_weekly")
    parser.add_argument("--job-id", default="", help="Optional job ID")
    parser.add_argument("--spk-wav", help="Local reference speaker WAV file for single-item mode")
    parser.add_argument("--prompt-text", default=DEFAULT_PROMPT_TEXT, help="Reference audio transcript")
    parser.add_argument("--text", help="Text to synthesize for single-item mode")
    parser.add_argument("--output", help="Local output WAV or MP3 path for single-item mode")
    parser.add_argument("--manifest", help="Path to JSON manifest list of {id, spk_wav, prompt_text, text, output_wav}")
    parser.add_argument("--cortex-request", help="Path to Cortex voice job request JSON")
    parser.add_argument("--keep-session", action="store_true", help="Do not stop session after completion")

    # IndexTTS 2.5 emotional expression controls
    parser.add_argument("--emo-audio", help="Optional emotion reference audio for IndexTTS 2.5")
    parser.add_argument("--emo-alpha", type=float, default=0.40, help="Emotion strength/alpha weight for IndexTTS 2.5 (default: 0.40)")
    parser.add_argument("--emo-vector", help="Custom 8D emotion vector e.g. '[0,1,0,0,0,0,0,0]'")
    parser.add_argument("--emo-text", help="Emotion text description or prompt")
    parser.add_argument(
        "--emotion",
        choices=["happy", "angry", "sad", "fearful", "afraid", "surprised", "calm", "cold_laugh", "whisper", "disgusted", "melancholic"],
        help="Emotion preset for IndexTTS 2.5 & CosyVoice3 (angry, sad, happy, fearful, surprised, calm, cold_laugh, whisper)",
    )

    # Fun-CosyVoice3 & Qwen3-TTS / VoxCPM2 prosody & style controls
    parser.add_argument("--instruct-text", help="Instruction prompt for Fun-CosyVoice3 or Qwen3-TTS")
    parser.add_argument("--temperature", type=float, default=0.42, help="Sampling temperature (default: 0.42)")
    parser.add_argument("--top-p", type=float, default=0.85, help="Top-p sampling (default: 0.85)")
    parser.add_argument("--speed-ratio", type=float, default=1.0, help="Speech speed multiplier (default: 1.0)")
    parser.add_argument("--prosody-weight", type=float, default=1.0, help="Prosody/CFG scale weight")
    parser.add_argument("--auto-normalize", action="store_true", default=True, help="Auto-normalize Chinese polyphones and numbers")
    args = parser.parse_args()

    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    waiting_marker = QUEUE_DIR / f"{os.getpid()}.waiting"
    waiting_marker.write_text(str(time.time()), encoding="utf-8")

    lock_fd = open(LOCK_FILE, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        waiting_marker.unlink(missing_ok=True)

        if args.cortex_request:
            return handle_cortex_request(Path(args.cortex_request), args.session, args.gpu, args.proxy)

        engine = select_engine(args.engine, job_id=args.job_id, voice_kind=args.voice_kind)
        if args.manifest:
            items = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        elif args.spk_wav and args.text and args.output:
            synth_text = args.text
            if args.auto_normalize:
                try:
                    norm_script = Path(__file__).parent / "chinese_normalizer.py"
                    if norm_script.exists():
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("chinese_normalizer", str(norm_script))
                        c_norm = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(c_norm)
                        synth_text = c_norm.normalize_chinese_text_for_tts(synth_text)
                except Exception:
                    pass
            items = [
                {
                    "id": "single",
                    "spk_wav": args.spk_wav,
                    "prompt_text": args.prompt_text,
                    "text": synth_text,
                    "output_wav": args.output,
                    "emo_audio": args.emo_audio,
                    "emo_alpha": args.emo_alpha,
                    "emo_vector": args.emo_vector,
                    "emo_text": args.emo_text,
                    "emotion": args.emotion,
                    "instruct_text": args.instruct_text,
                    "temperature": args.temperature,
                    "top_p": args.top_p,
                    "speed_ratio": args.speed_ratio,
                    "prosody_weight": args.prosody_weight,
                }
            ]
        else:
            parser.error("Provide --cortex-request, --manifest, or (--spk-wav, --text, --output)")

        execute_remote_batch(args.session, args.gpu, args.proxy, engine, items)
        return 0
    finally:
        waiting_marker.unlink(missing_ok=True)
        if not args.keep_session:
            if has_waiting_peers():
                log_trace(
                    f"[colab-tts] Another TTS job is waiting in queue; keeping session '{args.session}' warm for handoff."
                )
            else:
                log_trace(
                    f"[colab-tts] Queue drained; stopping session '{args.session}' immediately to save Compute Units..."
                )
                run_colab(["stop", "-s", args.session], args.proxy, check=False)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            lock_fd.close()


if __name__ == "__main__":
    raise SystemExit(main())
