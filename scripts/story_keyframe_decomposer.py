#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AetherDirector Studio — 4-Level Story-to-Keyframe Decomposition Engine
======================================================================
Solves the "coarse outline / flat storytelling / missing intermediate keyframes" problem
by decomposing any narrative premise through a 4-Level Industrial Cinematography Pipeline:

  Level 1 [Dramatic Beat & Subtext Architecture (戏剧节拍与潜台词冲突层)]:
    - Breaks flat plot summaries into high-retention dramatic beats:
      (1) Sensory Hook & Hidden Crisis (0-3s 感官强钩子与隐秘危机)
      (2) Friction & Power Escalation (人际施压与物理阻碍升级)
      (3) Micro-Climax & Evidence Insert (微距铁证切入与情绪极性反转)
      (4) Decisive Payoff & Cliffhanger (破局决断与尾钩定格)
    - Explicitly separates Spoken Line (表层台词) vs. Subtext/Inner Objective (潜台词与真实动机)
      vs. Physical Blocking & Prop Action (物理调度与手部道具博弈).

  Level 2 [Multi-Camera Editing Sequence (电影级正反打/微距插入镜/反应特写拆解层)]:
    - Never dumps a whole scene into a single static talking-head shot.
    - Decomposes each dramatic beat into locked 180-degree South-Side camera setups:
      Establishing -> OTS A (Over-the-Shoulder) -> ECU Macro Prop Insert -> OTS B Reverse ->
      Silent Reaction Close-Up -> Low-Angle Heroic Payoff.

  Level 3 [Intra-Shot 17k Frame-by-Frame Keyframe Spec (单镜内部 17k 黄金相位逐帧关键帧拆解层)]:
    - For every shot (`90f = 3.75s`, `141f = 5.88s`, `192f = 8.00s`), decomposes motion into
      exact `17k` frame anchors (`Frame 0`, `Frame 34`, `Frame 51`, `Frame 85`, `Frame 102`, `Frame 136`):
      * Exact frame index (`17k`) & timestamp (`sec`)
      * Bound `POSE-DB-01` (1,439 Poses) skeleton ID & camera angle
      * `Nano Banana Pro (nano-pro)` / `Flux` Multi-Reference Img2Img synthesis prompt
        (combining Character Turnaround Card + Room Spatial Anchor + Pose Skeleton Image)
        so every intermediate keyframe is physically rendered BEFORE video generation!

  Level 4 [Micro-Timeline Acoustic & Motion Envelope (毫秒级声画包络与气闸舱同步层)]:
    - Aligns `[0.00s - 1.10s]` Silent Preparatory Airlock -> `[1.10s - 1.60s]` Foley Trigger ->
      `[1.60s - 4.50s]` `<d>` Dialogue Peak + `T8mars` Emotion Vector -> `[4.50s - End]`
      Closed-Mouth `V9_TailLock` `[107, 136]`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class KeyframeAnchorSpec:
    frame_idx: int                # Must be 0 or 17k (0, 17, 34, 51, 68, 85, 102, 136, 170)
    timestamp_sec: float          # frame_idx / 24.0
    anchor_role: str              # "StartLock_F0" | "MidAction_17k" | "ClimaxPeak_17k" | "V9_TailLock"
    strength: float               # 1.0 for F0, 0.85~0.90 for intermediate/tail
    pose_id: str                  # POSE-DB-01 ID (e.g. "full_single_P001_low", "upper80v2_P008_diag")
    camera_angle: str             # "front" | "side" | "diag" | "low" | "high"
    body_blocking: str            # Exact physical posture & hand chirality at this exact frame
    facial_micro_expression: str  # Eye direction, brow tension, lip state (closed/speaking) at this frame
    nano_pro_i2i_prompt: str      # Ready-to-run Google Flow `nano-pro` (10-ref) keyframe synthesis prompt


@dataclass
class MicroTimelineWindow:
    window_sec: str               # e.g. "00:00.000 - 00:01.100"
    phase_type: str               # "Silent_Airlock" | "Foley_Initiation" | "Vocal_Climax" | "Tail_Lock_Hold"
    visual_trajectory: str
    acoustic_cue: str


@dataclass
class DecomposedShotSpec:
    shot_id: str
    beat_number: int
    beat_title: str
    shot_type: str                # "Establishing" | "OTS_A" | "ECU_Insert" | "OTS_B_Reverse" | "Silent_Reaction" | "Hero_Climax"
    continuity_track: str         # "track_a_latent_relay" (22f MotionContext) | "track_b_hard_cut"
    golden_frames: int            # 90 (3.75s), 141 (5.88s), or 192 (8.00s)
    duration_sec: float
    lens_and_movement: str        # Single physical 3D camera directive
    axis_180_geography: str       # Left/Center/Right screen lock
    speaker: str
    spoken_line: str
    subtext_motivation: str       # Why the character says/does this (never spoken aloud!)
    emotion_mode: str             # "natural" | "t8mars_explosive" | "t8mars_fury" | "t8mars_weeping"
    character_card: Optional[str]
    keyframe_anchors: List[KeyframeAnchorSpec] = field(default_factory=list)
    micro_timeline: List[MicroTimelineWindow] = field(default_factory=list)


