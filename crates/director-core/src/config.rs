use std::path::{Path, PathBuf};
use crate::models::{FactSheet, StylePresetEntry, VoicePresetEntry};

pub const SYSTEM_NAME: &str = "AetherDirector Studio";
pub const SYSTEM_TITLE_CN: &str = "AetherDirector Studio · 天枢 AI 影视工业工作台";
pub const SYSTEM_SLUG: &str = "aether-director-studio";
pub const SYSTEM_AUTH_SALT: &str = "aether_director_studio_salt_2026";
pub const DEFAULT_PROJECT_ID: &str = "default_project";

pub const DEFAULT_ASPECT: &str = "16:9";
pub const DEFAULT_VIDEO_MODEL: &str = "veo-quality";

pub const GLOBAL_STYLE_LOCK: &str = "Shot on ARRI Alexa 65 with Panavision anamorphic lens, live-action cinematic historical drama realism blended with Rembrandt classical oil-painting chiaroscuro lighting, real human skin micro-texture, rich warm amber/tungsten highlights against deep slate shadows, fine Kodak Vision3 500T film grain, 8k cinematic color grading.";

pub const MODERN_STYLE_LOCK: &str = "Shot on ARRI Alexa 65 with Panavision anamorphic lens, live-action cinematic realism blended with Rembrandt classical oil-painting chiaroscuro lighting, real human skin micro-texture, rich warm tungsten desk lamp highlights against deep slate shadows, fine Kodak Vision3 500T film grain, 8k cinematic color grading. Clean video without any subtitles or text.";

pub const STYLE_3D_CHINESE_ANIME: &str = "半写实 3D 国产动画电影语言：人物骨骼、肌肉受力与服装结构可信，五官和轮廓经过适度概括，不退化成照片级真人，也不使用低幼卡通比例。皮肤保留细腻次表面散射与适量纹理，头发采用清楚发束，布料、皮革、金属、木材和石材具有可辨材质与克制高光；电影化可解释布光、自然景深、体积空气和细腻胶片颗粒。全程不生成任何字幕、旁白文字、对白文字、标题、角色名条或其他屏幕叠字。";

pub const STYLE_3D_EASTERN_DARK_FANTASY: &str = "半写实东方奇幻暗黑 3D 电影语言：人物解剖、面部表演、服装受力和空间尺度可信，以东方审美概括轮廓、发式、衣装层次、兵器与建筑秩序；视觉基调深沉克制，以低饱和墨黑、铁灰、暗青、土褐和旧木色为基础，按剧情使用朱砂红、冷玉色或金色作为有限强调；旧丝、粗麻、皮革、乌铁、青铜、漆和玉材质可辨。全程不生成任何字幕、旁白文字、对白文字、标题、角色名条或其他屏幕叠字。";

pub const NEGATIVE_PROMPT: &str = "cartoon, anime, 3d render, plastic skin, fantasy magic glow, neon lights, watermark, floating text, gibberish subtitles, deformed face, extra limbs";

