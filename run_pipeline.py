#!/usr/bin/env python3
"""Unified pipeline runner for Three Kingdoms AI Video production.
Supports both:
  1. Google Flow (Veo 3.1) [Default / Primary cloud engine using Google AI Ultra credits]
  2. MiniMax H3 [Local / Offline engine using local GPU]
"""
import argparse
import sys
from pathlib import Path

# Fix Windows console encoding for UTF-8 characters and emojis
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pipeline.flow_engine import FlowEngine
from pipeline.storyboard import StoryboardCompiler
from pipeline.director_linter import DirectorLinter
from pipeline.config import BASE_DIR, EPISODES_DIR, RAW_CLIPS_DIR, FINAL_EPISODES_DIR

try:
    from pipeline.h3_engine import H3Engine
    HAS_H3 = True
except Exception:
    HAS_H3 = False


EPISODE_CONFIGS = {
    1: {
        "dir_name": "ep01_crossing",
        "title": "第1集：一梦千八百载·初临祁山",
        "scenes": [
            {
                "id": "ep01_00a_convention_stage",
                "era": "modern",
                "room_id": "anime_convention_hall",
                "arc_phase": "phase_1_daily_empathy",
                "acoustic_space": "convention_hall_bustling",
                "framing": "establishing",
                "camera_motion": "35mm anamorphic lens, slow tracking orbit past flashing DSLR camera toward GuYuan speaking on the convention stage",
                "action": "Inside a bustling daytime university Three Kingdoms anime and cosplay convention hall. Under warm golden stage spotlights and crimson Three Kingdoms banners, 21-year-old student @GuYuan stands poised in his full Zhuge Liang cosplay (tall teal silk GuanJin headdress, wide-sleeved white crane-patterned robe HeChang with indigo brocade trim, sleek black-rimmed farsighted eyeglasses, matte-black hard-shell spare eyeglasses case clipped to his sash), gently fanning his white crane feather fan while looking at the camera and speaking aloud in Mandarin Chinese with clear, natural, synchronized lip and jaw movements. In the left foreground, an enthusiastic photographer crouches firing rapid DSLR camera flashes while college students hold up smartphones cheering; in the background on the right, fellow Zhao Yun and Sun Shangxiang cosplayers watch in admiration.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/ep01_00a_convention_stage_anchor.jpg",
                "dialogue_mode": "lipsync",
                "speaker": "GuYuan",
                "line": "先帝创业未半而中道崩殂……各位摄影老师，今天这身孔明行装，够还原吧！",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep01_00b_convention_selfie",
                "era": "modern",
                "room_id": "anime_convention_hall",
                "arc_phase": "phase_1_daily_empathy",
                "acoustic_space": "convention_hall_bustling",
                "framing": "medium-close",
                "camera_motion": "50mm anamorphic lens, subtle push-in on GuYuan speaking warmly with synchronized lip movements during the selfie interaction",
                "action": "Medium-close interactive shot in the exact same bustling Three Kingdoms anime convention hall. A lively female college cosplayer dressed as Xiao Qiao in red-and-white Hanfu happily holds up a smartphone to snap a two-shot selfie with @GuYuan, while a male cosplayer in Zhao Yun silver armor on the left grins and gives a thumbs-up, and an excited fan in the foreground snaps a DSLR close-up. @GuYuan smiles warmly behind his black-rimmed eyeglasses, gently raising his white crane feather fan in a modest traditional salute while speaking aloud in Mandarin Chinese with clear, natural, synchronized lip movements.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/ep01_00b_convention_selfie_anchor.jpg",
                "dialogue_mode": "lipsync",
                "speaker": "GuYuan",
                "line": "哈哈，多谢子龙兄弟和小乔学妹捧场！来，看镜头，咱们合张影！",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep01_01_rain_exterior",
                "era": "modern",
                "room_id": "dorm_room_night",
                "arc_phase": "phase_1_daily_empathy",
                "acoustic_space": "exterior_storm",
                "framing": "establishing",
                "camera_motion": "35mm lens, slow dolly in through torrential rain toward glowing dorm window",
                "action": "Midnight torrential rain outside a dark-framed apartment window with dark-slate curtains pulled to both sides. Raindrops stream down the glass in the foreground. Inside the warm tungsten-lit room (wooden desk along the left wall, 27-inch PC monitor on the left glowing with a photo gallery of his daytime anime convention Zhuge Liang cosplay photos, warm brass desk lamp beside the monitor, open black hard-shell eyeglasses case, white feather fan, folded teal GuanJin headscarf, and DSLR camera on the desk), 21-year-old student @GuYuan in his dark hoodie and black-rimmed eyeglasses sits facing the left monitor, clicking through his convention photos.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/ep01_01_exterior_window_anchor.jpg",
                "speaker": "GuYuan",
                "line": "今天漫展这身孔明行装，拍出来倒还有几分意思……",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep01_02_cosplay_sigh",
                "era": "modern",
                "room_id": "dorm_room_night",
                "arc_phase": "phase_1_daily_empathy",
                "acoustic_space": "interior_closed",
                "framing": "medium-close",
                "camera_motion": "50mm anamorphic lens, subtle slow push-in from cosplay photo album on monitor to GuYuan's face",
                "action": "Cut just inside the foreground window of the exact same warm dorm room (wooden bookshelf above the left desk and dim college dorm bunk beds in the background shadow). On the left 27-inch monitor screen, a photo gallery clearly displays vibrant daytime anime convention photos of @GuYuan dressed in his Zhuge Liang white crane robe, teal GuanJin headscarf, black-rimmed glasses, and white feather fan amidst convention booths and cosplayers, with a thumbnail filmstrip below and a DSLR camera connected on the desk. @GuYuan (wearing his dark hoodie, tactical vest, and sleek black-rimmed farsighted eyeglasses) gazes fondly at his cosplay photos on screen and gently strokes the real white feather fan on the desk beside his folded teal headscarf and open black eyeglasses case holding his spare glasses.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/ep01_02_interior_cosplay_screen_anchor.jpg",
                "speaker": "GuYuan",
                "line": "出师未捷身先死，长使英雄泪满襟……要是当年能为丞相守住街亭，该多好。",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep01_03_pack_and_sleep",
                "era": "modern",
                "room_id": "dorm_room_night",
                "arc_phase": "phase_1_daily_empathy",
                "acoustic_space": "interior_closed",
                "framing": "medium",
                "camera_motion": "35mm lens, gentle tilt down to backpack and desk lamp switch",
                "action": "Late at night inside the quiet dorm room. @GuYuan yawns lightly, sweeps the white crane feather fan, the folded teal GuanJin headscarf, and the black hard-shell eyeglasses case from the desk into his trekking backpack, zips it shut, and reaches out to click off the warm brass desk lamp, plunging the room into cool midnight blue shadow.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/ep01_02_interior_cosplay_screen_anchor.jpg",
                "speaker": "GuYuan",
                "line": "算了，明天还得去社团还道具，先睡了……",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep01_04_slippery_crash",
                "era": "modern",
                "arc_phase": "phase_2_sudden_accident",
                "acoustic_space": "exterior_street_wet",
                "framing": "wide",
                "camera_motion": "28mm handheld dynamic tracking into extreme slow-motion match cut",
                "action": "An overcast morning after heavy rain, wet city asphalt street covered in reflective puddles. @GuYuan walks across an intersection carrying his trekking backpack. Suddenly a car skids out of control on the slick wet road, tires spraying water as blinding headlights rush toward the camera. In extreme slow motion, the white crane feather fan bursts out of his backpack into the air amidst flying rainwater droplets.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/guyuan_modern_v2.jpg",
                "speaker": "GuYuan",
                "line": "小心——！！",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep01_05_mud_awaken",
                "era": "ancient",
                "arc_phase": "phase_3_shock_and_denial",
                "acoustic_space": "ancient_battlefield",
                "framing": "medium-close",
                "camera_motion": "40mm handheld rack focus from blurry mud to sharp armoured convoy",
                "action": "Match cut from flying rainwater droplets to cold muddy water splashing in a misty ancient Qinling mountain gorge. @GuYuan lies on the muddy trail coughing, squinting at his own mud-stained palm which appears blurry up close until he fumbles in the mud to put his black-rimmed convex eyeglasses back onto his nose. As near-field focus snaps crystal clear, he sees exhausted Shu Han soldiers in mud-caked leather armor and bloodstained straw sandals pushing heavy wooden grain carts past him under flickering torchlight.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/guyuan_ancient_v2.jpg",
                "speaker": "GuYuan",
                "line": "嘶……头好痛……这刀口上的血、这粮车……不是剧组拍戏？我真掉进古代战场了？！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep01_06_flag_and_zhuge",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_battlefield",
                "framing": "close-up",
                "camera_motion": "85mm telephoto pan from snapping HAN banner to candlelit command tent",
                "action": "High on the misty ridge, a giant black-and-red silk battle standard embroidered with 'HAN' snaps fiercely in the gale. Inside the main command tent, 47-year-old Chancellor @ZhugeLiang (Tang Guoqiang 1994 CCTV likeness, teal GuanJin headdress, white crane robe) holds a bamboo scroll at arm's length under candlelight, squinting and rubbing his fatigued eyes over a sand table of Jieting. Outside in the rain, @GuYuan grips his own mud-stained feather fan, eyes wide with awe and fierce resolve.",
                "characters": ["GuYuan", "ZhugeLiang"],
                "ref_image": "characters/images/zhugeliang_v2.jpg",
                "speaker": "GuYuan",
                "line": "‘汉’字大旗、建兴六年、街亭……真的是丞相！既然撞进这千八百年前的死局，这次街亭绝不能丢！",
                "style_variant": "intimate",
                "duration": 8,
                "model": "veo-quality"
            }
        ]
    },
    2: {
        "dir_name": "ep02_orientation",
        "title": "第2集：栈道辨时·急赴祁山",
        "scenes": [
            {
                "id": "ep02_01_muddy_crisis",
                "era": "ancient",
                "arc_phase": "phase_3_shock_and_denial",
                "acoustic_space": "ancient_battlefield",
                "framing": "establishing",
                "camera_motion": "28mm wide handheld tracking along perilous cliffside mud trail",
                "action": "On a perilous Qinling cliffside trail slick with mud, a massive ancient wooden grain cart has cracked its wooden axle, tilting dangerously over the sheer precipice. Exhausted Shu Han soldiers in wet leather armor strain desperately on hemp ropes as mud slides into the abyss.",
                "speaker": "Soldier",
                "line": "拉不住了！车轴断了，粮车要坠崖了！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep02_02_officer_despair",
                "era": "ancient",
                "arc_phase": "phase_3_shock_and_denial",
                "acoustic_space": "ancient_battlefield",
                "framing": "medium",
                "camera_motion": "50mm lens, low-angle push-in on desperate officer drawing sword",
                "action": "Shu Han logistics officer @OfficerWang brandishes his iron sword in fury, veins bulging on his forehead as he chops at a wooden post and yells at the stalled convoy amidst cold mountain rain.",
                "characters": ["OfficerWang"],
                "ref_image": "characters/images/guyuan_ancient.jpg",
                "speaker": "OfficerWang",
                "line": "山道塌陷，粮车坠崖！误了祁山大营军期，丞相军法如山，你我皆要斩首！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep02_03_guyuan_leverage",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_battlefield",
                "framing": "medium",
                "camera_motion": "35mm anamorphic tracking shot following GuYuan directing pulley rigging",
                "action": "@GuYuan in his white crane-patterned scholar robe and black-rimmed eyeglasses steps out of the misty woods holding his white feather fan. With calm authority, he directs soldiers to wedge sturdy pine logs under the broken axle as levers and loop hemp ropes around a cliffside pine trunk as a compound pulley system.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/guyuan_ancient_v2.jpg",
                "speaker": "GuYuan",
                "line": "慌什么！三人一组砍巨木作支点，藤索绕树作动滑轮，听我口令同时发力！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep02_04_cart_rescued",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_battlefield",
                "framing": "wide",
                "camera_motion": "40mm crane up from rescued grain cart to Wei scouts recoiling on cliff",
                "action": "With a synchronized heave, the heavy grain cart rolls safely back onto solid stone roadway. As @GuYuan turns his head toward the high ridge, a beam of mountain sunlight hits his convex eyeglass lenses, casting a blinding twin flash of cold white light across the gorge. On the opposite cliff, hidden Cao Wei scouts recoil in terror at the glowing crystal lenses on his face, while @OfficerWang kneels with clasped fists in stunned awe.",
                "characters": ["GuYuan", "OfficerWang"],
                "ref_image": "characters/images/guyuan_ancient_v2.jpg",
                "speaker": "OfficerWang",
                "line": "对岸魏军暗哨竟被先生目中寒光惊退！先生身披鹤氅，莫非是天降神人？！",
                "style_variant": "epic",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep02_05_bamboo_slip_year",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_battlefield",
                "framing": "close-up",
                "camera_motion": "85mm macro tilt across ink-inscribed military bamboo slip through convex lens",
                "action": "Extreme macro close-up of an official Shu Han military bamboo slip held in @GuYuan's mud-stained hands. Viewed through the edge of his convex eyeglass lens, the fine clerical ink characters are sharply magnified: 'Spring of the 6th Year of Jianxing - Transporting Hanzhong grain to Qishan Main Camp'.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/guyuan_ancient_v2.jpg",
                "speaker": "GuYuan",
                "line": "建兴六年春……督运汉中粮料，发祁山中军？！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep02_06_countdown_alarm",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_battlefield",
                "framing": "medium-close",
                "camera_motion": "50mm snap zoom on GuYuan's pale resolute face then sweeping pan up to Qishan fortress",
                "action": "@GuYuan's pupils contract sharply behind his glasses, knuckles whitening as he grips the bamboo slip tightly. The camera sweeps rapidly upward over jagged Qinling peaks to reveal the sprawling Qishan Shu Han military encampment with hundreds of red-and-black war banners flapping in the wind.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/guyuan_ancient_v2.jpg",
                "speaker": "GuYuan",
                "line": "建兴六年春！张郃五万铁骑已出关中，马谡马上就要去守街亭了！快备快马，带我见丞相！",
                "style_variant": "epic",
                "duration": 8,
                "model": "veo-quality"
            }
        ]
    },
    3: {
        "dir_name": "ep03_jieting",
        "title": "第3集：祁山惊雷·截胡马谡军令状",
        "scenes": [
            {
                "id": "ep03_01_establishing",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_battlefield",
                "framing": "establishing",
                "camera_motion": "24mm anamorphic aerial drone sweep over misty Qishan fortress at dawn",
                "action": "Sweeping aerial establishing shot of the sprawling Shu Han military fortress in the misty Qinling mountains at dawn. Towering wooden watchtowers and 'HAN' and 'ZHUGE' silk war banners snap fiercely in the freezing mountain gale outside the central command tent.",
                "speaker": "Narrator",
                "line": "建兴六年春，祁山大营。一场决定大汉国运的军议，正在帅帐中开启。",
                "style_variant": "epic",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep03_02_zhuge_fatigue",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_tent_interior",
                "framing": "medium",
                "camera_motion": "50mm lens, slow push-in on Zhuge Liang holding bamboo slip at arm's length and rubbing weary eyes",
                "action": "Inside the closed heavy canvas command tent, 47-year-old Chancellor @ZhugeLiang (Tang Guoqiang 1994 CCTV likeness, teal GuanJin headdress, white crane robe) sits behind a wooden campaign desk stacked with bamboo scrolls. Under flickering oil candlelight, he holds a fine-drawn military bamboo slip far away at arm's length, squinting at the tiny ink characters and briefly rubbing his fatigued brow before raising his white feather fan with solemn dignity.",
                "characters": ["ZhugeLiang"],
                "ref_image": "characters/images/zhugeliang_v2.jpg",
                "speaker": "ZhugeLiang",
                "line": "张郃引五万关中铁骑出斜谷，街亭乃汉中咽喉，谁敢引兵据守？",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep03_03_masu_vow",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_tent_interior",
                "framing": "medium",
                "camera_motion": "35mm low-angle dolly in on Ma Su stepping forward to claim command token",
                "action": "General @MaSu in gleaming silver-scale armor and white battle cloak strides proudly to the center of the tent, chin raised with haughty confidence, clasping his hands and reaching out to take the red-lacquered military command token.",
                "characters": ["MaSu"],
                "ref_image": "characters/images/zhuge_liang.jpg",
                "speaker": "MaSu",
                "line": "某自幼熟读兵书，街亭小小山僻之地，愿立军令状，乞存一军以当张郃！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep03_04_guyuan_stops_token",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_tent_interior",
                "framing": "medium-close",
                "camera_motion": "40mm handheld whip-pan to GuYuan's hand slamming down on the command token",
                "action": "@GuYuan in his mud-splashed white crane robe bursts through the tent flap and slams his hand firmly onto the wooden command token on the desk before it can be lifted. Torchlight glints sharply off his convex eyeglass lenses, casting twin bright reflections as armored generals gasp and step back in awe.",
                "characters": ["GuYuan"],
                "ref_image": "characters/images/guyuan_ancient_v2.jpg",
                "speaker": "GuYuan",
                "line": "丞相万万不可！这支令箭一旦发下，街亭必失，陇右三郡尽毁一旦！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep03_05_sandtable_reveal",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_tent_interior",
                "framing": "close-up",
                "camera_motion": "50mm anamorphic rack focus from Jieting sand table ridge to Zhuge Liang's astonished eyes",
                "action": "@GuYuan sweeps his white feather fan decisively across the clay sand table, pointing directly at the isolated arid mountaintop of Jieting and the narrow river waterway at its base. Behind the desk, @ZhugeLiang leans forward sharply, sword-like eyebrows raised in stunned recognition.",
                "characters": ["GuYuan", "ZhugeLiang"],
                "ref_image": "characters/images/zhugeliang_v2.jpg",
                "speaker": "GuYuan",
                "line": "马幼常必舍水登山！张郃只需围山断水，不出一日蜀军自乱，唯有当道筑垒方可破敌！",
                "style_variant": "tense",
                "duration": 8,
                "model": "veo-quality"
            },
            {
                "id": "ep03_06_glasses_gift",
                "era": "ancient",
                "arc_phase": "phase_4_evidence_awakening",
                "acoustic_space": "ancient_tent_interior",
                "framing": "medium-close",
                "camera_motion": "85mm warm portrait lens, slow dolly in on convex lenses magnifying bamboo characters and relaxed posture",
                "action": "Late at night in the quiet lantern-lit tent, @ZhugeLiang holds a dense military bamboo scroll at arm's length, squinting in the dim light. @GuYuan silently opens his matte-black hard-shell case and respectfully offers the spare metal-rimmed farsighted eyeglasses with both hands. @ZhugeLiang places the glasses onto his nose bridge; an over-the-shoulder macro insert shows the blurry tiny ink characters on the bamboo slip snapping into magnified, crystal-clear focus through the convex lenses. @ZhugeLiang's furrowed brow relaxes completely as he reads effortlessly at normal distance, nodding to @GuYuan in silent gratitude.",
                "characters": ["GuYuan", "ZhugeLiang"],
                "ref_image": "characters/images/zhugeliang_v2.jpg",
                "speaker": "ZhugeLiang",
                "line": "烛下细字，竟似拨云见日，一目了然……有子翼相助，亮何愁大事不成！",
                "style_variant": "intimate",
                "duration": 8,
                "model": "veo-quality"
            }
        ]
    }
}


