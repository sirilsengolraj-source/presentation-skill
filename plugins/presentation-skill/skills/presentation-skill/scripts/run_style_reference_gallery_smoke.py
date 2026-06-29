#!/usr/bin/env python3
"""Fast smoke check for generated synthetic style-reference gallery decks."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from design_tokens import PRESETS
from style_reference_catalog import (
    CONTENT_RECIPE_LIBRARY_VERSION,
    REQUIRED_CONTENT_TREATMENTS,
    STYLE_METRIC_PROFILE_VERSION,
    STRUCTURAL_MOTIF_LIBRARY_VERSION,
)

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PRESETS = sorted(PRESETS)
REQUIRED_BUCKETS = {
    "chart",
    "table",
    "figure",
    "comparison",
    "dashboard",
    "decision",
}
REQUIRED_RENDERER_FIELDS = {
    "title_layout",
    "footer_mode",
    "chart_treatment",
    "table_treatment",
    "figure_table_treatment",
    "stats_mode",
    "matrix_mode",
    "summary_callout_mode",
}


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError("Command failed:\n" + " ".join(cmd) + "\n" + result.stdout)
    return result.stdout


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="presentation-skill-style-gallery-") as tmp:
        outdir = Path(tmp) / "gallery"
        stdout = _run(
            [
                sys.executable,
                "scripts/build_style_reference_gallery.py",
                "--outdir",
                str(outdir),
                "--presets",
                *SAMPLE_PRESETS,
                "--build",
                "--qa",
            ]
        )
        summary = _load_json(outdir / "summary.json")
        failures: list[str] = []
        if summary.get("gallery_version") != "style_reference_gallery_v1":
            failures.append("summary gallery_version mismatch")
        if summary.get("preset_count") != len(SAMPLE_PRESETS):
            failures.append("summary preset_count mismatch")
        if summary.get("presets") != SAMPLE_PRESETS:
            failures.append("summary preset list mismatch")
        release_path_text = str(summary.get("release_evidence_path") or "")
        release_path = Path(release_path_text)
        if not release_path_text or not release_path.exists():
            failures.append(f"missing release evidence {release_path}")
            release_evidence: dict[str, Any] = {}
        else:
            release_evidence = _load_json(release_path)
        if release_evidence.get("evidence_version") != "style_reference_release_evidence_v1":
            failures.append("release evidence version mismatch")
        if release_evidence.get("gallery_version") != "style_reference_gallery_v1":
            failures.append("release evidence gallery version mismatch")
        if release_evidence.get("preset_count") != len(SAMPLE_PRESETS):
            failures.append("release evidence preset_count mismatch")
        qa_totals = summary.get("qa_totals") if isinstance(summary.get("qa_totals"), dict) else {}
        if qa_totals.get("record_count") != len(SAMPLE_PRESETS):
            failures.append("qa_totals record_count mismatch")
        if qa_totals.get("passed_render_free_gate_count") != len(SAMPLE_PRESETS):
            failures.append("qa_totals passed gate count mismatch")
        evidence_qa = release_evidence.get("qa_totals") if isinstance(release_evidence.get("qa_totals"), dict) else {}
        if evidence_qa != qa_totals:
            failures.append("release evidence qa_totals mismatch")
        content_summary = (
            release_evidence.get("content_signature_summary")
            if isinstance(release_evidence.get("content_signature_summary"), dict)
            else {}
        )
        renderer_summary = (
            release_evidence.get("renderer_treatment_summary")
            if isinstance(release_evidence.get("renderer_treatment_summary"), dict)
            else {}
        )
        recipe_summary = (
            release_evidence.get("content_recipe_library_summary")
            if isinstance(release_evidence.get("content_recipe_library_summary"), dict)
            else {}
        )
        structural_summary = (
            release_evidence.get("structural_playbook_summary")
            if isinstance(release_evidence.get("structural_playbook_summary"), dict)
            else {}
        )
        motif_summary = (
            release_evidence.get("structural_motif_summary")
            if isinstance(release_evidence.get("structural_motif_summary"), dict)
            else {}
        )
        if content_summary.get("unique_signature_count") != len(SAMPLE_PRESETS):
            failures.append("release evidence unique content signatures mismatch")
        if not content_summary.get("unique_first_four_content_signatures"):
            failures.append("release evidence did not prove unique first-four signatures")
        if renderer_summary.get("unique_signature_count") != len(SAMPLE_PRESETS):
            failures.append("release evidence unique renderer treatment signatures mismatch")
        if not renderer_summary.get("passed"):
            failures.append("release evidence did not prove renderer treatment diversity")
        if recipe_summary.get("library_version") != CONTENT_RECIPE_LIBRARY_VERSION:
            failures.append("release evidence recipe library version mismatch")
        if recipe_summary.get("unique_signature_count") != len(SAMPLE_PRESETS):
            failures.append("release evidence unique content recipe signatures mismatch")
        if not recipe_summary.get("passed"):
            failures.append("release evidence did not prove content recipe coverage and uniqueness")
        if structural_summary.get("unique_signature_count") != len(SAMPLE_PRESETS):
            failures.append("release evidence unique structural playbook signatures mismatch")
        if not structural_summary.get("passed"):
            failures.append("release evidence did not prove structural playbook coverage and diversity")
        if motif_summary.get("motif_library_version") != STRUCTURAL_MOTIF_LIBRARY_VERSION:
            failures.append("release evidence structural motif version mismatch")
        if motif_summary.get("unique_signature_count") != len(SAMPLE_PRESETS):
            failures.append("release evidence unique structural motif signatures mismatch")
        if not motif_summary.get("passed"):
            failures.append("release evidence did not prove structural motif coverage and diversity")
        structural_unique_counts = (
            structural_summary.get("first_choice_unique_counts")
            if isinstance(structural_summary.get("first_choice_unique_counts"), dict)
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
        structural_floors = (
            structural_summary.get("first_choice_unique_floors")
            if isinstance(structural_summary.get("first_choice_unique_floors"), dict)
            else {}
        )
        for field, minimum in structural_floors.items():
            if int(structural_unique_counts.get(field) or 0) < int(minimum or 0):
                failures.append(
                    f"structural playbook field {field} unique count "
                    f"{structural_unique_counts.get(field)} below {minimum}"
                )
        if structural_semantic_floor_failures:
            failures.append(
                "structural treatment semantic signatures are not unique across all presets: "
                f"{structural_semantic_floor_failures}"
            )
        records = summary.get("records") if isinstance(summary.get("records"), list) else []
        if len(records) != len(SAMPLE_PRESETS):
            failures.append("record count mismatch")
        seen_references: set[str] = set()
        content_signature_owners: dict[str, str] = {}
        renderer_signature_owners: dict[str, str] = {}
        content_recipe_signature_owners: dict[str, str] = {}
        structural_motif_signature_owners: dict[str, str] = {}
        style_metric_signature_owners: dict[str, str] = {}
        treatment_archetype_owners: dict[str, dict[str, str]] = {key: {} for key in REQUIRED_CONTENT_TREATMENTS}
        renderer_field_counts: dict[str, dict[str, int]] = {field: {} for field in REQUIRED_RENDERER_FIELDS}
        first_content_variant_counts: dict[str, int] = {}
        for record in records:
            preset = str(record.get("preset") or "")
            reference_id = str(record.get("style_reference_id") or "")
            if not reference_id:
                failures.append(f"{preset}: missing style reference id")
            if reference_id in seen_references:
                failures.append(f"{preset}: duplicate style reference id {reference_id}")
            seen_references.add(reference_id)
            if record.get("source_status") != "synthetic_original_publish_safe":
                failures.append(f"{preset}: unexpected source_status")
            structural_motif = (
                record.get("structural_motif_library")
                if isinstance(record.get("structural_motif_library"), dict)
                else {}
            )
            if structural_motif.get("motif_library_version") != STRUCTURAL_MOTIF_LIBRARY_VERSION:
                failures.append(f"{preset}: missing structural motif library version")
            if len(structural_motif.get("layout_motifs") if isinstance(structural_motif.get("layout_motifs"), list) else []) < 3:
                failures.append(f"{preset}: structural motif too thin")
            structural_motif_signature = str(structural_motif.get("motif_signature") or "")
            if not structural_motif_signature:
                failures.append(f"{preset}: missing structural motif signature")
            elif structural_motif_signature in structural_motif_signature_owners:
                failures.append(
                    f"{preset}: duplicate structural motif signature with "
                    f"{structural_motif_signature_owners[structural_motif_signature]}"
                )
            else:
                structural_motif_signature_owners[structural_motif_signature] = preset
            style_metric_profile = (
                record.get("style_metric_profile")
                if isinstance(record.get("style_metric_profile"), dict)
                else {}
            )
            if style_metric_profile.get("metric_profile_version") != STYLE_METRIC_PROFILE_VERSION:
                failures.append(f"{preset}: missing style metric profile version")
            style_metric_signature = str(style_metric_profile.get("metric_signature") or record.get("style_metric_signature") or "")
            if not style_metric_signature:
                failures.append(f"{preset}: missing style metric signature")
            elif style_metric_signature in style_metric_signature_owners:
                failures.append(
                    f"{preset}: duplicate style metric signature with "
                    f"{style_metric_signature_owners[style_metric_signature]}"
                )
            else:
                style_metric_signature_owners[style_metric_signature] = preset
            if len(style_metric_profile.get("artifact_bias") if isinstance(style_metric_profile.get("artifact_bias"), list) else []) < 2:
                failures.append(f"{preset}: style metric artifact bias too thin")
            if len(style_metric_profile.get("readability_bias") if isinstance(style_metric_profile.get("readability_bias"), list) else []) < 2:
                failures.append(f"{preset}: style metric readability bias too thin")
            if record.get("example_storyboard_version") != "style_reference_example_storyboard_v1":
                failures.append(f"{preset}: missing storyboard version")
            if not record.get("example_storyboard_topic") or not record.get("example_storyboard_title"):
                failures.append(f"{preset}: missing storyboard topic/title")
            source_intake = record.get("style_source_intake") if isinstance(record.get("style_source_intake"), dict) else {}
            if source_intake.get("manifest_version") != "style_reference_source_manifest_v1":
                failures.append(f"{preset}: missing style source intake manifest")
            if source_intake.get("derivation_mode") != "synthetic_reconstruction":
                failures.append(f"{preset}: unexpected style source derivation mode")
            if not record.get("style_source_ids") or not source_intake.get("sources"):
                failures.append(f"{preset}: missing style source ids")
            if record.get("layout_playbook_version") != "style_reference_layout_playbook_v1":
                failures.append(f"{preset}: missing layout playbook version")
            if not record.get("preferred_variants"):
                failures.append(f"{preset}: missing preferred variants")
            treatment_archetypes = (
                record.get("treatment_archetypes")
                if isinstance(record.get("treatment_archetypes"), dict)
                else {}
            )
            for treatment_key in REQUIRED_CONTENT_TREATMENTS:
                archetype = (
                    treatment_archetypes.get(treatment_key)
                    if isinstance(treatment_archetypes.get(treatment_key), dict)
                    else {}
                )
                archetype_id = str(archetype.get("archetype_id") or "")
                if not archetype_id:
                    failures.append(f"{preset}: missing {treatment_key} treatment archetype")
                    continue
                if archetype_id in treatment_archetype_owners[treatment_key]:
                    failures.append(
                        f"{preset}: duplicate {treatment_key} archetype {archetype_id} with "
                        f"{treatment_archetype_owners[treatment_key][archetype_id]}"
                    )
                else:
                    treatment_archetype_owners[treatment_key][archetype_id] = preset
            slide_recipe_trace = (
                record.get("slide_recipe_trace_summary")
                if isinstance(record.get("slide_recipe_trace_summary"), dict)
                else {}
            )
            if not slide_recipe_trace.get("passed"):
                failures.append(f"{preset}: slide recipe trace summary failed")
            if int(slide_recipe_trace.get("trace_count") or 0) != int(record.get("content_slide_count") or 0):
                failures.append(f"{preset}: slide recipe trace count does not match content slide count")
            content_recipe_summary = (
                record.get("content_recipe_summary")
                if isinstance(record.get("content_recipe_summary"), dict)
                else {}
            )
            if content_recipe_summary.get("library_version") != CONTENT_RECIPE_LIBRARY_VERSION:
                failures.append(f"{preset}: missing content recipe library version")
            if content_recipe_summary.get("recipe_count") != len(REQUIRED_CONTENT_TREATMENTS):
                failures.append(f"{preset}: incomplete content recipe count")
            if content_recipe_summary.get("missing_recipe_keys"):
                failures.append(f"{preset}: missing content recipe keys {content_recipe_summary.get('missing_recipe_keys')}")
            if content_recipe_summary.get("invalid_recipe_fields"):
                failures.append(f"{preset}: invalid content recipe fields {content_recipe_summary.get('invalid_recipe_fields')}")
            content_recipe_keys = set(
                content_recipe_summary.get("recipe_keys")
                if isinstance(content_recipe_summary.get("recipe_keys"), list)
                else []
            )
            if set(REQUIRED_CONTENT_TREATMENTS) != content_recipe_keys:
                failures.append(f"{preset}: content recipe keys mismatch")
            content_recipe_signature = str(content_recipe_summary.get("library_signature") or "")
            if not content_recipe_signature:
                failures.append(f"{preset}: missing content recipe library signature")
            elif content_recipe_signature in content_recipe_signature_owners:
                failures.append(
                    f"{preset}: duplicate content recipe library signature with "
                    f"{content_recipe_signature_owners[content_recipe_signature]}"
                )
            else:
                content_recipe_signature_owners[content_recipe_signature] = preset
            variant_sequence = (
                record.get("variant_sequence")
                if isinstance(record.get("variant_sequence"), list)
                else []
            )
            content_sequence = [
                str(item)
                for item in variant_sequence
                if str(item or "").strip() and str(item or "").strip() != "title"
            ]
            content_signature = ">".join(content_sequence[:4])
            if len(content_sequence) < 4:
                failures.append(f"{preset}: content variant sequence too short")
            elif content_signature in content_signature_owners:
                failures.append(
                    f"{preset}: duplicate first-four content variant signature "
                    f"{content_signature} with {content_signature_owners[content_signature]}"
                )
            else:
                content_signature_owners[content_signature] = preset
            if content_sequence:
                first = content_sequence[0]
                first_content_variant_counts[first] = first_content_variant_counts.get(first, 0) + 1
            outline_path = Path(str(record.get("outline") or ""))
            pptx_path = Path(str(record.get("pptx") or ""))
            qa_report = Path(str(record.get("qa_report") or ""))
            for label, path in (("outline", outline_path), ("pptx", pptx_path), ("qa", qa_report)):
                if not path.exists():
                    failures.append(f"{preset}: missing {label} artifact {path}")
            if not record.get("asset_paths"):
                failures.append(f"{preset}: synthetic figure assets were not generated")
            if int(record.get("slide_count") or 0) < 6:
                failures.append(f"{preset}: slide count too low")
            variant_counts = record.get("variant_counts") if isinstance(record.get("variant_counts"), dict) else {}
            if len(variant_counts) < 4:
                failures.append(f"{preset}: variant diversity too low")
            renderer_treatments = (
                record.get("renderer_treatments")
                if isinstance(record.get("renderer_treatments"), dict)
                else {}
            )
            renderer_fields = (
                renderer_treatments.get("fields")
                if isinstance(renderer_treatments.get("fields"), dict)
                else {}
            )
            renderer_signature = str(renderer_treatments.get("signature") or "")
            if not renderer_signature:
                failures.append(f"{preset}: missing renderer treatment signature")
            elif renderer_signature in renderer_signature_owners:
                failures.append(
                    f"{preset}: duplicate renderer treatment signature with "
                    f"{renderer_signature_owners[renderer_signature]}"
                )
            else:
                renderer_signature_owners[renderer_signature] = preset
            for field in REQUIRED_RENDERER_FIELDS:
                value = str(renderer_fields.get(field) or "")
                if not value:
                    failures.append(f"{preset}: missing renderer treatment field {field}")
                    continue
                renderer_field_counts[field][value] = renderer_field_counts[field].get(value, 0) + 1
            chart_treatments = (
                record.get("chart_treatment_sequence")
                if isinstance(record.get("chart_treatment_sequence"), list)
                else []
            )
            table_treatments = (
                record.get("table_treatment_sequence")
                if isinstance(record.get("table_treatment_sequence"), list)
                else []
            )
            if not chart_treatments:
                failures.append(f"{preset}: missing chart treatment sequence")
            if not table_treatments:
                failures.append(f"{preset}: missing table treatment sequence")
            treatment_buckets = set(record.get("treatment_buckets") if isinstance(record.get("treatment_buckets"), list) else [])
            if not REQUIRED_BUCKETS.issubset(treatment_buckets):
                failures.append(f"{preset}: record missing treatment buckets {sorted(REQUIRED_BUCKETS - treatment_buckets)}")
            qa_summary = record.get("qa_summary") if isinstance(record.get("qa_summary"), dict) else {}
            if not qa_summary.get("passed_render_free_gate"):
                failures.append(f"{preset}: qa summary did not pass render-free gate")
            if outline_path.exists():
                outline = _load_json(outline_path)
                metadata = outline.get("metadata") if isinstance(outline.get("metadata"), dict) else {}
                if metadata.get("gallery_version") != "style_reference_gallery_v1":
                    failures.append(f"{preset}: outline metadata gallery version mismatch")
                variants = {
                    str(slide.get("variant") or slide.get("type") or "")
                    for slide in outline.get("slides", [])
                    if isinstance(slide, dict)
                }
                for slide in outline.get("slides", []):
                    if not isinstance(slide, dict):
                        continue
                    if str(slide.get("type") or "content").lower() == "title":
                        continue
                    content_recipe = (
                        slide.get("content_recipe")
                        if isinstance(slide.get("content_recipe"), dict)
                        else {}
                    )
                    if not str(slide.get("slide_id") or "").strip():
                        failures.append(f"{preset}: gallery slide missing slide_id")
                    if str(slide.get("treatment_key") or "").strip() not in REQUIRED_CONTENT_TREATMENTS:
                        failures.append(f"{preset}: gallery slide missing valid treatment_key")
                    if (
                        content_recipe.get("library_version") != CONTENT_RECIPE_LIBRARY_VERSION
                        or not str(content_recipe.get("recipe_signature") or "").strip()
                    ):
                        failures.append(f"{preset}: gallery slide missing content recipe trace")
                buckets: set[str] = set()
                for slide in outline.get("slides", []):
                    if not isinstance(slide, dict):
                        continue
                    treatment_key = str(slide.get("treatment_key") or "").strip().lower()
                    if treatment_key in REQUIRED_CONTENT_TREATMENTS and treatment_key != "title":
                        buckets.add(treatment_key)
                for variant in variants:
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
                    if variant == "standard":
                        buckets.add("decision")
                slide_roles = {
                    str(slide.get("footer") or "").lower()
                    for slide in outline.get("slides", [])
                    if isinstance(slide, dict)
                }
                if any("decision" in role for role in slide_roles):
                    buckets.add("decision")
                if not REQUIRED_BUCKETS.issubset(buckets):
                    failures.append(f"{preset}: missing required treatment buckets {sorted(REQUIRED_BUCKETS - buckets)}")
                deck_style = outline.get("deck_style") if isinstance(outline.get("deck_style"), dict) else {}
                if not deck_style.get("style_seed"):
                    failures.append(f"{preset}: missing deterministic style seed")
                if not deck_style.get("table_treatment"):
                    failures.append(f"{preset}: missing deck_style.table_treatment")
                title_slides = [
                    slide
                    for slide in outline.get("slides", [])
                    if isinstance(slide, dict) and str(slide.get("type") or "").lower() == "title"
                ]
                if not title_slides:
                    failures.append(f"{preset}: missing title slide")
                else:
                    title_slide = title_slides[0]
                    title_archetype = (
                        title_slide.get("title_archetype")
                        if isinstance(title_slide.get("title_archetype"), dict)
                        else {}
                    )
                    if not title_archetype.get("archetype_id") or not title_slide.get("kicker"):
                        failures.append(f"{preset}: title slide missing archetype/kicker")
                for field in REQUIRED_RENDERER_FIELDS:
                    if str(deck_style.get(field) or "") != str(renderer_fields.get(field) or ""):
                        failures.append(
                            f"{preset}: renderer treatment field {field} does not match outline deck_style"
                        )
                table_slide_treatments = {
                    str(slide.get("table_treatment") or "")
                    for slide in outline.get("slides", [])
                    if isinstance(slide, dict) and str(slide.get("variant") or "") in {"table", "lab-run-results"}
                }
                if not any(item for item in table_slide_treatments):
                    failures.append(f"{preset}: table slides missing explicit table_treatment")
                reference_slides = [
                    slide
                    for slide in outline.get("slides", [])
                    if isinstance(slide, dict) and str(slide.get("treatment_key") or "") == "references"
                ]
                if not reference_slides:
                    failures.append(f"{preset}: missing references treatment slide")
                else:
                    reference_slide = reference_slides[0]
                    reference_variant = str(reference_slide.get("variant") or "").strip().lower()
                    reference_archetype = (
                        reference_slide.get("reference_archetype")
                        if isinstance(reference_slide.get("reference_archetype"), dict)
                        else {}
                    )
                    if not reference_archetype.get("archetype_id"):
                        failures.append(f"{preset}: references slide missing archetype")
                    if reference_variant == "table" and reference_slide.get("table_style") != "references":
                        failures.append(f"{preset}: references table slide missing table_style")
                style_reference = metadata.get("style_reference") if isinstance(metadata.get("style_reference"), dict) else {}
                if style_reference.get("reference_id") != reference_id:
                    failures.append(f"{preset}: metadata/reference id mismatch")
                storyboard = (
                    style_reference.get("example_storyboard")
                    if isinstance(style_reference.get("example_storyboard"), dict)
                    else {}
                )
                if storyboard.get("topic") != record.get("example_storyboard_topic"):
                    failures.append(f"{preset}: metadata/storyboard topic mismatch")
                chart = storyboard.get("chart") if isinstance(storyboard.get("chart"), dict) else {}
                if not chart.get("title") or not chart.get("labels"):
                    failures.append(f"{preset}: metadata/storyboard chart missing")
                metadata_source_intake = (
                    style_reference.get("style_source_intake")
                    if isinstance(style_reference.get("style_source_intake"), dict)
                    else {}
                )
                if metadata_source_intake.get("route_id") != source_intake.get("route_id"):
                    failures.append(f"{preset}: metadata/source intake route mismatch")
                layout_playbook = (
                    style_reference.get("layout_playbook")
                    if isinstance(style_reference.get("layout_playbook"), dict)
                    else {}
                )
                if layout_playbook.get("playbook_version") != "style_reference_layout_playbook_v1":
                    failures.append(f"{preset}: metadata missing layout playbook")
                metadata_archetypes = (
                    layout_playbook.get("treatment_archetypes")
                    if isinstance(layout_playbook.get("treatment_archetypes"), dict)
                    else {}
                )
                if not metadata_archetypes.get("title") or not metadata_archetypes.get("references"):
                    failures.append(f"{preset}: metadata missing treatment archetypes")
                metadata_recipe_library = (
                    style_reference.get("content_recipe_library")
                    if isinstance(style_reference.get("content_recipe_library"), dict)
                    else {}
                )
                if metadata_recipe_library.get("library_version") != CONTENT_RECIPE_LIBRARY_VERSION:
                    failures.append(f"{preset}: metadata missing content recipe library")

        if len(content_signature_owners) != len(SAMPLE_PRESETS):
            failures.append("gallery first-four content signatures are not unique across all presets")
        if len(renderer_signature_owners) != len(SAMPLE_PRESETS):
            failures.append("gallery renderer treatment signatures are not unique across all presets")
        if len(content_recipe_signature_owners) != len(SAMPLE_PRESETS):
            failures.append("gallery content recipe library signatures are not unique across all presets")
        if len(style_metric_signature_owners) != len(SAMPLE_PRESETS):
            failures.append("gallery style metric signatures are not unique across all presets")
        for treatment_key in REQUIRED_CONTENT_TREATMENTS:
            if len(treatment_archetype_owners[treatment_key]) != len(SAMPLE_PRESETS):
                failures.append(f"gallery {treatment_key} archetype ids are not unique across all presets")
        required_unique_counts = {
            "title_layout": 4,
            "footer_mode": 2,
            "chart_treatment": 3,
            "table_treatment": 4,
            "figure_table_treatment": 4,
        }
        for field, minimum in required_unique_counts.items():
            unique_count = len(renderer_field_counts.get(field, {}))
            if unique_count < minimum:
                failures.append(
                    f"renderer treatment field {field} unique count {unique_count} below {minimum}"
                )
        overloaded_openers = {
            variant: count
            for variant, count in first_content_variant_counts.items()
            if count > 3
        }
        if overloaded_openers:
            failures.append(f"too many presets share first content variant: {overloaded_openers}")

        result = {
            "passed": not failures,
            "sample_presets": SAMPLE_PRESETS,
            "unique_content_signature_count": len(content_signature_owners),
            "unique_renderer_treatment_signature_count": len(renderer_signature_owners),
            "unique_content_recipe_signature_count": len(content_recipe_signature_owners),
            "unique_style_metric_signature_count": len(style_metric_signature_owners),
            "structural_playbook_unique_counts": structural_unique_counts,
            "structural_archetype_unique_counts": {
                key: len(value) for key, value in treatment_archetype_owners.items()
            },
            "structural_archetype_semantic_unique_counts": structural_semantic_unique_counts,
            "first_content_variant_counts": dict(sorted(first_content_variant_counts.items())),
            "renderer_treatment_counts": {
                field: dict(sorted(counts.items()))
                for field, counts in sorted(renderer_field_counts.items())
            },
            "summary": str(outdir / "summary.json"),
            "stdout_tail": stdout[-1200:],
            "failures": failures,
        }
        print(json.dumps(result, indent=2))
        return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
