#!/usr/bin/env python3
"""Apply an outline-authoring handoff JSON packet to workspace sources.

`emit_outline_authoring_prompt.py` asks the main agent or one bounded subagent
to return strict `outline_authoring_handoff_v1` JSON. This helper applies only
the deterministic source patch fields from that JSON:

- replace `outline.json` when a full `outline_json` object is supplied;
- merge updates into `content_plan.json`, `evidence_plan.json`, and
  `asset_plan.json`;
- record assumptions and the handoff hash in `notes.md`.

The helper does not verify facts or invent missing evidence. The main agent
still owns claim/source verification before final delivery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


NOTE_START = "<!-- outline-authoring-handoff:start -->"
NOTE_END = "<!-- outline-authoring-handoff:end -->"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def _write_json_if_changed(path: Path, payload: Any, *, dry_run: bool) -> bool:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return True


def _write_text_if_changed(path: Path, text: str, *, dry_run: bool) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return True


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "sha256": _file_sha256(path),
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _identity_key(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("slide_id", "id", "name", "alias", "path", "title"):
            value = _text(item.get(key))
            if value:
                return f"{key}:{value.lower()}"
        return json.dumps(item, sort_keys=True, ensure_ascii=False)
    return str(item)


def _merge_list(existing: Any, incoming: list[Any], *, overwrite_named: bool) -> list[Any]:
    merged = list(existing) if isinstance(existing, list) else []
    positions: dict[str, int] = {}
    for index, item in enumerate(merged):
        key = _identity_key(item)
        if key:
            positions[key] = index
    for item in incoming:
        key = _identity_key(item)
        if key in positions:
            if overwrite_named:
                merged[positions[key]] = item
            continue
        positions[key] = len(merged)
        merged.append(item)
    return merged


def _merge_payload(target: dict[str, Any], updates: dict[str, Any], *, overwrite: bool) -> dict[str, Any]:
    result = dict(target)
    for key, value in updates.items():
        if value in (None, "", [], {}):
            continue
        existing = result.get(key)
        if isinstance(value, dict):
            result[key] = _merge_payload(existing if isinstance(existing, dict) else {}, value, overwrite=overwrite)
        elif isinstance(value, list):
            if overwrite or not isinstance(existing, list):
                result[key] = value
            else:
                result[key] = _merge_list(existing, value, overwrite_named=True)
        elif overwrite or existing in (None, "", [], {}):
            result[key] = value
    return result


def _source_patch(handoff: dict[str, Any]) -> dict[str, Any]:
    patch = handoff.get("source_patch")
    if isinstance(patch, dict):
        return patch
    return {
        "outline_json": handoff.get("outline_json"),
        "content_plan_updates": handoff.get("content_plan_updates"),
        "evidence_plan_updates": handoff.get("evidence_plan_updates"),
        "asset_plan_updates": handoff.get("asset_plan_updates"),
        "notes_append": handoff.get("notes_append"),
    }


def _artifact_rebuild_plan(handoff: dict[str, Any]) -> dict[str, Any]:
    plan = handoff.get("artifact_rebuild_plan")
    if isinstance(plan, dict):
        return plan
    main = _as_dict(handoff.get("main_agent_handoff"))
    plan = main.get("artifact_rebuild_plan")
    return plan if isinstance(plan, dict) else {}


def _quality_alignment(handoff: dict[str, Any]) -> dict[str, Any]:
    alignment = handoff.get("quality_alignment")
    if isinstance(alignment, dict):
        return alignment
    main = _as_dict(handoff.get("main_agent_handoff"))
    alignment = main.get("quality_alignment")
    return alignment if isinstance(alignment, dict) else {}


def _validate_handoff(handoff: Any) -> dict[str, Any]:
    if not isinstance(handoff, dict):
        raise ValueError("outline authoring handoff root must be a JSON object")
    version = _text(handoff.get("handoff_version"))
    if version != "outline_authoring_handoff_v1":
        raise ValueError("outline authoring handoff must declare handoff_version='outline_authoring_handoff_v1'")
    patch = _source_patch(handoff)
    if not any(value not in (None, "", [], {}) for value in patch.values()):
        raise ValueError("outline authoring handoff must include source_patch fields")
    outline = patch.get("outline_json")
    if outline is not None:
        if not isinstance(outline, dict):
            raise ValueError("source_patch.outline_json must be an object")
        slides = outline.get("slides")
        if not isinstance(slides, list) or not slides:
            raise ValueError("source_patch.outline_json.slides must be a non-empty list")
    for key in ("content_plan_updates", "evidence_plan_updates", "asset_plan_updates"):
        value = patch.get(key)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"source_patch.{key} must be an object")
    if "artifact_rebuild_plan" in handoff and not isinstance(handoff.get("artifact_rebuild_plan"), dict):
        raise ValueError("artifact_rebuild_plan must be an object when present")
    if "quality_alignment" in handoff and not isinstance(handoff.get("quality_alignment"), dict):
        raise ValueError("quality_alignment must be an object when present")
    return patch


def _replace_notes_section(existing: str, section: str) -> str:
    if NOTE_START in existing and NOTE_END in existing:
        before = existing.split(NOTE_START, 1)[0].rstrip()
        after = existing.split(NOTE_END, 1)[1].lstrip()
        parts = [part for part in (before, section.rstrip(), after.rstrip()) if part]
        return "\n\n".join(parts) + "\n"
    prefix = existing.rstrip()
    return (prefix + "\n\n" if prefix else "") + section.rstrip() + "\n"


def _notes_section(handoff: dict[str, Any], *, handoff_path: Path, handoff_sha: str, notes_append: Any) -> str:
    alignment = _as_dict(handoff.get("contract_alignment"))
    quality_alignment = _quality_alignment(handoff)
    main = _as_dict(handoff.get("main_agent_handoff"))
    rebuild_plan = _artifact_rebuild_plan(handoff)
    rebuild_commands = _as_list(rebuild_plan.get("commands_to_preserve"))
    checks = [_text(item) for item in _as_list(handoff.get("acceptance_checks")) if _text(item)]
    commands = [_text(item) for item in _as_list(main.get("commands_after_patch")) if _text(item)]
    lines = [
        NOTE_START,
        "## Outline Authoring Handoff",
        "",
        f"- Handoff JSON: `{handoff_path}`",
        f"- Handoff SHA-256: `{handoff_sha}`",
    ]
    if _text(alignment.get("style_seed")):
        lines.append(f"- Style seed: `{_text(alignment.get('style_seed'))}`")
    if _text(alignment.get("style_preset")):
        lines.append(f"- Style preset: `{_text(alignment.get('style_preset'))}`")
    if _text(alignment.get("style_reference_id")):
        lines.append(f"- Style reference: `{_text(alignment.get('style_reference_id'))}`")
    if _text(alignment.get("variant_mix_plan")):
        lines.append(f"- Variant mix: {_text(alignment.get('variant_mix_plan'))}")
    motif_used = _as_dict(alignment.get("structural_motif_library_used"))
    if motif_used:
        version = _text(motif_used.get("motif_library_version")) or "style_reference_structural_motif_library_v1"
        lines.append(f"- Structural motif library: `{version}`")
        background = _text(motif_used.get("background_structure"))
        if background:
            lines.append(f"- Background structure: {background}")
        motifs = [_text(item) for item in _as_list(motif_used.get("layout_motifs_used")) if _text(item)]
        if motifs:
            lines.append(f"- Layout motifs used: {', '.join(motifs[:6])}")
    metric_used = _as_dict(alignment.get("style_metric_profile_used"))
    if metric_used:
        version = _text(metric_used.get("metric_profile_version")) or "style_reference_metric_profile_v1"
        lines.append(f"- Style metric profile: `{version}`")
        density = _text(metric_used.get("density_level"))
        if density:
            lines.append(f"- Density posture: {density}")
        whitespace = _text(metric_used.get("whitespace_ratio_target"))
        if whitespace:
            lines.append(f"- Whitespace target: {whitespace}")
        body_budget = _as_list(metric_used.get("body_words_per_content_slide"))
        if body_budget:
            lines.append(f"- Body word budget: {', '.join(_text(item) for item in body_budget if _text(item))}")
        max_objects = _text(metric_used.get("max_primary_objects"))
        if max_objects:
            lines.append(f"- Max primary objects: {max_objects}")
    playbook_used = _as_dict(alignment.get("layout_playbook_used"))
    if playbook_used:
        version = _text(playbook_used.get("playbook_version"))
        lines.append(f"- Layout playbook: `{version or 'style_reference_layout_playbook_v1'}`")
        preferred = [_text(item) for item in _as_list(playbook_used.get("preferred_variants")) if _text(item)]
        if preferred:
            lines.append(f"- Playbook variants used: {', '.join(preferred[:8])}")
        archetypes = _as_dict(playbook_used.get("treatment_archetypes_used"))
        title_archetype = _text(archetypes.get("title"))
        refs_archetype = _text(archetypes.get("references"))
        if title_archetype:
            lines.append(f"- Title archetype used: {title_archetype}")
        if refs_archetype:
            lines.append(f"- References archetype used: {refs_archetype}")
        body_archetypes = [
            f"{key}={_text(value)}"
            for key, value in archetypes.items()
            if key not in {"title", "references"} and _text(value)
        ]
        if body_archetypes:
            lines.append(f"- Body treatment archetypes used: {', '.join(body_archetypes[:8])}")
        semantic_signatures = _as_dict(playbook_used.get("treatment_archetype_semantic_signatures_used"))
        semantic_bits = [
            f"{key}={_text(value)[:16]}"
            for key, value in semantic_signatures.items()
            if _text(value)
        ]
        if semantic_bits:
            lines.append(f"- Treatment semantic signatures used: {', '.join(semantic_bits[:8])}")
    recipe_used = _as_dict(alignment.get("content_recipe_library_used"))
    if recipe_used:
        version = _text(recipe_used.get("library_version")) or "style_reference_content_recipe_library_v1"
        lines.append(f"- Content recipe library: `{version}`")
        slide_recipe_map = [
            item
            for item in _as_list(recipe_used.get("slide_recipe_map"))
            if isinstance(item, dict)
        ]
        if slide_recipe_map:
            recipe_bits = []
            for item in slide_recipe_map[:6]:
                slide_id = _text(item.get("slide_id"))
                treatment = _text(item.get("treatment_key"))
                if slide_id and treatment:
                    recipe_bits.append(f"{slide_id}:{treatment}")
            if recipe_bits:
                lines.append(f"- Content recipes used: {', '.join(recipe_bits)}")
    if _text(notes_append):
        lines.extend(["", "### Author Notes", _text(notes_append)])
    if rebuild_plan:
        lines.extend(["", "### Artifact Rebuild Plan"])
        if _text(rebuild_plan.get("context_version")):
            lines.append(f"- Context: `{_text(rebuild_plan.get('context_version'))}`")
        if _text(rebuild_plan.get("producer_path")):
            lines.append(f"- Producer: `{_text(rebuild_plan.get('producer_path'))}`")
        for command in [_text(item) for item in rebuild_commands if _text(item)][:6]:
            lines.append(f"- `{command}`")
    if quality_alignment:
        lines.extend(["", "### Quality Alignment"])
        if _text(quality_alignment.get("contract_version")):
            lines.append(f"- Contract: `{_text(quality_alignment.get('contract_version'))}`")
        for label, key in (
            ("Readability", "readability_targets_used"),
            ("Layout", "layout_targets_used"),
            ("Artifact QA", "artifact_quality_targets_used"),
            ("QA gates", "qa_gates_used"),
        ):
            values = [_text(item) for item in _as_list(quality_alignment.get(key)) if _text(item)]
            if values:
                lines.append(f"- {label}: {'; '.join(values[:6])}")
        commands_used = [_text(item) for item in _as_list(quality_alignment.get("required_commands")) if _text(item)]
        for command in commands_used[:4]:
            lines.append(f"- `{command}`")
        if _text(quality_alignment.get("outline_choices")):
            lines.append(f"- Outline choices: {_text(quality_alignment.get('outline_choices'))}")
    if checks:
        lines.extend(["", "### Acceptance Checks"])
        lines.extend(f"- {item}" for item in checks[:12])
    if commands:
        lines.extend(["", "### Commands After Patch"])
        lines.extend(f"- `{item}`" for item in commands[:8])
    lines.append(NOTE_END)
    return "\n".join(lines)


def _apply_json_update(
    *,
    path: Path,
    updates: dict[str, Any],
    overwrite: bool,
    dry_run: bool,
) -> bool:
    existing = _load_json(path, {})
    if not isinstance(existing, dict):
        existing = {}
    merged = _merge_payload(existing, updates, overwrite=overwrite)
    return _write_json_if_changed(path, merged, dry_run=dry_run)


def _apply_handoff_metadata(
    *,
    workspace: Path,
    handoff: dict[str, Any],
    handoff_path: Path,
    handoff_sha: str,
    dry_run: bool,
) -> tuple[bool, list[str]]:
    rebuild_plan = _artifact_rebuild_plan(handoff)
    quality_alignment = _quality_alignment(handoff)
    contract_alignment = _as_dict(handoff.get("contract_alignment"))
    if not rebuild_plan and not quality_alignment and not contract_alignment:
        return False, []

    design_path = workspace / "design_brief.json"
    design = _load_json(design_path, {})
    if not isinstance(design, dict):
        design = {}

    outline_meta = design.get("outline_authoring_handoff")
    if not isinstance(outline_meta, dict):
        outline_meta = {}
    outline_meta.update(
        {
            "handoff_path": str(handoff_path),
            "handoff_sha256": handoff_sha,
        }
    )
    if rebuild_plan:
        outline_meta["artifact_rebuild_plan"] = rebuild_plan
    if quality_alignment:
        outline_meta["quality_alignment"] = quality_alignment
    if contract_alignment:
        outline_meta["contract_alignment"] = contract_alignment
    design["outline_authoring_handoff"] = outline_meta

    if rebuild_plan:
        analysis_plan = design.get("analysis_artifact_plan")
        if not isinstance(analysis_plan, dict):
            analysis_plan = {}
        analysis_plan["outline_authoring_rebuild_plan"] = rebuild_plan
        for source_key, target_key in (
            ("artifact_manifest", "artifact_manifest"),
            ("analysis_summary", "analysis_summary"),
            ("analysis_summary_markdown", "analysis_summary_markdown"),
        ):
            value = _text(rebuild_plan.get(source_key))
            if value:
                analysis_plan[target_key] = value
        commands = _as_dict(rebuild_plan.get("commands"))
        rebuild_command = _text(commands.get("rebuild_figures"))
        if rebuild_command:
            existing = analysis_plan.get("rebuild_commands")
            values = [item for item in _as_list(existing) if _text(item)]
            if rebuild_command not in values:
                values.append(rebuild_command)
            analysis_plan["rebuild_commands"] = values
        producer = _text(rebuild_plan.get("producer_path"))
        if producer and producer.lower() != "none":
            figure_scripts = [_text(item) for item in _as_list(analysis_plan.get("figure_scripts")) if _text(item)]
            if producer not in figure_scripts:
                figure_scripts.append(producer)
            analysis_plan["figure_scripts"] = figure_scripts
        design["analysis_artifact_plan"] = analysis_plan

    changed = _write_json_if_changed(design_path, design, dry_run=dry_run)
    touched = []
    if rebuild_plan:
        touched.extend(
            [
                "outline_authoring_handoff.artifact_rebuild_plan",
                "analysis_artifact_plan.outline_authoring_rebuild_plan",
            ]
        )
    if quality_alignment:
        touched.append("outline_authoring_handoff.quality_alignment")
    if contract_alignment:
        touched.append("outline_authoring_handoff.contract_alignment")
    return changed, touched


def apply_handoff(
    *,
    workspace: Path,
    handoff_path: Path,
    overwrite_plans: bool,
    dry_run: bool,
) -> dict[str, Any]:
    workspace = workspace.expanduser().resolve()
    handoff_path = handoff_path.expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ValueError(f"workspace not found: {workspace}")
    if not handoff_path.exists():
        raise ValueError(f"handoff JSON not found: {handoff_path}")

    handoff = _load_json(handoff_path, {})
    patch = _validate_handoff(handoff)
    handoff_sha = _file_sha256(handoff_path)
    changed_files: list[str] = []
    touched_fields: dict[str, list[str]] = {}

    outline = patch.get("outline_json")
    outline_changed = False
    if isinstance(outline, dict):
        outline_path = workspace / "outline.json"
        outline_changed = _write_json_if_changed(outline_path, outline, dry_run=dry_run)
        if outline_changed:
            changed_files.append(str(outline_path))
            touched_fields["outline.json"] = ["outline"]

    for key, filename in (
        ("content_plan_updates", "content_plan.json"),
        ("evidence_plan_updates", "evidence_plan.json"),
        ("asset_plan_updates", "asset_plan.json"),
    ):
        updates = patch.get(key)
        if not isinstance(updates, dict) or not updates:
            continue
        path = workspace / filename
        changed = _apply_json_update(
            path=path,
            updates=updates,
            overwrite=overwrite_plans,
            dry_run=dry_run,
        )
        if changed:
            changed_files.append(str(path))
            touched_fields[filename] = sorted(updates.keys())

    metadata_changed, metadata_fields = _apply_handoff_metadata(
        workspace=workspace,
        handoff=handoff,
        handoff_path=handoff_path,
        handoff_sha=handoff_sha,
        dry_run=dry_run,
    )
    if metadata_changed:
        design_path = workspace / "design_brief.json"
        changed_files.append(str(design_path))
        touched_fields["design_brief.json"] = metadata_fields

    notes_path = workspace / "notes.md"
    existing_notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
    next_notes = _replace_notes_section(
        existing_notes,
        _notes_section(
            handoff,
            handoff_path=handoff_path,
            handoff_sha=handoff_sha,
            notes_append=patch.get("notes_append"),
        ),
    )
    if _write_text_if_changed(notes_path, next_notes, dry_run=dry_run):
        changed_files.append(str(notes_path))
        touched_fields["notes.md"] = ["outline-authoring-handoff"]

    return {
        "workflow": "outline_authoring_handoff_apply_v1",
        "workspace": str(workspace),
        "handoff": str(handoff_path),
        "handoff_version": handoff.get("handoff_version"),
        "handoff_sha256": handoff_sha,
        "handoff_snapshot": _file_snapshot(handoff_path),
        "overwrite_plans": overwrite_plans,
        "dry_run": dry_run,
        "changed_files": changed_files,
        "changed_file_count": len(changed_files),
        "touched_fields": touched_fields,
        "outline_changed": outline_changed,
        "content_plan_changed": str(workspace / "content_plan.json") in changed_files,
        "evidence_plan_changed": str(workspace / "evidence_plan.json") in changed_files,
        "asset_plan_changed": str(workspace / "asset_plan.json") in changed_files,
        "design_brief_changed": str(workspace / "design_brief.json") in changed_files,
        "artifact_rebuild_plan_applied": bool(_artifact_rebuild_plan(handoff)),
        "quality_alignment_applied": bool(_quality_alignment(handoff)),
        "notes_changed": str(workspace / "notes.md") in changed_files,
        "next_commands": [
            f"python3 scripts/report_workspace_readiness.py --workspace {workspace}",
            (
                "python3 scripts/build_workspace.py "
                f"--workspace {workspace} --qa --skip-render "
                "--fail-on-planning-warnings --fail-on-whitespace-warnings --overwrite"
            ),
        ],
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Deck workspace directory")
    parser.add_argument("--handoff", required=True, help="outline_authoring_handoff_v1 JSON file")
    parser.add_argument(
        "--preserve-existing-plans",
        dest="overwrite_plans",
        action="store_false",
        help="Fill missing planning fields without replacing non-empty existing plan fields.",
    )
    parser.set_defaults(overwrite_plans=True)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing source files")
    parser.add_argument("--report", help="Optional JSON report path")
    return parser.parse_args()


def main() -> int:
    args = _args()
    try:
        report = apply_handoff(
            workspace=Path(args.workspace),
            handoff_path=Path(args.handoff),
            overwrite_plans=args.overwrite_plans,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: cannot apply outline-authoring handoff: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        report_path = Path(args.report).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
