#!/usr/bin/env python3
"""Emit a contract-aware prompt for authoring outline.json.

This is the deterministic handoff between a locked deck_design_contract_v1 and
the main-agent source edits that create the real deck outline. It does not
modify source files; it packages the current contract, plans, artifact context,
and authoring rules into a prompt that can be answered directly or pasted into
one outline-authoring subagent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from style_reference_catalog import REQUIRED_CONTENT_TREATMENTS, preset_style_reference


ROOT = Path(__file__).resolve().parent.parent


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_json(path: Path) -> Any | None:
    text = _read_optional(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n... [truncated at {limit} chars]"


def _compact_json(payload: Any, limit: int) -> str:
    if payload is None:
        return "<missing or malformed>"
    return _truncate(json.dumps(payload, indent=2, ensure_ascii=False), limit)


def _workspace_context(workspace: Path, limit: int) -> str:
    files = {
        "deck_start_packet.json": _load_json(workspace / "deck_start_packet.json"),
        "intake_answers.json": _load_json(workspace / "intake_answers.json"),
        "intake_apply_report.json": _load_json(workspace / "intake_apply_report.json"),
        "design_contract.json": _load_json(workspace / "design_contract.json"),
        "design_contract_apply_report.json": _load_json(workspace / "design_contract_apply_report.json"),
        "design_brief.json": _load_json(workspace / "design_brief.json"),
        "content_plan.json": _load_json(workspace / "content_plan.json"),
        "evidence_plan.json": _load_json(workspace / "evidence_plan.json"),
        "asset_plan.json": _load_json(workspace / "asset_plan.json"),
        "outline.json": _load_json(workspace / "outline.json"),
        "assets/artifacts_manifest.json": _load_json(workspace / "assets" / "artifacts_manifest.json"),
        "assets/analysis_summary.json": _load_json(workspace / "assets" / "analysis_summary.json"),
    }
    blocks = [f"Workspace: {workspace}"]
    for name, payload in files.items():
        blocks.append(f"\n{name}:\n{_compact_json(payload, limit)}")
    notes = _read_optional(workspace / "notes.md")
    blocks.append(f"\nnotes.md:\n{_truncate(notes or '<missing>', limit)}")
    return "\n".join(blocks)


def _reference_context(limit: int) -> str:
    refs = {
        "DESIGN.md": ROOT / "DESIGN.md",
        "outline_schema.md": ROOT / "references" / "outline_schema.md",
        "planning_schema.md": ROOT / "references" / "planning_schema.md",
    }
    blocks: list[str] = []
    for label, path in refs.items():
        text = _read_optional(path)
        blocks.append(f"{label}:\n{_truncate(text or '<missing>', limit)}")
    return "\n\n".join(blocks)


def _artifact_alias_summary(workspace: Path) -> str:
    manifest = _load_json(workspace / "assets" / "artifacts_manifest.json")
    if not isinstance(manifest, dict):
        return "<no generated artifact manifest found>"
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        return "<artifact manifest has no outputs>"
    lines: list[str] = []
    for output in outputs[:40]:
        if not isinstance(output, dict):
            continue
        output_id = str(output.get("id") or "").strip()
        title = str(output.get("title") or output_id or "artifact").strip()
        lines.append(f"- output `{output_id or title}`: {title}")
        artifacts = output.get("artifacts")
        if isinstance(artifacts, list):
            for artifact in artifacts[:8]:
                if not isinstance(artifact, dict):
                    continue
                alias = str(artifact.get("alias") or "").strip()
                role = str(artifact.get("role") or "").strip()
                path = str(artifact.get("path") or "").strip()
                if alias or path:
                    lines.append(f"  - {role or 'artifact'} `{alias or path}` from `{path}`")
    return "\n".join(lines) if lines else "<no usable artifact aliases found>"


def _artifact_rebuild_context_summary(workspace: Path, limit: int = 4000) -> str:
    contexts: list[dict[str, Any]] = []
    manifest = _load_json(workspace / "assets" / "artifacts_manifest.json")
    if isinstance(manifest, dict) and isinstance(manifest.get("rebuild_context"), dict):
        contexts.append(
            {
                "source": "assets/artifacts_manifest.json",
                "rebuild_context": manifest.get("rebuild_context"),
            }
        )
    summary = _load_json(workspace / "assets" / "analysis_summary.json")
    if isinstance(summary, dict) and isinstance(summary.get("rebuild_context"), dict):
        summary_context = summary.get("rebuild_context")
        if not contexts or contexts[0].get("rebuild_context") != summary_context:
            contexts.append(
                {
                    "source": "assets/analysis_summary.json",
                    "rebuild_context": summary_context,
                }
            )
    if not contexts:
        return "<no generated artifact rebuild context found>"
    return _compact_json({"contexts": contexts}, limit)


def _slide_quality_context(workspace: Path, limit: int = 4000) -> str:
    for path, key in (
        (workspace / "design_brief.json", "slide_quality_contract"),
        (workspace / "design_contract.json", "slide_quality_contract"),
        (workspace / "deck_start_packet.json", "slide_quality_contract"),
    ):
        payload = _load_json(path)
        if not isinstance(payload, dict):
            continue
        contract = payload.get(key)
        if isinstance(contract, dict):
            return _compact_json(
                {
                    "source": str(path),
                    "slide_quality_contract": contract,
                },
                limit,
            )
    return "<no slide_quality_contract found; derive conservative readability, whitespace, evidence-anchor, artifact, and QA targets from design_brief/readability_contract/qa_contract>"


def _style_preset_from_payload(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("style_system", "visual_system"):
        container = payload.get(key)
        if isinstance(container, dict):
            preset = str(container.get("style_preset") or "").strip()
            if preset:
                return preset
    return str(payload.get("style_preset") or "").strip()


def _compact_treatment_archetype_ids(reference: dict[str, Any]) -> dict[str, str]:
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    archetypes = playbook.get("treatment_archetypes") if isinstance(playbook.get("treatment_archetypes"), dict) else {}
    out: dict[str, str] = {}
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        archetype = archetypes.get(treatment_key) if isinstance(archetypes.get(treatment_key), dict) else {}
        archetype_id = str(archetype.get("archetype_id") or "").strip()
        if archetype_id:
            out[treatment_key] = archetype_id
    return out


def _semantic_archetype_signature(item: dict[str, Any]) -> str:
    material = {
        "structure": item.get("structure"),
        "object_pattern": item.get("object_pattern"),
        "required_fields": item.get("required_fields") if isinstance(item.get("required_fields"), list) else [],
        "primary_variants": item.get("primary_variants") if isinstance(item.get("primary_variants"), list) else [],
        "title_layout": item.get("title_layout"),
        "footer_mode": item.get("footer_mode"),
        "content_goal": item.get("content_goal"),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _compact_treatment_archetypes(reference: dict[str, Any]) -> dict[str, Any]:
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    archetypes = playbook.get("treatment_archetypes") if isinstance(playbook.get("treatment_archetypes"), dict) else {}
    out: dict[str, Any] = {}
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        archetype = archetypes.get(treatment_key) if isinstance(archetypes.get(treatment_key), dict) else {}
        if not archetype:
            continue
        out[treatment_key] = {
            "archetype_id": archetype.get("archetype_id"),
            "structure": archetype.get("structure"),
            "object_pattern": archetype.get("object_pattern"),
            "required_fields": archetype.get("required_fields") if isinstance(archetype.get("required_fields"), list) else [],
            "primary_variants": archetype.get("primary_variants") if isinstance(archetype.get("primary_variants"), list) else [],
            "title_layout": archetype.get("title_layout"),
            "footer_mode": archetype.get("footer_mode"),
            "semantic_signature": archetype.get("semantic_signature") or _semantic_archetype_signature(archetype),
        }
    return out


def _compact_recipe_library(reference: dict[str, Any]) -> dict[str, Any]:
    library = reference.get("content_recipe_library") if isinstance(reference.get("content_recipe_library"), dict) else {}
    recipes = library.get("recipes") if isinstance(library.get("recipes"), dict) else {}
    recipe_archetypes: dict[str, str] = {}
    recipe_slots: dict[str, list[str]] = {}
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        recipe = recipes.get(treatment_key) if isinstance(recipes.get(treatment_key), dict) else {}
        archetype = recipe.get("treatment_archetype") if isinstance(recipe.get("treatment_archetype"), dict) else {}
        archetype_id = str(archetype.get("archetype_id") or "").strip()
        if archetype_id:
            recipe_archetypes[treatment_key] = archetype_id
        slots = recipe.get("required_slots") if isinstance(recipe.get("required_slots"), list) else []
        if slots:
            recipe_slots[treatment_key] = [str(item) for item in slots[:4] if str(item).strip()]
    return {
        "library_version": library.get("library_version"),
        "recipe_archetype_ids": recipe_archetypes,
        "required_slots_by_treatment": recipe_slots,
        "recipe_signatures": library.get("recipe_signatures") if isinstance(library.get("recipe_signatures"), dict) else {},
        "authoring_contract": library.get("authoring_contract") if isinstance(library.get("authoring_contract"), list) else [],
    }


def _compact_style_source_intake(reference: dict[str, Any]) -> dict[str, Any]:
    intake = reference.get("style_source_intake") if isinstance(reference.get("style_source_intake"), dict) else {}
    patterns: list[str] = []
    observations: list[str] = []
    for source in intake.get("sources", []):
        if not isinstance(source, dict):
            continue
        patterns.extend(str(item) for item in source.get("generic_slide_patterns", [])[:2] if str(item).strip())
        observations.extend(str(item) for item in source.get("generic_style_observations", [])[:2] if str(item).strip())
    return {
        "route_id": intake.get("route_id"),
        "source_ids": intake.get("source_ids") if isinstance(intake.get("source_ids"), list) else [],
        "derivation_mode": intake.get("derivation_mode"),
        "use_cases": intake.get("use_cases") if isinstance(intake.get("use_cases"), list) else [],
        "required_synthetic_content": (
            intake.get("required_synthetic_content")
            if isinstance(intake.get("required_synthetic_content"), list)
            else []
        ),
        "generic_slide_patterns": patterns[:6],
        "generic_style_observations": observations[:6],
    }


def _compact_style_metric_profile(reference: dict[str, Any]) -> dict[str, Any]:
    profile = reference.get("style_metric_profile") if isinstance(reference.get("style_metric_profile"), dict) else {}
    return {
        "metric_profile_version": profile.get("metric_profile_version"),
        "density_level": profile.get("density_level"),
        "whitespace_ratio_target": profile.get("whitespace_ratio_target"),
        "body_words_per_content_slide": (
            profile.get("body_words_per_content_slide")
            if isinstance(profile.get("body_words_per_content_slide"), list)
            else []
        ),
        "max_primary_objects": profile.get("max_primary_objects"),
        "visual_hierarchy": profile.get("visual_hierarchy"),
        "evidence_object_mix": (
            profile.get("evidence_object_mix")
            if isinstance(profile.get("evidence_object_mix"), dict)
            else {}
        ),
        "source_burden": profile.get("source_burden"),
        "footer_posture": profile.get("footer_posture"),
        "artifact_bias": profile.get("artifact_bias") if isinstance(profile.get("artifact_bias"), list) else [],
        "readability_bias": (
            profile.get("readability_bias")
            if isinstance(profile.get("readability_bias"), list)
            else []
        ),
        "metric_signature": profile.get("metric_signature"),
    }


def _compact_style_reference_authoring_payload(source: str, payload: Any, reference: dict[str, Any]) -> dict[str, Any]:
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    motif = reference.get("structural_motif_library") if isinstance(reference.get("structural_motif_library"), dict) else {}
    return {
        "source": source,
        "style_preset": _style_preset_from_payload(payload),
        "reference_id": reference.get("reference_id"),
        "reference_name": reference.get("reference_name"),
        "style_dna": reference.get("style_dna"),
        "treatment_archetype_ids": _compact_treatment_archetype_ids(reference),
        "style_source_intake": _compact_style_source_intake(reference),
        "style_metric_profile": _compact_style_metric_profile(reference),
        "layout_playbook": {
            "playbook_version": playbook.get("playbook_version"),
            "preferred_variants": playbook.get("preferred_variants") if isinstance(playbook.get("preferred_variants"), list) else [],
            "gallery_showcase_variants": (
                playbook.get("gallery_showcase_variants")
                if isinstance(playbook.get("gallery_showcase_variants"), list)
                else []
            ),
            "treatment_variant_map": (
                playbook.get("treatment_variant_map")
                if isinstance(playbook.get("treatment_variant_map"), dict)
                else {}
            ),
            "treatment_archetypes": _compact_treatment_archetypes(reference),
            "opening_sequence": playbook.get("opening_sequence") if isinstance(playbook.get("opening_sequence"), list) else [],
            "content_rules": playbook.get("content_rules") if isinstance(playbook.get("content_rules"), list) else [],
            "avoid_variants": playbook.get("avoid_variants") if isinstance(playbook.get("avoid_variants"), list) else [],
        },
        "content_recipe_library": _compact_recipe_library(reference),
        "structural_motif_library": {
            "motif_library_version": motif.get("motif_library_version"),
            "background_structure": motif.get("background_structure"),
            "layout_motifs": motif.get("layout_motifs") if isinstance(motif.get("layout_motifs"), list) else [],
            "content_object_rules": motif.get("content_object_rules") if isinstance(motif.get("content_object_rules"), list) else [],
            "motif_signature": motif.get("motif_signature"),
        },
        "signature_moves": reference.get("signature_moves"),
        "content_treatments": reference.get("content_treatments"),
        "avoid": reference.get("avoid"),
    }


def _style_reference_authoring_context(workspace: Path, limit: int = 5500) -> str:
    for path in (workspace / "design_brief.json", workspace / "design_contract.json"):
        payload = _load_json(path)
        if not isinstance(payload, dict):
            continue
        style_system = payload.get("style_system") if isinstance(payload.get("style_system"), dict) else {}
        reference = style_system.get("style_reference") if isinstance(style_system.get("style_reference"), dict) else {}
        if isinstance(reference, dict) and reference:
            preset = _style_preset_from_payload(payload) or "executive-clinical"
            fallback = preset_style_reference(preset)
            if not isinstance(reference.get("layout_playbook"), dict):
                reference = dict(reference)
                reference["layout_playbook"] = fallback.get("layout_playbook", {})
            if not isinstance(reference.get("content_recipe_library"), dict):
                reference = dict(reference)
                reference["content_recipe_library"] = fallback.get("content_recipe_library", {})
            if not isinstance(reference.get("structural_motif_library"), dict):
                reference = dict(reference)
                reference["structural_motif_library"] = fallback.get("structural_motif_library", {})
            if not isinstance(reference.get("style_source_intake"), dict):
                reference = dict(reference)
                reference["style_source_intake"] = fallback.get("style_source_intake", {})
            if not isinstance(reference.get("style_metric_profile"), dict):
                reference = dict(reference)
                reference["style_metric_profile"] = fallback.get("style_metric_profile", {})
            return _compact_json(_compact_style_reference_authoring_payload(str(path), payload, reference), limit)
    design_brief = _load_json(workspace / "design_brief.json")
    design_contract = _load_json(workspace / "design_contract.json")
    preset = _style_preset_from_payload(design_brief) or _style_preset_from_payload(design_contract) or "executive-clinical"
    reference = preset_style_reference(preset)
    return _compact_json(_compact_style_reference_authoring_payload("fallback from scripts/style_reference_catalog.py", design_brief or design_contract or {"style_preset": preset}, reference), limit)


PROMPT_TEMPLATE = """\
You are authoring the source outline for a reproducible PowerPoint deck.

