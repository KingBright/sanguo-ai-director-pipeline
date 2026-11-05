---
name: director-speech
description: 独立生成语音、中文配音、旁白或角色台词 WAV，支持指定音色、情绪、语速和停顿。用户要把指定文字转成可下载的声音时使用。已有剧集的分镜、视频渲染和混音走各自的制片流程。
---

# 独立配音

使用用户给出的原文。音色描述人物的声音特征，语气描述这段话的具体演法。需要指定多音字、数字、专名的念法时，先把用户确认的读音整理到朗读稿里。

找到本技能的 `scripts/director_audio.py`。从源码仓库直接使用技能时，脚本位于仓库根目录的 `scripts/director_audio.py`。用唯一的绝对路径保存 WAV。多行原文优先写入 UTF-8 文件，通过 `--text-file` 传入。

## Gemini TTS

使用已配置了 `GEMINI_API_KEY` 或 `GOOGLE_API_KEY` 的 Python 环境。用 `--voice` 选择 Gemini 3.8 Flash TTS 的音色，如 `Kore`、`Puck`、`Charon`，也可使用项目已有的自定义音色 ID。用 `--style` 指定口音、情绪、语速或停顿。完整音色表见 [Gemini TTS](https://ai.google.dev/gemini-api/docs/speech-generation)。

```sh
python3 "/path/to/director_audio.py" speech --text "天快亮了，我们走吧。" --voice Kore --style "普通话，轻声说，开头克制，结尾温和" --output "/path/to/dialogue.wav"
```

## Qwen3-TTS VoiceDesign

有现成的 Qwen3-TTS VoiceDesign 环境时，可用 `--provider qwen`。`--voice` 填自然语言音色描述，`--style` 填语气。传入已安装模型的 `--model-dir`，并使用装有 `qwen-tts`、`torch` 和 `soundfile` 的 Python。省略模型路径时，使用用户目录下的 `minimax/Qwen3-TTS-12Hz-1.7B-VoiceDesign`。

```sh
python3 "/path/to/director_audio.py" speech --provider qwen --language Chinese --text "天快亮了，我们走吧。" --voice "年轻成年女声，音色清亮" --style "稍慢、轻声，带一点释然" --output "/path/to/dialogue.wav"
```

当前设备没有模型时，可在用户授权的 Octendra 设备上用该设备已配置的 Qwen 环境生成，然后把 WAV 取回。提交一次，观察同一个操作直到结束。缺少可用后端时，说明需要哪个环境或授权。把实际输出文件和使用的后端交给用户。
