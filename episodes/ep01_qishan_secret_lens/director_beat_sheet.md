# 🎬 《三国：逆天改命》第一幕精修版：祁山急报与烛下玄机

- **所属项目 (`project_id`)**: `sanguo`
- **剧集标识 (`episode_id`)**: `ep01_qishan_secret_lens`
- **核心戏剧冲突链 (`Dramatic Premise`)**: 47岁诸葛亮隐瞒老花眼强撑统帅威严 -> 暴雨夜张郃绝密竹简撞帐、马谡当众催读 -> 丞相推远竹简失焦陷入绝境 -> 顾渊借拨灯芯无声将凸透镜卡入光路保全丞相天威 -> 丞相瞬间看破断水毒计、当场喝止马谡登山

---

## Beat 1 · `sg_ep01_s01_storm_courier_hook` — 强钩子：暴雨急报撞帐（0-3.75秒生死倒计时切入）
- **机位类型**: `Establishing` | **连续性轨道**: `track_b_hard_cut` | **黄金帧长**: `90 帧 (3.75s)`
- **摄影机焦段与运动**: `28mm anamorphic lens, low-angle tracking push-in following the mud-splattered scout bursting through the tent flap`
- **180° 南侧空间拓扑锁**: `Camera-Left: rain-lashed tent entrance & iron brazier | Center: mud-soaked scout dropping to one knee | Camera-Right: assembled Shu generals turning in alarm`
- **角色与表层台词 (`Scout`)**: 「报——！陇右八百里加急！张郃前锋已过渭水，截获魏军绝密调兵竹简！」
- **潜台词与导演意图 (Subtext)**: *打破平庸开场，第一秒就用带血的未读绝密军报把诸葛亮推入『必须当众立即研判蝇头细字』的绝境。*

