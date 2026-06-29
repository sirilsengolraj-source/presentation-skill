#!/usr/bin/env python3
"""Build synthetic reference-gallery decks from the style catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except Exception:  # pragma: no cover - optional rendered/contact helper
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]

from office_package_hash import OFFICE_PACKAGE_HASH_ALGORITHM, office_package_normalized_sha256
from style_reference_catalog import (
    CONTENT_RECIPE_LIBRARY_VERSION,
    REQUIRED_CONTENT_RECIPE_FIELDS,
    REQUIRED_CONTENT_TREATMENTS,
    STYLE_METRIC_PROFILE_VERSION,
    STRUCTURAL_MOTIF_LIBRARY_VERSION,
    SUPPORTED_OUTLINE_VARIANTS,
    preset_style_reference,
)
from style_treatment_profiles import (
    RENDERER_TREATMENT_FIELDS,
    preset_treatment_profile,
    renderer_treatment_defaults_from_mix,
    renderer_treatment_summary,
)


ROOT = Path(__file__).resolve().parent.parent
GALLERY_VERSION = "style_reference_gallery_v1"
GALLERY_MAX_CONTENT_SLIDES = 10
RELEASE_EVIDENCE_VERSION = "style_reference_release_evidence_v1"
VISUAL_HASH_SIZE = (16, 9)
VISUAL_THUMB_SIGNATURE_SIZE = (32, 18)
VISUAL_DIVERSITY_MIN_NORMALIZED_DISTANCE = 0.10
VISUAL_SIMILARITY_WARN_NORMALIZED_DISTANCE = 0.18
TREATMENT_LAYOUT_UNIQUE_FLOORS = {
    "title": 8,
    "comparison": 8,
    "chart": 8,
    "table": 8,
    "figure": 8,
    "dashboard": 8,
    "decision": 8,
    "references": 8,
}
PRESET_CONTACT_COLLECTION_VERSION = "style_reference_preset_contact_collection_v1"
PRESET_CONTACT_COLLECTION_USE_CASES: dict[str, dict[str, Any]] = {
    "overview": {
        "label": "all treatment examples",
        "treatment_keys": list(REQUIRED_CONTENT_TREATMENTS),
        "columns": 4,
    },
    "data_evidence": {
        "label": "data, evidence, and proof layouts",
        "treatment_keys": ["chart", "table", "figure", "dashboard"],
        "columns": 2,
    },
    "decision_sources": {
        "label": "comparison, decision, and source handling",
        "treatment_keys": ["comparison", "decision", "references", "title"],
        "columns": 2,
    },
}

def _command_text(cmd: list[str]) -> str:
    return " ".join(str(part) for part in cmd)


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError("Command failed:\n" + _command_text(cmd) + "\n" + result.stdout)
    if result.stdout.strip():
        print(result.stdout.strip())
    return result.stdout


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _file_fingerprint(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists() or not path.is_file():
        return payload
    payload["size_bytes"] = path.stat().st_size
    payload["sha256"] = _file_sha256(path)
    return payload


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _pptx_fingerprint(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists() or not path.is_file():
        return payload
    try:
        payload["size_bytes"] = path.stat().st_size
        payload["sha256"] = _file_sha256(path)
        payload["normalized_sha256"] = office_package_normalized_sha256(path)
        payload["normalized_sha256_algorithm"] = OFFICE_PACKAGE_HASH_ALGORITHM
    except Exception as exc:
        payload["hash_error"] = str(exc)
    return payload


def _outline_summary(outline_path: Path) -> dict[str, Any]:
    payload = _load_json(outline_path)
    slides = payload.get("slides") if isinstance(payload, dict) else []
    if not isinstance(slides, list):
        slides = []
    deck_style = payload.get("deck_style") if isinstance(payload, dict) and isinstance(payload.get("deck_style"), dict) else {}
    variant_sequence: list[str] = []
    variant_counts: dict[str, int] = {}
    chart_treatments: list[str] = []
    table_treatments: list[str] = []
    slide_recipe_traces: list[dict[str, Any]] = []
    missing_recipe_trace_count = 0
    buckets: set[str] = set()
    for slide_index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        variant = str(slide.get("variant") or slide.get("type") or "content").strip().lower()
        if not variant:
            variant = "standard"
        variant_sequence.append(variant)
        variant_counts[variant] = variant_counts.get(variant, 0) + 1
        treatment_key = str(slide.get("treatment_key") or "").strip().lower()
        if treatment_key in REQUIRED_CONTENT_TREATMENTS and treatment_key != "title":
            buckets.add(treatment_key)
        else:
            role = str(slide.get("footer") or slide.get("slide_intent") or slide.get("role") or "").lower()
            if variant in {"stats", "kpi-hero"}:
                buckets.add("dashboard")
            if variant in {"comparison-2col", "split", "matrix"}:
                buckets.add("comparison")
            if variant == "chart":
                buckets.add("chart")
            if variant in {"table", "lab-run-results"}:
                buckets.add("table")
            if variant in {"scientific-figure", "image-sidebar", "flow", "generated-image"}:
                buckets.add("figure")
            if "decision" in role or variant == "standard":
                buckets.add("decision")
        if variant == "chart":
            treatment = str(slide.get("chart_treatment") or "").strip()
            if treatment:
                chart_treatments.append(treatment)
        if variant in {"table", "lab-run-results"}:
            treatment = str(slide.get("table_treatment") or "").strip()
            if treatment:
                table_treatments.append(treatment)
        if str(slide.get("type") or "content").strip().lower() != "title":
            content_recipe = (
                slide.get("content_recipe")
                if isinstance(slide.get("content_recipe"), dict)
                else {}
            )
            signature = str(content_recipe.get("recipe_signature") or "").strip()
            if not treatment_key or content_recipe.get("library_version") != CONTENT_RECIPE_LIBRARY_VERSION or not signature:
                missing_recipe_trace_count += 1
            slide_recipe_traces.append(
                {
                    "slide_index": slide_index,
                    "variant": variant,
                    "treatment_key": treatment_key,
                    "recipe_signature_hash": _text_sha256(signature) if signature else "",
                    "library_version": content_recipe.get("library_version"),
                }
            )
    return {
        "slide_count": len(slides),
        "content_slide_count": len([slide for slide in slides if isinstance(slide, dict) and str(slide.get("type") or "content").lower() != "title"]),
        "variant_sequence": variant_sequence,
        "variant_counts": dict(sorted(variant_counts.items())),
        "chart_treatment_sequence": chart_treatments,
        "table_treatment_sequence": table_treatments,
        "treatment_buckets": sorted(buckets),
        "renderer_treatments": renderer_treatment_summary(deck_style),
        "slide_recipe_trace_summary": {
            "trace_count": len(slide_recipe_traces),
            "missing_trace_count": missing_recipe_trace_count,
            "treatment_keys": sorted(
                {
                    str(item.get("treatment_key") or "")
                    for item in slide_recipe_traces
                    if str(item.get("treatment_key") or "").strip()
                }
            ),
            "traces": slide_recipe_traces,
            "passed": missing_recipe_trace_count == 0,
        },
    }


def _content_recipe_summary(reference: dict[str, Any]) -> dict[str, Any]:
    library = (
        reference.get("content_recipe_library")
        if isinstance(reference.get("content_recipe_library"), dict)
        else {}
    )
    recipes = library.get("recipes") if isinstance(library.get("recipes"), dict) else {}
    raw_signatures = (
        library.get("recipe_signatures")
        if isinstance(library.get("recipe_signatures"), dict)
        else {}
    )
    recipe_keys = [key for key in REQUIRED_CONTENT_TREATMENTS if key in recipes]
    missing_recipe_keys = [key for key in REQUIRED_CONTENT_TREATMENTS if key not in recipes]
    invalid_recipe_fields: dict[str, list[str]] = {}
    recipe_signature_hashes: dict[str, str] = {}
    slot_counts: dict[str, int] = {}
    data_role_counts: dict[str, int] = {}
    primary_variant_counts: dict[str, int] = {}

    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        recipe = recipes.get(treatment_key) if isinstance(recipes.get(treatment_key), dict) else {}
        missing_fields = [
            field
            for field in REQUIRED_CONTENT_RECIPE_FIELDS
            if field not in recipe or recipe.get(field) in (None, "", [])
        ]
        signature = str(raw_signatures.get(treatment_key) or recipe.get("recipe_signature") or "").strip()
        if not signature:
            missing_fields.append("recipe_signature")
        if missing_fields:
            invalid_recipe_fields[treatment_key] = sorted(set(missing_fields))
        recipe_signature_hashes[treatment_key] = _text_sha256(signature) if signature else ""
        slots = recipe.get("required_slots") if isinstance(recipe.get("required_slots"), list) else []
        data_roles = recipe.get("data_roles") if isinstance(recipe.get("data_roles"), list) else []
        variants = recipe.get("primary_variants") if isinstance(recipe.get("primary_variants"), list) else []
        slot_counts[treatment_key] = len([item for item in slots if str(item).strip()])
        data_role_counts[treatment_key] = len([item for item in data_roles if str(item).strip()])
        primary_variant_counts[treatment_key] = len([item for item in variants if str(item).strip()])

    library_signature_material = json.dumps(
        {key: recipe_signature_hashes.get(key, "") for key in REQUIRED_CONTENT_TREATMENTS},
        sort_keys=True,
        separators=(",", ":"),
    )
    version_ok = library.get("library_version") == CONTENT_RECIPE_LIBRARY_VERSION
    coverage_ok = not missing_recipe_keys and not invalid_recipe_fields
    return {
        "library_version": library.get("library_version"),
        "expected_library_version": CONTENT_RECIPE_LIBRARY_VERSION,
        "style_preset": library.get("style_preset") or reference.get("style_preset"),
        "reference_id": library.get("reference_id") or reference.get("reference_id"),
        "recipe_count": len(recipe_keys),
        "required_recipe_count": len(REQUIRED_CONTENT_TREATMENTS),
        "recipe_keys": recipe_keys,
        "missing_recipe_keys": missing_recipe_keys,
        "invalid_recipe_fields": invalid_recipe_fields,
        "recipe_signature_hashes": recipe_signature_hashes,
        "library_signature": _text_sha256(library_signature_material),
        "slot_counts": slot_counts,
        "data_role_counts": data_role_counts,
        "primary_variant_counts": primary_variant_counts,
        "passed": bool(version_ok and coverage_ok),
    }


def _content_recipe_trace(reference: dict[str, Any], treatment_key: str) -> dict[str, Any]:
    key = str(treatment_key or "").strip().lower()
    library = (
        reference.get("content_recipe_library")
        if isinstance(reference.get("content_recipe_library"), dict)
        else {}
    )
    recipes = library.get("recipes") if isinstance(library.get("recipes"), dict) else {}
    recipe = recipes.get(key) if isinstance(recipes.get(key), dict) else {}
    signatures = (
        library.get("recipe_signatures")
        if isinstance(library.get("recipe_signatures"), dict)
        else {}
    )
    signature = str(signatures.get(key) or recipe.get("recipe_signature") or "").strip()
    archetype = recipe.get("treatment_archetype") if isinstance(recipe.get("treatment_archetype"), dict) else {}
    return {
        "library_version": library.get("library_version"),
        "recipe_signature": signature,
        "recipe_signature_hash": _text_sha256(signature) if signature else "",
        "treatment_archetype_id": archetype.get("archetype_id"),
        "treatment_archetype_signature": archetype.get("archetype_signature"),
        "primary_variants": [
            str(item)
            for item in recipe.get("primary_variants", [])
            if str(item).strip()
        ]
        if isinstance(recipe.get("primary_variants"), list)
        else [],
        "required_slots": [
            str(item)
            for item in recipe.get("required_slots", [])
            if str(item).strip()
        ]
        if isinstance(recipe.get("required_slots"), list)
        else [],
        "data_roles": [
            str(item)
            for item in recipe.get("data_roles", [])
            if str(item).strip()
        ]
        if isinstance(recipe.get("data_roles"), list)
        else [],
    }


def _treatment_primary_variants(reference: dict[str, Any], treatment_key: str) -> list[str]:
    key = str(treatment_key or "").strip().lower()
    variants: list[str] = []
    library = (
        reference.get("content_recipe_library")
        if isinstance(reference.get("content_recipe_library"), dict)
        else {}
    )
    recipes = library.get("recipes") if isinstance(library.get("recipes"), dict) else {}
    recipe = recipes.get(key) if isinstance(recipes.get(key), dict) else {}
    if isinstance(recipe.get("primary_variants"), list):
        variants.extend(str(item).strip().lower() for item in recipe["primary_variants"] if str(item).strip())
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    treatment_map = playbook.get("treatment_variant_map") if isinstance(playbook.get("treatment_variant_map"), dict) else {}
    mapped = treatment_map.get(key)
    if isinstance(mapped, list):
        variants.extend(str(item).strip().lower() for item in mapped if str(item).strip())
    unique: list[str] = []
    for variant in variants:
        if variant in SUPPORTED_OUTLINE_VARIANTS and variant not in unique:
            unique.append(variant)
    return unique


def _treatment_key_for_gallery_slide(slide: dict[str, Any], reference: dict[str, Any]) -> str:
    explicit = str(slide.get("treatment_key") or "").strip().lower()
    if explicit in REQUIRED_CONTENT_TREATMENTS:
        return explicit
    footer = str(slide.get("footer") or "").strip().lower()
    role = footer.rsplit("/", 1)[-1].strip() if "/" in footer else footer
    role_map = {
        "architecture": "figure",
        "chart": "chart",
        "comparison": "comparison",
        "dashboard": "dashboard",
        "decision": "decision",
        "figure": "figure",
        "matrix": "comparison",
        "plan": "decision",
        "proof": "decision",
        "refs": "references",
        "table": "table",
    }
    if role in role_map:
        return role_map[role]
    variant = str(slide.get("variant") or slide.get("type") or "").strip().lower()
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    treatment_map = playbook.get("treatment_variant_map") if isinstance(playbook.get("treatment_variant_map"), dict) else {}
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        mapped = treatment_map.get(treatment_key)
        if isinstance(mapped, list) and variant in {str(item).strip().lower() for item in mapped}:
            return treatment_key
    if variant in {"stats", "kpi-hero"}:
        return "dashboard"
    if variant in {"comparison-2col", "split", "matrix"}:
        return "comparison"
    if variant == "chart":
        return "chart"
    if variant in {"table", "lab-run-results"}:
        return "table"
    if variant in {"scientific-figure", "image-sidebar", "flow", "generated-image"}:
        return "figure"
    if variant == "title":
        return "title"
    return "decision"


def _annotate_gallery_slide_recipes(slides: list[dict[str, Any]], reference: dict[str, Any]) -> list[dict[str, Any]]:
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        treatment_key = _treatment_key_for_gallery_slide(slide, reference)
        if not treatment_key:
            continue
        slide["treatment_key"] = treatment_key
        slide["content_recipe"] = _content_recipe_trace(reference, treatment_key)
    return slides


def _qa_summary(qa_report: Path) -> dict[str, Any]:
    payload = _load_json(qa_report)
    if not isinstance(payload, dict):
        return {"path": str(qa_report), "exists": qa_report.exists()}
    keys = [
        "overflow_count",
        "overlap_count",
        "geometry_error_count",
        "geometry_warning_count",
        "whitespace_warning_count",
        "visual_warning_count",
        "design_error_count",
        "design_warning_count",
        "rendered_slide_count",
        "expected_slide_count",
    ]
    summary = {"path": str(qa_report), "exists": qa_report.exists()}
    for key in keys:
        if key in payload:
            summary[key] = payload.get(key)
    placeholders = payload.get("placeholder_hits")
    if isinstance(placeholders, list):
        summary["placeholder_count"] = len(placeholders)
    summary["blocking_issue_count"] = sum(
        int(summary.get(key) or 0)
        for key in (
            "overflow_count",
            "overlap_count",
            "geometry_error_count",
            "design_error_count",
            "placeholder_count",
        )
    )
    summary["warning_issue_count"] = sum(
        int(summary.get(key) or 0)
        for key in (
            "geometry_warning_count",
            "whitespace_warning_count",
            "visual_warning_count",
            "design_warning_count",
        )
    )
    summary["passed_render_free_gate"] = all(
        int(summary.get(key) or 0) == 0
        for key in (
            "overflow_count",
            "overlap_count",
            "geometry_error_count",
            "design_error_count",
            "design_warning_count",
            "placeholder_count",
        )
    )
    return summary


def _preset_names() -> list[str]:
    script = (
        "const {listPresets}=require('./templates/pptxgenjs/presets.js'); "
        "console.log(JSON.stringify(listPresets()));"
    )
    result = subprocess.run(["node", "-e", script], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return [str(name) for name in json.loads(result.stdout)]


def _preset_tokens(preset: str) -> dict[str, str]:
    script = (
        "const {getPreset}=require('./templates/pptxgenjs/presets.js'); "
        f"console.log(JSON.stringify(getPreset({json.dumps(preset)})));"
    )
    result = subprocess.run(["node", "-e", script], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    raw = json.loads(result.stdout)
    return {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}


def _deck_style_for(preset: str, profile: dict[str, Any]) -> dict[str, Any]:
    mix = profile.get("style_mix_matrix") if isinstance(profile.get("style_mix_matrix"), dict) else {}
    header_pool = [str(item) for item in mix.get("header_variant_pool", []) if str(item).strip()]
    defaults = (
        profile.get("renderer_treatment_defaults")
        if isinstance(profile.get("renderer_treatment_defaults"), dict)
        else renderer_treatment_defaults_from_mix(preset, mix)
    )
    footer = str(defaults.get("footer_mode") or "standard").strip() or "standard"
    return {
        "style_seed": f"{preset}-reference-gallery",
        "header_mode": "lab-clean",
        "header_variant": "auto",
        "header_variants": header_pool[:4] or ["left-accent", "split-rule", "title-rule", "plain"],
        "title_layout": str(defaults.get("title_layout") or "split-hero").strip() or "split-hero",
        "footer_mode": footer,
        "footer_page_numbers": footer == "source-line",
        "footer_source_label": "Src",
        "footer_refs_label": "Refs",
        "chart_treatment": str(defaults.get("chart_treatment") or "standard").strip() or "standard",
        "table_treatment": str(defaults.get("table_treatment") or "standard").strip() or "standard",
        "figure_table_treatment": str(defaults.get("figure_table_treatment") or "figure-first").strip()
        or "figure-first",
        "stats_mode": str(defaults.get("stats_mode") or "tiles").strip() or "tiles",
        "matrix_mode": str(defaults.get("matrix_mode") or "cards").strip() or "cards",
        "summary_callout_mode": str(defaults.get("summary_callout_mode") or "default").strip() or "default",
    }


def _hex_to_rgb(value: str, fallback: str = "1D4ED8") -> tuple[int, int, int]:
    raw = str(value or fallback).replace("#", "").strip()
    if len(raw) != 6:
        raw = fallback
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except ValueError:
        return (29, 78, 216)


def _write_synthetic_figures(asset_dir: Path, preset: str, tokens: dict[str, str]) -> list[str]:
    asset_dir.mkdir(parents=True, exist_ok=True)
    if Image is None or ImageDraw is None:
        return []
    accent = _hex_to_rgb(tokens.get("accent_primary", "1D4ED8"))
    secondary = _hex_to_rgb(tokens.get("accent_secondary", "0891B2"))
    dark = _hex_to_rgb(tokens.get("bg_dark", "0F172A"))
    line = _hex_to_rgb(tokens.get("line", "CBD5E1"))
    surface = _hex_to_rgb(tokens.get("surface", "FFFFFF"))
    text = _hex_to_rgb(tokens.get("text", "111827"))
    font = ImageFont.load_default() if ImageFont else None
    paths: list[str] = []
    for idx in range(1, 4):
        path = asset_dir / f"{preset}-synthetic-panel-{idx}.png"
        img = Image.new("RGB", (1280, 720), surface)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 1279, 719], outline=line, width=3)
        draw.rectangle([0, 0, 1279, 20], fill=dark if idx == 1 else accent)
        draw.text((42, 40), f"Synthetic panel {idx}", fill=text, font=font)
        if idx == 1:
            for x in range(80, 1200, 110):
                draw.line([(x, 600), (x + 52, 120 + (x % 260))], fill=line, width=2)
            points = [(90, 520), (260, 430), (430, 455), (600, 300), (770, 330), (940, 205), (1110, 240)]
            draw.line(points, fill=accent, width=8, joint="curve")
            for x, y in points:
                draw.ellipse([x - 13, y - 13, x + 13, y + 13], fill=secondary, outline=surface, width=3)
        elif idx == 2:
            labels = ["A", "B", "C", "D"]
            values = [410, 275, 500, 335]
            for i, value in enumerate(values):
                x0 = 120 + i * 250
                draw.rectangle([x0, 610 - value, x0 + 120, 610], fill=accent if i != 1 else secondary)
                draw.text((x0 + 44, 628), labels[i], fill=text, font=font)
            draw.line([(90, 610), (1170, 610)], fill=line, width=3)
            draw.line([(90, 90), (90, 610)], fill=line, width=3)
        else:
            for i in range(4):
                x0 = 110 + i * 285
                y0 = 150 + (i % 2) * 95
                draw.rounded_rectangle([x0, y0, x0 + 190, y0 + 120], radius=12, outline=line, width=3)
                draw.rectangle([x0, y0, x0 + 190, y0 + 14], fill=accent if i % 2 == 0 else secondary)
                draw.text((x0 + 22, y0 + 42), f"State {i + 1}", fill=text, font=font)
            draw.line([(300, 210), (395, 210)], fill=dark, width=5)
            draw.line([(585, 305), (680, 305)], fill=dark, width=5)
            draw.line([(870, 210), (965, 210)], fill=dark, width=5)
        img.save(path)
        paths.append(str(path))
    return paths


def _compact_footer_item(value: Any, *, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 3)].rstrip(" -;:,")
    return f"{clipped}..." if clipped else text[:limit]


def _compact_reference_slug(value: Any, *, limit: int = 15) -> str:
    text = str(value or "style-reference").strip() or "style-reference"
    if text.startswith("ref-"):
        text = text[4:]
    if len(text) <= limit:
        return text
    parts = [part for part in text.split("-") if part]
    if len(parts) >= 2:
        candidate = f"{parts[0]}-{parts[-1]}"
        if len(candidate) <= limit:
            return candidate
    return _compact_footer_item(text, limit=limit)


def _base_slide(preset: str, role: str, reference: dict[str, Any]) -> dict[str, Any]:
    storyboard = _storyboard(reference)
    source_notes = storyboard.get("source_notes") if isinstance(storyboard.get("source_notes"), list) else []
    sources = [
        _compact_footer_item(item, limit=22)
        for item in source_notes
        if str(item).strip()
    ][:1] or ["Synthetic fixture"]
    return {
        "footer": f"{preset} / {role}",
        "sources": sources,
        "refs": [_compact_reference_slug(reference.get("reference_id"))],
    }


def _treatment_archetype(reference: dict[str, Any], treatment_key: str) -> dict[str, Any]:
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    archetypes = playbook.get("treatment_archetypes") if isinstance(playbook.get("treatment_archetypes"), dict) else {}
    archetype = archetypes.get(treatment_key) if isinstance(archetypes.get(treatment_key), dict) else {}
    return archetype


def _archetype_kicker(archetype: dict[str, Any], fallback: str) -> str:
    raw = str(archetype.get("archetype_id") or fallback).strip()
    label = raw.replace("-", " ").upper()
    return label[:32] or fallback


def _storyboard(reference: dict[str, Any]) -> dict[str, Any]:
    story = reference.get("example_storyboard") if isinstance(reference.get("example_storyboard"), dict) else {}
    return story


def _story_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _story_table(reference: dict[str, Any]) -> dict[str, Any]:
    story = _storyboard(reference)
    table = story.get("table") if isinstance(story.get("table"), dict) else {}
    if table:
        return table
    return {"headers": ["Role", "Signal", "Use"], "rows": _table_rows(reference)}


def _story_decision(reference: dict[str, Any]) -> dict[str, Any]:
    story = _storyboard(reference)
    decision = story.get("decision") if isinstance(story.get("decision"), dict) else {}
    if decision:
        return decision
    return {
        "headers": ["Field", "Reference rule", "Check"],
        "rows": [
            ["Action", reference["content_treatments"]["decision"], "Owner visible"],
            ["Sources", reference["content_treatments"]["references"], "Footer or table"],
        ],
    }


def _chart_payload(reference: dict[str, Any]) -> dict[str, Any]:
    story = _storyboard(reference)
    chart = story.get("chart") if isinstance(story.get("chart"), dict) else {}
    labels = [str(item) for item in _story_list(chart.get("labels")) if str(item).strip()]
    values = [
        value
        for value in _story_list(chart.get("values"))
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if not labels or len(labels) != len(values):
        labels = ["Structure", "Evidence", "Readability", "Replay"]
        values = [82, 91, 86, 94]
    facts = story.get("dashboard_facts") if isinstance(story.get("dashboard_facts"), list) else []
    return {
        "type": "bar",
        "title": str(chart.get("title") or "Reference treatment fit"),
        "labels": labels,
        "values": values,
        "notes": str(chart.get("note") or reference["content_treatments"]["chart"]),
        "facts": facts[:3] if facts else [
            {"value": "8", "label": "treatments", "detail": "title through refs"},
            {"value": "0", "label": "copied assets", "detail": "synthetic content"},
            {"value": "13", "label": "preset families", "detail": "distinct DNA"},
        ],
        "options": {
            "catAxisLabelFontSize": 8,
            "valAxisLabelFontSize": 8,
            "showLegend": False,
        },
        "sources": ["style_reference_catalog.py"],
    }


def _stats_for(reference: dict[str, Any]) -> list[dict[str, str]]:
    story = _storyboard(reference)
    facts = story.get("dashboard_facts") if isinstance(story.get("dashboard_facts"), list) else []
    normalized = [
        {
            "value": str(item.get("value") or ""),
            "label": str(item.get("label") or ""),
            "detail": str(item.get("detail") or ""),
        }
        for item in facts
        if isinstance(item, dict)
    ]
    return normalized[:3] or [
        {"value": "8", "label": "Treatments", "detail": "full slide grammar"},
        {"value": "1", "label": "Replay seed", "detail": "same rhythm rebuilds"},
    ]


def _table_rows(reference: dict[str, Any]) -> list[list[str]]:
    treatments = reference["content_treatments"]
    return [
        ["Title", treatments["title"], "Open"],
        ["Chart", treatments["chart"], "Evidence"],
        ["Table", treatments["table"], "Data"],
        ["Figure", treatments["figure"], "Proof"],
        ["Decision", treatments["decision"], "Action"],
    ]


def _figure_slide(
    preset: str,
    reference: dict[str, Any],
    deck_style: dict[str, Any],
    asset_paths: list[str],
    *,
    variant: str | None = None,
) -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    figure = story.get("figure") if isinstance(story.get("figure"), dict) else {}
    sections = _story_list(figure.get("sections"))
    sidebar_sections = [
        {
            "title": str(item.get("title") or "Readout"),
            "body": [str(line) for line in _story_list(item.get("body")) if str(line).strip()][:3],
        }
        for item in sections
        if isinstance(item, dict)
    ]
    if not sidebar_sections:
        sidebar_sections = [
            {"title": "Proof object", "body": ["One generated figure owns the slide.", "Sidebar carries the implication."]},
            {"title": "Replay path", "body": ["Asset path and caption stay in source JSON."]},
        ]
    caption = str(figure.get("caption") or "Synthetic figure generated by build_style_reference_gallery.py.")
    interpretation = str(figure.get("interpretation") or "The figure slot demonstrates proof objects, captions, and source posture.")
    requested = (variant or "").strip().lower()
    if requested not in {"scientific-figure", "image-sidebar", "flow"}:
        requested = "image-sidebar" if deck_style["figure_table_treatment"] == "image-sidebar" else "scientific-figure"
    treatment = str(deck_style.get("figure_table_treatment") or "figure-first").strip().lower()
    figure_layout = {
        "table-first": "ledger-rail",
        "stats-strip": "strip-readout",
    }.get(treatment, "panel-grid")
    if preset in {"executive-clinical", "forest-research"} and treatment == "figure-first":
        figure_layout = "primary-rail"
    if requested == "flow":
        return {
            **_base_slide(preset, "architecture", reference),
            "type": "content",
            "variant": "flow",
            "title": f"System route: {story.get('topic') or 'synthetic workflow'}",
            "subtitle": treatments["figure"],
            "assets": {"diagram": asset_paths[2]} if len(asset_paths) >= 3 else {},
            "sidebar_sections": sidebar_sections[:2],
            "summary_callout": interpretation,
        }
    if requested == "image-sidebar" or not asset_paths:
        return {
            **_base_slide(preset, "figure", reference),
            "type": "content",
            "variant": "image-sidebar",
            "title": f"Figure anchor: {story.get('topic') or 'synthetic proof'}",
            "subtitle": treatments["figure"],
            "assets": {"hero_image": asset_paths[0]} if asset_paths else {},
            "sections": sidebar_sections[:2],
            "caption": caption,
        }
    return {
        **_base_slide(preset, "figure", reference),
        "type": "content",
        "variant": "scientific-figure",
        "title": f"Figure panels: {story.get('topic') or 'synthetic proof'}",
        "subtitle": treatments["figure"],
        "figure_layout": figure_layout,
        "figures": [
            {"path": asset_paths[0], "label": "A", "title": "Signal trend", "caption": caption},
            {"path": asset_paths[1], "label": "B", "title": "Comparison readout", "caption": "Generated fixture."},
            {"path": asset_paths[2], "label": "C", "title": "State model", "caption": "No external asset."},
        ],
        "caption": caption,
        "interpretation": interpretation,
    }


def _dashboard_slide(
    preset: str,
    reference: dict[str, Any],
    deck_style: dict[str, Any],
    asset_paths: list[str] | None = None,
    *,
    requested_variant: str = "",
) -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    supported = {
        "stats",
        "kpi-hero",
        "chart",
        "table",
        "lab-run-results",
        "matrix",
        "flow",
        "split",
        "standard",
    }
    primary_variants = [variant for variant in _treatment_primary_variants(reference, "dashboard") if variant in supported]
    requested = str(requested_variant or "").strip().lower()
    variant = primary_variants[0] if primary_variants else ""
    if requested in primary_variants and requested not in {"stats", "standard"}:
        variant = requested
    if not variant:
        variant = requested if requested in supported else "stats"

    if variant == "kpi-hero":
        slide = _kpi_slide(preset, reference)
        slide["treatment_key"] = "dashboard"
        return slide

    if variant == "chart":
        chart = _chart_payload(reference)
        chart["title"] = f"Dashboard state: {chart.get('title') or story.get('topic') or 'operating readout'}"
        return {
            **_base_slide(preset, "dashboard", reference),
            "type": "content",
            "variant": "chart",
            "treatment_key": "dashboard",
            "title": f"Dashboard: {story.get('topic') or 'operating readout'}",
            "subtitle": treatments["dashboard"],
            "chart_treatment": deck_style["chart_treatment"],
            "chart": chart,
        }

    if variant in {"table", "lab-run-results"}:
        fact_rows = [
            [str(item.get("label") or ""), str(item.get("value") or ""), str(item.get("detail") or "")]
            for item in _stats_for(reference)
        ]
        if len(fact_rows) < 3:
            fact_rows.append(["Action", "Next", "Owner named"])
        return {
            **_base_slide(preset, "dashboard", reference),
            "type": "content",
            "variant": "lab-run-results" if variant == "lab-run-results" else "table",
            "treatment_key": "dashboard",
            "title": f"Dashboard: {story.get('topic') or 'operating readout'}",
            "subtitle": treatments["dashboard"],
            "table_treatment": deck_style.get("table_treatment", "standard"),
            "headers": ["State", "Value", "Context"],
            "rows": fact_rows[:4],
            "column_weights": [0.8, 0.55, 1.25],
            "caption": "Synthetic dashboard ledger: metric labels, values, and context remain editable.",
            "interpretation": "Table-first dashboards are used when the decision depends on context, owner, or state.",
        }

    if variant == "matrix":
        facts = _stats_for(reference)
        quadrants = [
            {
                "title": str(item.get("label") or f"State {idx + 1}"),
                "body": f"{item.get('value')}: {item.get('detail') or 'state needs context'}",
            }
            for idx, item in enumerate(facts[:3])
        ]
        quadrants.append({"title": "Action", "body": "Name owner, blocker, and next check."})
        return {
            **_base_slide(preset, "dashboard", reference),
            "type": "content",
            "variant": "matrix",
            "treatment_key": "dashboard",
            "title": f"Dashboard: {story.get('topic') or 'state board'}",
            "subtitle": treatments["dashboard"],
            "quadrants": quadrants[:4],
        }

    if variant == "split":
        facts = _stats_for(reference)
        bullets = [
            f"{item.get('value')} {item.get('label')}: {item.get('detail')}"
            for item in facts
            if str(item.get("value") or "").strip() and str(item.get("label") or "").strip()
        ]
        return {
            **_base_slide(preset, "dashboard", reference),
            "type": "content",
            "variant": "split",
            "treatment_key": "dashboard",
            "title": f"Signal board: {story.get('topic') or 'sparse readout'}",
            "subtitle": treatments["dashboard"],
            "bullets": bullets[:3] or ["Primary signal visible", "Argument stays singular", "Review point named"],
            "highlights_label": "Thesis",
            "highlights": [
                str(story.get("title") or story.get("topic") or "One argument per page"),
                "Sparse facts support the editorial line.",
                "No dashboard wall.",
            ],
        }

    if variant == "flow":
        facts = _stats_for(reference)
        return {
            **_base_slide(preset, "dashboard", reference),
            "type": "content",
            "variant": "flow",
            "treatment_key": "dashboard",
            "title": f"Dashboard route: {story.get('topic') or 'state board'}",
            "subtitle": treatments["dashboard"],
            "assets": {"diagram": asset_paths[2]} if asset_paths and len(asset_paths) >= 3 else {},
            "sidebar_sections": [
                {
                    "title": str(item.get("label") or f"Signal {idx + 1}"),
                    "body": [f"{item.get('value')}: {item.get('detail') or 'state context'}"],
                }
                for idx, item in enumerate(facts[:2])
            ],
            "summary_callout": "Console dashboards show route, state, and next action rather than a generic tile wall.",
        }

    if variant == "standard":
        facts = _stats_for(reference)
        bullets = [
            f"{item.get('value')} {item.get('label')}: {item.get('detail')}"
            for item in facts
            if str(item.get("value") or "").strip() and str(item.get("label") or "").strip()
        ]
        return {
            **_base_slide(preset, "dashboard", reference),
            "type": "content",
            "variant": "standard",
            "treatment_key": "dashboard",
            "title": f"Dashboard: {story.get('topic') or 'sparse readout'}",
            "subtitle": treatments["dashboard"],
            "body": "Sparse dashboard treatment: one argument, a few inspectable facts, and no metric wall.",
            "bullets": bullets[:3] or ["Primary metric visible", "Context stays close", "Owner or implication named"],
        }

    return {
        **_base_slide(preset, "dashboard", reference),
        "type": "content",
        "variant": "stats",
        "treatment_key": "dashboard",
        "title": f"Dashboard: {story.get('topic') or 'operating readout'}",
        "subtitle": treatments["dashboard"],
        "facts": _stats_for(reference),
    }


def _kpi_slide(preset: str, reference: dict[str, Any]) -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    kpi = story.get("kpi") if isinstance(story.get("kpi"), dict) else {}
    return {
        **_base_slide(preset, "dashboard", reference),
        "type": "content",
        "variant": "kpi-hero",
        "title": f"Hero metric: {story.get('topic') or 'synthetic proof'}",
        "subtitle": treatments["dashboard"],
        "value": str(kpi.get("value") or "8"),
        "label": str(kpi.get("label") or "reference moves"),
        "context": str(kpi.get("context") or "Use a KPI hero only when one metric, date, or threshold carries the argument."),
    }


def _cards_slide(preset: str, reference: dict[str, Any], *, variant: str = "cards-3") -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    table = _story_table(reference)
    table_rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    cards = [
        {"title": str(story.get("topic") or "Claim"), "body": str(treatments["title"]), "accent": "accent_primary"},
        {
            "title": "Proof",
            "body": str((table_rows[0][1] if table_rows and isinstance(table_rows[0], list) and len(table_rows[0]) > 1 else treatments["chart"])),
            "accent": "accent_secondary",
        },
        {"title": "Decision", "body": str(treatments["decision"]), "accent": "accent_primary"},
    ]
    slide = {
        **_base_slide(preset, "proof", reference),
        "type": "content",
        "variant": "cards-2" if variant == "cards-2" else "cards-3",
        "title": f"Proof blocks: {story.get('topic') or 'synthetic storyboard'}",
        "subtitle": "Use cards only when parallel choices are the content, not as default filler.",
        "cards": cards[:2] if variant == "cards-2" else cards,
    }
    if variant == "cards-3":
        slide["promote_card"] = 0
    return slide


def _comparison_slide(preset: str, reference: dict[str, Any], *, variant: str = "comparison-2col") -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    comparison = story.get("comparison") if isinstance(story.get("comparison"), dict) else {}
    if variant == "split":
        return {
            **_base_slide(preset, "comparison", reference),
            "type": "content",
            "variant": "split",
            "title": f"Structured contrast: {story.get('topic') or 'reference choice'}",
            "subtitle": treatments["comparison"],
            "bullets": [str(item) for item in _story_list(comparison.get("left_body"))[:2] + _story_list(comparison.get("right_body"))[:2]],
            "highlights_label": str(comparison.get("right_title") or "Reference move"),
            "highlights": [str(comparison.get("verdict") or "Choose proof type early"), "Lock variants", "Record source posture"],
        }
    return {
        **_base_slide(preset, "comparison", reference),
        "type": "content",
        "variant": "comparison-2col",
        "title": f"Comparison: {story.get('topic') or 'two useful states'}",
        "subtitle": treatments["comparison"],
        "left": {
            "title": str(comparison.get("left_title") or "Generic slide chrome"),
            "body": [str(item) for item in _story_list(comparison.get("left_body"))] or ["Shared title bar", "Layout chosen late"],
        },
        "right": {
            "title": str(comparison.get("right_title") or "Reference-led structure"),
            "body": [str(item) for item in _story_list(comparison.get("right_body"))] or ["Preset-specific grammar", "Evidence object first"],
        },
        "verdict": str(comparison.get("verdict") or "Reference first; outline second."),
    }


def _comparison_slide_for_reference(preset: str, reference: dict[str, Any]) -> dict[str, Any]:
    primary_variants = [
        variant
        for variant in _treatment_primary_variants(reference, "comparison")
        if variant in {"comparison-2col", "split", "matrix"}
    ]
    variant = primary_variants[0] if primary_variants else "comparison-2col"
    if variant == "matrix":
        return _matrix_slide(preset, reference)
    return _comparison_slide(preset, reference, variant=variant)


def _chart_slide(preset: str, reference: dict[str, Any], deck_style: dict[str, Any]) -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    chart = story.get("chart") if isinstance(story.get("chart"), dict) else {}
    return {
        **_base_slide(preset, "chart", reference),
        "type": "content",
        "variant": "chart",
        "title": f"Chart: {chart.get('title') or story.get('topic') or 'readable proof'}",
        "subtitle": treatments["chart"],
        "chart_treatment": deck_style["chart_treatment"],
        "chart": _chart_payload(reference),
    }


def _reference_rows(reference: dict[str, Any]) -> list[list[str]]:
    treatments = reference["content_treatments"]
    reference_archetype = _treatment_archetype(reference, "references")
    story = _storyboard(reference)
    notes = [str(item) for item in story.get("source_notes", []) if str(item).strip()]
    rows = [
        [
            f"S{idx + 1}",
            note,
            str(reference_archetype.get("structure") or treatments["references"]),
        ]
        for idx, note in enumerate(notes[:4])
    ]
    if rows:
        return rows
    return [
        ["S1", "Synthetic reference fixture", str(reference_archetype.get("structure") or treatments["references"])],
        ["S2", str(reference.get("reference_id") or "style reference"), "Catalog route"],
    ]


def _references_table_slide(
    preset: str,
    reference: dict[str, Any],
    deck_style: dict[str, Any],
) -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    reference_archetype = _treatment_archetype(reference, "references")
    return {
        **_base_slide(preset, "refs", reference),
        "type": "content",
        "variant": "table",
        "treatment_key": "references",
        "reference_archetype": reference_archetype,
        "title": f"References: {story.get('topic') or 'source posture'}",
        "subtitle": treatments["references"],
        "table_style": "references",
        "table_treatment": deck_style.get("table_treatment", "standard"),
        "headers": ["ID", "Source / basis", "Use in deck"],
        "rows": _reference_rows(reference),
        "column_weights": [0.32, 1.15, 1.25],
        "caption": "Synthetic reference gallery: sources are descriptors, not bundled third-party slides.",
    }


def _references_slide(
    preset: str,
    reference: dict[str, Any],
    deck_style: dict[str, Any],
    *,
    requested_variant: str = "",
) -> dict[str, Any]:
    treatments = reference["content_treatments"]
    story = _storyboard(reference)
    reference_archetype = _treatment_archetype(reference, "references")
    supported = {"table", "standard", "split", "matrix"}
    primary_variants = [variant for variant in _treatment_primary_variants(reference, "references") if variant in supported]
    requested = str(requested_variant or "").strip().lower()
    variant = primary_variants[0] if primary_variants else ""
    if requested in primary_variants and requested != "table":
        variant = requested
    if not variant:
        variant = requested if requested in supported else "table"
    if variant == "table":
        return _references_table_slide(preset, reference, deck_style)

    rows = _reference_rows(reference)
    labels = [row[0] for row in rows[:3]]
    notes = [row[1] for row in rows[:3]]
    source_lines = [f"{label}: {note}" for label, note in zip(labels, notes)]
    structure = str(reference_archetype.get("structure") or treatments["references"])
    if variant == "split":
        split_bullets = source_lines[:3]
        if len(split_bullets) < 3:
            split_bullets.append(f"Use: {_compact_footer_item(structure, limit=58)}")
        return {
            **_base_slide(preset, "refs", reference),
            "type": "content",
            "variant": "split",
            "treatment_key": "references",
            "reference_archetype": reference_archetype,
            "title": f"Source posture: {story.get('topic') or 'reference route'}",
            "subtitle": treatments["references"],
            "bullets": split_bullets or [
                "Short source IDs stay in the footer.",
                "Long notes move into an appendix table.",
                "Use a source table only when proof burden rises.",
            ],
            "highlights_label": "Provenance rule",
            "highlights": [
                _compact_footer_item(structure, limit=70),
                "No bundled third-party slides",
                "Synthetic descriptors only",
            ],
        }
    if variant == "matrix":
        quadrants = [
            {
                "title": rows[0][0] if len(rows) > 0 else "S1",
                "body": _compact_footer_item(rows[0][1] if len(rows) > 0 else "Synthetic source route.", limit=44),
            },
            {
                "title": rows[1][0] if len(rows) > 1 else "Use",
                "body": _compact_footer_item(
                    rows[1][1] if len(rows) > 1 else structure,
                    limit=44,
                ),
            },
            {"title": "Allowed", "body": "Descriptors, URLs, synthetic examples."},
            {"title": "Blocked", "body": "Copied slides, logos, private data."},
        ]
        return {
            **_base_slide(preset, "refs", reference),
            "type": "content",
            "variant": "matrix",
            "treatment_key": "references",
            "reference_archetype": reference_archetype,
            "title": f"Provenance matrix: {story.get('topic') or 'source route'}",
            "subtitle": treatments["references"],
            "quadrants": quadrants,
        }
    return {
        **_base_slide(preset, "refs", reference),
        "type": "content",
        "variant": "standard",
        "treatment_key": "references",
        "reference_archetype": reference_archetype,
        "title": f"Sources: {story.get('topic') or 'source posture'}",
        "subtitle": treatments["references"],
        "body": _compact_footer_item(structure, limit=120),
        "bullets": source_lines[:3] or ["Use compact footer source IDs.", "Move long citations into an editable table."],
    }


def _table_slide(
    preset: str,
    reference: dict[str, Any],
    deck_style: dict[str, Any],
    *,
    role: str = "table",
    variant: str = "table",
) -> dict[str, Any]:
    treatments = reference["content_treatments"]
    if role in {"decision", "close", "refs"}:
        if role == "refs":
            return _references_slide(preset, reference, deck_style, requested_variant=variant)
        decision = _story_decision(reference)
        rows = decision.get("rows") if isinstance(decision.get("rows"), list) else []
        headers = decision.get("headers") if isinstance(decision.get("headers"), list) else []
        return {
            **_base_slide(preset, "decision", reference),
            "type": "content",
            "variant": "table",
            "title": f"Decision: {_storyboard(reference).get('topic') or 'references treatment'}",
            "subtitle": treatments["decision"],
            "table_treatment": deck_style.get("table_treatment", "standard"),
            "headers": [str(item) for item in headers] or ["Decision", "Evidence", "Owner"],
            "rows": [[str(cell) for cell in row] for row in rows if isinstance(row, list)] or [
                ["Action", treatments["decision"], "Owner visible"],
                ["Sources", treatments["references"], "Footer or table"],
                ["Avoid", "; ".join(reference.get("avoid", [])[:2]), "No copied geometry"],
            ],
            "column_weights": [0.78, 1.35, 0.85],
            "caption": "Synthetic reference gallery: decision rows use generic data only.",
        }
    table = _story_table(reference)
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    headers = table.get("headers") if isinstance(table.get("headers"), list) else []
    return {
        **_base_slide(preset, "table", reference),
        "type": "content",
        "variant": "lab-run-results" if variant == "lab-run-results" else "table",
        "title": f"Table: {_storyboard(reference).get('topic') or 'compact evidence map'}",
        "subtitle": treatments["table"],
        "table_treatment": deck_style.get("table_treatment", "standard"),
        "headers": [str(item) for item in headers] or ["Role", "Treatment rule", "Use"],
        "rows": [[str(cell) for cell in row] for row in rows if isinstance(row, list)] or _table_rows(reference),
        "column_weights": [0.75, 1.25, 0.80],
        "caption": "Rows are synthetic storyboard data from the style-reference catalog.",
        "interpretation": "Readable tables stay short; long detail moves into notes or references.",
    }


def _timeline_slide(preset: str, reference: dict[str, Any]) -> dict[str, Any]:
    story = _storyboard(reference)
    milestones = [
        {"label": str(item.get("label") or ""), "title": str(item.get("title") or ""), "body": str(item.get("body") or "")}
        for item in _story_list(story.get("timeline"))
        if isinstance(item, dict)
    ]
    return {
        **_base_slide(preset, "plan", reference),
        "type": "content",
        "variant": "timeline",
        "title": f"Sequence: {story.get('topic') or 'staged proof gates'}",
        "subtitle": "Use timelines only when sequence changes the decision.",
        "milestones": milestones[:4] or [
            {"label": "01", "title": "Frame", "body": "Pick reference family"},
            {"label": "02", "title": "Bind", "body": "Choose proof object"},
            {"label": "03", "title": "Build", "body": "Render from outline"},
            {"label": "04", "title": "QA", "body": "Check geometry"},
        ],
    }


def _matrix_slide(preset: str, reference: dict[str, Any]) -> dict[str, Any]:
    story = _storyboard(reference)
    quadrants = [
        {"title": str(item.get("title") or ""), "body": str(item.get("body") or "")}
        for item in _story_list(story.get("quadrants"))
        if isinstance(item, dict)
    ]
    return {
        **_base_slide(preset, "matrix", reference),
        "type": "content",
        "variant": "matrix",
        "title": f"Tradeoff: {story.get('topic') or 'four useful quadrants'}",
        "subtitle": reference["content_treatments"]["comparison"],
        "quadrants": quadrants[:4] or [
            {"title": "High proof", "body": "Use chart or figure first."},
            {"title": "High action", "body": "Surface owner and trigger."},
            {"title": "Low certainty", "body": "Show caveat visibly."},
            {"title": "Low burden", "body": "Keep footer compact."},
        ],
    }


def _standard_slide(preset: str, reference: dict[str, Any], *, role: str = "decision") -> dict[str, Any]:
    story = _storyboard(reference)
    comparison = story.get("comparison") if isinstance(story.get("comparison"), dict) else {}
    decision_rows = _story_decision(reference).get("rows")
    slide = {
        **_base_slide(preset, role, reference),
        "type": "content",
        "variant": "standard",
        "title": f"Synthesis: {story.get('topic') or 'one decision line'}",
        "subtitle": reference["content_treatments"]["decision"],
        "body": str(comparison.get("verdict") or "The reference family should constrain structure before the deck is rendered."),
        "bullets": ["State the decision", "Name the evidence object", "Keep sources traceable"],
    }
    if preset == "editorial-minimal":
        slide["bullets"] = ["State the recommendation", "Name the evidence object"]
    else:
        slide["summary_callout"] = str(
            decision_rows[0][0]
            if isinstance(decision_rows, list) and decision_rows and isinstance(decision_rows[0], list)
            else "Do not let style collapse into color and header differences only."
        )
    return slide


def _slide_for_variant(
    preset: str,
    reference: dict[str, Any],
    deck_style: dict[str, Any],
    asset_paths: list[str],
    *,
    role: str,
    variant: str,
) -> dict[str, Any]:
    normalized = (variant or "standard").strip().lower()
    if role in {"refs", "references"}:
        return _references_slide(preset, reference, deck_style, requested_variant=normalized)
    if role == "dashboard":
        return _dashboard_slide(
            preset,
            reference,
            deck_style,
            asset_paths,
            requested_variant=normalized,
        )
    if normalized == "stats":
        return _dashboard_slide(
            preset,
            reference,
            deck_style,
            asset_paths,
            requested_variant=normalized,
        )
    if normalized == "kpi-hero":
        return _kpi_slide(preset, reference)
    if normalized in {"cards-2", "cards-3"}:
        return _cards_slide(preset, reference, variant=normalized)
    if normalized == "comparison-2col":
        return _comparison_slide(preset, reference)
    if normalized == "split":
        return _comparison_slide(preset, reference, variant="split")
    if normalized == "chart":
        return _chart_slide(preset, reference, deck_style)
    if normalized in {"table", "lab-run-results"}:
        return _table_slide(preset, reference, deck_style, role=role, variant=normalized)
    if normalized in {"scientific-figure", "image-sidebar", "flow"}:
        return _figure_slide(preset, reference, deck_style, asset_paths, variant=normalized)
    if normalized == "timeline":
        return _timeline_slide(preset, reference)
    if normalized == "matrix":
        return _matrix_slide(preset, reference)
    return _standard_slide(preset, reference, role=role)


def _slide_buckets(slides: list[dict[str, Any]]) -> set[str]:
    buckets: set[str] = set()
    for slide in slides:
        variant = str(slide.get("variant") or slide.get("type") or "").strip().lower()
        role = str(slide.get("footer") or "").lower()
        treatment_key = str(slide.get("treatment_key") or "").strip().lower()
        if treatment_key in REQUIRED_CONTENT_TREATMENTS and treatment_key != "title":
            buckets.add(treatment_key)
            continue
        if "refs" in role:
            buckets.add("references")
        if variant in {"stats", "kpi-hero"}:
            buckets.add("dashboard")
        if variant in {"comparison-2col", "split", "matrix"}:
            buckets.add("comparison")
        if variant == "chart":
            buckets.add("chart")
        if variant in {"table", "lab-run-results"}:
            buckets.add("table")
        if variant in {"scientific-figure", "image-sidebar", "flow"}:
            buckets.add("figure")
        if "decision" in role or variant == "standard":
            buckets.add("decision")
    return buckets


def _gallery_role_for_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    if normalized in {"stats", "kpi-hero"}:
        return "dashboard"
    if normalized in {"cards-2", "cards-3"}:
        return "proof"
    if normalized in {"comparison-2col", "split"}:
        return "comparison"
    if normalized == "matrix":
        return "matrix"
    if normalized == "timeline":
        return "plan"
    if normalized == "flow":
        return "architecture"
    if normalized in {"scientific-figure", "image-sidebar", "generated-image"}:
        return "figure"
    if normalized in {"table", "lab-run-results"}:
        return "table"
    if normalized == "chart":
        return "chart"
    return "decision"


def _signature_slides(
    preset: str,
    reference: dict[str, Any],
    deck_style: dict[str, Any],
    asset_paths: list[str],
) -> list[dict[str, Any]]:
    slides: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    seen_variants: set[str] = set()
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    showcase_variants = (
        playbook.get("gallery_showcase_variants")
        if isinstance(playbook.get("gallery_showcase_variants"), list)
        else []
    )
    for variant_value in showcase_variants:
        variant = str(variant_value or "").strip().lower()
        if not variant or variant == "title":
            continue
        role = _gallery_role_for_variant(variant)
        key = (role, variant)
        if key in seen or variant in seen_variants:
            continue
        seen.add(key)
        seen_variants.add(variant)
        slides.append(_slide_for_variant(preset, reference, deck_style, asset_paths, role=role, variant=variant))

    archetype_source = (
        playbook.get("slide_archetypes")
        if isinstance(playbook.get("slide_archetypes"), list)
        else reference.get("signature_slide_family", [])
    )
    for item in archetype_source:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "content").strip().lower()
        variant = str(item.get("variant") or "standard").strip().lower()
        if variant == "title":
            continue
        key = (role, variant)
        if key in seen or variant in seen_variants:
            continue
        slide = _slide_for_variant(preset, reference, deck_style, asset_paths, role=role, variant=variant)
        slide_treatments = _slide_buckets([slide])
        if "dashboard" in slide_treatments and "dashboard" in _slide_buckets(slides):
            continue
        seen.add(key)
        seen_variants.add(variant)
        slides.append(slide)

    buckets = _slide_buckets(slides)
    fillers = [
        ("dashboard", lambda: _dashboard_slide(preset, reference, deck_style, asset_paths)),
        ("comparison", lambda: _comparison_slide_for_reference(preset, reference)),
        ("chart", lambda: _chart_slide(preset, reference, deck_style)),
        (
            "table",
            lambda: _table_slide(
                preset,
                reference,
                deck_style,
                variant="lab-run-results" if preset in {"lab-report", "executive-clinical"} else "table",
            ),
        ),
        ("figure", lambda: _figure_slide(preset, reference, deck_style, asset_paths)),
        ("decision", lambda: _table_slide(preset, reference, deck_style, role="decision")),
        ("references", lambda: _references_slide(preset, reference, deck_style)),
    ]
    for bucket, factory in fillers:
        if bucket not in buckets:
            slides.append(factory())
            buckets.add(bucket)
    return _annotate_gallery_slide_recipes(slides[:GALLERY_MAX_CONTENT_SLIDES], reference)


def _outline_for_preset(preset: str, asset_paths: list[str]) -> dict[str, Any]:
    reference = preset_style_reference(preset)
    profile = preset_treatment_profile(preset)
    deck_style = _deck_style_for(preset, profile)
    slides = _signature_slides(preset, reference, deck_style, asset_paths)
    storyboard = _storyboard(reference)
    title_archetype = _treatment_archetype(reference, "title")
    reference_archetype = _treatment_archetype(reference, "references")
    title_slide = {
        "type": "title",
        "title_layout": str(title_archetype.get("title_layout") or deck_style.get("title_layout") or "split-hero"),
        "title_archetype": title_archetype,
        "reference_archetype": reference_archetype,
        "kicker": _archetype_kicker(title_archetype, str(profile.get("family") or "STYLE REFERENCE")),
        "title": str(storyboard.get("title") or reference["reference_name"]),
        "subtitle": str(storyboard.get("subtitle") or reference.get("style_dna") or ""),
        "footer": str(reference_archetype.get("structure") or reference["content_treatments"].get("references") or ""),
        "sources": [str(reference_archetype.get("archetype_id") or reference.get("reference_id") or "")],
        "refs": [_compact_reference_slug(reference.get("reference_id"))],
        "chips": [
            preset,
            str(profile.get("family") or "style"),
            str(storyboard.get("topic") or reference.get("source_status") or "synthetic"),
        ],
    }
    _annotate_gallery_slide_recipes([title_slide], reference)
    all_slides = [title_slide, *slides]
    for slide_index, slide in enumerate(all_slides, start=1):
        slide.setdefault("slide_id", f"s{slide_index}")
    return {
        "title": f"{reference['reference_name']} gallery",
        "subtitle": str(reference.get("style_dna") or ""),
        "deck_style": deck_style,
        "metadata": {
            "gallery_version": GALLERY_VERSION,
            "style_reference": {
                "catalog_version": reference.get("catalog_version"),
                "style_preset": preset,
                "reference_id": reference.get("reference_id"),
                "reference_name": reference.get("reference_name"),
                "source_status": reference.get("source_status"),
                "style_source_intake": reference.get("style_source_intake", {}),
                "style_metric_profile": reference.get("style_metric_profile", {}),
                "example_storyboard": storyboard,
                "layout_playbook": reference.get("layout_playbook"),
                "content_recipe_library": reference.get("content_recipe_library"),
            },
            "publish_safety": reference.get("publish_safety", {}),
            "signature_slide_family": reference.get("signature_slide_family", []),
        },
        "slides": all_slides,
    }


def _write_outline(outline_path: Path, preset: str, asset_paths: list[str]) -> None:
    outline_path.parent.mkdir(parents=True, exist_ok=True)
    outline_path.write_text(json.dumps(_outline_for_preset(preset, asset_paths), indent=2) + "\n", encoding="utf-8")


def _rendered_slide_images(preset_dir: Path) -> list[Path]:
    render_dir = preset_dir / "renders"
    images: list[Path] = []
    for pattern in ("*.jpg", "*.jpeg", "*.png"):
        images.extend(sorted(render_dir.glob(pattern)))
    return images


def _rendered_visual_signature(record: dict[str, Any]) -> dict[str, Any]:
    images = [
        Path(str(path))
        for path in record.get("rendered_slide_images", [])
        if str(path).strip()
    ]
    content_images = images[1:5] if len(images) > 1 else images[:4]
    if Image is None or ImageStat is None:
        return {
            "available": False,
            "reason": "pillow_unavailable",
            "source_slide_count": len(content_images),
        }
    if not content_images:
        return {
            "available": False,
            "reason": "no_rendered_content_slides",
            "source_slide_count": 0,
        }

    values: list[int] = []
    brightness_means: list[float] = []
    brightness_stddevs: list[float] = []
    nonblank = 0
    used_paths: list[str] = []
    for path in content_images:
        if not path.exists():
            continue
        with Image.open(path) as raw:
            gray = raw.convert("L")
            stat = ImageStat.Stat(gray)
            brightness_means.append(round(float(stat.mean[0]), 3))
            brightness_stddevs.append(round(float(stat.stddev[0]), 3))
            if float(stat.stddev[0]) > 1.0:
                nonblank += 1
            thumb = gray.resize(VISUAL_HASH_SIZE)
            values.extend(int(value) for value in thumb.getdata())
            used_paths.append(str(path))
    if not values:
        return {
            "available": False,
            "reason": "rendered_content_images_unreadable",
            "source_slide_count": len(content_images),
            "used_slide_count": 0,
        }
    mean_value = sum(values) / len(values)
    bits = "".join("1" if value >= mean_value else "0" for value in values)
    return {
        "available": True,
        "algorithm": "average_hash_v1",
        "hash_size": list(VISUAL_HASH_SIZE),
        "average_hash": hex(int(bits, 2))[2:].zfill((len(bits) + 3) // 4),
        "bit_count": len(bits),
        "source_slide_count": len(content_images),
        "used_slide_count": len(used_paths),
        "used_slide_images": used_paths,
        "nonblank_slide_count": nonblank,
        "brightness_mean": round(sum(brightness_means) / len(brightness_means), 3) if brightness_means else None,
        "brightness_stddev_mean": round(sum(brightness_stddevs) / len(brightness_stddevs), 3) if brightness_stddevs else None,
    }


def _image_visual_signature(path: Path) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {
            "available": False,
            "reason": "pillow_unavailable",
            "path": str(path),
        }
    if not path.exists() or not path.is_file():
        return {
            "available": False,
            "reason": "image_missing",
            "path": str(path),
        }
    try:
        with Image.open(path) as raw:
            gray = raw.convert("L")
            stat = ImageStat.Stat(gray)
            gray_thumb = gray.resize(VISUAL_HASH_SIZE)
            gray_values = [int(value) for value in gray_thumb.getdata()]
            mean_value = sum(gray_values) / len(gray_values)
            bits = "".join("1" if value >= mean_value else "0" for value in gray_values)

            color_thumb = raw.convert("RGB").resize(VISUAL_THUMB_SIGNATURE_SIZE)
            quantized_values: list[int] = []
            for pixel in color_thumb.getdata():
                quantized_values.extend(int(channel) // 16 for channel in pixel)
    except Exception as exc:
        return {
            "available": False,
            "reason": "image_unreadable",
            "path": str(path),
            "error": str(exc),
        }
    return {
        "available": True,
        "path": str(path),
        "layout_hash_algorithm": "average_hash_v1",
        "layout_hash_size": list(VISUAL_HASH_SIZE),
        "layout_average_hash": hex(int(bits, 2))[2:].zfill((len(bits) + 3) // 4),
        "layout_bit_count": len(bits),
        "thumb_signature_algorithm": "rgb_quantized_thumbnail_sha256_v1",
        "thumb_signature_size": list(VISUAL_THUMB_SIGNATURE_SIZE),
        "thumb_signature_sha256": hashlib.sha256(bytes(quantized_values)).hexdigest(),
        "brightness_mean": round(float(stat.mean[0]), 3),
        "brightness_stddev": round(float(stat.stddev[0]), 3),
        "nonblank": float(stat.stddev[0]) > 1.0,
    }


def _hash_distance(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _content_signature(record: dict[str, Any], *, limit: int = 4) -> str:
    sequence = [
        str(item).strip()
        for item in record.get("variant_sequence", [])
        if str(item).strip() and str(item).strip() != "title"
    ]
    return ">".join(sequence[:limit])


def _structural_playbook_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    unique_floors = {
        "title": 1,
        "comparison": 3,
        "chart": 2,
        "table": 2,
        "figure": 3,
        "dashboard": 4,
        "decision": 3,
        "references": 3,
    }
    signatures: dict[str, str] = {}
    treatment_maps_by_preset: dict[str, dict[str, list[str]]] = {}
    gallery_showcase_by_preset: dict[str, list[str]] = {}
    missing_by_preset: dict[str, list[str]] = {}
    invalid_by_preset: dict[str, dict[str, list[str]]] = {}
    first_choice_counts: dict[str, dict[str, int]] = {key: {} for key in REQUIRED_CONTENT_TREATMENTS}
    option_counts: dict[str, dict[str, int]] = {key: {} for key in REQUIRED_CONTENT_TREATMENTS}
    version_counts: dict[str, int] = {}
    archetype_counts: dict[str, dict[str, int]] = {key: {} for key in REQUIRED_CONTENT_TREATMENTS}
    semantic_archetype_counts: dict[str, dict[str, int]] = {key: {} for key in REQUIRED_CONTENT_TREATMENTS}
    archetypes_by_preset: dict[str, dict[str, Any]] = {}
    semantic_archetypes_by_preset: dict[str, dict[str, Any]] = {}
    missing_archetypes_by_preset: dict[str, list[str]] = {}
    for record in records:
        preset = str(record.get("preset") or "").strip()
        version = str(record.get("layout_playbook_version") or "").strip()
        if version:
            version_counts[version] = version_counts.get(version, 0) + 1
        raw_map = (
            record.get("treatment_variant_map")
            if isinstance(record.get("treatment_variant_map"), dict)
            else {}
        )
        normalized: dict[str, list[str]] = {}
        missing: list[str] = []
        invalid: dict[str, list[str]] = {}
        for treatment_key in REQUIRED_CONTENT_TREATMENTS:
            values = raw_map.get(treatment_key)
            variants = (
                [str(item).strip() for item in values if str(item).strip()]
                if isinstance(values, list)
                else []
            )
            normalized[treatment_key] = variants
            if not variants:
                missing.append(treatment_key)
            bad_variants = [
                variant for variant in variants if variant not in SUPPORTED_OUTLINE_VARIANTS
            ]
            if bad_variants:
                invalid[treatment_key] = bad_variants
            if variants:
                first = variants[0]
                first_choice_counts[treatment_key][first] = first_choice_counts[treatment_key].get(first, 0) + 1
                for variant in variants:
                    option_counts[treatment_key][variant] = option_counts[treatment_key].get(variant, 0) + 1
        treatment_maps_by_preset[preset] = normalized
        signatures[preset] = _text_sha256(json.dumps(normalized, sort_keys=True))
        gallery_variants = (
            [str(item).strip() for item in record.get("gallery_showcase_variants", []) if str(item).strip()]
            if isinstance(record.get("gallery_showcase_variants"), list)
            else []
        )
        gallery_showcase_by_preset[preset] = gallery_variants
        if missing:
            missing_by_preset[preset] = missing
        if invalid:
            invalid_by_preset[preset] = invalid
        raw_archetypes = (
            record.get("treatment_archetypes")
            if isinstance(record.get("treatment_archetypes"), dict)
            else {}
        )
        preset_archetypes: dict[str, Any] = {}
        preset_semantic_archetypes: dict[str, Any] = {}
        missing_archetypes: list[str] = []
        for treatment_key in REQUIRED_CONTENT_TREATMENTS:
            archetype = raw_archetypes.get(treatment_key) if isinstance(raw_archetypes.get(treatment_key), dict) else {}
            archetype_id = str(archetype.get("archetype_id") or "").strip()
            if not archetype_id:
                missing_archetypes.append(treatment_key)
                continue
            semantic_material = {
                "structure": archetype.get("structure"),
                "object_pattern": archetype.get("object_pattern"),
                "required_fields": (
                    archetype.get("required_fields")
                    if isinstance(archetype.get("required_fields"), list)
                    else []
                ),
                "primary_variants": (
                    archetype.get("primary_variants")
                    if isinstance(archetype.get("primary_variants"), list)
                    else []
                ),
                "title_layout": archetype.get("title_layout"),
                "footer_mode": archetype.get("footer_mode"),
                "content_goal": archetype.get("content_goal"),
            }
            semantic_signature = _text_sha256(json.dumps(semantic_material, sort_keys=True))
            preset_archetypes[treatment_key] = {
                "archetype_id": archetype_id,
                "structure": archetype.get("structure"),
                "object_pattern": archetype.get("object_pattern"),
                "primary_variants": archetype.get("primary_variants"),
                "title_layout": archetype.get("title_layout"),
                "footer_mode": archetype.get("footer_mode"),
                "archetype_signature": archetype.get("archetype_signature"),
            }
            preset_semantic_archetypes[treatment_key] = {
                **semantic_material,
                "semantic_signature": semantic_signature,
            }
            archetype_counts[treatment_key][archetype_id] = archetype_counts[treatment_key].get(archetype_id, 0) + 1
            semantic_archetype_counts[treatment_key][semantic_signature] = (
                semantic_archetype_counts[treatment_key].get(semantic_signature, 0) + 1
            )
        archetypes_by_preset[preset] = preset_archetypes
        semantic_archetypes_by_preset[preset] = preset_semantic_archetypes
        if missing_archetypes:
            missing_archetypes_by_preset[preset] = missing_archetypes
    first_choice_unique_counts = {
        key: len(values) for key, values in first_choice_counts.items()
    }
    option_unique_counts = {
        key: len(values) for key, values in option_counts.items()
    }
    floor_failures = {
        key: {
            "minimum": minimum,
            "actual": int(first_choice_unique_counts.get(key) or 0),
        }
        for key, minimum in unique_floors.items()
        if int(first_choice_unique_counts.get(key) or 0) < minimum
    }
    archetype_unique_counts = {
        key: len(values) for key, values in archetype_counts.items()
    }
    semantic_archetype_unique_counts = {
        key: len(values) for key, values in semantic_archetype_counts.items()
    }
    archetype_floor_failures = {
        key: {
            "minimum": len(records),
            "actual": int(archetype_unique_counts.get(key) or 0),
        }
        for key in REQUIRED_CONTENT_TREATMENTS
        if int(archetype_unique_counts.get(key) or 0) < len(records)
    }
    semantic_archetype_floor_failures = {
        key: {
            "minimum": len(records),
            "actual": int(semantic_archetype_unique_counts.get(key) or 0),
        }
        for key in REQUIRED_CONTENT_TREATMENTS
        if int(semantic_archetype_unique_counts.get(key) or 0) < len(records)
    }
    gallery_signatures = {
        preset: ">".join(variants[:4])
        for preset, variants in gallery_showcase_by_preset.items()
    }
    unique_signatures = len(set(signatures.values()))
    unique_gallery_signatures = len(set(gallery_signatures.values()))
    coverage_passed = (
        bool(records)
        and not missing_by_preset
        and not invalid_by_preset
        and not missing_archetypes_by_preset
        and all(version_counts)
    )
    diversity_passed = (
        unique_signatures == len(records)
        and unique_gallery_signatures == len(records)
        and not floor_failures
        and not archetype_floor_failures
        and not semantic_archetype_floor_failures
    )
    return {
        "playbook_version": "style_reference_layout_playbook_v1",
        "required_treatment_keys": list(REQUIRED_CONTENT_TREATMENTS),
        "signature_count": len(signatures),
        "unique_signature_count": unique_signatures,
        "signatures": signatures,
        "treatment_variant_maps_by_preset": treatment_maps_by_preset,
        "gallery_showcase_signatures": gallery_signatures,
        "unique_gallery_showcase_signature_count": unique_gallery_signatures,
        "gallery_showcase_by_preset": gallery_showcase_by_preset,
        "version_counts": dict(sorted(version_counts.items())),
        "first_choice_counts": {
            key: dict(sorted(values.items())) for key, values in first_choice_counts.items()
        },
        "first_choice_unique_counts": first_choice_unique_counts,
        "option_counts": {
            key: dict(sorted(values.items())) for key, values in option_counts.items()
        },
        "option_unique_counts": option_unique_counts,
        "treatment_archetypes_by_preset": archetypes_by_preset,
        "treatment_archetype_semantics_by_preset": semantic_archetypes_by_preset,
        "treatment_archetype_counts": {
            key: dict(sorted(values.items())) for key, values in archetype_counts.items()
        },
        "treatment_archetype_semantic_counts": {
            key: dict(sorted(values.items())) for key, values in semantic_archetype_counts.items()
        },
        "treatment_archetype_unique_counts": archetype_unique_counts,
        "treatment_archetype_semantic_unique_counts": semantic_archetype_unique_counts,
        "treatment_archetype_floor_failures": archetype_floor_failures,
        "treatment_archetype_semantic_floor_failures": semantic_archetype_floor_failures,
        "missing_archetypes_by_preset": missing_archetypes_by_preset,
        "first_choice_unique_floors": unique_floors,
        "floor_failures": floor_failures,
        "missing_by_preset": missing_by_preset,
        "invalid_by_preset": invalid_by_preset,
        "coverage_passed": coverage_passed,
        "diversity_passed": diversity_passed,
        "passed": coverage_passed and diversity_passed,
    }


def _structural_motif_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    signatures: dict[str, str] = {}
    version_counts: dict[str, int] = {}
    motifs_by_preset: dict[str, list[str]] = {}
    background_by_preset: dict[str, str] = {}
    thin_by_preset: dict[str, dict[str, int]] = {}
    for record in records:
        preset = str(record.get("preset") or "").strip()
        motif = (
            record.get("structural_motif_library")
            if isinstance(record.get("structural_motif_library"), dict)
            else {}
        )
        version = str(motif.get("motif_library_version") or record.get("motif_library_version") or "").strip()
        if version:
            version_counts[version] = version_counts.get(version, 0) + 1
        signature = str(motif.get("motif_signature") or record.get("structural_motif_signature") or "").strip()
        signatures[preset] = _text_sha256(signature) if signature else ""
        layout_motifs = (
            [str(item).strip() for item in motif.get("layout_motifs", []) if str(item).strip()]
            if isinstance(motif.get("layout_motifs"), list)
            else []
        )
        rules = (
            [str(item).strip() for item in motif.get("content_object_rules", []) if str(item).strip()]
            if isinstance(motif.get("content_object_rules"), list)
            else []
        )
        motifs_by_preset[preset] = layout_motifs
        background_by_preset[preset] = str(motif.get("background_structure") or "").strip()
        if len(layout_motifs) < 3 or len(rules) < 3 or not background_by_preset[preset] or not signature:
            thin_by_preset[preset] = {
                "layout_motif_count": len(layout_motifs),
                "content_object_rule_count": len(rules),
                "has_background_structure": int(bool(background_by_preset[preset])),
                "has_signature": int(bool(signature)),
            }
    coverage_passed = (
        bool(records)
        and not thin_by_preset
        and version_counts.get(STRUCTURAL_MOTIF_LIBRARY_VERSION) == len(records)
        and all(signatures.values())
    )
    diversity_passed = len(set(signatures.values())) == len(records) if records else False
    return {
        "motif_library_version": STRUCTURAL_MOTIF_LIBRARY_VERSION,
        "signature_count": len(signatures),
        "unique_signature_count": len(set(signatures.values())),
        "signature_hashes": signatures,
        "version_counts": dict(sorted(version_counts.items())),
        "background_structure_by_preset": background_by_preset,
        "layout_motifs_by_preset": motifs_by_preset,
        "thin_by_preset": thin_by_preset,
        "coverage_passed": coverage_passed,
        "diversity_passed": diversity_passed,
        "passed": coverage_passed and diversity_passed,
    }


def _style_metric_profile_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    signatures: dict[str, str] = {}
    version_counts: dict[str, int] = {}
    density_by_preset: dict[str, str] = {}
    whitespace_by_preset: dict[str, float] = {}
    body_words_by_preset: dict[str, list[int]] = {}
    thin_by_preset: dict[str, dict[str, Any]] = {}
    required_mix_keys = {"chart", "table", "figure", "prose"}
    for record in records:
        preset = str(record.get("preset") or "").strip()
        profile = (
            record.get("style_metric_profile")
            if isinstance(record.get("style_metric_profile"), dict)
            else {}
        )
        version = str(profile.get("metric_profile_version") or "").strip()
        if version:
            version_counts[version] = version_counts.get(version, 0) + 1
        signature = str(profile.get("metric_signature") or record.get("style_metric_signature") or "").strip()
        signatures[preset] = signature
        density_by_preset[preset] = str(profile.get("density_level") or "").strip()
        try:
            whitespace = float(profile.get("whitespace_ratio_target"))
        except (TypeError, ValueError):
            whitespace = -1.0
        whitespace_by_preset[preset] = round(whitespace, 3)
        budget_raw = (
            profile.get("body_words_per_content_slide")
            if isinstance(profile.get("body_words_per_content_slide"), list)
            else []
        )
        budget = [
            int(item)
            for item in budget_raw
            if isinstance(item, int) or (isinstance(item, str) and item.isdigit())
        ][:2]
        body_words_by_preset[preset] = budget
        mix = profile.get("evidence_object_mix") if isinstance(profile.get("evidence_object_mix"), dict) else {}
        missing_mix = sorted(required_mix_keys - {str(key) for key in mix})
        issues: dict[str, Any] = {}
        if version != STYLE_METRIC_PROFILE_VERSION:
            issues["version"] = version
        if not density_by_preset[preset]:
            issues["density_level"] = "missing"
        if not 0.12 <= whitespace <= 0.55:
            issues["whitespace_ratio_target"] = whitespace
        if len(budget) != 2 or budget[0] < 10 or budget[1] < budget[0] or budget[1] > 90:
            issues["body_words_per_content_slide"] = budget_raw
        try:
            max_objects = int(profile.get("max_primary_objects") or 0)
        except (TypeError, ValueError):
            max_objects = 0
        if max_objects < 1 or max_objects > 4:
            issues["max_primary_objects"] = profile.get("max_primary_objects")
        if missing_mix:
            issues["missing_evidence_object_mix"] = missing_mix
        for key in ("visual_hierarchy", "source_burden", "footer_posture"):
            if not str(profile.get(key) or "").strip():
                issues[key] = "missing"
        for key in ("artifact_bias", "readability_bias"):
            if len(profile.get(key) if isinstance(profile.get(key), list) else []) < 2:
                issues[key] = "too_thin"
        if not signature:
            issues["metric_signature"] = "missing"
        if issues:
            thin_by_preset[preset] = issues
    coverage_passed = (
        bool(records)
        and not thin_by_preset
        and version_counts.get(STYLE_METRIC_PROFILE_VERSION) == len(records)
        and all(signatures.values())
    )
    diversity_passed = len(set(signatures.values())) == len(records) if records else False
    return {
        "metric_profile_version": STYLE_METRIC_PROFILE_VERSION,
        "signature_count": len(signatures),
        "unique_signature_count": len(set(signatures.values())),
        "signatures": signatures,
        "version_counts": dict(sorted(version_counts.items())),
        "density_by_preset": density_by_preset,
        "whitespace_ratio_target_by_preset": whitespace_by_preset,
        "body_words_per_content_slide_by_preset": body_words_by_preset,
        "thin_by_preset": thin_by_preset,
        "coverage_passed": coverage_passed,
        "diversity_passed": diversity_passed,
        "passed": coverage_passed and diversity_passed,
    }


def _release_evidence(
    *,
    outdir: Path,
    records: list[dict[str, Any]],
    qa_totals: dict[str, Any],
    contact: Path | None,
    structure_contact: Path | None,
    footer_contact: Path | None = None,
    treatment_contact_sheets: dict[str, Path] | None = None,
    preset_contact_collections: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content_signatures = {
        str(record.get("preset")): _content_signature(record)
        for record in records
    }
    renderer_signatures = {
        str(record.get("preset")): str(
            (
                record.get("renderer_treatments", {})
                if isinstance(record.get("renderer_treatments"), dict)
                else {}
            ).get("signature")
            or ""
        )
        for record in records
    }
    content_recipe_summaries = {
        str(record.get("preset")): (
            record.get("content_recipe_summary")
            if isinstance(record.get("content_recipe_summary"), dict)
            else {}
        )
        for record in records
    }
    content_recipe_signatures = {
        preset: str(summary.get("library_signature") or "")
        for preset, summary in content_recipe_summaries.items()
    }
    recipe_version_counts: dict[str, int] = {}
    recipe_missing_by_preset: dict[str, list[str]] = {}
    recipe_invalid_by_preset: dict[str, dict[str, list[str]]] = {}
    recipe_count_by_preset: dict[str, int] = {}
    recipe_signature_hashes_by_preset: dict[str, dict[str, str]] = {}
    for preset, summary in content_recipe_summaries.items():
        version = str(summary.get("library_version") or "")
        if version:
            recipe_version_counts[version] = recipe_version_counts.get(version, 0) + 1
        recipe_count_by_preset[preset] = int(summary.get("recipe_count") or 0)
        missing = summary.get("missing_recipe_keys") if isinstance(summary.get("missing_recipe_keys"), list) else []
        invalid = (
            summary.get("invalid_recipe_fields")
            if isinstance(summary.get("invalid_recipe_fields"), dict)
            else {}
        )
        if missing:
            recipe_missing_by_preset[preset] = [str(item) for item in missing]
        if invalid:
            recipe_invalid_by_preset[preset] = {
                str(key): [str(item) for item in value]
                for key, value in invalid.items()
                if isinstance(value, list)
            }
        hashes = (
            summary.get("recipe_signature_hashes")
            if isinstance(summary.get("recipe_signature_hashes"), dict)
            else {}
        )
        recipe_signature_hashes_by_preset[preset] = {
            str(key): str(value)
            for key, value in hashes.items()
            if str(key).strip() and str(value).strip()
        }
    renderer_field_counts: dict[str, dict[str, int]] = {field: {} for field in RENDERER_TREATMENT_FIELDS}
    for record in records:
        treatments = record.get("renderer_treatments") if isinstance(record.get("renderer_treatments"), dict) else {}
        fields = treatments.get("fields") if isinstance(treatments.get("fields"), dict) else {}
        for field in RENDERER_TREATMENT_FIELDS:
            value = str(fields.get(field) or "").strip()
            if value:
                renderer_field_counts[field][value] = renderer_field_counts[field].get(value, 0) + 1
    renderer_unique_counts = {
        field: len(counts)
        for field, counts in renderer_field_counts.items()
    }
    first_variants: dict[str, int] = {}
    for signature in content_signatures.values():
        first = signature.split(">", 1)[0] if signature else ""
        if first:
            first_variants[first] = first_variants.get(first, 0) + 1

    rendered_records = [record for record in records if record.get("rendered_slide_images")]
    footer_sheet_summary = _footer_contact_sheet_summary(records, footer_contact)
    treatment_sheet_summary = _treatment_contact_sheet_summary(records, treatment_contact_sheets or {})
    preset_collection_summary = _preset_contact_collection_summary(records, preset_contact_collections or {})
    treatment_visual_summary = _treatment_visual_diversity_summary(records)
    visual_records: list[dict[str, Any]] = []
    for record in rendered_records:
        signature = _rendered_visual_signature(record)
        record["rendered_visual_signature"] = signature
        if signature.get("available"):
            visual_records.append(
                {
                    "preset": record.get("preset"),
                    "average_hash": signature.get("average_hash"),
                    "bit_count": signature.get("bit_count"),
                    "source_slide_count": signature.get("source_slide_count"),
                    "nonblank_slide_count": signature.get("nonblank_slide_count"),
                    "brightness_mean": signature.get("brightness_mean"),
                    "brightness_stddev_mean": signature.get("brightness_stddev_mean"),
                }
            )

    pairwise: list[dict[str, Any]] = []
    for index, left in enumerate(visual_records):
        for right in visual_records[index + 1 :]:
            distance = _hash_distance(str(left.get("average_hash") or ""), str(right.get("average_hash") or ""))
            bit_count = int(left.get("bit_count") or right.get("bit_count") or 0)
            pairwise.append(
                {
                    "left": left.get("preset"),
                    "right": right.get("preset"),
                    "distance": distance,
                    "normalized_distance": round(distance / bit_count, 4) if bit_count else None,
                }
            )
    pairwise.sort(key=lambda item: (float(item.get("normalized_distance") or 0), int(item.get("distance") or 0)))
    min_pair = pairwise[0] if pairwise else {}
    min_normalized = float(min_pair.get("normalized_distance") or 0) if min_pair else None
    unique_hash_count = len({str(item.get("average_hash")) for item in visual_records if item.get("average_hash")})
    low_distance_pairs = [
        item
        for item in pairwise
        if float(item.get("normalized_distance") or 0) < VISUAL_SIMILARITY_WARN_NORMALIZED_DISTANCE
    ][:8]

    all_qa_clean = all(
        int(qa_totals.get(key) or 0) == 0
        for key in (
            "overflow_count",
            "overlap_count",
            "geometry_error_count",
            "design_error_count",
            "design_warning_count",
            "visual_warning_count",
            "placeholder_count",
        )
    )
    rendered_available = len(visual_records) == len(records) and bool(records)
    visual_distinct = (
        not rendered_records
        or (
            rendered_available
            and unique_hash_count == len(records)
            and min_normalized is not None
            and min_normalized >= VISUAL_DIVERSITY_MIN_NORMALIZED_DISTANCE
        )
    )
    renderer_treatments_distinct = (
        len(set(renderer_signatures.values())) == len(records)
        and renderer_unique_counts.get("chart_treatment", 0) >= 3
        and renderer_unique_counts.get("table_treatment", 0) >= 4
        and renderer_unique_counts.get("figure_table_treatment", 0) >= 4
        and renderer_unique_counts.get("title_layout", 0) >= 4
        and renderer_unique_counts.get("footer_mode", 0) >= 2
    )
    structural_playbook_summary = _structural_playbook_summary(records)
    structural_motif_summary = _structural_motif_summary(records)
    style_metric_profile_summary = _style_metric_profile_summary(records)
    content_recipe_coverage = (
        bool(records)
        and all(summary.get("passed") for summary in content_recipe_summaries.values())
        and all(recipe_count == len(REQUIRED_CONTENT_TREATMENTS) for recipe_count in recipe_count_by_preset.values())
    )
    content_recipes_distinct = (
        content_recipe_coverage
        and len(set(content_recipe_signatures.values())) == len(records)
        and all(content_recipe_signatures.values())
    )

    return {
        "evidence_version": RELEASE_EVIDENCE_VERSION,
        "gallery_version": GALLERY_VERSION,
        "outdir": str(outdir),
        "preset_count": len(records),
        "presets": [record.get("preset") for record in records],
        "qa_totals": qa_totals,
        "qa_clean": all_qa_clean,
        "contact_sheet": _file_fingerprint(contact) if contact else {"path": "", "exists": False},
        "structure_contact_sheet": (
            _file_fingerprint(structure_contact)
            if structure_contact
            else {"path": "", "exists": False}
        ),
        "footer_contact_sheet": (
            _file_fingerprint(footer_contact)
            if footer_contact
            else {"path": "", "exists": False}
        ),
        "footer_contact_sheet_summary": footer_sheet_summary,
        "treatment_contact_sheets": {
            treatment_key: _file_fingerprint(path)
            for treatment_key, path in sorted((treatment_contact_sheets or {}).items())
        },
        "treatment_contact_sheet_summary": treatment_sheet_summary,
        "preset_contact_collections": preset_contact_collections or {},
        "preset_contact_collection_summary": preset_collection_summary,
        "treatment_visual_diversity": treatment_visual_summary,
        "content_signature_summary": {
            "signature_count": len(content_signatures),
            "unique_signature_count": len(set(content_signatures.values())),
            "first_content_variant_counts": dict(sorted(first_variants.items())),
            "signatures": content_signatures,
            "unique_first_four_content_signatures": len(set(content_signatures.values())) == len(records),
        },
        "renderer_treatment_summary": {
            "field_order": list(RENDERER_TREATMENT_FIELDS),
            "signature_count": len(renderer_signatures),
            "unique_signature_count": len(set(renderer_signatures.values())),
            "signatures": renderer_signatures,
            "field_counts": {
                field: dict(sorted(counts.items()))
                for field, counts in renderer_field_counts.items()
            },
            "unique_field_counts": renderer_unique_counts,
            "passed": renderer_treatments_distinct,
        },
        "structural_playbook_summary": structural_playbook_summary,
        "structural_motif_summary": structural_motif_summary,
        "style_metric_profile_summary": style_metric_profile_summary,
        "content_recipe_library_summary": {
            "library_version": CONTENT_RECIPE_LIBRARY_VERSION,
            "required_treatment_keys": list(REQUIRED_CONTENT_TREATMENTS),
            "signature_count": len(content_recipe_signatures),
            "unique_signature_count": len(set(content_recipe_signatures.values())),
            "signatures": content_recipe_signatures,
            "version_counts": dict(sorted(recipe_version_counts.items())),
            "recipe_count_by_preset": dict(sorted(recipe_count_by_preset.items())),
            "missing_by_preset": recipe_missing_by_preset,
            "invalid_by_preset": recipe_invalid_by_preset,
            "recipe_signature_hashes_by_preset": recipe_signature_hashes_by_preset,
            "coverage_passed": content_recipe_coverage,
            "unique_library_signatures": content_recipes_distinct,
            "passed": content_recipe_coverage and content_recipes_distinct,
        },
        "visual_diversity": {
            "available": bool(rendered_records),
            "rendered_record_count": len(rendered_records),
            "visual_signature_count": len(visual_records),
            "unique_visual_hash_count": unique_hash_count,
            "hash_algorithm": "average_hash_v1",
            "hash_size": list(VISUAL_HASH_SIZE),
            "min_normalized_distance_floor": VISUAL_DIVERSITY_MIN_NORMALIZED_DISTANCE,
            "similarity_warning_distance": VISUAL_SIMILARITY_WARN_NORMALIZED_DISTANCE,
            "min_pairwise_distance": min_pair,
            "lowest_distance_pairs": pairwise[:10],
            "low_distance_pairs": low_distance_pairs,
            "passed": visual_distinct,
            "records": visual_records,
        },
        "passed_release_evidence_gate": all_qa_clean
        and len(set(content_signatures.values())) == len(records)
        and renderer_treatments_distinct
        and structural_playbook_summary.get("passed")
        and structural_motif_summary.get("passed")
        and style_metric_profile_summary.get("passed")
        and content_recipes_distinct
        and (not rendered_records or footer_sheet_summary.get("passed"))
        and (not rendered_records or treatment_sheet_summary.get("passed"))
        and (not rendered_records or preset_collection_summary.get("passed"))
        and (not rendered_records or treatment_visual_summary.get("passed"))
        and visual_distinct,
    }


def _make_contact_sheet(outdir: Path, records: list[dict[str, Any]]) -> Path | None:
    if Image is None or ImageDraw is None:
        return None
    thumb_w, thumb_h = 300, 169
    label_h = 38
    gutter = 14
    cols = 4
    rows = len(records)
    sheet_w = cols * thumb_w + (cols + 1) * gutter
    sheet_h = rows * (thumb_h + label_h + gutter) + gutter
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#F8FAFC")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default() if ImageFont else None
    for row_idx, record in enumerate(records):
        preset_dir = Path(record["preset_dir"])
        preset = str(record["preset"])
        images = _rendered_slide_images(preset_dir)[1:5]
        y = gutter + row_idx * (thumb_h + label_h + gutter)
        draw.text((gutter, y), preset, fill="#111827", font=font)
        for col_idx, image_path in enumerate(images[:cols]):
            x = gutter + col_idx * (thumb_w + gutter)
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                img.thumbnail((thumb_w, thumb_h))
                canvas = Image.new("RGB", (thumb_w, thumb_h), "#FFFFFF")
                canvas.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
                sheet.paste(canvas, (x, y + label_h))
    output = outdir / "style_reference_contact_sheet.jpg"
    sheet.save(output, quality=88)
    return output


def _unique_contact_indices(count: int, candidates: list[int]) -> list[int]:
    indices: list[int] = []
    for candidate in candidates:
        index = candidate if candidate >= 0 else count + candidate
        if 0 <= index < count and index not in indices:
            indices.append(index)
    return indices


def _make_structure_contact_sheet(outdir: Path, records: list[dict[str, Any]]) -> Path | None:
    if Image is None or ImageDraw is None:
        return None
    thumb_w, thumb_h = 300, 169
    label_h = 50
    header_h = 26
    gutter = 14
    cols = 4
    column_labels = ["opener", "evidence", "data", "refs"]
    rows = len(records)
    sheet_w = cols * thumb_w + (cols + 1) * gutter
    sheet_h = header_h + rows * (thumb_h + label_h + gutter) + gutter
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#F8FAFC")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default() if ImageFont else None
    for col_idx, label in enumerate(column_labels):
        x = gutter + col_idx * (thumb_w + gutter)
        draw.text((x, gutter), label, fill="#475569", font=font)
    for row_idx, record in enumerate(records):
        preset_dir = Path(record["preset_dir"])
        preset = str(record["preset"])
        images = _rendered_slide_images(preset_dir)
        if not images:
            continue
        mid_index = 3 if len(images) > 4 else max(1, len(images) // 2)
        selected = [
            images[index]
            for index in _unique_contact_indices(len(images), [0, 1, mid_index, -1])
        ][:cols]
        y = header_h + gutter + row_idx * (thumb_h + label_h + gutter)
        draw.text((gutter, y), preset, fill="#111827", font=font)
        archetypes = (
            record.get("treatment_archetypes")
            if isinstance(record.get("treatment_archetypes"), dict)
            else {}
        )
        title_id = ""
        refs_id = ""
        title = archetypes.get("title") if isinstance(archetypes.get("title"), dict) else {}
        refs = archetypes.get("references") if isinstance(archetypes.get("references"), dict) else {}
        if isinstance(title, dict):
            title_id = str(title.get("archetype_id") or "")
        if isinstance(refs, dict):
            refs_id = str(refs.get("archetype_id") or "")
        if title_id or refs_id:
            draw.text((gutter, y + 13), f"{title_id} / {refs_id}"[:92], fill="#64748B", font=font)
        for col_idx, image_path in enumerate(selected):
            x = gutter + col_idx * (thumb_w + gutter)
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                img.thumbnail((thumb_w, thumb_h))
                canvas = Image.new("RGB", (thumb_w, thumb_h), "#FFFFFF")
                canvas.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
                sheet.paste(canvas, (x, y + label_h))
    output = outdir / "style_reference_structure_contact_sheet.jpg"
    sheet.save(output, quality=88)
    return output


def _rendered_images_for_record(record: dict[str, Any]) -> list[Path]:
    images = [
        Path(str(path))
        for path in record.get("rendered_slide_images", [])
        if str(path).strip()
    ]
    if images:
        return images
    preset_dir = Path(str(record.get("preset_dir") or ""))
    return _rendered_slide_images(preset_dir) if preset_dir else []


def _treatment_archetype_id(record: dict[str, Any], treatment_key: str) -> str:
    archetypes = (
        record.get("treatment_archetypes")
        if isinstance(record.get("treatment_archetypes"), dict)
        else {}
    )
    archetype = (
        archetypes.get(treatment_key)
        if isinstance(archetypes.get(treatment_key), dict)
        else {}
    )
    return str(archetype.get("archetype_id") or "").strip()


def _treatment_slide_image(record: dict[str, Any], treatment_key: str) -> dict[str, Any]:
    images = _rendered_images_for_record(record)
    if not images:
        return {}
    normalized = str(treatment_key or "").strip().lower()
    if normalized == "title":
        return {
            "slide_index": 1,
            "variant": "title",
            "path": str(images[0]),
            "archetype_id": _treatment_archetype_id(record, normalized),
        }
    trace_summary = (
        record.get("slide_recipe_trace_summary")
        if isinstance(record.get("slide_recipe_trace_summary"), dict)
        else {}
    )
    traces = trace_summary.get("traces") if isinstance(trace_summary.get("traces"), list) else []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        trace_key = str(trace.get("treatment_key") or "").strip().lower()
        if trace_key != normalized:
            continue
        try:
            slide_index = int(trace.get("slide_index") or 0)
        except (TypeError, ValueError):
            slide_index = 0
        if 1 <= slide_index <= len(images):
            return {
                "slide_index": slide_index,
                "variant": str(trace.get("variant") or ""),
                "path": str(images[slide_index - 1]),
                "archetype_id": _treatment_archetype_id(record, normalized),
                "recipe_signature_hash": str(trace.get("recipe_signature_hash") or ""),
            }
    return {}


def _treatment_contact_sheet_summary(
    records: list[dict[str, Any]],
    treatment_contact_sheets: dict[str, Path],
) -> dict[str, Any]:
    image_counts: dict[str, int] = {}
    missing_by_treatment: dict[str, list[str]] = {}
    slide_indices_by_preset: dict[str, dict[str, int]] = {}
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        image_counts[treatment_key] = 0
        missing: list[str] = []
        for record in records:
            preset = str(record.get("preset") or "")
            image_record = _treatment_slide_image(record, treatment_key)
            image_path = Path(str(image_record.get("path") or ""))
            if image_record and image_path.is_file():
                image_counts[treatment_key] += 1
                slide_indices_by_preset.setdefault(preset, {})[treatment_key] = int(
                    image_record.get("slide_index") or 0
                )
            else:
                missing.append(preset)
        if missing:
            missing_by_treatment[treatment_key] = missing
    sheet_fingerprints = {
        treatment_key: _file_fingerprint(path)
        for treatment_key, path in sorted(treatment_contact_sheets.items())
    }
    missing_sheets = [
        treatment_key
        for treatment_key in REQUIRED_CONTENT_TREATMENTS
        if not sheet_fingerprints.get(treatment_key, {}).get("exists")
        or not sheet_fingerprints.get(treatment_key, {}).get("sha256")
    ]
    expected_count = len(records)
    passed = (
        bool(records)
        and not missing_by_treatment
        and not missing_sheets
        and all(int(image_counts.get(key) or 0) == expected_count for key in REQUIRED_CONTENT_TREATMENTS)
    )
    return {
        "required_treatment_keys": list(REQUIRED_CONTENT_TREATMENTS),
        "expected_image_count_per_treatment": expected_count,
        "image_counts": image_counts,
        "missing_by_treatment": missing_by_treatment,
        "sheet_count": len(sheet_fingerprints),
        "missing_sheets": missing_sheets,
        "slide_indices_by_preset": slide_indices_by_preset,
        "sheet_fingerprints": sheet_fingerprints,
        "passed": passed,
    }


def _treatment_visual_diversity_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {
            "available": False,
            "reason": "pillow_unavailable",
            "required_treatment_keys": list(REQUIRED_CONTENT_TREATMENTS),
            "passed": False,
        }
    expected_count = len(records)
    by_treatment: dict[str, Any] = {}
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        signatures: list[dict[str, Any]] = []
        missing: list[str] = []
        for record in records:
            preset = str(record.get("preset") or "")
            image_record = _treatment_slide_image(record, treatment_key)
            image_path = Path(str(image_record.get("path") or ""))
            if not image_record or not image_path.is_file():
                missing.append(preset)
                continue
            signature = _image_visual_signature(image_path)
            signature.update(
                {
                    "preset": preset,
                    "treatment_key": treatment_key,
                    "slide_index": int(image_record.get("slide_index") or 0),
                    "variant": str(image_record.get("variant") or ""),
                    "archetype_id": str(image_record.get("archetype_id") or ""),
                }
            )
            signatures.append(signature)

        layout_pairwise: list[dict[str, Any]] = []
        available = [item for item in signatures if item.get("available")]
        for index, left in enumerate(available):
            for right in available[index + 1 :]:
                distance = _hash_distance(
                    str(left.get("layout_average_hash") or ""),
                    str(right.get("layout_average_hash") or ""),
                )
                bit_count = int(left.get("layout_bit_count") or right.get("layout_bit_count") or 0)
                layout_pairwise.append(
                    {
                        "left": left.get("preset"),
                        "right": right.get("preset"),
                        "distance": distance,
                        "normalized_distance": round(distance / bit_count, 4) if bit_count else None,
                    }
                )
        layout_pairwise.sort(key=lambda item: (float(item.get("normalized_distance") or 0), int(item.get("distance") or 0)))
        min_pair = layout_pairwise[0] if layout_pairwise else {}
        low_distance_pairs = [
            item
            for item in layout_pairwise
            if float(item.get("normalized_distance") or 0) < VISUAL_SIMILARITY_WARN_NORMALIZED_DISTANCE
        ][:8]
        thumb_hashes = [
            str(item.get("thumb_signature_sha256") or "")
            for item in available
            if str(item.get("thumb_signature_sha256") or "")
        ]
        layout_hashes = [
            str(item.get("layout_average_hash") or "")
            for item in available
            if str(item.get("layout_average_hash") or "")
        ]
        unique_layout_hash_count = len(set(layout_hashes))
        layout_unique_floor = min(
            expected_count,
            int(TREATMENT_LAYOUT_UNIQUE_FLOORS.get(treatment_key, 1) or 1),
        )
        nonblank_count = len([item for item in available if item.get("nonblank")])
        by_treatment[treatment_key] = {
            "image_count": len(signatures),
            "visual_signature_count": len(available),
            "nonblank_count": nonblank_count,
            "missing_presets": missing,
            "unique_thumb_signature_count": len(set(thumb_hashes)),
            "unique_layout_hash_count": unique_layout_hash_count,
            "unique_layout_hash_floor": layout_unique_floor,
            "min_layout_pairwise_distance": min_pair,
            "low_layout_distance_pairs": low_distance_pairs,
            "records": [
                {
                    "preset": item.get("preset"),
                    "slide_index": item.get("slide_index"),
                    "variant": item.get("variant"),
                    "archetype_id": item.get("archetype_id"),
                    "thumb_signature_sha256": item.get("thumb_signature_sha256"),
                    "layout_average_hash": item.get("layout_average_hash"),
                    "brightness_mean": item.get("brightness_mean"),
                    "brightness_stddev": item.get("brightness_stddev"),
                    "nonblank": item.get("nonblank"),
                }
                for item in available
            ],
            "passed": (
                len(signatures) == expected_count
                and len(available) == expected_count
                and nonblank_count == expected_count
                and len(set(thumb_hashes)) == expected_count
                and unique_layout_hash_count >= layout_unique_floor
                and not missing
            ),
        }
    failed_treatments = [
        treatment_key
        for treatment_key, summary in by_treatment.items()
        if not summary.get("passed")
    ]
    return {
        "available": True,
        "required_treatment_keys": list(REQUIRED_CONTENT_TREATMENTS),
        "expected_image_count_per_treatment": expected_count,
        "thumb_signature_algorithm": "rgb_quantized_thumbnail_sha256_v1",
        "thumb_signature_size": list(VISUAL_THUMB_SIGNATURE_SIZE),
        "layout_hash_algorithm": "average_hash_v1",
        "layout_hash_size": list(VISUAL_HASH_SIZE),
        "layout_unique_floors": {
            treatment_key: min(
                expected_count,
                int(TREATMENT_LAYOUT_UNIQUE_FLOORS.get(treatment_key, 1) or 1),
            )
            for treatment_key in REQUIRED_CONTENT_TREATMENTS
        },
        "similarity_warning_distance": VISUAL_SIMILARITY_WARN_NORMALIZED_DISTANCE,
        "by_treatment": by_treatment,
        "failed_treatments": failed_treatments,
        "passed": bool(records) and not failed_treatments,
    }


def _renderer_fields(record: dict[str, Any]) -> dict[str, str]:
    treatments = record.get("renderer_treatments") if isinstance(record.get("renderer_treatments"), dict) else {}
    fields = treatments.get("fields") if isinstance(treatments.get("fields"), dict) else {}
    return {
        str(key): str(value)
        for key, value in fields.items()
        if str(key).strip() and str(value).strip()
    }


def _footer_slide_image(record: dict[str, Any]) -> dict[str, Any]:
    images = record.get("rendered_slide_images") if isinstance(record.get("rendered_slide_images"), list) else []
    if not images:
        return {}
    slide_index = 2 if len(images) >= 2 else 1
    return {
        "path": str(images[slide_index - 1]),
        "slide_index": slide_index,
        "footer_mode": _renderer_fields(record).get("footer_mode", ""),
    }


def _footer_crop_signature(image_path: Path) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {"available": False, "reason": "pillow_unavailable"}
    if not image_path.is_file():
        return {"available": False, "reason": "missing_image", "path": str(image_path)}
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        crop_h = min(img.height, max(44, int(img.height * 0.12)))
        top = max(0, img.height - crop_h)
        crop = img.crop((0, top, img.width, img.height))
        thumb = crop.resize((320, 56))
        stat = ImageStat.Stat(crop.convert("L"))
        stddev = float(stat.stddev[0]) if stat.stddev else 0.0
        mean = float(stat.mean[0]) if stat.mean else 0.0
        return {
            "available": True,
            "path": str(image_path),
            "crop_box_px": [0, top, img.width, img.height],
            "crop_signature_sha256": hashlib.sha256(thumb.tobytes()).hexdigest(),
            "brightness_mean": round(mean, 3),
            "brightness_stddev": round(stddev, 3),
            "nonblank": stddev > 1.0,
        }


def _footer_contact_sheet_summary(records: list[dict[str, Any]], footer_contact: Path | None) -> dict[str, Any]:
    expected_count = len(records)
    sheet = _file_fingerprint(footer_contact) if footer_contact else {"path": "", "exists": False}
    mode_counts: dict[str, int] = {}
    missing: list[str] = []
    signatures: list[dict[str, Any]] = []
    for record in records:
        preset = str(record.get("preset") or "")
        footer_mode = _renderer_fields(record).get("footer_mode", "standard") or "standard"
        mode_counts[footer_mode] = mode_counts.get(footer_mode, 0) + 1
        image_record = _footer_slide_image(record)
        image_path = Path(str(image_record.get("path") or ""))
        signature = _footer_crop_signature(image_path)
        if not image_record or not image_path.is_file() or not signature.get("available"):
            missing.append(preset)
            continue
        signatures.append(
            {
                "preset": preset,
                "slide_index": int(image_record.get("slide_index") or 0),
                "footer_mode": footer_mode,
                "crop_signature_sha256": signature.get("crop_signature_sha256"),
                "brightness_mean": signature.get("brightness_mean"),
                "brightness_stddev": signature.get("brightness_stddev"),
                "nonblank": signature.get("nonblank"),
            }
        )
    nonblank_count = len([item for item in signatures if item.get("nonblank")])
    unique_signature_count = len(
        {
            str(item.get("crop_signature_sha256") or "")
            for item in signatures
            if str(item.get("crop_signature_sha256") or "")
        }
    )
    passed = (
        bool(records)
        and sheet.get("exists")
        and sheet.get("sha256")
        and not missing
        and len(signatures) == expected_count
        and nonblank_count == expected_count
        and unique_signature_count >= min(expected_count, 8)
        and int(mode_counts.get("source-line") or 0) > 0
        and int(mode_counts.get("standard") or 0) > 0
    )
    return {
        "expected_image_count": expected_count,
        "image_count": len(signatures),
        "nonblank_count": nonblank_count,
        "missing_presets": missing,
        "footer_mode_counts": dict(sorted(mode_counts.items())),
        "required_footer_modes": ["standard", "source-line"],
        "unique_crop_signature_count": unique_signature_count,
        "unique_crop_signature_floor": min(expected_count, 8),
        "sheet_fingerprint": sheet,
        "records": signatures,
        "passed": passed,
    }


def _make_footer_contact_sheet(outdir: Path, records: list[dict[str, Any]]) -> Path | None:
    if Image is None or ImageDraw is None:
        return None
    thumb_w, thumb_h = 300, 62
    label_h = 48
    header_h = 36
    gutter = 14
    cols = 4
    rows = max(1, (len(records) + cols - 1) // cols)
    font = ImageFont.load_default() if ImageFont else None
    sheet_w = cols * thumb_w + (cols + 1) * gutter
    sheet_h = header_h + rows * (thumb_h + label_h + gutter) + gutter
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#F8FAFC")
    draw = ImageDraw.Draw(sheet)
    draw.text((gutter, gutter), "footer chrome across presets", fill="#111827", font=font)
    for idx, record in enumerate(records):
        row_idx = idx // cols
        col_idx = idx % cols
        x = gutter + col_idx * (thumb_w + gutter)
        y = header_h + gutter + row_idx * (thumb_h + label_h + gutter)
        preset = str(record.get("preset") or "")
        fields = _renderer_fields(record)
        footer_mode = fields.get("footer_mode", "standard") or "standard"
        image_record = _footer_slide_image(record)
        slide_index = int(image_record.get("slide_index") or 0)
        draw.text((x, y), _compact_footer_item(preset, limit=38), fill="#111827", font=font)
        draw.text(
            (x, y + 14),
            _compact_footer_item(f"footer: {footer_mode}", limit=42),
            fill="#475569",
            font=font,
        )
        if slide_index:
            draw.text(
                (x, y + 28),
                _compact_footer_item(f"crop from s{slide_index}", limit=42),
                fill="#64748B",
                font=font,
            )
        image_path = Path(str(image_record.get("path") or ""))
        if image_record and image_path.is_file():
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                crop_h = min(img.height, max(44, int(img.height * 0.12)))
                crop = img.crop((0, max(0, img.height - crop_h), img.width, img.height))
                crop.thumbnail((thumb_w, thumb_h))
                canvas = Image.new("RGB", (thumb_w, thumb_h), "#FFFFFF")
                canvas.paste(crop, ((thumb_w - crop.width) // 2, (thumb_h - crop.height) // 2))
                sheet.paste(canvas, (x, y + label_h))
        else:
            draw.rectangle(
                [x, y + label_h, x + thumb_w, y + label_h + thumb_h],
                fill="#E2E8F0",
                outline="#CBD5E1",
            )
            draw.text((x + 12, y + label_h + 22), "missing render", fill="#475569", font=font)
    output = outdir / "style_reference_footer_contact_sheet.jpg"
    sheet.save(output, quality=88)
    return output


def _make_treatment_contact_sheets(outdir: Path, records: list[dict[str, Any]]) -> dict[str, Path]:
    if Image is None or ImageDraw is None:
        return {}
    thumb_w, thumb_h = 300, 169
    label_h = 58
    header_h = 36
    gutter = 14
    cols = 4
    rows = max(1, (len(records) + cols - 1) // cols)
    font = ImageFont.load_default() if ImageFont else None
    outputs: dict[str, Path] = {}
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        sheet_w = cols * thumb_w + (cols + 1) * gutter
        sheet_h = header_h + rows * (thumb_h + label_h + gutter) + gutter
        sheet = Image.new("RGB", (sheet_w, sheet_h), "#F8FAFC")
        draw = ImageDraw.Draw(sheet)
        draw.text(
            (gutter, gutter),
            f"{treatment_key} treatment across presets",
            fill="#111827",
            font=font,
        )
        for idx, record in enumerate(records):
            row_idx = idx // cols
            col_idx = idx % cols
            x = gutter + col_idx * (thumb_w + gutter)
            y = header_h + gutter + row_idx * (thumb_h + label_h + gutter)
            preset = str(record.get("preset") or "")
            image_record = _treatment_slide_image(record, treatment_key)
            archetype_id = str(image_record.get("archetype_id") or "").strip()
            slide_index = int(image_record.get("slide_index") or 0)
            variant = str(image_record.get("variant") or treatment_key).strip()
            draw.text((x, y), _compact_footer_item(preset, limit=38), fill="#111827", font=font)
            if archetype_id:
                draw.text(
                    (x, y + 14),
                    _compact_footer_item(archetype_id, limit=42),
                    fill="#475569",
                    font=font,
                )
            if slide_index:
                draw.text(
                    (x, y + 28),
                    _compact_footer_item(f"s{slide_index} / {variant}", limit=42),
                    fill="#64748B",
                    font=font,
                )
            image_path = Path(str(image_record.get("path") or ""))
            if image_record and image_path.is_file():
                with Image.open(image_path) as img:
                    img = img.convert("RGB")
                    img.thumbnail((thumb_w, thumb_h))
                    canvas = Image.new("RGB", (thumb_w, thumb_h), "#FFFFFF")
                    canvas.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
                    sheet.paste(canvas, (x, y + label_h))
            else:
                draw.rectangle(
                    [x, y + label_h, x + thumb_w, y + label_h + thumb_h],
                    fill="#E2E8F0",
                    outline="#CBD5E1",
                )
                draw.text((x + 12, y + label_h + 72), "missing render", fill="#475569", font=font)
        output = outdir / f"style_reference_treatment_{treatment_key}_contact_sheet.jpg"
        sheet.save(output, quality=88)
        outputs[treatment_key] = output
    return outputs


def _make_preset_contact_sheet(
    outdir: Path,
    record: dict[str, Any],
    use_case: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    preset = str(record.get("preset") or "").strip()
    treatment_keys = [
        str(item).strip().lower()
        for item in config.get("treatment_keys", [])
        if str(item).strip().lower() in REQUIRED_CONTENT_TREATMENTS
    ]
    label = str(config.get("label") or use_case).strip() or use_case
    try:
        cols = max(1, int(config.get("columns") or 2))
    except (TypeError, ValueError):
        cols = 2
    cols = min(cols, max(1, len(treatment_keys) or 1))
    expected_count = len(treatment_keys)
    output_dir = outdir / "preset_contact_collections" / preset
    output = output_dir / f"{use_case}_contact_sheet.jpg"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata: dict[str, Any] = {
        "collection_version": PRESET_CONTACT_COLLECTION_VERSION,
        "preset": preset,
        "use_case": use_case,
        "label": label,
        "path": str(output),
        "treatment_keys": treatment_keys,
        "expected_image_count": expected_count,
        "image_count": 0,
        "missing_treatment_keys": [],
        "columns": cols,
        "renderer_fields": _renderer_fields(record),
    }
    if Image is None or ImageDraw is None:
        metadata.update({"available": False, "reason": "pillow_unavailable"})
        return metadata

    thumb_w, thumb_h = 340, 191
    label_h = 58
    header_h = 58
    gutter = 16
    rows = max(1, (expected_count + cols - 1) // cols)
    sheet_w = cols * thumb_w + (cols + 1) * gutter
    sheet_h = header_h + rows * (thumb_h + label_h + gutter) + gutter
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#F8FAFC")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default() if ImageFont else None
    fields = _renderer_fields(record)
    draw.text((gutter, gutter), f"{preset}: {label}", fill="#111827", font=font)
    subtitle = (
        f"title {fields.get('title_layout', '-')} / "
        f"footer {fields.get('footer_mode', '-')} / "
        f"chart {fields.get('chart_treatment', '-')}"
    )
    draw.text((gutter, gutter + 18), _compact_footer_item(subtitle, limit=110), fill="#475569", font=font)

    image_count = 0
    missing: list[str] = []
    tile_records: list[dict[str, Any]] = []
    for idx, treatment_key in enumerate(treatment_keys):
        row_idx = idx // cols
        col_idx = idx % cols
        x = gutter + col_idx * (thumb_w + gutter)
        y = header_h + gutter + row_idx * (thumb_h + label_h + gutter)
        image_record = _treatment_slide_image(record, treatment_key)
        archetype_id = str(image_record.get("archetype_id") or "").strip()
        slide_index = int(image_record.get("slide_index") or 0)
        variant = str(image_record.get("variant") or treatment_key).strip() or treatment_key
        label_line = treatment_key.replace("_", " ")
        draw.text((x, y), _compact_footer_item(label_line, limit=44), fill="#111827", font=font)
        if archetype_id:
            draw.text(
                (x, y + 14),
                _compact_footer_item(archetype_id, limit=46),
                fill="#475569",
                font=font,
            )
        if slide_index:
            draw.text(
                (x, y + 28),
                _compact_footer_item(f"s{slide_index} / {variant}", limit=46),
                fill="#64748B",
                font=font,
            )
        image_path = Path(str(image_record.get("path") or ""))
        if image_record and image_path.is_file():
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                img.thumbnail((thumb_w, thumb_h))
                canvas = Image.new("RGB", (thumb_w, thumb_h), "#FFFFFF")
                canvas.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
                sheet.paste(canvas, (x, y + label_h))
            image_count += 1
            tile_records.append(
                {
                    "treatment_key": treatment_key,
                    "slide_index": slide_index,
                    "variant": variant,
                    "archetype_id": archetype_id,
                    "path": str(image_path),
                }
            )
        else:
            missing.append(treatment_key)
            draw.rectangle(
                [x, y + label_h, x + thumb_w, y + label_h + thumb_h],
                fill="#E2E8F0",
                outline="#CBD5E1",
            )
            draw.text((x + 14, y + label_h + 82), "missing render", fill="#475569", font=font)

    sheet.save(output, quality=88)
    metadata.update(
        {
            "available": True,
            "image_count": image_count,
            "missing_treatment_keys": missing,
            "tile_records": tile_records,
            "fingerprint": _file_fingerprint(output),
        }
    )
    return metadata


def _make_preset_contact_collections(outdir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "collection_version": PRESET_CONTACT_COLLECTION_VERSION,
        "root": str(outdir / "preset_contact_collections"),
        "required_use_cases": list(PRESET_CONTACT_COLLECTION_USE_CASES),
        "use_case_definitions": PRESET_CONTACT_COLLECTION_USE_CASES,
        "preset_count": len(records),
        "presets": {},
        "sheet_count": 0,
    }
    if Image is None or ImageDraw is None:
        manifest.update({"available": False, "reason": "pillow_unavailable"})
        return manifest
    presets: dict[str, Any] = {}
    sheet_count = 0
    for record in records:
        preset = str(record.get("preset") or "").strip()
        if not preset:
            continue
        use_cases: dict[str, Any] = {}
        for use_case, config in PRESET_CONTACT_COLLECTION_USE_CASES.items():
            metadata = _make_preset_contact_sheet(outdir, record, use_case, config)
            use_cases[use_case] = metadata
            if metadata.get("fingerprint", {}).get("exists"):
                sheet_count += 1
        presets[preset] = {
            "preset": preset,
            "directory": str(outdir / "preset_contact_collections" / preset),
            "use_cases": use_cases,
        }
    manifest["available"] = True
    manifest["presets"] = presets
    manifest["sheet_count"] = sheet_count
    return manifest


def _preset_contact_collection_summary(
    records: list[dict[str, Any]],
    preset_contact_collections: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest = preset_contact_collections if isinstance(preset_contact_collections, dict) else {}
    required_use_cases = list(PRESET_CONTACT_COLLECTION_USE_CASES)
    expected_sheet_count = len(records) * len(required_use_cases)
    if not manifest:
        return {
            "collection_version": "",
            "expected_collection_version": PRESET_CONTACT_COLLECTION_VERSION,
            "available": False,
            "required_use_cases": required_use_cases,
            "expected_sheet_count": expected_sheet_count,
            "sheet_count": 0,
            "passed": False,
        }
    preset_entries = manifest.get("presets") if isinstance(manifest.get("presets"), dict) else {}
    missing_presets: list[str] = []
    missing_use_cases_by_preset: dict[str, list[str]] = {}
    missing_treatments_by_preset: dict[str, dict[str, list[str]]] = {}
    image_counts_by_preset: dict[str, dict[str, int]] = {}
    sheet_fingerprints: dict[str, dict[str, dict[str, Any]]] = {}

    for record in records:
        preset = str(record.get("preset") or "").strip()
        entry = preset_entries.get(preset) if isinstance(preset_entries.get(preset), dict) else {}
        if not entry:
            missing_presets.append(preset)
            missing_use_cases_by_preset[preset] = list(required_use_cases)
            continue
        use_cases = entry.get("use_cases") if isinstance(entry.get("use_cases"), dict) else {}
        for use_case in required_use_cases:
            config = PRESET_CONTACT_COLLECTION_USE_CASES.get(use_case, {})
            expected_treatments = [
                str(item).strip().lower()
                for item in config.get("treatment_keys", [])
                if str(item).strip().lower() in REQUIRED_CONTENT_TREATMENTS
            ]
            metadata = use_cases.get(use_case) if isinstance(use_cases.get(use_case), dict) else {}
            if not metadata:
                missing_use_cases_by_preset.setdefault(preset, []).append(use_case)
                continue
            image_counts_by_preset.setdefault(preset, {})[use_case] = int(metadata.get("image_count") or 0)
            missing_treatments = [
                str(item)
                for item in metadata.get("missing_treatment_keys", [])
                if str(item).strip()
            ]
            if missing_treatments:
                missing_treatments_by_preset.setdefault(preset, {})[use_case] = missing_treatments
            path = Path(str(metadata.get("path") or ""))
            fingerprint = (
                metadata.get("fingerprint")
                if isinstance(metadata.get("fingerprint"), dict)
                else _file_fingerprint(path)
            )
            sheet_fingerprints.setdefault(preset, {})[use_case] = fingerprint
            if not fingerprint.get("exists") or not fingerprint.get("sha256"):
                missing_use_cases_by_preset.setdefault(preset, []).append(use_case)
            if int(metadata.get("expected_image_count") or 0) != len(expected_treatments):
                missing_treatments_by_preset.setdefault(preset, {})[use_case] = expected_treatments
            elif int(metadata.get("image_count") or 0) != len(expected_treatments):
                missing_treatments_by_preset.setdefault(preset, {})[use_case] = missing_treatments or expected_treatments

    sheet_count = int(manifest.get("sheet_count") or 0)
    passed = (
        bool(records)
        and manifest.get("collection_version") == PRESET_CONTACT_COLLECTION_VERSION
        and bool(manifest.get("available"))
        and sheet_count == expected_sheet_count
        and not missing_presets
        and not missing_use_cases_by_preset
        and not missing_treatments_by_preset
    )
    return {
        "collection_version": manifest.get("collection_version"),
        "expected_collection_version": PRESET_CONTACT_COLLECTION_VERSION,
        "available": bool(manifest.get("available")),
        "required_use_cases": required_use_cases,
        "use_case_definitions": PRESET_CONTACT_COLLECTION_USE_CASES,
        "expected_preset_count": len(records),
        "preset_count": len(preset_entries),
        "expected_sheet_count": expected_sheet_count,
        "sheet_count": sheet_count,
        "missing_presets": missing_presets,
        "missing_use_cases_by_preset": missing_use_cases_by_preset,
        "missing_treatments_by_preset": missing_treatments_by_preset,
        "image_counts_by_preset": image_counts_by_preset,
        "sheet_fingerprints": sheet_fingerprints,
        "passed": passed,
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build synthetic style-reference gallery decks.")
    parser.add_argument("--outdir", default="decks/style-reference-gallery-20260620")
    parser.add_argument("--presets", nargs="*", default=[], help="Optional subset of presets")
    parser.add_argument("--build", action="store_true", help="Build PPTX files")
    parser.add_argument("--qa", action="store_true", help="Build and run render-free QA")
    parser.add_argument("--render", action="store_true", help="Build and render decks to images/contact sheet")
    parser.add_argument("--dpi", type=int, default=110)
    return parser.parse_args()


def main() -> int:
    args = _args()
    outdir = (ROOT / args.outdir).resolve() if not Path(args.outdir).is_absolute() else Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    presets = args.presets or _preset_names()
    records: list[dict[str, Any]] = []

    for preset in presets:
        reference = preset_style_reference(preset)
        storyboard = _storyboard(reference)
        missing = [key for key in REQUIRED_CONTENT_TREATMENTS if key not in reference.get("content_treatments", {})]
        if missing:
            raise SystemExit(f"{preset} missing content treatments: {', '.join(missing)}")
        preset_dir = outdir / preset
        asset_dir = preset_dir / "assets"
        tokens = _preset_tokens(preset)
        asset_paths = _write_synthetic_figures(asset_dir, preset, tokens)
        outline = preset_dir / "outline.json"
        pptx = preset_dir / f"{preset}.pptx"
        qa_report = preset_dir / "qa" / "report.json"
        render_dir = preset_dir / "renders"
        _write_outline(outline, preset, asset_paths)

        build_cmd = [
            "node",
            "scripts/build_deck_pptxgenjs.js",
            "--outline",
            str(outline),
            "--output",
            str(pptx),
            "--style-preset",
            preset,
        ]
        build_stdout = ""
        if args.build or args.qa or args.render:
            build_stdout = _run(build_cmd)

        qa_cmd: list[str] = []
        qa_stdout = ""
        if args.qa:
            qa_cmd = [
                sys.executable,
                "scripts/qa_gate.py",
                "--input",
                str(pptx),
                "--outdir",
                str(preset_dir / "qa"),
                "--style-preset",
                preset,
                "--strict-geometry",
                "--skip-manual-review",
                "--skip-render",
                "--fail-on-design-warnings",
                "--outline",
                str(outline),
                "--report",
                str(qa_report),
            ]
            qa_stdout = _run(qa_cmd)

        render_cmd: list[str] = []
        render_stdout = ""
        if args.render:
            render_cmd = [
                sys.executable,
                "scripts/render_slides.py",
                "--input",
                str(pptx),
                "--outdir",
                str(render_dir),
                "--dpi",
                str(args.dpi),
                "--format",
                "jpeg",
            ]
            render_stdout = _run(render_cmd)

        outline_summary = _outline_summary(outline)
        layout_playbook = (
            reference.get("layout_playbook")
            if isinstance(reference.get("layout_playbook"), dict)
            else {}
        )
        content_recipe_summary = _content_recipe_summary(reference)
        structural_motif = (
            reference.get("structural_motif_library")
            if isinstance(reference.get("structural_motif_library"), dict)
            else {}
        )
        style_metric_profile = (
            reference.get("style_metric_profile")
            if isinstance(reference.get("style_metric_profile"), dict)
            else {}
        )
        qa_summary = _qa_summary(qa_report) if args.qa else {}
        rendered_images = [str(path) for path in _rendered_slide_images(preset_dir)] if args.render else []
        records.append(
            {
                "gallery_version": GALLERY_VERSION,
                "preset": preset,
                "preset_dir": str(preset_dir),
                "style_reference_id": reference.get("reference_id"),
                "style_reference_name": reference.get("reference_name"),
                "source_status": reference.get("source_status"),
                "structural_motif_library": structural_motif,
                "motif_library_version": structural_motif.get("motif_library_version"),
                "structural_motif_signature": structural_motif.get("motif_signature"),
                "style_metric_profile": style_metric_profile,
                "style_metric_signature": style_metric_profile.get("metric_signature"),
                "background_structure": structural_motif.get("background_structure"),
                "layout_motifs": (
                    structural_motif.get("layout_motifs")
                    if isinstance(structural_motif.get("layout_motifs"), list)
                    else []
                ),
                "example_storyboard_version": storyboard.get("storyboard_version"),
                "example_storyboard_topic": storyboard.get("topic"),
                "example_storyboard_title": storyboard.get("title"),
                "style_source_intake": reference.get("style_source_intake", {}),
                "style_source_ids": (
                    reference.get("style_source_intake", {}).get("source_ids")
                    if isinstance(reference.get("style_source_intake"), dict)
                    else []
                ),
                "layout_playbook_version": (
                    layout_playbook.get("playbook_version")
                ),
                "preferred_variants": (
                    layout_playbook.get("preferred_variants")
                    if isinstance(layout_playbook.get("preferred_variants"), list)
                    else []
                ),
                "gallery_showcase_variants": (
                    layout_playbook.get("gallery_showcase_variants")
                    if isinstance(layout_playbook.get("gallery_showcase_variants"), list)
                    else []
                ),
                "treatment_variant_map": (
                    layout_playbook.get("treatment_variant_map")
                    if isinstance(layout_playbook.get("treatment_variant_map"), dict)
                    else {}
                ),
                "treatment_archetypes": (
                    layout_playbook.get("treatment_archetypes")
                    if isinstance(layout_playbook.get("treatment_archetypes"), dict)
                    else {}
                ),
                "content_treatments": sorted(reference.get("content_treatments", {})),
                "content_recipe_summary": content_recipe_summary,
                "slide_count": outline_summary.get("slide_count"),
                "content_slide_count": outline_summary.get("content_slide_count"),
                "variant_sequence": outline_summary.get("variant_sequence"),
                "variant_counts": outline_summary.get("variant_counts"),
                "chart_treatment_sequence": outline_summary.get("chart_treatment_sequence"),
                "table_treatment_sequence": outline_summary.get("table_treatment_sequence"),
                "renderer_treatments": outline_summary.get("renderer_treatments"),
                "treatment_buckets": outline_summary.get("treatment_buckets"),
                "slide_recipe_trace_summary": outline_summary.get("slide_recipe_trace_summary"),
                "outline": str(outline),
                "pptx": str(pptx),
                "pptx_fingerprint": _pptx_fingerprint(pptx),
                "qa_report": str(qa_report) if args.qa else "",
                "qa_summary": qa_summary,
                "render_dir": str(render_dir) if args.render else "",
                "rendered_slide_images": rendered_images,
                "rendered_slide_count": len(rendered_images),
                "asset_paths": asset_paths,
                "build_command": build_cmd,
                "qa_command": qa_cmd,
                "render_command": render_cmd,
                "build_stdout_tail": build_stdout[-1200:],
                "qa_stdout_tail": qa_stdout[-1200:],
                "render_stdout_tail": render_stdout[-1200:],
            }
        )

    contact = _make_contact_sheet(outdir, records) if args.render else None
    structure_contact = _make_structure_contact_sheet(outdir, records) if args.render else None
    footer_contact = _make_footer_contact_sheet(outdir, records) if args.render else None
    treatment_contacts = _make_treatment_contact_sheets(outdir, records) if args.render else {}
    preset_contact_collections = _make_preset_contact_collections(outdir, records) if args.render else {}
    qa_summaries = [record.get("qa_summary") for record in records if isinstance(record.get("qa_summary"), dict)]
    qa_totals = {
        "record_count": len(qa_summaries),
        "passed_render_free_gate_count": len([item for item in qa_summaries if item.get("passed_render_free_gate")]),
        "overflow_count": sum(int(item.get("overflow_count") or 0) for item in qa_summaries),
        "overlap_count": sum(int(item.get("overlap_count") or 0) for item in qa_summaries),
        "geometry_error_count": sum(int(item.get("geometry_error_count") or 0) for item in qa_summaries),
        "design_error_count": sum(int(item.get("design_error_count") or 0) for item in qa_summaries),
        "design_warning_count": sum(int(item.get("design_warning_count") or 0) for item in qa_summaries),
        "visual_warning_count": sum(int(item.get("visual_warning_count") or 0) for item in qa_summaries),
        "placeholder_count": sum(int(item.get("placeholder_count") or 0) for item in qa_summaries),
    }
    release_evidence = _release_evidence(
        outdir=outdir,
        records=records,
        qa_totals=qa_totals,
        contact=contact,
        structure_contact=structure_contact,
        footer_contact=footer_contact,
        treatment_contact_sheets=treatment_contacts,
        preset_contact_collections=preset_contact_collections,
    )
    release_evidence_path = outdir / "release_evidence.json"
    release_evidence_path.write_text(json.dumps(release_evidence, indent=2) + "\n", encoding="utf-8")
    summary = {
        "gallery_version": GALLERY_VERSION,
        "outdir": str(outdir),
        "preset_count": len(presets),
        "presets": presets,
        "qa_totals": qa_totals,
        "rendered_contact_sheet": str(contact) if contact else "",
        "rendered_structure_contact_sheet": str(structure_contact) if structure_contact else "",
        "rendered_footer_contact_sheet": str(footer_contact) if footer_contact else "",
        "rendered_treatment_contact_sheets": {
            treatment_key: str(path) for treatment_key, path in sorted(treatment_contacts.items())
        },
        "preset_contact_collections": preset_contact_collections,
        "release_evidence": release_evidence,
        "release_evidence_path": str(release_evidence_path),
        "records": records,
        "contact_sheet": str(contact) if contact else "",
        "structure_contact_sheet": str(structure_contact) if structure_contact else "",
        "footer_contact_sheet": str(footer_contact) if footer_contact else "",
        "treatment_contact_sheets": {
            treatment_key: str(path) for treatment_key, path in sorted(treatment_contacts.items())
        },
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
