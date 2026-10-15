#!/usr/bin/env python3
"""Unified pipeline runner for MiniMax H3 Local AI Video production.
Operates on the Sanguo project alongside the Google Flow pipeline without collision.
"""
import argparse
import sys
from pathlib import Path

# Fix Windows console encoding for UTF-8 characters and emojis
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pipeline.h3_engine import H3Engine
from pipeline.storyboard import StoryboardCompiler
from pipeline.config import BASE_DIR, EPISODES_DIR, RAW_CLIPS_DIR, FINAL_EPISODES_DIR


def cmd_status(engine: H3Engine):
    print("=" * 65)
    print("  三国逆天改命·诸葛亮北伐 - MiniMax H3 本地全自动音视频流水线")
    print("=" * 65)
    sys_status = engine.check_system()
    print("🖥️  [硬件与计算卡检测]:")
    print(f"   设备型号: {sys_status['device_name']}")
    print(f"   显存容量: {sys_status['vram_gb']} GB (已在 BIOS 分配 96G 专属显存)")
    print(f"   硬件加速: {'✅ 已就绪 (AMD Strix Halo / gfx1151)' if sys_status['gpu_detected'] else '❌ 未就绪'}")
    if sys_status['torch_version'] != 'N/A':
        print(f"   PyTorch : {sys_status['torch_version']}")

    print("\n🎭 [核心角色视觉一致性锚点 (Ref2VA 原生多图参考)]: ")
    char_dir = engine.characters_dir
    if char_dir.exists():
        anchors = list(char_dir.glob("*.jpg")) + list(char_dir.glob("*.png"))
        for a in anchors:
            print(f"   ✓ 人设图就绪: {a.name} ({a.stat().st_size // 1024} KB)")

    print("\n📁 [工程目录状态]:")
    print(f"   工程根目录: {BASE_DIR}")
    print(f"   分镜工程目录: {EPISODES_DIR}")
    print(f"   生成的视频片段: {RAW_CLIPS_DIR}")
    print(f"   最终成片目录: {FINAL_EPISODES_DIR}")
    print("=" * 65)


EPISODE_CONFIGS = {
    1: {
        "dir_name": "ep01_crossing",
        "title": "第1集：梦回千载·初临汉界",
        "scenes": [
            {
                "id": "ep01_01_modern_study",
                "action": "A dimly lit modern study at midnight, rain pouring outside the window. Maps of the Three Kingdoms, Zhuge Liang's portrait, and reference books spread on the desk. Young scholar @GuYuan stares at the mountain pass on the map with deep emotional reverence.",
                "framing": "medium",
                "characters": ["GuYuan"],
                "duration": 5,
                "model": "minimax-h3"
            },
            {
                "id": "ep01_02_mountain_storm",
                "action": "A dangerous ancient plank road cliff in the Qinling mountains covered in thick eerie white mist. A sudden blinding flash of supernatural lightning illuminates the rugged canyon and envelops the solitary figure.",
                "framing": "wide",
                "style_variant": "epic",
                "duration": 5,
                "model": "minimax-h3"
            },
            {
                "id": "ep01_03_awaken_in_wild",
                "action": "@GuYuan wakes up on damp mossy ground beneath towering ancient pine trees, covered in dirt. He checks his smartphone, which displays 'No Service' before going completely dead. The mountain wind howls.",
                "framing": "medium-close",
                "characters": ["GuYuan"],
                "duration": 5,
                "model": "minimax-h3"
            },
            {
                "id": "ep01_04_valley_convoy",
                "action": "A breathtaking high-angle view looking down into a deep muddy mountain valley. A long supply convoy of ancient Chinese soldiers in leather armor are struggling to push wooden wheelbarrows and grain carts along a rocky trail.",
                "framing": "establishing",
                "style_variant": "epic",
                "duration": 5,
                "model": "minimax-h3"
            },
            {
                "id": "ep01_05_flag_reveal",
                "action": "A dramatic close-up slow-motion shot of a magnificent weathered black silk military battle standard fluttering violently in the mountain wind, embroidered with a golden Han dynasty seal script character 'HAN'.",
                "framing": "close-up",
                "style_variant": "epic",
                "duration": 5,
                "model": "minimax-h3"
            },
            {
                "id": "ep01_06_emotional_realize",
                "action": "A poignant emotional close-up of @GuYuan's face, trembling with tears of awe and disbelief as he whispers to himself, realizing he has truly arrived in the Three Kingdoms era to find Chancellor Zhuge Liang.",
                "framing": "close-up",
                "characters": ["GuYuan"],
                "style_variant": "intimate",
                "duration": 5,
                "model": "minimax-h3"
            }
        ]
    }
}


