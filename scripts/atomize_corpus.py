"""Atomize the 2,000-record style corpus into a token atlas.

The base corpus stores style descriptors per record (palette_tokens,
typography_tokens, layout_tags, content_treatments). For LEGO-style
composition we need to invert that: catalog every distinct atom across
all records, plus the skill-specific treatments those atoms imply
(chart_treatment, table_treatment, header_treatment, etc.).

The atlas at references/style_token_atlas.json is queried at deck-build
time by scripts/style_atom_router.py to mix-and-match atoms across
families. This is the corpus working as a LEGO box, not a family lookup.

Atom types catalogued:
- palette        : color tokens (e.g., "neon cyan", "clinical blue")
- typography     : type tokens (e.g., "monospace labels", "magazine heading")
- layout_motif   : layout tags (e.g., "thin rules", "risk register")
- content_treatment : content tags (e.g., "KPI cards", "method comparison")
- chart_treatment : derived (sparse-wide, facts-right, threshold-band, ...)
- table_treatment : derived (compact-ledger, decision-matrix, journal-grid)
- header_treatment : derived (auto, eyebrow, lab-clean, side-rail, plain)
- footer_treatment : derived (source-line, page-numbers, plain)
- density         : derived (low, medium, high)
- decorative_motif : derived (eyebrow-tag, focus-box, side-rail, accent-strip)
- arc_beat        : derived (problem, evidence, decision, ...)
- rhythm_signature : derived (essay-spread, board-memo, method-results, ...)

For each atom we record: id, type, value, family_origins (which families
use it and how often), frequency, distinctiveness_avg, co_occurring_atoms,
semantic_tags.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ENRICHED_CORPUS_PATH = REPO_ROOT / "references" / "large_style_corpus_catalog_enriched.json"
BASE_CORPUS_PATH = REPO_ROOT / "references" / "large_style_corpus_catalog.json"
OUTPUT_PATH = REPO_ROOT / "references" / "style_token_atlas.json"


def _resolve_corpus_path() -> Path:
    """Prefer the enriched catalog when present, fall back to the base corpus."""
    return ENRICHED_CORPUS_PATH if ENRICHED_CORPUS_PATH.exists() else BASE_CORPUS_PATH


# Skill-vocabulary derivations from descriptive corpus tags.
# Each rule: substring match in any of (layout_tags + content_treatments)
# → emit one skill-specific atom value.

CHART_TREATMENT_RULES = [
    ("sparse technical grid", "sparse-wide"),
    ("sparse", "sparse-wide"),
    ("thin rule", "sparse-wide"),
    ("minimal chart", "minimal"),
    ("quiet", "sparse-wide"),
    ("trend chart", "facts-right"),
    ("dashboard", "facts-right"),
    ("KPI rail", "hero-stat"),
    ("kpi", "hero-stat"),
    ("neon metric", "threshold-band"),
    ("threshold", "threshold-band"),
    ("risk matrix", "threshold-band"),
    ("clinical KPI", "threshold-band"),
    ("financial chart", "facts-below"),
    ("financial bridge", "facts-below"),
    ("model chart", "facts-right"),
    ("essay spread", "sparse-wide"),
    ("editorial", "sparse-wide"),
]

TABLE_TREATMENT_RULES = [
    ("board memo table", "compact-ledger"),
    ("variance table", "compact-ledger"),
    ("ledger", "compact-ledger"),
    ("control matrix", "decision-matrix"),
    ("risk register", "decision-matrix"),
    ("control table", "decision-matrix"),
    ("incident", "decision-matrix"),
    ("spec table", "journal-grid"),
    ("citation rail", "journal-grid"),
    ("equation", "journal-grid"),
    ("paper summary", "journal-grid"),
    ("decision table", "readout-sidecar"),
    ("clinical outcome", "readout-sidecar"),
    ("patient cohort", "readout-sidecar"),
    ("evidence plate", "readout-sidecar"),
    ("lab readout", "readout-sidecar"),
    ("instrument", "readout-sidecar"),
]

HEADER_TREATMENT_RULES = [
    ("editorial masthead", "eyebrow"),
    ("magazine", "eyebrow"),
    ("journal spread", "stack"),
    ("article-like", "stack"),
    ("dark console", "bar"),
    ("code-demo", "bar"),
    ("dashboard grid", "bar"),
    ("KPI rail", "bar"),
    ("clinical KPI", "lab-clean"),
    ("lab", "lab-clean"),
    ("instrument result", "lab-clean"),
    ("assay table", "lab-clean"),
    ("method-readout", "lab-clean"),
    ("result-table", "lab-clean"),
    ("scientific figure", "lab-clean"),
    ("risk register", "bar"),
    ("workshop canvas", "eyebrow"),
    ("civic explainer", "eyebrow"),
    ("field report", "stack"),
    ("sparse technical grid", "bar"),
    ("architecture frame", "bar"),
    ("narrative reveal", "eyebrow"),
    ("market wedge", "bar"),
    ("investor storyline", "bar"),
    ("workflow board", "bar"),
    ("roadmap bands", "bar"),
]

FOOTER_TREATMENT_RULES = [
    ("citation", "source-line"),
    ("bibliography", "source-line"),
    ("paper summary", "source-line"),
    ("journal", "source-line"),
    ("field-note", "source-line"),
    ("incident summary", "source-line"),
    ("control table", "source-line"),
    ("decision table", "source-line"),
    ("ask/use of funds", "source-line"),
    ("clinical outcome", "source-line"),
    ("policy", "source-line"),
    ("workshop prompt", "standard"),
    ("dark console", "none"),
    ("code demo", "none"),
    ("KPI cards", "standard"),
    ("dashboards", "standard"),
]

DECORATIVE_RULES = [
    ("eyebrow", "eyebrow-tag-above-title"),
    ("editorial masthead", "eyebrow-tag-above-title"),
    ("magazine", "eyebrow-tag-above-title"),
    ("citation rail", "side-rail-citations"),
    ("field-note sidebar", "side-rail-citations"),
    ("decision readout", "focus-box-right"),
    ("KPI rail", "accent-strip-along-top"),
    ("neon metric strip", "accent-strip-along-top"),
    ("thin rule", "thin-rule-under-title"),
    ("thin rules", "thin-rule-under-title"),
    ("incident timeline", "timeline-axis-bottom"),
    ("operating cadence", "timeline-axis-bottom"),
    ("risk register", "matrix-grid-overlay"),
    ("control matrix", "matrix-grid-overlay"),
    ("equation or figure plate", "figure-plate-with-caption"),
    ("evidence plate", "figure-plate-with-caption"),
    ("essay spread", "wide-margin-quiet-page"),
    ("sparse technical grid", "wide-margin-quiet-page"),
    ("architecture frame", "thin-frame-around-canvas"),
    ("dark console", "code-block-band"),
    ("narrative reveal", "punchy-pull-quote"),
    ("market wedge", "bold-call-to-action-strip"),
    ("workshop canvas", "soft-edge-card-cluster"),
    ("focus box", "focus-box-right"),
]

DENSITY_RULES = [
    ("sparse", "low"),
    ("minimal", "low"),
    ("quiet", "low"),
    ("essay spread", "low"),
    ("wide margin", "low"),
    ("single-figure-plate", "low"),
    ("field-narrative-band", "low"),
    ("dashboard grid", "high"),
    ("dense", "high"),
    ("compact", "high"),
    ("ledger", "high"),
    ("board memo", "high"),
    ("KPI rail", "high"),
    ("risk register", "high"),
    ("dataset-explorer-grid", "high"),
    ("longitudinal-run-strip", "high"),
    ("editorial", "medium"),
    ("narrative", "medium"),
    ("workshop", "medium"),
    ("civic explainer", "medium"),
    ("field report", "medium"),
    ("figure-first", "medium"),
    ("result-table", "medium"),
    ("method-readout", "medium"),
    ("method-block", "medium"),
    ("source-footer", "medium"),
    ("evidence plate", "medium"),
    ("field-note", "medium"),
    ("executive evidence brief", "medium"),
    ("decision readout", "medium"),
    ("clinical KPI", "medium"),
    ("workflow board", "medium"),
    ("roadmap bands", "medium"),
    ("operating cadence", "medium"),
    ("journal spread", "medium"),
    ("paper", "medium"),
    ("citation rail", "medium"),
    ("scientific figure", "medium"),
]

ARC_BEAT_RULES = [
    ("problem/solution", "problem"),
    ("problem", "problem"),
    ("solution", "solution"),
    ("traction proof", "traction"),
    ("growth loops", "traction"),
    ("market sizing", "market"),
    ("market map", "market"),
    ("market wedge", "market"),
    ("ask/use of funds", "ask"),
    ("business model", "model"),
    ("financial chart", "financials"),
    ("financial bridge", "financials"),
    ("method", "method"),
    ("paper summary", "method"),
    ("equations", "method"),
    ("results", "results"),
    ("evidence interpretation", "results"),
    ("evidence plate", "results"),
    ("KPI cards", "kpi-summary"),
    ("dashboards", "kpi-summary"),
    ("trend charts", "trend"),
    ("variance", "variance"),
    ("decision table", "decision"),
    ("decision readout", "decision"),
    ("risk matrix", "risk"),
    ("incident", "risk"),
    ("mitigation", "mitigation"),
    ("control table", "controls"),
    ("clinical outcome", "outcomes"),
    ("risk/benefit", "risk-benefit"),
    ("patient cohort", "cohort"),
    ("workflow diagram", "workflow"),
    ("workflow board", "workflow"),
    ("architecture diagram", "architecture"),
    ("roadmap", "roadmap"),
    ("team status", "status"),
    ("operating metrics", "operations"),
    ("community findings", "field-findings"),
    ("training step", "training"),
    ("policy summary", "policy"),
    ("workshop prompt", "workshop"),
    ("annotated examples", "annotated"),
    ("quotes", "voice"),
    ("citation", "references"),
    ("bibliography", "references"),
    ("code demo", "demo"),
    ("model chart", "model-card"),
    ("security readout", "security"),
    ("method-readout", "method"),
    ("result-table", "results"),
    ("assay table", "results"),
    ("scientific figure", "results"),
    ("run metadata", "method"),
    ("field observation", "field-findings"),
    ("method caveat", "method"),
    ("study design", "method"),
    ("plots", "results"),
    ("annotated chart", "results"),
    ("source-footer", "references"),
]

RHYTHM_RULES = [
    ("essay spread", "essay-spread-with-pauses"),
    ("editorial", "essay-spread-with-pauses"),
    ("narrative reveal", "punchy-claim+visual-proof"),
    ("market wedge", "punchy-claim+visual-proof"),
    ("product proof", "punchy-claim+visual-proof"),
    ("risk register", "risk-then-control"),
    ("control matrix", "risk-then-control"),
    ("dashboard grid", "metric-driven-board-memo"),
    ("board memo", "metric-driven-board-memo"),
    ("kpi rail", "metric-driven-board-memo"),
    ("journal spread", "method-then-results"),
    ("paper summary", "method-then-results"),
    ("citation rail", "method-then-results"),
    ("dark console", "console-with-headline-stat"),
    ("neon metric", "console-with-headline-stat"),
    ("clinical KPI", "evidence-brief-with-decision-strip"),
    ("decision readout", "evidence-brief-with-decision-strip"),
    ("workflow board", "operating-cadence-with-status-color"),
    ("roadmap bands", "operating-cadence-with-status-color"),
    ("operating cadence", "operating-cadence-with-status-color"),
    ("investor storyline", "investor-story-with-financial-spine"),
    ("financial bridge", "investor-story-with-financial-spine"),
    ("workshop canvas", "human-scale-narrative"),
    ("civic explainer", "human-scale-narrative"),
    ("field report", "human-scale-narrative"),
    ("evidence plate", "chart-plus-interpretation"),
    ("chart-plus-interpretation", "chart-plus-interpretation"),
    ("field-note sidebar", "chart-plus-interpretation"),
    ("sparse technical grid", "thin-rules-quiet-grid"),
    ("architecture frame", "thin-rules-quiet-grid"),
    ("thin rules", "thin-rules-quiet-grid"),
    ("method-readout", "method-then-results"),
    ("result-table", "method-then-results"),
    ("assay table", "method-then-results"),
    ("scientific figure", "method-then-results"),
    ("run metadata", "method-then-results"),
    ("evidence plate", "chart-plus-interpretation"),
    ("field-note sidebar", "chart-plus-interpretation"),
    ("study design", "chart-plus-interpretation"),
    ("executive evidence brief", "evidence-brief-with-decision-strip"),
    ("clinical KPI", "evidence-brief-with-decision-strip"),
]


def _slug(value: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in (value or "").lower()).strip("-")


def _derive(record_tags: list[str], rules: list[tuple[str, str]]) -> set[str]:
    """Match record tags against substring rules, return derived atom values."""
    record_text = " | ".join(record_tags).lower()
    out: set[str] = set()
    for substring, derived_value in rules:
        if substring.lower() in record_text:
            out.add(derived_value)
    return out


def _collect_record_atoms(record: dict[str, Any]) -> dict[str, list[str]]:
    """Extract all atom values from a single record across all atom types."""
    palette = list(record.get("palette_tokens", []))
    typography = list(record.get("typography_tokens", []))
    layout = list(record.get("layout_tags", []))
    content = list(record.get("content_treatments", []))
    all_descriptive = layout + content

    atoms = {
        "palette": palette,
        "typography": typography,
        "layout_motif": layout,
        "content_treatment": content,
        "chart_treatment": sorted(_derive(all_descriptive, CHART_TREATMENT_RULES)),
        "table_treatment": sorted(_derive(all_descriptive, TABLE_TREATMENT_RULES)),
        "header_treatment": sorted(_derive(all_descriptive, HEADER_TREATMENT_RULES)),
        "footer_treatment": sorted(_derive(all_descriptive, FOOTER_TREATMENT_RULES)),
        "decorative_motif": sorted(_derive(all_descriptive, DECORATIVE_RULES)),
        "density": sorted(_derive(all_descriptive, DENSITY_RULES)),
        "arc_beat": sorted(_derive(all_descriptive, ARC_BEAT_RULES)),
        "rhythm_signature": sorted(_derive(all_descriptive, RHYTHM_RULES)),
    }
    return atoms


def build_atlas(records: list[dict[str, Any]]) -> dict[str, Any]:
    atoms_by_type: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    co_occurrence_counter: Counter = Counter()
    family_atom_index: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))

    for record in records:
        family = record.get("primary_style_family", "unknown")
        distinct = record.get("distinctiveness_score") or 0
        record_atoms = _collect_record_atoms(record)

        for atom_type, values in record_atoms.items():
            for value in values:
                key = _slug(value)
                bucket = atoms_by_type[atom_type].setdefault(
                    key,
                    {
                        "atom_id": f"{atom_type}:{key}",
                        "atom_type": atom_type,
                        "value": value,
                        "frequency": 0,
                        "family_origins": Counter(),
                        "distinctiveness_sum": 0,
                    },
                )
                bucket["frequency"] += 1
                bucket["family_origins"][family] += 1
                bucket["distinctiveness_sum"] += distinct
                family_atom_index[family][atom_type][key] += 1

        flat = [
            f"{atype}:{_slug(v)}"
            for atype, values in record_atoms.items()
            for v in values
        ]
        for i, a in enumerate(flat):
            for b in flat[i + 1:]:
                pair = tuple(sorted([a, b]))
                co_occurrence_counter[pair] += 1

    atoms_out: dict[str, list[dict[str, Any]]] = {}
    for atom_type, items in atoms_by_type.items():
        out_list = []
        for key, info in items.items():
            freq = info["frequency"]
            avg_dist = round(info["distinctiveness_sum"] / freq, 2) if freq else 0.0
            out_list.append(
                {
                    "atom_id": info["atom_id"],
                    "atom_type": atom_type,
                    "value": info["value"],
                    "frequency": freq,
                    "distinctiveness_avg": avg_dist,
                    "family_origins": dict(info["family_origins"].most_common()),
                }
            )
        out_list.sort(key=lambda a: (-a["frequency"], a["atom_id"]))
        atoms_out[atom_type] = out_list

    by_family = {
        family: {atype: dict(counter.most_common(20)) for atype, counter in by_type.items()}
        for family, by_type in family_atom_index.items()
    }

    top_co_occurrences = [
        {"pair": list(pair), "count": count}
        for pair, count in co_occurrence_counter.most_common(500)
    ]

    return {
        "schema_version": "style_token_atlas_v1",
        "source_records_processed": len(records),
        "atom_type_counts": {atype: len(items) for atype, items in atoms_out.items()},
        "atoms": atoms_out,
        "indexes": {"by_family": by_family},
        "co_occurrence_top": top_co_occurrences,
    }


def main() -> None:
    corpus_path = _resolve_corpus_path()
    with corpus_path.open() as fh:
        corpus = json.load(fh)

    atlas = build_atlas(corpus.get("records", []))
    atlas["source_corpus"] = corpus_path.name
    OUTPUT_PATH.write_text(json.dumps(atlas, indent=2, sort_keys=False))

    print(f"Source corpus: {corpus_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  source records processed: {atlas['source_records_processed']}")
    for atype, count in atlas["atom_type_counts"].items():
        print(f"  {atype}: {count} distinct atoms")


if __name__ == "__main__":
    main()
