#!/usr/bin/env python3
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

STYLE_BASE = (
    "2D Western-Cyberpunk Comic Cel-Shaded Animation, bold black ink outlines, "
    "Rick and Morty and Futurama comic cartoon aesthetics, vibrant saturated cel-shaded flat colors, "
    "gritty cyberpunk wasteland paper texture, expressive oversized cartoon eyes, dynamic facial exaggeration, zero 3D plastic gloss"
)

MISSING = [
    {
        "id": "ep01_02",
        "prompt": (
            f"{STYLE_BASE}, medium closeup: purple-haired deadpan alien sister Xiaodai wearing round circular glasses, "
            "tapping glowing cyan holographic wanted bounty tablet with bounty '2.50 CREDITS', unimpressed deadpan sarcastic expression, "
            "concrete bunker wall background, bold black ink comic line art."
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
        "id": "ep01_10",
        "prompt": (
            f"{STYLE_BASE}, medium shot inside underground neon Lanke Tavern: purple rookie Libei clutching his frog-hood head "
            "in frantic panic across a floating magnetic poker table, giant cartoon sweat drops splashing, glowing holographic playing cards, "
            "alien tavern background, bold comic cel art."
        )
    },
    {
        "id": "ep01_11",
        "prompt": (
            f"{STYLE_BASE}, medium shot in tavern booth: green goblin Ximu lounging smugly with a fluffy white blue-eyed cat perched on his head as a wig, "
            "slamming four glowing holographic playing cards onto magnetic table, triumphant wink, bounty hunter across table stunned, golden confetti, bold comic art."
        )
    },
    {
        "id": "ep01_12",
        "prompt": (
            f"{STYLE_BASE}, wide closing tavern tableau: pink alien PinkWeirdo leaning long noodle neck over booth divider waving megaphone, "
            "Ximu winking with white cat on head raising cider mug, Libei staring slack-jawed, Kato in apron holding dish towel in defeat, "
            "classic cartoon iris-out circular border closing frame, bold cyberpunk comic art."
        )
    },
]

def main():
    # Ensure character anchors have .png versions
    for anchor in ["kato_anchor", "libei_anchor", "pinkweirdo_anchor", "xiaodai_anchor", "ximu_anchor"]:
        jpg_p = CHAR_DIR / f"{anchor}.jpg"
        png_p = CHAR_DIR / f"{anchor}.png"
        if jpg_p.exists() and not png_p.exists():
            from PIL import Image
            Image.open(str(jpg_p)).save(str(png_p), "PNG")
            print(f"Synced {anchor}.png from {anchor}.jpg", flush=True)

    for item in MISSING:
        sc_id = item["id"]
        out_f = KF_DIR / f"{sc_id}_kf.jpg"
        if out_f.exists() and out_f.stat().st_size > 10000:
            print(f"Skipping {sc_id}_kf.jpg (already exists, {out_f.stat().st_size} bytes)", flush=True)
            continue

        print(f"Generating AI keyframe {sc_id}_kf.jpg...", flush=True)
        cmd = [
            GFLOW, "image", "t2i",
            item["prompt"],
            "--model", "nano-pro",
            "--aspect", "16:9",
            "-o", str(out_f)
        ]
        t0 = time.time()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        out_str = out.decode("utf-8", errors="replace")
        err_str = err.decode("utf-8", errors="replace")

        if p.returncode != 0:
            print(f"Error on {sc_id}: {err_str}", flush=True)
        else:
            print(f"Successfully generated {sc_id}_kf.jpg in {time.time() - t0:.1f}s!", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    main()
