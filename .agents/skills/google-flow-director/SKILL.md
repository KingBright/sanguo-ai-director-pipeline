---
name: google-flow-director
description: 全能 AI 剧情影像（Cinematic Drama）与短视频工业化制作工作流（整合 s1dashu/director Cinematic Drama 资产与分镜体系 + L1-L5 五层导演门禁 + Seedance 2.0 / Google Veo 3.1 / 本机 Strix Halo H3 多引擎路由 + 开源 IndexTTS-2/MMAudio/ACE-Step 非破坏性 5 轨剪映母带管线）。支持 Antigravity、Codex、Claude Code 通过 MCP 与 CLI 全自动一条龙执行。
---

# AetherDirector Studio (天枢 AI 影视工业工作台) 全能剧情影像与多引擎一条龙制片 Skill (`google-flow-director` v3.5)

本技能将 **`AetherDirector Studio (天枢 AI 影视工业工作台)`** 平台能力、**`s1dashu/director` Cinematic Drama（剧情影像）工业级防漂移资产规范**、**`MiniMax-H3 v2.5 / V9` 极致音画同步架构**、**`POSE-DB-01` (1,439 姿态库 + 17k 黄金相位锚定)**、**L1–L5 五层导演决策门禁**以及**本机 96GB 大显存开源非破坏性分轨母带管线（Qwen3-TTS / IndexTTS-2 + MMAudio + ACE-Step + 剪映 5 轨草稿直出）**融为一体。

无论是 **Antigravity**、**Codex** 还是 **Claude Code**，均可通过 **MCP 工具集 (`aether-director-studio`)** 或 **单文件 CLI (`director-server.exe cli <tool_name> '<json>'`)** 零人工干预完成从「立项 $\rightarrow$ 锁画风 $\rightarrow$ 检索 1439 姿态库与 17k 轨迹锚点 $\rightarrow$ 建角色四视图/换装卡/武魂道具/17款音色锚点/三维房间 $\rightarrow$ 写剧本与分镜 $\rightarrow$ 编译 H3 v2.5 Ref2VA / Seedance 2.0 / Veo 节点并渲染 $\rightarrow$ 导出非破坏性剪映 5 轨工程与成片」的全链路闭环。

---

## 1. Agent 一条龙调用方式（MCP + CLI 双通道原生支持）

### 通道 A：MCP 原生工具调用（推荐 Antigravity / Claude Code / Codex MCP 模式）
服务器同时提供 `stdio` (`director-server.exe mcp-stdio`) 与 `HTTP Streamable MCP` (`http://127.0.0.1:18443/mcp`) 两种标准接入，内置 **16 个全生命周期 MCP 工具**：

