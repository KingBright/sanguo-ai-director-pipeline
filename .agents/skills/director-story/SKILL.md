---
name: director-story
description: 将故事制作成剧情短片或动画，先设计人物目标、场景冲突和对白表演，再据实际试演安排镜头与配乐。用于新建或重做剧情样片、修复赶台词或后期撕裂问题；单独配音和配乐分别使用 director-speech、director-bgm。
---

# 从故事到短片

“约 30 秒”等时长是故事体量目标。先说明谁想要什么、遇到什么阻碍、如何应对、最后发生什么变化。选择必要的角色和场景，再设计铺垫与回收。不要倒推等长镜头、每句字数配额或统一短台词。

为角色分别记录稳定身份与当句表演：身份包括语言习惯、音色、共鸣和口音；表演包括意图、对象、潜台词、情绪变化、重音、停顿与动作。惜字、絮叨、抢话、迟疑都是角色策略。固定声线不等于固定情绪。

先确认主要冲突在画面中有结果：人物做出选择、行动产生后果，不能把一句挖苦或吃惊表情当成故事结局。

用户指出故事薄弱、场景衔接或表演不连贯时，先用[故事与导演预演](references/dramaturgy-and-shot-flow.md)完善整片因果、人物策略和剪接逻辑。静态分镜仅验证信息安排；对白试演、动作试拍及整片观看另行进行，不能用逐镜技术检查代替。

涉及交付、取物、装盒、进出场或修复道具错误时，先读[剧情因果与物体连续性](references/continuity-and-causality.md)。先核实堂食/外带、付款/赠送和人物位置，再记录关键物体转移前后状态；关键事实失败或未验证时停止扩展，不能靠技术检查放行。

先试演完整对白，再据自然时长安排说话者、听者、反应和环境镜头。长对白可以跨镜头，短对白之后可以留反应。素材不够就补覆盖镜头；禁止重采样加速台词、截掉字尾、局部冻结身体或按音量扭曲嘴部。对白优先于音乐，配乐的停顿和收尾服务于情节。

出镜对白先选择已验证的原生画音联合生成或音频条件动画；原生画音必须保留同一次生成的原声，并以相同入出点剪辑。独立静音视频加TTS仅适用于旁白、画外音或草案，不能按此路线交付需要口型同步的角色对白。

先制作一段能暴露问题的小样，实际检查完整台词、嘴形启闭、说话者归属、意图转变和听者反应。小样未成立不批量制作。模型或参数声称支持同步并不等于小样通过。

需要完整制作与验收标准时，读 [故事与表演制作方法](references/story-performance-method.md)。

使用 Google Flow Omni 1.2 Flash 制作原生画音或接续长片时，读 [Flow 新模型与接续操作](references/flow-omni12.md)，以网页实际模型和报价为准。

## 执行能力与边界

- `scripts/episode_audio.py` 在已有 Qwen3-TTS 环境和本地模型目录中建立原创合成音色，再用 Base 固定身份。需要 torch、qwen-tts、soundfile、numpy。不会自动下载模型。当前表演控制来自合成参考声与台词标点，Base 没有独立情绪指令接口；`delivery` 是试演验收标准，不能声称已作为模型参数执行。
- `scripts/h3_performance.py` 使用已安装的 MiniMax H3/DiffSynth 本地模型，把指定对白作为生成条件。输入 `shots[{id,audio,keyframe,prompt,before,after,seed}]`，按实际语音长度向上对齐后端帧数，保留完整声音及反应时间；不下载模型、不加速。已完成单镜音频条件试镜，不能据此批准任意新镜头。每次重做使用新输出目录，单镜记录输入哈希与状态。需要 torch、diffsynth、Pillow、soundfile、numpy 和已验证的 GPU 环境。 单镜可设置 `cfg_scale` 和 `negative_prompt`。当前后端在默认 `cfg_scale=1` 时不执行负面提示分支；如需启用该约束，必须显式提高引导值并重新试镜，不能仅凭填写了负面提示就声称已生效。
- 镜头使用项目已有的真实视频生成后端。先确认当前 CLI/API 支持的选项；按已完成的表演申请足够覆盖。不要把静态推拉包装成完整角色动画，也不要用伪口型迎合质检分数。
- `scripts/native_av_master.py` 剪辑原生画音素材，按同一帧区间裁切画面和原声，保存原始PCM并核对。输入 `shots[{id,file,first_frame,end_frame,text,review}]`，只输出候选片；不能用声轨保留证明模型嘴形正确。
- `scripts/clean_master.py` 是后配音剪辑器，不生成口型。需要 ffmpeg/ffprobe、numpy、soundfile。它按对白实际长度及前后反应时间分配完整原帧，允许一句话跨多个覆盖镜头。不足时明确失败。先将明确标记的素材统一为 BT.709 并记录转换，再无损剪辑并逐帧核对；不改变画面结构或播放速度。色彩标记缺失时要求先明确处理。输出独立声轨与可选 SRT，不烧入字幕。

原生画音剪辑：

```sh
python scripts/native_av_master.py native_story.json --raw-dir /path/to/native-clips --music /path/to/score.mp3 --output /path/to/new-candidate
```

旁白/画外音路线的 `episode_audio.py` 与 `clean_master.py` 输入为 JSON。`cast` 以角色 ID 为键，包含 `seed`、稳定音色描述 `voice`、原创合成参考台词 `reference_text`。`dialogue` 顺序列出 `id`、`speaker`、`text`、`delivery`、对白前后停顿 `before`/`after`、视频文件名列表 `coverage`。可指定 `reaction_video` 在台词之后切听者，`reaction_start_frame` 选择反应入点，`music_gain` 表示这一拍的配乐强弱。`target_duration_about` 只记录预期，不强制压时长。

```sh
python scripts/episode_audio.py story.json --model-root /path/to/models --output /path/to/speech
python scripts/clean_master.py story.json --raw-dir /path/to/clips --audio-dir /path/to/speech --music /path/to/real-score.mp3 --output /path/to/new-master
```

Qwen 模型目录包含 `Qwen3-TTS-12Hz-1.7B-VoiceDesign` 和 `Qwen3-TTS-12Hz-1.7B-Base`。每份不同脚本使用独立输出目录，保留原版及来源。

验收分开报告：技术检查（解码、帧来源、声音截断、混音）与故事/表演检查（因果、性格、情绪、笑点或情感落点）。自动转写只是辅助；运动量、音量相关性、对比度均不能批准成片。保留模型原片和最终片对照，明确后配音并不等于已验证逐音素口型同步。

用户拒绝的版本必须保留为 rejected；技术合格不能覆盖故事或表演不合格。只对实际观察到的能力作结论，未观察的项目记录为未验证。
