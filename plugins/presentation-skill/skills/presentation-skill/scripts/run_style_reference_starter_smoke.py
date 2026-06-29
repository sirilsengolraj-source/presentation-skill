#!/usr/bin/env python3
"""Fast smoke for all-preset style-reference workspace starters."""

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


STARTER_VERSION = "style_reference_starter_outline_v1"
STARTER_STATUS = "synthetic_scaffold_replace_before_delivery"
STYLE_REFERENCE_KIND = "style_reference"


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


def _starter_asset_refs(slide: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    assets = slide.get("assets") if isinstance(slide.get("assets"), dict) else {}
    for key in ("hero_image", "image", "diagram", "mermaid_source", "mermaid"):
        value = assets.get(key)
        if isinstance(value, str) and value.strip() and not value.startswith(("asset:", "image:", "generated:")):
            refs.append(value.strip())
    icons = assets.get("icons")
    if isinstance(icons, list):
        for value in icons:
            if isinstance(value, str) and value.strip() and ":" not in value:
                refs.append(value.strip())
    figures = slide.get("figures")
    if isinstance(figures, list):
        for item in figures:
            if isinstance(item, str) and item.strip():
                refs.append(item.strip())
            elif isinstance(item, dict):
                value = item.get("path") or item.get("image") or item.get("src")
                if isinstance(value, str) and value.strip():
                    refs.append(value.strip())
    return refs


def _path_exists(workspace: Path, raw: str) -> bool:
    path = Path(raw)
    if path.is_absolute():
        return path.exists()
    candidates = [
        workspace / path,
        workspace / "assets" / path,
        workspace / "assets" / "icons" / (raw if Path(raw).suffix else f"{raw}.png"),
    ]
    return any(candidate.exists() for candidate in candidates)


def _assert_workspace(
    *,
    workspace: Path,
    preset: str,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    outline = _load_json(workspace / "outline.json")
    content = _load_json(workspace / "content_plan.json")
    design = _load_json(workspace / "design_brief.json")
    contract = _load_json(workspace / "style_contract.json")

    slides = outline.get("slides") if isinstance(outline.get("slides"), list) else []
    metadata = outline.get("metadata") if isinstance(outline.get("metadata"), dict) else {}
    style_meta = metadata.get("style_reference") if isinstance(metadata.get("style_reference"), dict) else {}
    scaffold_slides = [
        slide
        for slide in slides
        if isinstance(slide, dict) and slide.get("starter_kind") == STYLE_REFERENCE_KIND
    ]
    variants = [
        str(slide.get("variant") or "").strip()
        for slide in scaffold_slides
        if str(slide.get("variant") or "").strip()
    ]
    treatments = [
        str(slide.get("treatment_key") or "").strip()
        for slide in scaffold_slides
        if str(slide.get("treatment_key") or "").strip()
    ]
    signature = "|".join(variants)

    if (
        metadata.get("starter_outline_version") != STARTER_VERSION
        or metadata.get("starter_outline_status") != STARTER_STATUS
        or style_meta.get("catalog_version") != "style_reference_catalog_v1"
        or style_meta.get("playbook_version") != "style_reference_layout_playbook_v1"
    ):
        failures.append(
            {
                "preset": preset,
                "reason": "starter_metadata_missing",
                "metadata": metadata,
            }
        )
    if len(scaffold_slides) < 3 or len(set(variants)) < 3 or len(set(treatments)) < 3:
        failures.append(
            {
                "preset": preset,
                "reason": "starter_scaffold_too_thin",
                "variants": variants,
                "treatments": treatments,
            }
        )
    if not any(variant in variants for variant in ("chart", "table", "lab-run-results", "scientific-figure", "image-sidebar", "flow", "stats")):
        failures.append({"preset": preset, "reason": "starter_missing_evidence_variant", "variants": variants})

    plan = content.get("slide_plan") if isinstance(content.get("slide_plan"), list) else []
    plan_by_id = {
        str(item.get("slide_id") or "").strip(): item
        for item in plan
        if isinstance(item, dict) and str(item.get("slide_id") or "").strip()
    }
    slide_ids = [
        str(slide.get("slide_id") or "").strip()
        for slide in slides
        if isinstance(slide, dict) and str(slide.get("slide_id") or "").strip()
    ]
    if sorted(plan_by_id) != sorted(slide_ids):
        failures.append(
            {
                "preset": preset,
                "reason": "content_plan_slide_ids_drift",
                "outline_ids": slide_ids,
                "plan_ids": sorted(plan_by_id),
            }
        )
    for slide in scaffold_slides:
        slide_id = str(slide.get("slide_id") or "").strip()
        plan_item = plan_by_id.get(slide_id, {})
        evidence_needs = plan_item.get("evidence_needs") if isinstance(plan_item.get("evidence_needs"), list) else []
        if (
            plan_item.get("source_status") != "synthetic_style_reference_scaffold"
            or "replace_synthetic_style_reference_content" not in evidence_needs
        ):
            failures.append(
                {
                    "preset": preset,
                    "slide_id": slide_id,
                    "reason": "scaffold_plan_flag_missing",
                    "plan": plan_item,
                }
            )
        for raw in _starter_asset_refs(slide):
            if not _path_exists(workspace, raw):
                failures.append(
                    {
                        "preset": preset,
                        "slide_id": slide_id,
                        "reason": "starter_asset_missing",
                        "asset": raw,
                    }
                )

    style_system = design.get("style_system") if isinstance(design.get("style_system"), dict) else {}
    style_reference = (
        style_system.get("style_reference")
        if isinstance(style_system.get("style_reference"), dict)
        else {}
    )
    if (
        style_system.get("style_preset") != preset
        or style_reference.get("catalog_version") != "style_reference_catalog_v1"
        or style_reference.get("source_status") != "synthetic_original_publish_safe"
        or not isinstance(style_reference.get("layout_playbook"), dict)
        or not isinstance(style_reference.get("example_storyboard"), dict)
    ):
        failures.append(
            {
                "preset": preset,
                "reason": "design_style_reference_missing",
                "style_system": style_system,
            }
        )
    contract_reference = (
        contract.get("style_reference")
        if isinstance(contract.get("style_reference"), dict)
        else {}
    )
    if (
        contract_reference.get("starter_outline_version") != STARTER_VERSION
        or contract_reference.get("reference_id") != style_reference.get("reference_id")
    ):
        failures.append(
            {
                "preset": preset,
                "reason": "style_contract_reference_missing",
                "style_contract_reference": contract_reference,
            }
        )

    return {
        "preset": preset,
        "reference_id": style_reference.get("reference_id"),
        "variant_signature": signature,
        "variants": variants,
        "treatments": treatments,
        "slide_count": len(slides),
        "scaffold_slide_count": len(scaffold_slides),
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize and QA all style-reference starter workspaces."
    )
    parser.add_argument(
        "--workspace-root",
        default="",
        help="Optional root directory for generated starter workspaces. Defaults to a temp dir.",
    )
    parser.add_argument(
        "--keep-workspace",
        action="store_true",
        help="Keep the temporary workspace root after a passing run.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Only inspect initialized starter sources; do not run build_workspace.py QA.",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    repo = Path(__file__).resolve().parent.parent
    created_temp = not bool(str(args.workspace_root).strip())
    root = (
        Path(args.workspace_root).expanduser().resolve()
        if str(args.workspace_root).strip()
        else Path(tempfile.mkdtemp(prefix="presentation-skill-style-starters-"))
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
        init_cmd = [
            py,
            str(repo / "scripts" / "init_deck_workspace.py"),
            "--workspace",
            str(workspace),
            "--title",
            f"Starter Smoke {preset}",
            "--style-preset",
            preset,
            "--overwrite",
        ]
        init_result = _run(init_cmd, cwd=repo)
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
        record = _assert_workspace(workspace=workspace, preset=preset, failures=failures)
        signature = str(record.get("variant_signature") or "")
        if not signature:
            failures.append({"preset": preset, "reason": "starter_signature_empty"})
        elif signature in signature_owners:
            failures.append(
                {
                    "preset": preset,
                    "reason": "duplicate_starter_signature",
                    "signature": signature,
                    "matches": signature_owners[signature],
                }
            )
        else:
            signature_owners[signature] = preset
        if not args.skip_build:
            build_cmd = [
                py,
                str(repo / "scripts" / "build_workspace.py"),
                "--workspace",
                str(workspace),
                "--qa",
                "--skip-render",
                "--overwrite",
            ]
            build_result = _run(build_cmd, cwd=repo)
            record["build_returncode"] = build_result.returncode
            if build_result.returncode != 0:
                failures.append(
                    {
                        "preset": preset,
                        "reason": "build_qa_failed",
                        "returncode": build_result.returncode,
                        "stdout_tail": build_result.stdout[-2200:],
                    }
                )
            qa_report = _load_json(workspace / "build" / "qa" / "report.json")
            if isinstance(qa_report, dict):
                counts = {
                    "overflow_count": qa_report.get("overflow_count"),
                    "overlap_count": qa_report.get("overlap_count"),
                    "geometry_error_count": qa_report.get("geometry_error_count"),
                    "whitespace_warning_count": qa_report.get("whitespace_warning_count"),
                    "visual_warning_count": qa_report.get("visual_warning_count"),
                    "design_error_count": qa_report.get("design_error_count"),
                    "design_warning_count": qa_report.get("design_warning_count"),
                }
                record["qa_counts"] = counts
                if any(int(value or 0) for value in counts.values()):
                    failures.append(
                        {
                            "preset": preset,
                            "reason": "qa_counts_nonzero",
                            "qa_counts": counts,
                        }
                    )
        records.append(record)

    coverage: dict[str, int] = {}
    for record in records:
        for variant in record.get("variants", []):
            coverage[variant] = coverage.get(variant, 0) + 1
    required_coverage = {"chart", "table", "lab-run-results", "scientific-figure", "image-sidebar", "flow", "matrix", "stats", "comparison-2col"}
    missing_coverage = sorted(required_coverage - set(coverage))
    if missing_coverage:
        failures.append({"reason": "starter_variant_coverage_missing", "missing": missing_coverage, "coverage": coverage})

    summary = {
        "passed": not failures,
        "workspace_root": str(root),
        "workspace_preserved": (not created_temp) or bool(args.keep_workspace) or bool(failures),
        "preset_count": len(PRESETS),
        "record_count": len(records),
        "unique_signature_count": len(signature_owners),
        "variant_coverage": dict(sorted(coverage.items())),
        "records": records,
        "failures": failures,
    }
    print(json.dumps(summary, indent=2))
    if created_temp and not failures and not args.keep_workspace:
        shutil.rmtree(root, ignore_errors=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