def build_sanguo_flagship_blueprint() -> Dict:
    """
    Deep dramatic & frame-by-frame keyframe rework for Project `sanguo`:
    《三国：逆天改命》EP01 核心重头戏：《祁山帅帐·烛影微茫与急报惊变》
    - 彻底摒弃原来“念一句诗、喊一句口号、直接递眼镜说拨云见日”的流水账写法！
    - 戏剧核心冲突（悬念与潜台词博弈）：
      建兴六年春夜，祁山中军帐。47岁的诸葛亮因长年批阅军务已患严重老花眼（远视），但为了稳住军心、压住质疑北伐的宿将与恃才傲物的马谡，他绝不能在众将面前暴露自己“看不清军报细字”的生理弱点——平日里的文书他全靠提前背诵或摸索竹简刻痕强撑威严！
      然而此刻，帐外暴雨倾盆，陇右前线斥候浑身浴血撞入帅帐，呈上一卷**刚刚截获、墨迹未干的曹魏张郃奇袭街亭绝密调兵竹简**！
      众将屏息等待丞相决断。诸葛亮展开竹简，烛光摇曳下，上面密密麻麻的蝇头小楷在他眼中化成一片模糊重影。他不动声色地将手臂一点点推远，指尖微不可察地发颤，额角沁出冷汗——一旦念错或迟疑，马谡必以此轻敌冒进，三军军心必乱！
      就在这千钧一发的死局时刻，站在帅案阴影侧后方的年轻参军顾渊看穿了丞相“手臂推远却瞳孔失焦”的秘密，借着上前添拨灯芯的动作，用身体挡住众将视线，将那副凸透镜无声嵌入烛台与竹简之间的视线光路上！
    """
    shots: List[DecomposedShotSpec] = [
        DecomposedShotSpec(
            shot_id="sg_ep01_s01_storm_courier_hook",
            beat_number=1,
            beat_title="强钩子：暴雨急报撞帐（0-3.75秒生死倒计时切入）",
            shot_type="Establishing",
            continuity_track="track_b_hard_cut",
            golden_frames=90,
            duration_sec=3.75,
            lens_and_movement="28mm anamorphic lens, low-angle tracking push-in following the mud-splattered scout bursting through the tent flap",
            axis_180_geography="Camera-Left: rain-lashed tent entrance & iron brazier | Center: mud-soaked scout dropping to one knee | Camera-Right: assembled Shu generals turning in alarm",
            speaker="Scout",
            spoken_line="报——！陇右八百里加急！张郃前锋已过渭水，截获魏军绝密调兵竹简！",
            subtext_motivation="打破平庸开场，第一秒就用带血的未读绝密军报把诸葛亮推入『必须当众立即研判蝇头细字』的绝境。",
            emotion_mode="t8mars_explosive",
            character_card=None,
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="full_single_P035_diag",
                    camera_angle="low",
                    body_blocking="Scout in rain-drenched leather armor bursts through heavy canvas tent flap from camera-left, right hand clutching a blood-stained bamboo scroll high.",
                    facial_micro_expression="Mouth closed in a sharp inhalation, rain streaming down brow, eyes wide with urgency.",
                    nano_pro_i2i_prompt="16:9 widescreen ARRI Alexa 65 frame. Low-angle 28mm shot inside a candlelit Three Kingdoms military command tent at night. A rain-soaked Shu Han scout bursts in from camera-left holding a blood-stained bamboo scroll, heavy rain visible outside the tent flap, generals on camera-right turning sharply. Match pose skeleton full_single_P035_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.88,
                    pose_id="full_single_P022_diag",
                    camera_angle="diag",
                    body_blocking="Scout drops heavily onto one knee in the muddy straw at center foreground, both hands thrusting the bamboo scroll forward toward the main command desk.",
                    facial_micro_expression="Veins taut on neck, roaring the urgent dispatch.",
                    nano_pro_i2i_prompt="16:9 widescreen ARRI Alexa 65 frame. The rain-soaked Shu Han scout kneels on one knee in the center of the candlelit command tent, both hands presenting a blood-stained bamboo scroll high above his head. Warm oil lamp light and cold rain droplets. Match pose skeleton full_single_P022_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=85,
                    timestamp_sec=3.54,
                    anchor_role="V9_TailLock",
                    strength=0.90,
                    pose_id="full_single_P022_front",
                    camera_angle="diag",
                    body_blocking="Scout holds the kneeling posture steady with head bowed, bamboo scroll held level in both hands, chest heaving silently.",
                    facial_micro_expression="Lips pressed shut, breathing heavily through nose, gaze locked downward.",
                    nano_pro_i2i_prompt="16:9 widescreen ARRI Alexa 65 frame. Kneeling scout holds the bamboo scroll steady in both hands with head bowed and mouth closed, oil lamps flickering in background. Match pose skeleton full_single_P022_front.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:00.850", "Silent_Airlock", "Heavy canvas tent flap whips open; scout lunges two steps inward.", "Foley: violent canvas flap snap + thunder rumble outside."),
                MicroTimelineWindow("00:00.850 - 00:02.950", "Vocal_Climax", "Scout crashes to one knee at frame 51, thrusting scroll up.", "Foley: knee armor slam at 00:00.900 + <d>[Mandarin] urgent report</d>."),
                MicroTimelineWindow("00:02.950 - 00:03.750", "Tail_Lock_Hold", "Scout freezes in bowed kneeling posture (`[68, 85]` V9 TailLock).", "Foley: dripping rainwater on floor, tense silence."),
            ],
        ),
        DecomposedShotSpec(
            shot_id="sg_ep01_s02_masu_pressure_ots",
            beat_number=2,
            beat_title="人际施压：马谡傲慢请战与众将逼视（把丞相架在火上烤）",
            shot_type="OTS_A",
            continuity_track="track_b_hard_cut",
            golden_frames=141,
            duration_sec=5.88,
            lens_and_movement="50mm anamorphic lens, over-the-shoulder from behind Zhuge Liang's left shoulder toward Ma Su and Wei Yan on camera-right, slow tense push-in",
            axis_180_geography="Foreground Left: Zhuge Liang's dark-teal GuanJin shoulder silhouette | Center: clay sand table of Jieting | Right Midground: Ma Su stepping forward arrogantly beside Wei Yan",
            speaker="MaSu",
            spoken_line="丞相！区区张郃何足道哉？请丞相即刻宣读竹简军情，某愿立军令状，连夜赶往街亭屯兵当道！",
            subtext_motivation="马谡急于抢功，当众催促诸葛亮『即刻宣读竹简』，无形中封死了诸葛亮退后私阅的退路，将戏剧张力拉满。",
            emotion_mode="natural",
            character_card="马谡|蜀汉参军 · 抚军从事",
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="full_single_P015_diag",
                    camera_angle="diag",
                    body_blocking="Ma Su in silver-scale armor and white battle cloak stands on camera-right behind the Jieting sand table, chin slightly raised.",
                    facial_micro_expression="Confident, haughty composure, lips closed before speaking.",
                    nano_pro_i2i_prompt="16:9 widescreen OTS shot inside Shu Han command tent. Foreground left shows blurred shoulder of Zhuge Liang in white crane robe. On camera-right across the clay sand table stands proud advisor-general Ma Su in silver armor. Match pose full_single_P015_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.86,
                    pose_id="upper80v2_P016_diag",
                    camera_angle="diag",
                    body_blocking="Ma Su takes half a step toward the sand table, right hand clasping his left fist in a sharp military salute while speaking.",
                    facial_micro_expression="Brows arched with pride, eyes locked onto the bamboo scroll on Zhuge Liang's desk.",
                    nano_pro_i2i_prompt="16:9 widescreen OTS shot. Ma Su on camera-right clasps his hands in a confident military salute over the clay sand table, speaking fervently under warm candlelight. Match pose upper80v2_P016_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=136,
                    timestamp_sec=5.67,
                    anchor_role="V9_TailLock",
                    strength=0.90,
                    pose_id="upper80v2_P016_front",
                    camera_angle="diag",
                    body_blocking="Ma Su holds his clasped-hand salute stationary, head held level, waiting expectantly for Zhuge Liang to read the scroll aloud.",
                    facial_micro_expression="Mouth closed, expectant proud gaze locked toward camera-left.",
                    nano_pro_i2i_prompt="16:9 widescreen OTS shot. Ma Su holds his salute motionless on camera-right with mouth closed and gaze fixed on camera-left. Match pose upper80v2_P016_front.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:01.100", "Silent_Airlock", "Ma Su shifts weight forward beside the sand table, armor plates clicking softly.", "Foley: subtle silver armor clink."),
                MicroTimelineWindow("00:01.100 - 00:04.600", "Vocal_Climax", "Ma Su salutes at frame 51 and urges Zhuge Liang to read the dispatch aloud immediately.", "<d>[Mandarin] Ma Su dialogue</d>."),
                MicroTimelineWindow("00:04.600 - 00:05.880", "Tail_Lock_Hold", "All generals' eyes lock onto Zhuge Liang (`[107, 136]` V9 TailLock).", "Foley: oil lamp wick crackle."),
            ],
        ),
        DecomposedShotSpec(
            shot_id="sg_ep01_s03_zhuge_hidden_presbyopia_crisis",
            beat_number=3,
            beat_title="隐秘危机：丞相展简失焦（Show, Don't Tell 物理光学细节）",
            shot_type="OTS_B_Reverse",
            continuity_track="track_b_hard_cut",
            golden_frames=141,
            duration_sec=5.88,
            lens_and_movement="85mm anamorphic portrait lens, medium close-up on Zhuge Liang seated at camera-left desk, shallow depth of field",
            axis_180_geography="Camera-Left/Center: Zhuge Liang seated behind wooden desk holding unrolled bamboo scroll | Camera-Right Background: Gu Yuan standing quietly in half-shadow behind the brass oil lamp",
            speaker="ZhugeLiang",
            spoken_line="且慢……张郃用兵老辣，此简所载行军里数，干系三军生死……",
            subtext_motivation="诸葛亮嘴上说『且慢、干系三军生死』是在拖延时间！画面上他将竹简一点点推远到一臂之外、眉头紧锁微眯双眼，用纯物理动作告诉观众：他看不清上面的蝇头小楷！",
            emotion_mode="natural",
            character_card="诸葛亮|蜀汉丞相 · 武乡侯",
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="full_single_P002_front",
                    camera_angle="front",
                    body_blocking="47-year-old Zhuge Liang sits upright in teal GuanJin and white crane robe, unrolling the bamboo scroll at normal reading distance with both hands.",
                    facial_micro_expression="Dignified calm mask, mouth closed, eyes dropping to the bamboo slips.",
                    nano_pro_i2i_prompt="16:9 widescreen 85mm close-up. 47-year-old Chancellor Zhuge Liang (Tang Guoqiang 1994 likeness) seated at wooden campaign desk under candlelight, holding an unrolled bamboo scroll with both hands. Young advisor Gu Yuan stands quietly in deep shadow on camera-right. Match pose full_single_P002_front.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.88,
                    pose_id="full_single_P012_diag",
                    camera_angle="diag",
                    body_blocking="Zhuge Liang slowly extends his arms to push the bamboo scroll further away to arm's length while keeping his shoulders composed so the generals do not notice.",
                    facial_micro_expression="Subtle squint of his eyes, fine bead of sweat on temple under candlelight, speaking slowly and gravely.",
                    nano_pro_i2i_prompt="16:9 widescreen 85mm medium close-up. Zhuge Liang holds the bamboo scroll extended out at arm's length under flickering oil lamp light, squinting subtly with furrowed brow while maintaining a dignified posture. In the background shadow, Gu Yuan notices his outstretched arms. Match pose full_single_P012_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=136,
                    timestamp_sec=5.67,
                    anchor_role="V9_TailLock",
                    strength=0.90,
                    pose_id="full_single_P012_front",
                    camera_angle="diag",
                    body_blocking="Zhuge Liang's right thumb presses tightly against the edge of the bamboo slip to steady a faint tremor, head held level.",
                    facial_micro_expression="Lips closed, solemn strained gaze fixed on the scroll.",
                    nano_pro_i2i_prompt="16:9 widescreen 85mm close-up. Zhuge Liang holds the bamboo scroll steady at arm's length with mouth closed and solemn strained eyes under warm candlelight. Match pose full_single_P012_front.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:01.100", "Silent_Airlock", "Zhuge Liang unrolls the bamboo scroll; his pupils contract as the tiny ink characters blur.", "Foley: dry bamboo slips unrolling."),
                MicroTimelineWindow("00:01.100 - 00:04.500", "Vocal_Climax", "He subtly pushes the scroll to arm's length at frame 51 while speaking slowly to buy time.", "<d>[Mandarin] Zhuge Liang stalling line</d>."),
                MicroTimelineWindow("00:04.500 - 00:05.880", "Tail_Lock_Hold", "In the background shadow, Gu Yuan's eyes lock onto Zhuge Liang's outstretched arms (`[107, 136]` V9 TailLock).", "Foley: tense heartbeat-like drum pulse."),
            ],
        ),
        DecomposedShotSpec(
            shot_id="sg_ep01_s04_pov_blur_to_lens_insert",
            beat_number=4,
            beat_title="微距铁证：失焦蝇头小楷 vs 借拨灯芯无声入画的凸透镜（全场高潮转折）",
            shot_type="ECU_Insert",
            continuity_track="track_b_hard_cut",
            golden_frames=90,
            duration_sec=3.75,
            lens_and_movement="100mm macro lens, extreme close-up over Zhuge Liang's optical axis onto the bamboo slips, rack focus through convex lens",
            axis_180_geography="Foreground Left: Zhuge Liang's fingers holding bamboo slip | Center Optical Axis: sleek metal-rimmed convex eyeglass lens sliding smoothly between candle flame and bamboo slip | Background: sharp black ink characters",
            speaker="GuYuan",
            spoken_line="丞相，夜雨湿寒，容属下为您拨亮灯芯。",
            subtext_motivation="顾渊绝不当众喊『丞相您老花眼戴个眼镜吧』（那会瞬间毁掉诸葛亮的统帅威严！），而是以『拨亮灯芯』为掩护，将凸透镜片精准卡在诸葛亮视线与竹简之间，既保全丞相天威，又瞬间破局！",
            emotion_mode="natural",
            character_card="顾渊|随军参军 · 守夜人",
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="upper80v2_P018_high",
                    camera_angle="high",
                    body_blocking="Macro POV of the damp bamboo scroll: the dense tiny brush-ink characters ('张郃、街亭、绝水、断道') are severely out-of-focus and swimming with double-vision ghosting under flickering candlelight.",
                    facial_micro_expression="N/A (Macro Optical POV Insert).",
                    nano_pro_i2i_prompt="16:9 widescreen 100mm macro POV shot. Close-up of an ancient Chinese bamboo scroll held by weathered fingers under candlelight; the tiny black ink characters are blurry and out-of-focus with double-vision ghosting.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.90,
                    pose_id="upper80v2_P018_diag",
                    camera_angle="high",
                    body_blocking="Gu Yuan's steady hand enters from camera-right holding a brass wick trimmer while subtly positioning the convex optical lens right over the bamboo slip along Zhuge Liang's line of sight.",
                    facial_micro_expression="Through the convex lens, the blurry ink characters ('张郃弃大路，奇袭街亭水源') snap into razor-sharp, magnified crystal-clear focus!",
                    nano_pro_i2i_prompt="16:9 widescreen 100mm macro shot. A young scholar's hand enters from camera-right beside a brass oil lamp, holding a sleek convex optical lens over an ancient bamboo scroll. Viewed through the convex lens, the tiny Chinese ink characters snap into magnified, razor-sharp focus with warm golden rim light.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=85,
                    timestamp_sec=3.54,
                    anchor_role="V9_TailLock",
                    strength=0.92,
                    pose_id="upper80v2_P018_front",
                    camera_angle="high",
                    body_blocking="The convex lens remains rock-steady over the bamboo slip, every stroke of '断绝水道' magnified with crisp optical refraction.",
                    facial_micro_expression="N/A (Macro Optical Lock).",
                    nano_pro_i2i_prompt="16:9 widescreen 100mm macro shot. Crystal-clear magnified ink characters on a bamboo slip viewed through a stationary convex optical lens under warm oil lamp light.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:01.000", "Silent_Airlock", "Blurry double-vision bamboo characters swim under flickering oil flame.", "Foley: low tense string tremor."),
                MicroTimelineWindow("00:01.000 - 00:02.900", "Vocal_Climax", "Gu Yuan's hand slides the convex lens into the optical path at frame 51; characters snap into 2x magnified focus.", "Foley: crisp metallic tick + <d>[Mandarin] Gu Yuan respectful low voice</d>."),
                MicroTimelineWindow("00:02.900 - 00:03.750", "Tail_Lock_Hold", "Magnified ink characters ('袭取街亭水源') lock in crystal-clear focus.", "Foley: resonant guqin harmonic chord."),
            ],
        ),
        DecomposedShotSpec(
            shot_id="sg_ep01_s05_zhuge_awakening_command_climax",
            beat_number=5,
            beat_title="破局决断：丞相双目寒光乍现·当场改令破马谡（高燃爽点兑现）",
            shot_type="Hero_Climax",
            continuity_track="track_a_latent_relay",
            golden_frames=141,
            duration_sec=5.88,
            lens_and_movement="50mm anamorphic lens, low-angle slowtilt up and pull back as Zhuge Liang leans forward with thunderous authority",
            axis_180_geography="Camera-Left/Center: Zhuge Liang leaning forward over desk, white feather fan striking the Jieting river valley on the sand table | Camera-Right: Gu Yuan stepping back respectfully into shadow",
            speaker="ZhugeLiang",
            spoken_line="好一个张郃！竟欲断我街亭汲水之道！马谡听令——严禁弃城登山！王平即刻分兵五千死守水源，违令者斩！",
            subtext_motivation="看清竹简上『断绝水道』四字后，诸葛亮瞬间识破张郃毒计并预判了马谡『弃城登山』的死穴，一改前镜的迟疑，雷霆下令逆天改命！",
            emotion_mode="t8mars_explosive",
            character_card=None,
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="full_single_P001_low",
                    camera_angle="low",
                    body_blocking="Zhuge Liang looks through the lens; his furrowed brow suddenly relaxes as a twin glint of cold white light reflects off the lens onto his eyes.",
                    facial_micro_expression="Eyes widening with piercing clarity and awe, exchanging a brief knowing glance with Gu Yuan.",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm low-angle shot. Chancellor Zhuge Liang behind his campaign desk; his brow relaxes as a sharp glint of light illuminates his piercing eyes, white feather fan poised in his right hand. Match pose full_single_P001_low.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.88,
                    pose_id="upper80v2_P022_low",
                    camera_angle="low",
                    body_blocking="Remaining seated with commanding headroom, Zhuge Liang leans his upper torso forward and strikes the tip of his white feather fan decisively onto the Jieting water valley on the sand table.",
                    facial_micro_expression="Commanding, thunderous authority, sword-like eyebrows raised, delivering the decree.",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm low-angle heroic shot. Chancellor Zhuge Liang leans forward with commanding presence, pointing his white crane feather fan sharply at the river pass on the clay sand table under dramatic chiaroscuro candlelight. Match pose upper80v2_P022_low.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=136,
                    timestamp_sec=5.67,
                    anchor_role="V9_TailLock",
                    strength=0.90,
                    pose_id="full_single_P002_front",
                    camera_angle="low",
                    body_blocking="Zhuge Liang holds the wooden command token upright in his left hand and feather fan steady in his right, head held completely level and stationary.",
                    facial_micro_expression="Mouth closed, piercing resolute gaze locked forward (`[107, 136]` V9 TailLock).",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm low-angle shot. Chancellor Zhuge Liang holds a wooden military command token upright, mouth closed and gaze locked steadily forward with supreme authority. Match pose full_single_P002_front.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:01.100", "Silent_Airlock", "Zhuge Liang's brow unfurls; a sharp optical glint flashes across his eyes.", "Foley: sharp wooden token pick-up."),
                MicroTimelineWindow("00:01.100 - 00:04.700", "Vocal_Climax", "He strikes the sand table at frame 51 and issues the life-saving Jieting water-defense order (`+8.2dB` T8mars peak).", "Foley: command token slam at 00:01.200 + <d>[Mandarin] Zhuge Liang thunderous command</d>."),
                MicroTimelineWindow("00:04.700 - 00:05.880", "Tail_Lock_Hold", "Zhuge Liang freezes in heroic command posture (`[107, 136]` V9 TailLock).", "Foley: booming war drum resonance."),
            ],
        ),
    ]
    return {
        "project_id": "sanguo",
        "episode_id": "ep01_qishan_secret_lens",
        "title": "《三国：逆天改命》第一幕精修版：祁山急报与烛下玄机",
        "dramatic_premise": "47岁诸葛亮隐瞒老花眼强撑统帅威严 -> 暴雨夜张郃绝密竹简撞帐、马谡当众催读 -> 丞相推远竹简失焦陷入绝境 -> 顾渊借拨灯芯无声将凸透镜卡入光路保全丞相天威 -> 丞相瞬间看破断水毒计、当场喝止马谡登山",
        "total_shots": len(shots),
        "shots": [asdict(s) for s in shots],
    }