The design contract is already locked. Your job is NOT to redesign the deck
from scratch. Use the contract, planning files, artifact aliases, and rules
below to produce a source patch packet that the main agent can apply to
`outline.json`, `content_plan.json`, `evidence_plan.json`, `asset_plan.json`,
and `notes.md`.

Return ONLY valid JSON. Do not include prose outside JSON.
Save the JSON as `{workspace}/outline_authoring_handoff.json`, then apply it
with `python3 scripts/apply_outline_authoring_handoff.py --workspace {workspace}
--handoff {workspace}/outline_authoring_handoff.json --report
{workspace}/outline_authoring_handoff_apply_report.json`.

Return this JSON shape:

{{
  "handoff_version": "outline_authoring_handoff_v1",
  "workspace": "{workspace}",
  "contract_alignment": {{
    "style_seed": "copied from design_contract/design_brief",
    "style_preset": "copied from contract",
    "style_reference_id": "copied from style_reference.layout_playbook context",
    "header_footer_plan": "how the locked header/footer system is used",
    "variant_mix_plan": "how structure_blueprint.allowed_variants and style_reference.layout_playbook preferred_variants are used without random cycling",
    "structural_motif_library_used": {{
      "motif_library_version": "style_reference_structural_motif_library_v1",
      "background_structure": "selected reference background_structure",
      "layout_motifs_used": ["motifs that changed the outline, such as run metadata plate or workflow lanes"],
      "content_object_rules_used": ["content-object rules that changed chart/table/figure/source placement"],
      "motif_signature": "selected structural motif signature"
    }},
    "style_metric_profile_used": {{
      "metric_profile_version": "style_reference_metric_profile_v1",
      "metric_signature": "selected reference metric signature",
      "density_level": "selected reference density posture",
      "whitespace_ratio_target": "selected reference whitespace target",
      "body_words_per_content_slide": "selected reference body word budget",
      "max_primary_objects": "selected reference object-count limit",
      "visual_hierarchy": "selected reference evidence scan path",
      "evidence_object_mix": "selected reference chart/table/figure/prose weights"
    }},
    "layout_playbook_used": {{
      "playbook_version": "style_reference_layout_playbook_v1",
      "preferred_variants": ["ordered variants actually used"],
      "treatment_archetypes_used": {{
        "title": "chosen title archetype_id and structure from layout_playbook.treatment_archetypes.title",
        "comparison": "chosen comparison archetype_id and object pattern",
        "chart": "chosen chart archetype_id and object pattern",
        "table": "chosen table archetype_id and object pattern",
        "figure": "chosen figure archetype_id and object pattern",
        "dashboard": "chosen dashboard archetype_id and object pattern",
        "decision": "chosen decision archetype_id and object pattern",
        "references": "chosen references archetype_id and source/provenance structure"
      }},
      "treatment_archetype_semantic_signatures_used": {{
        "title": "copy semantic_signature from layout_playbook.treatment_archetypes.title",
        "comparison": "copy semantic_signature from layout_playbook.treatment_archetypes.comparison",
        "chart": "copy semantic_signature from layout_playbook.treatment_archetypes.chart",
        "table": "copy semantic_signature from layout_playbook.treatment_archetypes.table",
        "figure": "copy semantic_signature from layout_playbook.treatment_archetypes.figure",
        "dashboard": "copy semantic_signature from layout_playbook.treatment_archetypes.dashboard",
        "decision": "copy semantic_signature from layout_playbook.treatment_archetypes.decision",
        "references": "copy semantic_signature from layout_playbook.treatment_archetypes.references"
      }},
      "treatment_variant_map_used": {{
        "title": "chosen title variant",
        "dashboard": "chosen dashboard variant",
        "chart": "chosen chart variant",
        "table": "chosen table variant",
        "figure": "chosen figure variant",
        "comparison": "chosen comparison variant",
        "decision": "chosen decision variant",
        "references": "chosen references variant"
      }},
      "content_rules_used": ["rules from the playbook that changed outline choices"]
    }},
    "content_recipe_library_used": {{
      "library_version": "style_reference_content_recipe_library_v1",
      "recipe_signatures_used": {{
        "chart": "signature copied when chart recipe is used",
        "table": "signature copied when table recipe is used",
        "figure": "signature copied when figure recipe is used"
      }},
      "slide_recipe_map": [
        {{
          "slide_id": "s3",
          "treatment_key": "chart | table | figure | dashboard | comparison | decision | references",
          "recipe_signature": "copied from content_recipe_library.recipes[treatment_key].recipe_signature",
          "required_slots_filled": ["which recipe slots are filled by this slide"],
          "data_roles_bound": ["which recipe data roles are bound to source fields/artifacts"]
        }}
      ]
    }}
  }},
  "artifact_rebuild_plan": {{
    "context_version": "presentation_skill_artifact_rebuild_context_v1 or none",
    "producer_path": "assets/make_figures.py or none",
    "source_paths": ["data/source.csv"],
    "output_paths": ["assets/figures/example.png"],
    "commands_to_preserve": [
      "copy rebuild_context.commands.rebuild_figures when available",
      "copy rebuild_context.commands.inspect_manifest when available",
      "copy rebuild_context.commands.auto_select_lead or auto_select_all when available",
      "copy rebuild_context.commands.validate_planning when available"
    ],
    "notes": "how generated artifacts should be rebuilt or rebound after outline edits"
  }},
  "quality_alignment": {{
    "contract_version": "slide_quality_contract_v1 or derived",
    "readability_targets_used": [
      "min_title_pt=24",
      "min_body_pt=12",
      "chart_label_min_pt=7",
      "footer_reserved_inches=0.25"
    ],
    "layout_targets_used": [
      "evidence_anchor_required",
      "fail_on_awkward_whitespace",
      "avoid_repeated_card_grids",
      "compact_source_footer"
    ],
    "artifact_quality_targets_used": [
      "record generated artifact source fingerprints and producer fingerprints",
      "record image whitespace measurement or trim rule when generated figures are used"
    ],
    "qa_gates_used": [
      "planning_warnings",
      "whitespace_warnings",
      "design_readability_warnings"
    ],
    "required_commands": [
      "copy the relevant slide_quality_contract.qa_gates.required_commands"
    ],
    "outline_choices": "how the chosen slide variants, evidence anchors, and prose density satisfy the quality contract"
  }},
  "source_patch": {{
    "outline_json": {{
      "title": "final deck title",
      "subtitle": "optional subtitle",
      "deck_style": {{}},
      "slides": [
        {{
          "type": "title | content | section",
          "slide_id": "stable ID from structure_blueprint where possible",
          "title": "specific non-placeholder title",
          "subtitle": "optional",
          "variant": "supported variant",
          "slide_intent": "context | evidence | method | comparison | implication | close",
          "visual_intent": "figure | chart | table | image | structured comparison | concise report body",
          "body": "short body text when useful",
          "bullets": [],
          "sources": ["S1: compact source label or citation ID"]
        }}
      ]
    }},
    "content_plan_updates": {{
      "thesis": "deck-level thesis",
      "audience": "target audience",
      "slide_plan": [],
      "narrative_arc": []
    }},
    "evidence_plan_updates": {{
      "source_policy": "none | cite key claim | source every factual claim",
      "items": [],
      "chart_candidates": []
    }},
    "asset_plan_updates": {{
      "images": [],
      "charts": [],
      "tables": [],
      "generated_images": []
    }},
    "notes_append": "manual assumptions, skipped conditional phases, and unresolved inputs"
  }},
  "acceptance_checks": [
    "outline has no TODO/TBD/lorem/[insert]/[placeholder] visible text",
    "every content slide has a visual or evidence anchor",
    "sources match evidence_plan.source_policy",
    "artifact aliases resolve to asset_plan or assets/artifacts_manifest.json",
    "slide IDs resolve across content_plan, evidence_plan, asset_plan, and figure_export_contract",
    "text density stays inside readability_contract budgets",
    "quality_alignment explicitly references slide_quality_contract_v1 targets",
    "run: python3 scripts/report_workspace_readiness.py --workspace {workspace}"
  ],
  "main_agent_handoff": {{
    "files_to_patch": [
      "{workspace}/outline.json",
      "{workspace}/content_plan.json",
      "{workspace}/evidence_plan.json",
      "{workspace}/asset_plan.json",
      "{workspace}/notes.md"
    ],
    "commands_after_patch": [
      "python3 scripts/apply_outline_authoring_handoff.py --workspace {workspace} --handoff {workspace}/outline_authoring_handoff.json --report {workspace}/outline_authoring_handoff_apply_report.json",
      "python3 scripts/report_workspace_readiness.py --workspace {workspace}",
      "python3 scripts/build_workspace.py --workspace {workspace} --qa --skip-render --fail-on-planning-warnings --fail-on-whitespace-warnings --overwrite"
    ]
  }}
}}

