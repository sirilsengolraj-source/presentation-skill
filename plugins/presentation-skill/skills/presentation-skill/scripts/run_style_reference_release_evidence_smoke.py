#!/usr/bin/env python3
"""Rendered smoke for style-reference release evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from design_tokens import PRESETS
from build_style_reference_gallery import (
    PRESET_CONTACT_COLLECTION_USE_CASES,
    PRESET_CONTACT_COLLECTION_VERSION,
)
from style_reference_catalog import (
    CONTENT_RECIPE_LIBRARY_VERSION,
    REQUIRED_CONTENT_TREATMENTS,
    STYLE_METRIC_PROFILE_VERSION,
    STRUCTURAL_MOTIF_LIBRARY_VERSION,
)


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build rendered all-preset style-reference release evidence.")
    parser.add_argument("--workspace-root", default="", help="Optional output root. Defaults to a temp directory.")
    parser.add_argument("--keep-workspace", action="store_true", help="Keep the temporary root after a passing run.")
    parser.add_argument("--dpi", type=int, default=90, help="Render DPI for the contact-sheet evidence smoke.")
    return parser.parse_args()


def main() -> int:
    args = _args()
    repo = Path(__file__).resolve().parent.parent
    created_temp = not bool(str(args.workspace_root).strip())
    root = (
        Path(args.workspace_root).expanduser().resolve()
        if str(args.workspace_root).strip()
        else Path(tempfile.mkdtemp(prefix="presentation-skill-style-release-"))
    )
    failures: list[dict[str, Any]] = []
    if root.exists() and any(root.iterdir()):
        print(
            json.dumps(
                {
                    "passed": False,
                    "workspace_root": str(root),
                    "failures": [{"reason": "workspace_root_must_be_empty"}],
                },
                indent=2,
            )
        )
        return 1
    root.mkdir(parents=True, exist_ok=True)
    outdir = root / "gallery"

    cmd = [
        sys.executable,
        str(repo / "scripts" / "build_style_reference_gallery.py"),
        "--outdir",
        str(outdir),
        "--build",
        "--qa",
        "--render",
        "--dpi",
        str(args.dpi),
    ]
    result = _run(cmd, cwd=repo)
    if result.returncode != 0:
        failures.append(
            {
                "reason": "build_release_evidence_failed",
                "returncode": result.returncode,
                "stdout_tail": result.stdout[-2400:],
            }
        )

    summary = _load_json(outdir / "summary.json")
    evidence_path = Path(str(summary.get("release_evidence_path") or outdir / "release_evidence.json"))
    evidence = _load_json(evidence_path)
    records = summary.get("records") if isinstance(summary.get("records"), list) else []
    qa_totals = evidence.get("qa_totals") if isinstance(evidence.get("qa_totals"), dict) else {}
    content_summary = (
        evidence.get("content_signature_summary")
        if isinstance(evidence.get("content_signature_summary"), dict)
        else {}
    )
    visual = evidence.get("visual_diversity") if isinstance(evidence.get("visual_diversity"), dict) else {}
    renderer = (
        evidence.get("renderer_treatment_summary")
        if isinstance(evidence.get("renderer_treatment_summary"), dict)
        else {}
    )
    recipe_summary = (
        evidence.get("content_recipe_library_summary")
        if isinstance(evidence.get("content_recipe_library_summary"), dict)
        else {}
    )
    structural_summary = (
        evidence.get("structural_playbook_summary")
        if isinstance(evidence.get("structural_playbook_summary"), dict)
        else {}
    )
    motif_summary = (
        evidence.get("structural_motif_summary")
        if isinstance(evidence.get("structural_motif_summary"), dict)
        else {}
    )
    metric_summary = (
        evidence.get("style_metric_profile_summary")
        if isinstance(evidence.get("style_metric_profile_summary"), dict)
        else {}
    )
    contact = evidence.get("contact_sheet") if isinstance(evidence.get("contact_sheet"), dict) else {}
    structure_contact = (
        evidence.get("structure_contact_sheet")
        if isinstance(evidence.get("structure_contact_sheet"), dict)
        else {}
    )
    footer_contact = (
        evidence.get("footer_contact_sheet")
        if isinstance(evidence.get("footer_contact_sheet"), dict)
        else {}
    )
    footer_contact_summary = (
        evidence.get("footer_contact_sheet_summary")
        if isinstance(evidence.get("footer_contact_sheet_summary"), dict)
        else {}
    )
    treatment_contacts = (
        evidence.get("treatment_contact_sheets")
        if isinstance(evidence.get("treatment_contact_sheets"), dict)
        else {}
    )
    treatment_contact_summary = (
        evidence.get("treatment_contact_sheet_summary")
        if isinstance(evidence.get("treatment_contact_sheet_summary"), dict)
        else {}
    )
    treatment_visual = (
        evidence.get("treatment_visual_diversity")
        if isinstance(evidence.get("treatment_visual_diversity"), dict)
        else {}
    )
    preset_collections = (
        evidence.get("preset_contact_collections")
        if isinstance(evidence.get("preset_contact_collections"), dict)
        else {}
    )
    preset_collection_summary = (
        evidence.get("preset_contact_collection_summary")
        if isinstance(evidence.get("preset_contact_collection_summary"), dict)
        else {}
    )

    if summary.get("gallery_version") != "style_reference_gallery_v1":
        failures.append({"reason": "summary_gallery_version_mismatch", "summary": summary.get("gallery_version")})
    if summary.get("preset_count") != len(PRESETS) or len(records) != len(PRESETS):
        failures.append(
            {
                "reason": "summary_preset_count_mismatch",
                "preset_count": summary.get("preset_count"),
                "record_count": len(records),
            }
        )
    if evidence.get("evidence_version") != "style_reference_release_evidence_v1":
        failures.append({"reason": "release_evidence_version_mismatch", "evidence_version": evidence.get("evidence_version")})
    if not evidence.get("passed_release_evidence_gate"):
        failures.append({"reason": "release_evidence_gate_failed", "release_evidence": evidence})
    if not contact.get("exists") or not contact.get("sha256"):
        failures.append({"reason": "contact_sheet_fingerprint_missing", "contact_sheet": contact})
    if not structure_contact.get("exists") or not structure_contact.get("sha256"):
        failures.append(
            {
                "reason": "structure_contact_sheet_fingerprint_missing",
                "structure_contact_sheet": structure_contact,
            }
        )
    if not footer_contact.get("exists") or not footer_contact.get("sha256"):
        failures.append(
            {
                "reason": "footer_contact_sheet_fingerprint_missing",
                "footer_contact_sheet": footer_contact,
            }
        )
    if not footer_contact_summary.get("passed"):
        failures.append(
            {
                "reason": "footer_contact_sheet_summary_failed",
                "footer_contact_sheet_summary": footer_contact_summary,
            }
        )
    footer_mode_counts = (
        footer_contact_summary.get("footer_mode_counts")
        if isinstance(footer_contact_summary.get("footer_mode_counts"), dict)
        else {}
    )
    for footer_mode in ("standard", "source-line"):
        if int(footer_mode_counts.get(footer_mode) or 0) <= 0:
            failures.append(
                {
                    "reason": "footer_mode_missing_from_contact_sheet",
                    "footer_mode": footer_mode,
                    "footer_mode_counts": footer_mode_counts,
                }
            )
    for field in ("image_count", "nonblank_count"):
        if int(footer_contact_summary.get(field) or 0) != len(PRESETS):
            failures.append(
                {
                    "reason": "footer_contact_count_mismatch",
                    "field": field,
                    "expected": len(PRESETS),
                    "footer_contact_sheet_summary": footer_contact_summary,
                }
            )
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        sheet = treatment_contacts.get(treatment_key) if isinstance(treatment_contacts.get(treatment_key), dict) else {}
        if not sheet.get("exists") or not sheet.get("sha256"):
            failures.append(
                {
                    "reason": "treatment_contact_sheet_fingerprint_missing",
                    "treatment_key": treatment_key,
                    "treatment_contact_sheet": sheet,
                }
            )
    if not treatment_contact_summary.get("passed"):
        failures.append(
            {
                "reason": "treatment_contact_sheet_summary_failed",
                "treatment_contact_sheet_summary": treatment_contact_summary,
            }
        )
    if preset_collections.get("collection_version") != PRESET_CONTACT_COLLECTION_VERSION:
        failures.append(
            {
                "reason": "preset_contact_collection_version_mismatch",
                "preset_contact_collections": preset_collections,
            }
        )
    if not preset_collection_summary.get("passed"):
        failures.append(
            {
                "reason": "preset_contact_collection_summary_failed",
                "preset_contact_collection_summary": preset_collection_summary,
            }
        )
    if preset_collection_summary.get("collection_version") != PRESET_CONTACT_COLLECTION_VERSION:
        failures.append(
            {
                "reason": "preset_contact_collection_summary_version_mismatch",
                "preset_contact_collection_summary": preset_collection_summary,
            }
        )
    required_use_cases = set(PRESET_CONTACT_COLLECTION_USE_CASES)
    if set(preset_collection_summary.get("required_use_cases") or []) != required_use_cases:
        failures.append(
            {
                "reason": "preset_contact_required_use_cases_mismatch",
                "preset_contact_collection_summary": preset_collection_summary,
            }
        )
    expected_preset_sheets = len(PRESETS) * len(required_use_cases)
    if int(preset_collection_summary.get("sheet_count") or 0) != expected_preset_sheets:
        failures.append(
            {
                "reason": "preset_contact_sheet_count_mismatch",
                "expected": expected_preset_sheets,
                "preset_contact_collection_summary": preset_collection_summary,
            }
        )
    if int(preset_collection_summary.get("preset_count") or 0) != len(PRESETS):
        failures.append(
            {
                "reason": "preset_contact_preset_count_mismatch",
                "expected": len(PRESETS),
                "preset_contact_collection_summary": preset_collection_summary,
            }
        )
    sheet_fingerprints = (
        preset_collection_summary.get("sheet_fingerprints")
        if isinstance(preset_collection_summary.get("sheet_fingerprints"), dict)
        else {}
    )
    image_counts_by_preset = (
        preset_collection_summary.get("image_counts_by_preset")
        if isinstance(preset_collection_summary.get("image_counts_by_preset"), dict)
        else {}
    )
    for preset in PRESETS:
        preset_fingerprints = (
            sheet_fingerprints.get(preset)
            if isinstance(sheet_fingerprints.get(preset), dict)
            else {}
        )
        preset_counts = (
            image_counts_by_preset.get(preset)
            if isinstance(image_counts_by_preset.get(preset), dict)
            else {}
        )
        for use_case, config in PRESET_CONTACT_COLLECTION_USE_CASES.items():
            fingerprint = (
                preset_fingerprints.get(use_case)
                if isinstance(preset_fingerprints.get(use_case), dict)
                else {}
            )
            if not fingerprint.get("exists") or not fingerprint.get("sha256"):
                failures.append(
                    {
                        "reason": "preset_contact_sheet_fingerprint_missing",
                        "preset": preset,
                        "use_case": use_case,
                        "fingerprint": fingerprint,
                    }
                )
            expected_images = len(config.get("treatment_keys", []))
            if int(preset_counts.get(use_case) or 0) != expected_images:
                failures.append(
                    {
                        "reason": "preset_contact_image_count_mismatch",
                        "preset": preset,
                        "use_case": use_case,
                        "expected": expected_images,
                        "image_counts": preset_counts,
                    }
                )
    if set(treatment_contact_summary.get("required_treatment_keys") or []) != set(REQUIRED_CONTENT_TREATMENTS):
        failures.append(
            {
                "reason": "treatment_contact_required_keys_mismatch",
                "treatment_contact_sheet_summary": treatment_contact_summary,
            }
        )
    image_counts = (
        treatment_contact_summary.get("image_counts")
        if isinstance(treatment_contact_summary.get("image_counts"), dict)
        else {}
    )
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        if int(image_counts.get(treatment_key) or 0) != len(PRESETS):
            failures.append(
                {
                    "reason": "treatment_contact_image_count_mismatch",
                    "treatment_key": treatment_key,
                    "expected": len(PRESETS),
                    "image_counts": image_counts,
                }
            )
    if not treatment_visual.get("available") or not treatment_visual.get("passed"):
        failures.append(
            {
                "reason": "treatment_visual_diversity_failed",
                "treatment_visual_diversity": treatment_visual,
            }
        )
    if set(treatment_visual.get("required_treatment_keys") or []) != set(REQUIRED_CONTENT_TREATMENTS):
        failures.append(
            {
                "reason": "treatment_visual_required_keys_mismatch",
                "treatment_visual_diversity": treatment_visual,
            }
        )
    treatment_visual_by_key = (
        treatment_visual.get("by_treatment")
        if isinstance(treatment_visual.get("by_treatment"), dict)
        else {}
    )
    treatment_layout_unique_floors = (
        treatment_visual.get("layout_unique_floors")
        if isinstance(treatment_visual.get("layout_unique_floors"), dict)
        else {}
    )
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        visual_summary = (
            treatment_visual_by_key.get(treatment_key)
            if isinstance(treatment_visual_by_key.get(treatment_key), dict)
            else {}
        )
        for field in ("image_count", "visual_signature_count", "nonblank_count", "unique_thumb_signature_count"):
            if int(visual_summary.get(field) or 0) != len(PRESETS):
                failures.append(
                    {
                        "reason": "treatment_visual_count_mismatch",
                        "treatment_key": treatment_key,
                        "field": field,
                        "expected": len(PRESETS),
                        "visual_summary": visual_summary,
                    }
                )
        if visual_summary.get("missing_presets"):
            failures.append(
                {
                    "reason": "treatment_visual_missing_presets",
                    "treatment_key": treatment_key,
                    "visual_summary": visual_summary,
                }
            )
        layout_floor = int(
            visual_summary.get("unique_layout_hash_floor")
            or treatment_layout_unique_floors.get(treatment_key)
            or 0
        )
        if layout_floor and int(visual_summary.get("unique_layout_hash_count") or 0) < layout_floor:
            failures.append(
                {
                    "reason": "treatment_visual_layout_unique_count_below_floor",
                    "treatment_key": treatment_key,
                    "minimum": layout_floor,
                    "visual_summary": visual_summary,
                }
            )
    if int(qa_totals.get("passed_render_free_gate_count") or 0) != len(PRESETS):
        failures.append({"reason": "qa_gate_count_mismatch", "qa_totals": qa_totals})
    for key in (
        "overflow_count",
        "overlap_count",
        "geometry_error_count",
        "design_error_count",
        "design_warning_count",
        "visual_warning_count",
        "placeholder_count",
    ):
        if int(qa_totals.get(key) or 0) != 0:
            failures.append({"reason": "qa_totals_nonzero", "key": key, "value": qa_totals.get(key)})
    if content_summary.get("unique_signature_count") != len(PRESETS):
        failures.append({"reason": "content_signature_count_mismatch", "content_signature_summary": content_summary})
    if not content_summary.get("unique_first_four_content_signatures"):
        failures.append({"reason": "content_signatures_not_unique", "content_signature_summary": content_summary})
    if renderer.get("unique_signature_count") != len(PRESETS) or not renderer.get("passed"):
        failures.append({"reason": "renderer_treatment_diversity_failed", "renderer_treatment_summary": renderer})
    if recipe_summary.get("library_version") != CONTENT_RECIPE_LIBRARY_VERSION:
        failures.append({"reason": "content_recipe_library_version_mismatch", "content_recipe_library_summary": recipe_summary})
    if recipe_summary.get("unique_signature_count") != len(PRESETS) or not recipe_summary.get("passed"):
        failures.append({"reason": "content_recipe_library_diversity_failed", "content_recipe_library_summary": recipe_summary})
    if set(recipe_summary.get("required_treatment_keys") or []) != set(REQUIRED_CONTENT_TREATMENTS):
        failures.append({"reason": "content_recipe_required_keys_mismatch", "content_recipe_library_summary": recipe_summary})
    if recipe_summary.get("missing_by_preset") or recipe_summary.get("invalid_by_preset"):
        failures.append({"reason": "content_recipe_coverage_failed", "content_recipe_library_summary": recipe_summary})
    if structural_summary.get("unique_signature_count") != len(PRESETS) or not structural_summary.get("passed"):
        failures.append({"reason": "structural_playbook_diversity_failed", "structural_playbook_summary": structural_summary})
    if set(structural_summary.get("required_treatment_keys") or []) != set(REQUIRED_CONTENT_TREATMENTS):
        failures.append({"reason": "structural_playbook_required_keys_mismatch", "structural_playbook_summary": structural_summary})
    if structural_summary.get("missing_by_preset") or structural_summary.get("invalid_by_preset"):
        failures.append({"reason": "structural_playbook_coverage_failed", "structural_playbook_summary": structural_summary})
    if motif_summary.get("motif_library_version") != STRUCTURAL_MOTIF_LIBRARY_VERSION:
        failures.append({"reason": "structural_motif_library_version_mismatch", "structural_motif_summary": motif_summary})
    if motif_summary.get("unique_signature_count") != len(PRESETS) or not motif_summary.get("passed"):
        failures.append({"reason": "structural_motif_diversity_failed", "structural_motif_summary": motif_summary})
    if motif_summary.get("thin_by_preset"):
        failures.append({"reason": "structural_motif_coverage_failed", "structural_motif_summary": motif_summary})
    if metric_summary.get("metric_profile_version") != STYLE_METRIC_PROFILE_VERSION:
        failures.append({"reason": "style_metric_profile_version_mismatch", "style_metric_profile_summary": metric_summary})
    if metric_summary.get("unique_signature_count") != len(PRESETS) or not metric_summary.get("passed"):
        failures.append({"reason": "style_metric_profile_diversity_failed", "style_metric_profile_summary": metric_summary})
    if metric_summary.get("thin_by_preset"):
        failures.append({"reason": "style_metric_profile_coverage_failed", "style_metric_profile_summary": metric_summary})
    structural_floors = (
        structural_summary.get("first_choice_unique_floors")
        if isinstance(structural_summary.get("first_choice_unique_floors"), dict)
        else {}
    )
    structural_unique_counts = (
        structural_summary.get("first_choice_unique_counts")
        if isinstance(structural_summary.get("first_choice_unique_counts"), dict)
        else {}
    )
    structural_archetype_unique_counts = (
        structural_summary.get("treatment_archetype_unique_counts")
        if isinstance(structural_summary.get("treatment_archetype_unique_counts"), dict)
        else {}
    )
    structural_semantic_unique_counts = (
        structural_summary.get("treatment_archetype_semantic_unique_counts")
        if isinstance(structural_summary.get("treatment_archetype_semantic_unique_counts"), dict)
        else {}
    )
    structural_semantic_floor_failures = (
        structural_summary.get("treatment_archetype_semantic_floor_failures")
        if isinstance(structural_summary.get("treatment_archetype_semantic_floor_failures"), dict)
        else {}
    )
    for field, minimum in structural_floors.items():
        if int(structural_unique_counts.get(field) or 0) < int(minimum or 0):
            failures.append(
                {
                    "reason": "structural_playbook_field_coverage_below_floor",
                    "field": field,
                    "minimum": minimum,
                    "first_choice_unique_counts": structural_unique_counts,
                }
            )
    for field in REQUIRED_CONTENT_TREATMENTS:
        if int(structural_archetype_unique_counts.get(field) or 0) != len(PRESETS):
            failures.append(
                {
                    "reason": "structural_playbook_archetype_coverage_failed",
                    "field": field,
                    "expected": len(PRESETS),
                    "treatment_archetype_unique_counts": structural_archetype_unique_counts,
                }
            )
        if int(structural_semantic_unique_counts.get(field) or 0) != len(PRESETS):
            failures.append(
                {
                    "reason": "structural_playbook_semantic_archetype_coverage_failed",
                    "field": field,
                    "expected": len(PRESETS),
                    "treatment_archetype_semantic_unique_counts": structural_semantic_unique_counts,
                    "semantic_floor_failures": structural_semantic_floor_failures,
                }
            )
    renderer_unique_counts = (
        renderer.get("unique_field_counts")
        if isinstance(renderer.get("unique_field_counts"), dict)
        else {}
    )
    for field, minimum in {
        "title_layout": 4,
        "footer_mode": 2,
        "chart_treatment": 3,
        "table_treatment": 4,
        "figure_table_treatment": 4,
    }.items():
        if int(renderer_unique_counts.get(field) or 0) < minimum:
            failures.append(
                {
                    "reason": "renderer_treatment_field_coverage_below_floor",
                    "field": field,
                    "minimum": minimum,
                    "unique_field_counts": renderer_unique_counts,
                }
            )
    if not visual.get("available") or not visual.get("passed"):
        failures.append({"reason": "visual_diversity_failed", "visual_diversity": visual})
    if int(visual.get("rendered_record_count") or 0) != len(PRESETS):
        failures.append({"reason": "visual_rendered_record_count_mismatch", "visual_diversity": visual})
    if int(visual.get("unique_visual_hash_count") or 0) != len(PRESETS):
        failures.append({"reason": "visual_hashes_not_unique", "visual_diversity": visual})
    min_pair = visual.get("min_pairwise_distance") if isinstance(visual.get("min_pairwise_distance"), dict) else {}
    min_distance = float(min_pair.get("normalized_distance") or 0)
    floor = float(visual.get("min_normalized_distance_floor") or 0.10)
    if min_distance < floor:
        failures.append(
            {
                "reason": "visual_min_distance_below_floor",
                "min_pairwise_distance": min_pair,
                "floor": floor,
            }
        )
    for record in records:
        preset = str(record.get("preset") or "")
        content_recipe = (
            record.get("content_recipe_summary")
            if isinstance(record.get("content_recipe_summary"), dict)
            else {}
        )
        structural_motif = (
            record.get("structural_motif_library")
            if isinstance(record.get("structural_motif_library"), dict)
            else {}
        )
        style_metric_profile = (
            record.get("style_metric_profile")
            if isinstance(record.get("style_metric_profile"), dict)
            else {}
        )
        if structural_motif.get("motif_library_version") != STRUCTURAL_MOTIF_LIBRARY_VERSION:
            failures.append({"preset": preset, "reason": "record_structural_motif_version_missing", "structural_motif": structural_motif})
        if len(structural_motif.get("layout_motifs") if isinstance(structural_motif.get("layout_motifs"), list) else []) < 3:
            failures.append({"preset": preset, "reason": "record_structural_motif_too_thin", "structural_motif": structural_motif})
        if not str(structural_motif.get("motif_signature") or "").strip():
            failures.append({"preset": preset, "reason": "record_structural_motif_signature_missing", "structural_motif": structural_motif})
        if style_metric_profile.get("metric_profile_version") != STYLE_METRIC_PROFILE_VERSION:
            failures.append({"preset": preset, "reason": "record_style_metric_version_missing", "style_metric_profile": style_metric_profile})
        if not str(style_metric_profile.get("metric_signature") or record.get("style_metric_signature") or "").strip():
            failures.append({"preset": preset, "reason": "record_style_metric_signature_missing", "style_metric_profile": style_metric_profile})
        if not content_recipe.get("passed"):
            failures.append({"preset": preset, "reason": "record_content_recipe_summary_failed", "content_recipe_summary": content_recipe})
        slide_recipe_trace = (
            record.get("slide_recipe_trace_summary")
            if isinstance(record.get("slide_recipe_trace_summary"), dict)
            else {}
        )
        if not slide_recipe_trace.get("passed"):
            failures.append({"preset": preset, "reason": "record_slide_recipe_trace_failed", "slide_recipe_trace_summary": slide_recipe_trace})
        if int(slide_recipe_trace.get("trace_count") or 0) != int(record.get("content_slide_count") or 0):
            failures.append({"preset": preset, "reason": "record_slide_recipe_trace_count_mismatch", "slide_recipe_trace_summary": slide_recipe_trace})
        signature = record.get("rendered_visual_signature") if isinstance(record.get("rendered_visual_signature"), dict) else {}
        if not signature.get("available"):
            failures.append({"preset": preset, "reason": "missing_rendered_visual_signature", "signature": signature})
            continue
        if int(signature.get("nonblank_slide_count") or 0) != int(signature.get("used_slide_count") or 0):
            failures.append({"preset": preset, "reason": "rendered_signature_blank_slide", "signature": signature})

    report = {
        "passed": not failures,
        "workspace_root": str(root),
        "workspace_preserved": (not created_temp) or bool(args.keep_workspace) or bool(failures),
        "summary": str(outdir / "summary.json"),
        "release_evidence": str(evidence_path),
        "contact_sheet": contact.get("path"),
        "structure_contact_sheet": structure_contact.get("path"),
        "footer_contact_sheet": footer_contact.get("path"),
        "treatment_contact_sheets": {
            str(key): value.get("path")
            for key, value in treatment_contacts.items()
            if isinstance(value, dict)
        },
        "preset_contact_collection_root": preset_collections.get("root"),
        "preset_contact_sheet_count": preset_collection_summary.get("sheet_count"),
        "preset_contact_required_use_cases": preset_collection_summary.get("required_use_cases"),
        "preset_count": len(PRESETS),
        "min_pairwise_distance": min_pair,
        "renderer_treatment_unique_counts": renderer_unique_counts,
        "footer_contact_mode_counts": footer_mode_counts,
        "structural_playbook_unique_counts": structural_unique_counts,
        "structural_archetype_unique_counts": structural_archetype_unique_counts,
        "structural_archetype_semantic_unique_counts": structural_semantic_unique_counts,
        "treatment_contact_image_counts": image_counts,
        "treatment_visual_unique_thumb_counts": {
            key: value.get("unique_thumb_signature_count")
            for key, value in treatment_visual_by_key.items()
            if isinstance(value, dict)
        },
        "treatment_visual_unique_layout_counts": {
            key: value.get("unique_layout_hash_count")
            for key, value in treatment_visual_by_key.items()
            if isinstance(value, dict)
        },
        "unique_structural_motif_signature_count": motif_summary.get("unique_signature_count"),
        "unique_style_metric_signature_count": metric_summary.get("unique_signature_count"),
        "unique_content_recipe_signature_count": recipe_summary.get("unique_signature_count"),
        "low_distance_pairs": visual.get("low_distance_pairs"),
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    if created_temp and not failures and not args.keep_workspace:
        shutil.rmtree(root, ignore_errors=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
