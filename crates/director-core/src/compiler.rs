use std::path::{Path, PathBuf};

use crate::config::{DEFAULT_ASPECT, GLOBAL_STYLE_LOCK, MODERN_STYLE_LOCK, NEGATIVE_PROMPT};
use crate::models::{CharacterProfile, ProfilesToml, SceneSpec};

pub struct StoryboardCompiler {
    pub characters: Vec<CharacterProfile>,
}

impl StoryboardCompiler {
    pub fn from_profiles_path(path: &Path) -> Self {
        let characters = if path.exists() {
            std::fs::read_to_string(path)
                .ok()
                .and_then(|s| toml::from_str::<ProfilesToml>(&s).ok())
                .map(|p| p.characters)
                .unwrap_or_default()
        } else {
            Vec::new()
        };
        Self { characters }
    }

    pub fn compile_to_toml(
        &self,
        title: &str,
        scenes: &[SceneSpec],
        project_id: &str,
        output_dir: Option<&Path>,
        aspect: Option<&str>,
    ) -> String {
        let aspect = aspect.unwrap_or(DEFAULT_ASPECT);
        let mut lines = vec![
            format!("# Auto-generated L1-L5 Industrial AI Video Manifest: {}", title),
            "schema_version = 1".to_string(),
            format!("title = {}", escape_toml_str(title)),
            format!("project = {}", escape_toml_str(project_id)),
        ];

        if let Some(out) = output_dir {
            let safe_out = out.to_string_lossy().replace('\\', "/");
            lines.push(format!("output_dir = {}", escape_toml_str(&safe_out)));
        }

        lines.extend([
            "".to_string(),
            "[style]".to_string(),
            r#"look = "cinematic, 8k film grain, photorealistic, dramatic Rembrandt chiaroscuro lighting""#.to_string(),
            r#"palette = "rich earthy tones, warm tungsten highlights against deep slate shadows, Kodak Vision3 500T""#.to_string(),
            format!("negative = {}", escape_toml_str(NEGATIVE_PROMPT)),
            format!("suffix = {}", escape_toml_str(GLOBAL_STYLE_LOCK)),
            "".to_string(),
            "  [style.variants.modern]".to_string(),
            format!("  suffix = {}", escape_toml_str(MODERN_STYLE_LOCK)),
            "".to_string(),
            "  [style.variants.tense]".to_string(),
            r#"  suffix = "Tense claustrophobic military council, heavy shadows, flickering torchlight.""#.to_string(),
            "".to_string(),
            "  [style.variants.epic]".to_string(),
            r#"  suffix = "Vast sweeping landscape, misty Qinling mountains, sprawling ancient armies, cinematic grandeur.""#.to_string(),
            "".to_string(),
            "  [style.variants.intimate]".to_string(),
            r#"  suffix = "Soft warm lantern light, emotional quiet character focus, shallow depth of field.""#.to_string(),
        ]);

        for ch in &self.characters {
            lines.push("".to_string());
            lines.push("[[characters]]".to_string());
            lines.push(format!("name = {}", escape_toml_str(&ch.name)));
            if !ch.tier.is_empty() {
                lines.push(format!("tier = {}", escape_toml_str(&ch.tier)));
            }
            lines.push(format!("appearance = {}", escape_toml_str(&ch.appearance)));
            if let Some(ref v) = ch.appearance_modern {
                lines.push(format!("appearance_modern = {}", escape_toml_str(v)));
            }
            if let Some(ref v) = ch.appearance_ancient {
                lines.push(format!("appearance_ancient = {}", escape_toml_str(v)));
            }
            if let Some(ref v) = ch.voice {
                lines.push(format!("voice = {}", escape_toml_str(v)));
            }
            if let Some(ref v) = ch.ref_image_modern {
                lines.push(format!("ref_image_modern = {}", escape_toml_str(v)));
            }
            if let Some(ref v) = ch.ref_image_ancient {
                lines.push(format!("ref_image_ancient = {}", escape_toml_str(v)));
            }
            if let Some(ref v) = ch.ref_image {
                lines.push(format!("ref_image = {}", escape_toml_str(v)));
            }
            if let Some(ref v) = ch.turnaround_ref_image {
                lines.push(format!("turnaround_ref_image = {}", escape_toml_str(v)));
            }
            if let Some(ref v) = ch.costume_version {
                lines.push(format!("costume_version = {}", escape_toml_str(v)));
            }
        }

        for sc in scenes {
            let selected_model = sc
                .selected_model
                .as_deref()
                .filter(|s| !s.is_empty())
                .unwrap_or_else(|| {
                    if sc.model.is_empty() {
                        "veo-quality"
                    } else {
                        &sc.model
                    }
                });
            let produced_by = sc
                .produced_by_model
                .as_deref()
                .filter(|s| !s.is_empty())
                .unwrap_or(selected_model);

            let id_lower = sc.id.to_lowercase();
            let era = if !sc.era.is_empty() {
                sc.era.as_str()
            } else if ["modern", "dorm", "cosplay", "pack", "rain_exterior", "crash"]
                .iter()
                .any(|k| id_lower.contains(k))
            {
                "modern"
            } else {
                "ancient"
            };

            let style_variant = sc
                .style_variant
                .as_deref()
                .filter(|s| !s.is_empty())
                .unwrap_or_else(|| if era == "modern" { "modern" } else { "" });

            lines.push("".to_string());
            lines.push("[[scenes]]".to_string());
            lines.push(format!("id = {}", escape_toml_str(&sc.id)));
            lines.push(format!("era = {}", escape_toml_str(era)));
            lines.push(format!("action = {}", escape_toml_str(&sc.action)));
            lines.push(format!(
                "framing = {}",
                escape_toml_str(if sc.framing.is_empty() { "medium" } else { &sc.framing })
            ));
            lines.push(format!(
                "aspect = {}",
                escape_toml_str(if sc.aspect.is_empty() { aspect } else { &sc.aspect })
            ));
            lines.push(format!(
                "duration = {}",
                if sc.duration == 0 { 8 } else { sc.duration }
            ));
            lines.push(format!("model = {}", escape_toml_str(selected_model)));
            lines.push(format!("selected_model = {}", escape_toml_str(selected_model)));
            lines.push(format!("produced_by_model = {}", escape_toml_str(produced_by)));

            if let Some(ref v) = sc.room_id {
                if !v.is_empty() {
                    lines.push(format!("room_id = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.arc_phase {
                if !v.is_empty() {
                    lines.push(format!("arc_phase = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.acoustic_space {
                if !v.is_empty() {
                    lines.push(format!("acoustic_space = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.camera_motion {
                if !v.is_empty() {
                    lines.push(format!("camera_motion = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.ref_image {
                if !v.is_empty() {
                    lines.push(format!("ref_image = {}", escape_toml_str(v)));
                }
            }
            if !sc.characters.is_empty() {
                let chars_str = sc
                    .characters
                    .iter()
                    .map(|c| escape_toml_str(c))
                    .collect::<Vec<_>>()
                    .join(", ");
                lines.push(format!("characters = [{}]", chars_str));
            }
            if !sc.props.is_empty() {
                let props_str = sc
                    .props
                    .iter()
                    .map(|p| escape_toml_str(p))
                    .collect::<Vec<_>>()
                    .join(", ");
                lines.push(format!("props = [{}]", props_str));
            }
            if !style_variant.is_empty() {
                lines.push(format!("style_variant = {}", escape_toml_str(style_variant)));
            }
            if let Some(ref v) = sc.style_suffix {
                if !v.is_empty() {
                    lines.push(format!("style_suffix = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.dialogue_mode {
                if !v.is_empty() {
                    lines.push(format!("dialogue_mode = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.speaker {
                if !v.is_empty() {
                    lines.push(format!("speaker = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.line {
                if !v.is_empty() {
                    lines.push(format!("line = {}", escape_toml_str(v)));
                }
            }
            if let Some(v) = sc.shot_count {
                if v > 0 {
                    lines.push(format!("shot_count = {}", v));
                }
            }
            if let Some(v) = sc.trim_start_sec {
                if v > 0.0 {
                    lines.push(format!("trim_start_sec = {:.2}", v));
                }
            }
            if let Some(v) = sc.trim_end_sec {
                if v > 0.0 {
                    lines.push(format!("trim_end_sec = {:.2}", v));
                }
            }
            if let Some(ref v) = sc.foley_cue {
                if !v.is_empty() {
                    lines.push(format!("foley_cue = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.bgm_mood {
                if !v.is_empty() {
                    lines.push(format!("bgm_mood = {}", escape_toml_str(v)));
                }
            }
            if !sc.pose_anchors.is_empty() {
                let p_str = sc
                    .pose_anchors
                    .iter()
                    .map(|p| escape_toml_str(p))
                    .collect::<Vec<_>>()
                    .join(", ");
                lines.push(format!("pose_anchors = [{}]", p_str));
            }
            if !sc.keyframe_indices.is_empty() {
                let idx_str = sc
                    .keyframe_indices
                    .iter()
                    .map(|i| i.to_string())
                    .collect::<Vec<_>>()
                    .join(", ");
                lines.push(format!("keyframe_indices = [{}]", idx_str));
            }
            if !sc.keyframe_strengths.is_empty() {
                let s_str = sc
                    .keyframe_strengths
                    .iter()
                    .map(|s| format!("{:.2}", s))
                    .collect::<Vec<_>>()
                    .join(", ");
                lines.push(format!("keyframe_strengths = [{}]", s_str));
            }
            if let Some(ref v) = sc.continuity_track {
                if !v.is_empty() {
                    lines.push(format!("continuity_track = {}", escape_toml_str(v)));
                }
            }
            if let Some(v) = sc.tail_lock_v9 {
                lines.push(format!("tail_lock_v9 = {}", v));
            }
            if let Some(ref v) = sc.emotion_mode {
                if !v.is_empty() {
                    lines.push(format!("emotion_mode = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.character_card {
                if !v.is_empty() {
                    lines.push(format!("character_card = {}", escape_toml_str(v)));
                }
            }
            if !sc.micro_beats.is_empty() {
                let mb_str = sc
                    .micro_beats
                    .iter()
                    .map(|b| escape_toml_str(b))
                    .collect::<Vec<_>>()
                    .join(", ");
                lines.push(format!("micro_beats = [{}]", mb_str));
            }
            if let Some(ref v) = sc.facial_progression {
                if !v.is_empty() {
                    lines.push(format!("facial_progression = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.prop_interaction {
                if !v.is_empty() {
                    lines.push(format!("prop_interaction = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.listener_reaction {
                if !v.is_empty() {
                    lines.push(format!("listener_reaction = {}", escape_toml_str(v)));
                }
            }
            if let Some(ref v) = sc.env_micro_physics {
                if !v.is_empty() {
                    lines.push(format!("env_micro_physics = {}", escape_toml_str(v)));
                }
            }
            if !sc.sub_beat_emotions.is_empty() {
                let sbe_str = sc
                    .sub_beat_emotions
                    .iter()
                    .map(|e| escape_toml_str(e))
                    .collect::<Vec<_>>()
                    .join(", ");
                lines.push(format!("sub_beat_emotions = [{}]", sbe_str));
            }
        }

        lines.join("\n") + "\n"
    }

    /// Compiles a scene into a self-contained Seedance 2.0 Pro (720p) Cinematic Drama prompt
    /// with strict Reference Asset Matrix (`图片1... 图片2... 音频1...`), No-Subtitles Lock,
    /// No-BGM Raw Lock, and Multi-Shot (`镜头1... 镜头2...`) structure.
    pub fn compile_seedance_prompt(
        &self,
        sc: &SceneSpec,
        fact_sheet: &crate::models::FactSheet,
    ) -> serde_json::Value {
        let mut image_refs = Vec::new();
        let mut audio_refs = Vec::new();
        let mut ref_declarations = Vec::new();

        // 1. Bind visible characters' turnaround or reference cards
        for ch_name in &sc.characters {
            if let Some(ch) = self.characters.iter().find(|c| &c.name == ch_name) {
                if ch.tier == "extra" {
                    continue;
                }
                let img = ch
                    .turnaround_ref_image
                    .as_deref()
                    .or(ch.ref_image.as_deref())
                    .or(ch.ref_image_ancient.as_deref())
                    .or(ch.ref_image_modern.as_deref());
                if let Some(img_path) = img {
                    image_refs.push(img_path.to_string());
                    let idx = image_refs.len();
                    let costume = ch.costume_version.as_deref().unwrap_or("常规服饰 v1");
                    ref_declarations.push(format!(
                        "图片{}为{}的无文字多视图人物形象卡（当前服装版本：{}），卡中左侧正脸与右侧正面、侧面、背面全身均为同一个“{}”，只参考{}的面部身份、发型、体型、服装结构与材质 ({})，不把多个视图生成成多个角色。",
                        idx, ch.name, costume, ch.name, ch.name, ch.appearance
                    ));
                }
            }
        }

        // 2. Bind room/scene spatial reference if present
        if let Some(ref r_id) = sc.room_id {
            if let Some(room) = fact_sheet.spatial_rooms.get(r_id) {
                if let Some(ref room_img) = room.interior_anchor_image.as_ref().or(room.exterior_anchor_image.as_ref()) {
                    image_refs.push(room_img.to_string());
                    let idx = image_refs.len();
                    ref_declarations.push(format!(
                        "图片{}为场景『{}』的空间参考图，只参考空间结构（左：{}；中：{}；右：{}）、固定陈设、材质和基础光位。",
                        idx, r_id, room.camera_left, room.center_foreground, room.camera_right
                    ));
                }
            }
        } else if let Some(ref img_path) = sc.ref_image {
            if !image_refs.contains(img_path) {
                image_refs.push(img_path.clone());
                let idx = image_refs.len();
                ref_declarations.push(format!(
                    "图片{}为当前片段的首帧与空间构图参考。",
                    idx
                ));
            }
        }

        // 3. Bind continuity props / martial spirits / key items
        for prop_id in &sc.props {
            if let Some(prop) = fact_sheet.continuity_props.get(prop_id) {
                if let Some(ref p_img) = prop.ref_image {
                    image_refs.push(p_img.clone());
                    let idx = image_refs.len();
                    ref_declarations.push(format!(
                        "图片{}为关键连续性主体『{}』（版本：{}）的参考图，只参考其稳定造型、材质与比例（{}）。",
                        idx,
                        prop.name,
                        prop.version_tag.as_deref().unwrap_or("v1"),
                        prop.description
                    ));
                }
            }
        }

        // 4. Bind audio ONLY for the character who actually speaks in this clip
        if let (Some(speaker), Some(line)) = (sc.speaker.as_deref(), sc.line.as_deref()) {
            if !speaker.trim().is_empty() && !line.trim().is_empty() {
                if let Some(ch) = self.characters.iter().find(|c| c.name == speaker) {
                    if let Some(ref v_id) = ch.voice {
                        audio_refs.push(format!("assets/voices/{}.wav", v_id.trim_end_matches(".wav")));
                        let a_idx = audio_refs.len();
                        ref_declarations.push(format!(
                            "音频{}仅用于参考{}的音色，本片段准确台词只以提示词中 `{}` 内的对白为准。",
                            a_idx, speaker, "{}"
                        ));
                    }
                }
            }
        }

        let style_lock_str = if !fact_sheet.style_lock.global_suffix.is_empty() {
            fact_sheet.style_lock.global_suffix.clone()
        } else {
            GLOBAL_STYLE_LOCK.to_string()
        };

        let no_sub_lock = if fact_sheet.project.no_subtitles_lock {
            "全程不生成任何字幕、旁白文字、对白文字、标题、角色名条或其他屏幕叠字，所有信息只通过画面与声音表达。"
        } else {
            ""
        };

        let foley_part = sc
            .foley_cue
            .as_deref()
            .filter(|s| !s.is_empty())
            .map(|f| format!("<{}>", f))
            .unwrap_or_else(|| "<自然空间环境声与衣料动作拟音>".to_string());

        let dialogue_part = match (sc.speaker.as_deref(), sc.line.as_deref()) {
            (Some(sp), Some(ln)) if !ln.trim().is_empty() => {
                let phonetic_ln = normalize_chinese_phonetics_for_av(ln.trim());
                format!(
                    "{}说出{{{}}}。台词锁：整段能听到的人声只有双引号/花括号里的原话；不加任何词、语气词或笑声；没有台词的人完全不出声；动作里写的笑只是表情、没有声音。",
                    sp, phonetic_ln
                )
            }
            _ => "台词锁：本镜头全员完全不出声，不加任何语气词、叹气或笑声。".to_string(),
        };

        let camera_part = sc.camera_motion.as_deref().unwrap_or("50mm 标准镜头稳步推进");
        let full_prompt = format!(
            "{} 视觉风格锁定：{} {} 只有环境音效，不要音乐。纯净画面，无字幕，画面中不要出现任何字幕、文字或水印。\n镜头调度与动作（{}）：{} 声音时间线：{}{}",
            ref_declarations.join(""),
            style_lock_str,
            no_sub_lock,
            camera_part,
            sc.action,
            foley_part,
            dialogue_part
        );

        serde_json::json!({
            "scene_id": sc.id,
            "engine": "seedance-2.0-pro",
            "resolution": "720p",
            "duration": if sc.duration == 0 { 15 } else { sc.duration },
            "aspect_ratio": if sc.aspect.is_empty() { "16:9" } else { &sc.aspect },
            "enable_sound": true,
            "input_mode": if !image_refs.is_empty() || !audio_refs.is_empty() { "mixed2video" } else { "text2video" },
            "image_references": image_refs,
            "audio_references": audio_refs,
            "prompt": full_prompt,
        })
    }

    pub fn compile_h3_prompt_block(
        &self,
        sc: &SceneSpec,
        fact_sheet: &crate::models::FactSheet,
    ) -> serde_json::Value {
        self.compile_h3_v25_prompt(sc, fact_sheet)
    }

    /// Compiles a scene into the official MiniMax-H3 v2.5 / V9 `Ref2VA` 6-Block Prompt Protocol
    /// with `Speech-Active Gating`, `T8mars` Emotion Decoupling, `17k + 5` Golden Frame Contract,
    /// `$17k$` Pose Anchor Phase Alignment, `V9_TailLock`, and `MotionContext` relay flags.
    pub fn compile_h3_v25_prompt(
        &self,
        sc: &SceneSpec,
        fact_sheet: &crate::models::FactSheet,
    ) -> serde_json::Value {
        let mut image_refs = Vec::new();
        let mut audio_refs = Vec::new();
        let mut subject_lines = Vec::new();
        let mut retention_lines = Vec::new();

        // 1. Mount visual subjects (`<Picture 1>`, `<Picture 2>`, ...)
        for ch_name in &sc.characters {
            if let Some(ch) = self.characters.iter().find(|c| &c.name == ch_name) {
                if ch.tier == "extra" {
                    continue;
                }
                let img = ch
                    .turnaround_ref_image
                    .as_deref()
                    .or(ch.ref_image.as_deref())
                    .or(ch.ref_image_ancient.as_deref())
                    .or(ch.ref_image_modern.as_deref());
                if let Some(img_path) = img {
                    image_refs.push(img_path.to_string());
                    let idx = image_refs.len();
                    subject_lines.push(format!(
                        "- <Picture {}>: Visual identity and wardrobe reference for {} ({}).",
                        idx, ch.name, ch.appearance
                    ));
                    retention_lines.push(format!(
                        "- Preserve exact facial geometry, skin micro-texture, hairstyle, and costume materials of {} from <Picture {}> without splitting turnaround views into multiple people.",
                        ch.name, idx
                    ));
                }
            }
        }

        if let Some(ref r_id) = sc.room_id {
            if let Some(room) = fact_sheet.spatial_rooms.get(r_id) {
                if let Some(ref room_img) = room.interior_anchor_image.as_ref().or(room.exterior_anchor_image.as_ref()) {
                    if !image_refs.contains(room_img) {
                        image_refs.push(room_img.to_string());
                        let idx = image_refs.len();
                        subject_lines.push(format!(
                            "- <Picture {}>: 3D spatial environment reference for `{}` (Left: {}; Center: {}; Right: {}).",
                            idx, r_id, room.camera_left, room.center_foreground, room.camera_right
                        ));
                    }
                }
                retention_lines.push(format!(
                    "- Lock 180-degree south-side axis and spatial layout of `{}`: camera-left={}, center={}, camera-right={}.",
                    r_id, room.camera_left, room.center_foreground, room.camera_right
                ));
            }
        } else if let Some(ref img_path) = sc.ref_image {
            if !img_path.is_empty() && !image_refs.contains(img_path) {
                image_refs.push(img_path.clone());
                let idx = image_refs.len();
                subject_lines.push(format!(
                    "- <Picture {}>: Primary first-frame and spatial composition anchor.",
                    idx
                ));
            }
        }

        // 2. Speech-Active Gating: ONLY mount `<Audio 1>` when the character actively speaks
        let emotion_mode = sc.emotion_mode.as_deref().unwrap_or("natural");
        let mut has_speech = false;
        if let (Some(speaker), Some(line)) = (sc.speaker.as_deref(), sc.line.as_deref()) {
            let clean_line = line.trim();
            if !speaker.trim().is_empty() && !clean_line.is_empty() && sc.dialogue_mode.as_deref() != Some("vo") {
                has_speech = true;
                if let Some(ch) = self.characters.iter().find(|c| c.name == speaker) {
                    if let Some(ref v_id) = ch.voice {
                        audio_refs.push(format!("assets/voices/{}.wav", v_id.trim_end_matches(".wav")));
                    }
                }
                let a_tag = "<Audio 1>";
                if emotion_mode.starts_with("t8mars") {
                    subject_lines.push(format!(
                        "- {}: Vocal identity timbre anchor for {} (preserving ONLY the fundamental vocal identity from {} while breaking away from its calm baseline tone).",
                        a_tag, speaker, a_tag
                    ));
                } else {
                    subject_lines.push(format!(
                        "- {}: Vocal identity and acoustic timbre reference for {}.",
                        a_tag, speaker
                    ));
                }
            }
        }

        if subject_lines.is_empty() {
            subject_lines.push("- Primary cinema scene with photorealistic optics and natural physical motion.".to_string());
        }

        // Snap duration to zero-audio-overhang Golden Frames (39, 90, 141, 192)
        let target_frames = ((if sc.duration == 0 { 4 } else { sc.duration }) * 24) as i32;
        let golden_candidates = [39, 90, 141, 192];
        let golden_frames = *golden_candidates
            .iter()
            .min_by_key(|&&g| (g - target_frames).abs())
            .unwrap_or(&90);

        retention_lines.push(
            "- Maintain natural headroom and axis preservation keeping full head and shoulders comfortably inside the frame with natural micro-movements and steady eye-line axis, and keep zero screen text or subtitles.".to_string(),
        );
        if !sc.sub_beat_emotions.is_empty() {
            retention_lines.push(format!(
                "- Sub-beat emotion trajectory: {}.",
                sc.sub_beat_emotions.join(" -> ")
            ));
        }

        let summary_line = if has_speech && !image_refs.is_empty() {
            "[reference generation + audio reference] Joint audio-visual cinema shot with frame-accurate lip synchronization and locked 3D spatial continuity."
        } else if !image_refs.is_empty() {
            "[reference generation] Visually anchored cinema shot with locked subject identity and diegetic environmental acoustics."
        } else {
            "[text to audio-video generation] Photorealistic cinema shot with synchronized diegetic soundscape."
        };

        // 3. Detailed Description with 4-Beat Micro-Acting Timeline + <d>[Mandarin]...</d> + T8mars + LaoZhang1982 Locks
        let four_beat_desc = self.compile_4beat_micro_acting_description(sc, golden_frames);
        let dialogue_clause = match (sc.speaker.as_deref(), sc.line.as_deref()) {
            (Some(_sp), Some(ln)) if !ln.trim().is_empty() && sc.dialogue_mode.as_deref() != Some("vo") => {
                let phonetic_ln = normalize_chinese_phonetics_for_av(ln.trim());
                if emotion_mode == "t8mars_explosive" || emotion_mode == "t8mars_fury" {
                    format!(
                        " Speaking with explosive dramatic projection (+8dB vocal surge), preserving ONLY the vocal identity from <Audio 1> while breaking away from its calm tone—urgent, commanding, not calm, not restrained: <d>[Mandarin] {}</d> 台词锁：整段能听到的人声只有双引号里的原话；不加任何词、语气词或笑声；没有台词的人完全不出声。",
                        phonetic_ln
                    )
                } else {
                    format!(
                        " Speaking in the exact vocal timbre of <Audio 1> with crisp lip articulation: <d>[Mandarin] {}</d> 台词锁：整段能听到的人声只有双引号里的原话；不加任何词、语气词或笑声；没有台词的人完全不出声。",
                        phonetic_ln
                    )
                }
            }
            _ => " 台词锁：没有台词的人完全不出声，不加任何语气词或笑声。".to_string(),
        };

        let cam_line = sc
            .camera_motion
            .as_deref()
            .unwrap_or("The camera holds a steady 50mm anamorphic framing with a subtle slow push-in.");

        let pose_clause = if !sc.pose_anchors.is_empty() {
            format!(" Pose trajectory anchors (17k phase-locked): {:?}.", sc.pose_anchors)
        } else {
            String::new()
        };

        let soundscape = sc
            .foley_cue
            .as_deref()
            .filter(|s| !s.is_empty())
            .unwrap_or("Natural room acoustics, crisp fabric movement, and clear vocal presence.");

        let prompt_6block = format!(
            "subject_definitions:\n{}\n\nsummary: {}\n\nretention_analysis:\n{}\n\ndetailed_description:\n{}\nBase Action & Blocking: {}{}{}\nCamera Motion: {}\n\noverall_soundscape: {}\n\nnon_diegetic_music: None. 只有环境音效，不要音乐。纯净画面，无字幕，画面中不要出现任何字幕、文字或水印。",
            subject_lines.join("\n"),
            summary_line,
            retention_lines.join("\n"),
            four_beat_desc,
            sc.action.trim(),
            pose_clause,
            dialogue_clause,
            cam_line,
            soundscape
        );

        let snapped_indices: Vec<i32> = if !sc.keyframe_indices.is_empty() {
            sc.keyframe_indices
                .iter()
                .map(|&idx| {
                    if idx <= 0 {
                        0
                    } else {
                        let k = ((idx as f32) / 17.0).round() as i32;
                        (k * 17).min(golden_frames - 5)
                    }
                })
                .collect()
        } else if !sc.pose_anchors.is_empty() {
            match sc.pose_anchors.len() {
                1 => vec![0],
                2 => vec![0, 85.min(golden_frames - 5)],
                _ => vec![0, 51.min(golden_frames - 5), 85.min(golden_frames - 5)],
            }
        } else {
            vec![0]
        };

        let strengths: Vec<f32> = if !sc.keyframe_strengths.is_empty() {
            sc.keyframe_strengths.clone()
        } else {
            snapped_indices
                .iter()
                .enumerate()
                .map(|(i, _)| if i == 0 { 1.0 } else { 0.88 })
                .collect()
        };

        serde_json::json!({
            "scene_id": sc.id,
            "engine": "minimax-h3-v2.5",
            "golden_frames": golden_frames,
            "duration_sec": (golden_frames as f64) / 24.0,
            "continuity_track": sc.continuity_track.as_deref().unwrap_or("track_b_hard_cut"),
            "tail_lock_v9": sc.tail_lock_v9.unwrap_or(true),
            "emotion_mode": emotion_mode,
            "speech_active_gated": has_speech,
            "pose_anchors": sc.pose_anchors,
            "keyframe_indices_17k": snapped_indices,
            "keyframe_strengths": strengths,
            "image_references": image_refs,
            "audio_references": audio_refs,
            "character_card": sc.character_card,
            "prompt": prompt_6block,
        })
    }

    /// Compiles a scene into a Google Flow Veo 3.1 (`veo-quality` / `veo-fast` / `omni-flash`)
    /// Native Joint Audio-Video Prompt where Mandarin Chinese speech, vocal emotion, lip-sync,
    /// micro-expression acting, and diegetic sound effects are co-generated in a single pass.
    pub fn compile_veo_native_av_prompt(
        &self,
        sc: &SceneSpec,
        _fact_sheet: &crate::models::FactSheet,
    ) -> serde_json::Value {
        let initial_frame = sc
            .keyframes
            .first()
            .cloned()
            .or_else(|| sc.ref_image.clone())
            .unwrap_or_default();

        let emotion_mode = sc.emotion_mode.as_deref().unwrap_or("natural");
        let vocal_emotion_desc = match emotion_mode {
            "t8mars_explosive" | "t8mars_fury" => {
                "with explosive dramatic intensity, sharp commanding projection, and urgent emotional tension"
            }
            _ => "with expressive theatrical weight, natural emotional inflection, and authentic breathing pauses",
        };

        let dialogue_directive = match (sc.speaker.as_deref(), sc.line.as_deref()) {
            (Some(sp), Some(ln)) if !ln.trim().is_empty() => {
                let phonetic_ln = normalize_chinese_phonetics_for_av(ln.trim());
                let voice_id = self
                    .characters
                    .iter()
                    .find(|c| c.name == sp)
                    .and_then(|c| c.voice.as_deref())
                    .unwrap_or("alnilam");
                format!(
                    " Speaking aloud in Mandarin Chinese {} with clear, natural, synchronized lip movements. {} ({}) says: '{}' Strict Dialogue Lock: the ONLY human voice heard is the exact quoted line; no filler words, no sighs, no laughter; all other characters remain completely silent.",
                    vocal_emotion_desc,
                    sp,
                    voice_id,
                    phonetic_ln
                )
            }
            _ => " Strict Dialogue Lock: all characters remain completely silent with mouths closed.".to_string(),
        };

        let foley_desc = sc
            .foley_cue
            .as_deref()
            .filter(|s| !s.is_empty())
            .unwrap_or("authentic room acoustics, subtle prop and clothing movement foley");

        let full_prompt = format!(
            "{}{} Audio: {}. Only environmental sound effects, no background music, no English speech, clean video without any subtitles, text, or watermark.",
            sc.action.trim(),
            dialogue_directive,
            foley_desc
        );

        serde_json::json!({
            "scene_id": sc.id,
            "engine": sc.selected_model.as_deref().unwrap_or("veo-quality"),
            "mode": "native_joint_audio_video",
            "initial_frame": initial_frame,
            "aspect_ratio": if sc.aspect.is_empty() { "16:9" } else { &sc.aspect },
            "duration_sec": if sc.duration == 0 { 8 } else { sc.duration },
            "display_subtitle_line": sc.line,
            "phonetic_prompt_line": sc.line.as_deref().map(normalize_chinese_phonetics_for_av),
            "prompt": full_prompt,
        })
    }

    pub fn write_movie_file(
        &self,
        output_file: &Path,
        title: &str,
        scenes: &[SceneSpec],
        project_id: &str,
        output_dir: Option<&Path>,
        aspect: Option<&str>,
    ) -> anyhow::Result<PathBuf> {
        let content = self.compile_to_toml(title, scenes, project_id, output_dir, aspect);
        if let Some(parent) = output_file.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(output_file, content)?;
        Ok(output_file.to_path_buf())
    }

    /// Compiles a 4-beat micro-acting temporal performance description with explicit
    /// timestamped windows (Beat 1 airlock, Beat 2 delivery, Beat 3 climax & listener reaction, Beat 4 latent resonance).
    pub fn compile_4beat_micro_acting_description(
        &self,
        sc: &SceneSpec,
        golden_frames: i32,
    ) -> String {
        let dur_sec = (golden_frames as f64) / 24.0;
        let airlock_sec = 1.100f64.min(dur_sec * 0.35);
        let tail_sec = 1.300f64.min(dur_sec * 0.35);
        let speech_end = (dur_sec - tail_sec).max(airlock_sec + 0.4);
        let mid_sec = airlock_sec + (speech_end - airlock_sec) * 0.5;

        let b1_time = format!("During 00:00.000–{}", format_mmss_ms(airlock_sec));
        let b2_time = format!(
            "During {}–{}",
            format_mmss_ms(airlock_sec),
            format_mmss_ms(mid_sec)
        );
        let b3_time = format!(
            "During {}–{}",
            format_mmss_ms(mid_sec),
            format_mmss_ms(speech_end)
        );
        let b4_time = format!(
            "During {}–{}",
            format_mmss_ms(speech_end),
            format_mmss_ms(dur_sec)
        );

        if sc.micro_beats.len() == 4 {
            let mut formatted = Vec::new();
            let times = [&b1_time, &b2_time, &b3_time, &b4_time];
            for (i, beat) in sc.micro_beats.iter().enumerate() {
                if beat.starts_with("During ") {
                    formatted.push(beat.clone());
                } else {
                    let title = match i {
                        0 => "Beat 1: Subtext & Preparatory Airlock",
                        1 => "Beat 2: Opening Delivery & Micro-Expression Shift",
                        2 => "Beat 3: Climax Accent, Tactile Prop Force & Active Listener Reaction",
                        _ => "Beat 4: Emotional Resonance & Environmental Micro-Physics Tail Anchor",
                    };
                    formatted.push(format!("{} ({}) — {}", times[i], title, beat));
                }
            }
            if !sc.sub_beat_emotions.is_empty() {
                formatted.push(format!(
                    "Sub-beat emotion trajectory: [{}].",
                    sc.sub_beat_emotions.join(" -> ")
                ));
            }
            return formatted.join("\n");
        }

        let prop_b1 = sc
            .prop_interaction
            .as_deref()
            .filter(|s| !s.is_empty())
            .map(|p| format!("tactile hand contact with prop: {}.", p))
            .unwrap_or_else(|| "hands establish resting tactile grip with steady fingers.".to_string());

        let facial_b2 = sc
            .facial_progression
            .as_deref()
            .filter(|s| !s.is_empty())
            .unwrap_or("brow glabella micro-tension deepens, lower eyelids narrow into focused gaze, nasolabial lines define initial emotion");

        let listener_b3 = sc
            .listener_reaction
            .as_deref()
            .filter(|s| !s.is_empty())
            .map(|l| format!(" Non-speaking character physiological reaction: {}.", l))
            .unwrap_or_else(|| {
                if sc.characters.len() >= 2 {
                    " Non-speaking character exhibits involuntary physiological reaction with sharp pupil contraction and neck tension.".to_string()
                } else {
                    String::new()
                }
            });

        let env_b4 = sc
            .env_micro_physics
            .as_deref()
            .filter(|s| !s.is_empty())
            .unwrap_or("candle wick flame micro-tremor, subtle fabric sway, and delicate atmospheric breath mist");

        let b1 = format!(
            "{} (Beat 1: Subtext & Preparatory Airlock) — Eye-line shift with subtle pupil dilation, visible chest inhalation causing micro-expansion of ribs, brow/jaw micro-tension, {}; lips naturally closed with zero vocalization.",
            b1_time, prop_b1
        );
        let b2 = format!(
            "{} (Beat 2: Opening Delivery & Micro-Expression Shift) — Subtle upper-torso lean forward keeping headroom comfortably inside frame, initial facial muscle transition ({}), crisp Mandarin articulation begins.",
            b2_time, facial_b2
        );
        let b3 = format!(
            "{} (Beat 3: Climax Accent, Tactile Prop Force & Active Listener Reaction) — Peak vocal & facial muscle intensity (masseter flexing, jaw clenching), tactile hand/prop interaction climax;{}.",
            b3_time, listener_b3
        );
        let b4 = format!(
            "{} (Beat 4: Emotional Resonance & Environmental Micro-Physics Tail Anchor) — Lips close cleanly for 22f latent relay while chest breathing, piercing gaze along steady eye-line axis, and environmental micro-physics ({}) continue naturally.",
            b4_time, env_b4
        );

        let mut lines = vec![b1, b2, b3, b4];
        if !sc.sub_beat_emotions.is_empty() {
            lines.push(format!(
                "Sub-beat emotion trajectory: [{}].",
                sc.sub_beat_emotions.join(" -> ")
            ));
        }
        lines.join("\n")
    }
}

/// Formats seconds into mm:ss.sss timestamp format (e.g., 00:01.100).
pub fn format_mmss_ms(sec: f64) -> String {
    let clamped = sec.max(0.0);
    let mins = (clamped / 60.0).floor() as u32;
    let rem = clamped - (mins as f64 * 60.0);
    format!("{:02}:{:06.3}", mins, rem)
}

/// Converts rare Chinese characters, classical names, and stroke-dense literary words into
/// low-stroke Tier-1 phonetic homophones for native audio-video models (Veo 3.1 / MiniMax-H3)
/// while keeping the literary display text intact in the subtitle track (LaoZhang1982 Section 6).
///
/// Empirical discovery on Veo 3.1 Quality:
/// - Modern everyday Chinese (`你重构的？请解释一下，第四一二行这个暗门指针也是你写的？`) is pronounced 100% accurately.
/// - Dense/classical Chinese characters (`丞`, `拨`, `诡`, `察`, `伐`, `芯`, `烛`) suffer from VLM glyph-stroke
///   confusion (`丞->肘`, `拨->拖`, `诡->苦`, `察->习`, `伐->货`, `芯->乎`, `烛->入`).
/// - Replacing classical characters with low-stroke Tier-1 homophones (`成相`, `波亮`, `灯心`, `鬼炸`, `北发`, `详查`)
///   eliminates glyph hallucination while preserving natural 4-tone Mandarin prosody.
pub fn normalize_chinese_phonetics_for_av(line: &str) -> String {
    let replacements = [
        // Classical / rare historical names & terms -> low-stroke Tier-1 homophones
        ("张郃", "张河"),
        ("马谡", "马素"),
        ("街亭", "皆亭"),
        ("渭水", "畏水"),
        ("陇右", "拢右"),
        ("汲道", "吉道"),
        ("何足道哉", "何足道灾"),
        ("诡诈", "鬼炸"),
        ("所载", "所写"),
        ("北伐", "北发"),
        ("须细细详察", "需细细详查"),
        ("详察", "详查"),
        ("丞相", "成相"),
        ("湿寒", "失寒"),
        ("烛火", "竹火"),
        ("拨亮", "波亮"),
        ("灯芯", "灯心"),
        ("拨云见日", "波云见日"),
        ("之策", "之测"),
    ];
    let mut out = line.to_string();
    for (src, dst) in replacements {
        out = out.replace(src, dst);
    }
    out
}

fn escape_toml_str(s: &str) -> String {
    serde_json::to_string(s).unwrap_or_else(|_| format!("\"{}\"", s.replace('"', "\\\"")))
}