| 阶段 | MCP 工具名 | 核心职责 |
| :--- | :--- | :--- |
| **1. 项目与画风锁** | `studio_list_projects` | 列出所有短视频/漫剧项目及当前激活状态 |
| | `studio_select_or_create_project` | 切换或新建独立隔离项目 (`projects/<id>/`)，初始化默认画风与空间 |
| | `studio_apply_style_preset` | 一键锁定验证画风：`live_action_arri`（真人电影 ARRI）、`semi_realistic_3d_chinese_animation`（半写实 3D 国漫）、`semi_realistic_eastern_dark_fantasy_3d`（东方奇幻暗黑 3D）、`storytime_2d_handdrawn`（2D 解说漫剧）及**项目级无字幕锁** |
| **2. 连续性资产建立** | `studio_get_assets` | 读取当前项目全部资产、4 大画风预设与 **17 款 48kHz 标准中英文音色库** |
| | `studio_upsert_character` | 建立分级角色资产（`protagonist` 主角 / `supporting` 配角 / `extra` 路人）、绑定 9:16 立绘、**16:9 纯白底四视图卡 (`turnaround_ref_image`)**、**图生图换装版本 (`costume_version`)** 与 **48kHz 音色锚点 (`voice`)** |
| | `studio_upsert_prop` | 建立独立连续性主体：**武魂、召唤物、神兵武器、核心信物 (`[continuity_props]`)** 及形态版本 |
| | `studio_upsert_room` | 建立跨镜头**三维空间拓扑锁 (`[spatial_rooms]`)**，锁定左/中/右陈设坐标与内外景锚点 |
| **3. 剧本与分镜工程** | `studio_list_episodes` | 列出当前项目所有剧集及 L1–L5 门禁状态 |
| | `studio_get_episode` | 读取指定剧集的 `script.md`、`movie.toml` 分镜与门禁质检报告 |
| | `studio_update_script_markdown` | 写入或修改定稿文学剧本 (`script.md`) |
| | `studio_update_scene` | 单镜精细编辑（含 `shot_count` 一镜多切数、`trim_start_sec`/`trim_end_sec` 微剪去毛刺、`foley_cue` 动作拟音、`bgm_mood` 等）并自动执行 L1–L5 质检 |
| | `studio_replace_all_scenes` | 批量写入整集分镜 (`movie.toml`) 并自动运行 `DirectorLinter` |
| **4. 渲染与后期交付** | `studio_compile_seedance_prompts` | 按「片段 × 可辨识元素矩阵」自动生成 **Seedance 2.0 Pro (720p)** 多模态节点 JSON（自动过滤未出镜资产与闭嘴角色音频） |
| | `studio_submit_render_job` | 提交单镜或整集渲染任务至 `h3`（本机免费）、`veo-fast` 或 `veo-quality` |
| | `studio_export_jianying_draft` | 一键导出**非破坏性 5 轨《剪映专业版 / CapCut 草稿 (`draft_content.json`)》+ 独立 `.srt` 字幕** |
| | `studio_notify_reply` | 向 Web 工作台实时推送完成通知并触发前端无感刷新 |

### 通道 B：Codex / Shell Agent 命令行直调模式 (`director-server.exe cli`)
任何支持 Shell 命令的 Agent 在项目根目录 (`c:\Users\Liang\Downloads\sanguo`) 下可直接运行：
```powershell
# 查看所有项目
.\target\release\director-server.exe cli studio_list_projects '{}'

# 创建新漫剧项目并锁定「东方奇幻暗黑 3D」画风
.\target\release\director-server.exe cli studio_select_or_create_project '{\"project_id\":\"dark_xianxia\",\"name\":\"玄冥剑尊\",\"style_preset\":\"semi_realistic_eastern_dark_fantasy_3d\"}'

# 编译 Seedance 2.0 Pro 15秒多模态节点包
.\target\release\director-server.exe cli studio_compile_seedance_prompts '{\"episode_id\":\"ep01_awakening\"}'

# 导出剪映 5 轨非破坏性工程包与 SRT 字幕
.\target\release\director-server.exe cli studio_export_jianying_draft '{\"episode_id\":\"ep01_awakening\"}'
```

---

## 2. Cinematic Drama（剧情影像）核心资产与分镜铁律

剧情制作先完成故事、人物动机和对白表演，再按试演安排镜头。可使用同仓库的 `director-story` 技能执行这一流程。大致时长用于控制故事体量，不用于倒推每句字数；固定角色声线与当句情绪分别设计。

1. **角色三级制度与两步法四视图人物卡**：
   - **主角 (`protagonist`) / 跨片段配角 (`supporting`)**：先用 `GPT Image 2` / `Flux` 生成 **9:16 竖版正面直立全身候选图**；确认后必须以该图走 **图生图 (`Img2Img`)** 生成 **16:9 纯白背景、无文字四视图人物卡**（左侧大尺寸正脸近照 + 右侧正/侧/背全身等比视图）。
   - **干净常服铁律**：人物卡只展示常规干净状态，**严禁把某场戏的雨水、泥污、血迹、战损或法术特效画进基础人物卡**；临时战损只在当场视频 Prompt 中描述。
   - **换装必须走图生图 (`costume_version`)**：角色换装或跨时期变化时，必须基于已确认人物卡走图生图派生新版本，严禁仅靠文字重抽导致换脸。
   - **人名与阶位防读飘规范**：固定角色名优先使用 2–3 个常用汉字；等级体系避免连续拉丁字母（如 `SSS/S/F`），统一采用中文阶位（如“凡阶、天阶、神阶”）。