def build_reborn_coder_flagship_blueprint() -> Dict:
    """
    Deep dramatic & frame-by-frame keyframe rework for Project `reborn_coder`:
    《重生之我是天才程序员》EP01 核心重头戏：《零点回档·2014核心熔断前十分钟》
    - 戏剧核心冲突（高密度科技悬疑与精准反杀）：
      35岁的顶尖分布式系统架构师林辰，在 2026 年公司纳斯达克敲钟前夜，发现副总赵坤在底层清算引擎中埋入了延时十年的逻辑炸弹。林辰在机房被锁死缺氧倒下的最后一秒，死死盯住屏幕上那行特征哈希 `0x7F3A_BACKDOOR`——
      下一瞬（Match Cut 瞳孔频闪转场），刺耳的服务器蜂鸣变成 2014 年夏夜创业车库老式机械键盘的清脆敲击声！
      他猛然惊醒，发现自己回到了十年前『星海支付 v1.0』上线发布会的最后 10 分钟！此时，年轻时的赵坤正满脸假笑地站在大屏幕前，手里握着无线演示笔，准备向投资人按下那个包含致命后门的 `Merge Pull Request #409`！
      没有废话解释，林辰在短短 20 秒内，直接盲敲键盘通过 SSH 接管主控大屏，当着全场投资人的面把赵坤隐藏在 C++ 内存指针偏移里的后门当场反编译投屏引爆！
    """
    shots: List[DecomposedShotSpec] = [
        DecomposedShotSpec(
            shot_id="rc_ep01_s01_2026_betrayal_matchcut",
            beat_number=1,
            beat_title="强钩子：2026机房窒息红警 -> 2014发布会倒计时瞳孔匹配转场",
            shot_type="Establishing",
            continuity_track="track_b_hard_cut",
            golden_frames=90,
            duration_sec=3.75,
            lens_and_movement="35mm anamorphic lens, fast dolly-in into extreme close-up of Lin Chen's eye reflecting red server alerts, snapping into warm 2014 fluorescent office light",
            axis_180_geography="Camera-Left: glowing terminal monitor (`00:09:59` countdown) | Center: 25-year-old Lin Chen jolting upright at his mechanical keyboard | Camera-Right: glass conference room where investors gather",
            speaker="LinChen",
            spoken_line="哈希值 0x7F3A……二〇一四年八月十五号？！离 v1.0 主网合并还有九分钟！",
            subtext_motivation="用『瞳孔里的红光倒影切换成2014年的终端时间戳』完成零废话跨时空转场，第一句话直接抛出精确的哈希值与9分钟生死倒计时。",
            emotion_mode="t8mars_explosive",
            character_card="林辰|核心架构师 · 记忆回档者",
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="full_single_P067_diag",
                    camera_angle="diag",
                    body_blocking="Lin Chen slumped forward over a dark desk in front of a glowing dual-monitor terminal, crimson warning reflections fading into 2014 warm desk lamp light.",
                    facial_micro_expression="Eyes snapping wide open in sudden shock, pupils dilated.",
                    nano_pro_i2i_prompt="16:9 widescreen ARRI Alexa 65 frame. Young Chinese software architect Lin Chen in a dark charcoal shirt jolts awake at a coding desk with dual monitors displaying Linux kernel code and a digital clock reading 23:50. Cinematic teal-and-amber lighting. Match pose full_single_P067_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.88,
                    pose_id="full_single_P002_front",
                    camera_angle="front",
                    body_blocking="Lin Chen sits bolt upright, both hands slamming onto the mechanical keyboard as he checks the `git log` hash on the left monitor.",
                    facial_micro_expression="Jaw set tight, cold razor-sharp focus replacing initial shock.",
                    nano_pro_i2i_prompt="16:9 widescreen 35mm medium close-up. Lin Chen sits bolt upright at his workstation, hands poised on a mechanical keyboard, green terminal reflections on his sharp focused face. Match pose full_single_P002_front.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=85,
                    timestamp_sec=3.54,
                    anchor_role="V9_TailLock",
                    strength=0.90,
                    pose_id="full_single_P079_side",
                    camera_angle="diag",
                    body_blocking="Lin Chen turns his gaze 30 degrees toward the glass conference room on camera-right, fingers frozen over the Enter key.",
                    facial_micro_expression="Mouth closed, ice-cold piercing stare.",
                    nano_pro_i2i_prompt="16:9 widescreen medium close-up. Lin Chen at his dual-monitor desk looking sharply toward camera-right with mouth closed and cold determined eyes. Match pose full_single_P079_side.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:00.850", "Silent_Airlock", "Sharp intake of breath as Lin Chen snaps upright from the desk.", "Foley: sub-bass heartbeat cut to crisp fluorescent hum."),
                MicroTimelineWindow("00:00.850 - 00:02.950", "Vocal_Climax", "His hands lock onto the mechanical keyboard at frame 51 as he reads the 2014 date.", "Foley: mechanical keyboard clack + <d>[Mandarin] Lin Chen realization</d>."),
                MicroTimelineWindow("00:02.950 - 00:03.750", "Tail_Lock_Hold", "Gaze locks onto Zhao Kun in the conference room (`[68, 85]` V9 TailLock).", "Foley: tense ticking clock."),
            ],
        ),
        DecomposedShotSpec(
            shot_id="rc_ep01_s02_zhaokun_hypocrisy_ots",
            beat_number=2,
            beat_title="反派施压：赵坤在投资人面前假意邀功、准备合入后门代码",
            shot_type="OTS_A",
            continuity_track="track_b_hard_cut",
            golden_frames=141,
            duration_sec=5.88,
            lens_and_movement="50mm anamorphic lens, OTS from behind Lin Chen standing in the conference room doorway toward Zhao Kun at the 85-inch presentation screen",
            axis_180_geography="Foreground Left: Lin Chen holding a sleek black laptop | Center Background: 85-inch screen showing 'Merge PR #409' button | Camera-Right: Zhao Kun in tailored suit holding laser pointer before seated investors",
            speaker="ZhaoKun",
            spoken_line="各位投资人请看，这套底层清算模块是我连续熬了三个通宵独立重构的，现在我点击合并，星海支付正式上线！",
            subtext_motivation="赵坤不仅剽窃了林辰的架构，还把后门藏在 PR #409 里，企图当着投资人的面既抢走股权又埋下十年后的炸弹。",
            emotion_mode="natural",
            character_card="赵坤|联合创始人 · 技术副总",
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="full_single_P015_diag",
                    camera_angle="diag",
                    body_blocking="Zhao Kun in a bespoke navy suit stands confidently beside the glowing 85-inch presentation screen on camera-right, right hand gesturing toward the 'Merge Pull Request #409' UI.",
                    facial_micro_expression="Smug, polished corporate smile, mouth closed before speaking.",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm OTS shot in a modern glass-walled tech boardroom at night. Foreground left shows silhouette of Lin Chen holding a laptop. On camera-right stands smug executive Zhao Kun in a navy suit beside an 85-inch screen showing Git code merge UI. Match pose full_single_P015_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.86,
                    pose_id="upper80v2_P022_diag",
                    camera_angle="diag",
                    body_blocking="Zhao Kun raises the wireless presenter remote in his right hand, thumb hovering over the confirm button while boasting to the investors.",
                    facial_micro_expression="Arrogant triumphant grin, eyes glancing smugly toward Lin Chen at the door.",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm shot. Zhao Kun in a navy suit raises a wireless presenter remote beside a large presentation screen, smiling smugly at seated venture capital investors. Match pose upper80v2_P022_diag.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=136,
                    timestamp_sec=5.67,
                    anchor_role="V9_TailLock",
                    strength=0.90,
                    pose_id="full_single_P017_front",
                    camera_angle="diag",
                    body_blocking="Zhao Kun freezes as the large screen behind him suddenly flashes crimson 'SSH OVERRIDE: MERGE BLOCKED BY ROOT'.",
                    facial_micro_expression="Smile freezing on his lips, mouth closed, eyes narrowing in sudden confusion.",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm shot. Zhao Kun stands frozen beside the boardroom screen as red terminal warning light illuminates his stunned face, mouth closed. Match pose full_single_P017_front.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:01.100", "Silent_Airlock", "Zhao Kun steps before the 85-inch screen, gesturing smoothly to the investors.", "Foley: quiet boardroom murmur."),
                MicroTimelineWindow("00:01.100 - 00:04.600", "Vocal_Climax", "He boasts of writing the core engine himself and lifts the remote at frame 51.", "<d>[Mandarin] Zhao Kun boastful speech</d>."),
                MicroTimelineWindow("00:04.600 - 00:05.880", "Tail_Lock_Hold", "Red SSH override alert flashes across his face (`[107, 136]` V9 TailLock).", "Foley: sharp digital alert chime."),
            ],
        ),
        DecomposedShotSpec(
            shot_id="rc_ep01_s03_linchen_live_decompile_counter",
            beat_number=3,
            beat_title="降维反杀：林辰盲敲终端劫持大屏，当众拆穿第 412 行内存后门",
            shot_type="Hero_Climax",
            continuity_track="track_b_hard_cut",
            golden_frames=141,
            duration_sec=5.88,
            lens_and_movement="50mm anamorphic lens, medium shot on Lin Chen walking two steps into the boardroom while typing one-handed on his laptop, camera slowly arcing to reveal the projected C++ hex dump behind him",
            axis_180_geography="Camera-Left/Center: Lin Chen holding laptop in left arm, right hand striking Enter | Background Center: 85-inch screen projecting disassembled pointer overflow at line 412 | Camera-Right: stunned investors",
            speaker="LinChen",
            spoken_line="你独立重构的？那请赵总向投资人解释一下，第 412 行这个指向海外匿名账户的未对齐指针偏移，也是你写的吗？",
            subtext_motivation="林辰不跟赵坤吵架，直接用工程师最硬核的方式——当众投屏反汇编代码与资金劫持地址，一剑封喉！",
            emotion_mode="t8mars_explosive",
            character_card=None,
            keyframe_anchors=[
                KeyframeAnchorSpec(
                    frame_idx=0,
                    timestamp_sec=0.00,
                    anchor_role="StartLock_F0",
                    strength=1.0,
                    pose_id="full_single_P015_front",
                    camera_angle="low",
                    body_blocking="Lin Chen stands in the glass doorway cradling his open laptop on his left forearm, right index finger pressing the Enter key decisively.",
                    facial_micro_expression="Mouth closed, calm razor-sharp eyes locked on Zhao Kun.",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm low-angle shot. Young Chinese tech architect Lin Chen stands in a modern boardroom holding an open laptop on his left arm, right finger pressing Enter, red-and-cyan code projected behind him. Match pose full_single_P015_front.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=51,
                    timestamp_sec=2.12,
                    anchor_role="MidAction_17k",
                    strength=0.88,
                    pose_id="upper80v2_P022_low",
                    camera_angle="low",
                    body_blocking="Lin Chen tilts the laptop screen toward the seated investors while his right hand points sharply at line 412 highlighted in red on the giant 85-inch display.",
                    facial_micro_expression="Cold, commanding precision, delivering the surgical question.",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm low-angle shot. Lin Chen holds his laptop in his left hand and points sharply with his right hand toward the highlighted red code block on the boardroom screen behind him. Match pose upper80v2_P022_low.",
                ),
                KeyframeAnchorSpec(
                    frame_idx=136,
                    timestamp_sec=5.67,
                    anchor_role="V9_TailLock",
                    strength=0.90,
                    pose_id="full_single_P022_front",
                    camera_angle="low",
                    body_blocking="Lin Chen snaps his laptop half-shut with a crisp click, standing tall and stationary under the cool boardroom spotlights.",
                    facial_micro_expression="Lips closed, unshakeable cold gaze locked on camera-right (`[107, 136]` V9 TailLock).",
                    nano_pro_i2i_prompt="16:9 widescreen 50mm low-angle shot. Lin Chen stands tall in the boardroom holding his laptop, mouth closed and gaze locked steadily toward camera-right under dramatic lighting. Match pose full_single_P022_front.",
                ),
            ],
            micro_timeline=[
                MicroTimelineWindow("00:00.000 - 00:01.100", "Silent_Airlock", "Lin Chen presses Enter; the giant screen behind him flips to line 412 hex dump.", "Foley: crisp Enter key strike + projector relay click."),
                MicroTimelineWindow("00:01.100 - 00:04.700", "Vocal_Climax", "He points at line 412 at frame 51, exposing the hidden offshore pointer exploit.", "<d>[Mandarin] Lin Chen surgical counter-strike</d>."),
                MicroTimelineWindow("00:04.700 - 00:05.880", "Tail_Lock_Hold", "Lin Chen holds his cold commanding gaze as the boardroom erupts in shock (`[107, 136]` V9 TailLock).", "Foley: dramatic low synth bass drop."),
            ],
        ),
    ]
    return {
        "project_id": "reborn_coder",
        "episode_id": "ep01_zero_hour_rollback",
        "title": "《重生之我是天才程序员》第一幕精修版：零点回档与第412行反杀",
        "dramatic_premise": "2026机房窒息红警与特征哈希0x7F3A -> 瞳孔匹配转场回到2014年v1.0上线前9分钟 -> 副总赵坤当着投资人剽窃架构并准备点击合并后门PR -> 林辰SSH盲敲劫持大屏、当众反汇编第412行内存偏移一剑封喉",
        "total_shots": len(shots),
        "shots": [asdict(s) for s in shots],
    }