def cmd_status(flow_engine: FlowEngine):
    print("=" * 65)
    print("  三国逆天改命·诸葛亮北伐 - 全自动 AI 视频制作流水线")
    print("=" * 65)
    
    # 1. Google Flow Status
    print("🌐 [主引擎: Google Flow / Veo 3.1 云端影视级引擎]:")
    auth = flow_engine.check_auth()
    if auth["authenticated"]:
        print("   ✅ 认证状态: 已登录并验证有效")
        print(f"      详情: {auth['details']}")
    else:
        print("   ❌ 认证状态: 未登录或会话未初始化")
        print(f"      提示: 请执行 python run_pipeline.py --login 进行一次性授权")

    credits = flow_engine.get_credits()
    if credits["success"]:
        print(f"   📊 账户点数/额度: {credits['output']}")
    else:
        print(f"   📊 账户点数/额度: (需完成登录后查询) {credits.get('error')}")

    # 2. Local Engine Status (if present)
    if HAS_H3:
        print("\n🖥️  [备用/辅助引擎: MiniMax H3 本地推理引擎]:")
        try:
            h3_engine = H3Engine()
            sys_status = h3_engine.check_system()
            print(f"   设备型号: {sys_status['device_name']}")
            print(f"   显存容量: {sys_status['vram_gb']} GB")
            print(f"   模型就绪: {'✅ 已就绪' if sys_status['model_ready'] else '⏳ 权重未就绪'}")
        except Exception as e:
            print(f"   状态检测略过: {e}")

    # 3. Project Directories
    print("\n📁 [工程目录状态]:")
    print(f"   工程根目录: {BASE_DIR}")
    print(f"   分镜工程目录: {EPISODES_DIR}")
    print(f"   生成的视频片段: {RAW_CLIPS_DIR}")
    print(f"   最终成片目录: {FINAL_EPISODES_DIR}")
    print("=" * 65)


