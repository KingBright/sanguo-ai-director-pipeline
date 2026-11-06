# 《三国：逆天改命·诸葛亮北伐》— L1~L5 工业化 AI 视频制作工作流与双引擎制片管线

> **架构定位**：本项目将《工业化 AI 视频制作工作流：编剧与导演角色的标准化方法论与可复用 SOP》（[docs/industrial_ai_video_sop.md](docs/industrial_ai_video_sop.md)）与 `S1–S6` 六工位体系落地为可执行的自动化代码管线。  
> 底层统筹调度 **云端 Google Flow (`Veo 3.1 Quality / Fast / Omni 1.1 Flash`)** 与 **本机 AMD Strix Halo 96GB ROCm (`MiniMax H3` 原生音视频同生引擎)**，实现“人类掌舵叙事弧光与审美决策，AI 执行工业化分镜编译、静态门禁质检与物理声学母带混音”。

---

## 🏗️ 一、 L1–L5 五层可产品化导演决策架构

针对直接让 AI 生成视频常见的三大结构性失效（**跨层决策坍缩与剧透台词**、**文学修辞与视听语言错位**、**概率模型均值回归与五官漂移**），本工程通过 [`pipeline/director_linter.py`](pipeline/director_linter.py) 强制执行五层门禁：

| 层级 | 架构名称 | 核心工程约束与门禁规则 (`DirectorLinter`) | 唯一事实源 / 对应模块 |
| :--- | :--- | :--- | :--- |
| **L1** | **叙事骨架与人物心理弧光层** | 1. **契诃夫之枪静默律（Show, Don't Tell）**：铺垫期（`phase_1`/`phase_2`）严禁在台词中点破未来转折道具（如顾渊的**第二副备用眼镜**），仅作为静默视觉道具自然陈列于画面中，直至回收期（`phase_4`）兑现。<br>2. **心理四阶段单调演进律**：强制校验 `phase_1_daily_empathy` $\rightarrow$ `phase_2_sudden_accident` $\rightarrow$ `phase_3_shock_and_denial` $\rightarrow$ `phase_4_evidence_awakening` 单调非递减。 | [`fact_sheet.toml`](fact_sheet.toml)<br>`[director_rules]` |
| **L2** | **视觉资产与全局事实锁层** | 1. **跨时空骨相与定妆母图锁**：每个含角色的镜头必须显式绑定真实存在的 `ref_image`（`guyuan_modern_v2.jpg` / `guyuan_ancient_v2.jpg` / `zhugeliang_v2.jpg`）。<br>2. **双向时代服化道隔离**：区分 `era = "modern" \| "ancient"`，防止古今服饰与环境提示词串戏。<br>3. **全局胶片锁**：`ARRI Alexa 65 + Panavision anamorphic + Rembrandt chiaroscuro + Kodak Vision3 500T`。 | [`characters/profiles.toml`](characters/profiles.toml)<br>[`pipeline/storyboard.py`](pipeline/storyboard.py) |
| **L3** | **视听空间调度与声学矩阵层** | 1. **外景建置先行律（Establishing $\rightarrow$ Interior Cut）**：切入封闭内景前必须先有外景建置镜头。<br>2. **物理声学低通滤波（LPF）**：关窗室内 (`interior_closed`) 自动施加 `lowpass=f=420,volume=0.18`；中军帅帐内 (`ancient_tent_interior`) 自动施加 `lowpass=f=380,volume=0.22`，将窗外/帐外风雨压为沉闷底噪。 | [`pipeline/director_linter.py`](pipeline/director_linter.py)<br>`master_scene_clip()` |
| **L4** | **去文学化“可拍性”编译器层** | 1. **物理焦段与运镜锁**：强制校验 `camera_motion` 包含明确物理焦段（`24mm`/`35mm`/`50mm`/`85mm`）。<br>2. **中英文抽象废话拦截**：自动阻断 `内心涌起`、`史诗感`、`realizes the`、`feels a sense of` 等不可拍心理词。 | [`pipeline/director_linter.py`](pipeline/director_linter.py)<br>`lint_manifest()` |
| **L5** | **双引擎分级渲染与精修成片层** | 本机 `MiniMax H3`（0 积分预演与声画同生）+ 云端 `Veo 3.1 Quality`（100 点/8秒母带精修）+ `ffmpeg silencedetect` 帧级 `.ass` 字幕烧录 + 五维积分产能汇报。 | [`pipeline/flow_engine.py`](pipeline/flow_engine.py)<br>[`pipeline/h3_engine.py`](pipeline/h3_engine.py) |

---

## 🎬 二、 前三集完整叙事弧线与伏笔闭环（建兴六年·公元 228 年）

