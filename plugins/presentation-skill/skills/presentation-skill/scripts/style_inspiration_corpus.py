#!/usr/bin/env python3
"""Validate and compact the descriptor-only style inspiration corpus."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from design_tokens import PRESETS


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = ROOT / "references" / "style_inspiration_corpus.json"
STYLE_INSPIRATION_CORPUS_VERSION = "style_inspiration_corpus_v1"
STYLE_INSPIRATION_SUBAGENT_CONTRACT_VERSION = "style_inspiration_subagent_contract_v1"
STYLE_INSPIRATION_STORAGE_RULE = "descriptor_only_no_raw_decks"
REQUIRED_SOURCE_FIELDS = (
    "source_id",
    "source_name",
    "source_url",
    "rights_posture",
    "license_summary",
    "allowed_extractions",
    "forbidden_materials",
    "descriptor_tags",
    "preset_affinity",
    "visual_dna",
    "layout_families",
    "palette_tokens",
    "typography_tokens",
    "content_treatments",
    "mixing_affordances",
    "extraction_limits",
    "source_verification",
)
REQUIRED_USE_CASES = ("overview", "data_evidence", "decision_sources")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_style_inspiration_corpus(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or DEFAULT_CORPUS)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _source_map(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sources = corpus.get("source_classes") if isinstance(corpus.get("source_classes"), list) else []
    out: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id") or "").strip()
        if source_id and source_id not in out:
            out[source_id] = source
    return out


def _routes(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes = corpus.get("preset_routes") if isinstance(corpus.get("preset_routes"), dict) else {}
    return {str(key): value for key, value in routes.items() if isinstance(value, dict)}


def validate_style_inspiration_corpus(
    corpus: dict[str, Any],
    *,
    supported_presets: list[str] | None = None,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if corpus.get("corpus_version") != STYLE_INSPIRATION_CORPUS_VERSION:
        failures.append(
            {
                "path": "corpus_version",
                "reason": "wrong_corpus_version",
                "value": corpus.get("corpus_version"),
            }
        )
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(corpus.get("checked_date") or "")):
        failures.append({"path": "checked_date", "reason": "missing_or_invalid_checked_date"})
    policy = corpus.get("policy") if isinstance(corpus.get("policy"), dict) else {}
    if policy.get("storage_rule") != STYLE_INSPIRATION_STORAGE_RULE:
        failures.append(
            {
                "path": "policy.storage_rule",
                "reason": "wrong_storage_rule",
                "value": policy.get("storage_rule"),
            }
        )
    if not _string_list(policy.get("allowed_record_types")):
        failures.append({"path": "policy.allowed_record_types", "reason": "missing_list"})
    forbidden = set(_string_list(policy.get("forbidden_materials")))
    for forbidden_token in ("raw third-party PPTX files", "raw screenshots from proprietary decks"):
        if forbidden_token not in forbidden:
            failures.append(
                {
                    "path": "policy.forbidden_materials",
                    "reason": "missing_required_forbidden_material",
                    "value": forbidden_token,
                }
            )
    schema = corpus.get("descriptor_schema") if isinstance(corpus.get("descriptor_schema"), dict) else {}
    required_schema_fields = set(_string_list(schema.get("required_fields")))
    missing_schema_fields = set(
        field for field in REQUIRED_SOURCE_FIELDS if field not in {"source_name", "license_summary", "source_verification"}
    ) - required_schema_fields
    if missing_schema_fields:
        failures.append(
            {
                "path": "descriptor_schema.required_fields",
                "reason": "missing_required_descriptor_fields",
                "missing": sorted(missing_schema_fields),
            }
        )

    sources = _source_map(corpus)
    if len(sources) < 8:
        failures.append({"path": "source_classes", "reason": "too_few_sources", "count": len(sources)})
    seen_urls: set[str] = set()
    for source_id, source in sources.items():
        path = f"source_classes.{source_id}"
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source or source.get(field) in (None, "", []):
                failures.append({"path": f"{path}.{field}", "reason": "missing_field"})
        url = str(source.get("source_url") or "").strip()
        if not re.match(r"^https://", url):
            failures.append({"path": f"{path}.source_url", "reason": "source_url_must_be_https", "value": url})
        if url in seen_urls:
            failures.append({"path": f"{path}.source_url", "reason": "duplicate_source_url", "value": url})
        seen_urls.add(url)
        for key in (
            "allowed_extractions",
            "forbidden_materials",
            "descriptor_tags",
            "preset_affinity",
            "layout_families",
            "palette_tokens",
            "typography_tokens",
            "content_treatments",
            "mixing_affordances",
        ):
            if not _string_list(source.get(key)):
                failures.append({"path": f"{path}.{key}", "reason": "missing_list"})
        verification = (
            source.get("source_verification")
            if isinstance(source.get("source_verification"), dict)
            else {}
        )
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(verification.get("checked_date") or "")):
            failures.append(
                {
                    "path": f"{path}.source_verification.checked_date",
                    "reason": "missing_or_invalid_checked_date",
                }
            )
        if len(str(verification.get("evidence_summary") or "").strip()) < 50:
            failures.append(
                {
                    "path": f"{path}.source_verification.evidence_summary",
                    "reason": "evidence_summary_too_short",
                }
            )

    route_map = _routes(corpus)
    presets = supported_presets or sorted(PRESETS)
    for preset in presets:
        route = route_map.get(preset)
        if not isinstance(route, dict):
            failures.append({"path": f"preset_routes.{preset}", "reason": "missing_route"})
            continue
        route_path = f"preset_routes.{preset}"
        source_ids = _string_list(route.get("source_ids"))
        if len(source_ids) < 2:
            failures.append({"path": f"{route_path}.source_ids", "reason": "too_few_source_ids"})
        for source_id in source_ids:
            if source_id not in sources:
                failures.append({"path": f"{route_path}.source_ids", "reason": "unknown_source_id", "source_id": source_id})
        for key in ("query_intents", "preferred_descriptor_tags", "contact_collection_use_cases"):
            if not _string_list(route.get(key)):
                failures.append({"path": f"{route_path}.{key}", "reason": "missing_list"})
        use_cases = set(_string_list(route.get("contact_collection_use_cases")))
        missing_use_cases = set(REQUIRED_USE_CASES) - use_cases
        if missing_use_cases:
            failures.append(
                {
                    "path": f"{route_path}.contact_collection_use_cases",
                    "reason": "missing_required_use_cases",
                    "missing": sorted(missing_use_cases),
                }
            )
        if not isinstance(route.get("mixing_knobs"), dict) or not route.get("mixing_knobs"):
            failures.append({"path": f"{route_path}.mixing_knobs", "reason": "missing_object"})

    contract = corpus.get("subagent_contract") if isinstance(corpus.get("subagent_contract"), dict) else {}
    if contract.get("contract_version") != STYLE_INSPIRATION_SUBAGENT_CONTRACT_VERSION:
        failures.append(
            {
                "path": "subagent_contract.contract_version",
                "reason": "wrong_contract_version",
                "value": contract.get("contract_version"),
            }
        )
    for key in ("output_schema", "safety_rules", "scout_loop"):
        value = contract.get(key)
        if key == "output_schema":
            if not isinstance(value, dict) or not value:
                failures.append({"path": f"subagent_contract.{key}", "reason": "missing_object"})
        elif not _string_list(value):
            failures.append({"path": f"subagent_contract.{key}", "reason": "missing_list"})
    return failures


def _route_score(query: str, preset: str, route: dict[str, Any], source_map: dict[str, dict[str, Any]]) -> int:
    text = query.lower()
    score = 0
    if preset.lower() in text:
        score += 5
    for term in _string_list(route.get("query_intents")):
        if term.lower() in text:
            score += 4
        else:
            score += sum(1 for part in term.lower().split() if len(part) > 3 and part in text)
    for tag in _string_list(route.get("preferred_descriptor_tags")):
        if tag.replace("_", " ").lower() in text or tag.lower() in text:
            score += 2
    for source_id in _string_list(route.get("source_ids")):
        source = source_map.get(source_id, {})
        for tag in _string_list(source.get("descriptor_tags")):
            if tag.replace("_", " ").lower() in text or tag.lower() in text:
                score += 1
    return score


def compact_style_inspiration_context(
    query: str = "",
    *,
    primary_preset: str = "",
    corpus: dict[str, Any] | None = None,
    max_sources: int = 6,
    max_routes: int = 4,
) -> dict[str, Any]:
    payload = corpus if isinstance(corpus, dict) else load_style_inspiration_corpus()
    source_map = _source_map(payload)
    routes = _routes(payload)
    preset = str(primary_preset or "").strip()
    ranked_routes: list[tuple[int, str, dict[str, Any]]] = []
    if preset and preset in routes:
        ranked_routes.append((999, preset, routes[preset]))
    for route_preset, route in routes.items():
        if route_preset == preset:
            continue
        ranked_routes.append((_route_score(query, route_preset, route, source_map), route_preset, route))
    ranked_routes.sort(key=lambda item: (-item[0], item[1]))
    selected_routes = ranked_routes[:max_routes]
    selected_source_ids: list[str] = []
    compact_routes: list[dict[str, Any]] = []
    for score, route_preset, route in selected_routes:
        source_ids = _string_list(route.get("source_ids"))
        for source_id in source_ids:
            if source_id not in selected_source_ids:
                selected_source_ids.append(source_id)
        compact_routes.append(
            {
                "preset": route_preset,
                "score": score,
                "query_intents": _string_list(route.get("query_intents"))[:4],
                "source_ids": source_ids,
                "preferred_descriptor_tags": _string_list(route.get("preferred_descriptor_tags"))[:6],
                "mixing_knobs": route.get("mixing_knobs") if isinstance(route.get("mixing_knobs"), dict) else {},
                "contact_collection_use_cases": _string_list(route.get("contact_collection_use_cases")),
            }
        )
    compact_sources: list[dict[str, Any]] = []
    for source_id in selected_source_ids[:max_sources]:
        source = source_map.get(source_id, {})
        compact_sources.append(
            {
                "source_id": source_id,
                "source_name": source.get("source_name"),
                "source_url": source.get("source_url"),
                "rights_posture": source.get("rights_posture"),
                "allowed_extractions": _string_list(source.get("allowed_extractions"))[:4],
                "forbidden_materials": _string_list(source.get("forbidden_materials"))[:5],
                "descriptor_tags": _string_list(source.get("descriptor_tags"))[:6],
                "visual_dna": source.get("visual_dna"),
                "layout_families": _string_list(source.get("layout_families"))[:5],
                "content_treatments": _string_list(source.get("content_treatments"))[:5],
                "mixing_affordances": _string_list(source.get("mixing_affordances"))[:3],
                "extraction_limits": source.get("extraction_limits"),
            }
        )
    policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
    contract = payload.get("subagent_contract") if isinstance(payload.get("subagent_contract"), dict) else {}
    return {
        "corpus_version": payload.get("corpus_version"),
        "policy": {
            "storage_rule": policy.get("storage_rule"),
            "scale_strategy": policy.get("scale_strategy"),
            "agent_use_rule": policy.get("agent_use_rule"),
            "forbidden_materials": _string_list(policy.get("forbidden_materials"))[:8],
        },
        "selected_routes": compact_routes,
        "sources": compact_sources,
        "subagent_contract": {
            "contract_version": contract.get("contract_version"),
            "trigger": contract.get("trigger"),
            "output_schema": contract.get("output_schema") if isinstance(contract.get("output_schema"), dict) else {},
            "safety_rules": _string_list(contract.get("safety_rules"))[:5],
            "scout_loop": _string_list(contract.get("scout_loop"))[:5],
        },
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_CORPUS), help="Corpus JSON path")
    parser.add_argument("--validate", action="store_true", help="Validate the corpus")
    parser.add_argument("--preset", default="", help="Emit compact context for one preset")
    parser.add_argument("--prompt", default="", help="Prompt text used for compact context ranking")
    return parser.parse_args()


def main() -> int:
    args = _args()
    path = Path(args.manifest).expanduser().resolve()
    corpus = load_style_inspiration_corpus(path)
    failures = validate_style_inspiration_corpus(corpus, supported_presets=sorted(PRESETS))
    if args.validate or not args.preset:
        summary = {
            "passed": not failures,
            "corpus_version": corpus.get("corpus_version"),
            "manifest": str(path),
            "source_count": len(_source_map(corpus)),
            "route_count": len(_routes(corpus)),
            "preset_count": len(PRESETS),
            "failures": failures,
        }
        print(json.dumps(summary, indent=2))
        return 0 if not failures else 1
    context = compact_style_inspiration_context(
        args.prompt,
        primary_preset=args.preset,
        corpus=corpus,
    )
    print(json.dumps(context, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