pub fn builtin_style_presets() -> Vec<StylePresetEntry> {
    vec![
        StylePresetEntry {
            id: "live_action_arri".to_string(),
            name: "真人电影写实 (ARRI Alexa 65 伦勃朗光影)".to_string(),
            mode: "cinematic_drama".to_string(),
            summary: "好莱坞/院线级真人影视质感，ARRI Alexa 65 + Panavision 变形宽银幕镜头，真实皮肤微纹理与柯达 500T 胶片颗粒。".to_string(),
            camera_base: "Shot on ARRI Alexa 65 with Panavision anamorphic lens, shallow depth of field".to_string(),
            lighting_base: "Rembrandt classical oil-painting chiaroscuro lighting, rich warm amber/tungsten highlights against deep slate shadows".to_string(),
            film_stock: "Kodak Vision3 500T film grain, 8k cinematic color grading".to_string(),
            global_suffix: GLOBAL_STYLE_LOCK.to_string(),
            negative_prompt: NEGATIVE_PROMPT.to_string(),
        },
        StylePresetEntry {
            id: "semi_realistic_3d_chinese_animation".to_string(),
            name: "半写实 3D 国漫电影 (追光/凡人修仙传质感)".to_string(),
            mode: "cinematic_drama".to_string(),
            summary: "吸收自 director Cinematic Drama 样片验证画风：兼具国漫造型概括、次表面散射肤质、清晰发束与电影级摄影运镜。".to_string(),
            camera_base: "Cinema 3D animation virtual camera, 35mm/50mm/85mm prime lenses, natural depth of field".to_string(),
            lighting_base: "Cinematic physically-based lighting, subsurface skin scattering, volumetric atmospheric air".to_string(),
            film_stock: "Semi-realistic 3D Chinese animation film rendering, subtle film grain".to_string(),
            global_suffix: STYLE_3D_CHINESE_ANIME.to_string(),
            negative_prompt: "photorealistic live-action actor, cheap plastic toy, chibi cartoon, watermark, subtitles, screen text".to_string(),
        },
        StylePresetEntry {
            id: "semi_realistic_eastern_dark_fantasy_3d".to_string(),
            name: "东方奇幻暗黑 3D 电影 (黑暗修真/志怪权谋)".to_string(),
            mode: "cinematic_drama".to_string(),
            summary: "吸收自 director Cinematic Drama 样片验证画风：低饱和墨黑/铁灰/旧木基调，朱砂红与冷玉青点缀，粗麻乌铁青铜高质感。".to_string(),
            camera_base: "Dark Eastern fantasy 3D cinema camera, dramatic low-angle and close-up tension".to_string(),
            lighting_base: "Deep ink-black and iron-grey low-key chiaroscuro with cinnabar red and cold jade accents".to_string(),
            film_stock: "Semi-realistic Eastern dark fantasy 3D film rendering, weathered bronze/silk/linen textures".to_string(),
            global_suffix: STYLE_3D_EASTERN_DARK_FANTASY.to_string(),
            negative_prompt: "western high fantasy, neon MMO wings, overexposed flat lighting, watermark, subtitles, screen text".to_string(),
        },
        StylePresetEntry {
            id: "storytime_2d_handdrawn".to_string(),
            name: "2D 叙事动画 / 解说漫剧 (Storytime & Explainer)".to_string(),
            mode: "storytime_animation".to_string(),
            summary: "适合第一人称故事讲述与高信息密度动画解说，线条干净、角色表情生动、视觉隐喻直观。".to_string(),
            camera_base: "2D animation storyboard camera, clean staging and readable silhouettes".to_string(),
            lighting_base: "Expressive cel-shaded lighting with warm/cool emotional contrast".to_string(),
            film_stock: "High-detail 2D digital animation, clean line art".to_string(),
            global_suffix: "High-quality 2D animated storytelling style, expressive character acting, clean composition without any screen text or subtitles.".to_string(),
            negative_prompt: "3d photorealism, uncanny valley, blurry lines, watermark, gibberish text".to_string(),
        },
        StylePresetEntry {
            id: "modern_cinema_drama".to_string(),
            name: "现代都市/职场/悬疑院线短剧 (Sony Venice 2 电影感)".to_string(),
            mode: "cinematic_drama".to_string(),
            summary: "通用现代剧预设：适用于都市情感、律政职场、悬疑商战、豪门反转等现代题材，Sony Venice 2 配合 Cooke Anamorphic 镜头，通透肤质与自然室内光比。".to_string(),
            camera_base: "Shot on Sony Venice 2 with Cooke Anamorphic/i Full Frame Plus lens, shallow depth of field".to_string(),
            lighting_base: "Natural architectural window light blended with soft tungsten practicals, refined contrast".to_string(),
            film_stock: "Kodak Vision3 250D clean modern cinema color grading, natural skin micro-texture".to_string(),
            global_suffix: "Shot on Sony Venice 2 with Cooke Anamorphic lens, photorealistic modern cinema drama, natural human skin micro-texture, refined architectural lighting, clean frame without any subtitles or watermarks.".to_string(),
            negative_prompt: "cartoon, anime, plastic skin, ancient armor, watermark, floating text, gibberish subtitles, deformed hands".to_string(),
        },
        StylePresetEntry {
            id: "high_fashion_gravure".to_string(),
            name: "时尚写真 / 模特T台 / 商业视觉大片 (Hasselblad + ARRI)".to_string(),
            mode: "commercial_showcase".to_string(),
            summary: "通用商业与模特展示预设：适用于服装电商、时尚大片、模特多姿态写真（联动 POSE-DB-01 1,439 动作库 17k 相位流转），极致皮肤光泽与丝绸/布料物理垂坠感。".to_string(),
            camera_base: "Shot on ARRI Alexa Mini LF with 85mm Master Prime lens at T1.4, creamy bokeh".to_string(),
            lighting_base: "High-fashion studio butterfly key light, warm golden rim light sculpting silhouette and hair strands".to_string(),
            film_stock: "Editorial luxury magazine color grading, luminous skin subsurface scattering, crisp fabric weave".to_string(),
            global_suffix: "High-fashion editorial cinema showcase, Shot on ARRI Alexa Mini LF 85mm Master Prime, luminous realistic skin texture, fluid posture transition, zero text overlays.".to_string(),
            negative_prompt: "cartoon, 3d doll, stiff posture, deformed fingers, extra limbs, watermark, subtitles".to_string(),
        },
    ]
}

