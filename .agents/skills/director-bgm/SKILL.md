---
name: director-bgm
description: 用 Google Flow Music 生成独立背景音乐、纯器乐配乐或 BGM，支持用 prompt 定制曲风、节奏、乐器、情绪和时长意图。需要程序化调用时也可使用 Gemini API 的 Lyria。仅在用户请求新生成音轨时触发。
---

# 独立背景音乐

保留用户的 prompt，补足纯器乐、无歌词、无人声的要求。把曲风、情绪、主要乐器、速度和时长写进 prompt。用于对白下方时，可以要求低动态、少主旋律和干净收尾。将成品保存为独立音轨。

## Google Flow Music

用户指定 Flow Music 时，使用 [Google Flow Music](https://flowmusic.google/) 和设备上已获授权的登录会话。优先按当前设备的 ego-browser 技能操作，先运行 `ego-browser skill`。若环境没有 ego-browser，可使用客户端支持的浏览器。

1. 打开录音室，查看当前界面。若显示登录，使用获授权的 Google 账号完成登录。遇到需用户完成的验证时保留原页面，交给用户。
2. 在描述歌曲的输入框提交 prompt。选择纯器乐选项（如界面提供）。如果联合制作人先提出方案，按用户的意图确认生成一条音轨。避免重复提交。
3. 等待当前请求生成的新音轨。通过该音轨的下载按钮保存，保留实际下载格式，核实文件可解码。若遇到账户、区域或配额错误，记录页面实际提示。
4. 交付实际下载的文件，说明使用了 Google Flow Music。网站的配额以当前账号界面为准。

## Gemini API

批处理或用户选择 Gemini API 时，可以用同样在 Flow Music 提供的 Lyria 3.5 模型。它使用 Gemini API 项目的授权和额度。预先配置 `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`。脚本位于本技能的 `scripts/director_audio.py`，也可运行仓库根目录下的同名脚本。

```sh
python3 "/path/to/director_audio.py" music --prompt "夜间潜入场景，约 30 秒。稀疏拨弦、低音单簧管、96 BPM，轻巧紧张，在对白下方留出空间" --output "/path/to/underscore.mp3"
```

需要约 30 秒的固定短片预览时加 `--clip`，调用 Lyria 3 Clip。Lyria 3.5 的时长由 prompt 引导。只有下载或命令生成的音频通过检查才报告成功，后端失败时保留原错误，切换后端须明确告知用户。
