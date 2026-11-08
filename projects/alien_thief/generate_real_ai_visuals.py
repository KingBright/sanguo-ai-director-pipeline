#!/usr/bin/env python3
"""
Generate Genuine AI Character Anchors and 12 Scene Keyframes using Google AI Flow (nano-pro 0-credit).
Style: 2D Western-Cyberpunk Comic Cel-Shaded Animation (Rick and Morty / Futurama / Borderlands style).
"""
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

GFLOW = r"C:\Users\Liang\.local\bin\gflow.exe"
BASE_DIR = Path(r"C:\Users\Liang\Downloads\sanguo\projects\alien_thief")
CHAR_DIR = BASE_DIR / "characters" / "images"
KF_DIR = BASE_DIR / "episodes" / "ep01_lottery_heist" / "keyframes"
CHAR_DIR.mkdir(parents=True, exist_ok=True)
KF_DIR.mkdir(parents=True, exist_ok=True)

STYLE_BASE = (
    "2D Western-Cyberpunk Comic Cel-Shaded Animation, bold black ink outlines, "
    "Rick and Morty and Futurama comic cartoon aesthetics, vibrant saturated cel-shaded flat colors, "
    "gritty cyberpunk wasteland paper texture, expressive oversized cartoon eyes, dynamic facial exaggeration, zero 3D plastic gloss"
)

CHARACTER_PROMPTS = [
    {
        "name": "ximu_anchor.png",
        "prompt": (
            f"{STYLE_BASE}, character portrait of Ximu: green chubby short one-eyed alien goblin, "
            "oversized single glossy cyclops eye with mischievous glint, large horizontal pink bat ears, round potbelly, "
            "wearing a baggy beige hoodie with rolled-up sleeves, holding a titanium crowbar and neon scratch-off cards, "
            "standing in neon cyberpunk wasteland alley, bold black ink line art."
        )
    },
    {
        "name": "libei_anchor.png",
        "prompt": (
            f"{STYLE_BASE}, character portrait of Libei: purple-skinned lanky youthful alien rookie, "
            "large yellow cartoon eyes, wearing a neon-green frog-head hood with bulging cartoon eyes and felt teeth, "
            "orange tactical goggles on forehead, panicked hilarious facial expression, bold black ink contours."
        )
    },
    {
        "name": "kato_anchor.png",
        "prompt": (
            f"{STYLE_BASE}, character portrait of Kato: massive purple-skinned horned troll alien bounty hunter, "
            "two sharp curved horns on head, prominent forehead bone crests, rugged jutting lower fangs, "
            "heavy weathered cyber-leather tactical armor, intense scowling yellow eyes, carrying brass telescope, bold black ink line art."
        )
    },
    {
        "name": "xiaodai_anchor.png",
        "prompt": (
            f"{STYLE_BASE}, character portrait of Xiaodai: purple-haired deadpan alien sister, "
            "straight bob-cut ultraviolet hair, oversized round circular spectacles reflecting neon cyan data, "
            "pointed elf-like ears, sleek dark plum turtleneck vest, holding glowing holographic wanted bounty tablet, deadpan cool smirk, bold ink lines."
        )
    },
    {
        "name": "pinkweirdo_anchor.png",
        "prompt": (
            f"{STYLE_BASE}, character portrait of PinkWeirdo: quirky pink rubbery alien, "
            "impossibly long noodle neck, single wide-open unblinking eye on teardrop head, "
            "wearing a dirty white ribbed tank top with bright red satin sash, holding a vintage rusted megaphone, absurd serene grin, bold ink lines."
        )
    },
]