* **第 1 集：《一梦千八百载·初临祁山》** ([`episodes/ep01_crossing/script.md`](episodes/ep01_crossing/script.md))
  * **L1–L3 标准场次链**：`Shot 1` 室外暴雨拍打树叶与二楼暖光窗（外景建置，全频雨声）$\rightarrow$ `Shot 2` 关窗宿舍内景（420Hz 低通闷雨声），21岁大学生顾渊半披漫展诸葛亮鹤氅翻看返图，感慨一千八百年前的建兴六年祁山悲剧（桌角敞开装着**第二副备用眼镜**的硬壳眼镜盒，台词绝不剧透）$\rightarrow$ `Shot 3` 睡前将白羽扇、纶巾与备用眼镜盒拢入双肩包熄灯 $\rightarrow$ `Shot 4` 次日雨后路滑突发车祸，飞旋的白羽扇与水花做跨时空 **匹配剪辑（Match Cut）** $\rightarrow$ `Shot 5` 秦岭泥水呛咳摸回眼镜，从怀疑剧组拍戏到看见刀口真血与运粮蜀军 $\rightarrow$ `Shot 6` 仰望“漢”字帅旗与帐内 94 版唐国强神韵诸葛亮，立誓守住街亭。
* **第 2 集：《栈道辨时·急赴祁山》** ([`episodes/ep02_orientation/script.md`](episodes/ep02_orientation/script.md))
  * 秦岭险道运粮重车断轴滑崖 $\rightarrow$ 押粮官绝望拔剑 $\rightarrow$ 顾渊以原木杠杆与复合滑轮组救下粮车 $\rightarrow$ 取出胸前眼镜盒里的**备用镜片**与主镜片叠合竹筒远眺路况（伏笔初次半展开）$\rightarrow$ 验看通关竹简确认“建兴六年春·督运汉中粮料发祁山中军” $\rightarrow$ 疾驰中军大营。
* **第 3 集：《祁山惊雷·截胡马谡军令状》** ([`episodes/ep03_jieting/script.md`](episodes/ep03_jieting/script.md))
  * 破晓祁山大营外景建置 $\rightarrow$ 帅帐内（380Hz 低通滤波）诸葛亮烛下揉眼疲惫点将 $\rightarrow$ 马谡傲然请命欲接令箭 $\rightarrow$ 顾渊闯帐按住令箭 $\rightarrow$ 沙盘直指街亭孤山无水死穴 $\rightarrow$ 深夜帐中双手献上**第二副备用金属框眼镜**助丞相明目看清舆图（契诃夫之枪高光回收）。

---

## 📁 三、 仓库目录结构

```text
sanguo/
├── .agents/skills/google-flow-director/
│   └── SKILL.md                  # 工业化 AI 视频导演与双引擎制片管理 Skill (v2.3)
├── docs/
│   └── industrial_ai_video_sop.md# 《工业化 AI 视频制作工作流：L1-L5 导演决策架构与 SOP》
├── fact_sheet.toml               # 产线唯一事实源 (L1-L5 规则词表、声学滤波矩阵、角色骨相锁)
├── characters/
│   ├── profiles.toml             # 角色多时代外观与语音锚点配置
│   └── images/                   # V2 影视级 16:9 定妆参考母图 (用于 Veo i2v 与 H3 Ref2VA)
├── episodes/
│   ├── ep01_crossing/            # 第1集剧本 (script.md)、编译清单 (movie.toml) 与 ASS 字幕
│   ├── ep02_orientation/         # 第2集剧本 (script.md) 与编译清单 (movie.toml)
│   └── ep03_jieting/             # 第3集剧本 (script.md) 与编译清单 (movie.toml)
├── pipeline/
│   ├── config.py                 # 全局摄影胶片锁与时代隔离配置
│   ├── director_linter.py        # L1-L5 静态规则检查器与 FFmpeg 物理声学混音母带引擎
│   ├── storyboard.py             # L1-L5 分镜编译器 (生成标准 movie.toml)
│   ├── flow_engine.py            # 云端 Google Flow (Veo 3.1) 调度与五维积分精算引擎
│   └── h3_engine.py              # 本机 AMD Strix Halo (MiniMax H3) 4阶段显存管理与 ROCm 推理引擎
├── run_pipeline.py               # 双引擎主控 CLI 入口
└── run_h3.py                     # 本机 MiniMax H3 独立推理与测试入口
```

---

## 🚀 四、 快速使用指南