pub fn builtin_voice_presets() -> Vec<VoicePresetEntry> {
    vec![
        VoicePresetEntry {
            id: "温厚沉稳青年男声-v1".to_string(),
            label: "温厚沉稳青年男声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "22岁青年男声".to_string(),
            description: "中低音域，清晰温厚、略带磁性；胸腔共鸣稳定，气息克制，语速适中略慢，冷静理性而有力量感。".to_string(),
            duration_sec: 5.06,
            file_name: "温厚沉稳青年男声-v1.wav".to_string(),
            url: "/media/voices/温厚沉稳青年男声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "冷硬自信青年男声-v1".to_string(),
            label: "冷硬自信青年男声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "21岁青年男声".to_string(),
            description: "中低音域，胸腔共鸣饱满，音色冷硬紧实；咬字清楚有棱角，从容自信并带压迫感。".to_string(),
            duration_sec: 5.06,
            file_name: "冷硬自信青年男声-v1.wav".to_string(),
            url: "/media/voices/冷硬自信青年男声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "沉静青年男声-v1".to_string(),
            label: "沉静克制青年男声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "青年男声".to_string(),
            description: "沉静、克制、平稳的青年男声，适合内敛智谋型主角或深度独白。".to_string(),
            duration_sec: 15.09,
            file_name: "沉静青年男声-v1.wav".to_string(),
            url: "/media/voices/沉静青年男声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "明亮高亢青年音-v2".to_string(),
            label: "明亮高亢热血青年音 v2".to_string(),
            language: "zh".to_string(),
            gender_age: "青年男声".to_string(),
            description: "明亮、高亢、富有活力的青年男声，适合少年英雄或高燃破局台词。".to_string(),
            duration_sec: 2.93,
            file_name: "明亮高亢青年音-v2.wav".to_string(),
            url: "/media/voices/明亮高亢青年音-v2.wav".to_string(),
        },
        VoicePresetEntry {
            id: "磁性沧桑中年男声-v1".to_string(),
            label: "磁性沧桑中年男声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "45岁中年男声".to_string(),
            description: "低音域，低厚磁性，带细碎颗粒感与轻微沧桑感；语速偏慢，沉着而有故事性（极适合统帅/长者/掌门）。".to_string(),
            duration_sec: 5.06,
            file_name: "磁性沧桑中年男声-v1.wav".to_string(),
            url: "/media/voices/磁性沧桑中年男声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "慈祥睿智老年男声-v1".to_string(),
            label: "慈祥睿智老年男声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "65岁老年男声".to_string(),
            description: "中低音域，浑厚温润，带自然年龄质感；语速舒缓，吐字清晰，表达慈祥睿智。".to_string(),
            duration_sec: 5.06,
            file_name: "慈祥睿智老年男声-v1.wav".to_string(),
            url: "/media/voices/慈祥睿智老年男声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "清透克制年轻女声-v1".to_string(),
            label: "清透克制年轻女声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "18岁年轻女声".to_string(),
            description: "中高音域，清透偏冷，带轻柔气息但吐字清楚；尾音收束干净，表达疏离克制而平静。".to_string(),
            duration_sec: 5.06,
            file_name: "清透克制年轻女声-v1.wav".to_string(),
            url: "/media/voices/清透克制年轻女声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "清冷疏离年轻女声-v1".to_string(),
            label: "清冷疏离年轻女声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "25岁年轻女声".to_string(),
            description: "中高音域，清透偏冷，语速从容，尾音收束，适合高冷女主或清冷剑仙。".to_string(),
            duration_sec: 5.06,
            file_name: "清冷疏离年轻女声-v1.wav".to_string(),
            url: "/media/voices/清冷疏离年轻女声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "灵动活泼年轻女声-v1".to_string(),
            label: "灵动活泼年轻女声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "年轻女声".to_string(),
            description: "中高音域，明亮轻盈，尾音富有弹性；语速稍快，活泼聪慧，不过度卡通化。".to_string(),
            duration_sec: 5.08,
            file_name: "灵动活泼年轻女声-v1.wav".to_string(),
            url: "/media/voices/灵动活泼年轻女声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "温柔治愈成年女声-v1".to_string(),
            label: "温柔治愈成年女声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "30岁成年女声".to_string(),
            description: "中低音域，柔和温暖，带少量自然气息；语速舒缓，语气亲切。".to_string(),
            duration_sec: 5.06,
            file_name: "温柔治愈成年女声-v1.wav".to_string(),
            url: "/media/voices/温柔治愈成年女声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "冷静知性成年女声-v1".to_string(),
            label: "冷静知性成年女声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "35岁成年女声".to_string(),
            description: "中低音域，清晰冷静、质地干净；气息克制，节奏利落，知性而有逻辑感。".to_string(),
            duration_sec: 5.06,
            file_name: "冷静知性成年女声-v1.wav".to_string(),
            url: "/media/voices/冷静知性成年女声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "清澈自然少年音-v1".to_string(),
            label: "清澈自然少年音 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "16岁少年音".to_string(),
            description: "中高音域，清澈干净，语速适中，节奏轻快，表达真诚。".to_string(),
            duration_sec: 5.06,
            file_name: "清澈自然少年音-v1.wav".to_string(),
            url: "/media/voices/清澈自然少年音-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "童真自然女童声-v1".to_string(),
            label: "童真自然女童声 v1".to_string(),
            language: "zh".to_string(),
            gender_age: "10岁女童声".to_string(),
            description: "高音域，清脆纯净；节奏轻盈，童真自然，不过度卖萌或卡通化。".to_string(),
            duration_sec: 5.06,
            file_name: "童真自然女童声-v1.wav".to_string(),
            url: "/media/voices/童真自然女童声-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "English-Exhausted-Weak-Young-Male-v1".to_string(),
            label: "English Exhausted Young Male v1".to_string(),
            language: "en".to_string(),
            gender_age: "18-19yo English Male".to_string(),
            description: "Breath-weak, low-energy, slightly raspy young male voice; restrained and natural.".to_string(),
            duration_sec: 5.06,
            file_name: "English-Exhausted-Weak-Young-Male-v1.wav".to_string(),
            url: "/media/voices/English-Exhausted-Weak-Young-Male-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "English-Bright-High-Pitched-Teenage-Female-v1".to_string(),
            label: "English Bright Teenage Female v1".to_string(),
            language: "en".to_string(),
            gender_age: "15-16yo English Female".to_string(),
            description: "Bright, energetic, confident teenage female voice without cartoon exaggeration.".to_string(),
            duration_sec: 5.06,
            file_name: "English-Bright-High-Pitched-Teenage-Female-v1.wav".to_string(),
            url: "/media/voices/English-Bright-High-Pitched-Teenage-Female-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "English-Bright-High-Pitched-Teenage-Male-v1".to_string(),
            label: "English Bright Teenage Male v1".to_string(),
            language: "en".to_string(),
            gender_age: "17-18yo English Male".to_string(),
            description: "High tenor teenage male voice, bright and confident with clear chest resonance.".to_string(),
            duration_sec: 5.06,
            file_name: "English-Bright-High-Pitched-Teenage-Male-v1.wav".to_string(),
            url: "/media/voices/English-Bright-High-Pitched-Teenage-Male-v1.wav".to_string(),
        },
        VoicePresetEntry {
            id: "English-Ultra-High-Pitched-Teenage-Male-v1".to_string(),
            label: "English Ultra-High Teenage Male v1".to_string(),
            language: "en".to_string(),
            gender_age: "15-16yo English Male".to_string(),
            description: "Ultra-high register energetic teenage voice for animated explainers or stylized youth leads.".to_string(),
            duration_sec: 5.06,
            file_name: "English-Ultra-High-Pitched-Teenage-Male-v1.wav".to_string(),
            url: "/media/voices/English-Ultra-High-Pitched-Teenage-Male-v1.wav".to_string(),
        },
    ]
}

