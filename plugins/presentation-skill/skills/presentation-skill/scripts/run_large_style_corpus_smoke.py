#!/usr/bin/env python3
"""Fast smoke for the descriptor-only large style corpus tooling."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from large_style_corpus import (
    DEFAULT_SOURCE_MANIFEST,
    STYLE_FAMILY_DESCRIPTORS,
    _normalize_record,
    _select_balanced_records,
    build_catalog,
    compact_large_style_corpus_context,
    load_source_manifest,
    validate_large_style_corpus,
    validate_source_manifest,
    write_digest,
)


def _fixture_records(source_manifest: dict) -> list[dict]:
    records: list[dict] = []
    extensions = ["pptx", "pdf", "md", "html", "odp"]
    for idx, (family, descriptor) in enumerate(STYLE_FAMILY_DESCRIPTORS.items()):
        extension = extensions[idx % len(extensions)]
        keywords = descriptor.get("keywords", [])[:4]
        terms = " ".join(str(keyword) for keyword in keywords)
        repo = f"presentation-fixtures/{family}-examples"
        path = f"examples/{family}/realistic-{family}-slides.{extension}"
        item = {
            "repository": {
                "nameWithOwner": repo,
                "url": f"https://github.com/{repo}",
                "isFork": False,
                "isPrivate": False,
            },
            "path": path,
            "url": f"https://github.com/{repo}/blob/fixture/{path}",
        }
        query = {
            "provider": "github_code_search",
            "query_id": f"fixture_{family}",
            "terms": terms,
            "extension": extension,
            "target_families": [family],
            "design_signal": f"fixture route for {family}",
        }
        record = _normalize_record(item, query)
        if not record:
            raise AssertionError(f"failed to normalize fixture record for {family}")
        records.append(record)
    return records


def main() -> int:
    source_manifest = load_source_manifest(DEFAULT_SOURCE_MANIFEST)
    source_failures = validate_source_manifest(source_manifest)
    if source_failures:
        raise AssertionError(json.dumps(source_failures[:5], indent=2))

    records = _fixture_records(source_manifest)
    selected, diagnostics = _select_balanced_records(
        records,
        source_manifest=source_manifest,
        target_count=len(records),
        min_per_family=1,
        max_per_repository=2,
        max_per_owner=30,
        max_per_overlap_key=20,
    )
    catalog = build_catalog(
        selected,
        source_manifest=source_manifest,
        query_reports=[{"query_id": "fixture", "status": "ok", "result_count": len(records)}],
        selection_diagnostics=diagnostics,
    )
    failures = validate_large_style_corpus(catalog, min_records=len(records), min_family_records=1)
    if failures:
        raise AssertionError(json.dumps(failures[:8], indent=2))

    context = compact_large_style_corpus_context(
        "clinical lab AI agent dashboard with source footers",
        primary_family="lab-report",
        catalog=catalog,
        max_records=5,
    )
    if not context.get("available"):
        raise AssertionError("compact context did not mark catalog available")
    if not context.get("sample_records"):
        raise AssertionError("compact context did not include sample records")
    selected_families = [item.get("style_family") for item in context.get("selected_family_summaries", [])]
    if "lab-report" not in selected_families:
        raise AssertionError(f"lab-report missing from selected families: {selected_families}")

    with tempfile.TemporaryDirectory(prefix="large-style-corpus-smoke-") as tmp:
        digest_path = Path(tmp) / "digest.md"
        write_digest(catalog, digest_path)
        text = digest_path.read_text(encoding="utf-8")
        if "Descriptor-only public deck index" not in text or "## Family Coverage" not in text:
            raise AssertionError("digest missing expected sections")

    print(
        json.dumps(
            {
                "passed": True,
                "fixture_records": len(records),
                "selected_records": len(selected),
                "family_count": len(STYLE_FAMILY_DESCRIPTORS),
                "context_samples": len(context.get("sample_records", [])),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
