use std::path::PathBuf;

use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::Command;

use director_core::{
    config::{builtin_style_presets, builtin_voice_presets},
    AcousticSpace, CharacterProfile, ContinuityProp, DirectorLinter, FactSheet, MasteringEngine,
    MovieManifest, ProfilesToml, ProjectMeta, SceneSpec, SpatialRoom, StoryboardCompiler,
    StyleLock, WorkspacePaths,
};

/// Default conversation ID of the active Antigravity agent session
pub const DEFAULT_CONVERSATION_ID: &str = "e2e3111c-e08d-41d4-8bec-b19c04139f88";

/// Proxy Bridge that forwards family demands from the Web UI directly to the Antigravity Agent
/// via `agentapi.bat send-message`, prompting the Agent to use its MCP tools (`aether-director-studio`)
/// to modify scripts, scenes, and manifests on the platform.
pub async fn send_demand_to_antigravity_agent(
    conversation_id: &str,
    member_name: &str,
    episode_id: &str,
    scene_id: Option<&str>,
    demand_text: &str,
    server_port: u16,
) -> anyhow::Result<String> {
    let user_profile = std::env::var("USERPROFILE").unwrap_or_else(|_| "C:\\Users\\Liang".to_string());
    let agentapi_main = PathBuf::from(&user_profile)
        .join(".gemini")
        .join("antigravity")
        .join("bin")
        .join("agentapi.bat");
    let agentapi_ide = PathBuf::from(&user_profile)
        .join(".gemini")
        .join("antigravity-ide")
        .join("bin")
        .join("agentapi.bat");

    let bin = if agentapi_main.exists() {
        agentapi_main
    } else if agentapi_ide.exists() {
        agentapi_ide
    } else {
        anyhow::bail!("找不到 Antigravity agentapi.bat 桥接程序");
    };

    let target_scope = match scene_id {
        Some(sc) if !sc.is_empty() => format!("剧集 `{}` 的镜头 `{}`", episode_id, sc),
        _ => format!("剧集 `{}`", episode_id),
    };

    let structured_prompt = format!(
        "【来自 AI 短视频创作工作室 Web 端的实时修改需求】\n\
        - 发起创作者：{member_name}\n\
        - 目标范围：{target_scope}\n\
        - 具体需求：{demand_text}\n\n\
        请你立即通过工作室 MCP 工具（或 HTTP 接口 `http://127.0.0.1:{server_port}/api/v1/mcp`）读取并直接修改当前项目上的对应剧本 (`script.md`)、分镜配置 (`movie.toml`) 或角色/空间资产，确保 100% 符合 L1-L5 导演门禁规范（0 Error），完成后调用 `studio_notify_reply` 将修改结果同步推送到网页端！"
    );

    let out = Command::new("cmd")
        .args([
            "/C",
            &bin.to_string_lossy(),
            "send-message",
            "--title",
            &format!("家人需求: {}", member_name),
            conversation_id,
            &structured_prompt,
        ])
        .output()
        .await?;

    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
    let stderr = String::from_utf8_lossy(&out.stderr).to_string();
    if !out.status.success() {
        anyhow::bail!("agentapi 调用返回异常: {} {}", stdout, stderr);
    }
    Ok(stdout)
}

/// Runs the JSON-RPC 2.0 MCP Server over `stdio` (`director-server.exe mcp-stdio`)
pub async fn run_mcp_stdio(root_dir: PathBuf) -> anyhow::Result<()> {
    let stdin = tokio::io::stdin();
    let mut stdout = tokio::io::stdout();
    let mut reader = BufReader::new(stdin).lines();

    while let Some(line) = reader.next_line().await? {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(req) = serde_json::from_str::<Value>(trimmed) {
            let active_proj = WorkspacePaths::resolve_active_project_id(&root_dir);
            let paths = WorkspacePaths::for_project(&root_dir, &active_proj);
            if let Some(resp) = handle_mcp_jsonrpc(&paths, req).await {
                let mut out_str = serde_json::to_string(&resp)?;
                out_str.push('\n');
                stdout.write_all(out_str.as_bytes()).await?;
                stdout.flush().await?;
            }
        }
    }
    Ok(())
}

/// Handles an MCP JSON-RPC 2.0 request (works identically for both `stdio` and Streamable HTTP `POST /mcp`)
pub async fn handle_mcp_jsonrpc(paths: &WorkspacePaths, req: Value) -> Option<Value> {
    let id = req.get("id").cloned();
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = req.get("params").cloned().unwrap_or_else(|| json!({}));

    // Notifications (no id) do not expect a response
    if id.is_none() || method.starts_with("notifications/") {
        return None;
    }

    let result = match method {
        "initialize" => Ok(json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": { "listChanged": false }
            },
            "serverInfo": {
                "name": director_core::config::SYSTEM_SLUG,
                "version": "0.3.0"
            }
        })),
        "ping" => Ok(json!({})),
        "tools/list" => Ok(mcp_tools_list()),
        "tools/call" => mcp_tools_call(paths, &params).await,
        _ => Err(format!("Method not found: {}", method)),
    };

    Some(match result {
        Ok(res_val) => json!({
            "jsonrpc": "2.0",
            "id": id,
            "result": res_val
        }),
        Err(err_msg) => json!({
            "jsonrpc": "2.0",
            "id": id,
            "error": {
                "code": -32601,
                "message": err_msg
            }
        }),
    })
}

