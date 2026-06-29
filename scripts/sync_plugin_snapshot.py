#!/usr/bin/env python3
"""Refresh the Codex plugin skill snapshot from the repo-root skill."""

from __future__ import annotations

import shutil
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO / "plugins" / "presentation-skill"
PLUGIN_SKILL_ROOT = PLUGIN_ROOT / "skills" / "presentation-skill"
PLUGIN_ASSETS = PLUGIN_ROOT / "assets"

FILES = [
    "SKILL.md",
    "DESIGN.md",
    "README.md",
    "DISCOVERY.md",
    "LICENSE",
    "package.json",
]

DIRECTORIES = [
    "agents",
    "examples",
    "references",
    "scripts",
    "templates",
]

SCREENSHOTS = {
    "presentation_skill_variant_proof.png": REPO
    / "decks/native-vs-latest-random-topics-20260623/readme_images/presentation_skill_variant_proof.png",
    "presentation_skill_style_family_proof.png": REPO
    / "decks/native-vs-latest-random-topics-20260623/readme_images/presentation_skill_style_family_proof.png",
    "codex_native_vs_updated_clean_three_topics.png": REPO
    / "decks/native-vs-latest-random-topics-20260623/readme_images/codex_native_vs_updated_clean_three_topics.png",
}


def _ignore(_dir: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in {"__pycache__", ".pytest_cache", ".mypy_cache", "node_modules"}:
            ignored.add(name)
        elif name.endswith((".pyc", ".pyo", ".DS_Store")):
            ignored.add(name)
    return ignored


def _copy_file(relative_path: str) -> None:
    src = REPO / relative_path
    if not src.is_file():
        raise FileNotFoundError(src)
    dst = PLUGIN_SKILL_ROOT / relative_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree(relative_path: str) -> None:
    src = REPO / relative_path
    if not src.is_dir():
        raise FileNotFoundError(src)
    dst = PLUGIN_SKILL_ROOT / relative_path
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore)


def main() -> int:
    if PLUGIN_SKILL_ROOT.exists():
        shutil.rmtree(PLUGIN_SKILL_ROOT)
    PLUGIN_SKILL_ROOT.mkdir(parents=True, exist_ok=True)

    for relative_path in FILES:
        _copy_file(relative_path)
    for relative_path in DIRECTORIES:
        _copy_tree(relative_path)

    PLUGIN_ASSETS.mkdir(parents=True, exist_ok=True)
    for name, src in SCREENSHOTS.items():
        if not src.is_file():
            raise FileNotFoundError(src)
        shutil.copy2(src, PLUGIN_ASSETS / name)

    print(f"Synced plugin snapshot: {PLUGIN_SKILL_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
