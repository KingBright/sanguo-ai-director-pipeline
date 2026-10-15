---
name: google-flow-director
description: 工业化 AI 视频制作工作流（L1-L5 五层导演决策架构 + S1-S6 六工位 SOP + Google Flow Veo 3.1 / 本机 MiniMax H3 双引擎协同与积分精算管理技能）。用于编剧心理弧光设计、静默伏笔保护与物理光学细节体现（Show, Don't Tell）、同场次三维空间拓扑与声学低通滤波一致性、台词视觉证据对齐、去文学化分镜编译审查、模型选型及五维积分产能汇报。
---

# 工业化 AI 视频导演与双引擎制片管理 Skill (`google-flow-director` v2.4)

本技能将《工业化 AI 视频制作工作流：编剧与导演角色的标准化方法论与可复用 SOP》（详见 [`docs/industrial_ai_video_sop.md`](file:///c:/Users/Liang/Downloads/sanguo/docs/industrial_ai_video_sop.md)）与 `open-ai-canvas` S1–S6 六工位体系转化为强制工程约束与可执行代码管线，统筹调度 **云端 Google Flow (`Veo 3.1`)** 与 **本机 AMD Strix Halo (`MiniMax H3`)**。

---

## 0. 核心症结防御与 L1–L5 五层可产品化导演决策架构

直接用单次提示词让 AI 包办编剧与导演会触发三大结构性失效：**① 跨层决策坍缩与上下文失忆（上帝视角剧透台词、同房间跨镜空间拓扑跳变）**、**② 文学性语言与视听语言的维度错位（不可拍心理描写、台词提漫展屏幕却放地图、室内外声场违和）**、**③ 概率生成模型的均值回归（死板居中构图、五官漂移）**。

所有剧集生产必须严格执行以下 **L1–L5 五层导演决策架构**，并通过 [`pipeline/director_linter.py`](file:///c:/Users/Liang/Downloads/sanguo/pipeline/director_linter.py) (`python run_pipeline.py --lint-ep X`) 自动化门禁审查（0 Error 方可进入渲染）：

### L1：叙事骨架、人物心理弧光与物理细节体现层 (Narrative, Arc & Show-Don't-Tell)
1. **契诃夫之枪静默律（铺垫期伏笔绝不进台词明牌）**：
   - 凡属未来剧情转折的伏笔道具（如顾渊的**第二副备用远视眼镜 / 眼镜盒**），在铺垫期（`phase_1` / `phase_2`）只能作为**静默视觉道具**写入画面描述 (`action`) 中自然陈列（如第1集漫展归来敞开在桌角、睡前拢入双肩包），**严禁在铺垫期台词 (`line`) 中直接点破**！
2. **物理光学细节体现律（全剧严禁台词直白说出“远视眼/老花眼/凸透镜/度数”）**：
   - 顾渊佩戴的是**远视凸透镜 (`convex eyeglass lenses`)**，兼具两大戏剧功能：**① 解决 47 岁诸葛亮夙夜批阅竹简的老花眼**；**② 镜片折射强光令曹魏暗哨/武将误认为天降神器**。
   - `DirectorLinter` 通过 `always_banned_explicit_medical_terms_in_dialogue` 全剧封禁“远视眼/老花眼/凸透镜/度数”等直白说教台词，强制通过三组纯视觉镜头体现：
     - **老花症状铺垫**：诸葛亮烛下看竹简时必须**伸直手臂拉远 (`holds bamboo slip at arm's length`) + 微眯眼揉眉心**；
     - **凸透镜光学放大微距**：透过镜片边缘微距特写，展示原本模糊的竹简汉隶细字**瞬间光学放大变清晰 (`magnified into crystal-clear focus through the convex lenses`)**，诸葛亮眉头舒展、拉回正常距离阅读；
     - **寒光反射震慑敌哨**：阳光或火把照射在凸透镜上折射出**双道刺目冷白寒光 (`blinding twin flash of cold white light`)**，惊退高崖魏军暗哨。
3. **人物心理四阶段单调演进律（禁止一秒接受设定或弧光倒退）**：
   - `phase_1_daily_empathy`（日常共情铺垫） $\rightarrow$ `phase_2_sudden_accident`（物理因果突发意外） $\rightarrow$ `phase_3_shock_and_denial`（生理苏醒与怀疑否认） $\rightarrow$ `phase_4_evidence_awakening`（铁证冲击、智谋破局与伏笔回收）。

### L2：视觉资产与全局事实锁层 (Fact Sheet & Asset Lock)
- 以 [`fact_sheet.toml`](file:///c:/Users/Liang/Downloads/sanguo/fact_sheet.toml) 为唯一事实源：
  1. **全局摄影胶片锁 (`GLOBAL_STYLE_LOCK`)**：`Shot on ARRI Alexa 65 with Panavision anamorphic lens, Rembrandt classical oil-painting chiaroscuro lighting, Kodak Vision3 500T film grain`。
  2. **跨时空同一角色骨相与空间母图锚定 (`i2v` / `Ref2VA`)**：每个镜头必须显式绑定真实存在的 `ref_image`。
  3. **双向时代服化道物理隔离 (`era = "modern" | "ancient"`)**：现代场景自动绑定 `style.variants.modern`，现代与古代画面词双向隔离。

### L3：视听空间调度、同房间三维拓扑锁与声学矩阵层 (3D Spatial Topology & Acoustic Space)
1. **外景建置先行律（Exterior Establishing $\rightarrow$ Interior Cut）**：
   - 切入封闭内景（`interior_closed` 或 `ancient_tent_interior`）前，必须先有室外环境建置镜头。
2. **同场次跨镜三维空间拓扑锁 (`[spatial_rooms]` / `room_id`)**：
   - 同一房间连续镜头（如 `room_id = "dorm_room_night"` 的窗外透视 Shot 1 $\rightarrow$ 室内近景 Shot 2 $\rightarrow$ 收拾背包 Shot 3）必须严格锁定**左/中/右三维空间方位**：
     - **左 (`camera_left`)**：27寸显示器（亮着漫展 Cos 诸葛亮活动返图相册）+ 黄铜暖光台灯；
     - **中前景 (`center_foreground`)**：木质书桌，依次摆放敞开的黑色硬壳眼镜盒（内含备用眼镜）、白羽扇、青色纶巾、连着数据线的单反相机、双肩包；
     - **右 (`camera_right`)**：顾渊面朝左侧显示器而坐。
   - **透窗推镜 Z 轴一致性守则**：Shot 1 绑定窗外透视锚定图 `ep01_01_exterior_window_anchor.jpg`，Shot 2/3 绑定室内屏幕锚定图 `ep01_02_interior_cosplay_screen_anchor.jpg`；严禁跨镜发生 180° 越轴或左右陈设颠倒。
3. **声画空间物理滤波（Acoustic Space Low-Pass Filtering）**：
   - `exterior_storm` / `ancient_battlefield`：全频段清晰环境雨风声（`volume=0.75~0.90`）；
   - `interior_closed`（关窗室内）：自动施加 **FFmpeg `lowpass=f=420,volume=0.18` 低通滤波**，化为沉闷窗外底噪；
   - `ancient_tent_interior`（中军帅帐内）：自动施加 **FFmpeg `lowpass=f=380,volume=0.22` 低通滤波**，凸显帐内烛火噼啪声与竹简声。

### L4：去文学化“可拍性”与台词视觉证据对齐编译器层 (Shootability & Visual Evidence Compiler)
1. **物理焦段与运镜锁**：强制每个镜头声明包含明确物理焦段（如 `28mm`, `35mm`, `50mm`, `85mm`）的 `camera_motion`。
2. **台词指涉物与屏幕/道具视觉证据强对齐律 (`dialogue_visual_evidence_rules`)**：
   - 当台词提及特定媒介或光学现象时，画面 `action` 必须呈现直接视觉证据（如台词提**“漫展”** $\rightarrow$ 显示器屏幕必须展示**漫展现场 Cos 诸葛亮的活动抓拍相册与底部缩略图条 + 桌面单反相机**，严禁只放无关地图；台词提**“拨云见日”** $\rightarrow$ 画面必须展示**凸透镜放大竹简细字**）。
3. **中英文抽象废话拦截**：自动阻断 `内心涌起`、`史诗感`、`realizes the`、`feels a sense of` 等不可拍心理词。

---

## 1. 视频模型档位与积分消耗标准（8秒/镜头基准）

| 模型名称 (UI 显示) | CLI 参数 (`--model`) | 单次积分消耗 (8秒) | 每分钟成片消耗 (7.5个镜头) | 适用场景定位 |
| :--- | :--- | :--- | :--- | :--- |
| **Veo 3.1 - Quality** | `veo-quality` | **100 点** | **750 点 / 分钟** | **旗舰最高画质（当前最佳模型）**。用于重头戏、人物特写、首帧锁定 (`i2v`) 母带交付。 |
| **Omni 1.1 Flash** | `omni-flash` | **12 点** | **90 点 / 分钟** | **新一代全能模型**。支持 **10秒** 超长单镜与多图参考（最多7张），适合长镜头过渡。 |
| **Veo 3.1 - Fast** | `veo-fast` | **10 点** | **75 点 / 分钟** | **主力高性价比标准档**。适合常规叙事镜头与大规模量产。 |
| **Veo 3.1 - Lite** | `veo-lite` | **5 点** | **37.5 点 / 分钟** | **轻量快速走位预览档**。用于低成本测试运镜构图。 |

---

## 2. 每次生成后的强制汇报规范（五维报告）

1. **🎬 视频内容与 L1–L5 导演质检核验**：提供本地视频文件链接、图片预览、所用模型、房间拓扑锚点、声学空间滤波档位及核对后的台词文本。
2. **💸 本次消耗积分 (Credits Used)**：本次调用消耗的精确点数（本地 `MiniMax H3` 消耗 `0 点`；云端 `Veo 3.1 Quality` 消耗 `100 点`）。
3. **💰 当前剩余积分 (Remaining Credits)**：读取最新账户余额。
4. **⏳ 距离下次刷新时间 (Time Until Refresh)**：根据刷新时间戳（Unix Epoch `1792265525`）计算剩余倒计时。
5. **📊 预计剩余产能（还能做几分钟视频）**：换算 `Quality`、`Fast`、`Lite` 及本机 `MiniMax H3` 下的剩余可制作时长。

---

## 3. 标准 CLI 操作指令速查

```powershell
# 1. 编译第 1/2/3 集 L1-L5 标准分镜并自动运行 DirectorLinter 门禁审查
python run_pipeline.py --build-ep 1
python run_pipeline.py --build-ep 2
python run_pipeline.py --build-ep 3

# 2. 单独对指定集数执行 L1-L5 编剧导演 SOP 质检
python run_pipeline.py --lint-ep 1

# 3. 检查云端 Google Flow 与本机 Strix Halo (MiniMax H3) 双引擎状态及积分
python run_pipeline.py --status

# 4. 本机 MiniMax H3 零积分渲染测试（已内置 ROCm Qwen3-VL eager 注意力防黑屏修复）
C:\Users\Liang\minimax\.venv\Scripts\python.exe run_h3.py --test-shot
```
