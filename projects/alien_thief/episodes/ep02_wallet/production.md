# 《这钱眼熟》制作记录

状态：制作中，尚未通过作品验收。故事和对白见 `story.md`，实际音频条件与镜头提示见 `performance.json`。

`audio/` 是本片新生成的原创合成角色对白，沿用 V3 的固定卡托/西木参考声线，未变速。离场文件是明确的无对白条件，不能作为“有声台词”通过质检。背景音乐使用已生成的 Flow Music《Alien Alley Lottery》，不包含参考 B 站视频的音轨。

在已安装并验证的 MiniMax H3/DiffSynth GPU 环境中，从仓库根目录运行：

```sh
python scripts/h3_performance.py projects/alien_thief/episodes/ep02_wallet/performance.json --model-root /path/to/MiniMax-H3 --output /path/to/new-take
```

每次重做必须使用新目录；支持 `--shot intro` 选择独立镜头。`keyframe_from` 指向本次选择中先生成的镜头；单独续拍时应把已人工检查过的末帧作为显式 `keyframe` 输入。生成后需要检查脸、手、道具、说话者和反应，不把未检查的末帧继续传播。

结尾先行试验使用同一构图的基准图，分为收回钱包/控制人物与离场两个动作镜头。实际剪辑需检查与前镜的空间和动作连续性，不能凭提示文本认定衔接成立。最终片的选段和验收记录须另行保存。
