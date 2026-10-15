"""Configuration for the Google Flow & MiniMax H3 Industrial AI Video Pipeline (L1-L5)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Output Directories
OUTPUT_DIR = BASE_DIR / "output"
RAW_CLIPS_DIR = OUTPUT_DIR / "raw_clips"
FINAL_EPISODES_DIR = OUTPUT_DIR / "final_episodes"

# Project Directories
CHARACTERS_FILE = BASE_DIR / "characters" / "profiles.toml"
EPISODES_DIR = BASE_DIR / "episodes"

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RAW_CLIPS_DIR.mkdir(parents=True, exist_ok=True)
FINAL_EPISODES_DIR.mkdir(parents=True, exist_ok=True)
EPISODES_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "characters").mkdir(parents=True, exist_ok=True)

# Google Flow Generation Defaults
DEFAULT_ASPECT = "16:9"              # "16:9" for cinematic landscape, "9:16" for short drama
DEFAULT_VIDEO_MODEL = "veo-quality"  # Options: "veo-quality", "veo-fast", "omni-flash", "veo-lite"
DEFAULT_IMAGE_MODEL = "nano-pro"     # Options: "nano-pro", "image4", "nano2"

# L2 Unified Global Style Locks (Era-Isolated between Modern and Ancient scenes)
GLOBAL_STYLE_LOCK = (
    "Shot on ARRI Alexa 65 with Panavision anamorphic lens, live-action cinematic historical drama realism "
    "blended with Rembrandt classical oil-painting chiaroscuro lighting, real human skin micro-texture, "
    "rich warm amber/tungsten highlights against deep slate shadows, fine Kodak Vision3 500T film grain, "
    "8k cinematic color grading."
)

MODERN_STYLE_LOCK = (
    "Shot on ARRI Alexa 65 with Panavision anamorphic lens, live-action cinematic realism "
    "blended with Rembrandt classical oil-painting chiaroscuro lighting, real human skin micro-texture, "
    "rich warm tungsten desk lamp highlights against deep slate shadows, fine Kodak Vision3 500T film grain, "
    "8k cinematic color grading. Clean video without any subtitles or text."
)

BASE_CINEMATIC_STYLE = GLOBAL_STYLE_LOCK

# Era-neutral negative prompt (does NOT ban modern clothes globally so modern setup scenes render cleanly)
NEGATIVE_PROMPT = (
    "cartoon, anime, 3d render, plastic skin, fantasy magic glow, neon lights, watermark, "
    "floating text, gibberish subtitles, deformed face, extra limbs"
)
