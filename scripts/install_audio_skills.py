#!/usr/bin/env python3
"""Install director creation skills into selected clients' user skill directories."""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("director-speech", "director-bgm", "director-story", "director-playground")


def payload(name):
    files = {
        Path("SKILL.md"): (REPO_ROOT / ".agents" / "skills" / name / "SKILL.md").read_bytes(),
    }
    if name == "director-playground":
        return files
    scripts = ("episode_audio.py", "clean_master.py", "native_av_master.py", "h3_performance.py") if name == "director-story" else ("director_audio.py",)
    files.update({Path("scripts") / script: (REPO_ROOT / "scripts" / script).read_bytes() for script in scripts})
    if name == "director-story":
        for reference in ("story-performance-method.md", "flow-omni12.md", "continuity-and-causality.md", "dramaturgy-and-shot-flow.md"):
            files[Path("references") / reference] = (REPO_ROOT / ".agents/skills/director-story/references" / reference).read_bytes()
    return files


def matches(target, files):
    return target.is_dir() and not target.is_symlink() and all(
        (target / path).is_file()
        and not (target / path).is_symlink()
        and (target / path).read_bytes() == data
        for path, data in files.items()
    )


def install(target, files):
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".director-install-", dir=target.parent))
    try:
        for path, data in files.items():
            destination = staging / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    home = Path.home()
    roots = {
        "codex": home / ".agents" / "skills",
        "antigravity": home / ".gemini" / "config" / "skills",
        "dsh": Path(os.environ.get("DSH_HOME") or home / ".dsh").expanduser() / "skills",
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, action="append", choices=roots)
    parser.add_argument("--skill", action="append", choices=SKILLS, help="Install selected skills (default: all).")
    parser.add_argument("--check", action="store_true", help="Verify installed files without copying.")
    args = parser.parse_args()

    selected = args.skill or SKILLS
    files_by_skill = {name: payload(name) for name in selected}
    targets = {
        roots[client] / name: files_by_skill[name]
        for client in args.client
        for name in selected
    }
    for target, files in targets.items():
        if (args.check or os.path.lexists(target)) and not matches(target, files):
            parser.exit(1, f"Skill files missing or different: {target}\n")
    for target, files in targets.items():
        if not target.exists():
            install(target, files)
        if not matches(target, files):
            parser.exit(1, f"Installed files failed verification: {target}\n")

    print(json.dumps({
        "verified": [str(target) for target in targets],
        "runner_sha256": hashlib.sha256((REPO_ROOT / "scripts/director_audio.py").read_bytes()).hexdigest(),
    }))


if __name__ == "__main__":
    main()