def cmd_login(flow_engine: FlowEngine, browser: str = "auto"):
    print(f"\n🚀 正在打开浏览器以完成 Google Flow 账号授权 (模式: {browser})...")
    print("💡 提示:")
    print("   1. 系统已为您自动配置好 Chromium/浏览器环境；")
    print("   2. 请在弹出的浏览器窗口中登录拥有 Google AI Ultra 订阅的 Google 账号；")
    print("   3. 登录成功进入 Google Flow 主页面后，系统会自动保存凭证并关闭浏览器。\n")
    code = flow_engine.trigger_login(browser=browser)
    if code == 0:
        print("\n🎉 登录验证成功！会话凭证已安全持久化到本地。")
        print("   您可以随时运行 python run_pipeline.py --status 查看账户点数。")
    else:
        print(f"\n⚠️ 登录流程退出，返回码: {code}")


def cmd_lint_episode(ep_num: int) -> bool:
    if ep_num not in EPISODE_CONFIGS:
        print(f"❌ 未定义的集数: {ep_num}。当前支持: 1, 2, 3")
        return False
    cfg = EPISODE_CONFIGS[ep_num]
    manifest_path = EPISODES_DIR / cfg["dir_name"] / "movie.toml"
    if not manifest_path.exists():
        cmd_build_episode(ep_num)
    linter = DirectorLinter()
    report = linter.lint_manifest(manifest_path)
    print(report.format_report())
    return report.passed


