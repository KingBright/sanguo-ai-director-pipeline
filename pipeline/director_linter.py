"""L1-L5 Industrial Screenwriter & Director Linter and Acoustic Mastering Engine.

Implements the standardized methodology from `docs/industrial_ai_video_sop.md`:
  - L1 Gatekeeper:
      * Chekhov's Gun Silent Prop Protection (blocks foreshadowed props like spare glasses
        from being explicitly spoiled in early setup dialogue).
      * Show-Don't-Tell Optical/Medical Term Guard (forbids modern optometry terms like
        '远视眼/老花眼/凸透镜/度数' in dialogue across ALL phases; mandates visual action).
      * Psychological 4-Phase Arc Validation (enforces mandatory `arc_phase` declaration
        and monotonic progression across the episode).
      * Mandatory Dialogue / Voiceover check (`line`).
  - L2 Gatekeeper:
      * Mandatory Visual Reference Anchor (`ref_image`) binding and file existence check
        for every scene containing characters.
      * Bidirectional Era Isolation check (prevents ancient armor terms in modern scenes
        and modern electronics/vehicles in ancient scenes).
  - L3 Gatekeeper:
      * Mandatory `acoustic_space` validation against `fact_sheet.toml`.
      * Spatial Blocking Sequence Check (enforces Exterior Establishing shot before
        cutting to any closed interior space `interior_closed` / `ancient_tent_interior`).
      * 3D Room Layout Topology & Continuity Check (`[spatial_rooms]` / `room_id`):
        verifies that multi-shot interior/exterior sequences in the same room bind the
        matching spatial anchor keyframes and do not flip left/right 180-degree camera axis.
      * Acoustic Space Physical Consistency (maps `acoustic_space` to FFmpeg low-pass
        filters so indoor/tent scenes muffle outdoor rain/wind realistically).
  - L4 Gatekeeper:
      * Mandatory `camera_motion` with explicit physical lens focal length (e.g. `35mm`, `50mm`).
      * Dialogue Referent Visual Evidence Alignment (`dialogue_visual_evidence_rules`):
        when dialogue mentions a specific medium/event (e.g. '漫展', '拨云见日', '目中寒光'),
        verifies that `action` contains the corresponding physical visual evidence (e.g.
        convention cosplay photo album on monitor, convex lens magnification, cold light glint).
      * Bilingual De-Literary Shootability Check (blocks unshootable literary vagueness and
        abstract internal states in both Chinese and English).
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
import re
import subprocess
import shutil

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from .config import BASE_DIR


@dataclass
class LintIssue:
    level: str          # "ERROR" or "WARNING"
    layer: str          # "L1", "L2", "L3", "L4", "L5"
    scene_id: str
    message: str
    suggestion: str


@dataclass
class LintReport:
    manifest_path: Path
    passed: bool
    issues: List[LintIssue] = field(default_factory=list)
    scene_count: int = 0

    def format_report(self) -> str:
        lines = [
            "=" * 78,
            f"🎬 [L1-L5 工业化编剧导演质检报告] 分镜工程: {self.manifest_path.parent.name}/{self.manifest_path.name}",
            "=" * 78,
            f"总镜头数: {self.scene_count} 幕 | 质检结果: {'✅ 通过 (PASS)' if self.passed else '❌ 阻断 (BLOCKED - 存在违反导演铁律项)'}",
        ]
        if not self.issues:
            lines.append("✨ 全部镜头已 100% 通过 L1(叙事弧光/静默伏笔/禁直白说破)、L2(事实锁/时代隔离)、L3(空间建置/三维房间拓扑/声学滤波)、L4(物理焦段/台词视觉证据对齐/去文学化) 审查！")
        else:
            lines.append("\n发现以下需要修正的工程问题:")
            for idx, iss in enumerate(self.issues, 1):
                icon = "🛑" if iss.level == "ERROR" else "⚠️"
                lines.append(f"  {idx}. {icon} [{iss.layer}][{iss.level}] 镜头 `{iss.scene_id}`: {iss.message}")
                lines.append(f"     💡 导演修正建议: {iss.suggestion}")
        lines.append("=" * 78)
        return "\n".join(lines)


class DirectorLinter:
    """Enforces L1-L5 Industrial Screenwriter & Director SOP rules on movie.toml manifests."""

    def __init__(self, fact_sheet_path: Optional[Path] = None):
        self.fact_sheet_path = fact_sheet_path or (BASE_DIR / "fact_sheet.toml")
        self.fact_sheet = self._load_toml(self.fact_sheet_path)
        self.rules = self.fact_sheet.get("director_rules", {})
        self.acoustic_spaces = self.fact_sheet.get("acoustic_spaces", {})
        self.spatial_rooms = self.fact_sheet.get("spatial_rooms", {})
        self.ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    @staticmethod
    def _load_toml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "rb") as f:
            return tomllib.load(f)

    def lint_manifest(self, manifest_path: Path) -> LintReport:
        data = self._load_toml(manifest_path)
        scenes: List[Dict[str, Any]] = data.get("scenes", [])
        issues: List[LintIssue] = []

        banned_dialogue_kw = self.rules.get("silent_foreshadow_keywords_banned_in_dialogue", [])
        always_banned_dialogue = self.rules.get("always_banned_explicit_medical_terms_in_dialogue", [])
        banned_action_kw = self.rules.get("banned_literary_vagueness_in_action", [])
        evidence_rules: List[Dict[str, Any]] = self.rules.get("dialogue_visual_evidence_rules", [])
        valid_arc_phases: List[str] = self.rules.get("psychological_arc_phases", [
            "phase_1_daily_empathy",
            "phase_2_sudden_accident",
            "phase_3_shock_and_denial",
            "phase_4_evidence_awakening",
        ])
        phase_rank = {p: i for i, p in enumerate(valid_arc_phases)}

        seen_exterior_establishing = False
        last_phase_idx = -1

        for idx, sc in enumerate(scenes):
            sc_id = sc.get("id", f"scene_{idx+1:02d}")
            era = sc.get("era", "modern" if any(k in sc_id.lower() for k in ("modern", "dorm", "cosplay", "pack", "rain_exterior", "crash")) else "ancient")
            room_id = sc.get("room_id", "")
            action = sc.get("action", "")
            action_lower = action.lower()
            line = sc.get("line", "")
            arc_phase = sc.get("arc_phase", "")
            acoustic_space = sc.get("acoustic_space", "")
            camera_motion = sc.get("camera_motion", "")
            chars = sc.get("characters", [])
            ref_image = sc.get("ref_image", "")

            # --- L1 Check 1: Psychological Arc Phase Presence & Monotonic Progression ---
            if not arc_phase or arc_phase not in phase_rank:
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L1-人物心理四阶段律",
                    scene_id=sc_id,
                    message=f"未声明合法的 `arc_phase`（当前值: '{arc_phase}'）。",
                    suggestion=f"必须显式指定心理弧光阶段，可选值: {valid_arc_phases}"
                ))
            else:
                curr_phase_idx = phase_rank[arc_phase]
                if curr_phase_idx < last_phase_idx:
                    issues.append(LintIssue(
                        level="ERROR",
                        layer="L1-人物心理四阶段律",
                        scene_id=sc_id,
                        message=f"心理弧光阶段出现倒退（上一镜阶段索引 {last_phase_idx} -> 当前 `{arc_phase}`）。",
                        suggestion="人物心理弧光必须按 phase_1 -> phase_2 -> phase_3 -> phase_4 单调推进，不可逻辑倒退。"
                    ))
                last_phase_idx = max(last_phase_idx, curr_phase_idx)

            # --- L1 Check 2: Mandatory Script Line / Voiceover ---
            if not line.strip():
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L1-台词与叙事锁",
                    scene_id=sc_id,
                    message="镜头缺少核定台词或画外音 (`line`)。",
                    suggestion="在分镜配置中补充与 `script.md` 严格对齐的 `speaker` 与 `line`。"
                ))

            # --- L1 Check 3: Chekhov's Gun Silent Foreshadowing & Show-Don't-Tell Protection ---
            for kw in always_banned_dialogue:
                if kw in line:
                    issues.append(LintIssue(
                        level="ERROR",
                        layer="L1-细节体现律(禁直白说破)",
                        scene_id=sc_id,
                        message=f"台词中直白说出了现代验光/设定术语『{kw}』：\"{line}\"",
                        suggestion="远视镜解决丞相老花眼及敌军误认神器必须完全靠画面物理细节体现（如竹简拉远微眯、凸透镜放大墨字、寒光反射震慑敌哨），严禁在台词中直白点破！"
                    ))
            if arc_phase in ("phase_1_daily_empathy", "phase_2_sudden_accident", ""):
                for kw in banned_dialogue_kw:
                    if kw in line:
                        issues.append(LintIssue(
                            level="ERROR",
                            layer="L1-契诃夫之枪静默律",
                            scene_id=sc_id,
                            message=f"铺垫期台词中直接明牌剧透了静默伏笔关键词『{kw}』：\"{line}\"",
                            suggestion="备用眼镜/穿越机制在铺垫期属于视觉暗线（Show, Don't Tell），仅允许写在画面 action 中自然陈列，严禁在台词中直接说破！"
                        ))

            # --- L2 Check 1: Character Reference Anchor & Existence ---
            if chars:
                if not ref_image:
                    issues.append(LintIssue(
                        level="ERROR",
                        layer="L2-视觉资产事实锁",
                        scene_id=sc_id,
                        message=f"镜头包含角色 {chars}，但未显式绑定定妆母图 `ref_image`。",
                        suggestion="在 scene 中指定 `ref_image` 定妆/空间锚定母图，防止五官与空间漂移。"
                    ))
                elif not (BASE_DIR / ref_image).exists():
                    issues.append(LintIssue(
                        level="ERROR",
                        layer="L2-视觉资产事实锁",
                        scene_id=sc_id,
                        message=f"绑定的定妆母图文件不存在: `{ref_image}`。",
                        suggestion="请检查 `characters/images/` 目录下的定妆母图路径。"
                    ))

            # --- L2 Check 2: Bidirectional Era Isolation ---
            is_convention_cosplay = room_id == "anime_convention_hall" or "convention" in action_lower or "cosplayer" in action_lower
            if era == "modern" and not is_convention_cosplay and ("armor" in action_lower or "ancient chinese soldiers" in action_lower):
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L2-时代服化道隔离",
                    scene_id=sc_id,
                    message="现代非漫展场景画面描述中混入了古代盔甲/古装士卒词汇，会导致古今串戏。",
                    suggestion="使用 `era = \"modern\"` 与现代场景描述，将现代日常场景与古代战场服化道严格物理隔离。"
                ))
            elif era == "ancient" and any(w in action_lower for w in ("dormitory", "laptop", "computer monitor", "asphalt street", "sedan")):
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L2-时代服化道隔离",
                    scene_id=sc_id,
                    message="古代场景画面描述中混入了现代宿舍/电子屏幕/柏油路汽车词汇。",
                    suggestion="确保古代场景完全使用建兴六年历史环境与古装服化道描述。"
                ))

            # --- L3 Check 1: Mandatory Acoustic Space Validation ---
            if not acoustic_space or acoustic_space not in self.acoustic_spaces:
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L3-声画空间物理锁",
                    scene_id=sc_id,
                    message=f"未声明合法的声学空间 `acoustic_space`（当前值: '{acoustic_space}'）。",
                    suggestion=f"必须指定 `fact_sheet.toml` 中定义的声学空间: {list(self.acoustic_spaces.keys())}"
                ))

            # --- L3 Check 2: Exterior Establishing before Closed Interior ---
            if (
                acoustic_space in ("exterior_storm", "exterior_street_wet", "ancient_battlefield")
                or "establishing" in sc.get("framing", "").lower()
                or "exterior" in sc_id.lower()
            ):
                seen_exterior_establishing = True

            if acoustic_space in ("interior_closed", "ancient_tent_interior"):
                if not seen_exterior_establishing:
                    issues.append(LintIssue(
                        level="ERROR",
                        layer="L3-视听空间建置律",
                        scene_id=sc_id,
                        message=f"在未交代外部环境建置镜头的情况下，直接切入封闭内景 (`{acoustic_space}`)。",
                        suggestion="场次必须遵循『外景建置先行律 (Exterior Establishing -> Interior Cut)』，先用外景镜头交代风雨或军营环境，再切入室内/帐内。"
                    ))
                if "heavy rain pouring" in action_lower and "window" not in action_lower and "muffled" not in action_lower:
                    issues.append(LintIssue(
                        level="WARNING",
                        layer="L3-声画空间一致性",
                        scene_id=sc_id,
                        message="关窗室内镜头提示词中包含未加修饰的倾盆大雨描述，易诱发视频模型生成室内漏雨或过大雨声。",
                        suggestion="室内镜头提示词应强调温暖静谧内景，并将 `acoustic_space` 设为 `interior_closed` 以启用 FFmpeg 420Hz 低通滤波闷雨声。"
                    ))

            # --- L3 Check 3: 3D Room Layout Topology & Cross-Shot Axis Continuity ---
            if room_id:
                if room_id not in self.spatial_rooms:
                    issues.append(LintIssue(
                        level="ERROR",
                        layer="L3-三维空间拓扑锁",
                        scene_id=sc_id,
                        message=f"声明的 `room_id = \"{room_id}\"` 未在 `fact_sheet.toml` 的 `[spatial_rooms]` 中定义。",
                        suggestion=f"请在 `[spatial_rooms]` 中登记该房间的左/中/右三维坐标与配对首帧母图，可选值: {list(self.spatial_rooms.keys())}"
                    ))
                else:
                    room_cfg = self.spatial_rooms[room_id]
                    for bad_topo in room_cfg.get("banned_topology_contradictions", []):
                        if bad_topo.lower() in action_lower:
                            issues.append(LintIssue(
                                level="ERROR",
                                layer="L3-三维空间拓扑锁",
                                scene_id=sc_id,
                                message=f"镜头画面描述违反了房间 `{room_id}` 的固定三维空间拓扑（出现了越轴/方位颠倒词『{bad_topo}』）。",
                                suggestion=f"必须严格保持房间拓扑一致：左={room_cfg.get('camera_left')} | 中={room_cfg.get('center_foreground')} | 右={room_cfg.get('camera_right')}。"
                            ))
                    if acoustic_space == "exterior_storm" and room_cfg.get("exterior_anchor_image"):
                        expected_ext = room_cfg["exterior_anchor_image"]
                        if ref_image != expected_ext:
                            issues.append(LintIssue(
                                level="ERROR",
                                layer="L3-三维空间拓扑锁",
                                scene_id=sc_id,
                                message=f"外景透窗镜头未绑定该房间专用的外景透窗空间锚定图 `{expected_ext}`（当前: `{ref_image}`）。",
                                suggestion=f"将 `ref_image` 设为 `\"{expected_ext}\"`，确保从窗外看室内的桌面布局与内景镜头 100% 咬合。"
                            ))

            # --- L4 Check 1: Mandatory Physical Camera Lens & Motion Vector ---
            if not camera_motion.strip() or not re.search(r"\d+\s*mm\b", camera_motion.lower()):
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L4-物理摄影机参数锁",
                    scene_id=sc_id,
                    message=f"`camera_motion` 缺失或未包含明确物理镜头焦段（如 35mm/50mm/85mm）：'{camera_motion}'。",
                    suggestion="在 `camera_motion` 中明确指定物理焦段与运镜矢量，例如 `\"50mm anamorphic lens, subtle slow push-in\"`。"
                ))

            # --- L4 Check 2: Dialogue Referent -> Visual Evidence Alignment ---
            for rule in evidence_rules:
                trig = rule.get("dialogue_trigger", "")
                req_list = rule.get("required_any_in_action", [])
                if trig and trig in line and req_list:
                    if not any(req.lower() in action_lower for req in req_list):
                        issues.append(LintIssue(
                            level="ERROR",
                            layer="L4-台词视觉证据对齐律",
                            scene_id=sc_id,
                            message=f"台词提到了『{trig}』，但画面 `action` 中缺少对应的直接视觉证据（需包含以下任一特征词: {req_list}）。",
                            suggestion=rule.get("description", "确保台词所谈论的照片、器物或光学现象在画面中有直接对应的特写或屏幕画面。")
                        ))

            # --- L4 Check 3: Bilingual De-Literary Shootability Check ---
            for bad_kw in banned_action_kw:
                if bad_kw.lower() in action_lower:
                    issues.append(LintIssue(
                        level="ERROR",
                        layer="L4-去文学化可拍性",
                        scene_id=sc_id,
                        message=f"视频画面提示词包含不可拍的中/英文抽象词或心理描写『{bad_kw}』。",
                        suggestion="摄影机只能拍摄物理可见的动作与光影，请将其改写为具体的面部微表情、肢体动作、焦段景深与光影方向。"
                    ))

            # --- L5 Check 1: Voiceover Pacing & Polyphonic / Prosody Split Guard ---
            dur = float(sc.get("duration", 8))
            clean_chars = re.sub(r"[^\u4e00-\u9fff0-9A-Za-z]", "", line)
            max_chars = int(dur * 4.5)  # max ~4.5 chars/sec so TTS never needs >+12% speedup
            if len(clean_chars) > max_chars:
                issues.append(LintIssue(
                    level="WARNING",
                    layer="L5-配音韵律与语速锁",
                    scene_id=sc_id,
                    message=f"单镜头（{dur:.0f}秒）台词字数过多（{len(clean_chars)}字 > 建议上限 {max_chars}字），会导致 TTS 强行加速失真或断词错误。",
                    suggestion=f"精简台词至 {max_chars} 字以内，确保在正常语速（+0% ~ +12%）下自然从容念完。"
                ))
            if "替丞相" in line:
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L5-配音防拆词与多音字锁",
                    scene_id=sc_id,
                    message="台词包含『替丞相』，神经 TTS 分词器会将其误切分为『替城 / 相守住』（把“丞相”拆成“城、乡”两个字）！",
                    suggestion="请改为『为丞相』（如『能为丞相守住街亭』），确保“丞相 (chéng xiàng)”完整连读。"
                ))
            if "孔明行头" in line:
                issues.append(LintIssue(
                    level="ERROR",
                    layer="L5-配音防拆词与多音字锁",
                    scene_id=sc_id,
                    message="台词包含多音字易错词『孔明行头』，TTS 默认会误读为『háng tóu』而非『xíng tou』。",
                    suggestion="请改为『孔明行装』或通过 `format_tts_text()` 映射，确保发音 100% 准确。"
                ))

        has_errors = any(i.level == "ERROR" for i in issues)
        return LintReport(
            manifest_path=manifest_path,
            passed=not has_errors,
            issues=issues,
            scene_count=len(scenes),
        )

    def format_tts_text(self, line: str) -> str:
        """Apply L5 phonetic & prosody overrides from `fact_sheet.toml` before sending text to TTS
        (e.g. mapping '长使英雄泪满襟' -> '出师未捷，身先死，常使英雄，泪满襟' so '长' is read as cháng and follows 4-3 poetic meter).
        """
        tts_text = line
        overrides: Dict[str, str] = self.rules.get("tts_pronunciation_overrides", {})
        for src, dst in overrides.items():
            if src in tts_text:
                if src == "长使英雄泪满襟" and "出师未捷" in tts_text:
                    tts_text = re.sub(r"出师未捷身先死[，,]\s*长使英雄泪满襟[…—。，]*", dst + "。", tts_text)
                else:
                    tts_text = tts_text.replace(src, dst)
        return tts_text

    def get_ffmpeg_bg_filter(self, acoustic_space: str) -> str:
        """Return physically accurate FFmpeg audio filter for the scene's acoustic space."""
        space_cfg = self.acoustic_spaces.get(acoustic_space, {})
        return space_cfg.get("ffmpeg_bg_filter", "volume=0.35")

    def master_scene_clip(
        self,
        raw_video_path: Path,
        output_video_path: Path,
        acoustic_space: str = "interior_closed",
        voiceover_path: Optional[Path] = None,
        ass_subtitle_path: Optional[Path] = None,
        target_duration: float = 8.0,
        vo_delay_ms: int = 200,
        use_native_audio: bool = False,
    ) -> bool:
        """L5 Acoustic Space & Subtitle Mastering:
        - When `use_native_audio=True` (on-screen lip-sync mode for Veo 3.1 / MiniMax H3), preserves
          the model's native lip-synced audio track `[0:a]` at full clarity and does NOT time-stretch
          video frames relative to audio (preventing any lip-sync drift), nor overwrite `[0:a]` with external TTS!
        - When `use_native_audio=False` (off-screen inner monologue / VO mode), smoothly stretches shorter clips
          to `target_duration` and mixes the continuous stereo rain/ambient bed with the voiceover track.
        """
        if not raw_video_path.exists():
            raise FileNotFoundError(f"Raw video clip not found: {raw_video_path}")
        if not use_native_audio and voiceover_path is not None and not voiceover_path.exists():
            raise FileNotFoundError(f"Voiceover audio file not found: {voiceover_path}")
        if ass_subtitle_path is not None and not ass_subtitle_path.exists():
            raise FileNotFoundError(f"ASS subtitle file not found: {ass_subtitle_path}")

        bg_filter = self.get_ffmpeg_bg_filter(acoustic_space)
        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        # Probe input video duration using ffmpeg stderr
        probe = subprocess.run(
            [self.ffmpeg_bin, "-i", str(raw_video_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        raw_dur = target_duration
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
        if m:
            raw_dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

        effective_dur = raw_dur if use_native_audio else target_duration

        v_filters = []
        if not use_native_audio and raw_dur > 0.5 and abs(raw_dur - target_duration) > 0.25:
            stretch = round(target_duration / raw_dur, 4)
            v_filters.append(f"setpts={stretch}*PTS")
            v_filters.append("minterpolate=fps=24:mi_mode=blend")
        else:
            v_filters.append("fps=24")
        v_filters.append("scale=1280:720:flags=lanczos")

        if ass_subtitle_path:
            safe_ass = ass_subtitle_path.as_posix().replace(":", "\\:")
            v_filters.append(f"ass='{safe_ass}'")
        v_chain = ",".join(v_filters)

        # Ensure a continuous, audible rain/ambient bed for storm/interior scenes even if raw I2V clip has near-silent audio
        rain_bed = Path("output/raw_clips/ep01_crossing/ep01_01_rain_exterior_v3_cloud.mp4")
        use_rain_bed = rain_bed.exists() and acoustic_space in ("exterior_storm", "interior_closed")

        if use_native_audio:
            filter_complex = (
                f"[0:v]{v_chain}[v];"
                f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.35[a]"
            )
            cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(raw_video_path),
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-t", f"{effective_dur:.2f}",
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                str(output_video_path),
            ]
        elif use_rain_bed and voiceover_path:
            bed_filter = "volume=0.80" if acoustic_space == "exterior_storm" else "lowpass=f=420,volume=0.35"
            filter_complex = (
                f"[0:v]{v_chain}[v];"
                f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bg_filter}[raw_a];"
                f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bed_filter}[bed_a];"
                f"[2:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay={vo_delay_ms}|{vo_delay_ms},apad=whole_dur={target_duration},volume=1.85[vo];"
                f"[raw_a][bed_a][vo]amix=inputs=3:duration=first:dropout_transition=2:normalize=0[a]"
            )
            cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(raw_video_path),
                "-i", str(rain_bed),
                "-i", str(voiceover_path),
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-t", str(target_duration),
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                str(output_video_path),
            ]
        elif voiceover_path:
            filter_complex = (
                f"[0:v]{v_chain}[v];"
                f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bg_filter}[bg];"
                f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay={vo_delay_ms}|{vo_delay_ms},apad=whole_dur={target_duration},volume=1.85[vo];"
                f"[bg][vo]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]"
            )
            cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(raw_video_path),
                "-i", str(voiceover_path),
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-t", str(target_duration),
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                str(output_video_path),
            ]
        else:
            filter_complex = (
                f"[0:v]{v_chain}[v];"
                f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={target_duration},{bg_filter}[a]"
            )
            cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(raw_video_path),
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-t", str(target_duration),
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
                str(output_video_path),
            ]

        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg mastering failed ({res.returncode}): {res.stderr[-600:]}")
        return True
