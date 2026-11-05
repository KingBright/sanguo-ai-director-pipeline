use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FactSheet {
    #[serde(default)]
    pub project: ProjectMeta,
    #[serde(default)]
    pub style_lock: StyleLock,
    #[serde(default)]
    pub director_rules: DirectorRules,
    #[serde(default)]
    pub master_stages: Vec<MasterStage>,
    #[serde(default)]
    pub spatial_rooms: BTreeMap<String, SpatialRoom>,
    #[serde(default)]
    pub acoustic_spaces: BTreeMap<String, AcousticSpace>,
    #[serde(default)]
    pub continuity_props: BTreeMap<String, ContinuityProp>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProjectMeta {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub pipeline_type: String,
    #[serde(default)]
    pub episode_aspect: String,
    #[serde(default)]
    pub historical_anchor_year: String,
    #[serde(default = "default_production_mode")]
    pub production_mode: String,
    #[serde(default = "default_style_preset")]
    pub style_preset: String,
    #[serde(default = "default_true")]
    pub no_subtitles_lock: bool,
}

fn default_production_mode() -> String {
    "cinematic_drama".to_string()
}

fn default_style_preset() -> String {
    "live_action_arri".to_string()
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ContinuityProp {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub category: String, // "prop", "weapon", "summon", "vehicle", "artifact"
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub ref_image: Option<String>,
    #[serde(default)]
    pub version_tag: Option<String>, // e.g. "v1_normal", "v2_awakened"
    #[serde(default)]
    pub owner_character: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoicePresetEntry {
    pub id: String,
    pub label: String,
    pub language: String,
    pub gender_age: String,
    pub description: String,
    pub duration_sec: f64,
    pub file_name: String,
    pub url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StylePresetEntry {
    pub id: String,
    pub name: String,
    pub mode: String,
    pub summary: String,
    pub camera_base: String,
    pub lighting_base: String,
    pub film_stock: String,
    pub global_suffix: String,
    pub negative_prompt: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct StyleLock {
    #[serde(default)]
    pub camera_base: String,
    #[serde(default)]
    pub lighting_base: String,
    #[serde(default)]
    pub film_stock: String,
    #[serde(default)]
    pub global_suffix: String,
    #[serde(default)]
    pub modern_suffix: String,
    #[serde(default)]
    pub negative_prompt: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DirectorRules {
    #[serde(default)]
    pub silent_foreshadow_keywords_banned_in_dialogue: Vec<String>,
    #[serde(default)]
    pub always_banned_explicit_medical_terms_in_dialogue: Vec<String>,
    #[serde(default)]
    pub banned_literary_vagueness_in_action: Vec<String>,
    #[serde(default)]
    pub psychological_arc_phases: Vec<String>,
    #[serde(default)]
    pub tts_max_rate_percent: u32,
    #[serde(default)]
    pub tts_pronunciation_overrides: BTreeMap<String, String>,
    #[serde(default)]
    pub dialogue_visual_evidence_rules: Vec<DialogueEvidenceRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DialogueEvidenceRule {
    #[serde(default)]
    pub dialogue_trigger: String,
    #[serde(default)]
    pub required_any_in_action: Vec<String>,
    #[serde(default)]
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MasterStage {
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub description: String,
    #[serde(default = "default_axis_lock")]
    pub axis_lock: String,
    #[serde(default)]
    pub slots: BTreeMap<String, CharacterSlot>,
}

fn default_axis_lock() -> String {
    "180deg_south".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CharacterSlot {
    #[serde(default)]
    pub x_slot: f64,
    #[serde(default)]
    pub z_depth: f64,
    #[serde(default)]
    pub facing: String,
    #[serde(default)]
    pub initial_props: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DialogueTurn {
    pub speaker: String,
    #[serde(default)]
    pub start_offset: f64,
    #[serde(default)]
    pub duration: f64,
    #[serde(default)]
    pub line: String,
    #[serde(default)]
    pub mouth_roi: Option<Vec<f64>>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SpatialRoom {
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub camera_left: String,
    #[serde(default)]
    pub center_foreground: String,
    #[serde(default)]
    pub camera_right: String,
    #[serde(default)]
    pub exterior_anchor_image: Option<String>,
    #[serde(default)]
    pub interior_anchor_image: Option<String>,
    #[serde(default)]
    pub banned_topology_contradictions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AcousticSpace {
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub ffmpeg_bg_filter: String,
    #[serde(default)]
    pub h3_audio_cue: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProfilesToml {
    #[serde(default)]
    pub characters: Vec<CharacterProfile>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CharacterProfile {
    pub name: String,
    #[serde(default = "default_char_tier")]
    pub tier: String, // "protagonist", "supporting", "extra"
    #[serde(default)]
    pub appearance: String,
    #[serde(default)]
    pub appearance_modern: Option<String>,
    #[serde(default)]
    pub appearance_ancient: Option<String>,
    #[serde(default)]
    pub voice: Option<String>,
    #[serde(default)]
    pub ref_image: Option<String>,
    #[serde(default)]
    pub ref_image_modern: Option<String>,
    #[serde(default)]
    pub ref_image_ancient: Option<String>,
    #[serde(default)]
    pub turnaround_ref_image: Option<String>, // 16:9 pure-white 4-view character turnaround card
    #[serde(default)]
    pub costume_version: Option<String>, // e.g. "v1_base", "v2_battle_armor"
}

fn default_char_tier() -> String {
    "protagonist".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MovieManifest {
    #[serde(default = "default_schema_version")]
    pub schema_version: u32,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub project: String,
    #[serde(default)]
    pub output_dir: Option<String>,
    #[serde(default)]
    pub master_stages: Vec<MasterStage>,
    #[serde(default)]
    pub characters: Vec<CharacterProfile>,
    #[serde(default)]
    pub scenes: Vec<SceneSpec>,
}

fn default_schema_version() -> u32 {
    1
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SceneSpec {
    pub id: String,
    #[serde(default)]
    pub era: String,
    #[serde(default)]
    pub action: String,
    #[serde(default = "default_framing")]
    pub framing: String,
    #[serde(default = "default_aspect")]
    pub aspect: String,
    #[serde(default = "default_duration")]
    pub duration: u32,
    #[serde(default = "default_model")]
    pub model: String,
    #[serde(default)]
    pub selected_model: Option<String>,
    #[serde(default)]
    pub produced_by_model: Option<String>,
    #[serde(default)]
    pub room_id: Option<String>,
    #[serde(default)]
    pub arc_phase: Option<String>,
    #[serde(default)]
    pub acoustic_space: Option<String>,
    #[serde(default)]
    pub camera_motion: Option<String>,
    #[serde(default)]
    pub ref_image: Option<String>,
    #[serde(default)]
    pub characters: Vec<String>,
    #[serde(default)]
    pub props: Vec<String>,
    #[serde(default)]
    pub style_variant: Option<String>,
    #[serde(default)]
    pub style_suffix: Option<String>,
    #[serde(default)]
    pub dialogue_mode: Option<String>,
    #[serde(default)]
    pub speaker: Option<String>,
    #[serde(default)]
    pub line: Option<String>,
    #[serde(default)]
    pub shot_count: Option<u32>, // e.g., 5 shots in a 15s Seedance clip
    #[serde(default)]
    pub trim_start_sec: Option<f64>,
    #[serde(default)]
    pub trim_end_sec: Option<f64>, // e.g. 0.15s tail glitch trim
    #[serde(default)]
    pub foley_cue: Option<String>, // MMAudio / SFX cue
    #[serde(default)]
    pub bgm_mood: Option<String>, // ACE-Step / YuE BGM mood tag
    // Universal MiniMax-H3 v2.5 / V9 & POSE-DB-01 (1,439 Poses) Fields
    #[serde(default)]
    pub keyframes: Vec<String>, // Physical keyframe image paths for 17k multi-keyframe conditioning
    #[serde(default)]
    pub pose_anchors: Vec<String>, // e.g. ["full_single_P011_front", "full_single_P004_diag"]
    #[serde(default)]
    pub keyframe_indices: Vec<i32>, // 17k phase-aligned frame indices: [0, 51, 85]
    #[serde(default)]
    pub keyframe_strengths: Vec<f32>, // per-keyframe conditioning strengths: [1.0, 0.88, 0.90]
    #[serde(default)]
    pub continuity_track: Option<String>, // "track_a_latent_relay" (22f MotionContext) or "track_b_hard_cut"
    #[serde(default)]
    pub tail_lock_v9: Option<bool>, // V9 Dual-End TailLock (`[68, 85]` or `[107, 136]`)
    #[serde(default)]
    pub emotion_mode: Option<String>, // "natural" | "t8mars_explosive" | "t8mars_fury" | "t8mars_weeping"
    #[serde(default)]
    pub character_card: Option<String>, // "Name|Role Title" for staggered glassmorphic intro card
    // Master-Stage Spatial Blocking & Multi-Character Continuity Fields
    #[serde(default)]
    pub master_stage_id: Option<String>,
    #[serde(default)]
    pub sub_framing_rect: Option<Vec<f64>>,
    #[serde(default)]
    pub visible_characters: Vec<String>,
    #[serde(default)]
    pub prop_state_ledger: BTreeMap<String, String>,
    #[serde(default)]
    pub dialogue_turns: Vec<DialogueTurn>,
    // 4-Beat Micro-Acting & Detail Density Fields
    #[serde(default)]
    pub micro_beats: Vec<String>, // explicit 4-beat temporal descriptions
    #[serde(default)]
    pub facial_progression: Option<String>, // concrete facial muscle progression: brow glabella, lower eyelids, nostrils, jaw masseter, lip corner
    #[serde(default)]
    pub prop_interaction: Option<String>, // tactile hand & prop interaction
    #[serde(default)]
    pub listener_reaction: Option<String>, // non-speaking character's physiological reaction
    #[serde(default)]
    pub env_micro_physics: Option<String>, // candle wick, rain droplets, breath mist, fabric sway
    #[serde(default)]
    pub sub_beat_emotions: Vec<String>, // intra-line multi-emotion arc for TTS, e.g. ["cold_laugh:0.45", "pause:350ms", "angry:0.65"]
}

fn default_framing() -> String {
    "medium".to_string()
}
fn default_aspect() -> String {
    "16:9".to_string()
}
fn default_duration() -> u32 {
    8
}
fn default_model() -> String {
    "veo-quality".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EpisodeSummary {
    pub id: String,
    pub episode_number: u32,
    pub dir_name: String,
    pub title: String,
    pub scene_count: usize,
    pub lint_passed: bool,
    pub error_count: usize,
    pub warning_count: usize,
    pub final_videos: Vec<MediaFileEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MediaFileEntry {
    pub name: String,
    pub rel_path: String,
    pub url: String,
    pub size_bytes: u64,
    pub engine_tag: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectSummary {
    pub id: String,
    pub name: String,
    pub subtitle: String,
    pub aspect: String,
    pub episode_count: usize,
    pub character_count: usize,
    pub room_count: usize,
    pub image_count: usize,
    pub video_count: usize,
    pub is_active: bool,
}