fn mcp_tools_list() -> Value {
    json!({
        "tools": [
            {
                "name": "studio_list_projects",
                "description": "列出 AetherDirector Studio (天枢 AI 影视工作台) 上的所有短视频/短剧项目及其激活状态、剧集数、角色数和画风配置。",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "studio_select_or_create_project",
                "description": "切换当前活跃项目，或创建一个全新的短视频/短剧项目（自动初始化独立目录、Style 锁、三维房间拓扑和声学空间）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": { "type": "string", "description": "项目唯一英文 ID，如 modern_drama, fashion_showcase, cyberpunk_short 等" },
                        "name": { "type": "string", "description": "可选：创建新项目时的中文名称" },
                        "subtitle": { "type": "string", "description": "可选：项目题材与世界观简述" },
                        "aspect": { "type": "string", "description": "可选：画幅比例，如 16:9 或 9:16" },
                        "style_preset": { "type": "string", "description": "可选：初始画风 ID（live_action_arri / semi_realistic_3d_chinese_animation / semi_realistic_eastern_dark_fantasy_3d / storytime_2d_handdrawn）" }
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "studio_get_assets",
                "description": "获取当前项目的完整资产清单（包含 4 大内置画风预设、17 款 48kHz 中英文音色锚点、角色形象卡/换装卡、武魂/关键道具、三维空间拓扑、声学空间与定妆图列表）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "studio_apply_style_preset",
                "description": "一键切换当前项目的全局画风锁与制作模式（如『半写实 3D 国漫电影』、『东方奇幻暗黑 3D 电影』、『真人电影写实 ARRI』），并可设置项目级无字幕锁。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "preset_id": { "type": "string", "description": "画风预设 ID：live_action_arri | semi_realistic_3d_chinese_animation | semi_realistic_eastern_dark_fantasy_3d | storytime_2d_handdrawn" },
                        "production_mode": { "type": "string", "description": "可选：cinematic_drama | animated_explainer | storytime_animation" },
                        "no_subtitles_lock": { "type": "boolean", "description": "可选：是否开启项目级无画面叠字锁（默认 true）" }
                    },
                    "required": ["preset_id"]
                }
            },
            {
                "name": "studio_upsert_character",
                "description": "新增或更新项目角色资产（支持主角/配角/路人分级、16:9 纯白底四视图卡、图生图换装版本标记，以及绑定 17 款 48kHz 标准音色锚点）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": { "type": "string", "description": "角色名（建议使用2-3个常用汉字以保证口播准确）" },
                        "tier": { "type": "string", "description": "角色层级：protagonist (主角) | supporting (跨片段配角) | extra (路人)" },
                        "appearance": { "type": "string", "description": "角色面部五官、发型、体型与干净常规服装层次描述" },
                        "voice": { "type": "string", "description": "绑定的音色 ID，如 温厚沉稳青年男声-v1, 冷硬自信青年男声-v1, 磁性沧桑中年男声-v1, 清透克制年轻女声-v1 等" },
                        "ref_image": { "type": "string", "description": "可选：9:16 正面立绘候选图路径，如 characters/images/hero_v1.jpg" },
                        "turnaround_ref_image": { "type": "string", "description": "可选：16:9 纯白底无文字四视图人物卡路径" },
                        "costume_version": { "type": "string", "description": "可选：服装版本标识，如 v1_base, v2_battle_armor" }
                    },
                    "required": ["name", "appearance"]
                }
            },
            {
                "name": "studio_upsert_prop",
                "description": "新增或更新『武魂 / 召唤物 / 关键道具』独立连续性主体资产（防止跨镜头武器、法器、信物造型漂移）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prop_id": { "type": "string", "description": "道具英文/拼音唯一标识，如 bronze_sword_v1, convex_glasses" },
                        "name": { "type": "string", "description": "道具/武魂中文名称" },
                        "category": { "type": "string", "description": "类别：prop | weapon | summon | artifact | vehicle" },
                        "description": { "type": "string", "description": "干净无遮挡展示状态下的轮廓、比例、结构、材质与主辅色描述" },
                        "ref_image": { "type": "string", "description": "可选：独立参考图路径" },
                        "version_tag": { "type": "string", "description": "可选：形态版本，如 v1_normal, v2_awakened" },
                        "owner_character": { "type": "string", "description": "可选：归属角色名" }
                    },
                    "required": ["prop_id", "name", "description"]
                }
            },
            {
                "name": "studio_upsert_room",
                "description": "新增或更新跨镜头三维空间拓扑锁 (`[spatial_rooms]`)，锁定左/中/右方位陈设与室内外锚定图，杜绝 180 度越轴。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "room_id": { "type": "string", "description": "空间英文 ID，如 ancestral_hall_night, dorm_room_night" },
                        "description": { "type": "string", "description": "空间整体结构与光线简述" },
                        "camera_left": { "type": "string", "description": "画面左侧固定陈设与光源" },
                        "center_foreground": { "type": "string", "description": "画面中前景核心调度区与道具" },
                        "camera_right": { "type": "string", "description": "画面右侧固定陈设与人物朝向" },
                        "exterior_anchor_image": { "type": "string", "description": "可选：外景建置锚定图路径" },
                        "interior_anchor_image": { "type": "string", "description": "可选：内景空间参考图路径" }
                    },
                    "required": ["room_id", "description", "camera_left", "center_foreground", "camera_right"]
                }
            },
            {
                "name": "studio_list_episodes",
                "description": "列出当前项目上所有剧集（含剧本路径、分镜数量、L1-L5 门禁状态与已渲染视频数）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "studio_get_episode",
                "description": "读取指定剧集的完整信息，包括文学剧本 (`script.md`)、分镜数组 (`scenes`) 与 L1-L5 `DirectorLinter` 报告。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep01_crossing, ep02_orientation, ep03_jieting" }
                    },
                    "required": ["episode_id"]
                }
            },
            {
                "name": "studio_update_script_markdown",
                "description": "直接修改或覆写平台上指定剧集的文学剧本正文 (`script.md`)。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep01_crossing" },
                        "script_markdown": { "type": "string", "description": "完整的 Markdown 剧本内容" }
                    },
                    "required": ["episode_id", "script_markdown"]
                }
            },
            {
                "name": "studio_update_scene",
                "description": "直接修改平台上指定剧集中的某一个分镜卡片（台词 line、摄影机画面描述 action、物理焦段 camera_motion、参考母图 ref_image、出镜角色 characters、道具 props、一镜多切数 shot_count、微剪入出点 trim_start_sec/trim_end_sec、动作拟音 foley_cue、配乐情绪 bgm_mood 等），自动重编译 movie.toml 并运行 L1-L5 DirectorLinter 校验。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep01_crossing" },
                        "scene_id": { "type": "string", "description": "镜头 ID，如 ep01_02_cosplay_sigh（若不存在则自动追加为新镜头）" },
                        "speaker": { "type": "string", "description": "可选：说话人" },
                        "line": { "type": "string", "description": "可选：修改后的中文核定台词（15秒内建议不超过50-55字）" },
                        "action": { "type": "string", "description": "可选：修改后的摄影级画面描述（支持镜头1...镜头2...多镜写法）" },
                        "camera_motion": { "type": "string", "description": "可选：修改后的物理焦段与运镜描述（需包含如 35mm/50mm/85mm）" },
                        "ref_image": { "type": "string", "description": "可选：绑定的定妆/空间参考图路径" },
                        "characters": { "type": "array", "items": { "type": "string" }, "description": "可选：本片段实际出镜的角色名数组" },
                        "props": { "type": "array", "items": { "type": "string" }, "description": "可选：本片段实际出现的武魂/关键道具 ID 数组" },
                        "shot_count": { "type": "integer", "description": "可选：15秒片段内的硬切镜头数（快节奏默认5镜，重表演3-4镜）" },
                        "trim_start_sec": { "type": "number", "description": "可选：片头微剪切除秒数" },
                        "trim_end_sec": { "type": "number", "description": "可选：片尾微剪去毛刺秒数（默认 0.15 秒）" },
                        "foley_cue": { "type": "string", "description": "可选：MMAudio 画面同步动作拟音提示" },
                        "bgm_mood": { "type": "string", "description": "可选：ACE-Step 跨镜情绪配乐标签" },
                        "acoustic_space": { "type": "string", "description": "可选：声学空间，如 interior_closed, ancient_tent_interior, exterior_storm" },
                        "arc_phase": { "type": "string", "description": "可选：心理弧光阶段" },
                        "room_id": { "type": "string", "description": "可选：三维房间拓扑 ID" },
                        "pose_anchors": { "type": "array", "items": { "type": "string" }, "description": "可选：绑定的 POSE-DB-01 姿态 ID 数组（如 [\"full_single_P011_front\", \"full_single_P004_diag\"]）" },
                        "keyframe_indices": { "type": "array", "items": { "type": "integer" }, "description": "可选：17k 相位对齐关键帧索引数组（如 [0, 51, 85]）" },
                        "keyframe_strengths": { "type": "array", "items": { "type": "number" }, "description": "可选：各关键帧锁死强度数组（如 [1.0, 0.88, 0.90]）" },
                        "continuity_track": { "type": "string", "description": "可选：跨镜连续性轨道（track_a_latent_relay 22帧潜空间接力 | track_b_hard_cut 多机位硬切）" },
                        "tail_lock_v9": { "type": "boolean", "description": "可选：是否开启 V9 双端潜空间尾锁防漂移（默认 true）" },
                        "emotion_mode": { "type": "string", "description": "可选：音色情绪解耦模式（natural | t8mars_explosive | t8mars_fury | t8mars_weeping）" },
                        "character_card": { "type": "string", "description": "可选：交错式毛玻璃角色出场名片（格式：\"姓名|头衔身份\"）" }
                    },
                    "required": ["episode_id", "scene_id"]
                }
            },
            {
                "name": "studio_search_poses",
                "description": "检索并规划通用 1,439 姿态动作库 (`ai-pose-gallery.pages.dev` / `POSE-DB-01`) 与 `17k` 黄金相位轨迹锚点（支持中/英/日语义搜索、4大姿态系统、5大摄影机角度切换，以及现代都市剧、时尚写真模特、动作武打 V3 ProSeam、数字人口播、历史正剧等跨题材预设轨迹）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": { "type": "string", "description": "可选：搜索关键词（如 坐姿、S曲线、撩发、格斗、双人对视、单膝跪、回眸）" },
                        "system": { "type": "string", "description": "可选：姿态系统过滤：standard (全身标准) | sexy (时尚/写真) | upper (上半身/口播特写) | pair (双人互动/对手戏)" },
                        "angle": { "type": "string", "description": "可选：机位角度过滤：front (正面) | side (90度正侧脸) | diag (3/4斜侧) | low (仰拍) | high (俯拍)" },
                        "preset": { "type": "string", "description": "可选：直接生成跨题材 17k 轨迹方案：modern_drama_confrontation | modern_seated_table_slam | fashion_gravure_s_curve_flow | fashion_gravure_recline_allure | action_martial_proseam_valley | digital_human_explainer_koubo | historical_epic_command_oath | romance_couple_interaction" },
                        "poses": { "type": "array", "items": { "type": "string" }, "description": "可选：指定一组 pose_id 自动计算 17k 相位帧索引并按需下载缓存姿态原图" },
                        "frames": { "type": "integer", "description": "可选：目标帧数（自动对齐至 39/90/141/192 零音频悬垂黄金帧，默认 90）" },
                        "limit": { "type": "integer", "description": "可选：返回条数上限（默认 12）" }
                    }
                }
            },
            {
                "name": "studio_compile_h3_v25_prompts",
                "description": "将指定剧集编译为 MiniMax-H3 v2.5 / V9 官方 `Ref2VA` 六段式生产节点包（自动执行 Speech-Active Gating 仅挂载当前开口角色 `<Audio 1>`、注入 `T8mars` 情绪解耦、`17k+5` 黄金帧契约、`17k` 姿态锚点相位锁定、`V9_TailLock` 双端尾锁与 `MotionContext` 22帧潜空间接力配置）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep01_crossing" }
                    },
                    "required": ["episode_id"]
                }
            },
            {
                "name": "studio_replace_all_scenes",
                "description": "批量替换或新建整集的所有分镜列表 (`movie.toml`) 并可选同步更新文学剧本 (`script.md`)，自动执行 L1-L5 门禁检查。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep01_crossing 或新剧集 ep04_chencang" },
                        "title": { "type": "string", "description": "剧集标题" },
                        "script_markdown": { "type": "string", "description": "可选：同步更新的 script.md 内容" },
                        "scenes": {
                            "type": "array",
                            "description": "完整分镜对象数组",
                            "items": { "type": "object" }
                        }
                    },
                    "required": ["episode_id", "title", "scenes"]
                }
            },
            {
                "name": "studio_compile_seedance_prompts",
                "description": "将指定剧集编译为 Seedance 2.0 Pro (720p) 标准多模态生产节点清单（自动按『片段 × 可辨识元素矩阵』连接人物四视图卡、空间图、武魂道具图与实际开口说话角色的 48kHz 音色 WAV，自动注入无字幕锁与全程无背景音乐锁）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep01_crossing" }
                    },
                    "required": ["episode_id"]
                }
            },
            {
                "name": "studio_submit_render_job",
                "description": "向工作室渲染队列提交单镜或整集视频生成任务（支持 local H3 免费预演、veo-fast、veo-quality 等），自动过 L1-L5 门禁校验。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集 ID" },
                        "scene_id": { "type": "string", "description": "可选：单个镜头 ID；不传则渲染整集" },
                        "model": { "type": "string", "description": "模型：h3 | veo-lite | veo-fast | omni-flash | veo-quality" },
                        "dry_run": { "type": "boolean", "description": "可选：是否仅做零积分 Dry-Run 预检" },
                        "admin_pin": { "type": "string", "description": "可选：使用 veo-quality 时的管理员审批 PIN (默认 2280)" }
                    },
                    "required": ["episode_id", "model"]
                }
            },
            {
                "name": "studio_export_jianying_draft",
                "description": "一键导出非破坏性 5 轨《剪映专业版 / CapCut 多轨工程草稿 (`draft_content.json`)》与独立 SRT 字幕文件。所有原片自动应用片尾去毛刺微剪 (`trim_end_sec`)，并将对白 (Qwen3-TTS)、动作音效 (MMAudio/H3)、闪避配乐 (ACE-Step 1.5 Sidechain Ducking) 与字幕分离到独立轨道，方便后期任意修剪。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep01_crossing, ep04_beifa" }
                    },
                    "required": ["episode_id"]
                }
            },
            {
                "name": "studio_synthesize_voiceover",
                "description": "使用本机 Qwen3-TTS (Qwen3-TTS-12Hz-1.7B-Base 零样本克隆 + Qwen3-TTS-12Hz-1.7B-VoiceDesign 情绪声音设计) 为指定剧集或单个分镜合成电影级中文对白配音 (`output/voiceovers/<episode_id>/<scene_id>.wav`)。支持自动读取角色绑定的 48kHz 音色锚点，或传入 instruct 执行情绪化声音定制。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep04_beifa" },
                        "scene_id": { "type": "string", "description": "可选：仅合成指定镜头 ID；不传则合成整集所有带台词镜头" },
                        "instruct": { "type": "string", "description": "可选：自然语言情绪/声线指导（传入后自动启用 Qwen3-TTS-VoiceDesign 模型）" }
                    },
                    "required": ["episode_id"]
                }
            },
            {
                "name": "studio_compose_bgm",
                "description": "使用本机 ACE-Step 1.5 Turbo 音乐大模型生成 48kHz 立体声电影级交响/国风配乐 (`output/bgm/<episode_id>_acestep_bgm.wav`)，已内置 GPU DiT + Zen 5 CPU OobleckVAE 防崩溃架构。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep04_beifa" },
                        "prompt": { "type": "string", "description": "音乐风格、配器与情绪提示词（英文或中文）" },
                        "duration_sec": { "type": "number", "description": "可选：音乐时长（秒，默认 20.0）" },
                        "seed": { "type": "integer", "description": "可选：随机种子（默认 42）" }
                    },
                    "required": ["episode_id"]
                }
            },
            {
                "name": "studio_master_episode",
                "description": "将指定剧集已生成的镜头视频、Qwen3-TTS 对白音轨与 ACE-Step 1.5 电影配乐执行全自动非破坏性母带混音（含 -12dB Sidechain 自动闪避压限），输出最终成片 `output/final_episodes/<episode_id>_local_h3_master.mp4`。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "剧集目录名，如 ep04_beifa" }
                    },
                    "required": ["episode_id"]
                }
            },
            {
                "name": "studio_notify_reply",
                "description": "当 Agent 通过 MCP 完成剧本、资产、分镜修改或导出后，调用此工具向网页端实时推送一条完成通知与修改说明，网页会自动刷新最新状态！",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "episode_id": { "type": "string", "description": "已操作的剧集 ID" },
                        "summary": { "type": "string", "description": "向创作者展示的友好执行总结" }
                    },
                    "required": ["episode_id", "summary"]
                }
            }
        ]
    })
}

