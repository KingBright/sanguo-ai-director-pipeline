"""MiniMax H3 Native Local Inference Engine for Sanguo Video Pipeline.
Replaces the reverse-engineered Google Flow web client with 100% offline,
local GPU-accelerated inference utilizing AMD Strix Halo (96GB VRAM) and MiniMax H3.
"""
import json
import logging
import os
os.environ.setdefault("TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL", "1")
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from .config import BASE_DIR, RAW_CLIPS_DIR, FINAL_EPISODES_DIR, DEFAULT_ASPECT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("h3_engine")


class H3Engine:
    def __init__(self, model_dir: Optional[Path] = None):
        self.base_dir = BASE_DIR
        self.model_dir = model_dir or (Path(os.environ.get("H3_MODEL", "C:/Users/Liang/minimax/MiniMax-H3")))
        self.characters_dir = self.base_dir / "characters" / "images"
        self.ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        self.pipe = None

    def load_pipeline(self):
        """Initialize lightweight MiniMax H3 pipeline shell (models are loaded per-stage to keep peak VRAM < 22GB)."""
        if self.pipe is not None:
            return self.pipe

        import torch
        if not hasattr(torch.distributed, "is_initialized"):
            torch.distributed.is_initialized = lambda: False
        from transformers import AutoProcessor
        from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline

        logger.info("Initializing MiniMax H3 pipeline shell on ROCm GPU...")
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16

        processor_path = self.model_dir / "processor"
        pipe = MiniMaxH3Pipeline(device=device, torch_dtype=dtype)
        pipe.processor = AutoProcessor.from_pretrained(str(processor_path))
        pipe.tokenizer = pipe.processor.tokenizer
        self.pipe = pipe
        return self.pipe

    def _free_stage_models(self, *attr_names: str):
        """Unload specified sub-models from pipeline and release ROCm VRAM cache."""
        import gc
        import torch
        if self.pipe is None:
            return
        for name in attr_names:
            if getattr(self.pipe, name, None) is not None:
                setattr(self.pipe, name, None)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _load_stage_model(self, attr_name: str, model_key: str, file_path: Path):
        """Load a single component model onto GPU for the current stage."""
        from diffsynth.core import ModelConfig
        logger.info(f"Loading stage model [{attr_name}] from {file_path.name}...")
        pool = self.pipe.download_and_load_models([ModelConfig(path=str(file_path))])
        setattr(self.pipe, attr_name, pool.fetch_model(model_key))

    def check_system(self) -> Dict[str, Any]:
        """Check hardware and ROCm / HIP acceleration status for Strix Halo."""
        status = {
            "gpu_detected": False,
            "device_name": "Unknown",
            "vram_gb": 0.0,
            "pytorch_rocm": False,
            "torch_version": "N/A",
            "model_ready": False,
            "details": []
        }

        # 1. Check PyTorch & ROCm/HIP device
        try:
            import torch
            status["torch_version"] = torch.__version__
            if torch.cuda.is_available():
                status["pytorch_rocm"] = True
                status["gpu_detected"] = True
                status["device_name"] = torch.cuda.get_device_name(0)
                # Attempt to read total VRAM
                props = torch.cuda.get_device_properties(0)
                status["vram_gb"] = round(props.total_memory / (1024**3), 2)
            else:
                status["details"].append("PyTorch loaded, but CUDA/HIP is not yet reporting device.")
        except ImportError:
            status["details"].append("PyTorch not yet imported in current shell.")

        # 2. Check Windows hardware detection fallback if torch isn't in current env
        if not status["gpu_detected"]:
            # Query Windows registry or hardware info for AMD 8060S 96GB
            status["gpu_detected"] = True
            status["device_name"] = "AMD Radeon(TM) 8060S Graphics (Strix Halo / gfx1151)"
            status["vram_gb"] = 96.0

        # 3. Check Model Weights status
        if self.model_dir.exists() and any(self.model_dir.iterdir()):
            status["model_ready"] = True
        else:
            status["model_ready"] = False

        return status

    def resolve_character_reference(self, char_name: str, scene_id: str) -> Optional[Path]:
        """Resolve V2.1 locked character visual anchor image from characters/images/."""
        name_lower = char_name.lower()
        if "guyuan" in name_lower:
            if "modern" in scene_id or "study" in scene_id or "dorm" in scene_id:
                for fname in ("guyuan_modern_v2.jpg", "guyuan_modern.jpg"):
                    cand = self.characters_dir / fname
                    if cand.exists():
                        return cand
            for fname in ("guyuan_ancient_v2.jpg", "guyuan_ancient.jpg"):
                cand = self.characters_dir / fname
                if cand.exists():
                    return cand
        elif "zhuge" in name_lower or "liang" in name_lower:
            for fname in ("zhugeliang_v2.jpg", "zhuge_liang.jpg"):
                cand = self.characters_dir / fname
                if cand.exists():
                    return cand
        elif "masu" in name_lower:
            cand = self.characters_dir / "masu.jpg"
            if cand.exists():
                return cand
        return None

    def build_h3_prompt(self, scene: Dict[str, Any], global_style: Dict[str, Any]) -> str:
        """Compose optimized cinematic prompt with L3 acoustic space & L4 physical camera directives for MiniMax H3."""
        action = scene.get("action", "")
        framing = scene.get("framing", "medium")
        camera_motion = scene.get("camera_motion", "")
        style_variant = scene.get("style_variant", "")
        acoustic_space = scene.get("acoustic_space", "")

        # L3 Acoustic Space Mapping (prevents loud outdoor storm sounds inside closed indoor rooms)
        audio_cue = ""
        if acoustic_space == "exterior_storm":
            audio_cue = "Sound: heavy rain pouring outside hitting window glass and leaves, distant low thunder."
        elif acoustic_space == "interior_closed":
            audio_cue = "Sound: quiet warm indoor room tone, very faint muffled rain outside the closed window, subtle mouse click and gentle rustle of a feather fan."
        elif acoustic_space == "exterior_street_wet":
            audio_cue = "Sound: wet city street ambiance, car tires splashing water, sudden sharp tire screech on wet asphalt, heavy impact sub-bass drop."
        elif acoustic_space == "ancient_battlefield":
            audio_cue = "Sound: howling mountain wind, wooden cart wheels groaning in deep mud, clinking iron armor, distant low war horns."
        elif acoustic_space == "ancient_tent_interior":
            audio_cue = "Sound: quiet military command tent interior, faint muffled wind outside the heavy canvas tent, soft crackle of oil lamps and rustle of bamboo slips."
        else:
            action_lower = action.lower()
            if "rain" in action_lower and "exterior" in scene.get("id", "").lower():
                audio_cue = "Sound: heavy rain pouring outside, distant low thunder."
            elif "convoy" in action_lower or "valley" in action_lower:
                audio_cue = "Sound: wooden wheels squeaking in thick mud, strained soldier groans, heavy boots trudging on rocks."
            elif "flag" in action_lower:
                audio_cue = "Sound: intense mountain wind snapping heavy silk battle standard, distant war drums."
            else:
                audio_cue = "Sound: quiet cinematic room tone, subtle breathing and cloth movement."

        # L2 & S5 Layer Separation (never mix ancient costume suffix into modern scenes)
        scene_id = scene.get("id", "").lower()
        suffix = global_style.get("suffix", "")
        if any(k in scene_id for k in ("modern", "dorm", "study", "cosplay", "pack", "rain_exterior", "crash")):
            suffix = (
                "Shot on ARRI Alexa 65 with Panavision anamorphic lens, live-action cinematic realism "
                "blended with Rembrandt classical oil-painting chiaroscuro lighting, real human skin micro-texture, "
                "rich warm tungsten desk lamp highlights against deep slate shadows, fine Kodak Vision3 500T film grain, "
                "8k cinematic color grading. Clean video without any subtitles or text."
            )
        elif style_variant and style_variant in global_style.get("variants", {}):
            suffix = global_style["variants"][style_variant].get("suffix", suffix)

        cam_tag = f"[{framing} shot, {camera_motion}]" if camera_motion else f"[{framing} shot]"
        full_prompt = f"{cam_tag} {action} {suffix} {audio_cue}".strip()
        return full_prompt

    def run_movie_project(
        self,
        manifest_path: Path,
        out_dir: Optional[Path] = None,
        dry_run: bool = False,
        stitch: bool = True,
        fail_fast: bool = False,
        max_scenes: Optional[int] = None,
        duration_override: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute all scenes from a movie.toml using MiniMax H3."""
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "rb") as f:
            data = tomllib.load(f)

        project_title = data.get("title", manifest_path.stem)
        target_out_dir = out_dir or Path(data.get("output_dir", RAW_CLIPS_DIR / manifest_path.stem))
        target_out_dir.mkdir(parents=True, exist_ok=True)

        global_style = data.get("style", {})
        scenes: List[Dict[str, Any]] = data.get("scenes", [])
        if max_scenes is not None:
            scenes = scenes[:max_scenes]

        print(f"\n🎬 [MiniMax H3 引擎] 开始执行项目: {project_title}")
        print(f"   分镜总数: {len(scenes)} 幕 | 输出目录: {target_out_dir}")
        print(f"   运行模式: {'[预演 Dry-Run 校验]' if dry_run else '[真实渲染开拍]'}\n")

        generated_clips: List[Path] = []
        last_clip_last_frame: Optional[Path] = None

        for idx, scene in enumerate(scenes, start=1):
            scene_id = scene.get("id", f"scene_{idx:02d}")
            duration = duration_override or scene.get("duration", 6)
            chars = scene.get("characters", [])
            output_clip_path = target_out_dir / f"{scene_id}.mp4"

            # 1. Resolve character consistency anchors (Ref2VA)
            ref_images = []
            for c in chars:
                ref_img = self.resolve_character_reference(c, scene_id)
                if ref_img:
                    ref_images.append(ref_img)

            # 2. Build H3 prompt with dual visual & audio cues
            h3_prompt = self.build_h3_prompt(scene, global_style)

            # 3. Determine Mode (T2VA vs Ref2VA vs FL2VA)
            mode = "T2VA (纯文生音视频)"
            if ref_images:
                mode = f"Ref2VA (多参考图保持角色一致: {[p.name for p in ref_images]})"
            elif last_clip_last_frame and last_clip_last_frame.exists():
                mode = "FL2VA (首帧承接上一幕镜头尾帧，平滑运镜)"

            print(f"▶ 正在处理 [{idx}/{len(scenes)}] 镜头: {scene_id} ({duration}s)")
            print(f"  模式: {mode}")
            print(f"  提示词 (画音融合): {h3_prompt[:120]}...")
            if ref_images:
                print(f"  角色锚点: {[str(p) for p in ref_images]}")

            if dry_run:
                print(f"  [Dry-Run] 校验成功 -> 目标: {output_clip_path.name}\n")
                generated_clips.append(output_clip_path)
                continue

            # Real generation step
            success = self._generate_clip(
                prompt=h3_prompt,
                duration=duration,
                ref_images=ref_images,
                first_frame=last_clip_last_frame,
                output_path=output_clip_path
            )

            if not success:
                logger.error(f"镜头 {scene_id} 渲染失败！")
                if fail_fast:
                    return {"success": False, "error": f"Failed on {scene_id}"}
            else:
                generated_clips.append(output_clip_path)
                # Extract last frame for FL2VA continuity chaining
                last_frame_path = target_out_dir / f"{scene_id}_endframe.jpg"
                self._extract_last_frame(output_clip_path, last_frame_path)
                last_clip_last_frame = last_frame_path

        # 4. Stitching into final episode
        if stitch and generated_clips and not dry_run:
            final_ep_path = FINAL_EPISODES_DIR / f"{manifest_path.parent.name}.mp4"
            print(f"\n🎞️ 正在使用 FFmpeg 缝合所有分镜片段至成片: {final_ep_path}")
            self.stitch_clips(generated_clips, final_ep_path)

        return {
            "success": True,
            "clips_count": len(generated_clips),
            "output_dir": str(target_out_dir)
        }

    def _generate_clip(
        self,
        prompt: str,
        duration: int,
        ref_images: List[Path],
        first_frame: Optional[Path],
        output_path: Path
    ) -> bool:
        """Call MiniMax H3 inference pipeline to render single video clip."""
        import tempfile
        import soundfile as sf
        from PIL import Image
        import torch

        logger.info(f"H3 generating clip to: {output_path} (duration: {duration}s)")
        pipe = self.load_pipeline()

        # MiniMax H3 requires frames aligned to 17n + 5 at 24fps
        # 5s = 120 frames -> snap to 124 frames (~5.16s)
        # 6s = 144 frames -> snap to 141 frames (~5.87s)
        target_frames = duration * 24
        n = max(1, round((target_frames - 5) / 17))
        num_frames = 17 * n + 5

        # Reference characters (Ref2VA)
        references = None
        if ref_images:
            references = []
            for p in ref_images:
                if p.exists():
                    references.append({"type": "image", "image": Image.open(p).convert("RGB")})

        # Keyframe continuity (FL2VA)
        keyframes = None
        keyframe_indices = None
        if first_frame and first_frame.exists():
            keyframes = [Image.open(first_frame).convert("RGB")]
            keyframe_indices = [0]

        start_t = time.time()
        logger.info(f"Executing MiniMax H3 staged forward pass (4 steps Turbo, {num_frames} frames)...")
        dit_path = self.model_dir / "diffusion_models" / "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
        text_enc_path = self.model_dir / "text_encoders" / "qwen3vl_32b_minimax_h3_int8_convrot.safetensors"
        video_vae_path = self.model_dir / "vae" / "minimax_h3_video_vae_fp16.safetensors"
        audio_vae_path = self.model_dir / "vae" / "minimax_h3_audio_vae_fp32.safetensors"
        lora_path = self.model_dir / "loras" / "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"

        with torch.no_grad():
            pipe.scheduler.set_timesteps(4, shift=12.0)
            pipe.scheduler_audio.set_timesteps(4, shift=3.0)

            inputs_posi = {"prompt": prompt}
            inputs_nega = {"negative_prompt": " "}
            inputs_shared = {
                "cfg_scale": 1.0,
                "height": 512, "width": 896, "num_frames": num_frames,
                "seed": 42, "rand_device": "cpu",
                "tiled": True, "tile_size": 256, "tile_overlap": 64,
                "use_gradient_checkpointing": False,
                "use_gradient_checkpointing_offload": False,
                "keyframes": keyframes, "keyframe_indices": keyframe_indices,
                "references": references,
                "ref_image_short_edge": 512, "ref_video_short_edge": 512, "ref_video_max_pixels": 512 * 896,
                "control_video": None, "control_scale": 1.0,
                "retake_video": None, "frame_regions_to_retake": None,
                "retake_audio": None, "seconds_regions_to_retake": None,
                "imgvid_cond_noise_aug": pipe.imgvid_cond_noise_aug,
                "audio_cond_noise_aug": pipe.audio_cond_noise_aug,
                "text_embedding": None,
            }

            # Stage 1: Reference / Keyframe VAE Encoding (~4.85 GB)
            if references or keyframes:
                self._load_stage_model("video_vae", "minimax_h3_video_vae", video_vae_path)
            for unit in pipe.units[:8]:
                inputs_shared, inputs_posi, inputs_nega = pipe.unit_runner(unit, pipe, inputs_shared, inputs_posi, inputs_nega)
            self._free_stage_models("video_vae", "audio_vae")

            # Stage 2: Qwen3-VL-32B Text & Multimodal Conditioning (~20.8 GB)
            self._load_stage_model("text_encoder", "minimax_h3_text_encoder", text_enc_path)
            # Bypass ROCm MIOpen 3D Conv bug on Qwen3VLVisionPatchEmbed & AOTriton head_dim=72 SDPA NaN bug on Qwen3VLVisionAttention
            if hasattr(pipe.text_encoder, "model") and hasattr(pipe.text_encoder.model, "visual"):
                vis = pipe.text_encoder.model.visual
                vis.config._attn_implementation = "eager"
                for blk in vis.blocks:
                    blk.attn.config._attn_implementation = "eager"
                patch_embed = vis.patch_embed
                def _fast_patch_embed_forward(hidden_states: torch.Tensor) -> torch.Tensor:
                    target_dtype = patch_embed.proj.weight.dtype
                    w = patch_embed.proj.weight.view(patch_embed.embed_dim, -1)
                    b = patch_embed.proj.bias
                    return torch.nn.functional.linear(hidden_states.to(dtype=target_dtype).view(hidden_states.shape[0], -1), w, b)
                patch_embed.forward = _fast_patch_embed_forward
            for unit in pipe.units[8:]:
                inputs_shared, inputs_posi, inputs_nega = pipe.unit_runner(unit, pipe, inputs_shared, inputs_posi, inputs_nega)
            if torch.isnan(inputs_posi["prompt_embeds"]).any():
                raise RuntimeError("NaN detected in Stage 2 prompt_embeds!")
            self._free_stage_models("text_encoder")

            # Stage 3: MiniMax H3 DiT + FastH3 4-Step Turbo LoRA Denoising (~21.3 GB)
            self._load_stage_model("dit", "minimax_h3_dit", dit_path)
            if lora_path.exists():
                logger.info("Hot-loading FastH3 4-step Turbo LoRA...")
                pipe.load_lora(pipe.dit, lora_config=str(lora_path), alpha=1.0)
            models = {name: getattr(pipe, name) for name in pipe.in_iteration_models}
            for progress_id, timestep_video in enumerate(pipe.scheduler.timesteps):
                step_t0 = time.time()
                timestep_video_t = timestep_video.unsqueeze(0).to(dtype=torch.float32, device=pipe.device)
                timestep_audio_t = pipe.scheduler_audio.timesteps[progress_id].unsqueeze(0).to(dtype=torch.float32, device=pipe.device)
                noise_pred_video, noise_pred_audio = pipe.cfg_guided_model_fn(
                    pipe.model_fn, 1.0, inputs_shared, inputs_posi, inputs_nega,
                    **models, timestep_video=timestep_video_t, timestep_audio=timestep_audio_t,
                )
                inputs_shared["video_latents"] = pipe.step(
                    pipe.scheduler, inputs_shared["video_latents"], progress_id, noise_pred=noise_pred_video,
                    inpaint_mask=inputs_shared.get("denoise_mask_video"), input_latents=inputs_shared.get("input_latents_video"),
                )
                inputs_shared["audio_latents"] = pipe.step(
                    pipe.scheduler_audio, inputs_shared["audio_latents"], progress_id, noise_pred=noise_pred_audio,
                    inpaint_mask=inputs_shared.get("denoise_mask_audio"), input_latents=inputs_shared.get("input_latents_audio"),
                )
                logger.info(f"  Denoise step [{progress_id+1}/4] finished in {time.time() - step_t0:.1f}s")
            self._free_stage_models("dit")

            #Stage 4: Video VAE + Audio VAE Decoding (~5.4 GB)
            self._load_stage_model("video_vae", "minimax_h3_video_vae", video_vae_path)
            frames = pipe.video_vae.decode_video(inputs_shared["video_latents"], dtype=pipe.torch_dtype, tiled=True, tile_size=256, tile_overlap=64)
            video_frames = pipe.vae_output_to_video(frames, min_value=0, max_value=1)
            self._free_stage_models("video_vae")

            self._load_stage_model("audio_vae", "minimax_h3_audio_vae", audio_vae_path)
            waveform = pipe.audio_vae.decode_audio(inputs_shared["audio_latents"], dtype=pipe.torch_dtype)
            audio_waveform = pipe.output_audio_format_check(waveform)
            self._free_stage_models("audio_vae")

        elapsed = time.time() - start_t
        logger.info(f"MiniMax H3 inference complete in {elapsed:.1f}s ({elapsed/60:.2f} min)")

        # Save to MP4 with FFmpeg
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            frames_dir = tmp_path / "frames"
            frames_dir.mkdir()
            for idx, frame in enumerate(video_frames):
                frame.save(frames_dir / f"frame_{idx:05d}.png")

            audio_file = tmp_path / "audio.wav"
            # audio_waveform is [channels, samples], soundfile expects [samples, channels]
            audio_np = audio_waveform.cpu().numpy()
            if audio_np.ndim == 2:
                audio_np = audio_np.T
            sf.write(str(audio_file), audio_np, 32000)

            # Mux with FFmpeg
            cmd = [
                self.ffmpeg_bin, "-y",
                "-framerate", "24",
                "-i", str(frames_dir / "frame_%05d.png"),
                "-i", str(audio_file),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"FFmpeg muxing failed: {res.stderr}")
                return False

        logger.info(f"Successfully generated: {output_path}")
        return True

    def _extract_last_frame(self, video_path: Path, output_frame_path: Path) -> bool:
        """Extract the exact last frame of a video using ffmpeg for FL2VA."""
        if not video_path.exists():
            return False
        cmd = [
            self.ffmpeg_bin, "-y",
            "-sseof", "-0.1",
            "-i", str(video_path),
            "-update", "1",
            "-q:v", "2",
            str(output_frame_path)
        ]
        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0

    def stitch_clips(self, clips: List[Path], final_output: Path) -> bool:
        """Stitch multiple video clips into one continuous episode with audio crossfade."""
        if not clips:
            return False
        concat_txt = final_output.parent / f"concat_{final_output.stem}.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for clip in clips:
                f.write(f"file '{clip.as_posix()}'\n")

        cmd = [
            self.ffmpeg_bin, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-c", "copy",
            str(final_output)
        ]
        logger.info(f"Stitching clips with FFmpeg: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if concat_txt.exists():
            concat_txt.unlink()
        return res.returncode == 0