Authoring rules:

- Use the locked `deck_design_contract_v1` and applied `design_brief.json`
  decisions. Preserve style_preset, style_seed, palette, background system,
  header/footer treatments, source-line/footer/page-number posture,
  readability_contract, speed_contract, slide_quality_contract, and
  style_mix_matrix.
- Use `structure_blueprint.slide_sequence` as the primary slide order. If a
  slide must be merged, split, or skipped, explain it in `notes_append`.
- Before choosing slide variants, read the Style reference motif grammar and
  layout playbook below. Use `structural_motif_library.background_structure`,
  `layout_motifs`, and `content_object_rules` to decide whether the outline is
  behaving like a lab run report, command console, workflow workbench,
  evidence rail, atlas plate, case-study journey, or editorial masthead before
  picking variants. Record the chosen motif pieces in
  `contract_alignment.structural_motif_library_used`.
- Apply `style_metric_profile` before writing prose: use its density level,
  whitespace target, body-word budget, maximum primary object count, visual
  hierarchy, evidence-object mix, source burden, and artifact/readability bias
  to decide whether to split a slide, change variant, or convert text into a
  chart/table/figure. Record the used values in
  `contract_alignment.style_metric_profile_used`.
- Then use `layout_playbook.opening_sequence` and
  `layout_playbook.treatment_variant_map` to make the preset structurally
  distinct. Example: lab/report decks should naturally start with
  `lab-run-results` or `scientific-figure`, dark technical decks with `stats`,
  `chart`, or `flow`, and editorial decks with `image-sidebar`, `split`, or
  sparse `standard` synthesis.