async fn mcp_tools_call(paths: &WorkspacePaths, params: &Value) -> Result<Value, String> {
    let name = params
        .get("name")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "Missing tool name".to_string())?;
    let args = params.get("arguments").cloned().unwrap_or_else(|| json!({}));

    let text_res = match name {
        "studio_list_projects" => {
            let mut list = Vec::new();
            for pp in WorkspacePaths::discover_all_projects(&paths.root_dir) {
                let pid = pp.active_project_id.clone();
                let pl = DirectorLinter::new(&pp.base_dir);
                let pc = StoryboardCompiler::from_profiles_path(&pp.characters_file);
                list.push(json!({
                    "project_id": pid,
                    "name": if pl.fact_sheet.project.name.is_empty() { pid.clone() } else { pl.fact_sheet.project.name },
                    "style_preset": pl.fact_sheet.project.style_preset,
                    "production_mode": pl.fact_sheet.project.production_mode,
                    "character_count": pc.characters.len(),
                    "is_active": paths.active_project_id == pid,
                }));
            }
            serde_json::to_string_pretty(&list).unwrap_or_default()
        }

        "studio_select_or_create_project" => {
            let pid = args
                .get("project_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing project_id")?;
            let safe_id: String = pid
                .chars()
                .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
                .collect::<String>()
                .to_lowercase();
            if safe_id.is_empty() {
                return Err("Invalid project_id".to_string());
            }
            let new_paths = WorkspacePaths::for_project(&paths.root_dir, &safe_id);
            new_paths.ensure_dirs().map_err(|e| e.to_string())?;

            if !new_paths.fact_sheet_file.exists() {
                let preset_id = args
                    .get("style_preset")
                    .and_then(|v| v.as_str())
                    .unwrap_or("live_action_arri");
                let presets = builtin_style_presets();
                let preset = presets
                    .iter()
                    .find(|p| p.id == preset_id)
                    .unwrap_or(&presets[0]);

                let mut fs = FactSheet::default();
                fs.project = ProjectMeta {
                    id: safe_id.clone(),
                    name: args
                        .get("name")
                        .and_then(|v| v.as_str())
                        .unwrap_or(&safe_id)
                        .to_string(),
                    pipeline_type: "AI_Studio_L1_L5".to_string(),
                    episode_aspect: args
                        .get("aspect")
                        .and_then(|v| v.as_str())
                        .unwrap_or("16:9")
                        .to_string(),
                    historical_anchor_year: args
                        .get("subtitle")
                        .and_then(|v| v.as_str())
                        .unwrap_or("AI 剧情影像项目")
                        .to_string(),
                    production_mode: preset.mode.clone(),
                    style_preset: preset.id.clone(),
                    no_subtitles_lock: true,
                };
                fs.style_lock = StyleLock {
                    camera_base: preset.camera_base.clone(),
                    lighting_base: preset.lighting_base.clone(),
                    film_stock: preset.film_stock.clone(),
                    global_suffix: preset.global_suffix.clone(),
                    modern_suffix: String::new(),
                    negative_prompt: preset.negative_prompt.clone(),
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
                        description: "主场景默认三维空间拓扑".to_string(),
                        camera_left: "key light window on camera-left".to_string(),
                        center_foreground: "main subject stage in center foreground".to_string(),
                        camera_right: "background depth on camera-right".to_string(),
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
                        h3_audio_cue: "Warm indoor room tone".to_string(),
                    },
                );
                let toml_str = toml::to_string_pretty(&fs).map_err(|e| e.to_string())?;
                std::fs::write(&new_paths.fact_sheet_file, toml_str).map_err(|e| e.to_string())?;
            }

            std::fs::write(paths.root_dir.join(".active_project"), &safe_id)
                .map_err(|e| e.to_string())?;
            notify_running_web_server(
                "all",
                &format!("📁 Agent 已切换/创建活跃项目为 `{}`", safe_id),
            )
            .await;
            format!("✅ 已切换活跃项目为 `{}` (目录: `{}`)", safe_id, new_paths.base_dir.display())
        }

        "studio_get_assets" => {
            let linter = DirectorLinter::new(&paths.base_dir);
            let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
            serde_json::to_string_pretty(&json!({
                "project_id": paths.active_project_id,
                "project_meta": linter.fact_sheet.project,
                "style_lock": linter.fact_sheet.style_lock,
                "style_presets": builtin_style_presets(),
                "voice_presets": builtin_voice_presets(),
                "characters": compiler.characters,
                "continuity_props": linter.fact_sheet.continuity_props,
                "spatial_rooms": linter.fact_sheet.spatial_rooms,
                "acoustic_spaces": linter.fact_sheet.acoustic_spaces,
            }))
            .unwrap_or_default()
        }

        "studio_apply_style_preset" => {
            let preset_id = args
                .get("preset_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing preset_id")?;
            let presets = builtin_style_presets();
            let p = presets
                .iter()
                .find(|x| x.id == preset_id)
                .ok_or_else(|| format!("未找到画风预设: {}", preset_id))?;

            let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
                let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
                toml::from_str(&s).unwrap_or_default()
            } else {
                FactSheet::default()
            };
            fs.project.style_preset = p.id.clone();
            fs.project.production_mode = args
                .get("production_mode")
                .and_then(|v| v.as_str())
                .unwrap_or(&p.mode)
                .to_string();
            if let Some(no_sub) = args.get("no_subtitles_lock").and_then(|v| v.as_bool()) {
                fs.project.no_subtitles_lock = no_sub;
            }
            fs.style_lock.camera_base = p.camera_base.clone();
            fs.style_lock.lighting_base = p.lighting_base.clone();
            fs.style_lock.film_stock = p.film_stock.clone();
            fs.style_lock.global_suffix = p.global_suffix.clone();
            fs.style_lock.negative_prompt = p.negative_prompt.clone();

            let serialized = toml::to_string_pretty(&fs).map_err(|e| e.to_string())?;
            std::fs::write(&paths.fact_sheet_file, serialized).map_err(|e| e.to_string())?;
            notify_running_web_server(
                "all",
                &format!("🎨 Agent 已将项目画风切换为『{}』", p.name),
            )
            .await;
            format!("✅ 已将项目画风切换为『{}』({})", p.name, p.id)
        }

        "studio_upsert_character" => {
            let char_name = args
                .get("name")
                .and_then(|v| v.as_str())
                .ok_or("Missing name")?;
            let appearance = args
                .get("appearance")
                .and_then(|v| v.as_str())
                .ok_or("Missing appearance")?;
            let mut profiles: ProfilesToml = if paths.characters_file.exists() {
                let s = std::fs::read_to_string(&paths.characters_file).unwrap_or_default();
                toml::from_str(&s).unwrap_or_default()
            } else {
                ProfilesToml::default()
            };
            let new_char = CharacterProfile {
                name: char_name.to_string(),
                tier: args
                    .get("tier")
                    .and_then(|v| v.as_str())
                    .unwrap_or("protagonist")
                    .to_string(),
                appearance: appearance.to_string(),
                appearance_modern: None,
                appearance_ancient: None,
                voice: args
                    .get("voice")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string())
                    .or_else(|| Some("温厚沉稳青年男声-v1".to_string())),
                ref_image: args
                    .get("ref_image")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string()),
                ref_image_modern: None,
                ref_image_ancient: None,
                turnaround_ref_image: args
                    .get("turnaround_ref_image")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string()),
                costume_version: args
                    .get("costume_version")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string())
                    .or_else(|| Some("v1_base".to_string())),
            };
            if let Some(ex) = profiles.characters.iter_mut().find(|c| c.name == char_name) {
                *ex = new_char;
            } else {
                profiles.characters.push(new_char);
            }
            if let Some(parent) = paths.characters_file.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            let serialized = toml::to_string_pretty(&profiles).map_err(|e| e.to_string())?;
            std::fs::write(&paths.characters_file, serialized).map_err(|e| e.to_string())?;
            notify_running_web_server(
                "all",
                &format!("🎭 Agent 已更新角色资产 `@{}`", char_name),
            )
            .await;
            format!("✅ 已保存角色资产 `@{}`", char_name)
        }

        "studio_upsert_prop" => {
            let prop_id = args
                .get("prop_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing prop_id")?;
            let prop_name = args
                .get("name")
                .and_then(|v| v.as_str())
                .ok_or("Missing name")?;
            let desc = args
                .get("description")
                .and_then(|v| v.as_str())
                .ok_or("Missing description")?;
            let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
                let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
                toml::from_str(&s).unwrap_or_default()
            } else {
                FactSheet::default()
            };
            fs.continuity_props.insert(
                prop_id.to_string(),
                ContinuityProp {
                    name: prop_name.to_string(),
                    category: args
                        .get("category")
                        .and_then(|v| v.as_str())
                        .unwrap_or("prop")
                        .to_string(),
                    description: desc.to_string(),
                    ref_image: args
                        .get("ref_image")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string()),
                    version_tag: args
                        .get("version_tag")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string())
                        .or_else(|| Some("v1_normal".to_string())),
                    owner_character: args
                        .get("owner_character")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string()),
                },
            );
            let serialized = toml::to_string_pretty(&fs).map_err(|e| e.to_string())?;
            std::fs::write(&paths.fact_sheet_file, serialized).map_err(|e| e.to_string())?;
            notify_running_web_server(
                "all",
                &format!("🗡️ Agent 已更新关键道具/连续性主体 `{}`", prop_name),
            )
            .await;
            format!("✅ 已保存关键道具/连续性主体 `{}` ({})", prop_name, prop_id)
        }

        "studio_upsert_room" => {
            let room_id = args
                .get("room_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing room_id")?;
            let mut fs: FactSheet = if paths.fact_sheet_file.exists() {
                let s = std::fs::read_to_string(&paths.fact_sheet_file).unwrap_or_default();
                toml::from_str(&s).unwrap_or_default()
            } else {
                FactSheet::default()
            };
            fs.spatial_rooms.insert(
                room_id.to_string(),
                SpatialRoom {
                    description: args
                        .get("description")
                        .and_then(|v| v.as_str())
                        .unwrap_or_default()
                        .to_string(),
                    camera_left: args
                        .get("camera_left")
                        .and_then(|v| v.as_str())
                        .unwrap_or_default()
                        .to_string(),
                    center_foreground: args
                        .get("center_foreground")
                        .and_then(|v| v.as_str())
                        .unwrap_or_default()
                        .to_string(),
                    camera_right: args
                        .get("camera_right")
                        .and_then(|v| v.as_str())
                        .unwrap_or_default()
                        .to_string(),
                    exterior_anchor_image: args
                        .get("exterior_anchor_image")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string()),
                    interior_anchor_image: args
                        .get("interior_anchor_image")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string()),
                    banned_topology_contradictions: vec![],
                },
            );
            let serialized = toml::to_string_pretty(&fs).map_err(|e| e.to_string())?;
            std::fs::write(&paths.fact_sheet_file, serialized).map_err(|e| e.to_string())?;
            notify_running_web_server(
                "all",
                &format!("📐 Agent 已更新三维房间拓扑 `{}`", room_id),
            )
            .await;
            format!("✅ 已保存三维房间拓扑 `{}`", room_id)
        }

        "studio_list_episodes" => {
            let linter = DirectorLinter::new(&paths.base_dir);
            let mut items = Vec::new();
            if let Ok(entries) = std::fs::read_dir(&paths.episodes_dir) {
                let mut dirs: Vec<_> = entries.flatten().filter(|e| e.path().is_dir()).collect();
                dirs.sort_by_key(|e| e.file_name());
                for d in dirs {
                    let ep_id = d.file_name().to_string_lossy().to_string();
                    let m_path = d.path().join("movie.toml");
                    if let Ok(raw) = std::fs::read_to_string(&m_path) {
                        if let Ok(m) = toml::from_str::<MovieManifest>(&raw) {
                            let rep = linter.lint_scenes(&ep_id, &m.scenes);
                            items.push(json!({
                                "episode_id": ep_id,
                                "title": m.title,
                                "scene_count": m.scenes.len(),
                                "lint_passed": rep.passed,
                                "error_count": rep.error_count,
                                "warning_count": rep.warning_count,
                            }));
                        }
                    }
                }
            }
            serde_json::to_string_pretty(&items).unwrap_or_default()
        }

        "studio_get_episode" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let ep_dir = paths.episodes_dir.join(ep_id);
            let m_path = ep_dir.join("movie.toml");
            let raw = std::fs::read_to_string(&m_path)
                .map_err(|e| format!("读取 movie.toml 失败: {}", e))?;
            let m: MovieManifest =
                toml::from_str(&raw).map_err(|e| format!("解析 movie.toml 失败: {}", e))?;
            let script_md = std::fs::read_to_string(ep_dir.join("script.md")).unwrap_or_default();
            let linter = DirectorLinter::new(&paths.base_dir);
            let rep = linter.lint_scenes(ep_id, &m.scenes);

            serde_json::to_string_pretty(&json!({
                "episode_id": ep_id,
                "title": m.title,
                "script_markdown": script_md,
                "scenes": m.scenes,
                "lint_report": rep,
            }))
            .unwrap_or_default()
        }

        "studio_update_script_markdown" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let script_md = args
                .get("script_markdown")
                .and_then(|v| v.as_str())
                .ok_or("Missing script_markdown")?;
            let ep_dir = paths.episodes_dir.join(ep_id);
            std::fs::create_dir_all(&ep_dir).map_err(|e| e.to_string())?;
            let script_path = ep_dir.join("script.md");
            std::fs::write(&script_path, script_md).map_err(|e| e.to_string())?;

            notify_running_web_server(
                ep_id,
                &format!("📝 Antigravity 已通过 MCP 更新 `{}` 的文学剧本 (`script.md`)", ep_id),
            )
            .await;

            format!("✅ 已成功更新 `{}/script.md` ({} 字节)", ep_id, script_md.len())
        }

        "studio_update_scene" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let scene_id = args
                .get("scene_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing scene_id")?;
            let ep_dir = paths.episodes_dir.join(ep_id);
            let m_path = ep_dir.join("movie.toml");
            let raw = std::fs::read_to_string(&m_path)
                .map_err(|e| format!("读取 movie.toml 失败: {}", e))?;
            let mut m: MovieManifest =
                toml::from_str(&raw).map_err(|e| format!("解析 movie.toml 失败: {}", e))?;

            let target = if let Some(sc) = m.scenes.iter_mut().find(|s| s.id == scene_id) {
                sc
            } else {
                m.scenes.push(SceneSpec {
                    id: scene_id.to_string(),
                    era: "ancient".to_string(),
                    framing: "medium".to_string(),
                    aspect: "16:9".to_string(),
                    duration: 8,
                    model: "veo-quality".to_string(),
                    ..Default::default()
                });
                m.scenes.last_mut().unwrap()
            };

            if let Some(v) = args.get("speaker").and_then(|v| v.as_str()) {
                target.speaker = Some(v.to_string());
            }
            if let Some(v) = args.get("line").and_then(|v| v.as_str()) {
                target.line = Some(v.to_string());
            }
            if let Some(v) = args.get("action").and_then(|v| v.as_str()) {
                target.action = v.to_string();
            }
            if let Some(v) = args.get("camera_motion").and_then(|v| v.as_str()) {
                target.camera_motion = Some(v.to_string());
            }
            if let Some(v) = args.get("ref_image").and_then(|v| v.as_str()) {
                target.ref_image = Some(v.to_string());
            }
            if let Some(v) = args.get("acoustic_space").and_then(|v| v.as_str()) {
                target.acoustic_space = Some(v.to_string());
            }
            if let Some(v) = args.get("arc_phase").and_then(|v| v.as_str()) {
                target.arc_phase = Some(v.to_string());
            }
            if let Some(v) = args.get("room_id").and_then(|v| v.as_str()) {
                target.room_id = Some(v.to_string());
            }
            if let Some(arr) = args.get("characters").and_then(|v| v.as_array()) {
                target.characters = arr
                    .iter()
                    .filter_map(|x| x.as_str().map(|s| s.to_string()))
                    .collect();
            }
            if let Some(arr) = args.get("props").and_then(|v| v.as_array()) {
                target.props = arr
                    .iter()
                    .filter_map(|x| x.as_str().map(|s| s.to_string()))
                    .collect();
            }
            if let Some(v) = args.get("shot_count").and_then(|v| v.as_u64()) {
                target.shot_count = Some(v as u32);
            }
            if let Some(v) = args.get("trim_start_sec").and_then(|v| v.as_f64()) {
                target.trim_start_sec = Some(v);
            }
            if let Some(v) = args.get("trim_end_sec").and_then(|v| v.as_f64()) {
                target.trim_end_sec = Some(v);
            }
            if let Some(v) = args.get("foley_cue").and_then(|v| v.as_str()) {
                target.foley_cue = Some(v.to_string());
            }
            if let Some(v) = args.get("bgm_mood").and_then(|v| v.as_str()) {
                target.bgm_mood = Some(v.to_string());
            }
            if let Some(arr) = args.get("pose_anchors").and_then(|v| v.as_array()) {
                target.pose_anchors = arr
                    .iter()
                    .filter_map(|x| x.as_str().map(|s| s.to_string()))
                    .collect();
            }
            if let Some(arr) = args.get("keyframe_indices").and_then(|v| v.as_array()) {
                target.keyframe_indices = arr
                    .iter()
                    .filter_map(|x| x.as_i64().map(|n| n as i32))
                    .collect();
            }
            if let Some(arr) = args.get("keyframe_strengths").and_then(|v| v.as_array()) {
                target.keyframe_strengths = arr
                    .iter()
                    .filter_map(|x| x.as_f64().map(|n| n as f32))
                    .collect();
            }
            if let Some(v) = args.get("continuity_track").and_then(|v| v.as_str()) {
                target.continuity_track = Some(v.to_string());
            }
            if let Some(v) = args.get("tail_lock_v9").and_then(|v| v.as_bool()) {
                target.tail_lock_v9 = Some(v);
            }
            if let Some(v) = args.get("emotion_mode").and_then(|v| v.as_str()) {
                target.emotion_mode = Some(v.to_string());
            }
            if let Some(v) = args.get("character_card").and_then(|v| v.as_str()) {
                target.character_card = Some(v.to_string());
            }

            let out_dir = paths.raw_clips_dir.join(ep_id);
            let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
            compiler
                .write_movie_file(
                    &m_path,
                    &m.title,
                    &m.scenes,
                    &m.project,
                    Some(&out_dir),
                    Some("16:9"),
                )
                .map_err(|e| e.to_string())?;

            let linter = DirectorLinter::new(&paths.base_dir);
            let rep = linter.lint_scenes(ep_id, &m.scenes);

            notify_running_web_server(
                ep_id,
                &format!(
                    "🎬 Agent 已通过 MCP 修改镜头 `{}` ({})",
                    scene_id,
                    if rep.passed {
                        "✅ L1-L5 0 Error 通过"
                    } else {
                        "⚠️ 存在门禁提示"
                    }
                ),
            )
            .await;

            rep.formatted_text
        }

        "studio_replace_all_scenes" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let title = args
                .get("title")
                .and_then(|v| v.as_str())
                .ok_or("Missing title")?;
            let scenes_val = args.get("scenes").ok_or("Missing scenes array")?;
            let scenes: Vec<SceneSpec> = serde_json::from_value(scenes_val.clone())
                .map_err(|e| format!("scenes 格式错误: {}", e))?;

            let ep_dir = paths.episodes_dir.join(ep_id);
            std::fs::create_dir_all(&ep_dir).map_err(|e| e.to_string())?;

            if let Some(md) = args.get("script_markdown").and_then(|v| v.as_str()) {
                let _ = std::fs::write(ep_dir.join("script.md"), md);
            }

            let m_path = ep_dir.join("movie.toml");
            let out_dir = paths.raw_clips_dir.join(ep_id);
            let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
            compiler
                .write_movie_file(
                    &m_path,
                    title,
                    &scenes,
                    &format!("{}_{}", paths.active_project_id, ep_id),
                    Some(&out_dir),
                    Some("16:9"),
                )
                .map_err(|e| e.to_string())?;

            let linter = DirectorLinter::new(&paths.base_dir);
            let rep = linter.lint_scenes(ep_id, &scenes);

            notify_running_web_server(
                ep_id,
                &format!("✨ Agent 已通过 MCP 更新整集《{}》分镜工程！", title),
            )
            .await;

            rep.formatted_text
        }

        "studio_compile_seedance_prompts" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let ep_dir = paths.episodes_dir.join(ep_id);
            let m_path = ep_dir.join("movie.toml");
            let raw = std::fs::read_to_string(&m_path)
                .map_err(|e| format!("读取 movie.toml 失败: {}", e))?;
            let m: MovieManifest =
                toml::from_str(&raw).map_err(|e| format!("解析 movie.toml 失败: {}", e))?;
            let linter = DirectorLinter::new(&paths.base_dir);
            let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
            let nodes: Vec<_> = m
                .scenes
                .iter()
                .map(|sc| compiler.compile_seedance_prompt(sc, &linter.fact_sheet))
                .collect();

            let out_json = json!({
                "episode_id": ep_id,
                "title": m.title,
                "production_mode": linter.fact_sheet.project.production_mode,
                "style_preset": linter.fact_sheet.project.style_preset,
                "seedance_nodes": nodes,
            });
            let save_path = ep_dir.join("seedance_prompts.json");
            let _ = std::fs::write(
                &save_path,
                serde_json::to_string_pretty(&out_json).unwrap_or_default(),
            );
            notify_running_web_server(
                ep_id,
                &format!("🎯 Agent 已编译生成 `{}` 的 Seedance 2.0 Pro 多模态节点包", ep_id),
            )
            .await;
            serde_json::to_string_pretty(&out_json).unwrap_or_default()
        }

        "studio_search_poses" => {
            let script_path = paths.root_dir.join("scripts").join("pose_library_engine.py");
            let mut cmd = Command::new("python");
            cmd.arg("-X").arg("utf8").arg(&script_path);
            if let Some(preset) = args.get("preset").and_then(|v| v.as_str()).filter(|s| !s.is_empty()) {
                cmd.arg("--preset").arg(preset);
            } else if let Some(poses) = args.get("poses").and_then(|v| v.as_array()).filter(|a| !a.is_empty()) {
                cmd.arg("--poses");
                for p in poses {
                    if let Some(ps) = p.as_str() {
                        cmd.arg(ps);
                    }
                }
            } else {
                if let Some(q) = args.get("query").and_then(|v| v.as_str()) {
                    cmd.arg("--query").arg(q);
                }
                if let Some(sys) = args.get("system").and_then(|v| v.as_str()) {
                    cmd.arg("--system").arg(sys);
                }
                if let Some(ang) = args.get("angle").and_then(|v| v.as_str()) {
                    cmd.arg("--angle").arg(ang);
                }
                if let Some(lim) = args.get("limit").and_then(|v| v.as_u64()) {
                    cmd.arg("--limit").arg(lim.to_string());
                }
            }
            if let Some(fr) = args.get("frames").and_then(|v| v.as_u64()) {
                cmd.arg("--frames").arg(fr.to_string());
            }
            let out = cmd.output().await.map_err(|e| format!("调用 pose_library_engine.py 失败: {}", e))?;
            let stdout = String::from_utf8_lossy(&out.stdout).to_string();
            let stderr = String::from_utf8_lossy(&out.stderr).to_string();
            if !out.status.success() {
                return Err(format!("检索姿态库异常: {}\n{}", stdout, stderr));
            }
            stdout
        }

        "studio_compile_h3_v25_prompts" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let ep_dir = paths.episodes_dir.join(ep_id);
            let m_path = ep_dir.join("movie.toml");
            let raw = std::fs::read_to_string(&m_path)
                .map_err(|e| format!("读取 movie.toml 失败: {}", e))?;
            let m: MovieManifest =
                toml::from_str(&raw).map_err(|e| format!("解析 movie.toml 失败: {}", e))?;
            let linter = DirectorLinter::new(&paths.base_dir);
            let compiler = StoryboardCompiler::from_profiles_path(&paths.characters_file);
            let nodes: Vec<_> = m
                .scenes
                .iter()
                .map(|sc| compiler.compile_h3_v25_prompt(sc, &linter.fact_sheet))
                .collect();

            let out_json = json!({
                "episode_id": ep_id,
                "title": m.title,
                "engine": "minimax-h3-v2.5-universal",
                "production_mode": linter.fact_sheet.project.production_mode,
                "style_preset": linter.fact_sheet.project.style_preset,
                "h3_v25_nodes": nodes,
            });
            let save_path = ep_dir.join("h3_v25_prompts.json");
            let _ = std::fs::write(
                &save_path,
                serde_json::to_string_pretty(&out_json).unwrap_or_default(),
            );
            notify_running_web_server(
                ep_id,
                &format!("🚀 Agent 已编译生成 `{}` 的 MiniMax-H3 v2.5 通用 Ref2VA 节点包", ep_id),
            )
            .await;
            serde_json::to_string_pretty(&out_json).unwrap_or_default()
        }

        "studio_submit_render_job" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let model = args
                .get("model")
                .and_then(|v| v.as_str())
                .unwrap_or("h3");
            let scene_id = args.get("scene_id").and_then(|v| v.as_str());
            let dry_run = args.get("dry_run").and_then(|v| v.as_bool()).unwrap_or(false);
            let admin_pin = args.get("admin_pin").and_then(|v| v.as_str());

            let port: u16 = std::env::var("DIRECTOR_PORT")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(18443);
            let pw = std::env::var("DIRECTOR_PASSWORD").unwrap_or_else(|_| "duanshipin123".to_string());
            let token = {
                use std::hash::{Hash, Hasher};
                let mut hasher = std::collections::hash_map::DefaultHasher::new();
                director_core::config::SYSTEM_AUTH_SALT.hash(&mut hasher);
                pw.hash(&mut hasher);
                format!("studio_auth_{:x}", hasher.finish())
            };

            let url = format!("http://127.0.0.1:{}/api/v1/render/jobs", port);
            let client = reqwest::Client::builder().no_proxy().build().map_err(|e| e.to_string())?;
            let resp = client
                .post(&url)
                .header("Authorization", format!("Bearer {}", token))
                .json(&json!({
                    "requested_by": "AI Agent (MCP/Skill)",
                    "episode_id": ep_id,
                    "scene_id": scene_id,
                    "model": model,
                    "dry_run": dry_run,
                    "admin_pin": admin_pin,
                }))
                .send()
                .await
                .map_err(|e| format!("提交渲染任务到工作台失败: {}", e))?;

            let body = resp.text().await.unwrap_or_default();
            format!("🚀 渲染任务已提交至工作台队列:\n{}", body)
        }

        "studio_export_jianying_draft" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let ep_dir = paths.episodes_dir.join(ep_id);
            let m_path = ep_dir.join("movie.toml");
            let raw = std::fs::read_to_string(&m_path)
                .map_err(|e| format!("读取 movie.toml 失败: {}", e))?;
            let m: MovieManifest =
                toml::from_str(&raw).map_err(|e| format!("解析 movie.toml 失败: {}", e))?;
            let engine = MasteringEngine::new(&paths.base_dir);
            let draft_dir = engine
                .export_jianying_multitrack_draft(ep_id, &m.title, &m.scenes)
                .map_err(|e| e.to_string())?;

            notify_running_web_server(
                ep_id,
                &format!(
                    "🎬 Agent 已导出《{}》非破坏性 5 轨剪映专业版草稿与独立 SRT 字幕包",
                    m.title
                ),
            )
            .await;

            serde_json::to_string_pretty(&json!({
                "ok": true,
                "episode_id": ep_id,
                "draft_dir": draft_dir.to_string_lossy(),
                "draft_content_json": draft_dir.join("draft_content.json").to_string_lossy(),
                "srt_subtitle_file": draft_dir.join(format!("{}.srt", ep_id)).to_string_lossy(),
            }))
            .unwrap_or_default()
        }

        "studio_Notify_Placeholder_DoNotUse" => String::new(),

        "studio_synthesize_voiceover" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let scene_id = args.get("scene_id").and_then(|v| v.as_str());
            let instruct = args.get("instruct").and_then(|v| v.as_str());
            let engine = director_engines::H3Engine::new(&paths.root_dir);
            let (ok, stdout, stderr) = engine
                .synthesize_voiceovers(&paths.base_dir, ep_id, scene_id, instruct)
                .await
                .map_err(|e| e.to_string())?;
            if !ok {
                return Err(format!("Qwen3-TTS 语音合成失败:\n{}\n{}", stdout, stderr));
            }
            notify_running_web_server(
                ep_id,
                &format!("🎙️ Agent 已通过本机 Qwen3-TTS 完成 `{}` 角色配音合成！", ep_id),
            )
            .await;
            stdout
        }

        "studio_compose_bgm" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let prompt = args
                .get("prompt")
                .and_then(|v| v.as_str())
                .unwrap_or("Cinematic dramatic orchestral film score, emotional strings and deep atmospheric percussion building into a grand thematic crescendo, 48kHz stereo");
            let duration_sec = args
                .get("duration_sec")
                .and_then(|v| v.as_f64())
                .unwrap_or(20.0);
            let seed = args.get("seed").and_then(|v| v.as_i64()).unwrap_or(42);
            let engine = director_engines::H3Engine::new(&paths.root_dir);
            let (ok, stdout, stderr) = engine
                .compose_bgm(&paths.base_dir, ep_id, prompt, duration_sec, seed)
                .await
                .map_err(|e| e.to_string())?;
            if !ok {
                return Err(format!("ACE-Step 1.5 BGM 生成失败:\n{}\n{}", stdout, stderr));
            }
            notify_running_web_server(
                ep_id,
                &format!("🎵 Agent 已通过本机 ACE-Step 1.5 生成 `{}` 48kHz 电影配乐！", ep_id),
            )
            .await;
            stdout
        }

        "studio_master_episode" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .ok_or("Missing episode_id")?;
            let engine = director_engines::H3Engine::new(&paths.root_dir);
            let (ok, stdout, stderr) = engine
                .master_episode_local(&paths.base_dir, ep_id)
                .await
                .map_err(|e| e.to_string())?;
            if !ok {
                return Err(format!("母带混音合成失败:\n{}\n{}", stdout, stderr));
            }
            notify_running_web_server(
                ep_id,
                &format!("🎞️ Agent 已完成 `{}` 母带混音与成片合成 (含自动闪避配乐)！", ep_id),
            )
            .await;
            stdout
        }

        "studio_notify_reply" => {
            let ep_id = args
                .get("episode_id")
                .and_then(|v| v.as_str())
                .unwrap_or("ep01_crossing");
            let summary = args
                .get("summary")
                .and_then(|v| v.as_str())
                .unwrap_or("已完成剧本与分镜修改");
            notify_running_web_server(ep_id, &format!("🤖 [Antigravity 主创已完成修改] {}", summary))
                .await;
            format!("✅ 已向网页端实时推送通知: {}", summary)
        }

        _ => return Err(format!("Unknown tool: {}", name)),
    };

    Ok(json!({
        "content": [
            {
                "type": "text",
                "text": text_res
            }
        ]
    }))
}

async fn notify_running_web_server(episode_id: &str, message: &str) {
    let port: u16 = std::env::var("DIRECTOR_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(18443);
    let url = format!("http://127.0.0.1:{}/api/v1/agent/mcp-webhook", port);
    if let Ok(client) = reqwest::Client::builder().no_proxy().build() {
        let _ = client
            .post(&url)
            .json(&json!({
                "episode_id": episode_id,
                "message": message,
            }))
            .send()
            .await;
    }
}
