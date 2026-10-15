---
name: google-flow-director
description: 工业化 AI 视频制作工作流（L1-L5 五层导演决策架构 + S1-S6 六工位 SOP + Google Flow Veo 3.1 / 本机 MiniMax H3 双引擎协同与积分精算管理技能）。用于编剧心理弧光设计、静默伏笔保护（Show, Don't Tell）、外景建置与声画空间一致性（室内低通滤波）、去文学化分镜编译审查、模型选型及五维积分产能汇报。
---

# 工业化 AI 视频导演与双引擎制片管理 Skill (`google-flow-director` v2.3)

本技能将《工业化 AI 视频制作工作流：编剧与导演角色的标准化方法论与可复用 SOP》（详见 [`docs/industrial_ai_video_sop.md`](file:///c:/Users/Liang/Downloads/sanguo/docs/industrial_ai_video_sop.md)）与 `open-ai-canvas` S1–S6 六工位体系转化为强制工程约束与可执行代码管线，统筹调度 **云端 Google Flow (`Veo 3.1`)** 与 **本机 AMD Strix Halo (`MiniMax H3`)**。

---

## 0. 核心症结防御与 L1–L5 五层可产品化导演决策架构

直接用单次提示词让 AI 包办编剧与导演会触发三大结构性失效：**① 跨层决策坍缩与上下文失忆（上帝视角剧透台词、多镜头空间割裂）**、**② 文学性语言与视听语言的维度错位（不可拍心理描写、室内外声场违和）**、**③ 概率生成模型的均值回归（死板居中构图、五官漂移）**。

所有剧集生产必须严格执行以下 **L1–L5 五层导演决策架构**，并通过 [`pipeline/director_linter.py`](file:///c:/Users/Liang/Downloads/sanguo/pipeline/director_linter.py) (`python run_pipeline.py --lint-ep X`) 自动化门禁审查（0 Error 方可进入渲染）：

### L1：叙事骨架与人物心理弧光层 (Narrative & Psychological Arc)
1. **契诃夫之枪静默律（Show, Don't Tell — 铺垫期伏笔绝不进台词明牌，回收期自然兑现）**：
   - 凡属未来剧情转折的伏笔道具（如顾渊的**第二副备用眼镜 / 眼镜盒**），在铺垫期（`phase_1_daily_empathy` / `phase_2_sudden_accident`）只能作为**静默视觉道具**写入画面描述 (`action`) 中自然陈列（如第1集漫展归来敞开在桌角、睡前拢入双肩包），**严禁在铺垫期台词 (`line`) 中直接点破**！直至回收期（`phase_4_evidence_awakening`，如第2集叠合镜片望远、第3集献给视物模糊的诸葛亮）才允许在台词中点明。
2. **人物心理四阶段单调演进律（禁止一秒接受设定或弧光倒退）**：
   - `phase_1_daily_empathy`（日常共情铺垫）：漫展 Cos 诸葛亮归来翻看返图，由己及人感慨**近一千八百年前（公元228年，建兴六年）**的真丞相；
   - `phase_2_sudden_accident`（物理因果突发意外）：前夜大雨导致次日路面湿滑突发车祸，仅有本能惊呼；
   - `phase_3_shock_and_denial`（生理苏醒与怀疑否认）：在泥水中呛咳摸回眼镜，第一反应以为是剧组拍戏；
   - `phase_4_evidence_awakening`（铁证冲击、智谋破局与伏笔回收）：看到刀口真血、泥泞粮车、“汉”字大旗与唐国强版诸葛亮真容，完成救粮车、截军令状与献备用眼镜的破局闭环。

### L2：视觉资产与全局事实锁层 (Fact Sheet & Asset Lock)
- 以 [`fact_sheet.toml`](file:///c:/Users/Liang/Downloads/sanguo/fact_sheet.toml) 为唯一事实源：
  1. **全局摄影胶片锁 (`GLOBAL_STYLE_LOCK`)**：`Shot on ARRI Alexa 65 with Panavision anamorphic lens, Rembrandt classical oil-painting chiaroscuro lighting, Kodak Vision3 500T film grain`。
  2. **跨时空同一角色骨相锚定 (`i2v` / `Ref2VA`)**：每个包含角色的镜头必须显式绑定真实存在的 `ref_image`（现代绑 `guyuan_modern_v2.jpg`，古代绑 `guyuan_ancient_v2.jpg`，诸葛亮绑 `zhugeliang_v2.jpg`）。
  3. **双向时代服化道物理隔离 (`era = "modern" | "ancient"`)**：现代场景自动绑定 `style.variants.modern`，严禁全局 `negative` 误禁现代服饰，且现代与古代画面词双向隔离。

### L3：视听空间调度与声学矩阵层 (Spatial Blocking & Acoustic Space)
1. **外景建置先行律（Exterior Establishing $\rightarrow$ Interior Cut）**：
   - 凡切入封闭内景（`interior_closed` 或 `ancient_tent_interior`），前置镜头必须先有室外环境建置镜头（`establishing` 或 `exterior_storm` / `ancient_battlefield`）。
2. **声画空间物理滤波（Acoustic Space Low-Pass Filtering）**：
   - `exterior_storm` / `ancient_battlefield`：全频段清晰环境雨风声（`volume=0.75~0.90`）；
   - `interior_closed`（关窗室内）：自动施加 **FFmpeg `lowpass=f=420,volume=0.18` 低通滤波**，化为沉闷窗外底噪；
   - `ancient_tent_interior`（中军帅帐内）：自动施加 **FFmpeg `lowpass=f=380,volume=0.22` 低通滤波**，凸显帐内烛火噼啪声与竹简声。

### L4：去文学化“可拍性”编译器层 (De-Literary Shootability Compiler)
- 强制每个镜头声明包含明确物理焦段（如 `28mm`, `35mm`, `50mm`, `85mm`）的 `camera_motion`，并拦截中英文不可拍心理/抽象词汇（如 `内心涌起`、`史诗感`、`realizes the`、`feels a sense of`）。

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

1. **🎬 视频内容与 L1–L5 导演质检核验**：提供本地视频文件链接、图片预览、所用模型、声学空间滤波档位及核对后的台词文本。
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