2. **武魂 / 召唤物 / 关键道具独立资产化 (`[continuity_props]`)**：
   - 凡跨片段反复出现或承担关键动作的武魂、召唤兽、神兵、核心信物，均建立干净无遮挡的独立参考图，并在出场分镜的 `props` 数组中显式挂载。
3. **「片段 × 可辨识元素」精准连接矩阵**：
   - 每个片段**只挂载本片段实际出镜的人物、空间和武魂道具**；
   - **只连接本片段实际开口说话的角色的 48kHz 音色参考 WAV**（出场但闭嘴的角色绝不挂载音频参考，防止串台抢话）。
4. **先试演，再分镜**：
   - 句式、长短、停顿与语气服务于人物目标和情节。保留需要絮叨、抢话或惜字的差异，不统一成短句。
   - 根据实际声音安排镜头，允许对白跨说话者与听者镜头。为呼吸、动作和反应留空间；不足时补镜或调整故事，禁止加速重采样、截词和局部冻结/像素嘴部变形。
   - 自动运动量、对比度和音量相关性仅作诊断，不能代替完整故事与声画验收。
5. **项目级无字幕锁与无背景音乐原片锁**：
   - 原片生成统一注入：`全程不生成任何字幕、旁白文字、对白文字、标题、角色名条或其他屏幕叠字，所有信息只通过画面与声音表达。全程无背景音乐。`

---

## 3. 内置 17 款 48kHz / 16-bit PCM 标准音色库 (`assets/voices/`)

所有音色均位于 `assets/voices/<id>.wav`，可直接填入角色的 `voice` 字段：
- **中文男声**：`温厚沉稳青年男声-v1`、`冷硬自信青年男声-v1`、`沉静青年男声-v1`、`明亮高亢青年音-v2`、`磁性沧桑中年男声-v1`、`慈祥睿智老年男声-v1`、`清澈自然少年音-v1`
- **中文女声**：`清透克制年轻女声-v1`、`清冷疏离年轻女声-v1`、`灵动活泼年轻女声-v1`、`温柔治愈成年女声-v1`、`冷静知性成年女声-v1`、`童真自然女童声-v1`
- **英文音色**：`English-Exhausted-Weak-Young-Male-v1`、`English-Bright-High-Pitched-Teenage-Female-v1`、`English-Bright-High-Pitched-Teenage-Male-v1`、`English-Ultra-High-Pitched-Teenage-Male-v1`

---

## 4. 本机 96GB 大显存开源「非破坏性 5 轨声画母带」架构

针对生成式视频片尾常有 0.1~0.2 秒声音毛刺或废帧、直接焊死 BGM 和字幕会导致后期修剪断拍的痛点，本工作流采用**先微剪干净原片、再分轨对齐合成**的双阶段架构：

1. **原片微剪去毛刺 (`trim_start_sec` / `trim_end_sec`)**：每个分镜默认开启 `trim_end_sec = 0.15` 秒片尾毛刺修剪。
2. **五轨独立合成与《剪映专业版 / CapCut 草稿》直出 (`studio_export_jianying_draft`)**：
   - **`V1_Clean_Video`**：修剪入出点后的无字干净画面轨；
   - **`A1_Dialogue_Stem` (`IndexTTS-2` / `CosyVoice 2.0` + `LatentSync`)**：48kHz 零样本克隆角色音色锚点，支持精确时长控制（Duration Control）与情绪气口演绎；
   - **`A2_Foley_SFX` (`MMAudio` CVPR 2025 SOTA + L3 空间声学滤波)**：根据修剪后的视频画面帧级同步生成拔剑、脚步、衣料摩擦等拟音，并自动叠加室内外低通滤波 (`lowpass=f=420`)；
   - **`A3_BGM_Score` (`ACE-Step` / `YuE` + FFmpeg `sidechaincompress`)**：按整集戏剧弧光（`P1_Hook` $\rightarrow$ `P3_Climax`）生成跨镜头连续配乐，并在有人声对白时自动闪避压低 `-12dB`；
   - **`T1_Subtitles` (`WhisperX` / `.srt`)**：独立时间轴字幕轨，随时可在剪映中自由调整样式与切点。
