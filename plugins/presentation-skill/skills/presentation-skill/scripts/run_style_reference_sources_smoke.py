#!/usr/bin/env python3
"""Smoke check for publish-safe style-reference source intake metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from design_tokens import PRESETS
from style_reference_sources import (
    REQUIRED_TREATMENTS,
    SOURCE_MANIFEST_VERSION,
    load_style_reference_source_manifest,
    preset_source_intake_route,
    style_reference_source_summary,
    validate_style_reference_source_manifest,
)


def main() -> int:
    manifest = load_style_reference_source_manifest()
    failures: list[dict[str, Any]] = validate_style_reference_source_manifest(
        manifest,
        supported_presets=sorted(PRESETS),
    )
    summary = style_reference_source_summary(manifest)
    routes: dict[str, Any] = {}
    for preset in sorted(PRESETS):
        route = preset_source_intake_route(preset, manifest)
        routes[preset] = {
            "route_id": route.get("route_id"),
            "source_ids": route.get("source_ids"),
            "derivation_mode": route.get("derivation_mode"),
            "source_count": len(route.get("sources") if isinstance(route.get("sources"), list) else []),
        }
        if route.get("manifest_version") != SOURCE_MANIFEST_VERSION:
            failures.append(
                {
                    "preset": preset,
                    "reason": "route_manifest_version_mismatch",
                    "manifest_version": route.get("manifest_version"),
                }
            )
        if route.get("derivation_mode") != "synthetic_reconstruction":
            failures.append(
                {
                    "preset": preset,
                    "reason": "route_must_use_synthetic_reconstruction",
                    "derivation_mode": route.get("derivation_mode"),
                }
            )
        source_ids = route.get("source_ids") if isinstance(route.get("source_ids"), list) else []
        sources = route.get("sources") if isinstance(route.get("sources"), list) else []
        if not source_ids or len(sources) != len(source_ids):
            failures.append(
                {
                    "preset": preset,
                    "reason": "route_sources_not_resolved",
                    "source_ids": source_ids,
                    "source_count": len(sources),
                }
            )
        scope = set(route.get("content_treatment_scope") if isinstance(route.get("content_treatment_scope"), list) else [])
        missing_scope = sorted(set(REQUIRED_TREATMENTS) - scope)
        if missing_scope:
            failures.append(
                {
                    "preset": preset,
                    "reason": "route_missing_content_treatment_scope",
                    "missing": missing_scope,
                }
            )
        publish_safety = route.get("publish_safety") if isinstance(route.get("publish_safety"), dict) else {}
        if publish_safety.get("status") != "publish_safe_descriptor":
            failures.append(
                {
                    "preset": preset,
                    "reason": "route_missing_publish_safe_descriptor",
                    "publish_safety": publish_safety,
                }
            )
    payload = {
        **summary,
        "passed": not failures,
        "required_treatments": list(REQUIRED_TREATMENTS),
        "routes": routes,
        "failures": failures,
        "manifest_path": str(Path("references") / "style_reference_sources.json"),
    }
    print(json.dumps(payload, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
