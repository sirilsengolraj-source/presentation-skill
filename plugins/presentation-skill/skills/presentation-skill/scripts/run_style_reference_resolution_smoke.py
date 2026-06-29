#!/usr/bin/env python3
"""Smoke-test build-time style-reference layout resolution across presets."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from design_tokens import PRESETS
from style_reference_catalog import CONTENT_RECIPE_LIBRARY_VERSION, STRUCTURAL_MOTIF_LIBRARY_VERSION


PNG_64 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAKElEQVR4nO3BAQ0AAADCoPdPbQ43o"
    "AAAAAAAAAAAAAAAAAAAAAAAAAPgZQ0AAAU3pNQAAAAAASUVORK5CYII="
)

TREATMENT_SLIDE_IDS = (
    "table",
    "chart",
    "figure",
    "comparison",
    "dashboard",
    "decision",
    "references",
)

EXPECTED_RESOLUTIONS = {
    ("bold-startup-narrative", "dashboard"): "kpi-hero",
    ("sunset-investor", "dashboard"): "kpi-hero",
    ("lavender-ops", "dashboard"): "table",
    ("warm-terracotta", "comparison"): "matrix",
    ("warm-terracotta", "decision"): "table",
    ("lab-report", "table"): "lab-run-results",
    ("lab-report", "dashboard"): "lab-run-results",
    ("forest-research", "figure"): "scientific-figure",
    ("data-heavy-boardroom", "comparison"): "matrix",
}


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _generic_slides() -> list[dict[str, Any]]:
    image_path = "assets/style_reference_resolution.png"
    return [
        {
            "slide_id": "title",
            "type": "title",
            "variant": "title",
            "title": "Resolution Smoke",
            "subtitle": "Same source JSON, preset-specific resolved treatments.",
        },
        {
            "slide_id": "table",
            "type": "content",
            "variant": "standard",
            "title": "Run Table",
            "treatment_key": "table",
            "headers": ["Metric", "Value"],
            "rows": [["Yield", "82%"], ["Flag", "Review"]],
        },
        {
            "slide_id": "chart",
            "type": "content",
            "variant": "standard",
            "title": "Signal Chart",
            "treatment_key": "chart",
            "chart": {"type": "bar", "labels": ["A", "B", "C"], "values": [1, 2, 3]},
        },
        {
            "slide_id": "figure",
            "type": "content",
            "variant": "standard",
            "title": "Evidence Figure",
            "treatment_key": "figure",
            "image": image_path,
            "figures": [{"path": image_path}],
            "steps": [
                {"title": "Gate A", "body": "First check."},
                {"title": "Gate B", "body": "Second check."},
            ],
        },
        {
            "slide_id": "comparison",
            "type": "content",
            "variant": "standard",
            "title": "Compare Routes",
            "treatment_key": "comparison",
            "body": "Short contrast setup.",
            "left": {"title": "Current", "body": ["Manual pass"]},
            "right": {"title": "Reference", "body": ["Structured pass"]},
            "quadrants": [
                {"title": "High", "body": "Act."},
                {"title": "Watch", "body": "Monitor."},
                {"title": "Low", "body": "Hold."},
                {"title": "Next", "body": "Owner."},
            ],
        },
        {
            "slide_id": "dashboard",
            "type": "content",
            "variant": "standard",
            "title": "Status Readout",
            "treatment_key": "dashboard",
            "value": "42%",
            "label": "Signal",
            "facts": [{"value": "1", "label": "A"}, {"value": "2", "label": "B"}],
            "headers": ["Metric", "Value"],
            "rows": [["A", "1"], ["B", "2"]],
        },
        {
            "slide_id": "decision",
            "type": "content",
            "variant": "standard",
            "title": "Decision Log",
            "treatment_key": "decision",
            "body": "Recommendation.",
            "headers": ["Action", "Owner"],
            "rows": [["Act", "A"], ["Watch", "B"]],
        },
        {
            "slide_id": "references",
            "type": "content",
            "variant": "standard",
            "title": "References",
            "treatment_key": "references",
            "body": "Synthetic source posture.",
            "bullets": ["S1: Synthetic", "S2: No private data"],
            "highlights": ["Descriptors only", "No copied slides"],
            "quadrants": [
                {"title": "S1", "body": "Synthetic"},
                {"title": "S2", "body": "No private data"},
                {"title": "Allowed", "body": "Descriptors"},
                {"title": "Blocked", "body": "Copied slides"},
            ],
            "headers": ["ID", "Source"],
            "rows": [["S1", "Synthetic"], ["S2", "Synthetic"]],
        },
    ]


def _replace_outline(workspace: Path) -> None:
    slides = _generic_slides()
    outline_path = workspace / "outline.json"
    outline = _load_json(outline_path)
    outline["slides"] = slides
    metadata = outline.get("metadata") if isinstance(outline.get("metadata"), dict) else {}
    metadata["resolution_smoke_version"] = "style_reference_resolution_smoke_v1"
    outline["metadata"] = metadata
    _write_json(outline_path, outline)

    content_path = workspace / "content_plan.json"
    content = _load_json(content_path)
    content["slide_plan"] = [
        {
            "slide_id": str(slide["slide_id"]),
            "purpose": str(slide.get("title") or slide["slide_id"]),
            "source_status": "synthetic_resolution_smoke",
            "evidence_needs": ["style_reference_resolution"],
        }
        for slide in slides
    ]
    _write_json(content_path, content)

    asset_dir = workspace / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / "style_reference_resolution.png").write_bytes(PNG_64)


def _source_variants_are_generic(workspace: Path, failures: list[dict[str, Any]], preset: str) -> None:
    source = _load_json(workspace / "outline.json")
    slides = source.get("slides") if isinstance(source.get("slides"), list) else []
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("slide_id") or "")
        if slide_id in TREATMENT_SLIDE_IDS and slide.get("variant") != "standard":
            failures.append(
                {
                    "preset": preset,
                    "slide_id": slide_id,
                    "reason": "source_outline_mutated",
                    "variant": slide.get("variant"),
                }
            )


def _assert_resolved_outline(
    *,
    workspace: Path,
    preset: str,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved_path = workspace / "build" / "outline_resolved.json"
    if not resolved_path.exists():
        failures.append({"preset": preset, "reason": "resolved_outline_missing"})
        return {"preset": preset, "variant_signature": ""}

    resolved = _load_json(resolved_path)
    slides = resolved.get("slides") if isinstance(resolved.get("slides"), list) else []
    slides_by_id = {
        str(slide.get("slide_id") or ""): slide
        for slide in slides
        if isinstance(slide, dict) and str(slide.get("slide_id") or "")
    }
    summary = (
        resolved.get("resolved_treatment_summary", {})
        .get("style_reference_layout", {})
        if isinstance(resolved.get("resolved_treatment_summary"), dict)
        else {}
    )
    if summary.get("playbook_version") != "style_reference_layout_playbook_v1":
        failures.append(
            {
                "preset": preset,
                "reason": "style_reference_layout_summary_missing",
                "summary": summary,
            }
        )
    if summary.get("motif_library_version") != STRUCTURAL_MOTIF_LIBRARY_VERSION or not summary.get("motif_signature"):
        failures.append(
            {
                "preset": preset,
                "reason": "style_reference_motif_summary_missing",
                "summary": summary,
            }
        )
    if int(summary.get("applied_count") or 0) < 4:
        failures.append(
            {
                "preset": preset,
                "reason": "too_few_resolved_variants",
                "summary": summary,
            }
        )
    if int(summary.get("annotated_count") or 0) < len(TREATMENT_SLIDE_IDS):
        failures.append(
            {
                "preset": preset,
                "reason": "too_few_annotated_treatments",
                "summary": summary,
            }
        )
    summary_semantics = (
        summary.get("treatment_archetype_semantic_signatures")
        if isinstance(summary.get("treatment_archetype_semantic_signatures"), dict)
        else {}
    )
    missing_summary_semantics = [
        slide_id
        for slide_id in TREATMENT_SLIDE_IDS
        if not str(summary_semantics.get(slide_id) or "").strip()
    ]
    if missing_summary_semantics:
        failures.append(
            {
                "preset": preset,
                "reason": "style_reference_semantic_summary_missing",
                "missing_treatments": missing_summary_semantics,
                "summary": summary,
            }
        )

    resolved_variants: dict[str, str] = {}
    recipe_signatures: set[str] = set()
    recipe_archetypes: set[str] = set()
    treatment_semantic_signatures: dict[str, str] = {}
    for slide_id in TREATMENT_SLIDE_IDS:
        slide = slides_by_id.get(slide_id)
        if not isinstance(slide, dict):
            failures.append({"preset": preset, "slide_id": slide_id, "reason": "slide_missing"})
            continue
        layout = (
            slide.get("resolved_treatments", {}).get("style_reference_layout", {})
            if isinstance(slide.get("resolved_treatments"), dict)
            else {}
        )
        resolved_variant = str(layout.get("resolved_variant") or "")
        resolved_variants[slide_id] = resolved_variant
        recipe_signature = str(layout.get("content_recipe_signature") or "").strip()
        if recipe_signature:
            recipe_signatures.add(recipe_signature)
        recipe_archetype_id = str(layout.get("content_recipe_archetype_id") or "").strip()
        if recipe_archetype_id:
            recipe_archetypes.add(recipe_archetype_id)
        treatment_archetype_id = str(layout.get("treatment_archetype_id") or "").strip()
        treatment_semantic_signature = str(layout.get("treatment_archetype_semantic_signature") or "").strip()
        content_semantic_signature = str(layout.get("content_recipe_archetype_semantic_signature") or "").strip()
        if treatment_semantic_signature:
            treatment_semantic_signatures[slide_id] = treatment_semantic_signature
        if (
            layout.get("playbook_version") != "style_reference_layout_playbook_v1"
            or layout.get("treatment_key") != slide_id
            or not layout.get("reference_id")
            or layout.get("motif_library_version") != STRUCTURAL_MOTIF_LIBRARY_VERSION
            or not layout.get("motif_signature")
            or not resolved_variant
            or slide.get("variant") != resolved_variant
            or layout.get("content_recipe_library_version") != CONTENT_RECIPE_LIBRARY_VERSION
            or not layout.get("content_recipe_signature")
            or not treatment_archetype_id
            or not layout.get("treatment_archetype_signature")
            or not treatment_semantic_signature
            or treatment_semantic_signature != content_semantic_signature
            or treatment_semantic_signature != str(summary_semantics.get(slide_id) or "").strip()
        ):
            failures.append(
                {
                    "preset": preset,
                    "slide_id": slide_id,
                    "reason": "slide_resolution_annotation_invalid",
                    "variant": slide.get("variant"),
                    "style_reference_layout": layout,
                }
            )
        if slide_id == "references" and not recipe_archetype_id:
            failures.append(
                {
                    "preset": preset,
                    "slide_id": slide_id,
                    "reason": "references_archetype_trace_missing",
                    "style_reference_layout": layout,
                }
            )

    for (expected_preset, slide_id), expected_variant in EXPECTED_RESOLUTIONS.items():
        if preset == expected_preset and resolved_variants.get(slide_id) != expected_variant:
            failures.append(
                {
                    "preset": preset,
                    "slide_id": slide_id,
                    "reason": "target_resolution_mismatch",
                    "expected": expected_variant,
                    "actual": resolved_variants.get(slide_id),
                }
            )

    signature = ">".join(f"{slide_id}:{resolved_variants.get(slide_id, '')}" for slide_id in TREATMENT_SLIDE_IDS)
    return {
        "preset": preset,
        "reference_id": summary.get("reference_id"),
        "applied_count": summary.get("applied_count"),
        "annotated_count": summary.get("annotated_count"),
        "variant_signature": signature,
        "content_recipe_signature_count": len(recipe_signatures),
        "content_recipe_archetype_count": len(recipe_archetypes),
        "treatment_archetype_semantic_signature_count": len(set(treatment_semantic_signatures.values())),
        "treatment_archetype_semantic_signatures": treatment_semantic_signatures,
        "resolved_variants": resolved_variants,
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build generic evidence slides and verify preset-specific resolved variants."
    )
    parser.add_argument(
        "--workspace-root",
        default="",
        help="Optional root directory for generated workspaces. Defaults to a temp dir.",
    )
    parser.add_argument(
        "--keep-workspace",
        action="store_true",
        help="Keep the temporary workspace root after a passing run.",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    repo = Path(__file__).resolve().parent.parent
    created_temp = not bool(str(args.workspace_root).strip())
    root = (
        Path(args.workspace_root).expanduser().resolve()
        if str(args.workspace_root).strip()
        else Path(tempfile.mkdtemp(prefix="presentation-skill-style-resolution-"))
    )
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

    py = sys.executable
    failures: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    signature_owners: dict[str, str] = {}

    for preset in sorted(PRESETS):
        workspace = root / preset
        init_result = _run(
            [
                py,
                str(repo / "scripts" / "init_deck_workspace.py"),
                "--workspace",
                str(workspace),
                "--title",
                f"Resolution Smoke {preset}",
                "--style-preset",
                preset,
                "--overwrite",
            ],
            cwd=repo,
        )
        if init_result.returncode != 0:
            failures.append(
                {
                    "preset": preset,
                    "reason": "init_failed",
                    "returncode": init_result.returncode,
                    "stdout_tail": init_result.stdout[-1600:],
                }
            )
            continue

        _replace_outline(workspace)
        build_result = _run(
            [
                py,
                str(repo / "scripts" / "build_workspace.py"),
                "--workspace",
                str(workspace),
                "--overwrite",
            ],
            cwd=repo,
        )
        if build_result.returncode != 0:
            failures.append(
                {
                    "preset": preset,
                    "reason": "build_failed",
                    "returncode": build_result.returncode,
                    "stdout_tail": build_result.stdout[-2200:],
                }
            )
            continue

        _source_variants_are_generic(workspace, failures, preset)
        record = _assert_resolved_outline(workspace=workspace, preset=preset, failures=failures)
        signature = str(record.get("variant_signature") or "")
        if not signature:
            failures.append({"preset": preset, "reason": "variant_signature_empty"})
        elif signature in signature_owners:
            failures.append(
                {
                    "preset": preset,
                    "reason": "duplicate_resolved_variant_signature",
                    "signature": signature,
                    "matches": signature_owners[signature],
                }
            )
        else:
            signature_owners[signature] = preset
        records.append(record)

    if len(signature_owners) != len(PRESETS):
        failures.append(
            {
                "reason": "resolved_signature_count_mismatch",
                "expected": len(PRESETS),
                "actual": len(signature_owners),
            }
        )

    coverage: dict[str, int] = {}
    semantic_owners_by_treatment: dict[str, dict[str, str]] = {key: {} for key in TREATMENT_SLIDE_IDS}
    for record in records:
        variants = record.get("resolved_variants") if isinstance(record.get("resolved_variants"), dict) else {}
        for variant in variants.values():
            if str(variant).strip():
                coverage[str(variant)] = coverage.get(str(variant), 0) + 1
        semantics = (
            record.get("treatment_archetype_semantic_signatures")
            if isinstance(record.get("treatment_archetype_semantic_signatures"), dict)
            else {}
        )
        preset = str(record.get("preset") or "")
        for treatment_key in TREATMENT_SLIDE_IDS:
            signature = str(semantics.get(treatment_key) or "").strip()
            if not signature:
                continue
            owners = semantic_owners_by_treatment.setdefault(treatment_key, {})
            if signature in owners:
                failures.append(
                    {
                        "preset": preset,
                        "reason": "duplicate_treatment_semantic_signature",
                        "treatment_key": treatment_key,
                        "signature": signature,
                        "matches": owners[signature],
                    }
                )
            else:
                owners[signature] = preset
    semantic_unique_counts = {
        treatment_key: len(owners)
        for treatment_key, owners in sorted(semantic_owners_by_treatment.items())
    }
    semantic_count_failures = {
        treatment_key: count
        for treatment_key, count in semantic_unique_counts.items()
        if count != len(PRESETS)
    }
    if semantic_count_failures:
        failures.append(
            {
                "reason": "treatment_semantic_signature_count_mismatch",
                "expected_per_treatment": len(PRESETS),
                "actual": semantic_count_failures,
            }
        )
    required_variants = {
        "chart",
        "comparison-2col",
        "flow",
        "image-sidebar",
        "kpi-hero",
        "lab-run-results",
        "matrix",
        "scientific-figure",
        "split",
        "stats",
        "table",
    }
    missing_variants = sorted(required_variants - set(coverage))
    if missing_variants:
        failures.append(
            {
                "reason": "resolved_variant_coverage_missing",
                "missing": missing_variants,
                "coverage": coverage,
            }
        )

    summary = {
        "passed": not failures,
        "workspace_root": str(root),
        "workspace_preserved": (not created_temp) or bool(args.keep_workspace) or bool(failures),
        "preset_count": len(PRESETS),
        "record_count": len(records),
        "unique_signature_count": len(signature_owners),
        "treatment_semantic_unique_counts": semantic_unique_counts,
        "resolved_variant_coverage": dict(sorted(coverage.items())),
        "records": records,
        "failures": failures,
    }
    print(json.dumps(summary, indent=2))
    if created_temp and not failures and not args.keep_workspace:
        shutil.rmtree(root, ignore_errors=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
