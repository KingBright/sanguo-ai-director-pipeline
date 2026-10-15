"""Storyboard compiler: translates structured episode scenes into Google Flow / MiniMax H3 movie.toml.
Enforces L1-L5 Industrial Screenwriter & Director metadata fields (`era`, `arc_phase`, `acoustic_space`, `ref_image`, `camera_motion`).
"""
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import tomllib  # Python 3.11+ built-in
except ImportError:
    import tomli as tomllib

from .config import BASE_CINEMATIC_STYLE, MODERN_STYLE_LOCK, NEGATIVE_PROMPT, DEFAULT_ASPECT, CHARACTERS_FILE


class StoryboardCompiler:
    def __init__(self, characters_path: Path = CHARACTERS_FILE):
        self.characters_path = characters_path
        self.characters = self._load_characters()

    def _load_characters(self) -> List[Dict[str, Any]]:
        if not self.characters_path.exists():
            return []
        with open(self.characters_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("characters", [])

    def compile_to_toml(
        self,
        title: str,
        scenes: List[Dict[str, Any]],
        project_id: str = "FLOW_AUTO_PROJECT",
        output_dir: Optional[Path] = None,
        aspect: str = DEFAULT_ASPECT,
    ) -> str:
        """Compile scenes into a movie.toml string compatible with gflow movie run and H3Engine."""
        lines = [
            f"# Auto-generated L1-L5 Industrial AI Video Manifest: {title}",
            "schema_version = 1",
            f'title = "{title}"',
            f'project = "{project_id}"',
        ]
        if output_dir:
            safe_out = str(output_dir).replace("\\", "/")
            lines.append(f'output_dir = "{safe_out}"')

        lines.extend([
            "",
            "[style]",
            'look = "cinematic, 8k film grain, photorealistic, dramatic Rembrandt chiaroscuro lighting"',
            'palette = "rich earthy tones, warm tungsten highlights against deep slate shadows, Kodak Vision3 500T"',
            f'negative = "{NEGATIVE_PROMPT}"',
            f'suffix = "{BASE_CINEMATIC_STYLE}"',
            "",
            "  [style.variants.modern]",
            f'  suffix = "{MODERN_STYLE_LOCK}"',
            "",
            "  [style.variants.tense]",
            '  suffix = "Tense claustrophobic military council, heavy shadows, flickering torchlight."',
            "",
            "  [style.variants.epic]",
            '  suffix = "Vast sweeping landscape, misty Qinling mountains, sprawling ancient armies, cinematic grandeur."',
            "",
            "  [style.variants.intimate]",
            '  suffix = "Soft warm lantern light, emotional quiet character focus, shallow depth of field."',
        ])

        # Write character blocks
        for char in self.characters:
            lines.extend([
                "",
                "[[characters]]",
                f'name = "{char["name"]}"',
                f'appearance = "{char["appearance"]}"',
            ])
            if "appearance_modern" in char:
                lines.append(f'appearance_modern = "{char["appearance_modern"]}"')
            if "appearance_ancient" in char:
                lines.append(f'appearance_ancient = "{char["appearance_ancient"]}"')
            if "voice" in char:
                lines.append(f'voice = "{char["voice"]}"')
            if "ref_image_modern" in char:
                lines.append(f'ref_image_modern = "{char["ref_image_modern"]}"')
            if "ref_image_ancient" in char:
                lines.append(f'ref_image_ancient = "{char["ref_image_ancient"]}"')
            if "ref_image" in char:
                lines.append(f'ref_image = "{char["ref_image"]}"')

        # Write scene blocks with L1-L5 industrial fields
        for sc in scenes:
            selected_model = sc.get("selected_model", sc.get("model", "veo-quality"))
            era = sc.get("era", "modern" if any(k in sc["id"].lower() for k in ("modern", "dorm", "cosplay", "pack", "rain_exterior", "crash")) else "ancient")
            style_variant = sc.get("style_variant", "modern" if era == "modern" else "")
            lines.extend([
                "",
                "[[scenes]]",
                f'id = "{sc["id"]}"',
                f'era = "{era}"',
                f'action = "{sc["action"]}"',
                f'framing = "{sc.get("framing", "medium")}"',
                f'aspect = "{sc.get("aspect", aspect)}"',
                f'duration = {sc.get("duration", 8)}',
                f'model = "{selected_model}"',
                f'selected_model = "{selected_model}"',
                f'produced_by_model = "{sc.get("produced_by_model", selected_model)}"',
            ])
            if "room_id" in sc:
                lines.append(f'room_id = "{sc["room_id"]}"')
            if "arc_phase" in sc:
                lines.append(f'arc_phase = "{sc["arc_phase"]}"')
            if "acoustic_space" in sc:
                lines.append(f'acoustic_space = "{sc["acoustic_space"]}"')
            if "camera_motion" in sc:
                lines.append(f'camera_motion = "{sc["camera_motion"]}"')
            if "ref_image" in sc:
                lines.append(f'ref_image = "{sc["ref_image"]}"')
            if "characters" in sc and sc["characters"]:
                chars_str = ", ".join([f'"{c}"' for c in sc["characters"]])
                lines.append(f'characters = [{chars_str}]')
            if style_variant:
                lines.append(f'style_variant = "{style_variant}"')
            if "style_suffix" in sc:
                lines.append(f'style_suffix = "{sc["style_suffix"]}"')
            if "speaker" in sc:
                lines.append(f'speaker = "{sc["speaker"]}"')
            if "line" in sc:
                lines.append(f'line = "{sc["line"]}"')

        return "\n".join(lines) + "\n"

    def write_movie_file(
        self,
        output_file: Path,
        title: str,
        scenes: List[Dict[str, Any]],
        project_id: str = "FLOW_AUTO_PROJECT",
        output_dir: Optional[Path] = None,
        aspect: str = DEFAULT_ASPECT,
    ) -> Path:
        """Write the compiled movie.toml file to disk."""
        content = self.compile_to_toml(title, scenes, project_id, output_dir, aspect)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        return output_file