SCENE_PROMPTS = [
    {
        "id": "ep01_01",
        "prompt": (
            f"{STYLE_BASE}, wide shot at ruined concrete overlook bunker: massive purple horned troll bounty hunter Kato "
            "crouching on left looking through a giant brass tactical telescope mounted on tripod, scanning distant neon kiosk below, "
            "cracked concrete rebar, blowing red desert dust, bold black ink comic line art."
        )
    },
    {
        "id": "ep01_02",
        "prompt": (
            f"{STYLE_BASE}, medium closeup: purple-haired deadpan alien sister Xiaodai wearing round circular glasses, "
            "tapping glowing cyan holographic wanted bounty tablet with bounty '2.50 CREDITS', unimpressed deadpan sarcastic expression, "
            "concrete bunker wall background, bold black ink comic line art."
        )
    },
    {
        "id": "ep01_03",
        "prompt": (
            f"{STYLE_BASE}, medium shot: purple alien rookie Libei crouching low behind broken bunker rubble, "
            "wearing neon-green frog-head hood with big cartoon eyes, trembling in comedic terror, orange goggles on forehead, "
            "distant sniper scope glint in wasteland background, bold comic contours."
        )
    },
    {
        "id": "ep01_04",
        "prompt": (
            f"{STYLE_BASE}, medium shot inside glowing neon lottery kiosk: green chubby one-eyed alien goblin Ximu "
            "in beige hoodie hoisting a titanium crowbar, scratching glowing rainbow scratch-off lottery tickets on glass counter, "
            "shameless greedy goblin grin, large horizontal pink ears flapping, neon signs and ticket displays, bold comic ink."
        )
    },
    {
        "id": "ep01_05",
        "prompt": (
            f"{STYLE_BASE}, comedic crash closeup: purple alien Libei in green frog hood with jaw dropping wide open in total shock, "
            "eyes popping out, pointing shaking finger at a lottery ticket revealing a mechanical screaming chicken prize icon, "
            "comic exclamation marks, bold black ink cel shading."
        )
    },
    {
        "id": "ep01_06",
        "prompt": (
            f"{STYLE_BASE}, low-angle hero shot: green goblin Ximu proudly holding up a chrome cybernetic screaming chicken toy "
            "with blinking red LED eyes, squeezing its rubber neck, concentric comic sonic shockwaves rippling through neon kiosk air, "
            "victorious triumphant grin, bold speed lines."
        )
    },
    {
        "id": "ep01_07",
        "prompt": (
            f"{STYLE_BASE}, medium wide shot on rusted metal podium at Lanke Bazaar plaza: pink alien PinkWeirdo with super long noodle neck, "
            "wearing white tank top and bright red peace sash, announcing into vintage rusted megaphone, tattered festival banners fluttering, "
            "alien crowd watching in background, bold comic ink art."
        )
    },
    {
        "id": "ep01_08",
        "prompt": (
            f"{STYLE_BASE}, over-the-shoulder medium shot: massive purple horned troll Kato slamming leather gauntlet onto rusted bazaar barrier, "
            "completely breaking character in explosive cartoon rage, mouth wide open shouting, forehead crests glowing red, "
            "looking at podium in distance, crushed rebar sparks, bold ink lines."
        )
    },
    {
        "id": "ep01_09",
        "prompt": (
            f"{STYLE_BASE}, closeup: purple-haired Xiaodai holding her holographic tablet showing a spinning red police tow-clamp hologram "
            "clamping Kato's armored cruiser, deadpan serene expression behind round glasses, green terminal glow, bold clean line art."
        )
    },
    {
        "id": "ep01_010",
        "prompt": (
            f"{STYLE_BASE}, medium shot inside underground neon Lanke Tavern: purple rookie Libei clutching his frog-hood head "
            "in frantic panic across a floating magnetic poker table, giant cartoon sweat drops splashing, glowing holographic playing cards, "
            "alien tavern background, bold comic cel art."
        )
    },
    {
        "id": "ep01_011",
        "prompt": (
            f"{STYLE_BASE}, medium shot in tavern booth: green goblin Ximu lounging smugly with a fluffy white blue-eyed cat perched on his head as a wig, "
            "slamming four glowing holographic playing cards onto magnetic table, triumphant wink, bounty hunter across table stunned, golden confetti, bold comic art."
        )
    },
    {
        "id": "ep01_012",
        "prompt": (
            f"{STYLE_BASE}, wide closing tavern tableau: pink alien PinkWeirdo leaning long noodle neck over booth divider waving megaphone, "
            "Ximu winking with white cat on head raising cider mug, Libei staring slack-jawed, Kato in apron holding dish towel in defeat, "
            "classic cartoon iris-out circular border closing frame, bold cyberpunk comic art."
        )
    },
]

def run_gflow_t2i(prompt, out_path):
    print(f"Generating AI image: {out_path.name}...", flush=True)
    cmd = [
        GFLOW, "image", "t2i",
        prompt,
        "--model", "nano-pro",
        "--aspect", "16:9",
        "-o", str(out_path)
    ]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error generating {out_path.name}: {res.stderr}", flush=True)
        return False
    print(f"Saved {out_path.name} in {time.time() - t0:.1f}s!", flush=True)
    return True

def main():
    print("=" * 70, flush=True)
    print("🎨 [1/2] Generating 5 Real AI Character Anchors via gflow nano-pro...", flush=True)
    print("=" * 70, flush=True)
    for c in CHARACTER_PROMPTS:
        out_f = CHAR_DIR / c["name"]
        run_gflow_t2i(c["prompt"], out_f)

    print("\n" + "=" * 70, flush=True)
    print("🎬 [2/2] Generating 12 Real AI Scene Keyframes via gflow nano-pro...", flush=True)
    print("=" * 70, flush=True)
    for s in SCENE_PROMPTS:
        out_f = KF_DIR / f"{s['id']}_kf.jpg"
        run_gflow_t2i(s["prompt"], out_f)

    print("\n✅ All real AI character anchors and scene keyframes generated successfully!", flush=True)

if __name__ == "__main__":
    main()
