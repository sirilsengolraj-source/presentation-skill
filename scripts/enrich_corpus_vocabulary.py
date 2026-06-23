"""Enrich the descriptor corpus with synthetic variants in thin families.

The base corpus at references/large_style_corpus_catalog.json is heavily
skewed: 3 families hold 65% of records and 4 families hold only 10-25.
Thin families typically have identical tag combinations across all of
their records, so the actual within-family vocabulary diversity is 0.

This script synthesizes additional DESCRIPTOR-ONLY records that vary the
layout_tags / content_treatments / palette_tokens / typography_tokens
combinations within each thin family. The records are clearly marked
``synthetic_variant: true`` and ``deck_format: descriptor-only`` so the
policy boundary is preserved (no slide assets, screenshots, or copied
content of any kind).

Output: references/large_style_corpus_catalog_enriched.json
(side-by-side with the original; original is untouched).

The atomization script reads whichever catalog path you point it at.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = REPO_ROOT / "references" / "large_style_corpus_catalog.json"
OUTPUT_PATH = REPO_ROOT / "references" / "large_style_corpus_catalog_enriched.json"

TARGET_RECORDS_PER_THIN_FAMILY = 60


# Family-specific axes of synthetic variation. Each "axis" is a list of
# tag-cluster choices that get combined to produce one descriptor record.
# The combinatorial product (e.g. 5 layouts × 4 contents × 3 palettes)
# generates the variant pool.

FAMILY_VARIATION_AXES: dict[str, dict[str, list[list[str]]]] = {
    "lab-report": {
        "layout_clusters": [
            ["figure-first", "result-table", "method-readout", "source-footer"],
            ["longitudinal-run-strip", "method-block", "result-table", "source-footer"],
            ["cohort-grid", "demographic-strip", "result-table", "source-footer"],
            ["protocol-frame", "method-block", "qc-rail", "source-footer"],
            ["quiet-margin", "single-figure-plate", "footnotes-block", "source-footer"],
            ["concordance-strip", "qc-rail", "result-table", "source-footer"],
            ["assay-readout-bar", "method-readout", "result-table", "source-footer"],
        ],
        "content_clusters": [
            ["assay tables", "references", "run metadata", "scientific figures"],
            ["assay tables", "longitudinal run summary", "qc passes", "scientific figures", "references"],
            ["assay tables", "cohort breakdown", "demographic notes", "scientific figures", "references"],
            ["protocol summary", "method comparison", "qc passes", "scientific figures", "references"],
            ["scientific figures", "footnotes", "references", "assay tables"],
            ["concordance summary", "qc passes", "scientific figures", "references"],
            ["assay tables", "instrument calibration", "scientific figures", "references"],
        ],
        "palette_clusters": [
            ["paper", "black ink", "subtle rule"],
            ["clinical blue", "white", "status accent"],
            ["ink", "soft cream", "muted accent"],
        ],
        "typography_clusters": [
            ["caption-rich-evidence", "method-block-headings"],
            ["quiet-technical-labels", "evidence-caption-pairs"],
            ["measured-body-copy", "small-references"],
        ],
    },
    "forest-research": {
        "layout_clusters": [
            ["evidence plates", "field-note sidebars", "chart-plus-interpretation"],
            ["longitudinal-monitoring-strip", "field-note sidebars", "chart-plus-interpretation"],
            ["method-and-uncertainty-pair", "evidence plates", "field-note sidebars"],
            ["field-narrative-band", "evidence plates", "annotated-photo"],
            ["dataset-explorer-grid", "evidence plates", "chart-plus-interpretation"],
            ["map-overlay-band", "field-note sidebars", "chart-plus-interpretation"],
        ],
        "content_clusters": [
            ["field observations", "method caveats", "plots", "study design"],
            ["longitudinal observations", "method caveats", "plots", "study design", "phenology notes"],
            ["uncertainty notes", "method comparisons", "plots", "study design"],
            ["field observations", "annotated photos", "plots", "site narrative"],
            ["dataset breakdown", "field observations", "plots", "study design"],
            ["site map", "field observations", "plots", "method caveats"],
        ],
        "palette_clusters": [
            ["forest green", "earth neutral", "moss accent"],
            ["bark brown", "sage", "muted leaf"],
            ["paper", "ink", "forest accent"],
        ],
        "typography_clusters": [
            ["field-report-headings", "annotated-caption-pairs"],
            ["plain language labels", "small-references"],
            ["sober-research-headings", "footnoted-method-text"],
        ],
    },
    "executive-clinical": {
        "layout_clusters": [
            ["executive evidence brief", "clinical KPI strip", "decision readout"],
            ["safety-focused band", "cohort-strip", "decision readout"],
            ["efficacy-headline frame", "kpi-rail", "decision readout"],
            ["cohort-comparison grid", "outcomes-strip", "decision readout"],
            ["decision-strip dominant", "kpi-strip", "executive evidence brief"],
            ["timeline-of-evidence", "kpi-strip", "decision readout"],
        ],
        "content_clusters": [
            ["clinical outcomes", "decision tables", "patient cohorts", "risk/benefit"],
            ["safety endpoints", "patient cohorts", "decision tables", "risk/benefit"],
            ["primary endpoint highlight", "patient cohorts", "decision tables", "risk/benefit"],
            ["cohort-comparison", "outcomes by arm", "decision tables", "risk/benefit"],
            ["decision strip", "patient cohorts", "outcomes summary"],
            ["timeline of evidence", "endpoint readout", "decision tables", "risk/benefit"],
        ],
        "palette_clusters": [
            ["clinical blue", "white", "status accent"],
            ["ink", "clinical neutral", "decisive accent"],
            ["navy", "pale", "warning accent"],
        ],
        "typography_clusters": [
            ["executive headings", "readable metric labels"],
            ["decisive headings", "metric-pair labels"],
            ["briefing headings", "evidence labels"],
        ],
    },
    "lavender-ops": {
        "layout_clusters": [
            ["workflow board", "roadmap bands", "operating cadence"],
            ["status-rail dominant", "workflow board", "roadmap bands"],
            ["cadence-calendar", "operating cadence", "roadmap bands"],
            ["squad-board grid", "workflow board", "operating cadence"],
            ["dependency-map", "workflow board", "roadmap bands"],
            ["blocker-strip dominant", "workflow board", "operating cadence"],
        ],
        "content_clusters": [
            ["operating metrics", "roadmaps", "team status", "workflow diagrams"],
            ["status updates", "roadmaps", "team status", "blocker list"],
            ["cadence summary", "operating metrics", "roadmaps"],
            ["squad standup notes", "team status", "workflow diagrams"],
            ["dependencies", "workflow diagrams", "team status", "roadmaps"],
            ["blocker triage", "team status", "operating metrics"],
        ],
        "palette_clusters": [
            ["lavender accent", "cool neutral", "soft status"],
            ["lilac", "slate", "status accent"],
            ["periwinkle", "pale neutral", "blocker red"],
        ],
        "typography_clusters": [
            ["ops labels", "planning metadata"],
            ["operational labels", "weekly-metadata-text"],
            ["squad headings", "status-pair labels"],
        ],
    },
}


def _synthesize_variants(family: str, axes: dict[str, list[list[str]]], existing_count: int) -> list[dict[str, Any]]:
    """Combine variation axes to generate target number of synthetic records."""
    needed = max(0, TARGET_RECORDS_PER_THIN_FAMILY - existing_count)
    if needed == 0:
        return []

    layouts = axes["layout_clusters"]
    contents = axes["content_clusters"]
    palettes = axes["palette_clusters"]
    typos = axes["typography_clusters"]

    out: list[dict[str, Any]] = []
    seed = 0
    for li, layout in enumerate(layouts):
        for ci, content in enumerate(contents):
            if li != ci:
                # Pair each layout primarily with its matched content cluster,
                # but allow cross-pairing for variation; here keep the natural
                # pairing and a few cross-pairs to avoid combinatorial blowup.
                if (li + ci) % 2 != 0:
                    continue
            for pi, palette in enumerate(palettes):
                for ti, typo in enumerate(typos):
                    if len(out) >= needed:
                        return out
                    seed += 1
                    distinctiveness = 25 + ((seed * 7) % 25)
                    out.append(
                        {
                            "deck_id": f"synthetic:{family}:{seed:03d}",
                            "primary_style_family": family,
                            "distinctiveness_score": distinctiveness,
                            "layout_tags": list(layout),
                            "content_treatments": list(content),
                            "palette_tokens": list(palette),
                            "typography_tokens": list(typo),
                            "synthetic_variant": True,
                            "deck_format": "descriptor-only",
                            "source_url": "",
                            "repository": "synthetic-variant",
                            "rights_posture": "descriptor-only-no-assets",
                        }
                    )
    return out


def main() -> None:
    with SOURCE_PATH.open() as fh:
        corpus = json.load(fh)

    records = list(corpus.get("records", []))
    family_counts: dict[str, int] = {}
    for r in records:
        fam = r.get("primary_style_family", "unknown")
        family_counts[fam] = family_counts.get(fam, 0) + 1

    synthetic_total = 0
    per_family_added: dict[str, int] = {}
    for family, axes in FAMILY_VARIATION_AXES.items():
        existing = family_counts.get(family, 0)
        added = _synthesize_variants(family, axes, existing)
        records.extend(added)
        synthetic_total += len(added)
        per_family_added[family] = len(added)

    enriched = dict(corpus)
    enriched["records"] = records
    enriched["catalog_version"] = "large_style_corpus_v1_enriched"
    enriched["enrichment_notes"] = {
        "target_per_thin_family": TARGET_RECORDS_PER_THIN_FAMILY,
        "synthetic_records_added": synthetic_total,
        "per_family_added": per_family_added,
        "policy": "synthetic descriptor records only; no slide assets, screenshots, or copied content of any kind.",
    }

    OUTPUT_PATH.write_text(json.dumps(enriched, indent=2, sort_keys=False))
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  total records (after enrichment): {len(records)}")
    print(f"  synthetic records added: {synthetic_total}")
    for family, count in per_family_added.items():
        existing = family_counts.get(family, 0)
        print(f"    {family}: {existing} → {existing + count}")


if __name__ == "__main__":
    main()