- Use `layout_playbook.treatment_archetypes` for every slide treatment, not
  just opener/footer: title, comparison, chart, table, figure, dashboard,
  decision, and references. Record the selected archetype IDs/object patterns
  in `contract_alignment.layout_playbook_used.treatment_archetypes_used`.
- Before writing each content slide, choose a recipe from
  `content_recipe_library.recipes` by `treatment_key`. Use its
  `required_slots`, `data_roles`, `primary_variants`, `source_posture`, and
  `authoring_checks` to decide what the slide must contain. Record the chosen
  recipe in `contract_alignment.content_recipe_library_used.slide_recipe_map`
  and keep the slide's `treatment_key` in `outline_json.slides[]`.
- Do not use variants listed in `layout_playbook.avoid_variants` unless the
  evidence shape truly requires it; explain any exception in `notes_append`.
- Fill `quality_alignment` from the Slide quality contract block below. It
  should name the concrete readability floors, whitespace/evidence-anchor
  rules, generated-artifact metadata expectations, and QA gates that changed
  the slide variant or prose-density choices.
- Use only supported outline variants. If the contract names an unsupported
  variant, map to the nearest supported variant and record the mapping.
- Every content/evidence slide must have a real visual or evidence anchor:
  chart, table, figure, image, diagram, stats, KPI, flow, or structured
  comparison. Do not leave report slides as stranded prose bands.
