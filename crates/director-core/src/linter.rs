use std::collections::HashMap;
use std::path::{Path, PathBuf};

use regex::Regex;
use serde::{Deserialize, Serialize};

use crate::models::{FactSheet, MovieManifest, SceneSpec};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LintIssue {
    pub level: String, // "ERROR" or "WARNING"
    pub layer: String, // "L1", "L2", "L3", "L4", "L5"
    pub scene_id: String,
    pub message: String,
    pub suggestion: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LintReport {
    pub manifest_path: String,
    pub passed: bool,
    pub issues: Vec<LintIssue>,
    pub scene_count: usize,
    pub error_count: usize,
    pub warning_count: usize,
    pub formatted_text: String,
}

impl LintReport {
    pub fn build(manifest_label: &str, scenes_len: usize, issues: Vec<LintIssue>) -> Self {
        let error_count = issues.iter().filter(|i| i.level == "ERROR").count();
        let warning_count = issues.iter().filter(|i| i.level == "WARNING").count();
        let passed = error_count == 0;

        let mut lines = vec![
            "=".repeat(78),
            format!("🎬 [L1-L5 工业化编剧导演质检报告] 分镜工程: {}", manifest_label),
            "=".repeat(78),
            format!(
                "总镜头数: {} 幕 | 质检结果: {}",
                scenes_len,
                if passed {
                    "✅ 通过 (PASS)"
                } else {
                    "❌ 阻断 (BLOCKED - 存在违反导演铁律项)"
                }
            ),
        ];

        if issues.is_empty() {
            lines.push("✨ 全部镜头已 100% 通过 L1(叙事弧光/静默伏笔/禁直白说破)、L2(事实锁/时代隔离)、L3(空间建置/三维房间拓扑/声学滤波)、L4(物理焦段/台词视觉证据对齐/去文学化) 审查！".to_string());
        } else {
            lines.push("\n发现以下需要修正的工程问题:".to_string());
            for (idx, iss) in issues.iter().enumerate() {
                let icon = if iss.level == "ERROR" { "🛑" } else { "⚠️" };
                lines.push(format!(
                    "  {}. {} [{}][{}] 镜头 `{}`: {}",
                    idx + 1,
                    icon,
                    iss.layer,
                    iss.level,
                    iss.scene_id,
                    iss.message
                ));
                lines.push(format!("     💡 导演修正建议: {}", iss.suggestion));
            }
        }
        lines.push("=".repeat(78));

        Self {
            manifest_path: manifest_label.to_string(),
            passed,
            issues,
            scene_count: scenes_len,
            error_count,
            warning_count,
            formatted_text: lines.join("\n"),
        }
    }
}

pub struct DirectorLinter {
    pub base_dir: PathBuf,
    pub fact_sheet: FactSheet,
}

impl DirectorLinter {
    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        let base_dir = base_dir.into();
        let fact_sheet_path = base_dir.join("fact_sheet.toml");
        let fact_sheet = if fact_sheet_path.exists() {
            std::fs::read_to_string(&fact_sheet_path)
                .ok()
                .and_then(|s| toml::from_str::<FactSheet>(&s).ok())
                .unwrap_or_default()
        } else {
            FactSheet::default()
        };
        Self {
            base_dir,
            fact_sheet,
        }
    }

    pub fn lint_manifest_file(&self, manifest_path: &Path) -> anyhow::Result<LintReport> {
        let raw = std::fs::read_to_string(manifest_path)?;
        let manifest: MovieManifest = toml::from_str(&raw)?;
        let label = manifest_path
            .parent()
            .and_then(|p| p.file_name())
            .map(|n| format!("{}/{}", n.to_string_lossy(), manifest_path.file_name().unwrap_or_default().to_string_lossy()))
            .unwrap_or_else(|| manifest_path.to_string_lossy().to_string());
        Ok(self.lint_scenes(&label, &manifest.scenes))
    }

    pub fn lint_scenes(&self, manifest_label: &str, scenes: &[SceneSpec]) -> LintReport {
        let mut issues = Vec::new();
        let rules = &self.fact_sheet.director_rules;

        let valid_arc_phases = if rules.psychological_arc_phases.is_empty() {
            vec![
                "phase_1_daily_empathy".to_string(),
                "phase_2_sudden_accident".to_string(),
                "phase_3_shock_and_denial".to_string(),
                "phase_4_evidence_awakening".to_string(),
            ]
        } else {
            rules.psychological_arc_phases.clone()
        };

        let phase_rank: HashMap<&str, isize> = valid_arc_phases
            .iter()
            .enumerate()
            .map(|(i, p)| (p.as_str(), i as isize))
            .collect();

        let focal_re = Regex::new(r"\d+\s*mm\b").unwrap();
        let non_word_re = Regex::new(r"[^\u4e00-\u9fff0-9A-Za-z]").unwrap();

        let mut seen_exterior_establishing = false;
        let mut last_phase_idx: isize = -1;

        for (idx, sc) in scenes.iter().enumerate() {
            let sc_id = if sc.id.is_empty() {
                format!("scene_{:02}", idx + 1)
            } else {
                sc.id.clone()
            };
            let sc_id_lower = sc_id.to_lowercase();
            let era = if !sc.era.is_empty() {
                sc.era.as_str()
            } else if ["modern", "dorm", "cosplay", "pack", "rain_exterior", "crash"]
                .iter()
                .any(|k| sc_id_lower.contains(k))
            {
                "modern"
            } else {
                "ancient"
            };

            let room_id = sc.room_id.as_deref().unwrap_or("");
            let action = sc.action.as_str();
            let action_lower = action.to_lowercase();
            let line = sc.line.as_deref().unwrap_or("");
            let arc_phase = sc.arc_phase.as_deref().unwrap_or("");
            let acoustic_space = sc.acoustic_space.as_deref().unwrap_or("");
            let camera_motion = sc.camera_motion.as_deref().unwrap_or("");
            let ref_image = sc.ref_image.as_deref().unwrap_or("");

            // --- L1 Check 1: Psychological Arc Phase Presence & Monotonic Progression ---
            if let Some(&curr_idx) = phase_rank.get(arc_phase) {
                if curr_idx < last_phase_idx {
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L1-人物心理四阶段律".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "心理弧光阶段出现倒退（上一镜阶段索引 {} -> 当前 `{}`）。",
                            last_phase_idx, arc_phase
                        ),
                        suggestion:
                            "人物心理弧光必须按 phase_1 -> phase_2 -> phase_3 -> phase_4 单调推进，不可逻辑倒退。"
                                .to_string(),
                    });
                }
                last_phase_idx = last_phase_idx.max(curr_idx);
            } else {
                issues.push(LintIssue {
                    level: "ERROR".to_string(),
                    layer: "L1-人物心理四阶段律".to_string(),
                    scene_id: sc_id.clone(),
                    message: format!("未声明合法的 `arc_phase`（当前值: '{}'）。", arc_phase),
                    suggestion: format!("必须显式指定心理弧光阶段，可选值: {:?}", valid_arc_phases),
                });
            }

            // --- L1 Check 2: Mandatory Script Line / Voiceover ---
            if line.trim().is_empty() {
                issues.push(LintIssue {
                    level: "ERROR".to_string(),
                    layer: "L1-台词与叙事锁".to_string(),
                    scene_id: sc_id.clone(),
                    message: "镜头缺少核定台词或画外音 (`line`)。".to_string(),
                    suggestion: "在分镜配置中补充与 `script.md` 严格对齐的 `speaker` 与 `line`。"
                        .to_string(),
                });
            }

            // --- L1 Check 3: Chekhov's Gun Silent Foreshadowing & Show-Don't-Tell Protection ---
            for kw in &rules.always_banned_explicit_medical_terms_in_dialogue {
                if line.contains(kw.as_str()) {
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L1-细节体现律(禁直白说破)".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "台词中直白说出了禁用的设定/专业术语『{}』：\"{}\"",
                            kw, line
                        ),
                        suggestion: "核心设定与器物机理必须完全靠画面物理细节体现（Show, Don't Tell），严禁在台词中直白点破！".to_string(),
                    });
                }
            }

            if matches!(
                arc_phase,
                "phase_1_daily_empathy" | "phase_2_sudden_accident" | ""
            ) {
                for kw in &rules.silent_foreshadow_keywords_banned_in_dialogue {
                    if line.contains(kw.as_str()) {
                        issues.push(LintIssue {
                            level: "ERROR".to_string(),
                            layer: "L1-契诃夫之枪静默律".to_string(),
                            scene_id: sc_id.clone(),
                            message: format!(
                                "铺垫期台词中直接明牌剧透了静默伏笔关键词『{}』：\"{}\"",
                                kw, line
                            ),
                            suggestion: "关键道具与核心伏笔在铺垫期属于视觉暗线（Show, Don't Tell），仅允许写在画面 action 中自然陈列，严禁在台词中直接说破！".to_string(),
                        });
                    }
                }
            }

            // --- L2 Check 1: Character Reference Anchor & Existence ---
            if !sc.characters.is_empty() {
                if ref_image.is_empty() {
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L2-视觉资产事实锁".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "镜头包含角色 {:?}，但未显式绑定定妆母图 `ref_image`。",
                            sc.characters
                        ),
                        suggestion: "在 scene 中指定 `ref_image` 定妆/空间锚定母图，防止五官与空间漂移。"
                            .to_string(),
                    });
                } else if !self.base_dir.join(ref_image).exists() {
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L2-视觉资产事实锁".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!("绑定的定妆母图文件不存在: `{}`。", ref_image),
                        suggestion: "请检查 `characters/images/` 目录下的定妆母图路径。".to_string(),
                    });
                }
            }

            // --- L2 Check 2: Bidirectional Era Isolation ---
            let is_convention_cosplay = room_id == "anime_convention_hall"
                || action_lower.contains("convention")
                || action_lower.contains("cosplayer");
            if era == "modern"
                && !is_convention_cosplay
                && (action_lower.contains("armor")
                    || action_lower.contains("ancient chinese soldiers"))
            {
                issues.push(LintIssue {
                    level: "ERROR".to_string(),
                    layer: "L2-时代服化道隔离".to_string(),
                    scene_id: sc_id.clone(),
                    message:
                        "现代非漫展场景画面描述中混入了古代盔甲/古装士卒词汇，会导致古今串戏。"
                            .to_string(),
                    suggestion:
                        "使用 `era = \"modern\"` 与现代场景描述，将现代日常场景与古代战场服化道严格物理隔离。"
                            .to_string(),
                });
            } else if era == "ancient"
                && [
                    "dormitory",
                    "laptop",
                    "computer monitor",
                    "asphalt street",
                    "sedan",
                ]
                .iter()
                .any(|w| action_lower.contains(w))
            {
                issues.push(LintIssue {
                    level: "ERROR".to_string(),
                    layer: "L2-时代服化道隔离".to_string(),
                    scene_id: sc_id.clone(),
                    message:
                        "古代场景画面描述中混入了现代宿舍/电子屏幕/柏油路汽车词汇。".to_string(),
                    suggestion: "确保古装/历史场景完全使用对应历史时代环境与古装服化道描述。"
                        .to_string(),
                });
            }

            // --- L3 Check 1: Mandatory Acoustic Space Validation ---
            if acoustic_space.is_empty()
                || !self.fact_sheet.acoustic_spaces.contains_key(acoustic_space)
            {
                let valid_spaces: Vec<_> = self.fact_sheet.acoustic_spaces.keys().cloned().collect();
                issues.push(LintIssue {
                    level: "ERROR".to_string(),
                    layer: "L3-声画空间物理锁".to_string(),
                    scene_id: sc_id.clone(),
                    message: format!(
                        "未声明合法的声学空间 `acoustic_space`（当前值: '{}'）。",
                        acoustic_space
                    ),
                    suggestion: format!(
                        "必须指定 `fact_sheet.toml` 中定义的声学空间: {:?}",
                        valid_spaces
                    ),
                });
            }

            // --- L3 Check 2: Exterior Establishing before Closed Interior ---
            if matches!(
                acoustic_space,
                "exterior_storm" | "exterior_street_wet" | "ancient_battlefield"
            ) || sc.framing.to_lowercase().contains("establishing")
                || sc_id_lower.contains("exterior")
            {
                seen_exterior_establishing = true;
            }

            if matches!(acoustic_space, "interior_closed" | "ancient_tent_interior") {
                if !seen_exterior_establishing {
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L3-视听空间建置律".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "在未交代外部环境建置镜头的情况下，直接切入封闭内景 (`{}`)。",
                            acoustic_space
                        ),
                        suggestion: "场次必须遵循『外景建置先行律 (Exterior Establishing -> Interior Cut)』，先用外景镜头交代风雨或军营环境，再切入室内/帐内。".to_string(),
                    });
                }
                if action_lower.contains("heavy rain pouring")
                    && !action_lower.contains("window")
                    && !action_lower.contains("muffled")
                {
                    issues.push(LintIssue {
                        level: "WARNING".to_string(),
                        layer: "L3-声画空间一致性".to_string(),
                        scene_id: sc_id.clone(),
                        message: "关窗室内镜头提示词中包含未加修饰的倾盆大雨描述，易诱发视频模型生成室内漏雨或过大雨声。".to_string(),
                        suggestion: "室内镜头提示词应强调温暖静谧内景，并将 `acoustic_space` 设为 `interior_closed` 以启用 FFmpeg 420Hz 低通滤波闷雨声。".to_string(),
                    });
                }
            }

            // --- L3 Check 3: 3D Room Layout Topology & Cross-Shot Axis Continuity ---
            if !room_id.is_empty() {
                if let Some(room_cfg) = self.fact_sheet.spatial_rooms.get(room_id) {
                    for bad_topo in &room_cfg.banned_topology_contradictions {
                        if action_lower.contains(&bad_topo.to_lowercase()) {
                            issues.push(LintIssue {
                                level: "ERROR".to_string(),
                                layer: "L3-三维空间拓扑锁".to_string(),
                                scene_id: sc_id.clone(),
                                message: format!(
                                    "镜头画面描述违反了房间 `{}` 的固定三维空间拓扑（出现了越轴/方位颠倒词『{}』）。",
                                    room_id, bad_topo
                                ),
                                suggestion: format!(
                                    "必须严格保持房间拓扑一致：左={} | 中={} | 右={}。",
                                    room_cfg.camera_left,
                                    room_cfg.center_foreground,
                                    room_cfg.camera_right
                                ),
                            });
                        }
                    }
                    if acoustic_space == "exterior_storm" {
                        if let Some(ref expected_ext) = room_cfg.exterior_anchor_image {
                            if !expected_ext.is_empty() && ref_image != expected_ext {
                                issues.push(LintIssue {
                                    level: "ERROR".to_string(),
                                    layer: "L3-三维空间拓扑锁".to_string(),
                                    scene_id: sc_id.clone(),
                                    message: format!(
                                        "外景透窗镜头未绑定该房间专用的外景透窗空间锚定图 `{}`（当前: `{}`）。",
                                        expected_ext, ref_image
                                    ),
                                    suggestion: format!(
                                        "将 `ref_image` 设为 `\"{}\"`，确保从窗外看室内的桌面布局与内景镜头 100% 咬合。",
                                        expected_ext
                                    ),
                                });
                            }
                        }
                    }
                } else {
                    let valid_rooms: Vec<_> = self.fact_sheet.spatial_rooms.keys().cloned().collect();
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L3-三维空间拓扑锁".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "声明的 `room_id = \"{}\"` 未在 `fact_sheet.toml` 的 `[spatial_rooms]` 中定义。",
                            room_id
                        ),
                        suggestion: format!(
                            "请在 `[spatial_rooms]` 中登记该房间的左/中/右三维坐标与配对首帧母图，可选值: {:?}",
                            valid_rooms
                        ),
                    });
                }
            }

            // --- L4 Check 1: Mandatory Physical Camera Lens & Motion Vector ---
            if camera_motion.trim().is_empty() || !focal_re.is_match(&camera_motion.to_lowercase())
            {
                issues.push(LintIssue {
                    level: "ERROR".to_string(),
                    layer: "L4-物理摄影机参数锁".to_string(),
                    scene_id: sc_id.clone(),
                    message: format!(
                        "`camera_motion` 缺失或未包含明确物理镜头焦段（如 35mm/50mm/85mm）：'{}'。",
                        camera_motion
                    ),
                    suggestion:
                        "在 `camera_motion` 中明确指定物理焦段与运镜矢量，例如 `\"50mm anamorphic lens, subtle slow push-in\"`。"
                            .to_string(),
                });
            }

            // --- L4 Check 2: Dialogue Referent -> Visual Evidence Alignment ---
            for rule in &rules.dialogue_visual_evidence_rules {
                if !rule.dialogue_trigger.is_empty()
                    && line.contains(&rule.dialogue_trigger)
                    && !rule.required_any_in_action.is_empty()
                {
                    let matched = rule
                        .required_any_in_action
                        .iter()
                        .any(|req| action_lower.contains(&req.to_lowercase()));
                    if !matched {
                        issues.push(LintIssue {
                            level: "ERROR".to_string(),
                            layer: "L4-台词视觉证据对齐律".to_string(),
                            scene_id: sc_id.clone(),
                            message: format!(
                                "台词提到了『{}』，但画面 `action` 中缺少对应的直接视觉证据（需包含以下任一特征词: {:?}）。",
                                rule.dialogue_trigger, rule.required_any_in_action
                            ),
                            suggestion: if rule.description.is_empty() {
                                "确保台词所谈论的照片、器物或光学现象在画面中有直接对应的特写或屏幕画面。".to_string()
                            } else {
                                rule.description.clone()
                            },
                        });
                    }
                }
            }

            // --- L4 Check 3: Bilingual De-Literary Shootability Check ---
            for bad_kw in &rules.banned_literary_vagueness_in_action {
                if action_lower.contains(&bad_kw.to_lowercase()) {
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L4-去文学化可拍性".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "视频画面提示词包含不可拍的中/英文抽象词或心理描写『{}』。",
                            bad_kw
                        ),
                        suggestion:
                            "摄影机只能拍摄物理可见的动作与光影，请将其改写为具体的面部微表情、肢体动作、焦段景深与光影方向。"
                                .to_string(),
                    });
                }
            }

            // --- L5 Check 1: Voiceover Pacing & Polyphonic / Prosody Split Guard ---
            let dur = if sc.duration == 0 { 8.0 } else { sc.duration as f64 };
            let clean_chars = non_word_re.replace_all(line, "");
            let char_count = clean_chars.chars().count();
            let max_chars = (dur * 4.5) as usize;
            if char_count > max_chars {
                issues.push(LintIssue {
                    level: "WARNING".to_string(),
                    layer: "L5-配音韵律与语速锁".to_string(),
                    scene_id: sc_id.clone(),
                    message: format!(
                        "单镜头（{:.0}秒）台词字数过多（{}字 > 建议上限 {}字），会导致 TTS 强行加速失真或断词错误。",
                        dur, char_count, max_chars
                    ),
                    suggestion: format!(
                        "精简台词至 {} 字以内，确保在正常语速（+0% ~ +12%）下自然从容念完。",
                        max_chars
                    ),
                });
            }
            for (bad_phrase, preferred_phrase) in &rules.tts_pronunciation_overrides {
                if !bad_phrase.is_empty()
                    && bad_phrase != preferred_phrase
                    && line.contains(bad_phrase.as_str())
                    && !preferred_phrase.contains(bad_phrase.as_str())
                {
                    issues.push(LintIssue {
                        level: "WARNING".to_string(),
                        layer: "L5-配音防拆词与多音字锁".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "台词包含易被神经 TTS 误切分或多音字误读的词组『{}』。",
                            bad_phrase
                        ),
                        suggestion: format!(
                            "建议改为『{}』或通过 `format_tts_text()` 映射，确保发音与连读 100% 准确。",
                            preferred_phrase
                        ),
                    });
                }
            }

            // --- Universal H3 v2.5 / V9 Physical Continuity & 17k Phase Linter Rules ---

            // Rule H3-1: $17k$ Keyframe Phase Alignment Check
            for &kf_idx in &sc.keyframe_indices {
                if kf_idx > 0 && kf_idx % 17 != 0 {
                    let nearest = ((kf_idx as f32) / 17.0).round() as i32 * 17;
                    issues.push(LintIssue {
                        level: "ERROR".to_string(),
                        layer: "L4-H3_17k关键帧相位锁".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "中间/尾锚关键帧索引 `{}` 未对齐 MiniMax-H3 的 `17k` 1-Frame 黄金相位槽（会导致落入 4-Frame 压缩槽产生约 0.17s 姿态重影）！",
                            kf_idx
                        ),
                        suggestion: format!(
                            "请将关键帧索引修正为 `17` 的整数倍（如 `{}`；标准 `17k` 槽位: 0, 17, 34, 51, 68, 85, 102, 136, 170）。",
                            nearest
                        ),
                    });
                }
            }

            // Rule H3-2: Action-Displacement & Camera-Reframing Coupling Law (Anti-Decapitation)
            let has_vertical_rise = ["stands up", "rises from chair", "rises to his feet", "rises to her feet", "猛然起身", "霍然起立", "站起身"]
                .iter()
                .any(|w| action_lower.contains(w));
            let is_static_tight_cam = (sc.framing == "medium" || sc.framing == "closeup" || action_lower.contains("medium shot"))
                && !camera_motion.to_lowercase().contains("tilt")
                && !camera_motion.to_lowercase().contains("pull")
                && !camera_motion.to_lowercase().contains("crane");
            if has_vertical_rise && is_static_tight_cam {
                issues.push(LintIssue {
                    level: "ERROR".to_string(),
                    layer: "L4-位移与景别耦合律(防裁头)".to_string(),
                    scene_id: sc_id.clone(),
                    message: "在未配置上摇 (`tilts up`) 或拉远 (`pulls out`) 的固定中近景镜头中要求角色『起立/站起』，会导致头顶直接冲出画框上沿被裁切！".to_string(),
                    suggestion: "二选一修正：(A) 改为保持坐姿上半身前倾 (`remaining seated, leaning upper torso forward with comfortable headroom above the crown`)；或 (B) 在 `camera_motion` 中明确加入同步上摇拉远 (`camera tilts up and pulls back to medium-wide`)。".to_string(),
                });
            }

            // Rule H3-3: Anti-Negative-Leakage Law (Positive Stationary Head-Lock Phrasing)
            for neg_leak in [
                "without turning her face",
                "without turning his face",
                "never turning toward the camera",
                "do not turn head",
                "never looks at camera",
            ] {
                if action_lower.contains(neg_leak) {
                    issues.push(LintIssue {
                        level: "WARNING".to_string(),
                        layer: "L4-H3正言锁头律(防负向词泄漏)".to_string(),
                        scene_id: sc_id.clone(),
                        message: format!(
                            "画面提示词包含否定式防转头描述『{}』，Qwen3-VL 文本编码器会激活 `turning face` 动作向量导致尾段转头漂移。",
                            neg_leak
                        ),
                        suggestion: "请改用自然头部构图与正向视线描述：保持自然微动、视线稳定锁定前方 (keeping full head and shoulders comfortably inside the frame with natural micro-movements and steady eye-line axis) 或 gaze locked steadily forward。".to_string(),
                    });
                }
            }

            // Rule H3-4: 90-Degree Profile Plural-Feature Conflict Check
            let is_90_profile = action_lower.contains("90-degree side profile")
                || action_lower.contains("strict side profile")
                || sc.pose_anchors.iter().any(|p| p.ends_with("_side"));
            if is_90_profile
                && (action_lower.contains("both eyes")
                    || action_lower.contains("furrowed brows")
                    || action_lower.contains("wide eyes"))
            {
                issues.push(LintIssue {
                    level: "WARNING".to_string(),
                    layer: "L4-90度正侧脸单侧五官律".to_string(),
                    scene_id: sc_id.clone(),
                    message: "90° 正侧脸镜头 (`_side` / `90-degree side profile`) 中使用了双侧复数五官词（`both eyes` / `furrowed brows` / `wide eyes`），会诱发模型强行把脸拧回正面以展示双眼！".to_string(),
                    suggestion: "在正侧脸镜头中请一律使用单侧五官描述：`visible brow`、`visible eye`、`profile jawline`。".to_string(),
                });
            }

            // Rule H3-5: L4-微表演与四节拍细节密度锁 (4-Beat Micro-Acting & Detail Density Lock)
            let has_timestamped_beats = !sc.micro_beats.is_empty()
                || action_lower.contains("during 00:")
                || action_lower.contains("during 00:00")
                || action_lower.contains("00:00.000");

            let has_rich_micro_fields = sc.facial_progression.is_some()
                || sc.prop_interaction.is_some()
                || sc.listener_reaction.is_some()
                || sc.env_micro_physics.is_some();

            let has_anatomical_cues = [
                "glabella",
                "eyelid",
                "masseter",
                "nostril",
                "inhalation",
                "pupil",
                "eye-line",
                "micro-expression",
                "micro-acting",
                "tactile",
                "neck tension",
                "chest breathing",
                "breath mist",
                "lip corner",
            ]
            .iter()
            .any(|cue| action_lower.contains(cue));

            if !has_timestamped_beats && !has_rich_micro_fields && !has_anatomical_cues {
                issues.push(LintIssue {
                    level: "WARNING".to_string(),
                    layer: "L4-微表演与四节拍细节密度锁".to_string(),
                    scene_id: sc_id.clone(),
                    message: "分镜缺少 L4 四节拍微表演时间轴 (micro_beats / During 00:00) 或微表情/道具触觉/环境微物理细节密度描述。".to_string(),
                    suggestion: "请配置 `micro_beats` 四节拍、`facial_progression` 面部肌肉渐变、`prop_interaction` 触觉手势交互或解剖级微表情词汇（如 glabella, eyelid, masseter, tactile 等），以激发大模型微表演潜力。".to_string(),
                });
            }
        }

        LintReport::build(manifest_label, scenes.len(), issues)
    }

    pub fn format_tts_text(&self, line: &str) -> String {
        let mut tts_text = line.to_string();
        for (src, dst) in &self.fact_sheet.director_rules.tts_pronunciation_overrides {
            if !src.is_empty() && tts_text.contains(src.as_str()) {
                tts_text = tts_text.replace(src.as_str(), dst.as_str());
            }
        }
        tts_text
    }

    pub fn get_ffmpeg_bg_filter(&self, acoustic_space: &str) -> String {
        self.fact_sheet
            .acoustic_spaces
            .get(acoustic_space)
            .map(|s| s.ffmpeg_bg_filter.clone())
            .filter(|f| !f.is_empty())
            .unwrap_or_else(|| "volume=0.35".to_string())
    }
}