### 🎞️ 单镜内部 `17k` 逐帧关键帧拆解表 (Intra-Shot Keyframe Decomposition)
| 帧索引 (`17k`) | 时间戳 | 锚点角色 (`Role`) | 锁死强度 | 绑定姿态库 (`POSE-DB-01`) | 肢体动作与手部朝向 (`Body Blocking`) | 面部微表情与口型状态 (`Micro-Expression`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Frame 0`** | `0.00s` | `StartLock_F0` | `1.0` | `full_single_P035_diag` (`low`) | Scout in rain-drenched leather armor bursts through heavy canvas tent flap from camera-left, right hand clutching a blood-stained bamboo scroll high. | Mouth closed in a sharp inhalation, rain streaming down brow, eyes wide with urgency. |
| **`Frame 51`** | `2.12s` | `MidAction_17k` | `0.88` | `full_single_P022_diag` (`diag`) | Scout drops heavily onto one knee in the muddy straw at center foreground, both hands thrusting the bamboo scroll forward toward the main command desk. | Veins taut on neck, roaring the urgent dispatch. |
| **`Frame 85`** | `3.54s` | `V9_TailLock` | `0.9` | `full_single_P022_front` (`diag`) | Scout holds the kneeling posture steady with head bowed, bamboo scroll held level in both hands, chest heaving silently. | Lips pressed shut, breathing heavily through nose, gaze locked downward. |

### ⏱️ 毫秒级声画包络与气闸舱时间轴 (Micro-Timeline Envelope)
- **`[00:00.000 - 00:00.850]` (Silent_Airlock)**: Heavy canvas tent flap whips open; scout lunges two steps inward. ｜ 🔊 *Foley: violent canvas flap snap + thunder rumble outside.*
- **`[00:00.850 - 00:02.950]` (Vocal_Climax)**: Scout crashes to one knee at frame 51, thrusting scroll up. ｜ 🔊 *Foley: knee armor slam at 00:00.900 + <d>[Mandarin] urgent report</d>.*
- **`[00:02.950 - 00:03.750]` (Tail_Lock_Hold)**: Scout freezes in bowed kneeling posture (`[68, 85]` V9 TailLock). ｜ 🔊 *Foley: dripping rainwater on floor, tense silence.*

---

## Beat 2 · `sg_ep01_s02_masu_pressure_ots` — 人际施压：马谡傲慢请战与众将逼视（把丞相架在火上烤）
- **机位类型**: `OTS_A` | **连续性轨道**: `track_b_hard_cut` | **黄金帧长**: `141 帧 (5.88s)`
- **摄影机焦段与运动**: `50mm anamorphic lens, over-the-shoulder from behind Zhuge Liang's left shoulder toward Ma Su and Wei Yan on camera-right, slow tense push-in`
- **180° 南侧空间拓扑锁**: `Foreground Left: Zhuge Liang's dark-teal GuanJin shoulder silhouette | Center: clay sand table of Jieting | Right Midground: Ma Su stepping forward arrogantly beside Wei Yan`
- **角色与表层台词 (`MaSu`)**: 「丞相！区区张郃何足道哉？请丞相即刻宣读竹简军情，某愿立军令状，连夜赶往街亭屯兵当道！」
- **潜台词与导演意图 (Subtext)**: *马谡急于抢功，当众催促诸葛亮『即刻宣读竹简』，无形中封死了诸葛亮退后私阅的退路，将戏剧张力拉满。*

### 🎞️ 单镜内部 `17k` 逐帧关键帧拆解表 (Intra-Shot Keyframe Decomposition)
| 帧索引 (`17k`) | 时间戳 | 锚点角色 (`Role`) | 锁死强度 | 绑定姿态库 (`POSE-DB-01`) | 肢体动作与手部朝向 (`Body Blocking`) | 面部微表情与口型状态 (`Micro-Expression`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Frame 0`** | `0.00s` | `StartLock_F0` | `1.0` | `full_single_P015_diag` (`diag`) | Ma Su in silver-scale armor and white battle cloak stands on camera-right behind the Jieting sand table, chin slightly raised. | Confident, haughty composure, lips closed before speaking. |
| **`Frame 51`** | `2.12s` | `MidAction_17k` | `0.86` | `upper80v2_P016_diag` (`diag`) | Ma Su takes half a step toward the sand table, right hand clasping his left fist in a sharp military salute while speaking. | Brows arched with pride, eyes locked onto the bamboo scroll on Zhuge Liang's desk. |
| **`Frame 136`** | `5.67s` | `V9_TailLock` | `0.9` | `upper80v2_P016_front` (`diag`) | Ma Su holds his clasped-hand salute stationary, head held level, waiting expectantly for Zhuge Liang to read the scroll aloud. | Mouth closed, expectant proud gaze locked toward camera-left. |

### ⏱️ 毫秒级声画包络与气闸舱时间轴 (Micro-Timeline Envelope)
- **`[00:00.000 - 00:01.100]` (Silent_Airlock)**: Ma Su shifts weight forward beside the sand table, armor plates clicking softly. ｜ 🔊 *Foley: subtle silver armor clink.*
- **`[00:01.100 - 00:04.600]` (Vocal_Climax)**: Ma Su salutes at frame 51 and urges Zhuge Liang to read the dispatch aloud immediately. ｜ 🔊 *<d>[Mandarin] Ma Su dialogue</d>.*
- **`[00:04.600 - 00:05.880]` (Tail_Lock_Hold)**: All generals' eyes lock onto Zhuge Liang (`[107, 136]` V9 TailLock). ｜ 🔊 *Foley: oil lamp wick crackle.*

---

## Beat 3 · `sg_ep01_s03_zhuge_hidden_presbyopia_crisis` — 隐秘危机：丞相展简失焦（Show, Don't Tell 物理光学细节）
- **机位类型**: `OTS_B_Reverse` | **连续性轨道**: `track_b_hard_cut` | **黄金帧长**: `141 帧 (5.88s)`
- **摄影机焦段与运动**: `85mm anamorphic portrait lens, medium close-up on Zhuge Liang seated at camera-left desk, shallow depth of field`
- **180° 南侧空间拓扑锁**: `Camera-Left/Center: Zhuge Liang seated behind wooden desk holding unrolled bamboo scroll | Camera-Right Background: Gu Yuan standing quietly in half-shadow behind the brass oil lamp`
- **角色与表层台词 (`ZhugeLiang`)**: 「且慢……张郃用兵老辣，此简所载行军里数，干系三军生死……」
- **潜台词与导演意图 (Subtext)**: *诸葛亮嘴上说『且慢、干系三军生死』是在拖延时间！画面上他将竹简一点点推远到一臂之外、眉头紧锁微眯双眼，用纯物理动作告诉观众：他看不清上面的蝇头小楷！*

### 🎞️ 单镜内部 `17k` 逐帧关键帧拆解表 (Intra-Shot Keyframe Decomposition)
| 帧索引 (`17k`) | 时间戳 | 锚点角色 (`Role`) | 锁死强度 | 绑定姿态库 (`POSE-DB-01`) | 肢体动作与手部朝向 (`Body Blocking`) | 面部微表情与口型状态 (`Micro-Expression`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Frame 0`** | `0.00s` | `StartLock_F0` | `1.0` | `full_single_P002_front` (`front`) | 47-year-old Zhuge Liang sits upright in teal GuanJin and white crane robe, unrolling the bamboo scroll at normal reading distance with both hands. | Dignified calm mask, mouth closed, eyes dropping to the bamboo slips. |
| **`Frame 51`** | `2.12s` | `MidAction_17k` | `0.88` | `full_single_P012_diag` (`diag`) | Zhuge Liang slowly extends his arms to push the bamboo scroll further away to arm's length while keeping his shoulders composed so the generals do not notice. | Subtle squint of his eyes, fine bead of sweat on temple under candlelight, speaking slowly and gravely. |
| **`Frame 136`** | `5.67s` | `V9_TailLock` | `0.9` | `full_single_P012_front` (`diag`) | Zhuge Liang's right thumb presses tightly against the edge of the bamboo slip to steady a faint tremor, head held level. | Lips closed, solemn strained gaze fixed on the scroll. |

### ⏱️ 毫秒级声画包络与气闸舱时间轴 (Micro-Timeline Envelope)
- **`[00:00.000 - 00:01.100]` (Silent_Airlock)**: Zhuge Liang unrolls the bamboo scroll; his pupils contract as the tiny ink characters blur. ｜ 🔊 *Foley: dry bamboo slips unrolling.*
- **`[00:01.100 - 00:04.500]` (Vocal_Climax)**: He subtly pushes the scroll to arm's length at frame 51 while speaking slowly to buy time. ｜ 🔊 *<d>[Mandarin] Zhuge Liang stalling line</d>.*
- **`[00:04.500 - 00:05.880]` (Tail_Lock_Hold)**: In the background shadow, Gu Yuan's eyes lock onto Zhuge Liang's outstretched arms (`[107, 136]` V9 TailLock). ｜ 🔊 *Foley: tense heartbeat-like drum pulse.*

---

## Beat 4 · `sg_ep01_s04_pov_blur_to_lens_insert` — 微距铁证：失焦蝇头小楷 vs 借拨灯芯无声入画的凸透镜（全场高潮转折）
- **机位类型**: `ECU_Insert` | **连续性轨道**: `track_b_hard_cut` | **黄金帧长**: `90 帧 (3.75s)`
- **摄影机焦段与运动**: `100mm macro lens, extreme close-up over Zhuge Liang's optical axis onto the bamboo slips, rack focus through convex lens`
- **180° 南侧空间拓扑锁**: `Foreground Left: Zhuge Liang's fingers holding bamboo slip | Center Optical Axis: sleek metal-rimmed convex eyeglass lens sliding smoothly between candle flame and bamboo slip | Background: sharp black ink characters`
- **角色与表层台词 (`GuYuan`)**: 「丞相，夜雨湿寒，容属下为您拨亮灯芯。」
- **潜台词与导演意图 (Subtext)**: *顾渊绝不当众喊『丞相您老花眼戴个眼镜吧』（那会瞬间毁掉诸葛亮的统帅威严！），而是以『拨亮灯芯』为掩护，将凸透镜片精准卡在诸葛亮视线与竹简之间，既保全丞相天威，又瞬间破局！*

### 🎞️ 单镜内部 `17k` 逐帧关键帧拆解表 (Intra-Shot Keyframe Decomposition)
| 帧索引 (`17k`) | 时间戳 | 锚点角色 (`Role`) | 锁死强度 | 绑定姿态库 (`POSE-DB-01`) | 肢体动作与手部朝向 (`Body Blocking`) | 面部微表情与口型状态 (`Micro-Expression`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Frame 0`** | `0.00s` | `StartLock_F0` | `1.0` | `upper80v2_P018_high` (`high`) | Macro POV of the damp bamboo scroll: the dense tiny brush-ink characters ('张郃、街亭、绝水、断道') are severely out-of-focus and swimming with double-vision ghosting under flickering candlelight. | N/A (Macro Optical POV Insert). |
| **`Frame 51`** | `2.12s` | `MidAction_17k` | `0.9` | `upper80v2_P018_diag` (`high`) | Gu Yuan's steady hand enters from camera-right holding a brass wick trimmer while subtly positioning the convex optical lens right over the bamboo slip along Zhuge Liang's line of sight. | Through the convex lens, the blurry ink characters ('张郃弃大路，奇袭街亭水源') snap into razor-sharp, magnified crystal-clear focus! |
| **`Frame 85`** | `3.54s` | `V9_TailLock` | `0.92` | `upper80v2_P018_front` (`high`) | The convex lens remains rock-steady over the bamboo slip, every stroke of '断绝水道' magnified with crisp optical refraction. | N/A (Macro Optical Lock). |

### ⏱️ 毫秒级声画包络与气闸舱时间轴 (Micro-Timeline Envelope)
- **`[00:00.000 - 00:01.000]` (Silent_Airlock)**: Blurry double-vision bamboo characters swim under flickering oil flame. ｜ 🔊 *Foley: low tense string tremor.*
- **`[00:01.000 - 00:02.900]` (Vocal_Climax)**: Gu Yuan's hand slides the convex lens into the optical path at frame 51; characters snap into 2x magnified focus. ｜ 🔊 *Foley: crisp metallic tick + <d>[Mandarin] Gu Yuan respectful low voice</d>.*
- **`[00:02.900 - 00:03.750]` (Tail_Lock_Hold)**: Magnified ink characters ('袭取街亭水源') lock in crystal-clear focus. ｜ 🔊 *Foley: resonant guqin harmonic chord.*

---

## Beat 5 · `sg_ep01_s05_zhuge_awakening_command_climax` — 破局决断：丞相双目寒光乍现·当场改令破马谡（高燃爽点兑现）
- **机位类型**: `Hero_Climax` | **连续性轨道**: `track_a_latent_relay` | **黄金帧长**: `141 帧 (5.88s)`
- **摄影机焦段与运动**: `50mm anamorphic lens, low-angle slowtilt up and pull back as Zhuge Liang leans forward with thunderous authority`
- **180° 南侧空间拓扑锁**: `Camera-Left/Center: Zhuge Liang leaning forward over desk, white feather fan striking the Jieting river valley on the sand table | Camera-Right: Gu Yuan stepping back respectfully into shadow`
- **角色与表层台词 (`ZhugeLiang`)**: 「好一个张郃！竟欲断我街亭汲水之道！马谡听令——严禁弃城登山！王平即刻分兵五千死守水源，违令者斩！」
- **潜台词与导演意图 (Subtext)**: *看清竹简上『断绝水道』四字后，诸葛亮瞬间识破张郃毒计并预判了马谡『弃城登山』的死穴，一改前镜的迟疑，雷霆下令逆天改命！*

### 🎞️ 单镜内部 `17k` 逐帧关键帧拆解表 (Intra-Shot Keyframe Decomposition)
| 帧索引 (`17k`) | 时间戳 | 锚点角色 (`Role`) | 锁死强度 | 绑定姿态库 (`POSE-DB-01`) | 肢体动作与手部朝向 (`Body Blocking`) | 面部微表情与口型状态 (`Micro-Expression`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Frame 0`** | `0.00s` | `StartLock_F0` | `1.0` | `full_single_P001_low` (`low`) | Zhuge Liang looks through the lens; his furrowed brow suddenly relaxes as a twin glint of cold white light reflects off the lens onto his eyes. | Eyes widening with piercing clarity and awe, exchanging a brief knowing glance with Gu Yuan. |
| **`Frame 51`** | `2.12s` | `MidAction_17k` | `0.88` | `upper80v2_P022_low` (`low`) | Remaining seated with commanding headroom, Zhuge Liang leans his upper torso forward and strikes the tip of his white feather fan decisively onto the Jieting water valley on the sand table. | Commanding, thunderous authority, sword-like eyebrows raised, delivering the decree. |
| **`Frame 136`** | `5.67s` | `V9_TailLock` | `0.9` | `full_single_P002_front` (`low`) | Zhuge Liang holds the wooden command token upright in his left hand and feather fan steady in his right, head held completely level and stationary. | Mouth closed, piercing resolute gaze locked forward (`[107, 136]` V9 TailLock). |

### ⏱️ 毫秒级声画包络与气闸舱时间轴 (Micro-Timeline Envelope)
- **`[00:00.000 - 00:01.100]` (Silent_Airlock)**: Zhuge Liang's brow unfurls; a sharp optical glint flashes across his eyes. ｜ 🔊 *Foley: sharp wooden token pick-up.*
- **`[00:01.100 - 00:04.700]` (Vocal_Climax)**: He strikes the sand table at frame 51 and issues the life-saving Jieting water-defense order (`+8.2dB` T8mars peak). ｜ 🔊 *Foley: command token slam at 00:01.200 + <d>[Mandarin] Zhuge Liang thunderous command</d>.*
- **`[00:04.700 - 00:05.880]` (Tail_Lock_Hold)**: Zhuge Liang freezes in heroic command posture (`[107, 136]` V9 TailLock). ｜ 🔊 *Foley: booming war drum resonance.*

---
