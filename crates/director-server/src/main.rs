#![recursion_limit = "512"]

use std::convert::Infallible;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::time::Duration;

use axum::{
    extract::{ConnectInfo, Multipart, Path as AxumPath, Request, State},
    http::{header, HeaderMap, StatusCode},
    middleware::{self, Next},
    response::{
        sse::{Event, KeepAlive, Sse},
        Html, IntoResponse, Json, Response,
    },
    routing::{delete, get, post, put},
    Router,
};
use director_core::{
    agent_plugin::{
        current_os, AgentPluginManifest, AgentPluginRegistry, AgentTaskRequest, AgentTaskResponse,
    },
    config::{builtin_style_presets, builtin_voice_presets},
    llm_assistant::{AiStoryboardRequest, AiWriterAssistant},
    AcousticSpace, CharacterProfile, ContinuityProp, DirectorLinter, EpisodeSummary, FactSheet,
    LintReport, MasteringEngine, MediaFileEntry, MovieManifest, ProfilesToml, ProjectMeta,
    ProjectSummary, SceneSpec, SpatialRoom, StoryboardCompiler, StyleLock, WorkspacePaths,
};
use director_engines::{
    ColabBridgeRunner, CreditReport, FlowEngine, FlowMusicEngine, H3Engine, JobStatus,
    LaneUtilization, LocalGpuStatus, MusicGenerateResult, ParallelConcurrencyConfig, RenderJob,
    RenderQueue, SumeEngine,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt;
use tower_http::{cors::CorsLayer, services::ServeDir};

mod mcp;
mod ui;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentDemandItem {
    pub id: String,
    pub created_at: String,
    pub member_name: String,
    pub episode_id: String,
    pub scene_id: Option<String>,
    pub demand_text: String,
    pub status: String,
    pub agent_reply: Option<String>,
}

#[derive(Clone)]
pub struct AppState {
    pub root_dir: std::path::PathBuf,
    pub active_project: Arc<RwLock<String>>,
    pub flow_engine: FlowEngine,
    pub flow_music_engine: FlowMusicEngine,
    pub h3_engine: H3Engine,
    pub sume_engine: SumeEngine,
    pub queue: RenderQueue,
    pub admin_pin: String,
    pub web_password: String,
    pub session_token: String,
    pub port: u16,
    pub agent_conversation_id: Arc<RwLock<String>>,
    pub agent_demands: Arc<RwLock<Vec<AgentDemandItem>>>,
    pub agent_registry: Arc<RwLock<AgentPluginRegistry>>,
    pub colab_runner: ColabBridgeRunner,
}

impl AppState {
    pub async fn current_paths(&self) -> WorkspacePaths {
        let proj = std::fs::read_to_string(self.root_dir.join(".active_project"))
            .ok()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        if let Some(p) = proj {
            let mut active = self.active_project.write().await;
            if *active != p {
                *active = p.clone();
            }
            return WorkspacePaths::for_project(&self.root_dir, &p);
        }
        let proj = self.active_project.read().await.clone();
        WorkspacePaths::for_project(&self.root_dir, &proj)
    }
}

fn resolve_workspace_root() -> std::path::PathBuf {
    if let Ok(cwd) = std::env::current_dir() {
        if cwd.join("fact_sheet.toml").exists() {
            return cwd;
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(p) = exe.parent().and_then(|p| p.parent()).and_then(|p| p.parent()) {
            if p.join("fact_sheet.toml").exists() {
                return p.to_path_buf();
            }
        }
    }
    std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."))
}

#[derive(Debug, Deserialize)]
struct LoginRequest {
    password: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColabEstimates {
    pub g4_video_hours: f64,
    pub estimated_video_minutes: f64,
    pub l4_audio_hours: f64,
    pub estimated_audio_minutes: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColabQuotaSummary {
    pub tier: String,
    pub remaining_ccu: f64,
    pub total_pool_ccu: f64,
    pub percentage: f64,
    pub burn_rate: f64,
    pub active_assignments: i64,
    pub expires_at: String,
    pub days_remaining: i64,
    pub refreshes_at: String,
    pub refresh_countdown: String,
    pub estimates: ColabEstimates,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowVideoEstimates {
    pub veo_fast_shots: i64,
    pub estimated_fast_video_minutes: f64,
    pub estimated_fast_video_seconds: i64,
    pub veo_quality_shots: i64,
    pub estimated_quality_video_minutes: f64,
    pub estimated_quality_video_seconds: i64,
    pub nano_pro_images: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowVideoQuotaSummary {
    pub tier: String,
    pub account: String,
    pub remaining_credits: i64,
    pub total_credits: i64,
    pub percentage: f64,
    pub last_spent: Option<i64>,
    pub expires_at: String,
    pub days_remaining: i64,
    pub refreshes_at: String,
    pub refresh_countdown: String,
    pub estimates: FlowVideoEstimates,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowMusicEstimates {
    pub estimated_music_minutes: f64,
    pub estimated_sfx_count: i64,
    pub ace_step_unlimited: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowMusicQuotaSummary {
    pub tier: String,
    pub daily_quota_tracks: i64,
    pub daily_remaining_tracks: i64,
    pub daily_used_tracks: i64,
    pub credits_deduction: i64,
    pub expires_at: String,
    pub days_remaining: i64,
    pub refreshes_at: String,
    pub refresh_countdown: String,
    pub estimates: FlowMusicEstimates,
    pub local_engine_status: String,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuotaSummaryResponse {
    pub colab: ColabQuotaSummary,
    pub flow_video: FlowVideoQuotaSummary,
    pub flow_music: FlowMusicQuotaSummary,
    pub lane_utilization: LaneUtilization,
    pub concurrency_config: ParallelConcurrencyConfig,
    pub updated_at: String,
}

#[derive(Debug, Serialize)]
struct ConcurrencyStatusResponse {
    config: ParallelConcurrencyConfig,
    utilization: LaneUtilization,
}

#[derive(Debug, Deserialize)]
pub struct MusicGenerateRequest {
    pub prompt: String,
    pub mood: Option<String>,
    pub duration_sec: Option<f64>,
    pub output_filename: Option<String>,
}

#[derive(Debug, Serialize)]
struct SystemStatusResponse {
    studio_name: String,
    active_project_id: String,
    project_name: String,
    historical_anchor: String,
    credits: CreditReport,
    local_gpu: LocalGpuStatus,
    require_approval_for_quality: bool,
    daily_credit_limit: i64,
    active_jobs_count: usize,
    pending_approvals_count: usize,
    agent_conversation_id: String,
    quota_summary: QuotaSummaryResponse,
    lane_utilization: LaneUtilization,
    concurrency_config: ParallelConcurrencyConfig,
}

#[derive(Debug, Serialize)]
struct EpisodeDetailResponse {
    id: String,
    dir_name: String,
    title: String,
    script_markdown: String,
    scenes: Vec<SceneSpec>,
    lint_report: LintReport,
    scene_media: std::collections::BTreeMap<String, Vec<MediaFileEntry>>,
    final_videos: Vec<MediaFileEntry>,
}

#[derive(Debug, Deserialize)]
struct SaveScenesRequest {
    title: String,
    scenes: Vec<SceneSpec>,
}

#[derive(Debug, Deserialize)]
struct PolishSceneRequest {
    scene: SceneSpec,
    chinese_visual_hint: Option<String>,
}

#[derive(Debug, Serialize)]
struct PolishSceneResponse {
    scene: SceneSpec,
    notes: Vec<String>,
    lint_report: LintReport,
}

#[derive(Debug, Deserialize)]
struct SubmitRenderRequest {
    requested_by: Option<String>,
    episode_id: String,
    scene_id: Option<String>,
    model: String,
    dry_run: Option<bool>,
    admin_pin: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ApproveJobRequest {
    admin_pin: Option<String>,
    approve: bool,
}

#[derive(Debug, Deserialize)]
struct CreateEpisodeRequest {
    dir_name: String,
    title: String,
    story_idea: String,
    preferred_model: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CreateCharacterRequest {
    name: String,
    #[serde(default)]
    tier: Option<String>,
    appearance: String,
    appearance_modern: Option<String>,
    appearance_ancient: Option<String>,
    voice: Option<String>,
    ref_image: Option<String>,
    ref_image_modern: Option<String>,
    ref_image_ancient: Option<String>,
    turnaround_ref_image: Option<String>,
    costume_version: Option<String>,
}

#[derive(Debug, Deserialize)]
struct UpsertPropRequest {
    prop_id: String,
    name: String,
    category: Option<String>,
    description: String,
    ref_image: Option<String>,
    version_tag: Option<String>,
    owner_character: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ApplyStylePresetRequest {
    preset_id: String,
    production_mode: Option<String>,
    no_subtitles_lock: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct CreateProjectRequest {
    id: String,
    name: String,
    subtitle: Option<String>,
    aspect: Option<String>,
    camera_base: Option<String>,
    lighting_base: Option<String>,
}

#[derive(Debug, Deserialize)]
struct SelectProjectRequest {
    project_id: String,
}

#[derive(Debug, Deserialize)]
struct UpsertRoomRequest {
    room_id: String,
    description: String,
    camera_left: String,
    center_foreground: String,
    camera_right: String,
    exterior_anchor_image: Option<String>,
    interior_anchor_image: Option<String>,
}

#[derive(Debug, Deserialize)]
struct UpsertAcousticRequest {
    space_id: String,
    description: String,
    ffmpeg_bg_filter: String,
    h3_audio_cue: String,
}

#[derive(Debug, Deserialize)]
struct UpdateGuardPolicyRequest {
    require_approval_for_quality: bool,
    daily_credit_limit: i64,
    agent_conversation_id: Option<String>,
}

#[derive(Debug, Deserialize)]
struct SaveScriptRequest {
    script_markdown: String,
}

#[derive(Debug, Deserialize)]
struct SubmitAgentDemandRequest {
    member_name: Option<String>,
    episode_id: String,
    scene_id: Option<String>,
    demand_text: String,
    preferred_plugin: Option<String>,
}

#[derive(Debug, Deserialize)]
struct RegisterPluginRequest {
    manifest: AgentPluginManifest,
}

#[derive(Debug, Deserialize)]
struct AgentDispatchRequest {
    task_type: Option<String>,
    prompt: String,
    preferred_plugin: Option<String>,
    workspace_dir: Option<String>,
    conversation_id: Option<String>,
}

#[derive(Debug, Deserialize)]
struct VideoCriticRequest {
    video_path: String,
}

#[derive(Debug, Deserialize)]
struct McpWebhookPayload {
    episode_id: String,
    message: String,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "mcp-stdio" || a == "--mcp-stdio") {
        let base_dir = resolve_workspace_root();
        return mcp::run_mcp_stdio(base_dir).await;
    }
    if let Some(pos) = args.iter().position(|a| a == "cli" || a == "--cli") {
        let base_dir = resolve_workspace_root();
        let tool_name = args
            .get(pos + 1)
            .cloned()
            .unwrap_or_else(|| "studio_list_projects".to_string());
        let json_arg = args.get(pos + 2).cloned().unwrap_or_else(|| "{}".to_string());
        let parsed_args: serde_json::Value =
            serde_json::from_str(&json_arg).unwrap_or_else(|_| serde_json::json!({}));
        let active_proj = WorkspacePaths::resolve_active_project_id(&base_dir);
        let paths = WorkspacePaths::for_project(&base_dir, &active_proj);
        let req = serde_json::json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parsed_args,
            }
        });
        if let Some(resp) = mcp::handle_mcp_jsonrpc(&paths, req).await {
            if let Some(text) = resp
                .pointer("/result/content/0/text")
                .and_then(|v| v.as_str())
            {
                println!("{}", text);
            } else {
                println!("{}", serde_json::to_string_pretty(&resp)?);
            }
        }
        return Ok(());
    }

    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "director_server=info,tower_http=info".into()),
        )
        .init();

    let base_dir = resolve_workspace_root();
    let initial_proj = WorkspacePaths::resolve_active_project_id(&base_dir);
    let paths = WorkspacePaths::for_project(&base_dir, &initial_proj);
    paths.ensure_dirs()?;

    let admin_pin = std::env::var("DIRECTOR_ADMIN_PIN").unwrap_or_else(|_| "2280".to_string());
    let web_password =
        std::env::var("DIRECTOR_PASSWORD").unwrap_or_else(|_| "duanshipin123".to_string());
    let session_token = format!("studio_auth_{:x}", md5_like_hash(&web_password));
    let port: u16 = std::env::var("DIRECTOR_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(18443);
    let conv_id = std::env::var("ANTIGRAVITY_CONVERSATION_ID")
        .unwrap_or_else(|_| mcp::DEFAULT_CONVERSATION_ID.to_string());

    let mut reg = AgentPluginRegistry::new();
    let plugins_dir = base_dir.join("plugins").join("agents");
    let loaded_count = reg.load_from_dir(&plugins_dir);
    tracing::info!(
        "Discovered {} agent plugins ({} loaded from {})",
        reg.list_plugins().len(),
        loaded_count,
        plugins_dir.display()
    );
    let agent_registry = Arc::new(RwLock::new(reg));
    let colab_runner = ColabBridgeRunner::new(&base_dir);

    let state = AppState {
        root_dir: base_dir.clone(),
        active_project: Arc::new(RwLock::new(initial_proj)),
        flow_engine: FlowEngine::new(&base_dir),
        flow_music_engine: FlowMusicEngine::new(&base_dir),
        h3_engine: H3Engine::new(&base_dir),
        sume_engine: SumeEngine::new(&base_dir),
        queue: RenderQueue::new(),
        admin_pin,
        web_password,
        session_token,
        port,
        agent_conversation_id: Arc::new(RwLock::new(conv_id)),
        agent_demands: Arc::new(RwLock::new(Vec::new())),
        agent_registry,
        colab_runner,
    };

    // Nest static file serving with automatic HTTP 206 Partial Content Range support for Safari / WeChat / NAS
    let app = Router::new()
        .route("/", get(serve_index))
        .route("/api/v1/auth/login", post(api_auth_login))
        .route("/api/v1/auth/logout", post(api_auth_logout))
        .route("/api/v1/auth/check", get(api_auth_check))
        .route("/mcp", post(api_mcp_http))
        .route("/api/v1/mcp", post(api_mcp_http))
        .route("/api/v1/plugins", get(api_list_plugins))
        .route("/api/v1/plugins/register", post(api_register_plugin))
        .route("/api/v1/agent/dispatch", post(api_agent_dispatch))
        .route("/api/v1/critic/evaluate", post(api_critic_evaluate))
        .route("/api/v1/projects", get(api_list_projects).post(api_create_project))
        .route("/api/v1/projects/select", post(api_select_project))
        .route("/api/v1/system/status", get(api_system_status))
        .route("/api/v1/system/policy", put(api_update_policy))
        .route("/api/v1/quota/summary", get(api_quota_summary))
        .route("/api/v1/queue/concurrency", get(api_get_concurrency).post(api_update_concurrency))
        .route("/api/v1/music/generate", post(api_generate_music))
        .route("/api/v1/episodes", get(api_list_episodes).post(api_create_episode))
        .route("/api/v1/episodes/:id", get(api_get_episode))
        .route("/api/v1/episodes/:id/scenes", put(api_save_episode_scenes))
        .route("/api/v1/episodes/:id/script", put(api_save_episode_script))
        .route("/api/v1/episodes/:id/compile-seedance", get(api_compile_seedance_episode))
        .route("/api/v1/episodes/:id/export-jianying", post(api_export_jianying_draft))
        .route("/api/v1/agent/demand", get(api_list_agent_demands).post(api_submit_agent_demand))
        .route("/api/v1/agent/mcp-webhook", post(api_mcp_webhook))
        .route("/api/v1/ai/generate-storyboard", post(api_ai_generate_storyboard))
        .route("/api/v1/ai/polish-scene", post(api_ai_polish_scene))
        .route("/api/v1/assets", get(api_get_assets))
        .route("/api/v1/assets/characters", post(api_create_character))
        .route("/api/v1/assets/characters/:name", delete(api_delete_character))
        .route("/api/v1/assets/props", post(api_upsert_prop))
        .route("/api/v1/assets/props/:id", delete(api_delete_prop))
        .route("/api/v1/assets/style-preset", post(api_apply_style_preset))
        .route("/api/v1/assets/rooms", post(api_upsert_room))
        .route("/api/v1/assets/rooms/:id", delete(api_delete_room))
        .route("/api/v1/assets/acoustics", post(api_upsert_acoustic))
        .route("/api/v1/assets/style-lock", put(api_update_style_lock))
        .route("/api/v1/assets/upload-image", post(api_upload_image))
        .route("/api/v1/assets/images/:name", delete(api_delete_image))
        .route("/api/v1/render/jobs", get(api_list_jobs).post(api_submit_render))
        .route("/api/v1/render/jobs/:id/approve", post(api_approve_job))
        .route("/api/v1/events/stream", get(api_sse_events))
        .nest_service("/media/voices", ServeDir::new(base_dir.join("assets").join("voices")))
        .nest_service("/media/characters", ServeDir::new(base_dir.join("characters")))
        .nest_service("/media/output", ServeDir::new(base_dir.join("output")))
        .nest_service("/media/projects", ServeDir::new(base_dir.join("projects")))
        .nest_service("/media/renders", ServeDir::new(base_dir.join("assets").join("renders")))
        .layer(middleware::from_fn_with_state(state.clone(), auth_middleware))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("=====================================================================");
    tracing::info!("🎬 {} 已启动!", director_core::config::SYSTEM_TITLE_CN);
    tracing::info!("🌐 本机访问地址: http://127.0.0.1:{}", port);
    tracing::info!("🌍 公网访问地址: https://studio.hackerlife.fun:8443");
    tracing::info!("🔒 网页访问登录密码 (DIRECTOR_PASSWORD): duanshipin123");
    tracing::info!("🔑 默认家庭精修审批口令 (DIRECTOR_ADMIN_PIN): 2280");
    tracing::info!("=====================================================================");

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;
    Ok(())
}

fn md5_like_hash(input: &str) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    director_core::config::SYSTEM_AUTH_SALT.hash(&mut hasher);
    input.hash(&mut hasher);
    hasher.finish()
}

fn is_request_authenticated(headers: &HeaderMap, expected_token: &str) -> bool {
    if let Some(auth_val) = headers.get(header::AUTHORIZATION).and_then(|v| v.to_str().ok()) {
        if auth_val.trim() == format!("Bearer {}", expected_token) {
            return true;
        }
    }
    if let Some(cookie_str) = headers.get(header::COOKIE).and_then(|v| v.to_str().ok()) {
        for part in cookie_str.split(';') {
            let kv = part.trim();
            if let Some(val) = kv.strip_prefix("director_session=") {
                if val.trim() == expected_token {
                    return true;
                }
            }
        }
    }
    false
}

async fn auth_middleware(
    State(state): State<AppState>,
    ConnectInfo(peer_addr): ConnectInfo<SocketAddr>,
    req: Request,
    next: Next,
) -> Response {
    let path = req.uri().path();
    // Always allow the login UI shell (`/`) and auth endpoints
    if path == "/" || path.starts_with("/api/v1/auth/") {
        return next.run(req).await;
    }
    // Allow local loopback (127.0.0.1 / ::1) MCP and webhook calls without browser cookie if not forwarded from NAS proxy
    let is_proxied = req.headers().contains_key("x-forwarded-for")
        || req.headers().contains_key("cf-connecting-ip");
    if peer_addr.ip().is_loopback()
        && !is_proxied
        && (path == "/mcp"
            || path == "/api/v1/mcp"
            || path == "/api/v1/agent/mcp-webhook"
            || path == "/api/v1/quota/summary"
            || path == "/api/v1/music/generate"
            || path == "/api/v1/queue/concurrency")
    {
        return next.run(req).await;
    }

    if is_request_authenticated(req.headers(), &state.session_token) {
        return next.run(req).await;
    }

    (
        StatusCode::UNAUTHORIZED,
        Json(serde_json::json!({
            "error": "unauthorized",
            "message": "请先输入家庭访问密码登录工作台"
        })),
    )
        .into_response()
}

async fn api_auth_login(
    State(state): State<AppState>,
    Json(req): Json<LoginRequest>,
) -> Response {
    if req.password.trim() == state.web_password {
        let cookie = format!(
            "director_session={}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax",
            state.session_token
        );
        (
            StatusCode::OK,
            [(header::SET_COOKIE, cookie)],
            Json(serde_json::json!({
                "ok": true,
                "token": state.session_token
            })),
        )
            .into_response()
    } else {
        (
            StatusCode::UNAUTHORIZED,
            Json(serde_json::json!({
                "ok": false,
                "message": "访问密码不正确，请重试"
            })),
        )
            .into_response()
    }
}

async fn api_auth_logout() -> Response {
    let cookie = "director_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax";
    (
        StatusCode::OK,
        [(header::SET_COOKIE, cookie)],
        Json(serde_json::json!({ "ok": true })),
    )
        .into_response()
}

async fn api_auth_check(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Json<serde_json::Value> {
    let authenticated = is_request_authenticated(&headers, &state.session_token);
    Json(serde_json::json!({ "authenticated": authenticated }))
}

async fn serve_index() -> Html<&'static str> {
    Html(ui::INDEX_HTML)
}

async fn api_system_status(State(state): State<AppState>) -> Json<SystemStatusResponse> {
    let paths = state.current_paths().await;
    let linter = DirectorLinter::new(&paths.base_dir);
    let credits = state.flow_engine.get_credits_and_status().await;
    let local_gpu = state.h3_engine.check_system();
    let jobs = state.queue.jobs.read().await;
    let active_jobs_count = jobs
        .iter()
        .filter(|j| matches!(j.status, JobStatus::Queued | JobStatus::Running))
        .count();
    let pending_approvals_count = jobs
        .iter()
        .filter(|j| j.status == JobStatus::PendingApproval)
        .count();
    let quota_summary = build_quota_summary(&state).await;
    let lane_utilization = state.queue.get_lane_utilization().await;
    let concurrency_config = state.queue.concurrency_config.read().await.clone();

    Json(SystemStatusResponse {
        studio_name: director_core::config::SYSTEM_TITLE_CN.to_string(),
        active_project_id: paths.active_project_id.clone(),
        project_name: if linter.fact_sheet.project.name.is_empty() {
            paths.active_project_id.clone()
        } else {
            linter.fact_sheet.project.name
        },
        historical_anchor: linter.fact_sheet.project.historical_anchor_year,
        credits,
        local_gpu,
        require_approval_for_quality: *state.queue.require_approval_for_quality.read().await,
        daily_credit_limit: *state.queue.daily_credit_limit_per_member.read().await,
        active_jobs_count,
        pending_approvals_count,
        agent_conversation_id: state.agent_conversation_id.read().await.clone(),
        quota_summary,
        lane_utilization,
        concurrency_config,
    })
}

async fn query_colab_usage(workspace_root: &std::path::Path) -> (f64, f64, i64, &'static str) {
    let colab_bin = director_engines::resolve_colab_bin();
    if let Some(bin) = colab_bin {
        let mut cmd = tokio::process::Command::new(bin);
        cmd.arg("usage");
        let timeout_fut = tokio::time::timeout(Duration::from_secs(5), cmd.output());
        if let Ok(Ok(out)) = timeout_fut.await {
            if out.status.success() {
                let stdout = String::from_utf8_lossy(&out.stdout);
                let mut balance = None;
                let mut rate = 0.0f64;
                let mut active = 0i64;
                for line in stdout.lines() {
                    let l = line.trim();
                    if l.starts_with("Current balance:") {
                        let parts: Vec<&str> = l.split_whitespace().collect();
                        if parts.len() >= 3 {
                            if let Ok(val) = parts[2].parse::<f64>() {
                                balance = Some(val);
                            }
                        }
                    } else if l.starts_with("Usage rate:") {
                        let parts: Vec<&str> = l.split_whitespace().collect();
                        if parts.len() >= 3 {
                            let r_str = parts[2].trim_end_matches("/hr");
                            if let Ok(val) = r_str.parse::<f64>() {
                                rate = val;
                            }
                        }
                    } else if l.starts_with("Active assignments:") {
                        let parts: Vec<&str> = l.split_whitespace().collect();
                        if parts.len() >= 3 {
                            if let Ok(val) = parts[2].parse::<i64>() {
                                active = val;
                            }
                        }
                    }
                }
                if let Some(bal) = balance {
                    return (bal, rate, active, "live colab CLI");
                }
            }
        }
    }

    let cache_p = workspace_root.join("colab_quota_cache.json");
    if cache_p.exists() {
        if let Ok(raw) = std::fs::read_to_string(&cache_p) {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&raw) {
                let bal = val.get("balance").and_then(|v| v.as_f64()).unwrap_or(1873.15);
                let rate = val.get("burn_rate").and_then(|v| v.as_f64()).unwrap_or(0.0);
                let active = val.get("active_assignments").and_then(|v| v.as_i64()).unwrap_or(0);
                return (bal, rate, active, "cached colab_quota_cache.json");
            }
        }
    }

    (1873.15, 0.0, 0, "default cache")
}

async fn build_quota_summary(state: &AppState) -> QuotaSummaryResponse {
    let now = chrono::Utc::now();
    let now_cst = now.with_timezone(&chrono::FixedOffset::east_opt(8 * 3600).unwrap());

    // 1. Colab
    let (colab_bal, burn_rate, active_assigns, colab_source) = query_colab_usage(&state.root_dir).await;
    let colab_total_pool = 2000.0f64;
    let colab_pct = ((colab_bal / colab_total_pool) * 100.0 * 10.0).round() / 10.0;

    let expires_ts = 1796054400i64; // 2026-12-01 00:00:00 UTC+8
    let days_remaining = ((expires_ts - now.timestamp()).max(0) / 86400).max(1);

    let g4_hours = ((colab_bal / 8.71) * 10.0).round() / 10.0;
    let est_video_mins = ((g4_hours * 6.0) * 10.0).round() / 10.0;
    let l4_hours = ((colab_bal / 1.71) * 10.0).round() / 10.0;
    let est_audio_mins = ((l4_hours * 150.0) * 10.0).round() / 10.0;

    let colab = ColabQuotaSummary {
        tier: "Google AI Ultra (Pro/Ultra Plan)".to_string(),
        remaining_ccu: (colab_bal * 100.0).round() / 100.0,
        total_pool_ccu: colab_total_pool,
        percentage: colab_pct,
        burn_rate,
        active_assignments: active_assigns,
        expires_at: "2026-12-01 00:00:00 UTC+8".to_string(),
        days_remaining,
        refreshes_at: "每月 1 日 16:00 CST (00:00 PT) 自动重置 +1,000~2,000 CCU".to_string(),
        refresh_countdown: format!("{}天后自动重置", days_remaining),
        estimates: ColabEstimates {
            g4_video_hours: g4_hours,
            estimated_video_minutes: est_video_mins,
            l4_audio_hours: l4_hours,
            estimated_audio_minutes: est_audio_mins,
        },
        source: colab_source.to_string(),
    };

    // 2. Google Flow Video & Image
    let flow_credits = state.flow_engine.get_credits_and_status().await;
    let flow_bal = flow_credits.balance;
    let flow_total = 10000i64;
    let flow_pct = (((flow_bal as f64 / flow_total as f64) * 100.0) * 100.0).round() / 100.0;
    let veo_fast = flow_bal / 10;
    let veo_quality = flow_bal / 100;
    let fast_sec = veo_fast * 8;
    let quality_sec = veo_quality * 8;
    let fast_min = ((fast_sec as f64 / 60.0) * 10.0).round() / 10.0;
    let quality_min = ((quality_sec as f64 / 60.0) * 10.0).round() / 10.0;

    let flow_account = std::env::var("GFLOW_ACCOUNT").unwrap_or_else(|_| "jl.kingbright@gmail.com".to_string());
    let flow_video = FlowVideoQuotaSummary {
        tier: "Google AI Ultra (TIER_ULTRA)".to_string(),
        account: flow_account,
        remaining_credits: flow_bal,
        total_credits: flow_total,
        percentage: flow_pct,
        last_spent: flow_credits.last_spent,
        expires_at: "2026-12-01 00:00:00 UTC+8".to_string(),
        days_remaining,
        refreshes_at: "每月 1 日 16:00 CST 自动补满 10,000 Credits".to_string(),
        refresh_countdown: flow_credits.refresh_countdown.clone(),
        estimates: FlowVideoEstimates {
            veo_fast_shots: veo_fast,
            estimated_fast_video_minutes: fast_min,
            estimated_fast_video_seconds: fast_sec,
            veo_quality_shots: veo_quality,
            estimated_quality_video_minutes: quality_min,
            estimated_quality_video_seconds: quality_sec,
            nano_pro_images: "0 Credits/张 (无限免费 ∞ 张)".to_string(),
        },
        source: if flow_credits.success { "credits_cache.json / session" } else { "default cache" }.to_string(),
    };

    // 3. Google Flow Music
    let music_status = state.flow_music_engine.get_quota_status().await;
    let flow_music = FlowMusicQuotaSummary {
        tier: music_status.tier,
        daily_quota_tracks: music_status.daily_quota_tracks,
        daily_remaining_tracks: music_status.daily_remaining_tracks,
        daily_used_tracks: music_status.daily_used_tracks,
        credits_deduction: 0,
        expires_at: music_status.expires_at,
        days_remaining,
        refreshes_at: music_status.refreshes_at,
        refresh_countdown: music_status.refresh_countdown,
        estimates: FlowMusicEstimates {
            estimated_music_minutes: music_status.estimates.estimated_music_minutes,
            estimated_sfx_count: music_status.estimates.estimated_sfx_count,
            ace_step_unlimited: true,
        },
        local_engine_status: music_status.local_engine_status,
        source: if music_status.has_oauth_token { "Google Labs OAuth Session" } else { "Local ACE-Step 1.5 + Curated Studio Engine" }.to_string(),
    };

    let lane_utilization = state.queue.get_lane_utilization().await;
    let concurrency_config = state.queue.concurrency_config.read().await.clone();

    QuotaSummaryResponse {
        colab,
        flow_video,
        flow_music,
        lane_utilization,
        concurrency_config,
        updated_at: now_cst.format("%Y-%m-%d %H:%M:%S CST").to_string(),
    }
}

async fn api_quota_summary(State(state): State<AppState>) -> Json<QuotaSummaryResponse> {
    let summary = build_quota_summary(&state).await;
    Json(summary)
}

async fn api_get_concurrency(State(state): State<AppState>) -> Json<ConcurrencyStatusResponse> {
    let config = state.queue.concurrency_config.read().await.clone();
    let utilization = state.queue.get_lane_utilization().await;
    Json(ConcurrencyStatusResponse { config, utilization })
}

async fn api_update_concurrency(
    State(state): State<AppState>,
    Json(req): Json<ParallelConcurrencyConfig>,
) -> Json<serde_json::Value> {
    state.queue.update_concurrency_config(req).await;
    let utilization = state.queue.get_lane_utilization().await;
    Json(serde_json::json!({
        "ok": true,
        "message": "并发通道调度池配置已更新",
        "utilization": utilization
    }))
}

async fn api_generate_music(
    State(state): State<AppState>,
    Json(req): Json<MusicGenerateRequest>,
) -> Result<Json<MusicGenerateResult>, (StatusCode, String)> {
    let mood = req.mood.as_deref().unwrap_or("epic");
    let dur = req.duration_sec.unwrap_or(15.0).clamp(1.0, 180.0);
    let paths = state.current_paths().await;
    let filename = req.output_filename.unwrap_or_else(|| {
        format!("bgm_{}_{}.wav", mood, uuid::Uuid::new_v4().simple())
    });
    let out_path = paths.base_dir.join("assets").join("renders").join(filename);
    if let Some(parent) = out_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    }

    let res = state
        .flow_music_engine
        .generate_bgm(&req.prompt, mood, dur, &out_path)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    Ok(Json(res))
}

fn build_project_summary(paths: &WorkspacePaths, active_id: &str) -> ProjectSummary {
    let linter = DirectorLinter::new(&paths.base_dir);
    let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);

    let episode_count = std::fs::read_dir(&paths.episodes_dir)
        .map(|entries| {
            entries
                .flatten()
                .filter(|e| e.path().is_dir() && e.path().join("movie.toml").exists())
                .count()
        })
        .unwrap_or(0);

    let image_count = std::fs::read_dir(&paths.characters_images_dir)
        .map(|entries| entries.flatten().filter(|e| e.path().is_file()).count())
        .unwrap_or(0);

    let final_vids = scan_final_videos(paths).len();
    let mut raw_vids = 0;
    if let Ok(ep_dirs) = std::fs::read_dir(&paths.raw_clips_dir) {
        for ep in ep_dirs.flatten() {
            if let Ok(files) = std::fs::read_dir(ep.path()) {
                raw_vids += files
                    .flatten()
                    .filter(|f| {
                        f.path()
                            .extension()
                            .map(|x| x.to_string_lossy().to_lowercase() == "mp4")
                            .unwrap_or(false)
                    })
                    .count();
            }
        }
    }

    ProjectSummary {
        id: paths.active_project_id.clone(),
        name: if linter.fact_sheet.project.name.is_empty() {
            paths.active_project_id.clone()
        } else {
            linter.fact_sheet.project.name
        },
        subtitle: linter.fact_sheet.project.historical_anchor_year,
        aspect: if linter.fact_sheet.project.episode_aspect.is_empty() {
            "16:9".to_string()
        } else {
            linter.fact_sheet.project.episode_aspect
        },
        episode_count,
        character_count: compiler.characters.len(),
        room_count: linter.fact_sheet.spatial_rooms.len(),
        image_count,
        video_count: final_vids + raw_vids,
        is_active: paths.active_project_id == active_id,
    }
}

async fn api_list_projects(State(state): State<AppState>) -> Json<Vec<ProjectSummary>> {
    let active_id = state.active_project.read().await.clone();
    let list = WorkspacePaths::discover_all_projects(&state.root_dir)
        .into_iter()
        .map(|p_paths| build_project_summary(&p_paths, &active_id))
        .collect();
    Json(list)
}

async fn api_create_project(
    State(state): State<AppState>,
    Json(req): Json<CreateProjectRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let safe_id: String = req
        .id
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
        .collect::<String>()
        .to_lowercase();
    let project_id = if safe_id.is_empty() {
        format!("proj_{}", chrono::Utc::now().timestamp() % 10000)
    } else {
        safe_id
    };

    let paths = WorkspacePaths::for_project(&state.root_dir, &project_id);
    paths
        .ensure_dirs()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    if !paths.fact_sheet_file.exists() {
        let mut fs = FactSheet::default();
        fs.project = ProjectMeta {
            id: project_id.clone(),
            name: req.name.clone(),
            pipeline_type: "AI_Studio_L1_L5".to_string(),
            episode_aspect: req.aspect.unwrap_or_else(|| "16:9".to_string()),
            historical_anchor_year: req
                .subtitle
                .unwrap_or_else(|| "AI 影视创作项目".to_string()),
            production_mode: "cinematic_drama".to_string(),
            style_preset: "live_action_arri".to_string(),
            no_subtitles_lock: true,
        };
        fs.style_lock = StyleLock {
            camera_base: req.camera_base.unwrap_or_else(|| {
                "Shot on ARRI Alexa 65, Panavision Primo 70mm anamorphic lens, shallow depth of field".to_string()
            }),
            lighting_base: req.lighting_base.unwrap_or_else(|| {
                "Naturalistic cinematic lighting, volumetric atmospheric haze, rich dynamic range".to_string()
            }),
            film_stock: "35mm Kodak Vision3 500T film grain".to_string(),
            global_suffix: "photorealistic live-action cinema, 8k raw footage".to_string(),
            modern_suffix: "contemporary realistic cinematography, clean natural skin texture".to_string(),
            negative_prompt: "3D render, CGI, anime, cartoon, plastic skin, watermark, subtitles".to_string(),
        };
        fs.director_rules.psychological_arc_phases = vec![
            "P1_Hook_Tension".to_string(),
            "P2_Escalation".to_string(),
            "P3_Climax_Turn".to_string(),
            "P4_Resolution".to_string(),
        ];
        fs.spatial_rooms.insert(
            "main_studio_set".to_string(),
            SpatialRoom {
                description: "主场景默认三维空间拓扑（可在资产中心自定义修改）".to_string(),
                camera_left: "key light window and warm practical lamp on camera-left".to_string(),
                center_foreground: "main subject desk / action area in center foreground".to_string(),
                camera_right: "bookshelf and deep corridor shadow on camera-right".to_string(),
                exterior_anchor_image: None,
                interior_anchor_image: None,
                banned_topology_contradictions: vec![],
            },
        );
        fs.acoustic_spaces.insert(
            "interior_room".to_string(),
            AcousticSpace {
                description: "室内自然空间混响".to_string(),
                ffmpeg_bg_filter: "lowpass=f=800,volume=0.18".to_string(),
                h3_audio_cue: "Warm indoor room tone, subtle cloth movement".to_string(),
            },
        );
        fs.acoustic_spaces.insert(
            "exterior_open".to_string(),
            AcousticSpace {
                description: "室外开阔环境声场".to_string(),
                ffmpeg_bg_filter: "volume=0.30".to_string(),
                h3_audio_cue: "Open air ambiance, distant natural wind".to_string(),
            },
        );

        let toml_str = toml::to_string_pretty(&fs)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        std::fs::write(&paths.fact_sheet_file, toml_str)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    }

    if !paths.characters_file.exists() {
        let profiles = ProfilesToml {
            characters: vec![CharacterProfile {
                name: "Protagonist".to_string(),
                tier: "protagonist".to_string(),
                appearance: "30-year-old lead character, expressive eyes, realistic skin texture, wearing structured dark charcoal coat".to_string(),
                appearance_modern: None,
                appearance_ancient: None,
                voice: Some("温厚沉稳青年男声-v1".to_string()),
                ref_image: None,
                ref_image_modern: None,
                ref_image_ancient: None,
                turnaround_ref_image: None,
                costume_version: Some("v1_base".to_string()),
            }],
        };
        let toml_str = toml::to_string_pretty(&profiles)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        std::fs::write(&paths.characters_file, toml_str)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    }

    // Switch active project immediately to the new project
    *state.active_project.write().await = project_id.clone();
    let _ = std::fs::write(state.root_dir.join(".active_project"), &project_id);

    state.queue.emit(
        "project_switched",
        Some(project_id.clone()),
        format!("🗂️ 已创建并切换到新项目《{}》 (`{}`)", req.name, project_id),
        None,
    );

    Ok(Json(serde_json::json!({
        "ok": true,
        "project_id": project_id
    })))
}

async fn api_select_project(
    State(state): State<AppState>,
    Json(req): Json<SelectProjectRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let pid = req.project_id.trim().to_string();
    let paths = WorkspacePaths::for_project(&state.root_dir, &pid);
    if !paths.base_dir.exists() {
        return Err((StatusCode::NOT_FOUND, format!("项目目录不存在: {}", pid)));
    }
    paths
        .ensure_dirs()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    *state.active_project.write().await = pid.clone();
    let _ = std::fs::write(state.root_dir.join(".active_project"), &pid);

    let linter = DirectorLinter::new(&paths.base_dir);
    let proj_title = if linter.fact_sheet.project.name.is_empty() {
        pid.clone()
    } else {
        linter.fact_sheet.project.name
    };

    state.queue.emit(
        "project_switched",
        Some(pid.clone()),
        format!("🔀 已切换工作台当前项目至：《{}》 (`{}`)", proj_title, pid),
        None,
    );

    Ok(Json(serde_json::json!({
        "ok": true,
        "project_id": pid,
        "project_name": proj_title
    })))
}

async fn api_update_policy(
    State(state): State<AppState>,
    Json(req): Json<UpdateGuardPolicyRequest>,
) -> impl IntoResponse {
    *state.queue.require_approval_for_quality.write().await = req.require_approval_for_quality;
    *state.queue.daily_credit_limit_per_member.write().await = req.daily_credit_limit;
    if let Some(cid) = req.agent_conversation_id {
        if !cid.trim().is_empty() {
            *state.agent_conversation_id.write().await = cid.trim().to_string();
        }
    }
    state.queue.emit(
        "policy_updated",
        None,
        format!(
            "🛡️ 家庭积分守卫与 Agent 桥接已更新：Quality 审批锁={}, 每日配额={}点",
            req.require_approval_for_quality, req.daily_credit_limit
        ),
        None,
    );
    Json(serde_json::json!({ "ok": true }))
}

async fn api_list_episodes(State(state): State<AppState>) -> Json<Vec<EpisodeSummary>> {
    let paths = state.current_paths().await;
    let linter = DirectorLinter::new(&paths.base_dir);
    let mut list = Vec::new();
    let all_finals = scan_final_videos(&paths);

    if let Ok(entries) = std::fs::read_dir(&paths.episodes_dir) {
        let mut dirs: Vec<_> = entries.flatten().filter(|e| e.path().is_dir()).collect();
        dirs.sort_by_key(|e| e.file_name());

        for (idx, entry) in dirs.into_iter().enumerate() {
            let dir_name = entry.file_name().to_string_lossy().to_string();
            let manifest_path = entry.path().join("movie.toml");
            if !manifest_path.exists() {
                continue;
            }
            if let Ok(raw) = std::fs::read_to_string(&manifest_path) {
                if let Ok(manifest) = toml::from_str::<MovieManifest>(&raw) {
                    let report = linter.lint_scenes(&dir_name, &manifest.scenes);
                    let ep_prefix = dir_name.split('_').next().unwrap_or(&dir_name).to_lowercase();
                    let final_videos: Vec<MediaFileEntry> = all_finals
                        .iter()
                        .filter(|v| v.name.to_lowercase().starts_with(&ep_prefix))
                        .cloned()
                        .collect();

                    list.push(EpisodeSummary {
                        id: dir_name.clone(),
                        episode_number: (idx + 1) as u32,
                        dir_name,
                        title: manifest.title,
                        scene_count: manifest.scenes.len(),
                        lint_passed: report.passed,
                        error_count: report.error_count,
                        warning_count: report.warning_count,
                        final_videos,
                    });
                }
            }
        }
    }

    Json(list)
}

async fn api_get_episode(
    State(state): State<AppState>,
    AxumPath(ep_id): AxumPath<String>,
) -> Result<Json<EpisodeDetailResponse>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let ep_dir = paths.episodes_dir.join(&ep_id);
    let manifest_path = ep_dir.join("movie.toml");
    if !manifest_path.exists() {
        return Err((StatusCode::NOT_FOUND, format!("找不到剧集: {}", ep_id)));
    }

    let raw = std::fs::read_to_string(&manifest_path)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let manifest: MovieManifest = toml::from_str(&raw)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let script_path = ep_dir.join("script.md");
    let script_markdown = std::fs::read_to_string(&script_path).unwrap_or_default();

    let linter = DirectorLinter::new(&paths.base_dir);
    let lint_report = linter.lint_scenes(&format!("{}/movie.toml", ep_id), &manifest.scenes);

    let all_finals = scan_final_videos(&paths);
    let ep_prefix = ep_id.split('_').next().unwrap_or(&ep_id).to_lowercase();
    let final_videos: Vec<MediaFileEntry> = all_finals
        .iter()
        .filter(|v| v.name.to_lowercase().starts_with(&ep_prefix))
        .cloned()
        .collect();

    let scene_media = scan_scene_clips(&paths, &ep_id, &manifest.scenes, &all_finals);

    Ok(Json(EpisodeDetailResponse {
        id: ep_id.clone(),
        dir_name: ep_id,
        title: manifest.title,
        script_markdown,
        scenes: manifest.scenes,
        lint_report,
        scene_media,
        final_videos,
    }))
}

async fn api_save_episode_scenes(
    State(state): State<AppState>,
    AxumPath(ep_id): AxumPath<String>,
    Json(req): Json<SaveScenesRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let ep_dir = paths.episodes_dir.join(&ep_id);
    let manifest_path = ep_dir.join("movie.toml");
    let out_dir = paths.raw_clips_dir.join(&ep_id);

    let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
    compiler
        .write_movie_file(
            &manifest_path,
            &req.title,
            &req.scenes,
            &format!("{}_{}", paths.active_project_id, ep_id),
            Some(&out_dir),
            Some("16:9"),
        )
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let linter = DirectorLinter::new(&paths.base_dir);
    let lint_report = linter.lint_scenes(&format!("{}/movie.toml", ep_id), &req.scenes);

    state.queue.emit(
        "episode_saved",
        None,
        format!(
            "💾 分镜工程 `{}` 已保存并完成 L1-L5 实时质检 ({})",
            req.title,
            if lint_report.passed { "✅ 0 Error 通过" } else { "⚠️ 存在待修复项" }
        ),
        None,
    );

    Ok(Json(serde_json::json!({
        "ok": true,
        "lint_report": lint_report
    })))
}

async fn api_save_episode_script(
    State(state): State<AppState>,
    AxumPath(ep_id): AxumPath<String>,
    Json(req): Json<SaveScriptRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let ep_dir = paths.episodes_dir.join(&ep_id);
    std::fs::create_dir_all(&ep_dir)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let script_path = ep_dir.join("script.md");
    std::fs::write(&script_path, &req.script_markdown)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    state.queue.emit(
        "script_saved",
        None,
        format!("📝 剧集 `{}` 的文学剧本 (`script.md`) 已保存更新", ep_id),
        None,
    );

    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_mcp_http(
    State(state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> impl IntoResponse {
    let paths = state.current_paths().await;
    match mcp::handle_mcp_jsonrpc(&paths, payload).await {
        Some(resp) => (StatusCode::OK, Json(resp)).into_response(),
        None => StatusCode::ACCEPTED.into_response(),
    }
}

async fn api_list_agent_demands(State(state): State<AppState>) -> Json<Vec<AgentDemandItem>> {
    let list = state.agent_demands.read().await.clone();
    Json(list)
}

async fn api_submit_agent_demand(
    State(state): State<AppState>,
    Json(req): Json<SubmitAgentDemandRequest>,
) -> Result<Json<AgentDemandItem>, (StatusCode, String)> {
    let member_name = req
        .member_name
        .unwrap_or_else(|| "家人创作者".to_string());
    let conv_id = state.agent_conversation_id.read().await.clone();

    let mut item = AgentDemandItem {
        id: uuid::Uuid::new_v4().to_string()[..8].to_string(),
        created_at: chrono::Local::now().format("%H:%M:%S").to_string(),
        member_name: member_name.clone(),
        episode_id: req.episode_id.clone(),
        scene_id: req.scene_id.clone(),
        demand_text: req.demand_text.clone(),
        status: "sent_to_agent".to_string(),
        agent_reply: None,
    };

    let reg = state.agent_registry.read().await;
    match mcp::send_demand_to_agent_registry(
        &reg,
        &conv_id,
        &member_name,
        &req.episode_id,
        req.scene_id.as_deref(),
        &req.demand_text,
        state.port,
        req.preferred_plugin.as_deref(),
    )
    .await
    {
        Ok(reply) => {
            item.status = "sent_to_agent".to_string();
            item.agent_reply = Some(reply);
            state.queue.emit(
                "agent_demand_sent",
                Some(item.id.clone()),
                format!(
                    "📨 已通过跨平台 AgentPluginRegistry 将 `{}` 的改稿需求直达本地 Agent，正在通过 MCP 修改剧本...",
                    member_name
                ),
                None,
            );
        }
        Err(e) => {
            item.status = "bridge_warning".to_string();
            item.agent_reply = Some(format!("代理发送提示: {}", e));
        }
    }

    state.agent_demands.write().await.insert(0, item.clone());
    Ok(Json(item))
}

async fn api_list_plugins(State(state): State<AppState>) -> Json<serde_json::Value> {
    let reg = state.agent_registry.read().await;
    let plugins = reg.list_plugins();
    let current_platform = current_os();
    let enriched: Vec<_> = plugins
        .into_iter()
        .map(|p| {
            let available = p.is_available_on_current_os() && p.check_binary_exists();
            serde_json::json!({
                "id": p.id,
                "name": p.name,
                "kind": p.kind,
                "command": p.command,
                "args_template": p.args_template,
                "capabilities": p.capabilities,
                "enabled": p.enabled,
                "priority": p.priority,
                "os_targets": p.os_targets,
                "description": p.description,
                "model": p.model,
                "is_available_on_os": p.is_available_on_current_os(),
                "binary_exists": p.check_binary_exists(),
                "available": available,
            })
        })
        .collect();

    Json(serde_json::json!({
        "os_platform": current_platform,
        "plugin_count": enriched.len(),
        "plugins": enriched,
    }))
}

async fn api_register_plugin(
    State(state): State<AppState>,
    Json(req): Json<RegisterPluginRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut reg = state.agent_registry.write().await;
    let id = req.manifest.id.clone();
    reg.register_plugin(req.manifest);
    Ok(Json(serde_json::json!({
        "status": "success",
        "message": format!("Successfully registered/updated plugin `{}`", id),
        "plugin_id": id
    })))
}

async fn api_agent_dispatch(
    State(state): State<AppState>,
    Json(req): Json<AgentDispatchRequest>,
) -> Result<Json<AgentTaskResponse>, (StatusCode, String)> {
    let task_type = req
        .task_type
        .unwrap_or_else(|| "expand_micro_acting".to_string());
    let default_conv_id = state.agent_conversation_id.read().await.clone();
    let task_req = AgentTaskRequest {
        task_type: task_type.clone(),
        prompt: req.prompt.clone(),
        workspace_dir: req
            .workspace_dir
            .clone()
            .or_else(|| Some(state.root_dir.to_string_lossy().to_string())),
        preferred_plugin: req.preferred_plugin.clone(),
        conversation_id: req.conversation_id.or(Some(default_conv_id)),
        extra_context: None,
    };

    let reg = state.agent_registry.read().await;
    match reg.dispatch_task(&task_req).await {
        Ok(resp) if resp.status == "success" => Ok(Json(resp)),
        other => {
            // Automatic fallback to local AiWriterAssistant 4-beat micro-acting expansion
            let err_summary = match &other {
                Ok(r) => r.output.clone(),
                Err(e) => e.to_string(),
            };
            let fallback_output = format!(
                "【Local AiWriterAssistant 4-Beat Micro-Acting Fallback】\n\
                During 00:00.000–00:01.100 (Beat 1: Subtext & Preparatory Airlock) — Eye-line shifts with subtle pupil dilation; visible chest inhalation expands ribcage; brow glabella micro-tension; lips naturally closed with zero vocalization.\n\
                During 00:01.100–00:02.425 (Beat 2: Opening Delivery & Micro-Expression Shift) — Subtle upper-torso lean forward keeping headroom comfortable inside frame; nasolabial crease deepens; crisp Mandarin articulation begins.\n\
                During 00:02.425–00:03.200 (Beat 3: Climax Accent, Tactile Prop Force & Active Listener Reaction) — Peak vocal projection (+8dB surge) and masseter muscle flex; tactile fingers clench firmly onto prop contours; silent listener exhibits sharp pupil contraction.\n\
                During 00:03.200–00:03.750 (Beat 4: Emotional Resonance & Environmental Micro-Physics Tail Anchor) — Lips close cleanly for 22f latent relay while chest breathing, piercing gaze along steady eye-line axis, and subtle environmental micro-physics continue naturally.\n\n\
                (Note: Native plugin dispatch notice: {})",
                err_summary
            );
            Ok(Json(AgentTaskResponse {
                plugin_id: "ai_writer_assistant_fallback".to_string(),
                status: "fallback".to_string(),
                output: fallback_output,
                elapsed_ms: 1,
                os_platform: current_os().to_string(),
            }))
        }
    }
}

async fn api_critic_evaluate(
    State(state): State<AppState>,
    Json(req): Json<VideoCriticRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let mut v_path = PathBuf::from(&req.video_path);
    if !v_path.is_absolute() {
        v_path = state.root_dir.join(&v_path);
    }
    if !v_path.exists() {
        return Err((
            StatusCode::NOT_FOUND,
            format!("Video file not found: {}", v_path.display()),
        ));
    }

    match state.colab_runner.run_video_quality_critic(&v_path).await {
        Ok(report) => Ok(Json(report)),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Video quality critic failed: {}", e),
        )),
    }
}

async fn api_mcp_webhook(
    State(state): State<AppState>,
    Json(payload): Json<McpWebhookPayload>,
) -> impl IntoResponse {
    {
        let mut demands = state.agent_demands.write().await;
        if let Some(latest) = demands
            .iter_mut()
            .find(|d| d.episode_id == payload.episode_id && d.status == "sent_to_antigravity")
        {
            latest.status = "completed_via_mcp".to_string();
            latest.agent_reply = Some(payload.message.clone());
        }
    }
    state.queue.emit(
        "mcp_updated",
        Some(payload.episode_id),
        payload.message,
        None,
    );
    Json(serde_json::json!({ "ok": true }))
}

async fn api_create_episode(
    State(state): State<AppState>,
    Json(req): Json<CreateEpisodeRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let safe_dir: String = req
        .dir_name
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
        .collect();
    let dir_name = if safe_dir.is_empty() {
        format!("ep_custom_{}", chrono::Utc::now().timestamp() % 10000)
    } else {
        safe_dir
    };

    let linter = DirectorLinter::new(&paths.base_dir);
    let ai_req = AiStoryboardRequest {
        episode_title: req.title.clone(),
        story_idea: req.story_idea.clone(),
        default_era: None,
        preferred_model: req.preferred_model,
    };
    let generated = AiWriterAssistant::generate_and_heal_storyboard(&linter, &ai_req)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let ep_dir = paths.episodes_dir.join(&dir_name);
    let manifest_path = ep_dir.join("movie.toml");
    let out_dir = paths.raw_clips_dir.join(&dir_name);

    let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
    compiler
        .write_movie_file(
            &manifest_path,
            &req.title,
            &generated.scenes,
            &format!("{}_{}", paths.active_project_id, dir_name),
            Some(&out_dir),
            Some("16:9"),
        )
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let script_md = format!("# {}\n\n> 创作梗概：{}\n", req.title, req.story_idea);
    let _ = std::fs::write(ep_dir.join("script.md"), script_md);

    state.queue.emit(
        "episode_created",
        None,
        format!("✨ 新剧集《{}》已自动生成并通过 L1-L5 门禁审查！", req.title),
        None,
    );

    Ok(Json(serde_json::json!({
        "ok": true,
        "id": dir_name,
        "generated": generated
    })))
}

async fn api_ai_generate_storyboard(
    State(state): State<AppState>,
    Json(req): Json<AiStoryboardRequest>,
) -> Result<Json<director_core::llm_assistant::AiStoryboardResponse>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let linter = DirectorLinter::new(&paths.base_dir);
    let res = AiWriterAssistant::generate_and_heal_storyboard(&linter, &req)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(res))
}

async fn api_ai_polish_scene(
    State(state): State<AppState>,
    Json(req): Json<PolishSceneRequest>,
) -> Json<PolishSceneResponse> {
    let paths = state.current_paths().await;
    let linter = DirectorLinter::new(&paths.base_dir);
    let (polished, notes) = AiWriterAssistant::polish_single_scene(
        &linter,
        req.scene,
        req.chinese_visual_hint.as_deref(),
    );
    let lint_report = linter.lint_scenes("单镜实时审查", &[polished.clone()]);
    Json(PolishSceneResponse {
        scene: polished,
        notes,
        lint_report,
    })
}

fn media_url_prefix(paths: &WorkspacePaths) -> String {
    if paths.is_root_hosted() {
        String::new()
    } else {
        format!("/projects/{}", paths.active_project_id)
    }
}

async fn api_get_assets(State(state): State<AppState>) -> Json<serde_json::Value> {
    let paths = state.current_paths().await;
    let linter = DirectorLinter::new(&paths.base_dir);
    let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
    let prefix = media_url_prefix(&paths);

    let mut images = Vec::new();
    if let Ok(entries) = std::fs::read_dir(&paths.characters_images_dir) {
        let mut files: Vec<_> = entries.flatten().filter(|e| e.path().is_file()).collect();
        files.sort_by_key(|e| e.file_name());
        for f in files {
            let name = f.file_name().to_string_lossy().to_string();
            let size = f.metadata().map(|m| m.len()).unwrap_or(0);
            images.push(serde_json::json!({
                "name": name,
                "rel_path": format!("characters/images/{}", name),
                "url": format!("/media{}/characters/images/{}", prefix, name),
                "size_bytes": size,
            }));
        }
    }

    let final_videos = scan_final_videos(&paths);
    let mut raw_clips = Vec::new();
    if let Ok(ep_dirs) = std::fs::read_dir(&paths.raw_clips_dir) {
        let mut dirs: Vec<_> = ep_dirs.flatten().filter(|d| d.path().is_dir()).collect();
        dirs.sort_by_key(|d| d.file_name());
        for ep_entry in dirs {
            let ep_id = ep_entry.file_name().to_string_lossy().to_string();
            if let Ok(files) = std::fs::read_dir(ep_entry.path()) {
                for f in files.flatten() {
                    if f.path()
                        .extension()
                        .map(|ext| ext.to_string_lossy().to_lowercase() == "mp4")
                        .unwrap_or(false)
                    {
                        let name = f.file_name().to_string_lossy().to_string();
                        let size = f.metadata().map(|m| m.len()).unwrap_or(0);
                        let engine_tag = if name.contains("cloud") || name.contains("veo") {
                            "Veo 3.1 Cloud".to_string()
                        } else {
                            "MiniMax H3 Local".to_string()
                        };
                        raw_clips.push(serde_json::json!({
                            "episode_id": ep_id,
                            "name": name,
                            "rel_path": format!("output/raw_clips/{}/{}", ep_id, name),
                            "url": format!("/media{}/output/raw_clips/{}/{}", prefix, ep_id, name),
                            "size_bytes": size,
                            "engine_tag": engine_tag,
                        }));
                    }
                }
            }
        }
    }

    Json(serde_json::json!({
        "project_id": paths.active_project_id,
        "media_prefix": prefix,
        "project_meta": linter.fact_sheet.project,
        "style_lock": linter.fact_sheet.style_lock,
        "style_presets": builtin_style_presets(),
        "voice_presets": builtin_voice_presets(),
        "sume_models": SumeEngine::curated_models(),
        "characters": compiler.characters,
        "continuity_props": linter.fact_sheet.continuity_props,
        "spatial_rooms": linter.fact_sheet.spatial_rooms,
        "acoustic_spaces": linter.fact_sheet.acoustic_spaces,
        "arc_phases": linter.fact_sheet.director_rules.psychological_arc_phases,
        "images": images,
        "final_videos": final_videos,
        "raw_clips": raw_clips,
    }))
}

async fn api_create_character(
    State(state): State<AppState>,
    Json(req): Json<CreateCharacterRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let mut profiles: ProfilesToml = if paths.characters_file.exists() {
        let s = std::fs::read_to_string(&paths.characters_file)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        toml::from_str(&s).unwrap_or_default()
    } else {
        ProfilesToml::default()
    };

    let new_char = CharacterProfile {
        name: req.name.clone(),
        tier: req.tier.unwrap_or_else(|| "protagonist".to_string()),
        appearance: req.appearance,
        appearance_modern: req.appearance_modern,
        appearance_ancient: req.appearance_ancient,
        voice: req.voice.or_else(|| Some("温厚沉稳青年男声-v1".to_string())),
        ref_image: req.ref_image,
        ref_image_modern: req.ref_image_modern,
        ref_image_ancient: req.ref_image_ancient,
        turnaround_ref_image: req.turnaround_ref_image,
        costume_version: req.costume_version.or_else(|| Some("v1_base".to_string())),
    };

    if let Some(existing) = profiles.characters.iter_mut().find(|c| c.name == req.name) {
        *existing = new_char;
    } else {
        profiles.characters.push(new_char);
    }

    let serialized = toml::to_string_pretty(&profiles)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.characters_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    state.queue.emit(
        "asset_updated",
        Some(req.name.clone()),
        format!("🎭 角色资产 `@{}` 已保存更新", req.name),
        None,
    );

    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_upsert_prop(
    State(state): State<AppState>,
    Json(req): Json<UpsertPropRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
        let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
        toml::from_str(&s).unwrap_or_default()
    } else {
        FactSheet::default()
    };

    fs.continuity_props.insert(
        req.prop_id.clone(),
        ContinuityProp {
            name: req.name.clone(),
            category: req.category.unwrap_or_else(|| "prop".to_string()),
            description: req.description,
            ref_image: req.ref_image.filter(|s| !s.trim().is_empty()),
            version_tag: req.version_tag.or_else(|| Some("v1_normal".to_string())),
            owner_character: req.owner_character.filter(|s| !s.trim().is_empty()),
        },
    );

    let serialized = toml::to_string_pretty(&fs)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.fact_sheet_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    state.queue.emit(
        "asset_updated",
        Some(req.prop_id.clone()),
        format!("🗡️ 关键道具/连续性主体 `{}` 已保存更新", req.name),
        None,
    );

    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_delete_prop(
    State(state): State<AppState>,
    AxumPath(prop_id): AxumPath<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    if !paths.fact_sheet_file.exists() {
        return Ok(Json(serde_json::json!({ "ok": true })));
    }
    let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
    let mut fs: FactSheet = toml::from_str(&s).unwrap_or_default();
    fs.continuity_props.remove(&prop_id);
    let serialized = toml::to_string_pretty(&fs)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.fact_sheet_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_apply_style_preset(
    State(state): State<AppState>,
    Json(req): Json<ApplyStylePresetRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
        let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
        toml::from_str(&s).unwrap_or_default()
    } else {
        FactSheet::default()
    };

    let presets = builtin_style_presets();
    if let Some(p) = presets.iter().find(|x| x.id == req.preset_id) {
        fs.project.style_preset = p.id.clone();
        fs.project.production_mode = req
            .production_mode
            .clone()
            .unwrap_or_else(|| p.mode.clone());
        if let Some(no_sub) = req.no_subtitles_lock {
            fs.project.no_subtitles_lock = no_sub;
        }
        fs.style_lock.camera_base = p.camera_base.clone();
        fs.style_lock.lighting_base = p.lighting_base.clone();
        fs.style_lock.film_stock = p.film_stock.clone();
        fs.style_lock.global_suffix = p.global_suffix.clone();
        fs.style_lock.negative_prompt = p.negative_prompt.clone();

        let serialized = toml::to_string_pretty(&fs)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
        std::fs::write(&paths.fact_sheet_file, serialized)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

        state.queue.emit(
            "asset_updated",
            Some(p.id.clone()),
            format!("🎨 已切换项目视觉画风锁为『{}』", p.name),
            None,
        );
        Ok(Json(serde_json::json!({ "ok": true, "preset": p })))
    } else {
        Err((StatusCode::NOT_FOUND, format!("未找到预设画风: {}", req.preset_id)))
    }
}

async fn api_compile_seedance_episode(
    State(state): State<AppState>,
    AxumPath(ep_id): AxumPath<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let ep_dir = paths.episodes_dir.join(&ep_id);
    let m_path = ep_dir.join("movie.toml");
    let raw = std::fs::read_to_string(&m_path)
        .map_err(|e| (StatusCode::NOT_FOUND, format!("读取 movie.toml 失败: {}", e)))?;
    let m: MovieManifest =
        toml::from_str(&raw).map_err(|e| (StatusCode::BAD_REQUEST, e.to_string()))?;
    let linter = DirectorLinter::new(&paths.base_dir);
    let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);

    let payloads: Vec<_> = m
        .scenes
        .iter()
        .map(|sc| compiler.compile_seedance_prompt(sc, &linter.fact_sheet))
        .collect();

    Ok(Json(serde_json::json!({
        "episode_id": ep_id,
        "title": m.title,
        "production_mode": linter.fact_sheet.project.production_mode,
        "style_preset": linter.fact_sheet.project.style_preset,
        "seedance_nodes": payloads,
    })))
}

async fn api_export_jianying_draft(
    State(state): State<AppState>,
    AxumPath(ep_id): AxumPath<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let ep_dir = paths.episodes_dir.join(&ep_id);
    let m_path = ep_dir.join("movie.toml");
    let raw = std::fs::read_to_string(&m_path)
        .map_err(|e| (StatusCode::NOT_FOUND, format!("读取 movie.toml 失败: {}", e)))?;
    let m: MovieManifest =
        toml::from_str(&raw).map_err(|e| (StatusCode::BAD_REQUEST, e.to_string()))?;

    let engine = MasteringEngine::new(&paths.base_dir);
    let draft_dir = engine
        .export_jianying_multitrack_draft(&ep_id, &m.title, &m.scenes)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    state.queue.emit(
        "jianying_exported",
        Some(ep_id.clone()),
        format!(
            "🎬 已生成《{}》非破坏性 5 轨剪映草稿与 SRT 字幕包 (`{}`)",
            m.title,
            draft_dir.display()
        ),
        None,
    );

    Ok(Json(serde_json::json!({
        "ok": true,
        "episode_id": ep_id,
        "draft_dir": draft_dir.to_string_lossy(),
        "draft_json": draft_dir.join("draft_content.json").to_string_lossy(),
        "srt_file": draft_dir.join(format!("{}.srt", ep_id)).to_string_lossy(),
    })))
}

async fn api_delete_character(
    State(state): State<AppState>,
    AxumPath(name): AxumPath<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    if !paths.characters_file.exists() {
        return Ok(Json(serde_json::json!({ "ok": true })));
    }
    let s = std::fs::read_to_string(&paths.characters_file)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let mut profiles: ProfilesToml = toml::from_str(&s).unwrap_or_default();
    profiles.characters.retain(|c| c.name != name);
    let serialized = toml::to_string_pretty(&profiles)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.characters_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_upsert_room(
    State(state): State<AppState>,
    Json(req): Json<UpsertRoomRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
        let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
        toml::from_str(&s).unwrap_or_default()
    } else {
        FactSheet::default()
    };

    let existing_banned = fs
        .spatial_rooms
        .get(&req.room_id)
        .map(|r| r.banned_topology_contradictions.clone())
        .unwrap_or_default();

    fs.spatial_rooms.insert(
        req.room_id.clone(),
        SpatialRoom {
            description: req.description,
            camera_left: req.camera_left,
            center_foreground: req.center_foreground,
            camera_right: req.camera_right,
            exterior_anchor_image: req.exterior_anchor_image.filter(|s| !s.trim().is_empty()),
            interior_anchor_image: req.interior_anchor_image.filter(|s| !s.trim().is_empty()),
            banned_topology_contradictions: existing_banned,
        },
    );

    let serialized = toml::to_string_pretty(&fs)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.fact_sheet_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    state.queue.emit(
        "asset_updated",
        Some(req.room_id.clone()),
        format!("📐 三维空间拓扑 `{}` 已保存更新", req.room_id),
        None,
    );

    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_delete_room(
    State(state): State<AppState>,
    AxumPath(room_id): AxumPath<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    if !paths.fact_sheet_file.exists() {
        return Ok(Json(serde_json::json!({ "ok": true })));
    }
    let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
    let mut fs: FactSheet = toml::from_str(&s).unwrap_or_default();
    fs.spatial_rooms.remove(&room_id);
    let serialized = toml::to_string_pretty(&fs)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.fact_sheet_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_upsert_acoustic(
    State(state): State<AppState>,
    Json(req): Json<UpsertAcousticRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
        let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
        toml::from_str(&s).unwrap_or_default()
    } else {
        FactSheet::default()
    };

    fs.acoustic_spaces.insert(
        req.space_id.clone(),
        AcousticSpace {
            description: req.description,
            ffmpeg_bg_filter: req.ffmpeg_bg_filter,
            h3_audio_cue: req.h3_audio_cue,
        },
    );

    let serialized = toml::to_string_pretty(&fs)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.fact_sheet_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_update_style_lock(
    State(state): State<AppState>,
    Json(req): Json<StyleLock>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
        let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
        toml::from_str(&s).unwrap_or_default()
    } else {
        FactSheet::default()
    };
    fs.style_lock = req;
    let serialized = toml::to_string_pretty(&fs)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    std::fs::write(&paths.fact_sheet_file, serialized)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    state.queue.emit(
        "asset_updated",
        None,
        "🎥 项目全局摄影机与胶片风格锁 (`[style_lock]`) 已保存更新",
        None,
    );

    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_upload_image(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let prefix = media_url_prefix(&paths);
    let _ = std::fs::create_dir_all(&paths.characters_images_dir);

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| (StatusCode::BAD_REQUEST, e.to_string()))?
    {
        let file_name = field
            .file_name()
            .map(|s| s.to_string())
            .unwrap_or_else(|| format!("anchor_{}.jpg", chrono::Utc::now().timestamp()));
        let safe_name: String = file_name
            .chars()
            .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-' || *c == '.')
            .collect();
        let data = field
            .bytes()
            .await
            .map_err(|e| (StatusCode::BAD_REQUEST, e.to_string()))?;
        let dst = paths.characters_images_dir.join(&safe_name);
        std::fs::write(&dst, &data)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

        return Ok(Json(serde_json::json!({
            "ok": true,
            "name": safe_name,
            "rel_path": format!("characters/images/{}", safe_name),
            "url": format!("/media{}/characters/images/{}", prefix, safe_name),
        })));
    }
    Err((StatusCode::BAD_REQUEST, "未找到上传的文件字段".to_string()))
}

async fn api_delete_image(
    State(state): State<AppState>,
    AxumPath(name): AxumPath<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let safe_name: String = name
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-' || *c == '.')
        .collect();
    let target = paths.characters_images_dir.join(&safe_name);
    if target.exists() {
        let _ = std::fs::remove_file(target);
    }
    Ok(Json(serde_json::json!({ "ok": true })))
}

async fn api_list_jobs(State(state): State<AppState>) -> Json<Vec<RenderJob>> {
    let jobs = state.queue.jobs.read().await.clone();
    Json(jobs)
}

async fn api_submit_render(
    State(state): State<AppState>,
    Json(req): Json<SubmitRenderRequest>,
) -> Result<Json<RenderJob>, (StatusCode, String)> {
    let paths = state.current_paths().await;
    let ep_dir = paths.episodes_dir.join(&req.episode_id);
    let manifest_path = ep_dir.join("movie.toml");
    if !manifest_path.exists() {
        return Err((
            StatusCode::NOT_FOUND,
            format!("找不到剧集配置文件: {}", req.episode_id),
        ));
    }

    let linter = DirectorLinter::new(&paths.base_dir);
    let report = linter
        .lint_manifest_file(&manifest_path)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let dry_run = req.dry_run.unwrap_or(false);
    if !report.passed && !dry_run {
        return Err((
            StatusCode::BAD_REQUEST,
            format!(
                "🛑 [L1-L5 导演门禁拦截] 当前分镜存在 {} 个 Error，已自动阻断渲染以保护积分！请先点击『AI 一键合规自愈』。",
                report.error_count
            ),
        ));
    }

    let scene_count = if req.scene_id.is_some() {
        1
    } else {
        report.scene_count.max(1)
    };
    let is_admin = req
        .admin_pin
        .as_deref()
        .map(|p| p == state.admin_pin)
        .unwrap_or(false);

    let job = state
        .queue
        .enqueue_job(
            req.requested_by.unwrap_or_else(|| "家人创作员".to_string()),
            req.episode_id,
            req.scene_id,
            req.model,
            dry_run,
            scene_count,
            is_admin,
        )
        .await;

    if job.status == JobStatus::Queued {
        spawn_job_worker(state, job.clone());
    }

    Ok(Json(job))
}

async fn api_approve_job(
    State(state): State<AppState>,
    AxumPath(job_id): AxumPath<String>,
    Json(req): Json<ApproveJobRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let pin_ok = req
        .admin_pin
        .as_deref()
        .map(|p| p == state.admin_pin)
        .unwrap_or(false);
    if !pin_ok {
        return Err((
            StatusCode::FORBIDDEN,
            "管理员审批口令不正确 (默认: 2280)".to_string(),
        ));
    }

    let mut target_job = None;
    {
        let mut jobs = state.queue.jobs.write().await;
        if let Some(j) = jobs.iter_mut().find(|j| j.id == job_id) {
            if req.approve {
                j.status = JobStatus::Queued;
                j.progress_message = "✅ 管理员已批准，正在启动引擎渲染...".to_string();
                target_job = Some(j.clone());
            } else {
                j.status = JobStatus::Rejected;
                j.progress_message = "已取消高消耗精修申请，建议先用本机 H3 免费预演".to_string();
            }
        }
    }

    if let Some(job) = target_job {
        state.queue.emit(
            "job_approved",
            Some(job.id.clone()),
            "✅ 管理员已批准 Veo 3.1 Quality 精修任务！",
            Some(JobStatus::Queued),
        );
        spawn_job_worker(state, job);
    }

    Ok(Json(serde_json::json!({ "ok": true })))
}

fn spawn_job_worker(state: AppState, job: RenderJob) {
    tokio::spawn(async move {
        let paths = state.current_paths().await;
        let lane = match job.engine.as_str() {
            "h3" => "local_rocm",
            "flow" => "flow",
            "sume" => "sume",
            "colab" => "colab_g4",
            _ => {
                if job.model.contains("tts") || job.model.contains("music") {
                    "audio_tts"
                } else {
                    "flow"
                }
            }
        };

        state
            .queue
            .update_job_status(
                &job.id,
                JobStatus::Running,
                format!("🚦 正在排队等待 [{}] 高并发通道槽位...", lane),
                None,
                None,
            )
            .await;

        // Acquire lane permit from the high-concurrency semaphore pool
        let _lane_permit = state.queue.acquire_lane_permit(lane).await;

        state
            .queue
            .update_job_status(
                &job.id,
                JobStatus::Running,
                format!(
                    "🎬 正在并发执行渲染 (通道: {} | {} | 模型: {} | 预演: {})...",
                    lane, job.episode_id, job.model, job.dry_run
                ),
                None,
                None,
            )
            .await;

        let manifest_path = paths
            .episodes_dir
            .join(&job.episode_id)
            .join("movie.toml");
        let out_dir = paths.raw_clips_dir.join(&job.episode_id);

        let res = if job.engine == "h3" {
            state
                .h3_engine
                .run_local_h3_render(&paths.base_dir, &job.episode_id, job.scene_id.as_deref(), job.dry_run)
                .await
        } else if job.engine == "sume" {
            let raw_str = std::fs::read_to_string(&manifest_path).unwrap_or_default();
            let manifest: MovieManifest = toml::from_str(&raw_str).unwrap_or_default();
            let target_sc = if let Some(ref sc_id) = job.scene_id {
                manifest.scenes.iter().find(|s| &s.id == sc_id)
            } else {
                manifest.scenes.first()
            };
            if let Some(sc) = target_sc {
                let out_file = out_dir.join(format!("{}_{}.mp4", sc.id, job.model));
                let init_frame = sc
                    .ref_image
                    .as_ref()
                    .map(|r| paths.base_dir.join(r));
                state
                    .sume_engine
                    .generate_single_scene_clip(
                        init_frame.as_deref(),
                        None,
                        &sc.action,
                        &out_file,
                        &job.model,
                        &sc.aspect,
                        sc.duration.max(5),
                        job.dry_run,
                    )
                    .await
            } else {
                Err(anyhow::anyhow!("未找到目标分镜"))
            }
        } else if let Some(ref sc_id) = job.scene_id {
            // Single scene render
            let raw_str = std::fs::read_to_string(&manifest_path).unwrap_or_default();
            let manifest: MovieManifest = toml::from_str(&raw_str).unwrap_or_default();
            if let Some(sc) = manifest.scenes.iter().find(|s| &s.id == sc_id) {
                if job.dry_run {
                    Ok((
                        true,
                        format!(
                            "[Dry-Run 零积分校验通过] 镜头 `{}` 提示词与首帧母图 `{:?}` 校验就绪。",
                            sc.id, sc.ref_image
                        ),
                        String::new(),
                    ))
                } else {
                    let out_file = out_dir.join(format!("{}_{}.mp4", sc.id, job.model));
                    let init_frame = sc
                        .ref_image
                        .as_ref()
                        .map(|r| paths.base_dir.join(r));
                    state
                        .flow_engine
                        .generate_single_scene_clip(
                            init_frame.as_deref(),
                            &sc.action,
                            &out_file,
                            &sc.aspect,
                            &job.model,
                        )
                        .await
                }
            } else {
                Err(anyhow::anyhow!("镜头 {} 不存在", sc_id))
            }
        } else {
            state
                .flow_engine
                .run_movie_project(&manifest_path, Some(&out_dir), job.dry_run, true)
                .await
        };

        match res {
            Ok((true, stdout, stderr)) => {
                let combined = format!("{}\n{}", stdout, stderr);
                let tail: String = combined
                    .lines()
                    .rev()
                    .take(15)
                    .collect::<Vec<_>>()
                    .into_iter()
                    .rev()
                    .collect::<Vec<_>>()
                    .join("\n");
                state
                    .queue
                    .update_job_status(
                        &job.id,
                        JobStatus::Completed,
                        format!(
                            "🎉 任务完成！(本次消耗: {} 点)",
                            if job.dry_run { 0 } else { job.estimated_credits }
                        ),
                        None,
                        Some(tail),
                    )
                    .await;
            }
            Ok((false, stdout, stderr)) => {
                let combined = format!("{}\n{}", stdout, stderr);
                state
                    .queue
                    .update_job_status(
                        &job.id,
                        JobStatus::Failed,
                        format!("⚠️ 引擎返回非零状态，请查看日志详情"),
                        None,
                        Some(combined),
                    )
                    .await;
            }
            Err(e) => {
                state
                    .queue
                    .update_job_status(
                        &job.id,
                        JobStatus::Failed,
                        format!("❌ 执行异常: {}", e),
                        None,
                        Some(e.to_string()),
                    )
                    .await;
            }
        }
    });
}

async fn api_sse_events(
    State(state): State<AppState>,
) -> Sse<impl tokio_stream::Stream<Item = Result<Event, Infallible>>> {
    let rx = state.queue.event_tx.subscribe();
    let stream = BroadcastStream::new(rx).filter_map(|res| match res {
        Ok(evt) => {
            let json = serde_json::to_string(&evt).unwrap_or_default();
            Some(Ok(Event::default().data(json)))
        }
        Err(_) => None,
    });
    Sse::new(stream).keep_alive(
        KeepAlive::new()
            .interval(Duration::from_secs(15))
            .text("keep-alive"),
    )
}

fn scan_final_videos(paths: &WorkspacePaths) -> Vec<MediaFileEntry> {
    let mut out = Vec::new();
    let prefix = media_url_prefix(paths);
    if let Ok(entries) = std::fs::read_dir(&paths.final_episodes_dir) {
        let mut files: Vec<_> = entries
            .flatten()
            .filter(|e| {
                e.path()
                    .extension()
                    .map(|ext| ext.to_string_lossy().to_lowercase() == "mp4")
                    .unwrap_or(false)
            })
            .collect();
        files.sort_by_key(|e| std::cmp::Reverse(e.file_name()));

        for f in files {
            let name = f.file_name().to_string_lossy().to_string();
            let size = f.metadata().map(|m| m.len()).unwrap_or(0);
            let engine_tag = if name.contains("cloud") || name.contains("veo") {
                "Veo 3.1 Cloud".to_string()
            } else if name.contains("local") || name.contains("h3") {
                "MiniMax H3 Local".to_string()
            } else {
                "Master".to_string()
            };
            out.push(MediaFileEntry {
                url: format!("/media{}/output/final_episodes/{}", prefix, name),
                rel_path: format!("output/final_episodes/{}", name),
                name,
                size_bytes: size,
                engine_tag,
            });
        }
    }
    out
}

fn scan_scene_clips(
    paths: &WorkspacePaths,
    ep_id: &str,
    scenes: &[SceneSpec],
    final_videos: &[MediaFileEntry],
) -> std::collections::BTreeMap<String, Vec<MediaFileEntry>> {
    let mut map = std::collections::BTreeMap::new();
    let raw_ep_dir = paths.raw_clips_dir.join(ep_id);
    let prefix = media_url_prefix(paths);
    let mut raw_files = Vec::new();

    if let Ok(entries) = std::fs::read_dir(&raw_ep_dir) {
        for e in entries.flatten() {
            if e.path()
                .extension()
                .map(|ext| ext.to_string_lossy().to_lowercase() == "mp4")
                .unwrap_or(false)
            {
                let name = e.file_name().to_string_lossy().to_string();
                let size = e.metadata().map(|m| m.len()).unwrap_or(0);
                let engine_tag = if name.contains("cloud") || name.contains("veo") {
                    "Veo 3.1 Cloud".to_string()
                } else {
                    "MiniMax H3 Local".to_string()
                };
                raw_files.push(MediaFileEntry {
                    url: format!("/media{}/output/raw_clips/{}/{}", prefix, ep_id, name),
                    rel_path: format!("output/raw_clips/{}/{}", ep_id, name),
                    name,
                    size_bytes: size,
                    engine_tag,
                });
            }
        }
    }

    for sc in scenes {
        let mut matched = Vec::new();
        // Match prefix like ep01_00a or ep01_01
        let short_prefix: String = sc.id.split('_').take(2).collect::<Vec<_>>().join("_");
        for fv in final_videos {
            if fv.name.starts_with(&sc.id)
                || (!short_prefix.is_empty() && fv.name.starts_with(&short_prefix))
            {
                matched.push(fv.clone());
            }
        }
        for rv in &raw_files {
            if rv.name.starts_with(&sc.id)
                || (!short_prefix.is_empty() && rv.name.starts_with(&short_prefix))
            {
                matched.push(rv.clone());
            }
        }
        map.insert(sc.id.clone(), matched);
    }

    map
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_quota_summary_calculation() {
        let base_dir = resolve_workspace_root();
        let initial_proj = WorkspacePaths::resolve_active_project_id(&base_dir);
        let reg = Arc::new(RwLock::new(AgentPluginRegistry::new()));
        let state = AppState {
            root_dir: base_dir.clone(),
            active_project: Arc::new(RwLock::new(initial_proj)),
            flow_engine: FlowEngine::new(&base_dir),
            flow_music_engine: FlowMusicEngine::new(&base_dir),
            h3_engine: H3Engine::new(&base_dir),
            sume_engine: SumeEngine::new(&base_dir),
            queue: RenderQueue::new(),
            admin_pin: "2280".to_string(),
            web_password: "pass".to_string(),
            session_token: "token".to_string(),
            port: 18443,
            agent_conversation_id: Arc::new(RwLock::new("conv".to_string())),
            agent_demands: Arc::new(RwLock::new(Vec::new())),
            agent_registry: reg,
            colab_runner: ColabBridgeRunner::new(&base_dir),
        };

        let summary = build_quota_summary(&state).await;
        assert!(summary.colab.remaining_ccu > 0.0);
        assert_eq!(summary.flow_video.remaining_credits, 9895);
        assert_eq!(summary.flow_music.daily_quota_tracks, 500);
        assert!(summary.colab.estimates.estimated_video_minutes > 1000.0);
        assert!(summary.colab.estimates.estimated_audio_minutes > 100000.0);
        assert_eq!(summary.flow_video.estimates.veo_fast_shots, 989);
        assert_eq!(summary.flow_video.estimates.veo_quality_shots, 98);
        assert_eq!(summary.flow_music.estimates.estimated_sfx_count, 1000);
    }
}
