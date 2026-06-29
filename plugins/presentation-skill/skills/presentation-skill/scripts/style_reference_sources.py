#!/usr/bin/env python3
"""Validate publish-safe source-intake metadata for style references."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "references" / "style_reference_sources.json"
SOURCE_MANIFEST_VERSION = "style_reference_source_manifest_v1"
REQUIRED_TREATMENTS = (
    "title",
    "comparison",
    "chart",
    "table",
    "figure",
    "dashboard",
    "decision",
    "references",
)
ALLOWED_SOURCE_STATUS = {
    "public_domain_with_restrictions",
    "public_domain_with_exceptions",
    "public_domain_design_system",
    "public_guidance_reference",
    "open_government_guidance",
    "open_source_design_system",
    "cc_by_template_reference",
}
ALLOWED_DERIVATION_MODES = {
    "metadata_only",
    "synthetic_reconstruction",
    "linked_attribution",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_style_reference_source_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or DEFAULT_MANIFEST)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _manifest_source_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sources = manifest.get("source_classes")
    if not isinstance(sources, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id") or "").strip()
        if source_id and source_id not in out:
            out[source_id] = source
    return out


def _manifest_routes(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes = manifest.get("preset_intake_routes")
    if not isinstance(routes, dict):
        return {}
    return {str(key): value for key, value in routes.items() if isinstance(value, dict)}


def validate_style_reference_source_manifest(
    manifest: dict[str, Any],
    *,
    supported_presets: list[str] | None = None,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if manifest.get("manifest_version") != SOURCE_MANIFEST_VERSION:
        failures.append(
            {
                "path": "manifest_version",
                "reason": "wrong_manifest_version",
                "value": manifest.get("manifest_version"),
            }
        )
    policy = manifest.get("policy") if isinstance(manifest.get("policy"), dict) else {}
    allowed_modes = set(_string_list(policy.get("allowed_derivation_modes")))
    if not ALLOWED_DERIVATION_MODES.issubset(allowed_modes):
        failures.append(
            {
                "path": "policy.allowed_derivation_modes",
                "reason": "missing_allowed_modes",
                "missing": sorted(ALLOWED_DERIVATION_MODES - allowed_modes),
            }
        )
    source_map = _manifest_source_map(manifest)
    if len(source_map) < 3:
        failures.append({"path": "source_classes", "reason": "too_few_source_classes", "count": len(source_map)})
    seen_urls: set[str] = set()
    for source_id, source in source_map.items():
        path = f"source_classes.{source_id}"
        url = str(source.get("source_url") or "").strip()
        if not re.match(r"^https://", url):
            failures.append({"path": f"{path}.source_url", "reason": "source_url_must_be_https", "value": url})
        if url in seen_urls:
            failures.append({"path": f"{path}.source_url", "reason": "duplicate_source_url", "value": url})
        seen_urls.add(url)
        if source.get("source_status") not in ALLOWED_SOURCE_STATUS:
            failures.append(
                {
                    "path": f"{path}.source_status",
                    "reason": "unsupported_source_status",
                    "value": source.get("source_status"),
                }
            )
        for key in ("license_summary", "attribution_policy", "storage_policy"):
            if not str(source.get(key) or "").strip():
                failures.append({"path": f"{path}.{key}", "reason": "missing_text"})
        verification = (
            source.get("source_verification")
            if isinstance(source.get("source_verification"), dict)
            else {}
        )
        if not verification:
            failures.append({"path": f"{path}.source_verification", "reason": "missing_verification"})
        else:
            checked_url = str(verification.get("checked_url") or "").strip()
            if checked_url != url:
                failures.append(
                    {
                        "path": f"{path}.source_verification.checked_url",
                        "reason": "checked_url_must_match_source_url",
                        "value": checked_url,
                    }
                )
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(verification.get("checked_date") or "")):
                failures.append(
                    {
                        "path": f"{path}.source_verification.checked_date",
                        "reason": "missing_or_invalid_checked_date",
                        "value": verification.get("checked_date"),
                    }
                )
            evidence_summary = str(verification.get("evidence_summary") or "").strip()
            if len(evidence_summary) < 80:
                failures.append(
                    {
                        "path": f"{path}.source_verification.evidence_summary",
                        "reason": "evidence_summary_too_short",
                    }
                )
            if not _string_list(verification.get("evidence_scope")):
                failures.append(
                    {
                        "path": f"{path}.source_verification.evidence_scope",
                        "reason": "missing_list",
                    }
                )
        for key in (
            "allowed_extractions",
            "forbidden_materials",
            "safe_derivation_modes",
            "preset_affinity",
            "generic_style_observations",
            "generic_slide_patterns",
        ):
            values = _string_list(source.get(key))
            if not values:
                failures.append({"path": f"{path}.{key}", "reason": "missing_list"})
            if key == "safe_derivation_modes":
                unsupported = sorted(set(values) - ALLOWED_DERIVATION_MODES)
                if unsupported:
                    failures.append({"path": f"{path}.{key}", "reason": "unsupported_modes", "values": unsupported})
    routes = _manifest_routes(manifest)
    presets = supported_presets or sorted(routes)
    for preset in presets:
        route = routes.get(preset)
        if not isinstance(route, dict):
            failures.append({"path": f"preset_intake_routes.{preset}", "reason": "missing_route"})
            continue
        route_path = f"preset_intake_routes.{preset}"
        if not str(route.get("route_id") or "").strip():
            failures.append({"path": f"{route_path}.route_id", "reason": "missing_route_id"})
        mode = str(route.get("derivation_mode") or "").strip()
        if mode not in ALLOWED_DERIVATION_MODES:
            failures.append({"path": f"{route_path}.derivation_mode", "reason": "unsupported_mode", "value": mode})
        source_ids = _string_list(route.get("source_ids"))
        if not source_ids:
            failures.append({"path": f"{route_path}.source_ids", "reason": "missing_source_ids"})
        for source_id in source_ids:
            source = source_map.get(source_id)
            if source is None:
                failures.append({"path": f"{route_path}.source_ids", "reason": "unknown_source_id", "source_id": source_id})
                continue
            source_modes = set(_string_list(source.get("safe_derivation_modes")))
            if mode not in source_modes:
                failures.append(
                    {
                        "path": f"{route_path}.derivation_mode",
                        "reason": "mode_not_allowed_for_source",
                        "source_id": source_id,
                        "mode": mode,
                    }
                )
        scope = set(_string_list(route.get("content_treatment_scope")))
        if set(REQUIRED_TREATMENTS) - scope:
            failures.append(
                {
                    "path": f"{route_path}.content_treatment_scope",
                    "reason": "missing_treatment_scope",
                    "missing": sorted(set(REQUIRED_TREATMENTS) - scope),
                }
            )
        for key in ("use_cases", "required_synthetic_content"):
            if not _string_list(route.get(key)):
                failures.append({"path": f"{route_path}.{key}", "reason": "missing_list"})
    return failures


def preset_source_intake_route(preset: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = manifest if isinstance(manifest, dict) else load_style_reference_source_manifest()
    source_map = _manifest_source_map(payload)
    routes = _manifest_routes(payload)
    key = str(preset or "").strip()
    route = dict(routes.get(key, {}))
    if not route:
        return {}
    source_ids = _string_list(route.get("source_ids"))
    route["manifest_version"] = payload.get("manifest_version")
    route["source_checked_date"] = payload.get("source_checked_date")
    route["source_ids"] = source_ids
    route["sources"] = [
        {
            "source_id": source_id,
            "source_name": source_map.get(source_id, {}).get("source_name"),
            "source_url": source_map.get(source_id, {}).get("source_url"),
            "source_status": source_map.get(source_id, {}).get("source_status"),
            "license_summary": source_map.get(source_id, {}).get("license_summary"),
            "source_verification": source_map.get(source_id, {}).get("source_verification", {}),
            "attribution_policy": source_map.get(source_id, {}).get("attribution_policy"),
            "storage_policy": source_map.get(source_id, {}).get("storage_policy"),
            "allowed_extractions": source_map.get(source_id, {}).get("allowed_extractions", []),
            "forbidden_materials": source_map.get(source_id, {}).get("forbidden_materials", []),
            "generic_style_observations": source_map.get(source_id, {}).get("generic_style_observations", []),
            "generic_slide_patterns": source_map.get(source_id, {}).get("generic_slide_patterns", []),
            "design_constraints": source_map.get(source_id, {}).get("design_constraints", []),
        }
        for source_id in source_ids
        if source_id in source_map
    ]
    route["publish_safety"] = {
        "status": "publish_safe_descriptor",
        "basis": "source manifest stores only URLs, license notes, verification evidence, allowed extraction modes, and synthetic reconstruction requirements",
        "repo_storage_rule": str((payload.get("policy") if isinstance(payload.get("policy"), dict) else {}).get("repo_storage_rule") or ""),
    }
    return route


def style_reference_source_summary(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = manifest if isinstance(manifest, dict) else load_style_reference_source_manifest()
    source_map = _manifest_source_map(payload)
    routes = _manifest_routes(payload)
    return {
        "manifest_version": payload.get("manifest_version"),
        "source_checked_date": payload.get("source_checked_date"),
        "source_count": len(source_map),
        "route_count": len(routes),
        "source_ids": sorted(source_map),
        "preset_routes": sorted(routes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or inspect style-reference source-intake metadata.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to style_reference_sources.json.")
    parser.add_argument("--preset", default="", help="Emit the compact source-intake route for one preset.")
    parser.add_argument("--validate", action="store_true", help="Validate the manifest and exit non-zero on failures.")
    args = parser.parse_args()
    manifest = load_style_reference_source_manifest(Path(args.manifest))
    if args.preset:
        payload: Any = preset_source_intake_route(args.preset, manifest)
    else:
        failures = validate_style_reference_source_manifest(manifest)
        payload = {
            **style_reference_source_summary(manifest),
            "passed": not failures,
            "failures": failures,
        }
    print(json.dumps(payload, indent=2))
    if args.validate:
        return 0 if not payload.get("failures") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