def cmd_preview_single_shot(engine: H3Engine, ep_num: int = 1, shot_idx: int = 1):
    """Preview or run single 5-second test shot."""
    manifest_path = EPISODES_DIR / "ep01_crossing" / "movie.toml"
    out_dir = RAW_CLIPS_DIR / "ep01_crossing"
    print(f"\n🎬 [MiniMax H3 快速试水] 仅运行 第 {ep_num} 集 第 {shot_idx} 幕镜头 (5秒测试)...")
    res = engine.run_movie_project(
        manifest_path=manifest_path,
        out_dir=out_dir,
        dry_run=True,
        stitch=False,
        max_scenes=1
    )
    return res


def cmd_render_single_shot(engine: H3Engine, ep_num: int = 1, shot_idx: int = 1):
    """Render single 5-second test shot."""
    manifest_path = EPISODES_DIR / "ep01_crossing" / "movie.toml"
    out_dir = RAW_CLIPS_DIR / "ep01_crossing"
    print(f"\n🚀 [MiniMax H3 快速试水开拍] 正在渲染 第 {ep_num} 集 第 {shot_idx} 幕镜头 (5秒测试)...")
    res = engine.run_movie_project(
        manifest_path=manifest_path,
        out_dir=out_dir,
        dry_run=False,
        stitch=False,
        max_scenes=1,
        duration_override=5
    )
    return res


def main():
    parser = argparse.ArgumentParser(description="三国逆天改命 - MiniMax H3 本地自动化视频流水线")
    parser.add_argument("--status", action="store_true", help="检查本地硬件算力、显存与流水线状态")
    parser.add_argument("--test-shot", action="store_true", help="快速试水：测试第1集第1镜头（5秒）")
    parser.add_argument("--preview-ep", type=int, help="对指定集数执行 Dry-Run 预演校验")
    parser.add_argument("--render-ep", type=int, help="全量生成指定集数全部镜头并合成")

    args = parser.parse_args()
    engine = H3Engine()

    if args.status:
        cmd_status(engine)
    elif args.test_shot:
        cmd_render_single_shot(engine, ep_num=1, shot_idx=1)
    elif args.preview_ep:
        manifest_path = EPISODES_DIR / f"ep{args.preview_ep:02d}_crossing" / "movie.toml" if args.preview_ep == 1 else EPISODES_DIR / f"ep{args.preview_ep:02d}_orientation" / "movie.toml"
        if not manifest_path.exists():
            # Fallback path search
            matching = list(EPISODES_DIR.glob(f"ep{args.preview_ep:02d}*/movie.toml"))
            if matching:
                manifest_path = matching[0]
        engine.run_movie_project(manifest_path, dry_run=True)
    elif args.render_ep:
        matching = list(EPISODES_DIR.glob(f"ep{args.render_ep:02d}*/movie.toml"))
        if matching:
            engine.run_movie_project(matching[0], dry_run=False)
        else:
            print(f"❌ 找不到第 {args.render_ep} 集的 movie.toml")
    else:
        cmd_status(engine)


if __name__ == "__main__":
    main()