- For lab/report decks, prefer evidence-first variants: `scientific-figure`,
  `image-sidebar`, `lab-run-results`, `table`, `chart`, then
  `comparison-2col` or concise standard report slides.
- Use existing generated artifact aliases when available. Do not invent local
  file paths, chart JSON, table JSON, or image paths. If the needed artifact is
  absent, add the need to `asset_plan_updates` and `notes_append` instead.
- When a `presentation_skill_artifact_rebuild_context_v1` block is available,
  preserve its rebuild, inspect, auto-bind, and validation commands in
  `artifact_rebuild_plan` and `main_agent_handoff.commands_after_patch` when
  generated evidence must be rerun or rebound.
- Keep footer/source provenance compact. Use short source IDs in slide
  footers/sources and move long citations to a References/Image Sources slide
  when needed.
- Do not use placeholders, TODO/TBD, lorem/ipsum, or PowerPoint prompt text in
  visible fields. If information is missing, write a concise assumption or
  skip note in `notes_append`.
- Keep text readable: short titles, compact bullets, no dense sentence-length
  table cells, and no overpacked charts. Respect footer_reserved_inches and
  chart_label_min_pt.
- Patch source files only. Do not mutate generated PPTX files.

Original user request or summary:
{user_prompt}

Slide quality contract:
{slide_quality_context}