#[derive(Debug, Clone)]
pub struct WorkspacePaths {
    pub root_dir: PathBuf,
    pub projects_dir: PathBuf,
    pub active_project_id: String,
    pub base_dir: PathBuf,
    pub fact_sheet_file: PathBuf,
    pub characters_file: PathBuf,
    pub characters_images_dir: PathBuf,
    pub episodes_dir: PathBuf,
    pub output_dir: PathBuf,
    pub raw_clips_dir: PathBuf,
    pub final_episodes_dir: PathBuf,
    pub studio_state_file: PathBuf,
}

impl WorkspacePaths {
    /// Detects the project ID defined in `root_dir/fact_sheet.toml` if a root-level project exists.
    pub fn detect_root_project_id(root_dir: &Path) -> Option<String> {
        let root_fs = root_dir.join("fact_sheet.toml");
        if !root_fs.exists() {
            return None;
        }
        if let Ok(raw) = std::fs::read_to_string(&root_fs) {
            if let Ok(fs) = toml::from_str::<FactSheet>(&raw) {
                let clean: String = fs
                    .project
                    .id
                    .chars()
                    .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
                    .collect();
                if !clean.is_empty() {
                    return Some(clean);
                }
            }
        }
        Some(DEFAULT_PROJECT_ID.to_string())
    }