def cmd_build_episode(ep_num: int):
    compiler = StoryboardCompiler()
    if ep_num not in EPISODE_CONFIGS:
        print(f"❌ 未定义的集数: {ep_num}。当前支持: 1, 2, 3")
        return

    cfg = EPISODE_CONFIGS[ep_num]
    target_file = EPISODES_DIR / cfg["dir_name"] / "movie.toml"
    out_dir = RAW_CLIPS_DIR / cfg["dir_name"]
    
    compiler.write_movie_file(
        output_file=target_file,
        title=cfg["title"],
        scenes=cfg["scenes"],
        project_id=f"sanguo_{cfg['dir_name']}",
        output_dir=out_dir,
        aspect="16:9"
    )
    print(f"✅ 成功编译第 {ep_num} 集分镜工程为 L1-L5 工业化规范文件:")
    print(f"   🎬 标题: {cfg['title']}")
    print(f"   📄 文件路径: {target_file}")
    print(f"   🎥 包含镜头数: {len(cfg['scenes'])} 幕 (使用 Veo 3.1 Quality 引擎)")
    linter = DirectorLinter()
    report = linter.lint_manifest(target_file)
    print(report.format_report())


def cmd_render_episode(flow_engine: FlowEngine, ep_num: int, dry_run: bool = False, engine_type: str = "flow"):
    if ep_num not in EPISODE_CONFIGS:
        print(f"❌ 未定义的集数: {ep_num}。当前支持: 1, 2, 3")
        return

    cfg = EPISODE_CONFIGS[ep_num]
    manifest_path = EPISODES_DIR / cfg["dir_name"] / "movie.toml"
    if not manifest_path.exists():
        print(f"❌ 找不到分镜工程文件: {manifest_path}，正在自动为您编译生成...")
        cmd_build_episode(ep_num)

    linter = DirectorLinter()
    report = linter.lint_manifest(manifest_path)
    print(report.format_report())
    if not report.passed and not dry_run:
        print("🛑 [L1-L5 导演门禁阻断] 分镜未通过工业化审查，已自动拦截渲染以防止浪费积分！请先修复上述 ERROR。")
        return

    out_dir = RAW_CLIPS_DIR / cfg["dir_name"]
    
    if engine_type == "flow":
        print(f"\n🎬 启动 Google Flow Veo 3.1 视频生成流水线 ({cfg['title']}, dry_run={dry_run})...")
        res = flow_engine.run_movie_project(
            manifest_path=manifest_path,
            out_dir=out_dir,
            dry_run=dry_run,
            stitch=True
        )
        if res["success"]:
            print("\n🎉 执行成功！")
            print(res["stdout"])
        else:
            print("\n❌ 执行遇到异常:")
            print(res["stdout"])
            print(res["stderr"])
    elif engine_type == "h3":
        if not HAS_H3:
            print("❌ MiniMax H3 模块未正确安装或导入失败。")
            return
        h3 = H3Engine()
        print(f"\n🎬 启动 MiniMax H3 本地视频生成流水线 ({cfg['title']}, dry_run={dry_run})...")
        res = h3.run_movie_project(
            manifest_path=manifest_path,
            out_dir=out_dir,
            dry_run=dry_run,
            stitch=True
        )
        if res["success"]:
            print("\n🎉 执行成功！")
        else:
            print(f"\n❌ 执行遇到异常: {res.get('error', '')}")