Style reference layout playbook:
{style_reference_context}

Generated artifact aliases:
{artifact_aliases}

Generated artifact rebuild context:
{artifact_rebuild_context}

Repository rules:
{reference_context}

Workspace context:
{workspace_context}
"""


def render_outline_authoring_prompt(
    *,
    workspace: Path,
    user_prompt: str = "",
    context_limit: int = 5000,
    reference_limit: int = 5000,
) -> str:
    resolved_workspace = workspace.expanduser().resolve()
    return PROMPT_TEMPLATE.format(
        workspace=str(resolved_workspace),
        user_prompt=user_prompt.strip() or "<infer from design_contract.json and planning files>",
        slide_quality_context=_slide_quality_context(resolved_workspace),
        style_reference_context=_style_reference_authoring_context(resolved_workspace),
        artifact_aliases=_artifact_alias_summary(resolved_workspace),
        artifact_rebuild_context=_artifact_rebuild_context_summary(resolved_workspace),
        reference_context=_reference_context(reference_limit),
        workspace_context=_workspace_context(resolved_workspace, context_limit),
    )


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit a contract-aware outline authoring prompt.")
    parser.add_argument("--workspace", required=True, help="Deck workspace directory")
    parser.add_argument("--user-prompt", default="", help="Original user deck request or concise summary")
    parser.add_argument("--output", default="", help="Optional path to write the prompt")
    parser.add_argument("--context-limit", type=int, default=5000, help="Per-file workspace context character limit")
    parser.add_argument("--reference-limit", type=int, default=5000, help="Per-reference character limit")
    return parser.parse_args()


def main() -> int:
    args = _args()
    prompt = render_outline_authoring_prompt(
        workspace=Path(args.workspace),
        user_prompt=args.user_prompt,
        context_limit=max(1000, args.context_limit),
        reference_limit=max(1000, args.reference_limit),
    )
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8")
    else:
        sys.stdout.write(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
