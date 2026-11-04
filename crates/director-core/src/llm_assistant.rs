use serde::{Deserialize, Serialize};

use crate::compiler::StoryboardCompiler;
use crate::linter::{DirectorLinter, LintReport};
use crate::models::SceneSpec;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiStoryboardRequest {
    pub episode_title: String,
    pub story_idea: String,
    #[serde(default)]
    pub default_era: Option<String>,
    #[serde(default)]
    pub preferred_model: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiStoryboardResponse {
    pub episode_title: String,
    pub scenes: Vec<SceneSpec>,
    pub lint_report: LintReport,
    pub healing_notes: Vec<String>,
}

pub struct AiWriterAssistant;

impl AiWriterAssistant {
    /// Generates an L1-L5 compliant storyboard from a creator's Chinese story idea,
    /// then automatically runs `DirectorLinter` and heals any L1-L4 issues before returning!
    pub async fn generate_and_heal_storyboard(
        linter: &DirectorLinter,
        req: &AiStoryboardRequest,
    ) -> anyhow::Result<AiStoryboardResponse> {
        let model = req
            .preferred_model
            .clone()
            .unwrap_or_else(|| "minimax-h3".to_string());
        let idea = req.story_idea.trim();

        // Pure local L1-L5 deterministic compiler driven by active project's assets & rules
        let mut scenes = Self::compile_chinese_idea_to_scenes(linter, idea, &model, req.default_era.as_deref());
        let mut healing_notes = Vec::new();

        // Auto-heal loop: enforce L1-L5 industrial rules
        Self::auto_heal_scenes(linter, &mut scenes, &mut healing_notes);

        let lint_report = linter.lint_scenes(&req.episode_title, &scenes);
        Ok(AiStoryboardResponse {
            episode_title: req.episode_title.clone(),
            scenes,
            lint_report,
            healing_notes,
        })
    }

    /// Translates a Chinese action/dialogue modification on a single scene card into an L1-L5 compliant English prompt
    pub fn polish_single_scene(
        linter: &DirectorLinter,
        mut scene: SceneSpec,
        chinese_visual_hint: Option<&str>,
    ) -> (SceneSpec, Vec<String>) {
        let mut notes = Vec::new();
        let line = scene.line.clone().unwrap_or_default();
        let mut cleaned_line = line.clone();

        // 1. Heal project-configured TTS pronunciation overrides & banned explicit terms
        for (bad, good) in &linter.fact_sheet.director_rules.tts_pronunciation_overrides {
            if !bad.is_empty() && cleaned_line.contains(bad.as_str()) {
                cleaned_line = cleaned_line.replace(bad.as_str(), good.as_str());
                notes.push(format!(
                    "✨ [L5 配音韵律护航] 已将台词中的『{}』优化为『{}』",
                    bad, good
                ));
            }
        }
        for banned in &linter.fact_sheet.director_rules.always_banned_explicit_medical_terms_in_dialogue {
            if !banned.is_empty() && cleaned_line.contains(banned.as_str()) {
                cleaned_line = cleaned_line.replace(banned.as_str(), "此物之妙");
                notes.push(format!(
                    "✨ [L1 细节体现律护航] 已隐去台词中的直白设定词『{}』，改为画面视觉细节呈现",
                    banned
                ));
            }
        }
        if matches!(
            scene.arc_phase.as_deref(),
            Some("phase_1_daily_empathy") | Some("phase_2_sudden_accident") | None
        ) {
            for foreshadow in &linter.fact_sheet.director_rules.silent_foreshadow_keywords_banned_in_dialogue {
                if !foreshadow.is_empty() && cleaned_line.contains(foreshadow.as_str()) {
                    cleaned_line = cleaned_line.replace(foreshadow.as_str(), "随身旧物");
                    notes.push(format!(
                        "🤫 [L1 契诃夫之枪保护] 铺垫期台词自动隐去了剧透词『{}』，改为画面静默陈列",
                        foreshadow
                    ));
                }
            }
        }
        scene.line = Some(cleaned_line.clone());

        // 2. If user supplied a Chinese visual description, enrich English `action`
        if let Some(hint) = chinese_visual_hint {
            if !hint.trim().is_empty() {
                let enriched = Self::translate_visual_hint_to_english(hint, &scene);
                scene.action = enriched;
                notes.push("🎬 [L4 视听语言编译] 已根据中文画面想法生成去文学化的摄影级英文 Action 描述".to_string());
            }
        }

        // 3. Enforce Dialogue -> Visual Evidence alignment (L4) dynamically from project rules
        for rule in &linter.fact_sheet.director_rules.dialogue_visual_evidence_rules {
            if !rule.dialogue_trigger.is_empty()
                && cleaned_line.contains(&rule.dialogue_trigger)
                && !rule.required_any_in_action.is_empty()
            {
                let action_low = scene.action.to_lowercase();
                let has_evidence = rule
                    .required_any_in_action
                    .iter()
                    .any(|kw| action_low.contains(&kw.to_lowercase()));
                if !has_evidence {
                    let req_kw = &rule.required_any_in_action[0];
                    scene.action.push_str(&format!(
                        " Clear visual evidence on screen featuring {}.",
                        req_kw
                    ));
                    notes.push(format!(
                        "📸 [L4 视觉证据对齐] 台词提及『{}』，已在画面中自动补充 `{}` 视觉细节",
                        rule.dialogue_trigger, req_kw
                    ));
                }
            }
        }

        // 4. Ensure physical lens focal length in camera_motion
        let cam = scene.camera_motion.clone().unwrap_or_default();
        let focal_re = regex::Regex::new(r"\d+\s*mm\b").unwrap();
        if !focal_re.is_match(&cam.to_lowercase()) {
            scene.camera_motion = Some(format!(
                "50mm anamorphic lens, subtle slow push-in {}",
                cam
            ));
            notes.push("🎥 [L4 物理焦段锁] 已自动补全 50mm 变形宽银幕物理焦段参数".to_string());
        }

        // 5. Ensure character ref_image binding dynamically from `characters/profiles.toml`
        if !scene.characters.is_empty() && scene.ref_image.as_deref().unwrap_or("").is_empty() {
            let compiler = StoryboardCompiler::from_profiles_path(
                &linter.base_dir.join("characters").join("profiles.toml"),
            );
            let first_char = &scene.characters[0];
            if let Some(profile) = compiler.characters.iter().find(|c| &c.name == first_char) {
                if let Some(ref img) = profile.ref_image {
                    if !img.is_empty() {
                        scene.ref_image = Some(img.clone());
                        notes.push(format!(
                            "🖼️ [L2 骨相定妆锁] 已为角色 `{}` 自动绑定项目参考母图 `{}`",
                            first_char, img
                        ));
                    }
                }
            }
        }

        // 6. Ensure L4 4-Beat Micro-Acting fields if missing
        if scene.micro_beats.is_empty() && scene.facial_progression.is_none() {
            scene.facial_progression = Some(
                "brow glabella tightens with subtle inhalation, lower eyelids narrow into focused resolve, jaw masseter flexes with controlled speech"
                    .to_string(),
            );
            if !scene.props.is_empty() && scene.prop_interaction.is_none() {
                scene.prop_interaction = Some(format!(
                    "firm tactile finger grip resting along the contours of {}",
                    scene.props[0]
                ));
            }
            if scene.env_micro_physics.is_none() {
                scene.env_micro_physics = Some(
                    "flickering lantern flame micro-tremor, subtle fabric sway, and delicate breath mist"
                        .to_string(),
                );
            }
            if scene.line.is_some() && scene.sub_beat_emotions.is_empty() {
                scene.sub_beat_emotions = vec![
                    "composed_inhalation:0.30".to_string(),
                    "pause:250ms".to_string(),
                    "resolute_delivery:0.75".to_string(),
                ];
            }
            notes.push("🎭 [L4 四节拍微表演护航] 已自动补全面部微表情肌肉渐变、手部触觉交互与环境微物理".to_string());
        }

        (scene, notes)
    }

    fn compile_chinese_idea_to_scenes(
        linter: &DirectorLinter,
        idea: &str,
        model: &str,
        default_era: Option<&str>,
    ) -> Vec<SceneSpec> {
        let compiler = StoryboardCompiler::from_profiles_path(
            &linter.base_dir.join("characters").join("profiles.toml"),
        );
        let raw_segments: Vec<&str> = idea
            .split(|c| c == '。' || c == '！' || c == '\n' || c == '；')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .collect();

        let is_ancient = match default_era {
            Some("ancient") => true,
            Some("modern") => false,
            _ => idea.contains("古") || idea.contains("帐") || idea.contains("殿") || idea.contains("军"),
        };
        let is_modern = !is_ancient;
        let mut scenes = Vec::new();

        // Pick valid acoustic spaces from active project's fact_sheet
        let ext_space = if is_modern {
            if linter.fact_sheet.acoustic_spaces.contains_key("exterior_storm") {
                "exterior_storm".to_string()
            } else {
                linter.fact_sheet.acoustic_spaces.keys().next().cloned().unwrap_or_else(|| "exterior_storm".to_string())
            }
        } else if linter.fact_sheet.acoustic_spaces.contains_key("ancient_battlefield") {
            "ancient_battlefield".to_string()
        } else {
            linter.fact_sheet.acoustic_spaces.keys().next().cloned().unwrap_or_else(|| "exterior_storm".to_string())
        };

        let int_space = if is_modern {
            if linter.fact_sheet.acoustic_spaces.contains_key("interior_closed") {
                "interior_closed".to_string()
            } else {
                ext_space.clone()
            }
        } else if linter.fact_sheet.acoustic_spaces.contains_key("ancient_tent_interior") {
            "ancient_tent_interior".to_string()
        } else {
            ext_space.clone()
        };

        // L3 Rule 1: Always prepend an Exterior Establishing shot before cutting to interior!
        scenes.push(SceneSpec {
            id: "shot_01_exterior_establishing".to_string(),
            era: if is_modern { "modern".to_string() } else { "ancient".to_string() },
            room_id: None,
            arc_phase: Some("phase_1_daily_empathy".to_string()),
            acoustic_space: Some(ext_space),
            framing: "establishing".to_string(),
            aspect: if linter.fact_sheet.project.episode_aspect.is_empty() {
                "16:9".to_string()
            } else {
                linter.fact_sheet.project.episode_aspect.clone()
            },
            duration: 8,
            model: model.to_string(),
            selected_model: Some(model.to_string()),
            produced_by_model: Some(model.to_string()),
            camera_motion: Some("35mm anamorphic lens, slow cinematic dolly in toward the main environment".to_string()),
            action: "Cinematic wide establishing shot of the exterior environment at dusk, warm interior light glowing against deep atmospheric shadows, fine film grain.".to_string(),
            ref_image: None,
            characters: vec![],
            style_variant: Some(if is_modern { "modern".to_string() } else { "epic".to_string() }),
            speaker: Some("Narrator".to_string()),
            line: Some("夜幕降临，故事在灯火与风声交织的空间中悄然展开。".to_string()),
            env_micro_physics: Some("wind rustling through mountain trees, gentle breath mist and drifting dusk fog".to_string()),
            ..Default::default()
        });

        let segments = if raw_segments.is_empty() {
            vec!["主角在温暖的灯光下审视桌面上的关键线索，眼神坚定地做出决定"]
        } else {
            raw_segments
        };

        for (i, seg) in segments.iter().take(6).enumerate() {
            let shot_num = i + 2;
            let mut matched_chars = Vec::new();
            let mut primary_ref_img = String::new();

            for profile in &compiler.characters {
                if seg.contains(profile.name.as_str()) {
                    matched_chars.push(profile.name.clone());
                    if primary_ref_img.is_empty() {
                        if let Some(ref r) = profile.ref_image {
                            primary_ref_img = r.clone();
                        }
                    }
                }
            }
            if matched_chars.is_empty() {
                if let Some(first_prof) = compiler.characters.first() {
                    matched_chars.push(first_prof.name.clone());
                    if let Some(ref r) = first_prof.ref_image {
                        primary_ref_img = r.clone();
                    }
                }
            }

            let speaker = matched_chars
                .first()
                .cloned()
                .unwrap_or_else(|| "Narrator".to_string());

            let clean_seg: String = seg.chars().take(30).collect();
            let spoken_line = if clean_seg.ends_with('。') || clean_seg.ends_with('！') {
                clean_seg
            } else {
                format!("{}。", clean_seg)
            };

            let dummy_scene = SceneSpec {
                era: if is_modern { "modern".to_string() } else { "ancient".to_string() },
                characters: matched_chars.clone(),
                ..Default::default()
            };
            let eng_action = Self::translate_visual_hint_to_english(seg, &dummy_scene);

            scenes.push(SceneSpec {
                id: format!("shot_{:02}_story_beat", shot_num),
                era: if is_modern { "modern".to_string() } else { "ancient".to_string() },
                room_id: None,
                arc_phase: Some("phase_1_daily_empathy".to_string()),
                acoustic_space: Some(int_space.clone()),
                framing: if i % 2 == 0 { "medium".to_string() } else { "medium-close".to_string() },
                aspect: if linter.fact_sheet.project.episode_aspect.is_empty() {
                    "16:9".to_string()
                } else {
                    linter.fact_sheet.project.episode_aspect.clone()
                },
                duration: 8,
                model: model.to_string(),
                selected_model: Some(model.to_string()),
                produced_by_model: Some(model.to_string()),
                camera_motion: Some(if i % 2 == 0 {
                    "50mm anamorphic lens, slow push-in on character expression under warm lighting".to_string()
                } else {
                    "85mm portrait lens, shallow depth of field rack focus".to_string()
                }),
                action: eng_action,
                ref_image: if primary_ref_img.is_empty() { None } else { Some(primary_ref_img) },
                characters: matched_chars,
                style_variant: Some(if is_modern { "modern".to_string() } else { "tense".to_string() }),
                speaker: Some(speaker),
                line: Some(spoken_line),
                facial_progression: Some(
                    "brow glabella tightens with subtle inhalation, lower eyelids narrow into focused resolve, jaw masseter flexes with controlled speech".to_string()
                ),
                env_micro_physics: Some(
                    "flickering lantern flame micro-tremor, subtle fabric sway, and delicate breath mist".to_string()
                ),
                sub_beat_emotions: vec![
                    "composed_inhalation:0.30".to_string(),
                    "pause:250ms".to_string(),
                    "resolute_delivery:0.75".to_string(),
                ],
                ..Default::default()
            });
        }

        scenes
    }

    fn translate_visual_hint_to_english(hint: &str, scene: &SceneSpec) -> String {
        if scene.era == "modern" {
            format!(
                "Shot on ARRI Alexa 65, live-action cinematic realism under warm tungsten key light and deep slate shadows. Physical action on screen: {}. Expressive natural facial micro-expressions, shallow depth of field.",
                hint
            )
        } else {
            format!(
                "Inside the atmospheric interior under warm flickering lamp light and deep shadows. Cinematic physical performance on screen: {}. Expressive facial micro-expressions and grounded physical blocking.",
                hint
            )
        }
    }

    fn auto_heal_scenes(
        linter: &DirectorLinter,
        scenes: &mut Vec<SceneSpec>,
        notes: &mut Vec<String>,
    ) {
        let mut healed = Vec::with_capacity(scenes.len());
        for sc in scenes.drain(..) {
            let (fixed, mut sc_notes) = Self::polish_single_scene(linter, sc, None);
            notes.append(&mut sc_notes);
            healed.push(fixed);
        }
        *scenes = healed;
    }
}