def export_markdown_beat_sheet(blueprint: Dict) -> str:
    lines = [
        f"# 🎬 {blueprint['title']}",
        "",
        f"- **所属项目 (`project_id`)**: `{blueprint['project_id']}`",
        f"- **剧集标识 (`episode_id`)**: `{blueprint['episode_id']}`",
        f"- **核心戏剧冲突链 (`Dramatic Premise`)**: {blueprint['dramatic_premise']}",
        "",
        "---",
        "",
    ]
    for sh in blueprint["shots"]:
        lines.extend([
            f"## Beat {sh['beat_number']} · `{sh['shot_id']}` — {sh['beat_title']}",
            f"- **机位类型**: `{sh['shot_type']}` | **连续性轨道**: `{sh['continuity_track']}` | **黄金帧长**: `{sh['golden_frames']} 帧 ({sh['duration_sec']}s)`",
            f"- **摄影机焦段与运动**: `{sh['lens_and_movement']}`",
            f"- **180° 南侧空间拓扑锁**: `{sh['axis_180_geography']}`",
            f"- **角色与表层台词 (`{sh['speaker']}`)**: 「{sh['spoken_line']}」",
            f"- **潜台词与导演意图 (Subtext)**: *{sh['subtext_motivation']}*",
            "",
            "### 🎞️ 单镜内部 `17k` 逐帧关键帧拆解表 (Intra-Shot Keyframe Decomposition)",
            "| 帧索引 (`17k`) | 时间戳 | 锚点角色 (`Role`) | 锁死强度 | 绑定姿态库 (`POSE-DB-01`) | 肢体动作与手部朝向 (`Body Blocking`) | 面部微表情与口型状态 (`Micro-Expression`) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for kf in sh["keyframe_anchors"]:
            lines.append(
                f"| **`Frame {kf['frame_idx']}`** | `{kf['timestamp_sec']:.2f}s` | `{kf['anchor_role']}` | `{kf['strength']}` | `{kf['pose_id']}` (`{kf['camera_angle']}`) | {kf['body_blocking']} | {kf['facial_micro_expression']} |"
            )
        lines.extend([
            "",
            "### ⏱️ 毫秒级声画包络与气闸舱时间轴 (Micro-Timeline Envelope)",
        ])
        for mt in sh["micro_timeline"]:
            lines.append(f"- **`[{mt['window_sec']}]` ({mt['phase_type']})**: {mt['visual_trajectory']} ｜ 🔊 *{mt['acoustic_cue']}*")
        lines.append("\n---\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AetherDirector 4-Level Story-to-Keyframe Decomposer")
    parser.add_argument("--project", choices=["sanguo", "reborn_coder", "all"], default="all")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    outputs = []
    if args.project in ("sanguo", "all"):
        bp_sg = build_sanguo_flagship_blueprint()
        out_dir = root / "episodes" / bp_sg["episode_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "story_keyframe_blueprint.json").write_text(json.dumps(bp_sg, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "director_beat_sheet.md").write_text(export_markdown_beat_sheet(bp_sg), encoding="utf-8")
        outputs.append(str(out_dir / "director_beat_sheet.md"))

    if args.project in ("reborn_coder", "all"):
        bp_rc = build_reborn_coder_flagship_blueprint()
        out_dir = root / "projects" / "reborn_coder" / "episodes" / bp_rc["episode_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "story_keyframe_blueprint.json").write_text(json.dumps(bp_rc, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "director_beat_sheet.md").write_text(export_markdown_beat_sheet(bp_rc), encoding="utf-8")
        outputs.append(str(out_dir / "director_beat_sheet.md"))

    print(json.dumps({"ok": True, "generated_blueprints": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