```powershell
# 1. 编译第 1~3 集分镜工程并自动运行 L1-L5 DirectorLinter 门禁审查
python run_pipeline.py --build-ep 1
python run_pipeline.py --build-ep 2
python run_pipeline.py --build-ep 3

# 2. 单独执行 L1-L5 编剧导演 SOP 静态质检
python run_pipeline.py --lint-ep 1

# 3. 查看云端 Google Flow 积分产能与本机 Strix Halo (MiniMax H3) 状态
python run_pipeline.py --status

# 4. 零积分预演校验 (Dry-Run)
python run_pipeline.py --preview-ep 1 --engine flow
python run_pipeline.py --preview-ep 1 --engine h3

# 5. 正式渲染成片 (需先通过 DirectorLinter 0 Error 门禁)
python run_pipeline.py --render-ep 1 --engine flow
```

## 独立配音和配乐

`director-speech` 接收原文，按音色和语气生成 WAV。可选 Gemini TTS 预设音色，或用已有的 Qwen3-TTS VoiceDesign 环境按自然语言设计音色。两种方式都支持单独生成旁白和角色台词。

`director-bgm` 可用 Google Flow Music 录音室根据 prompt 生成并下载纯器乐配乐。批处理可以通过 Gemini API 调用同样在 Flow Music 提供的 Lyria 3.5，输出 MP3。API 路径使用对应项目的密钥与额度。

在所需设备的仓库根目录运行安装命令。每个 `--client` 选择一款已安装的客户端。Windows 可以用 `py -3` 替换 `python3`。

```sh
python3 scripts/install_audio_skills.py --client codex --client antigravity --client dsh
python3 scripts/install_audio_skills.py --client codex --client antigravity --client dsh --check
```

在客户端新会话中调用 `director-speech` 或 `director-bgm`。在终端可直接运行下面的命令。Gemini API 读取已配置的 `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`。

```sh
python3 scripts/director_audio.py speech --text "我们走吧。" --voice Kore --style "用普通话轻声说，带一点释然" --output output/dialogue.wav
python3 scripts/director_audio.py music --prompt "纪录片的安静开场，稀疏钢琴和弦乐，约 30 秒" --output output/opening.mp3
```

[语音技能](.agents/skills/director-speech/SKILL.md) · [配乐技能](.agents/skills/director-bgm/SKILL.md) · [Google Flow Music](https://flowmusic.google/) · [Lyria API](https://ai.google.dev/gemini-api/docs/music-generation)

## 从故事到表演和镜头

`director-story` 将故事、人物关系与表演放在制片流程前面。“约 30 秒”表示故事体量，不是逐句字数配额。先明确人物目标、冲突与转折，记录稳定音色及每句的意图、重音、停顿和情绪，再根据实际试演安排镜头。长台词可以跨说话者与听者镜头，简短台词之后可以留反应。

当前制作示例：[《这钱眼熟》故事](projects/alien_thief/episodes/ep02_wallet/story.md)、[带真实对白的音频条件镜头计划](projects/alien_thief/episodes/ep02_wallet/performance.json)、[制作记录](projects/alien_thief/episodes/ep02_wallet/production.md)。[故事与表演方法](.agents/skills/director-story/references/story-performance-method.md)要求主要冲突在画面里有结果，逐镜检查说话者、听者、嘴形与道具，再进入剪辑。

出镜对白使用实际验证的音频条件动画或原生画音联合生成。下面的本地路线读取完整原速对白，并保留同一条声轨；需要已安装的 H3/DiffSynth GPU 环境和本地模型，不自动下载模型。

```sh
python3 scripts/install_audio_skills.py --client codex --skill director-story
python3 scripts/h3_performance.py projects/alien_thief/episodes/ep02_wallet/performance.json --model-root /path/to/MiniMax-H3 --output output/new-take
python3 scripts/native_av_master.py /path/to/reviewed-edit.json --raw-dir output/new-take --music output/real-score.mp3 --output output/new-master
```

历史 V3《两块五的尊严》已被用户拒绝：故事未完成、音画不同步、人物表演不足。其技术记录不能作为作品通过的示例。`clean_master.py` 保留用于旁白、画外音和后配音草案；它不生成口型，不能替代上述出镜对白路线。

语音脚本使用已安装的 Qwen3-TTS VoiceDesign/Base，后期需要 ffmpeg、numpy、soundfile。当前 Qwen Base 以合成参考声与标点控制表演，没有独立情绪指令接口；不能把 `delivery` 字段声称为已经执行的模型参数。精细表演仍需试演与选段。

后期保留语音自然速度，根据实际对白和反应时长剪完整原帧；视频覆盖不足会报错要求补镜。制片时保存逐帧来源校验与独立声轨；需要字幕时输出独立 SRT，不烧入画面。禁止局部贴帧、按音量拉扯嘴部、为评分加入测试音。`video_quality_critic.py --offline-only` 只给诊断，始终要求声画复核，不能凭高分批准成片。
