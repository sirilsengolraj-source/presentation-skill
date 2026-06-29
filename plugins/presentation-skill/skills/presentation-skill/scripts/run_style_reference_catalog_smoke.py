#!/usr/bin/env python3
"""Fast smoke check for the synthetic style-reference catalog."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from style_reference_catalog import (
    CONTENT_RECIPE_LIBRARY_VERSION,
    EXAMPLE_STORYBOARD_VERSION,
    LAYOUT_PLAYBOOK_VERSION,
    REQUIRED_CONTENT_RECIPE_FIELDS,
    REQUIRED_CONTENT_TREATMENTS,
    REQUIRED_LAYOUT_PLAYBOOK_FIELDS,
    REQUIRED_STYLE_METRIC_FIELDS,
    REQUIRED_STORYBOARD_FIELDS,
    STYLE_REFERENCE_VERSION,
    STYLE_REFERENCE_MIX_PLAN_VERSION,
    STYLE_METRIC_PROFILE_VERSION,
    STRUCTURAL_MOTIF_LIBRARY_VERSION,
    preset_example_storyboard,
    preset_style_metric_profile,
    preset_structural_motif,
    preset_style_reference,
    rank_style_references,
    style_reference_mix_plan,
)
from style_reference_sources import (
    SOURCE_MANIFEST_VERSION,
    load_style_reference_source_manifest,
    preset_source_intake_route,
    style_reference_source_summary,
    validate_style_reference_source_manifest,
)


ROOT = Path(__file__).resolve().parent.parent


MIN_PROMPT_TOP_SCORE = 8
MIN_PROMPT_MARGIN = 3

PROMPT_EXPECTATIONS = [
    {
        "name": "clinical executive evidence",
        "prompt": "hospital clinical pathway executive evidence review translational",
        "expected": "executive-clinical",
    },
    {
        "name": "startup pitch narrative",
        "prompt": "startup launch pitch growth product story",
        "expected": "bold-startup-narrative",
    },
    {
        "name": "board analytics memo",
        "prompt": "board metrics quarterly variance analytics dashboard review",
        "expected": "data-heavy-boardroom",
    },
    {
        "name": "investor unit economics",
        "prompt": "investor fundraising unit economics capital memo",
        "expected": "sunset-investor",
    },
    {
        "name": "field policy research",
        "prompt": "field ecology climate sustainability policy report",
        "expected": "forest-research",
    },
    {
        "name": "technical incident console",
        "prompt": "dark cybersecurity AI model monitoring incident console",
        "expected": "midnight-neon",
    },
    {
        "name": "journal methods note",
        "prompt": "journal methods results academic paper concordance note",
        "expected": "paper-journal",
    },
    {
        "name": "minimal architecture postmortem",
        "prompt": "minimal technical postmortem system architecture brief",
        "expected": "arctic-minimal",
    },
    {
        "name": "risk remediation memo",
        "prompt": "risk safety incident remediation control audit",
        "expected": "charcoal-safety",
    },
    {
        "name": "ops queue workbench",
        "prompt": "operations queue workflow SLA support workbench review",
        "expected": "lavender-ops",
    },
    {
        "name": "human-centered case brief",
        "prompt": "service case study museum membership community hospitality",
        "expected": "warm-terracotta",
    },
    {
        "name": "lab validation report",
        "prompt": "lab assay sequencing validation LOD sample report",
        "expected": "lab-report",
    },
    {
        "name": "editorial civic brief",
        "prompt": "editorial narrative civic magazine essay public-facing",
        "expected": "editorial-minimal",
    },
]

MIX_PLAN_EXPECTATIONS = [
    {
        "name": "clinical investor hybrid",
        "prompt": "clinical investor unit economics memo for hospital pathway decision",
        "expected_primary": "sunset-investor",
        "required_secondary": ["executive-clinical"],
    },
    {
        "name": "ops board hybrid",
        "prompt": "operations dashboard for support queue with board metrics and owner actions",
        "expected_primary": "lavender-ops",
        "required_secondary": ["data-heavy-boardroom"],
    },
    {
        "name": "field journal hybrid",
        "prompt": "field ecology policy brief with academic methods and results",
        "expected_primary": "forest-research",
        "required_secondary": ["paper-journal"],
    },
    {
        "name": "technical risk hybrid",
        "prompt": "technical postmortem for AI model incident console",
        "expected_primary": "midnight-neon",
        "required_secondary": ["charcoal-safety", "arctic-minimal"],
    },
]


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _preset_names(repo: Path) -> list[str]:
    script = (
        "const {listPresets}=require('./templates/pptxgenjs/presets.js'); "
        "console.log(JSON.stringify(listPresets()));"
    )
    result = _run(["node", "-e", script], cwd=repo)
    if result.returncode != 0:
        raise RuntimeError(result.stdout)
    return [str(name) for name in json.loads(result.stdout)]


def main() -> int:
    failures: list[dict[str, Any]] = []
    presets = _preset_names(ROOT)
    source_manifest = load_style_reference_source_manifest()
    source_failures = validate_style_reference_source_manifest(source_manifest, supported_presets=presets)
    if source_failures:
        failures.append({"reason": "source_manifest_invalid", "failures": source_failures})
    source_summary = style_reference_source_summary(source_manifest)
    if source_summary.get("manifest_version") != SOURCE_MANIFEST_VERSION:
        failures.append({"reason": "source_manifest_wrong_version", "summary": source_summary})
    if source_summary.get("route_count") != len(presets):
        failures.append({"reason": "source_manifest_route_count_mismatch", "summary": source_summary})
    reference_ids: dict[str, str] = {}
    style_dna_values: dict[str, str] = {}
    treatment_signatures: dict[str, str] = {}
    recipe_library_signatures: dict[str, str] = {}
    motif_signatures: dict[str, str] = {}
    metric_signatures: dict[str, str] = {}
    storyboard_topics: dict[str, str] = {}
    treatment_archetype_ids: dict[str, dict[str, str]] = {key: {} for key in REQUIRED_CONTENT_TREATMENTS}

    for preset in presets:
        reference = preset_style_reference(preset)
        storyboard = (
            reference.get("example_storyboard")
            if isinstance(reference.get("example_storyboard"), dict)
            else {}
        )
        direct_storyboard = preset_example_storyboard(preset)
        treatments = (
            reference.get("content_treatments")
            if isinstance(reference.get("content_treatments"), dict)
            else {}
        )
        playbook = (
            reference.get("layout_playbook")
            if isinstance(reference.get("layout_playbook"), dict)
            else {}
        )
        recipe_library = (
            reference.get("content_recipe_library")
            if isinstance(reference.get("content_recipe_library"), dict)
            else {}
        )
        motif = (
            reference.get("structural_motif_library")
            if isinstance(reference.get("structural_motif_library"), dict)
            else {}
        )
        direct_motif = preset_structural_motif(preset)
        metric_profile = (
            reference.get("style_metric_profile")
            if isinstance(reference.get("style_metric_profile"), dict)
            else {}
        )
        direct_metric_profile = preset_style_metric_profile(preset)
        reference_id = str(reference.get("reference_id") or "").strip()
        style_dna = str(reference.get("style_dna") or "").strip()
        if reference.get("catalog_version") != STYLE_REFERENCE_VERSION:
            failures.append({"preset": preset, "reason": "wrong_catalog_version"})
        if reference.get("style_preset") != preset:
            failures.append({"preset": preset, "reason": "preset_mismatch", "reference": reference.get("style_preset")})
        if reference.get("source_status") != "synthetic_original_publish_safe":
            failures.append({"preset": preset, "reason": "non_synthetic_source_status", "source_status": reference.get("source_status")})
        if motif.get("motif_library_version") != STRUCTURAL_MOTIF_LIBRARY_VERSION:
            failures.append({"preset": preset, "reason": "missing_or_wrong_structural_motif_version", "motif": motif})
        if motif.get("motif_signature") != direct_motif.get("motif_signature"):
            failures.append(
                {
                    "preset": preset,
                    "reason": "structural_motif_helper_mismatch",
                    "reference_motif": motif.get("motif_signature"),
                    "helper_motif": direct_motif.get("motif_signature"),
                }
            )
        if len(motif.get("layout_motifs") if isinstance(motif.get("layout_motifs"), list) else []) < 3:
            failures.append({"preset": preset, "reason": "structural_motif_too_thin", "motif": motif})
        motif_signature = str(motif.get("motif_signature") or "").strip()
        if not motif_signature or motif_signature in motif_signatures:
            failures.append(
                {
                    "preset": preset,
                    "reason": "duplicate_or_missing_structural_motif_signature",
                    "matches": motif_signatures.get(motif_signature),
                }
            )
        motif_signatures[motif_signature] = preset
        missing_metric_fields = [
            key
            for key in REQUIRED_STYLE_METRIC_FIELDS
            if key not in metric_profile or metric_profile.get(key) in (None, "", [], {})
        ]
        if missing_metric_fields:
            failures.append({"preset": preset, "reason": "missing_style_metric_fields", "missing": missing_metric_fields})
        if metric_profile.get("metric_profile_version") != STYLE_METRIC_PROFILE_VERSION:
            failures.append({"preset": preset, "reason": "style_metric_wrong_version", "style_metric_profile": metric_profile})
        if metric_profile.get("metric_signature") != direct_metric_profile.get("metric_signature"):
            failures.append(
                {
                    "preset": preset,
                    "reason": "style_metric_helper_mismatch",
                    "reference_metric": metric_profile.get("metric_signature"),
                    "helper_metric": direct_metric_profile.get("metric_signature"),
                }
            )
        try:
            whitespace_target = float(metric_profile.get("whitespace_ratio_target"))
        except (TypeError, ValueError):
            whitespace_target = -1.0
        body_budget = (
            metric_profile.get("body_words_per_content_slide")
            if isinstance(metric_profile.get("body_words_per_content_slide"), list)
            else []
        )
        max_objects = int(metric_profile.get("max_primary_objects") or 0) if str(metric_profile.get("max_primary_objects") or "").isdigit() else 0
        evidence_mix = metric_profile.get("evidence_object_mix") if isinstance(metric_profile.get("evidence_object_mix"), dict) else {}
        if not 0.12 <= whitespace_target <= 0.55:
            failures.append({"preset": preset, "reason": "style_metric_bad_whitespace_target", "value": metric_profile.get("whitespace_ratio_target")})
        if len(body_budget) != 2 or not all(isinstance(item, int) for item in body_budget) or body_budget[0] < 10 or body_budget[1] < body_budget[0] or body_budget[1] > 90:
            failures.append({"preset": preset, "reason": "style_metric_bad_body_budget", "body_words_per_content_slide": body_budget})
        if max_objects < 1 or max_objects > 4:
            failures.append({"preset": preset, "reason": "style_metric_bad_max_primary_objects", "value": metric_profile.get("max_primary_objects")})
        missing_mix_keys = sorted({"chart", "table", "figure", "prose"} - {str(key) for key in evidence_mix})
        if missing_mix_keys:
            failures.append({"preset": preset, "reason": "style_metric_missing_mix_keys", "missing": missing_mix_keys})
        for key in ("artifact_bias", "readability_bias"):
            if len(metric_profile.get(key) if isinstance(metric_profile.get(key), list) else []) < 2:
                failures.append({"preset": preset, "reason": f"style_metric_{key}_too_thin", key: metric_profile.get(key)})
        metric_signature = str(metric_profile.get("metric_signature") or "").strip()
        if not metric_signature or metric_signature in metric_signatures:
            failures.append(
                {
                    "preset": preset,
                    "reason": "duplicate_or_missing_style_metric_signature",
                    "matches": metric_signatures.get(metric_signature),
                }
            )
        metric_signatures[metric_signature] = preset
        source_intake = (
            reference.get("style_source_intake")
            if isinstance(reference.get("style_source_intake"), dict)
            else {}
        )
        direct_route = preset_source_intake_route(preset, source_manifest)
        if source_intake.get("manifest_version") != SOURCE_MANIFEST_VERSION:
            failures.append({"preset": preset, "reason": "missing_source_intake_manifest", "source_intake": source_intake})
        if source_intake.get("route_id") != direct_route.get("route_id"):
            failures.append(
                {
                    "preset": preset,
                    "reason": "source_intake_route_mismatch",
                    "reference_route": source_intake.get("route_id"),
                    "manifest_route": direct_route.get("route_id"),
                }
            )
        if source_intake.get("derivation_mode") != "synthetic_reconstruction":
            failures.append({"preset": preset, "reason": "unexpected_source_derivation_mode", "source_intake": source_intake})
        if not source_intake.get("source_ids") or not source_intake.get("sources"):
            failures.append({"preset": preset, "reason": "source_intake_missing_sources", "source_intake": source_intake})
        source_scope = set(source_intake.get("content_treatment_scope") if isinstance(source_intake.get("content_treatment_scope"), list) else [])
        if set(REQUIRED_CONTENT_TREATMENTS) - source_scope:
            failures.append(
                {
                    "preset": preset,
                    "reason": "source_intake_missing_treatment_scope",
                    "missing": sorted(set(REQUIRED_CONTENT_TREATMENTS) - source_scope),
                }
            )
        if storyboard.get("storyboard_version") != EXAMPLE_STORYBOARD_VERSION:
            failures.append({"preset": preset, "reason": "missing_storyboard_version", "storyboard": storyboard})
        if storyboard.get("topic") != direct_storyboard.get("topic"):
            failures.append(
                {
                    "preset": preset,
                    "reason": "storyboard_helper_mismatch",
                    "reference_topic": storyboard.get("topic"),
                    "helper_topic": direct_storyboard.get("topic"),
                }
            )
        missing_storyboard_fields = [
            key
            for key in REQUIRED_STORYBOARD_FIELDS
            if key not in storyboard or storyboard.get(key) in (None, "", [], {})
        ]
        if missing_storyboard_fields:
            failures.append({"preset": preset, "reason": "missing_storyboard_fields", "missing": missing_storyboard_fields})
        topic = str(storyboard.get("topic") or "").strip()
        if not topic or topic in storyboard_topics:
            failures.append({"preset": preset, "reason": "duplicate_or_missing_storyboard_topic", "topic": topic})
        storyboard_topics[topic] = preset
        chart = storyboard.get("chart") if isinstance(storyboard.get("chart"), dict) else {}
        labels = chart.get("labels") if isinstance(chart.get("labels"), list) else []
        values = chart.get("values") if isinstance(chart.get("values"), list) else []
        if len(labels) < 3 or len(labels) != len(values):
            failures.append({"preset": preset, "reason": "storyboard_chart_bad", "chart": chart})
        for key in ("dashboard_facts", "source_notes"):
            if len(storyboard.get(key) if isinstance(storyboard.get(key), list) else []) < 2:
                failures.append({"preset": preset, "reason": f"storyboard_{key}_too_thin"})
        for key in ("table", "decision"):
            item = storyboard.get(key) if isinstance(storyboard.get(key), dict) else {}
            if len(item.get("rows") if isinstance(item.get("rows"), list) else []) < 3:
                failures.append({"preset": preset, "reason": f"storyboard_{key}_too_thin", key: item})
        figure = storyboard.get("figure") if isinstance(storyboard.get("figure"), dict) else {}
        if len(figure.get("sections") if isinstance(figure.get("sections"), list) else []) < 2:
            failures.append({"preset": preset, "reason": "storyboard_figure_sections_too_thin", "figure": figure})
        comparison = storyboard.get("comparison") if isinstance(storyboard.get("comparison"), dict) else {}
        if not comparison.get("left_title") or not comparison.get("right_title") or not comparison.get("verdict"):
            failures.append({"preset": preset, "reason": "storyboard_comparison_bad", "comparison": comparison})
        if not reference_id or reference_id in reference_ids:
            failures.append({"preset": preset, "reason": "duplicate_or_missing_reference_id", "reference_id": reference_id})
        if not style_dna or style_dna in style_dna_values:
            failures.append({"preset": preset, "reason": "duplicate_or_missing_style_dna", "style_dna": style_dna})
        missing = [
            key
            for key in REQUIRED_CONTENT_TREATMENTS
            if not str(treatments.get(key) or "").strip()
        ]
        if missing:
            failures.append({"preset": preset, "reason": "missing_content_treatments", "missing": missing})
        signature = "\n".join(str(treatments.get(key) or "") for key in REQUIRED_CONTENT_TREATMENTS)
        if signature in treatment_signatures:
            failures.append(
                {
                    "preset": preset,
                    "reason": "duplicate_treatment_signature",
                    "matches": treatment_signatures[signature],
                }
            )
        missing_playbook_fields = [
            key
            for key in REQUIRED_LAYOUT_PLAYBOOK_FIELDS
            if key not in playbook
        ]
        if missing_playbook_fields:
            failures.append({"preset": preset, "reason": "missing_layout_playbook_fields", "missing": missing_playbook_fields})
        if playbook.get("playbook_version") != LAYOUT_PLAYBOOK_VERSION:
            failures.append({"preset": preset, "reason": "wrong_layout_playbook_version"})
        treatment_map = playbook.get("treatment_variant_map") if isinstance(playbook.get("treatment_variant_map"), dict) else {}
        missing_treatment_maps = [
            key
            for key in REQUIRED_CONTENT_TREATMENTS
            if not isinstance(treatment_map.get(key), list) or not treatment_map.get(key)
        ]
        if missing_treatment_maps:
            failures.append({"preset": preset, "reason": "missing_treatment_variant_map", "missing": missing_treatment_maps})
        treatment_archetypes = (
            playbook.get("treatment_archetypes")
            if isinstance(playbook.get("treatment_archetypes"), dict)
            else {}
        )
        missing_treatment_archetypes = [
            key
            for key in REQUIRED_CONTENT_TREATMENTS
            if not isinstance(treatment_archetypes.get(key), dict)
            or not str(treatment_archetypes.get(key, {}).get("archetype_id") or "").strip()
            or not str(treatment_archetypes.get(key, {}).get("archetype_signature") or "").strip()
            or len(treatment_archetypes.get(key, {}).get("required_fields") if isinstance(treatment_archetypes.get(key, {}).get("required_fields"), list) else []) < 2
        ]
        if missing_treatment_archetypes:
            failures.append(
                {
                    "preset": preset,
                    "reason": "missing_or_thin_treatment_archetypes",
                    "missing": missing_treatment_archetypes,
                    "treatment_archetypes": treatment_archetypes,
                }
            )
        for treatment_key in REQUIRED_CONTENT_TREATMENTS:
            archetype = treatment_archetypes.get(treatment_key) if isinstance(treatment_archetypes.get(treatment_key), dict) else {}
            archetype_id = str(archetype.get("archetype_id") or "").strip()
            if archetype_id:
                previous = treatment_archetype_ids[treatment_key].get(archetype_id)
                if previous:
                    failures.append(
                        {
                            "preset": preset,
                            "reason": "duplicate_treatment_archetype_id",
                            "treatment_key": treatment_key,
                            "archetype_id": archetype_id,
                            "matches": previous,
                        }
                    )
                treatment_archetype_ids[treatment_key][archetype_id] = preset
        preferred = playbook.get("preferred_variants") if isinstance(playbook.get("preferred_variants"), list) else []
        showcase = playbook.get("gallery_showcase_variants") if isinstance(playbook.get("gallery_showcase_variants"), list) else []
        avoid = playbook.get("avoid_variants") if isinstance(playbook.get("avoid_variants"), list) else []
        archetypes = playbook.get("slide_archetypes") if isinstance(playbook.get("slide_archetypes"), list) else []
        if len(preferred) < 5 or len(archetypes) < 5:
            failures.append(
                {
                    "preset": preset,
                    "reason": "layout_playbook_too_thin",
                    "preferred_count": len(preferred),
                    "archetype_count": len(archetypes),
                }
            )
        preferred_conflicts = sorted(set(str(item) for item in preferred) & set(str(item) for item in avoid))
        showcase_conflicts = sorted(set(str(item) for item in showcase) & set(str(item) for item in avoid))
        if preferred_conflicts or showcase_conflicts:
            failures.append(
                {
                    "preset": preset,
                    "reason": "layout_playbook_avoid_conflict",
                    "preferred_conflicts": preferred_conflicts,
                    "showcase_conflicts": showcase_conflicts,
                }
            )
        if not playbook.get("content_rules") or not playbook.get("opening_sequence"):
            failures.append({"preset": preset, "reason": "layout_playbook_missing_rules_or_sequence"})
        if recipe_library.get("library_version") != CONTENT_RECIPE_LIBRARY_VERSION:
            failures.append({"preset": preset, "reason": "content_recipe_library_wrong_version", "content_recipe_library": recipe_library})
        recipes = recipe_library.get("recipes") if isinstance(recipe_library.get("recipes"), dict) else {}
        missing_recipe_keys = [key for key in REQUIRED_CONTENT_TREATMENTS if key not in recipes]
        if missing_recipe_keys:
            failures.append({"preset": preset, "reason": "content_recipe_library_missing_recipes", "missing": missing_recipe_keys})
        recipe_signature_parts: list[str] = []
        for treatment_key in REQUIRED_CONTENT_TREATMENTS:
            recipe = recipes.get(treatment_key) if isinstance(recipes.get(treatment_key), dict) else {}
            missing_recipe_fields = [
                field
                for field in REQUIRED_CONTENT_RECIPE_FIELDS
                if field not in recipe or recipe.get(field) in (None, "", [], {})
            ]
            if missing_recipe_fields:
                failures.append(
                    {
                        "preset": preset,
                        "treatment_key": treatment_key,
                        "reason": "content_recipe_missing_fields",
                        "missing": missing_recipe_fields,
                    }
                )
            if recipe.get("recipe_version") != CONTENT_RECIPE_LIBRARY_VERSION:
                failures.append({"preset": preset, "treatment_key": treatment_key, "reason": "content_recipe_wrong_version"})
            recipe_archetype = (
                recipe.get("treatment_archetype")
                if isinstance(recipe.get("treatment_archetype"), dict)
                else {}
            )
            if not str(recipe_archetype.get("archetype_id") or "").strip():
                failures.append(
                    {
                        "preset": preset,
                        "treatment_key": treatment_key,
                        "reason": "content_recipe_missing_treatment_archetype",
                        "recipe": recipe,
                    }
                )
            unsupported_variants = [
                str(item)
                for item in recipe.get("primary_variants", [])
                if str(item) not in playbook.get("preferred_variants", []) and str(item) not in treatment_map.get(treatment_key, [])
            ]
            if unsupported_variants:
                failures.append(
                    {
                        "preset": preset,
                        "treatment_key": treatment_key,
                        "reason": "content_recipe_variant_not_in_playbook",
                        "variants": unsupported_variants,
                    }
                )
            recipe_signature_parts.append(str(recipe.get("recipe_signature") or ""))
        library_signature = "\n".join(recipe_signature_parts)
        if not library_signature.strip() or library_signature in recipe_library_signatures:
            failures.append(
                {
                    "preset": preset,
                    "reason": "duplicate_or_missing_content_recipe_signature",
                    "matches": recipe_library_signatures.get(library_signature),
                }
            )
        recipe_library_signatures[library_signature] = preset
        reference_ids[reference_id] = preset
        style_dna_values[style_dna] = preset
        treatment_signatures[signature] = preset

    covered_prompt_presets = sorted({str(item["expected"]) for item in PROMPT_EXPECTATIONS})
    if covered_prompt_presets != sorted(presets):
        failures.append(
            {
                "reason": "prompt_expectations_do_not_cover_presets",
                "expected_presets": sorted(presets),
                "covered_presets": covered_prompt_presets,
            }
        )

    rank_results: list[dict[str, Any]] = []
    for expectation in PROMPT_EXPECTATIONS:
        name = str(expectation["name"])
        prompt = str(expectation["prompt"])
        expected = str(expectation["expected"])
        matches = rank_style_references(prompt, limit=5)
        top = matches[0].get("style_preset") if matches else ""
        top_score = int(matches[0].get("score") or 0) if matches else 0
        second_score = int(matches[1].get("score") or 0) if len(matches) > 1 else 0
        margin = top_score - second_score
        top_matches = [
            {"style_preset": item.get("style_preset"), "score": item.get("score")}
            for item in matches[:3]
        ]
        rank_results.append(
            {
                "name": name,
                "prompt": prompt,
                "expected": expected,
                "top": top,
                "top_score": top_score,
                "score_margin": margin,
                "top_matches": top_matches,
            }
        )
        if top != expected:
            failures.append(
                {
                    "reason": "rank_mismatch",
                    "name": name,
                    "prompt": prompt,
                    "expected": expected,
                    "top": top,
                    "matches": top_matches,
                }
            )
        if top_score < MIN_PROMPT_TOP_SCORE:
            failures.append(
                {
                    "reason": "rank_score_too_low",
                    "name": name,
                    "prompt": prompt,
                    "expected": expected,
                    "top": top,
                    "top_score": top_score,
                    "minimum": MIN_PROMPT_TOP_SCORE,
                    "matches": top_matches,
                }
            )
        if margin < MIN_PROMPT_MARGIN:
            failures.append(
                {
                    "reason": "rank_margin_too_low",
                    "name": name,
                    "prompt": prompt,
                    "expected": expected,
                    "top": top,
                    "score_margin": margin,
                    "minimum": MIN_PROMPT_MARGIN,
                    "matches": top_matches,
                }
            )

    mix_plan_results: list[dict[str, Any]] = []
    for expectation in MIX_PLAN_EXPECTATIONS:
        name = str(expectation["name"])
        prompt = str(expectation["prompt"])
        expected_primary = str(expectation["expected_primary"])
        required_secondary = [str(item) for item in expectation.get("required_secondary", [])]
        mix_plan = style_reference_mix_plan(prompt, limit=3)
        if mix_plan.get("mix_plan_version") != STYLE_REFERENCE_MIX_PLAN_VERSION:
            failures.append({"reason": "mix_plan_wrong_version", "name": name, "mix_plan": mix_plan})
        primary = mix_plan.get("primary") if isinstance(mix_plan.get("primary"), dict) else {}
        secondaries = (
            mix_plan.get("secondary_influences")
            if isinstance(mix_plan.get("secondary_influences"), list)
            else []
        )
        treatment_mix = mix_plan.get("treatment_mix") if isinstance(mix_plan.get("treatment_mix"), dict) else {}
        secondary_presets = [str(item.get("style_preset") or "") for item in secondaries if isinstance(item, dict)]
        mix_plan_results.append(
            {
                "name": name,
                "prompt": prompt,
                "expected_primary": expected_primary,
                "primary": primary.get("style_preset"),
                "secondary_influences": secondary_presets,
            }
        )
        if primary.get("style_preset") != expected_primary:
            failures.append(
                {
                    "reason": "mix_plan_primary_unexpected",
                    "name": name,
                    "expected_primary": expected_primary,
                    "primary": primary,
                    "secondary_influences": secondary_presets,
                }
            )
        primary_metric = primary.get("style_metric_profile") if isinstance(primary.get("style_metric_profile"), dict) else {}
        if primary_metric.get("metric_profile_version") != STYLE_METRIC_PROFILE_VERSION or not primary_metric.get("metric_signature"):
            failures.append({"reason": "mix_plan_missing_primary_style_metric", "name": name, "primary": primary})
        missing_secondary = sorted(set(required_secondary) - set(secondary_presets))
        if missing_secondary:
            failures.append(
                {
                    "reason": "mix_plan_missing_required_secondary",
                    "name": name,
                    "missing": missing_secondary,
                    "secondary_influences": secondary_presets,
                    "mix_plan": mix_plan,
                }
            )
        missing_mix_treatments = [key for key in REQUIRED_CONTENT_TREATMENTS if key not in treatment_mix]
        if missing_mix_treatments:
            failures.append({"reason": "mix_plan_missing_treatments", "name": name, "missing": missing_mix_treatments})
        empty_primary_treatments = [
            key
            for key in REQUIRED_CONTENT_TREATMENTS
            if not str((treatment_mix.get(key) or {}).get("primary") if isinstance(treatment_mix.get(key), dict) else "")
        ]
        if empty_primary_treatments:
            failures.append({"reason": "mix_plan_empty_primary_treatments", "name": name, "missing": empty_primary_treatments})
        if required_secondary:
            secondary_metric_missing = [
                str(item.get("style_preset") or "")
                for item in secondaries
                if isinstance(item, dict)
                and (
                    not isinstance(item.get("style_metric_profile"), dict)
                    or item["style_metric_profile"].get("metric_profile_version") != STYLE_METRIC_PROFILE_VERSION
                    or not item["style_metric_profile"].get("metric_signature")
                )
            ]
            if secondary_metric_missing:
                failures.append({"reason": "mix_plan_missing_secondary_style_metrics", "name": name, "missing": secondary_metric_missing})
            treatment_keys_with_secondary = [
                key
                for key, value in treatment_mix.items()
                if isinstance(value, dict) and value.get("optional_secondary_influences")
            ]
            if not treatment_keys_with_secondary:
                failures.append({"reason": "mix_plan_no_treatment_secondary_options", "name": name, "mix_plan": mix_plan})
        if not mix_plan.get("mixing_rules"):
            failures.append({"reason": "mix_plan_missing_rules", "name": name})

    summary = {
        "passed": not failures,
        "catalog_version": STYLE_REFERENCE_VERSION,
        "layout_playbook_version": LAYOUT_PLAYBOOK_VERSION,
        "mix_plan_version": STYLE_REFERENCE_MIX_PLAN_VERSION,
        "example_storyboard_version": EXAMPLE_STORYBOARD_VERSION,
        "content_recipe_library_version": CONTENT_RECIPE_LIBRARY_VERSION,
        "structural_motif_library_version": STRUCTURAL_MOTIF_LIBRARY_VERSION,
        "style_metric_profile_version": STYLE_METRIC_PROFILE_VERSION,
        "source_manifest_version": SOURCE_MANIFEST_VERSION,
        "source_summary": source_summary,
        "preset_count": len(presets),
        "required_content_treatments": list(REQUIRED_CONTENT_TREATMENTS),
        "required_layout_playbook_fields": list(REQUIRED_LAYOUT_PLAYBOOK_FIELDS),
        "required_storyboard_fields": list(REQUIRED_STORYBOARD_FIELDS),
        "required_content_recipe_fields": list(REQUIRED_CONTENT_RECIPE_FIELDS),
        "required_style_metric_fields": list(REQUIRED_STYLE_METRIC_FIELDS),
        "unique_content_recipe_signature_count": len(recipe_library_signatures),
        "unique_structural_motif_signature_count": len(motif_signatures),
        "unique_style_metric_signature_count": len(metric_signatures),
        "unique_treatment_archetype_counts": {
            key: len(value) for key, value in treatment_archetype_ids.items()
        },
        "prompt_coverage_count": len(covered_prompt_presets),
        "prompt_min_top_score": MIN_PROMPT_TOP_SCORE,
        "prompt_min_margin": MIN_PROMPT_MARGIN,
        "rank_results": rank_results,
        "mix_plan_results": mix_plan_results,
        "failures": failures,
    }
    print(json.dumps(summary, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