def main():
    parser = argparse.ArgumentParser(description="三国逆天改命 - L1~L5 工业化自动化视频制作流水线 (Google Flow & MiniMax H3)")
    parser.add_argument("--status", action="store_true", help="检查流水线引擎、认证与账户点数状态")
    parser.add_argument("--login", action="store_true", help="启动交互式浏览器完成 Google Flow 账号授权")
    parser.add_argument("--browser", default="internal", choices=["auto", "chrome", "internal"], help="Google 登录浏览器策略 (默认: internal)")
    parser.add_argument("--build-ep", type=int, help="编译指定集数的分镜工程并执行 L1-L5 导演质检 (如 --build-ep 1)")
    parser.add_argument("--lint-ep", type=int, help="对指定集数的 movie.toml 执行 L1-L5 编剧导演 SOP 质检 (如 --lint-ep 1)")
    parser.add_argument("--preview-ep", type=int, help="对指定集数执行 Dry-Run 预演校验 (零点数消耗)")
    parser.add_argument("--render-ep", type=int, help="批量生成指定集数的全部镜头并自动拼接成片")
    parser.add_argument("--engine", default="flow", choices=["flow", "h3"], help="视频生成引擎 (默认: flow - Google Flow Veo 3.1)")
    parser.add_argument("--clip", type=str, help="快速生成单条测试视频，传入提示词")

    args = parser.parse_args()
    flow_engine = FlowEngine()

    if args.status:
        cmd_status(flow_engine)
    elif args.login:
        cmd_login(flow_engine, browser=args.browser)
    elif args.build_ep:
        cmd_build_episode(args.build_ep)
    elif args.lint_ep:
        cmd_lint_episode(args.lint_ep)
    elif args.preview_ep:
        cmd_render_episode(flow_engine, args.preview_ep, dry_run=True, engine_type=args.engine)
    elif args.render_ep:
        cmd_render_episode(flow_engine, args.render_ep, dry_run=False, engine_type=args.engine)
    elif args.clip:
        print(f"🎬 正在使用 Google Flow 生成单条测试视频: {args.clip}")
        res = flow_engine.generate_single_clip(prompt=args.clip)
        print(res)
    else:
        cmd_status(flow_engine)


if __name__ == "__main__":
    main()
