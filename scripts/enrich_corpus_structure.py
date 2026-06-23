"""Enrich the style corpus with structural-grammar fields.

The base corpus at references/large_style_corpus_catalog.json carries surface
descriptors only (palette tokens, typography tokens, layout tags). For the
corpus to actually drive slide grammar at generation time, records need
structural fields too:

- preferred_variants: ranked list of pptxgenjs variants this family reaches for
- variant_distribution_targets: target proportions across content slides
- narrative_arc: ordered list of arc beats (problem, evidence, decision, etc.)
- artifact_density: target share of slides carrying a non-text artifact
- slide_count_typical: [min, max] deck length range

This script writes references/style_grammar_index.json containing a curated,
family-balanced subset (~15 records per family) with these fields populated.
Generation-time routers query this index instead of inferring grammar from
descriptor tags alone.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ENRICHED_CORPUS_PATH = REPO_ROOT / "references" / "large_style_corpus_catalog_enriched.json"
BASE_CORPUS_PATH = REPO_ROOT / "references" / "large_style_corpus_catalog.json"
OUTPUT_PATH = REPO_ROOT / "references" / "style_grammar_index.json"
RECORDS_PER_FAMILY_CAP = 15


def _resolve_corpus_path() -> Path:
    return ENRICHED_CORPUS_PATH if ENRICHED_CORPUS_PATH.exists() else BASE_CORPUS_PATH


FAMILY_GRAMMAR_TEMPLATES: dict[str, dict[str, Any]] = {
    "bold-startup-narrative": {
        "preferred_variants": [
            "title", "kpi-hero", "comparison-2col", "image-sidebar", "stats",
            "cards-3", "chart"
        ],
        "variant_distribution_targets": {
            "kpi-hero": 0.15, "comparison-2col": 0.20, "image-sidebar": 0.15,
            "stats": 0.15, "cards-3": 0.15, "chart": 0.15, "split": 0.05
        },
        "narrative_arc": ["title", "problem", "solution", "traction", "moat", "ask", "close"],
        "artifact_density": 0.70,
        "slide_count_typical": [8, 12],
        "primary_evidence_form": "screenshots-and-stats",
        "rhythm_signature": "punchy-claim+visual-proof",
    },
    "editorial-minimal": {
        "preferred_variants": [
            "title", "section", "image-sidebar", "comparison-2col", "cards-3",
            "split", "stats"
        ],
        "variant_distribution_targets": {
            "image-sidebar": 0.25, "comparison-2col": 0.20, "section": 0.15,
            "cards-3": 0.15, "split": 0.15, "stats": 0.10
        },
        "narrative_arc": ["title", "premise", "exploration", "reflection", "close"],
        "artifact_density": 0.50,
        "slide_count_typical": [7, 12],
        "primary_evidence_form": "large-image-with-caption",
        "rhythm_signature": "essay-spread-with-pauses",
    },
    "charcoal-safety": {
        "preferred_variants": [
            "title", "matrix", "lab-run-results", "table", "timeline",
            "comparison-2col", "stats"
        ],
        "variant_distribution_targets": {
            "matrix": 0.20, "table": 0.20, "lab-run-results": 0.15,
            "timeline": 0.15, "comparison-2col": 0.15, "stats": 0.15
        },
        "narrative_arc": ["title", "risk-overview", "matrix", "incidents", "mitigation", "owners-and-timeline"],
        "artifact_density": 0.85,
        "slide_count_typical": [8, 14],
        "primary_evidence_form": "matrix-and-table",
        "rhythm_signature": "risk-then-control",
    },
    "paper-journal": {
        "preferred_variants": [
            "title", "section", "scientific-figure", "comparison-2col", "table",
            "image-sidebar", "matrix"
        ],
        "variant_distribution_targets": {
            "scientific-figure": 0.25, "comparison-2col": 0.20, "table": 0.20,
            "image-sidebar": 0.15, "matrix": 0.10, "section": 0.10
        },
        "narrative_arc": ["title", "abstract", "method", "results", "discussion", "references"],
        "artifact_density": 0.80,
        "slide_count_typical": [8, 15],
        "primary_evidence_form": "figure-plate-with-citation",
        "rhythm_signature": "method-then-results",
    },
    "warm-terracotta": {
        "preferred_variants": [
            "title", "section", "cards-3", "timeline", "split", "comparison-2col",
            "image-sidebar"
        ],
        "variant_distribution_targets": {
            "cards-3": 0.20, "timeline": 0.20, "split": 0.15,
            "comparison-2col": 0.15, "image-sidebar": 0.15, "section": 0.15
        },
        "narrative_arc": ["title", "context", "findings", "what-changed", "action", "close"],
        "artifact_density": 0.55,
        "slide_count_typical": [6, 10],
        "primary_evidence_form": "field-photo-and-quote",
        "rhythm_signature": "human-scale-narrative",
    },
    "data-heavy-boardroom": {
        "preferred_variants": [
            "title", "kpi-hero", "stats", "chart", "table", "comparison-2col",
            "matrix"
        ],
        "variant_distribution_targets": {
            "kpi-hero": 0.15, "stats": 0.20, "chart": 0.20, "table": 0.20,
            "comparison-2col": 0.15, "matrix": 0.10
        },
        "narrative_arc": ["title", "kpi-summary", "trend", "variance", "risks", "decision"],
        "artifact_density": 0.95,
        "slide_count_typical": [7, 12],
        "primary_evidence_form": "kpi-tile-and-trend-chart",
        "rhythm_signature": "metric-driven-board-memo",
    },
    "arctic-minimal": {
        "preferred_variants": [
            "title", "section", "flow", "chart", "table", "comparison-2col",
            "scientific-figure"
        ],
        "variant_distribution_targets": {
            "flow": 0.20, "chart": 0.20, "table": 0.20, "comparison-2col": 0.15,
            "scientific-figure": 0.15, "section": 0.10
        },
        "narrative_arc": ["title", "context", "architecture", "spec", "tradeoff", "conclusion"],
        "artifact_density": 0.70,
        "slide_count_typical": [7, 12],
        "primary_evidence_form": "architecture-diagram-and-spec-table",
        "rhythm_signature": "thin-rules-quiet-grid",
    },
    "midnight-neon": {
        "preferred_variants": [
            "title", "kpi-hero", "chart", "stats", "comparison-2col",
            "image-sidebar", "flow"
        ],
        "variant_distribution_targets": {
            "kpi-hero": 0.15, "chart": 0.20, "stats": 0.20,
            "comparison-2col": 0.15, "image-sidebar": 0.15, "flow": 0.15
        },
        "narrative_arc": ["title", "hook", "demo", "metrics", "what-next", "close"],
        "artifact_density": 0.75,
        "slide_count_typical": [7, 12],
        "primary_evidence_form": "dark-canvas-chart-with-neon-stat",
        "rhythm_signature": "console-with-headline-stat",
    },
    "sunset-investor": {
        "preferred_variants": [
            "title", "kpi-hero", "chart", "comparison-2col", "stats", "table",
            "cards-3"
        ],
        "variant_distribution_targets": {
            "kpi-hero": 0.15, "chart": 0.20, "comparison-2col": 0.20,
            "stats": 0.15, "table": 0.15, "cards-3": 0.15
        },
        "narrative_arc": ["title", "problem", "solution", "market", "traction", "use-of-funds", "ask"],
        "artifact_density": 0.85,
        "slide_count_typical": [10, 15],
        "primary_evidence_form": "market-chart-and-financial-bridge",
        "rhythm_signature": "investor-story-with-financial-spine",
    },
    "lavender-ops": {
        "preferred_variants": [
            "title", "timeline", "flow", "stats", "cards-3", "comparison-2col",
            "matrix"
        ],
        "variant_distribution_targets": {
            "timeline": 0.25, "flow": 0.15, "stats": 0.15, "cards-3": 0.15,
            "comparison-2col": 0.15, "matrix": 0.15
        },
        "narrative_arc": ["title", "overview", "roadmap", "cadence", "status", "blockers"],
        "artifact_density": 0.70,
        "slide_count_typical": [7, 12],
        "primary_evidence_form": "roadmap-band-and-status-board",
        "rhythm_signature": "operating-cadence-with-status-color",
    },
    "executive-clinical": {
        "preferred_variants": [
            "title", "kpi-hero", "stats", "lab-run-results", "comparison-2col",
            "table", "scientific-figure"
        ],
        "variant_distribution_targets": {
            "kpi-hero": 0.15, "stats": 0.15, "lab-run-results": 0.20,
            "comparison-2col": 0.20, "table": 0.15, "scientific-figure": 0.15
        },
        "narrative_arc": ["title", "cohort", "endpoints", "outcomes", "risk-benefit", "decision"],
        "artifact_density": 0.85,
        "slide_count_typical": [8, 12],
        "primary_evidence_form": "clinical-readout-and-decision-table",
        "rhythm_signature": "evidence-brief-with-decision-strip",
    },
    "forest-research": {
        "preferred_variants": [
            "title", "section", "scientific-figure", "image-sidebar",
            "comparison-2col", "chart", "table"
        ],
        "variant_distribution_targets": {
            "scientific-figure": 0.25, "image-sidebar": 0.20, "comparison-2col": 0.15,
            "chart": 0.15, "table": 0.15, "section": 0.10
        },
        "narrative_arc": ["title", "field-context", "evidence-plates", "interpretation", "conclusion"],
        "artifact_density": 0.85,
        "slide_count_typical": [8, 12],
        "primary_evidence_form": "evidence-plate-and-field-note",
        "rhythm_signature": "chart-plus-interpretation",
    },
    "lab-report": {
        "preferred_variants": [
            "title", "section", "scientific-figure", "lab-run-results", "table",
            "comparison-2col", "image-sidebar"
        ],
        "variant_distribution_targets": {
            "lab-run-results": 0.25, "scientific-figure": 0.20, "table": 0.20,
            "comparison-2col": 0.15, "image-sidebar": 0.10, "section": 0.10
        },
        "narrative_arc": ["title", "method", "results", "qc", "interpretation", "conclusion"],
        "artifact_density": 0.90,
        "slide_count_typical": [8, 15],
        "primary_evidence_form": "lab-readout-and-method-block",
        "rhythm_signature": "method-results-qc",
    },
}


def _slug(value: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in (value or "").lower()).strip("-")


def _content_tweak(record: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    """Per-record adjustment to the family template.

    Reads the record's layout_tags and content_treatments to nudge variant
    preference toward what that specific record emphasizes. Keeps the family
    skeleton; only tilts the distribution.
    """
    tweaks: dict[str, Any] = {}
    treatments = [t.lower() for t in record.get("content_treatments", [])]
    layout = [l.lower() for l in record.get("layout_tags", [])]
    all_tags = treatments + layout

    keyword_to_variant = {
        "kpi": "kpi-hero", "dashboard": "stats", "metric": "stats",
        "chart": "chart", "trend": "chart", "graph": "chart",
        "table": "table", "ledger": "table", "matrix": "matrix",
        "risk register": "matrix", "control": "matrix",
        "roadmap": "timeline", "milestone": "timeline", "cadence": "timeline",
        "architecture diagram": "flow", "workflow diagram": "flow",
        "figure": "scientific-figure", "plate": "scientific-figure",
        "image": "image-sidebar", "screenshot": "image-sidebar",
        "card": "cards-3", "pillar": "cards-3",
        "compar": "comparison-2col", "vs": "comparison-2col",
        "lab readout": "lab-run-results", "instrument": "lab-run-results",
    }

    seen_variants: set[str] = set()
    boosted: list[str] = []
    for kw, variant in keyword_to_variant.items():
        if any(kw in tag for tag in all_tags) and variant not in seen_variants:
            boosted.append(variant)
            seen_variants.add(variant)

    if boosted:
        base = list(template["preferred_variants"])
        reordered = [v for v in boosted if v in base]
        rest = [v for v in base if v not in reordered]
        tweaks["preferred_variants_record_tilt"] = reordered + rest

    if any("dense" in tag or "compact" in tag for tag in all_tags):
        tweaks["artifact_density_record_tilt"] = min(1.0, template["artifact_density"] + 0.05)
    elif any("sparse" in tag or "minimal" in tag or "quiet" in tag for tag in all_tags):
        tweaks["artifact_density_record_tilt"] = max(0.30, template["artifact_density"] - 0.10)

    return tweaks


def _enrich_record(record: dict[str, Any]) -> dict[str, Any] | None:
    family = record.get("primary_style_family")
    template = FAMILY_GRAMMAR_TEMPLATES.get(family)
    if not template:
        return None

    enriched = {
        "deck_id": record.get("deck_id"),
        "primary_style_family": family,
        "distinctiveness_score": record.get("distinctiveness_score"),
        "layout_tags": record.get("layout_tags", []),
        "content_treatments": record.get("content_treatments", []),
        "palette_tokens": record.get("palette_tokens", []),
        "typography_tokens": record.get("typography_tokens", []),
        "source_url": record.get("source_url"),
        "grammar": dict(template),
    }
    tweaks = _content_tweak(record, template)
    if tweaks:
        enriched["grammar_record_tilt"] = tweaks
    return enriched


def _select_curated(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        fam = r.get("primary_style_family")
        if fam not in FAMILY_GRAMMAR_TEMPLATES:
            continue
        by_family.setdefault(fam, []).append(r)

    curated: list[dict[str, Any]] = []
    for fam in FAMILY_GRAMMAR_TEMPLATES:
        fam_records = by_family.get(fam, [])
        fam_records.sort(key=lambda r: (r.get("distinctiveness_score", 0) or 0), reverse=True)
        cap = min(RECORDS_PER_FAMILY_CAP, len(fam_records))
        curated.extend(fam_records[:cap])
    return curated


def main() -> None:
    corpus_path = _resolve_corpus_path()
    with corpus_path.open() as fh:
        corpus = json.load(fh)

    curated = _select_curated(corpus.get("records", []))
    enriched_records = [r for r in (_enrich_record(rec) for rec in curated) if r is not None]

    family_counts: dict[str, int] = {}
    for r in enriched_records:
        fam = r["primary_style_family"]
        family_counts[fam] = family_counts.get(fam, 0) + 1

    output = {
        "schema_version": "style_grammar_index_v1",
        "source_corpus": corpus_path.name,
        "source_corpus_version": corpus.get("catalog_version"),
        "records_per_family_cap": RECORDS_PER_FAMILY_CAP,
        "family_counts": dict(sorted(family_counts.items())),
        "total_records": len(enriched_records),
        "family_grammar_templates": FAMILY_GRAMMAR_TEMPLATES,
        "records": enriched_records,
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=False))
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(enriched_records)} records, {len(family_counts)} families)")
    for fam, count in sorted(family_counts.items()):
        print(f"  {fam}: {count}")


if __name__ == "__main__":
    main()