    /// Resolves the currently active project ID from `.active_project`, or falls back to
    /// the first discovered project in `projects/` or root `fact_sheet.toml`.
    pub fn resolve_active_project_id(root_dir: &Path) -> String {
        if let Ok(raw) = std::fs::read_to_string(root_dir.join(".active_project")) {
            let trimmed: String = raw
                .trim()
                .chars()
                .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
                .collect();
            if !trimmed.is_empty() {
                return trimmed;
            }
        }
        if let Some(root_pid) = Self::detect_root_project_id(root_dir) {
            return root_pid;
        }
        if let Ok(entries) = std::fs::read_dir(root_dir.join("projects")) {
            let mut dirs: Vec<_> = entries
                .flatten()
                .filter(|e| e.path().is_dir() && !e.file_name().to_string_lossy().starts_with('.'))
                .collect();
            dirs.sort_by_key(|e| e.file_name());
            if let Some(first) = dirs.first() {
                return first.file_name().to_string_lossy().to_string();
            }
        }
        DEFAULT_PROJECT_ID.to_string()
    }

    /// Discovers all projects across the workspace (root project if present + `projects/*`).
    pub fn discover_all_projects(root_dir: &Path) -> Vec<Self> {
        let mut list = Vec::new();
        let mut seen_ids = std::collections::BTreeSet::new();

        if let Some(root_pid) = Self::detect_root_project_id(root_dir) {
            seen_ids.insert(root_pid.clone());
            list.push(Self::for_project(root_dir, &root_pid));
        }

        let projects_root = root_dir.join("projects");
        if let Ok(entries) = std::fs::read_dir(&projects_root) {
            let mut dirs: Vec<_> = entries.flatten().filter(|e| e.path().is_dir()).collect();
            dirs.sort_by_key(|e| e.file_name());
            for d in dirs {
                let pid = d.file_name().to_string_lossy().to_string();
                if pid.starts_with('.') || seen_ids.contains(&pid) {
                    continue;
                }
                seen_ids.insert(pid.clone());
                list.push(Self::for_project(root_dir, &pid));
            }
        }

        if list.is_empty() {
            list.push(Self::for_project(root_dir, DEFAULT_PROJECT_ID));
        }
        list
    }

    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        let root_dir = base_dir.into();
        let pid = Self::resolve_active_project_id(&root_dir);
        Self::for_project(root_dir, &pid)
    }

    pub fn for_project(root_dir: impl Into<PathBuf>, project_id: &str) -> Self {
        let root_dir = root_dir.into();
        let projects_dir = root_dir.join("projects");
        let clean_id: String = project_id
            .chars()
            .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
            .collect();
        let active_project_id = if clean_id.is_empty() {
            Self::resolve_active_project_id(&root_dir)
        } else {
            clean_id
        };

        let root_pid = Self::detect_root_project_id(&root_dir);
        let candidate = projects_dir.join(&active_project_id);
        let base_dir = if candidate.join("fact_sheet.toml").exists() {
            candidate
        } else if root_pid.as_deref() == Some(active_project_id.as_str())
            && root_dir.join("fact_sheet.toml").exists()
        {
            root_dir.clone()
        } else {
            candidate
        };

        let output_dir = base_dir.join("output");
        Self {
            fact_sheet_file: base_dir.join("fact_sheet.toml"),
            characters_file: base_dir.join("characters").join("profiles.toml"),
            characters_images_dir: base_dir.join("characters").join("images"),
            episodes_dir: base_dir.join("episodes"),
            raw_clips_dir: output_dir.join("raw_clips"),
            final_episodes_dir: output_dir.join("final_episodes"),
            studio_state_file: output_dir.join("studio_state.json"),
            output_dir,
            base_dir,
            projects_dir,
            active_project_id,
            root_dir,
        }
    }

    pub fn is_root_hosted(&self) -> bool {
        self.base_dir == self.root_dir
    }

    pub fn ensure_dirs(&self) -> std::io::Result<()> {
        std::fs::create_dir_all(&self.projects_dir)?;
        std::fs::create_dir_all(&self.characters_images_dir)?;
        std::fs::create_dir_all(&self.episodes_dir)?;
        std::fs::create_dir_all(&self.raw_clips_dir)?;
        std::fs::create_dir_all(&self.final_episodes_dir)?;
        Ok(())
    }
}
