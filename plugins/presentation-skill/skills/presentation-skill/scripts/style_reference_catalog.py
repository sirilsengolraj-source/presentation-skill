#!/usr/bin/env python3
"""Publish-safe synthetic style references for preset routing.

The catalog is intentionally descriptive, not a copied deck library. Each
reference describes an original generic slide family that agents can recreate
from source files without importing proprietary slide geometry or content.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

try:
    from style_reference_sources import SOURCE_MANIFEST_VERSION, preset_source_intake_route
except Exception:  # pragma: no cover - catalog can still emit synthetic refs if manifest is unavailable
    SOURCE_MANIFEST_VERSION = "style_reference_source_manifest_v1"

    def preset_source_intake_route(_preset: str) -> dict[str, Any]:
        return {}


STYLE_REFERENCE_VERSION = "style_reference_catalog_v1"
LAYOUT_PLAYBOOK_VERSION = "style_reference_layout_playbook_v1"
STYLE_REFERENCE_MIX_PLAN_VERSION = "style_reference_mix_plan_v1"
EXAMPLE_STORYBOARD_VERSION = "style_reference_example_storyboard_v1"
CONTENT_RECIPE_LIBRARY_VERSION = "style_reference_content_recipe_library_v1"
STRUCTURAL_MOTIF_LIBRARY_VERSION = "style_reference_structural_motif_library_v1"
STYLE_METRIC_PROFILE_VERSION = "style_reference_metric_profile_v1"

REQUIRED_CONTENT_TREATMENTS = (
    "title",
    "comparison",
    "chart",
    "table",
    "figure",
    "dashboard",
    "decision",
    "references",
)

REQUIRED_LAYOUT_PLAYBOOK_FIELDS = (
    "playbook_version",
    "preferred_variants",
    "treatment_variant_map",
    "treatment_archetypes",
    "slide_archetypes",
    "opening_sequence",
    "content_rules",
    "avoid_variants",
)

REQUIRED_STORYBOARD_FIELDS = (
    "storyboard_version",
    "topic",
    "title",
    "subtitle",
    "chart",
    "dashboard_facts",
    "table",
    "figure",
    "comparison",
    "decision",
    "source_notes",
)

REQUIRED_CONTENT_RECIPE_FIELDS = (
    "recipe_version",
    "treatment_key",
    "primary_variants",
    "content_goal",
    "evidence_anchor",
    "required_slots",
    "data_roles",
    "storyboard_example",
    "source_posture",
    "authoring_checks",
)

REQUIRED_STYLE_METRIC_FIELDS = (
    "metric_profile_version",
    "style_preset",
    "density_level",
    "whitespace_ratio_target",
    "body_words_per_content_slide",
    "max_primary_objects",
    "visual_hierarchy",
    "evidence_object_mix",
    "source_burden",
    "footer_posture",
    "artifact_bias",
    "readability_bias",
    "metric_signature",
)

SUPPORTED_OUTLINE_VARIANTS = (
    "title",
    "standard",
    "split",
    "cards-2",
    "cards-3",
    "timeline",
    "stats",
    "kpi-hero",
    "table",
    "lab-run-results",
    "comparison-2col",
    "matrix",
    "flow",
    "chart",
    "image-sidebar",
    "scientific-figure",
    "generated-image",
)

DEFAULT_TREATMENT_VARIANT_MAP: dict[str, list[str]] = {
    "title": ["title"],
    "comparison": ["comparison-2col", "split", "matrix"],
    "chart": ["chart"],
    "table": ["table", "lab-run-results"],
    "figure": ["image-sidebar", "scientific-figure"],
    "dashboard": ["stats", "table"],
    "decision": ["standard", "table"],
    "references": ["table"],
}

TITLE_ARCHETYPE_LIBRARY: dict[str, dict[str, Any]] = {
    "executive-clinical": {
        "archetype_id": "clinical-status-rail-opener",
        "title_layout": "split-hero",
        "structure": "left evidence rail, clinical scope chips, and one implication promise",
        "required_fields": ["pathway or cohort", "evidence promise", "decision audience"],
    },
    "bold-startup-narrative": {
        "archetype_id": "poster-proof-chip-opener",
        "title_layout": "poster",
        "structure": "oversized market claim, one proof chip cluster, and asymmetric accent slab",
        "required_fields": ["behavior shift", "proof chip", "next milestone"],
    },
    "data-heavy-boardroom": {
        "archetype_id": "board-period-scope-opener",
        "title_layout": "split-hero",
        "structure": "plain board title with operating period, scope, and decision context",
        "required_fields": ["period", "metric scope", "decision context"],
    },
    "sunset-investor": {
        "archetype_id": "investor-thesis-window-opener",
        "title_layout": "poster",
        "structure": "warm thesis opener with market window, round metadata, and downside note",
        "required_fields": ["thesis", "round or ask", "market timing"],
    },
    "forest-research": {
        "archetype_id": "atlas-scope-tag-opener",
        "title_layout": "light-atlas",
        "structure": "atlas-style opener with geography/system tags and a field-period cue",
        "required_fields": ["system or place", "field period", "management question"],
    },
    "midnight-neon": {
        "archetype_id": "command-state-strip-opener",
        "title_layout": "command-center",
        "structure": "dark command title with system state, active route, and severity/readout strip",
        "required_fields": ["system", "state", "escalation question"],
    },
    "paper-journal": {
        "archetype_id": "journal-masthead-abstract-opener",
        "title_layout": "masthead",
        "structure": "journal masthead with compact abstract subtitle and methods/results scope",
        "required_fields": ["method", "result scope", "caveat"],
    },
    "arctic-minimal": {
        "archetype_id": "sparse-object-label-opener",
        "title_layout": "light-atlas",
        "structure": "one exact object/scope label, large quiet title, and minimal decision line",
        "required_fields": ["object", "scope qualifier", "decision line"],
    },
    "charcoal-safety": {
        "archetype_id": "severity-rail-ask-opener",
        "title_layout": "command-center",
        "structure": "severity-first rail with incident system, date, and remediation ask",
        "required_fields": ["severity", "system/date", "ask"],
    },
    "lavender-ops": {
        "archetype_id": "workflow-lane-period-opener",
        "title_layout": "masthead",
        "structure": "workflow lane labels, operating period tag, and queue/cadence promise",
        "required_fields": ["workflow lanes", "period", "operating question"],
    },
    "warm-terracotta": {
        "archetype_id": "case-context-cue-opener",
        "title_layout": "masthead",
        "structure": "case context plus one object/place cue before evidence",
        "required_fields": ["place or object", "human/service moment", "decision"],
    },
    "lab-report": {
        "archetype_id": "lab-run-metadata-plate-opener",
        "title_layout": "lab-plate",
        "structure": "run/sample/method metadata plate with restrained top and bottom rules",
        "required_fields": ["run or sample scope", "method", "review state"],
    },
    "editorial-minimal": {
        "archetype_id": "editorial-masthead-linebreak-opener",
        "title_layout": "masthead",
        "structure": "editorial masthead with deliberate line break and one precise subtitle",
        "required_fields": ["civic or narrative question", "scope", "source posture"],
    },
}

REFERENCE_ARCHETYPE_LIBRARY: dict[str, dict[str, Any]] = {
    "executive-clinical": {
        "archetype_id": "trial-report-id-footer",
        "footer_mode": "source-line",
        "structure": "trial/report IDs in footer; full references only when proof burden requires it",
        "required_fields": ["source id", "n/r or report label", "claim link"],
    },
    "bold-startup-narrative": {
        "archetype_id": "appendix-credit-lite",
        "footer_mode": "standard",
        "structure": "short credibility IDs in footer and optional appendix credits for market claims",
        "required_fields": ["claim source", "proof chip source", "appendix note"],
    },
    "data-heavy-boardroom": {
        "archetype_id": "data-cut-version-appendix",
        "footer_mode": "source-line",
        "structure": "period, data cut, and version in footer with appendix table for long notes",
        "required_fields": ["period", "data cut", "version"],
    },
    "sunset-investor": {
        "archetype_id": "market-source-appendix",
        "footer_mode": "standard",
        "structure": "sparse footer IDs and appendix references for market/tam/unit-economics sources",
        "required_fields": ["market source", "economics source", "usage note"],
    },
    "forest-research": {
        "archetype_id": "report-dataset-footer",
        "footer_mode": "source-line",
        "structure": "dataset/report IDs in footer plus final references for reports and methods",
        "required_fields": ["dataset id", "method source", "access date"],
    },
    "midnight-neon": {
        "archetype_id": "dark-console-provenance",
        "footer_mode": "source-line",
        "structure": "dim readable console footer with run/log/config IDs and no tiny low-contrast refs",
        "required_fields": ["run id", "log/config source", "owner"],
    },
    "paper-journal": {
        "archetype_id": "academic-bibliography-table",
        "footer_mode": "standard",
        "structure": "academic source IDs in captions and final editable bibliography-style table",
        "required_fields": ["citation id", "title", "method/claim link"],
    },
    "arctic-minimal": {
        "archetype_id": "minimal-needed-only-source-line",
        "footer_mode": "standard",
        "structure": "omit refs unless needed; use one short footer line or a compact source slide",
        "required_fields": ["source label", "decision link"],
    },
    "charcoal-safety": {
        "archetype_id": "audit-ticket-footer",
        "footer_mode": "source-line",
        "structure": "audit/ticket/report IDs in footer with owner and remediation traceability",
        "required_fields": ["ticket id", "audit source", "owner"],
    },
    "lavender-ops": {
        "archetype_id": "ops-metric-source-footer",
        "footer_mode": "standard",
        "structure": "operating metric/source footer only on data-heavy pages; avoid appendix burden",
        "required_fields": ["metric source", "period", "owner"],
    },
    "warm-terracotta": {
        "archetype_id": "survey-interview-source-table",
        "footer_mode": "standard",
        "structure": "light footer plus source table for surveys, interviews, and service evidence",
        "required_fields": ["survey/interview source", "moment linked", "usage note"],
    },
    "lab-report": {
        "archetype_id": "lab-source-id-refs-table",
        "footer_mode": "source-line",
        "structure": "short source IDs under footer rule with final editable references table",
        "required_fields": ["method id", "run/source id", "reference table row"],
    },
    "editorial-minimal": {
        "archetype_id": "short-sources-note",
        "footer_mode": "standard",
        "structure": "small sources note or final sparse sources slide; never crowded provenance",
        "required_fields": ["source label", "claim link", "short note"],
    },
}

CONTENT_TREATMENT_ARCHETYPE_DEFAULTS: dict[str, dict[str, Any]] = {
    "comparison": {
        "archetype_id_suffix": "comparison-frame",
        "object_pattern": "paired states with comparable fields and a visible verdict",
        "required_fields": ["left state", "right state", "criterion", "verdict"],
    },
    "chart": {
        "archetype_id_suffix": "chart-readout",
        "object_pattern": "chart object plus direct readout, caveat, and source/data-cut cue",
        "required_fields": ["chart question", "labels", "values", "readout", "source"],
    },
    "table": {
        "archetype_id_suffix": "table-ledger",
        "object_pattern": "editable table with semantic row/column purpose and phrase-length cells",
        "required_fields": ["entity row", "status or metric", "owner/action", "provenance"],
    },
    "figure": {
        "archetype_id_suffix": "figure-proof-object",
        "object_pattern": "figure, image, or diagram owns the slide with caption and interpretation",
        "required_fields": ["proof object", "caption", "interpretation", "caveat"],
    },
    "dashboard": {
        "archetype_id_suffix": "dashboard-state-board",
        "object_pattern": "multi-metric state board with primary signal, context, and owner/implication",
        "required_fields": ["primary metric", "supporting metric", "state threshold", "owner or implication"],
    },
    "decision": {
        "archetype_id_suffix": "decision-record",
        "object_pattern": "actionable decision record with trigger, owner, timing, and caveat",
        "required_fields": ["action", "evidence trigger", "owner", "timing or caveat"],
    },
}

LAYOUT_PLAYBOOK_OVERRIDES: dict[str, dict[str, Any]] = {
    "executive-clinical": {
        "preferred_variants": ["title", "chart", "lab-run-results", "comparison-2col", "image-sidebar", "table", "standard"],
        "gallery_showcase_variants": ["chart", "lab-run-results", "comparison-2col", "table"],
        "treatment_variant_map": {
            "dashboard": ["lab-run-results", "stats"],
            "figure": ["image-sidebar", "scientific-figure"],
            "decision": ["table", "standard"],
            "references": ["table"],
        },
        "content_rules": [
            "Lead evidence pages with chart or protocol table before narrative synthesis.",
            "Keep clinical implication, caveat, and decision owner visible on the same slide.",
            "Use compact source IDs and n/r/context labels instead of long prose footers.",
        ],
        "avoid_variants": ["cards-3", "kpi-hero", "generated-image"],
    },
    "bold-startup-narrative": {
        "preferred_variants": ["title", "comparison-2col", "stats", "kpi-hero", "chart", "timeline", "image-sidebar", "table"],
        "gallery_showcase_variants": ["kpi-hero", "split", "cards-3", "timeline"],
        "treatment_variant_map": {
            "dashboard": ["kpi-hero", "stats"],
            "figure": ["image-sidebar"],
            "comparison": ["split", "comparison-2col"],
            "decision": ["table", "standard"],
            "references": ["standard", "table"],
        },
        "content_rules": [
            "Open with the market or behavior shift, then prove it with one strong metric or chart.",
            "Use timelines only for earned launch or funding gates, not default section filler.",
            "Keep source burden light on pitch pages and push full citations to appendix/reference slides.",
        ],
        "avoid_variants": ["lab-run-results", "scientific-figure", "matrix"],
    },
    "data-heavy-boardroom": {
        "preferred_variants": ["title", "stats", "chart", "table", "matrix", "comparison-2col", "standard"],
        "gallery_showcase_variants": ["stats", "chart", "matrix", "table"],
        "treatment_variant_map": {
            "dashboard": ["chart", "stats", "table"],
            "comparison": ["matrix", "comparison-2col"],
            "decision": ["table"],
            "references": ["table"],
        },
        "content_rules": [
            "Pair charts with variance or owner tables rather than standalone visuals.",
            "Make the bottom or right readout state the decision trigger.",
            "Use source-line footers for period, data cut, and version labels.",
        ],
        "avoid_variants": ["generated-image", "cards-3", "kpi-hero"],
    },
    "sunset-investor": {
        "preferred_variants": ["title", "chart", "table", "comparison-2col", "timeline", "kpi-hero", "stats", "standard"],
        "gallery_showcase_variants": ["chart", "table", "kpi-hero", "timeline"],
        "treatment_variant_map": {
            "dashboard": ["kpi-hero", "stats", "table"],
            "table": ["table"],
            "decision": ["standard", "table"],
            "references": ["standard", "table"],
        },
        "content_rules": [
            "Use warm thesis pages, then bind the claim to unit economics or market-timing proof.",
            "Keep sensitivity, payback, and milestone fields editable in tables.",
            "Separate upside narrative from downside caveat on the same decision slide.",
        ],
        "avoid_variants": ["lab-run-results", "scientific-figure", "cards-3"],
    },
    "forest-research": {
        "preferred_variants": ["title", "scientific-figure", "image-sidebar", "chart", "matrix", "table", "standard"],
        "gallery_showcase_variants": ["scientific-figure", "matrix", "chart", "table"],
        "treatment_variant_map": {
            "figure": ["scientific-figure", "image-sidebar"],
            "comparison": ["matrix", "comparison-2col"],
            "dashboard": ["chart", "stats"],
            "references": ["table"],
        },
        "content_rules": [
            "Start evidence sections with field/map/plot anchors before policy prose.",
            "Use plain-language interpretation below charts and uncertainty in tables.",
            "Make management or policy levers explicit in matrix and decision slides.",
        ],
        "avoid_variants": ["kpi-hero", "cards-3", "generated-image"],
    },
    "midnight-neon": {
        "preferred_variants": ["title", "stats", "comparison-2col", "chart", "flow", "table", "standard"],
        "gallery_showcase_variants": ["stats", "flow", "comparison-2col", "chart"],
        "treatment_variant_map": {
            "figure": ["flow", "image-sidebar"],
            "dashboard": ["flow", "stats"],
            "decision": ["standard", "table"],
            "references": ["matrix", "table"],
        },
        "content_rules": [
            "Reserve neon for active state, alert severity, threshold, or route highlights.",
            "Use console-like dashboards and flow diagrams for technical state instead of card walls.",
            "Keep dark captions and refs short enough to remain readable.",
        ],
        "avoid_variants": ["cards-3", "lab-run-results", "generated-image"],
    },
    "paper-journal": {
        "preferred_variants": ["title", "table", "scientific-figure", "chart", "comparison-2col", "standard"],
        "gallery_showcase_variants": ["table", "scientific-figure", "chart", "comparison-2col"],
        "treatment_variant_map": {
            "dashboard": ["table", "stats"],
            "figure": ["scientific-figure"],
            "references": ["matrix", "table"],
        },
        "content_rules": [
            "Use methods/results/caveat rhythm before synthesis.",
            "Let captions and panel labels carry the evidence hierarchy.",
            "Prefer restrained rules and academic references over heavy fills.",
        ],
        "avoid_variants": ["kpi-hero", "cards-3", "generated-image"],
    },
    "arctic-minimal": {
        "preferred_variants": ["title", "image-sidebar", "stats", "chart", "comparison-2col", "standard", "table"],
        "gallery_showcase_variants": ["image-sidebar", "chart", "comparison-2col", "table", "stats"],
        "treatment_variant_map": {
            "dashboard": ["stats", "chart"],
            "figure": ["image-sidebar"],
            "decision": ["standard"],
            "references": ["standard", "table"],
        },
        "content_rules": [
            "Choose one anchor per slide and leave deliberate whitespace around it.",
            "Use minimal charts and small decision lines rather than dense dashboards.",
            "Keep labels precise and avoid simultaneous accent systems.",
        ],
        "avoid_variants": ["cards-3", "kpi-hero", "lab-run-results"],
    },
    "charcoal-safety": {
        "preferred_variants": ["title", "timeline", "stats", "table", "comparison-2col", "matrix", "standard"],
        "gallery_showcase_variants": ["timeline", "matrix", "table", "stats"],
        "treatment_variant_map": {
            "dashboard": ["matrix", "stats"],
            "comparison": ["comparison-2col", "matrix"],
            "decision": ["table"],
            "references": ["matrix", "table"],
        },
        "content_rules": [
            "Use severity, exposure, and owner as first-class fields.",
            "Render incident sequence as bands or concise timelines only when chronology matters.",
            "Use red/amber as semantic state, never as decoration.",
        ],
        "avoid_variants": ["generated-image", "cards-3", "scientific-figure"],
    },
    "lavender-ops": {
        "preferred_variants": ["title", "flow", "chart", "table", "comparison-2col", "timeline", "stats", "image-sidebar"],
        "gallery_showcase_variants": ["flow", "chart", "table", "matrix"],
        "treatment_variant_map": {
            "dashboard": ["table", "stats"],
            "table": ["table"],
            "figure": ["flow", "image-sidebar"],
            "comparison": ["matrix", "comparison-2col"],
            "references": ["standard", "table"],
        },
        "content_rules": [
            "Reuse workflow lane labels as recurring slide eyebrows or table group labels.",
            "Show SLA/backlog/throughput before explaining process changes.",
            "End operating pages with owner, trigger, and next touch.",
        ],
        "avoid_variants": ["kpi-hero", "generated-image", "cards-3"],
    },
    "warm-terracotta": {
        "preferred_variants": ["title", "timeline", "image-sidebar", "cards-2", "matrix", "chart", "table", "comparison-2col", "standard"],
        "gallery_showcase_variants": ["timeline", "image-sidebar", "matrix", "chart"],
        "treatment_variant_map": {
            "figure": ["image-sidebar"],
            "comparison": ["matrix", "split", "comparison-2col"],
            "dashboard": ["chart", "stats"],
            "decision": ["table", "standard"],
            "references": ["split", "table"],
        },
        "content_rules": [
            "Anchor case-study pages with a place, object, service moment, or human evidence cue.",
            "Use journey or moment sequencing before charts when the prompt is a service/case narrative.",
            "Use friction/intervention tables for service design claims.",
            "Keep the warm palette balanced with neutral structure and concise captions.",
        ],
        "avoid_variants": ["kpi-hero", "lab-run-results", "cards-3"],
    },
    "lab-report": {
        "preferred_variants": ["title", "lab-run-results", "scientific-figure", "comparison-2col", "chart", "table"],
        "gallery_showcase_variants": ["lab-run-results", "scientific-figure", "comparison-2col", "chart"],
        "treatment_variant_map": {
            "dashboard": ["lab-run-results", "stats"],
            "table": ["lab-run-results", "table"],
            "figure": ["scientific-figure", "image-sidebar"],
            "references": ["table"],
        },
        "content_rules": [
            "Put run/sample/method metadata into structured table or caption fields.",
            "Prefer lab-run-results and scientific-figure before generic prose.",
            "Use compact footer source IDs plus final editable references when source-heavy.",
        ],
        "avoid_variants": ["cards-3", "kpi-hero", "generated-image"],
    },
    "editorial-minimal": {
        "preferred_variants": ["title", "image-sidebar", "chart", "split", "standard", "table"],
        "gallery_showcase_variants": ["image-sidebar", "split", "chart", "table"],
        "treatment_variant_map": {
            "comparison": ["split", "comparison-2col"],
            "figure": ["image-sidebar"],
            "dashboard": ["split", "chart", "stats"],
            "decision": ["standard"],
            "references": ["standard", "table"],
        },
        "content_rules": [
            "Use typographic hierarchy and one anchor at a time.",
            "Prefer image-sidebar, sparse chart, or structured prose split over dense grids.",
            "Use short source slides or standard footers; do not crowd refs.",
        ],
        "avoid_variants": ["kpi-hero", "lab-run-results", "cards-3"],
    },
}

STRUCTURAL_MOTIF_LIBRARY: dict[str, dict[str, Any]] = {
    "executive-clinical": {
        "background_structure": "light evidence brief with a recurring left evidence rail and implication sidecar",
        "layout_motifs": ["clinical status rail", "chart plus implication sidebar", "protocol gate table", "confidence/action strip"],
        "content_object_rules": [
            "put clinical implication, caveat, and owner beside the evidence object",
            "surface n/r/source context as compact chips or source-line footer fields",
            "use semantic fills only for status, confidence, or review state",
        ],
    },
    "bold-startup-narrative": {
        "background_structure": "high-contrast narrative stage with asymmetric proof blocks and poster-scale openers",
        "layout_motifs": ["poster claim", "proof chip cluster", "hero metric stage", "before-after unlock", "ask table"],
        "content_object_rules": [
            "one commercial proof point should own each pitch slide",
            "use comparisons to show behavior change rather than symmetric bullet lists",
            "move long source burden to appendix or references slides",
        ],
    },
    "data-heavy-boardroom": {
        "background_structure": "dense operating report with KPI strip, chart/table pair, and bottom decision band",
        "layout_motifs": ["variance band", "facts-right chart", "exception ledger", "owner decision table"],
        "content_object_rules": [
            "pair metrics with variance, source cut, and accountable owner",
            "use exception rows instead of decorative metric cards when decisions depend on details",
            "keep bottom readout bands concise enough for repeated board-review scanning",
        ],
    },
    "sunset-investor": {
        "background_structure": "warm thesis memo with market window, unit-economics proof, and capital decision strip",
        "layout_motifs": ["thesis window", "unit economics table", "sensitivity note", "milestone capital gate"],
        "content_object_rules": [
            "bind every narrative claim to unit proof, sensitivity, or milestone evidence",
            "separate upside and downside notes on the same slide",
            "keep warm color as structure, not a full-slide gradient blanket",
        ],
    },
    "forest-research": {
        "background_structure": "field atlas plate with figure-first evidence, observation sidebar, and policy consequence",
        "layout_motifs": ["atlas opener", "field observation sidecar", "plain-language interpretation strip", "policy tradeoff matrix"],
        "content_object_rules": [
            "lead with map, plot, figure, or field image before policy prose",
            "state uncertainty and management lever near the evidence object",
            "use matrices only for tradeoffs with comparable benefit/cost/uncertainty fields",
        ],
    },
    "midnight-neon": {
        "background_structure": "dark command console with signal panes, threshold charts, and active-route highlights",
        "layout_motifs": ["command status header", "threshold readout", "active route rail", "escalation bar"],
        "content_object_rules": [
            "reserve neon for thresholds, severity, active state, or route selection",
            "use dark tables only when labels and status chips remain high contrast",
            "make next action and owner visible on every incident or console slide",
        ],
    },
    "paper-journal": {
        "background_structure": "paper-like masthead with methods/result/caveat rhythm and caption-led figures",
        "layout_motifs": ["journal masthead", "methods ledger", "figure caption stack", "discussion limitation row"],
        "content_object_rules": [
            "let captions carry evidence context before interpretation",
            "use restrained rules and academic reference posture instead of heavy fills",
            "keep methods, result, caveat, and next experiment as visible slots",
        ],
    },
    "arctic-minimal": {
        "background_structure": "cool one-anchor technical brief with large whitespace and small decision line",
        "layout_motifs": ["single anchor field", "micro label stack", "sparse comparison divider", "bottom decision line"],
        "content_object_rules": [
            "select one visual or argument anchor per slide",
            "use tiny qualifiers and owner/date lines instead of heavy callout boxes",
            "avoid dense dashboards unless the prompt explicitly needs multiple live metrics",
        ],
    },
    "charcoal-safety": {
        "background_structure": "risk control-room report with severity rail, incident bands, and remediation ownership",
        "layout_motifs": ["severity rail", "incident sequence bands", "control gap table", "remediation due-date log"],
        "content_object_rules": [
            "treat red/amber/green as semantic state only",
            "show chronology as bands only when sequence changes the remediation decision",
            "every finding needs exposure, owner, blocker, and due date",
        ],
    },
    "lavender-ops": {
        "background_structure": "operations workbench with workflow lanes, queue/SLA readout, and next-touch table",
        "layout_motifs": ["workflow lane eyebrow", "queue facts rail", "worklist table", "cadence/trigger grid"],
        "content_object_rules": [
            "reuse workflow lane labels across section eyebrows, charts, and tables",
            "show SLA, backlog, throughput, and blocker before process explanation",
            "end operating pages with owner, trigger, and next touch",
        ],
    },
    "warm-terracotta": {
        "background_structure": "human-centered case brief with service moment sequence, artifact sidebar, and practical pilot decision",
        "layout_motifs": ["case context opener", "service journey strip", "artifact/photo sidecar", "friction-intervention table"],
        "content_object_rules": [
            "anchor each page in a place, object, moment, or beneficiary signal",
            "sequence service moments before metric explanation when the prompt is experiential",
            "keep the warm palette paired with neutral structure and concise captions",
        ],
    },
    "lab-report": {
        "background_structure": "source-first lab report with run metadata plate, table/figure evidence, and traceable refs",
        "layout_motifs": ["top-bottom lab rules", "plain no-rule evidence page", "run metadata plate", "semantic result table", "refs footer"],
        "content_object_rules": [
            "bind sample/run/method metadata to structured title, caption, or table fields",
            "prefer lab-run-results and scientific-figure variants before generic prose",
            "use compact footer source IDs plus editable references tables for dense source material",
        ],
    },
    "editorial-minimal": {
        "background_structure": "spare editorial brief with masthead, one argument per page, and caption-like evidence notes",
        "layout_motifs": ["typographic masthead", "single argument field", "image/sidebar caption", "quiet recommendation close"],
        "content_object_rules": [
            "make each slide answer one civic/editorial question",
            "use one image, chart, quote, or table anchor at a time",
            "avoid dashboard walls; use sparse facts only when they sharpen the argument",
        ],
    },
}

STYLE_METRIC_PROFILES: dict[str, dict[str, Any]] = {
    "executive-clinical": {
        "density_level": "medium-high evidence brief",
        "whitespace_ratio_target": 0.24,
        "body_words_per_content_slide": [34, 58],
        "max_primary_objects": 3,
        "visual_hierarchy": "chart or protocol table first, implication rail second, caveat/source always visible",
        "evidence_object_mix": {"chart": 0.34, "table": 0.28, "figure": 0.24, "prose": 0.14},
        "source_burden": "high; compact source IDs on evidence slides plus editable references when needed",
        "footer_posture": "source-line with report, cohort, n/r, or data-cut cues",
        "artifact_bias": ["editable clinical chart", "protocol/status table", "figure with implication rail"],
        "readability_bias": ["body 12-15 pt", "caption 7.5-9 pt", "avoid patient-detail prose blocks"],
    },
    "bold-startup-narrative": {
        "density_level": "low-medium pitch narrative",
        "whitespace_ratio_target": 0.33,
        "body_words_per_content_slide": [18, 38],
        "max_primary_objects": 2,
        "visual_hierarchy": "one commercial proof point dominates; supporting proof chips stay secondary",
        "evidence_object_mix": {"chart": 0.30, "table": 0.14, "figure": 0.20, "prose": 0.36},
        "source_burden": "light; proof notes in footer or appendix, not on hero slides",
        "footer_posture": "standard footer with short credibility IDs",
        "artifact_bias": ["hero metric", "growth chart", "before-after comparison"],
        "readability_bias": ["large claim type", "short body copy", "no dense source footers on pitch pages"],
    },
    "data-heavy-boardroom": {
        "density_level": "high operating report",
        "whitespace_ratio_target": 0.18,
        "body_words_per_content_slide": [42, 72],
        "max_primary_objects": 4,
        "visual_hierarchy": "KPI strip, chart/table pair, and owner/action row form one scan path",
        "evidence_object_mix": {"chart": 0.36, "table": 0.36, "figure": 0.08, "prose": 0.20},
        "source_burden": "high; every metric needs period, cut, version, and owner",
        "footer_posture": "source-line with period and data-cut labels",
        "artifact_bias": ["editable chart", "exception ledger", "owner decision table"],
        "readability_bias": ["compact but readable table cells", "split dashboards before shrinking below floor"],
    },
    "sunset-investor": {
        "density_level": "medium investor memo",
        "whitespace_ratio_target": 0.27,
        "body_words_per_content_slide": [26, 48],
        "max_primary_objects": 3,
        "visual_hierarchy": "market thesis first, unit proof second, downside caveat in the same frame",
        "evidence_object_mix": {"chart": 0.32, "table": 0.30, "figure": 0.10, "prose": 0.28},
        "source_burden": "medium; market and unit-economics claims get appendix/source rows",
        "footer_posture": "standard footer with sparse market-source cues",
        "artifact_bias": ["unit-economics table", "payback chart", "milestone timeline"],
        "readability_bias": ["keep sensitivity rows editable", "avoid oversized decorative charts without caveat"],
    },
    "forest-research": {
        "density_level": "medium field-policy brief",
        "whitespace_ratio_target": 0.29,
        "body_words_per_content_slide": [28, 54],
        "max_primary_objects": 3,
        "visual_hierarchy": "field figure or map owns the page; interpretation and uncertainty sit adjacent",
        "evidence_object_mix": {"chart": 0.26, "table": 0.20, "figure": 0.38, "prose": 0.16},
        "source_burden": "medium-high; dataset/method IDs stay near field evidence",
        "footer_posture": "source-line for datasets, methods, and access dates",
        "artifact_bias": ["map or field figure", "uncertainty table", "policy tradeoff matrix"],
        "readability_bias": ["plain-language interpretation", "visible uncertainty", "do not bury policy lever in notes"],
    },
    "midnight-neon": {
        "density_level": "medium technical console",
        "whitespace_ratio_target": 0.22,
        "body_words_per_content_slide": [24, 46],
        "max_primary_objects": 3,
        "visual_hierarchy": "active state, threshold, route, and owner are the dominant readout path",
        "evidence_object_mix": {"chart": 0.30, "table": 0.22, "figure": 0.30, "prose": 0.18},
        "source_burden": "medium; log/run/config IDs must remain readable on dark slides",
        "footer_posture": "dark source-line or compact provenance matrix",
        "artifact_bias": ["threshold chart", "system flow", "route/status table"],
        "readability_bias": ["high contrast captions", "neon only for state", "avoid small low-contrast refs"],
    },
    "paper-journal": {
        "density_level": "high academic note",
        "whitespace_ratio_target": 0.20,
        "body_words_per_content_slide": [38, 66],
        "max_primary_objects": 4,
        "visual_hierarchy": "method, result, caveat, and caption form the evidence order",
        "evidence_object_mix": {"chart": 0.22, "table": 0.32, "figure": 0.34, "prose": 0.12},
        "source_burden": "high; citations, method IDs, and caveats are part of the visible structure",
        "footer_posture": "captions plus final bibliography-style table",
        "artifact_bias": ["journal figure grid", "methods ledger", "references matrix"],
        "readability_bias": ["caption-led evidence", "restrained rules", "split overly dense methods tables"],
    },
    "arctic-minimal": {
        "density_level": "low sparse technical brief",
        "whitespace_ratio_target": 0.46,
        "body_words_per_content_slide": [14, 30],
        "max_primary_objects": 1,
        "visual_hierarchy": "single anchor, micro label stack, and one decision line",
        "evidence_object_mix": {"chart": 0.24, "table": 0.14, "figure": 0.28, "prose": 0.34},
        "source_burden": "low; cite only what is needed for the anchor decision",
        "footer_posture": "standard minimal source note or compact source slide",
        "artifact_bias": ["single figure", "minimal chart", "short decision line"],
        "readability_bias": ["large whitespace", "few labels", "no dashboard crowding"],
    },
    "charcoal-safety": {
        "density_level": "medium-high risk memo",
        "whitespace_ratio_target": 0.21,
        "body_words_per_content_slide": [34, 60],
        "max_primary_objects": 4,
        "visual_hierarchy": "severity, exposure, control gap, owner, and due date are first-class fields",
        "evidence_object_mix": {"chart": 0.22, "table": 0.34, "figure": 0.18, "prose": 0.26},
        "source_burden": "high; ticket/audit/report IDs need traceability",
        "footer_posture": "source-line with audit ticket and owner fields",
        "artifact_bias": ["incident timeline", "control gap table", "threshold chart"],
        "readability_bias": ["semantic red/amber only", "owner due-date rows", "avoid decorative severity color"],
    },
    "lavender-ops": {
        "density_level": "medium operations workbench",
        "whitespace_ratio_target": 0.25,
        "body_words_per_content_slide": [30, 54],
        "max_primary_objects": 3,
        "visual_hierarchy": "workflow lane, queue metric, blocker, and next touch create the scan path",
        "evidence_object_mix": {"chart": 0.28, "table": 0.32, "figure": 0.22, "prose": 0.18},
        "source_burden": "medium; metric source and period should travel with workbench pages",
        "footer_posture": "standard footer unless a metric page needs source detail",
        "artifact_bias": ["workflow flow", "worklist table", "SLA chart"],
        "readability_bias": ["reuse lane labels", "keep operating rows phrase-length", "avoid generic card walls"],
    },
    "warm-terracotta": {
        "density_level": "medium human-centered case brief",
        "whitespace_ratio_target": 0.31,
        "body_words_per_content_slide": [24, 46],
        "max_primary_objects": 2,
        "visual_hierarchy": "place or service moment first, friction/intervention evidence second, decision last",
        "evidence_object_mix": {"chart": 0.18, "table": 0.24, "figure": 0.34, "prose": 0.24},
        "source_burden": "medium-light; survey/interview notes can move to a source table",
        "footer_posture": "standard footer plus light source/interview table",
        "artifact_bias": ["case journey", "artifact sidecar", "friction-intervention table"],
        "readability_bias": ["warm palette with neutral structure", "concise captions", "avoid ornamental cards"],
    },
    "lab-report": {
        "density_level": "high clean lab report",
        "whitespace_ratio_target": 0.19,
        "body_words_per_content_slide": [36, 62],
        "max_primary_objects": 4,
        "visual_hierarchy": "run metadata, result table, figure panel, and refs stay traceable",
        "evidence_object_mix": {"chart": 0.22, "table": 0.34, "figure": 0.36, "prose": 0.08},
        "source_burden": "very high; method, run, sample, source IDs, and refs must remain auditable",
        "footer_posture": "source-line with bottom rule, refs text, and page number",
        "artifact_bias": ["lab-run-results table", "scientific figure", "editable references table"],
        "readability_bias": ["body 12-14 pt", "caption 7.5-9 pt", "split dense assay pages before shrinking text"],
    },
    "editorial-minimal": {
        "density_level": "low spare editorial brief",
        "whitespace_ratio_target": 0.42,
        "body_words_per_content_slide": [16, 34],
        "max_primary_objects": 1,
        "visual_hierarchy": "one argument, one visual or fact anchor, and a caption-like source note",
        "evidence_object_mix": {"chart": 0.20, "table": 0.10, "figure": 0.32, "prose": 0.38},
        "source_burden": "low-medium; source notes should be short and editorial, not report-like",
        "footer_posture": "standard footer or sparse source note slide",
        "artifact_bias": ["image-sidebar", "sparse chart", "essay-style split"],
        "readability_bias": ["typographic hierarchy", "single anchor per slide", "avoid KPI tile walls"],
    },
}

EXAMPLE_STORYBOARDS: dict[str, dict[str, Any]] = {
    "executive-clinical": {
        "topic": "Same-day oncology triage pathway",
        "title": "Oncology Triage Pathway Readout",
        "subtitle": "Synthetic executive evidence brief: referrals, review time, consult capacity, and escalation owner.",
        "chart": {
            "title": "Pathway readiness by step",
            "labels": ["Referral", "Triage", "Consult", "Escalate"],
            "values": [42, 68, 61, 79],
            "note": "Clinical pathway chart pairs the outcome with an implication sidebar.",
        },
        "dashboard_facts": [
            {"value": "79%", "label": "Escalation ready", "detail": "owner named"},
            {"value": "18h", "label": "Median review", "detail": "same-day target"},
        ],
        "kpi": {"value": "18h", "label": "median review", "context": "Target: same-day triage before oncology consult."},
        "table": {
            "headers": ["Cohort", "Signal", "Action"],
            "rows": [
                ["New referrals", "+14%", "Add nurse review"],
                ["High-risk flags", "9 cases", "Route to attending"],
                ["Consult slots", "6 open", "Hold reserve"],
                ["Escalations", "2 pending", "Owner named"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Protocol gate", "body": ["Eligibility and urgency are separated.", "Caveat stays beside evidence."]},
                {"title": "Clinical readout", "body": ["Action, owner, and next data cut remain visible."]},
            ],
            "caption": "Synthetic pathway figure; no patient data.",
            "interpretation": "Escalation capacity is the binding constraint, not referral volume.",
        },
        "comparison": {
            "left_title": "Current pathway",
            "left_body": ["Manual review queue", "Late owner assignment"],
            "right_title": "Reference structure",
            "right_body": ["Status rail first", "Decision table closes"],
            "verdict": "Surface owner and caveat on the evidence slide.",
        },
        "decision": {
            "headers": ["Decision", "Evidence", "Owner"],
            "rows": [
                ["Add reserve slots", "6 open slots", "Clinic lead"],
                ["Review high-risk flags", "9 cases", "Attending"],
                ["Publish next cut", "Friday", "Analytics"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "Referral", "body": "Capture urgency"},
            {"label": "02", "title": "Review", "body": "Same-day triage"},
            {"label": "03", "title": "Consult", "body": "Reserve slot"},
            {"label": "04", "title": "Escalate", "body": "Owner named"},
        ],
        "quadrants": [
            {"title": "High urgency", "body": "Route to attending."},
            {"title": "High capacity", "body": "Hold consult slots."},
            {"title": "Low certainty", "body": "Flag caveat visibly."},
            {"title": "Low burden", "body": "Track owner only."},
        ],
        "source_notes": ["Synthetic pathway registry", "No patient-level data"],
    },
    "bold-startup-narrative": {
        "topic": "Micro-fulfillment launch memo",
        "title": "Launch Wedge: Neighborhood Fulfillment",
        "subtitle": "Synthetic pitch narrative: behavior shift, early demand, launch proof, and next milestone.",
        "chart": {
            "title": "Weekly pilot order growth",
            "labels": ["W1", "W2", "W3", "W4"],
            "values": [18, 31, 57, 86],
            "note": "Pitch chart highlights the inflection and keeps the source burden light.",
        },
        "dashboard_facts": [
            {"value": "86", "label": "Week 4 orders", "detail": "pilot route"},
            {"value": "42%", "label": "Repeat rate", "detail": "early cohort"},
        ],
        "kpi": {"value": "42%", "label": "repeat rate", "context": "One hero metric earns the slide before detail."},
        "table": {
            "headers": ["Segment", "Signal", "Move"],
            "rows": [
                ["Campus", "Fast repeat", "Extend evening slots"],
                ["Apartments", "High basket", "Bundle route"],
                ["Small offices", "Low churn", "Add invoicing"],
                ["Retail pickup", "Mixed", "Keep as test"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Behavior shift", "body": ["Errand replaced by scheduled pickup.", "Proof chip stays visible."]},
                {"title": "Market unlock", "body": ["Repeat cohort supports expansion ask."]},
            ],
            "caption": "Synthetic launch figure generated locally.",
            "interpretation": "The wedge is repeat behavior, not raw awareness.",
        },
        "comparison": {
            "left_title": "Before",
            "left_body": ["One-off errands", "No route density"],
            "right_title": "After",
            "right_body": ["Scheduled pickups", "Repeat route demand"],
            "verdict": "Launch message should prove the behavior switch.",
        },
        "decision": {
            "headers": ["Ask", "Proof", "Milestone"],
            "rows": [
                ["Fund route 2", "42% repeat", "100 orders/week"],
                ["Hire ops lead", "86 orders", "2-zone launch"],
                ["Keep credit line", "Basket growth", "Margin check"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "Pilot", "body": "One route"},
            {"label": "02", "title": "Repeat", "body": "Cohort proof"},
            {"label": "03", "title": "Expand", "body": "Second zone"},
            {"label": "04", "title": "Raise", "body": "Milestone ask"},
        ],
        "quadrants": [
            {"title": "High demand", "body": "Fund route expansion."},
            {"title": "High proof", "body": "Show repeat cohort."},
            {"title": "Low margin", "body": "Hold pricing test."},
            {"title": "Low effort", "body": "Bundle pickups."},
        ],
        "source_notes": ["Synthetic pilot ledger", "Generic commercial data"],
    },
    "data-heavy-boardroom": {
        "topic": "Q3 retention operations review",
        "title": "Q3 Retention Operating Review",
        "subtitle": "Synthetic boardroom deck: renewal rate, backlog, variance drivers, and owner table.",
        "chart": {
            "title": "Renewal rate vs operating target",
            "labels": ["Apr", "May", "Jun", "Jul"],
            "values": [74, 78, 76, 83],
            "note": "Board charts carry the variance readout and data-cut footer.",
        },
        "dashboard_facts": [
            {"value": "83%", "label": "Renewal", "detail": "+5 vs May"},
            {"value": "17", "label": "At-risk accounts", "detail": "owner assigned"},
        ],
        "kpi": {"value": "83%", "label": "renewal rate", "context": "Board readout needs target, variance, and owner."},
        "table": {
            "headers": ["Driver", "Variance", "Owner"],
            "rows": [
                ["Enterprise saves", "+4 pts", "CS lead"],
                ["SMB backlog", "-2 pts", "Ops"],
                ["Late contracts", "-1 pt", "Legal"],
                ["Upgrade pull", "+3 pts", "Product"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Operating readout", "body": ["Chart and exception table stay paired.", "Decision trigger sits below."]},
                {"title": "Replay", "body": ["Data cut and version remain in footer."]},
            ],
            "caption": "Synthetic operating figure; no customer data.",
            "interpretation": "Enterprise saves offset backlog, but legal owner remains the risk.",
        },
        "comparison": {
            "left_title": "Plan",
            "left_body": ["Renewals by week 2", "Legal SLA under 3 days"],
            "right_title": "Actual",
            "right_body": ["Renewals drifted late", "Legal queue created drag"],
            "verdict": "Variance belongs beside the metric, not in speaker notes.",
        },
        "decision": {
            "headers": ["Trigger", "Action", "Owner"],
            "rows": [
                ["<80% renewal", "Open save desk", "CS lead"],
                [">10 late contracts", "Daily legal queue", "Legal"],
                ["Backlog >20", "Ops review", "COO"],
            ],
        },
        "timeline": [
            {"label": "Apr", "title": "Baseline", "body": "74% renewal"},
            {"label": "May", "title": "Lift", "body": "78% renewal"},
            {"label": "Jun", "title": "Drag", "body": "Legal delay"},
            {"label": "Jul", "title": "Recover", "body": "83% renewal"},
        ],
        "quadrants": [
            {"title": "High impact", "body": "Enterprise saves."},
            {"title": "High control", "body": "Legal queue."},
            {"title": "Low certainty", "body": "Upgrade pull."},
            {"title": "Low effort", "body": "Owner table."},
        ],
        "source_notes": ["Synthetic Q3 operating ledger", "Data cut v0"],
    },
    "sunset-investor": {
        "topic": "Community solar unit economics memo",
        "title": "Community Solar Unit Economics",
        "subtitle": "Synthetic investor memo: CAC, payback, margin sensitivity, and milestone use of funds.",
        "chart": {
            "title": "Payback months by cohort",
            "labels": ["Pilot", "Referral", "Partner", "Scaled"],
            "values": [19, 15, 13, 11],
            "note": "Investor chart frames sensitivity before the ask.",
        },
        "dashboard_facts": [
            {"value": "13mo", "label": "Partner payback", "detail": "base case"},
            {"value": "31%", "label": "Gross margin", "detail": "synthetic"},
        ],
        "kpi": {"value": "13mo", "label": "partner payback", "context": "Warm memo page binds thesis to unit proof."},
        "table": {
            "headers": ["Line", "Base", "Watch"],
            "rows": [
                ["CAC", "$420", "Partner mix"],
                ["Payback", "13mo", "Install delay"],
                ["Gross margin", "31%", "Hardware cost"],
                ["Use of funds", "$1.2m", "Sales pods"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Thesis", "body": ["Partner channel lowers CAC.", "Downside caveat remains visible."]},
                {"title": "Capital use", "body": ["Sales pods unlock next milestone."]},
            ],
            "caption": "Synthetic investor figure; not market data.",
            "interpretation": "The financing case depends on partner CAC holding below base.",
        },
        "comparison": {
            "left_title": "Direct sales",
            "left_body": ["Higher CAC", "Slower payback"],
            "right_title": "Partner channel",
            "right_body": ["Lower CAC", "Faster payback"],
            "verdict": "Decision slide must separate upside from sensitivity.",
        },
        "decision": {
            "headers": ["Decision", "Proof", "Caveat"],
            "rows": [
                ["Fund sales pods", "13mo payback", "CAC drift"],
                ["Hold hardware reserve", "31% margin", "cost spike"],
                ["Gate expansion", "2 partner LOIs", "install delay"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "LOI", "body": "Partner proof"},
            {"label": "02", "title": "Pod", "body": "Sales launch"},
            {"label": "03", "title": "Install", "body": "Cost check"},
            {"label": "04", "title": "Scale", "body": "Payback gate"},
        ],
        "quadrants": [
            {"title": "High upside", "body": "Partner channel."},
            {"title": "High risk", "body": "Hardware cost."},
            {"title": "Low burden", "body": "LOI gate."},
            {"title": "Low proof", "body": "Direct-only path."},
        ],
        "source_notes": ["Synthetic unit-economics model", "No market-source claims"],
    },
    "forest-research": {
        "topic": "Urban canopy heat mitigation brief",
        "title": "Canopy Heat Mitigation Field Brief",
        "subtitle": "Synthetic field-science policy deck: plot evidence, site table, uncertainty, and management lever.",
        "chart": {
            "title": "Median surface temperature by site",
            "labels": ["Bare", "Young", "Mixed", "Mature"],
            "values": [41, 36, 33, 30],
            "note": "Field chart uses plain-language interpretation and uncertainty.",
        },
        "dashboard_facts": [
            {"value": "-11C", "label": "Mature canopy", "detail": "vs bare site"},
            {"value": "4", "label": "Site classes", "detail": "synthetic plots"},
        ],
        "kpi": {"value": "-11C", "label": "temperature delta", "context": "Use as evidence only with site caveats."},
        "table": {
            "headers": ["Site", "Signal", "Uncertainty"],
            "rows": [
                ["Bare", "41C", "High exposure"],
                ["Young canopy", "36C", "Watering variable"],
                ["Mixed shade", "33C", "Moderate"],
                ["Mature canopy", "30C", "Stable"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Field plot", "body": ["Map or plot owns the slide.", "Interpretation stays under the visual."]},
                {"title": "Policy lever", "body": ["Prioritize mature-canopy corridors."]},
            ],
            "caption": "Synthetic field panels generated locally.",
            "interpretation": "Cooling signal is strongest where canopy continuity is highest.",
        },
        "comparison": {
            "left_title": "Bare corridor",
            "left_body": ["Higher exposure", "No shade continuity"],
            "right_title": "Canopy corridor",
            "right_body": ["Lower surface temp", "Maintenance burden"],
            "verdict": "Policy matrix needs both benefit and uncertainty.",
        },
        "decision": {
            "headers": ["Lever", "Benefit", "Uncertainty"],
            "rows": [
                ["Protect mature canopy", "-11C", "Low"],
                ["Water young sites", "-5C", "Medium"],
                ["Add shade structures", "-3C", "High"],
            ],
        },
        "timeline": [
            {"label": "S1", "title": "Survey", "body": "Plot class"},
            {"label": "S2", "title": "Measure", "body": "Midday temp"},
            {"label": "S3", "title": "Compare", "body": "Canopy effect"},
            {"label": "S4", "title": "Act", "body": "Policy lever"},
        ],
        "quadrants": [
            {"title": "High benefit", "body": "Mature canopy."},
            {"title": "High burden", "body": "Watering program."},
            {"title": "Low certainty", "body": "Shade structures."},
            {"title": "Low burden", "body": "Protection zoning."},
        ],
        "source_notes": ["Synthetic field survey", "No real site data"],
    },
    "midnight-neon": {
        "topic": "Model monitoring incident console",
        "title": "Model Drift Triage Console",
        "subtitle": "Synthetic technical deck: alert state, route, threshold chart, and escalation decision.",
        "chart": {
            "title": "Drift score by checkpoint",
            "labels": ["00:00", "04:00", "08:00", "12:00"],
            "values": [18, 24, 61, 73],
            "note": "Dark technical chart uses threshold and right-side readout.",
        },
        "dashboard_facts": [
            {"value": "73", "label": "Drift score", "detail": "alert zone"},
            {"value": "2", "label": "Routes", "detail": "shadow + rollback"},
        ],
        "kpi": {"value": "73", "label": "drift score", "context": "Neon marks active alert state only."},
        "table": {
            "headers": ["Route", "State", "Owner"],
            "rows": [
                ["Shadow model", "Active", "ML platform"],
                ["Rollback", "Ready", "SRE"],
                ["Feature gate", "Watch", "Data"],
                ["Customer notice", "Hold", "Support"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Active route", "body": ["Shadow path is highlighted.", "Rollback remains a decision, not decoration."]},
                {"title": "Replay", "body": ["Synthetic console figure; threshold labels stay readable."]},
            ],
            "caption": "Synthetic console diagram generated locally.",
            "interpretation": "Escalate when drift stays above threshold after shadow comparison.",
        },
        "comparison": {
            "left_title": "Raw alert",
            "left_body": ["Score spike", "No owner"],
            "right_title": "Triage console",
            "right_body": ["Route state", "Owner and trigger"],
            "verdict": "Dark pages need operational readout, not decoration.",
        },
        "decision": {
            "headers": ["Trigger", "Route", "Owner"],
            "rows": [
                [">70 drift", "Shadow compare", "ML platform"],
                [">80 drift", "Rollback", "SRE"],
                ["Customer impact", "Notify", "Support"],
            ],
        },
        "timeline": [
            {"label": "00", "title": "Baseline", "body": "18 score"},
            {"label": "04", "title": "Watch", "body": "24 score"},
            {"label": "08", "title": "Alert", "body": "61 score"},
            {"label": "12", "title": "Triage", "body": "73 score"},
        ],
        "quadrants": [
            {"title": "High severity", "body": "Rollback route."},
            {"title": "High proof", "body": "Shadow compare."},
            {"title": "Low confidence", "body": "Feature gate."},
            {"title": "Low impact", "body": "Watch only."},
        ],
        "source_notes": ["Synthetic monitoring log", "No production telemetry"],
    },
    "paper-journal": {
        "topic": "Assay concordance methods note",
        "title": "Methods Note: Assay Concordance",
        "subtitle": "Synthetic journal-style deck: method table, result figure, caveat, and editable references.",
        "chart": {
            "title": "Concordance by specimen group",
            "labels": ["Fresh", "Frozen", "Low copy", "Control"],
            "values": [96, 93, 84, 99],
            "note": "Journal chart is caption-led with result sentence below.",
        },
        "dashboard_facts": [
            {"value": "96%", "label": "Fresh concordance", "detail": "synthetic"},
            {"value": "84%", "label": "Low-copy group", "detail": "caveat"},
        ],
        "kpi": {"value": "96%", "label": "fresh concordance", "context": "KPI stays subordinate to method and caveat."},
        "table": {
            "headers": ["Group", "Method", "Caveat"],
            "rows": [
                ["Fresh", "Paired run", "High signal"],
                ["Frozen", "Matched aliquot", "Storage effect"],
                ["Low copy", "Repeat run", "Wide interval"],
                ["Control", "Panel", "Expected"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Panel hierarchy", "body": ["Methods/result/caveat order.", "Caption carries evidence context."]},
                {"title": "Discussion", "body": ["Low-copy group requires repeat validation."]},
            ],
            "caption": "Synthetic journal panels; no study data.",
            "interpretation": "Low-copy concordance drives the limitation, not the main result.",
        },
        "comparison": {
            "left_title": "Primary method",
            "left_body": ["High signal", "Short workflow"],
            "right_title": "Repeat method",
            "right_body": ["Improves low-copy confidence", "Adds burden"],
            "verdict": "Methods slide must preserve limitation beside result.",
        },
        "decision": {
            "headers": ["Finding", "Implication", "Next step"],
            "rows": [
                ["Fresh concordant", "Reportable", "Keep method"],
                ["Low-copy variable", "Caution", "Repeat validation"],
                ["Controls stable", "Accept", "Document refs"],
            ],
        },
        "timeline": [
            {"label": "M1", "title": "Collect", "body": "Specimens"},
            {"label": "M2", "title": "Run", "body": "Primary assay"},
            {"label": "M3", "title": "Repeat", "body": "Low copy"},
            {"label": "M4", "title": "Report", "body": "Caveat"},
        ],
        "quadrants": [
            {"title": "High signal", "body": "Fresh group."},
            {"title": "High burden", "body": "Repeat method."},
            {"title": "Low certainty", "body": "Low copy."},
            {"title": "Low burden", "body": "Control panel."},
        ],
        "source_notes": ["Synthetic methods ledger", "Editable references only"],
    },
    "arctic-minimal": {
        "topic": "Edge cache postmortem brief",
        "title": "Edge Cache Postmortem",
        "subtitle": "Synthetic minimal technical brief: one anchor per page, latency chart, and small decision line.",
        "chart": {
            "title": "P95 latency during recovery",
            "labels": ["T0", "T1", "T2", "T3"],
            "values": [420, 310, 190, 140],
            "note": "Minimal chart leaves space around the proof object.",
        },
        "dashboard_facts": [
            {"value": "140ms", "label": "Recovered P95", "detail": "T3"},
            {"value": "1", "label": "Primary anchor", "detail": "per slide"},
            {"value": "0", "label": "Extra frames", "detail": "proof stays quiet"},
        ],
        "kpi": {"value": "140ms", "label": "recovered P95", "context": "Use quiet proof, not a metric wall."},
        "table": {
            "headers": ["Cause", "Evidence", "Fix"],
            "rows": [
                ["TTL drift", "cache miss", "Pin config"],
                ["Warmup gap", "cold route", "Preload"],
                ["Alert lag", "late page", "Tighten SLO"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Anchor", "body": ["One diagram owns the slide.", "Notes stay concise."]},
                {"title": "Decision", "body": ["Pin config and preload route."]},
            ],
            "caption": "Synthetic edge-cache diagram.",
            "interpretation": "Recovery came from preload plus TTL pinning.",
        },
        "comparison": {
            "left_title": "Before incident",
            "left_body": ["TTL drift unobserved", "Cold route hidden"],
            "right_title": "After fix",
            "right_body": ["Pinned config", "Preload path"],
            "verdict": "Keep the postmortem sparse and exact.",
        },
        "decision": {
            "headers": ["Fix", "Proof", "Owner"],
            "rows": [
                ["Pin TTL", "Miss rate down", "Infra"],
                ["Preload route", "P95 140ms", "Edge"],
                ["Alert SLO", "Earlier page", "SRE"],
            ],
        },
        "timeline": [
            {"label": "T0", "title": "Miss", "body": "Latency spike"},
            {"label": "T1", "title": "Warm", "body": "Partial recover"},
            {"label": "T2", "title": "Pin", "body": "TTL fixed"},
            {"label": "T3", "title": "Verify", "body": "P95 stable"},
        ],
        "quadrants": [
            {"title": "High proof", "body": "Latency chart."},
            {"title": "High action", "body": "Pin TTL."},
            {"title": "Low noise", "body": "One anchor."},
            {"title": "Low burden", "body": "Preload route."},
        ],
        "source_notes": ["Synthetic incident notes", "No production logs"],
    },
    "charcoal-safety": {
        "topic": "Warehouse near-miss remediation",
        "title": "Forklift Near-Miss Control Review",
        "subtitle": "Synthetic safety deck: severity, sequence, control gap, owner, and due date.",
        "chart": {
            "title": "Open control gaps by area",
            "labels": ["Dock", "Aisle", "Charge", "Exit"],
            "values": [5, 7, 3, 2],
            "note": "Risk chart uses semantic red/amber only for state.",
        },
        "dashboard_facts": [
            {"value": "7", "label": "Aisle gaps", "detail": "highest risk"},
            {"value": "3", "label": "Owners", "detail": "named"},
        ],
        "kpi": {"value": "7", "label": "aisle gaps", "context": "Severity stays first; owner follows."},
        "table": {
            "headers": ["Control", "State", "Owner"],
            "rows": [
                ["Aisle markings", "Red", "Facilities"],
                ["Spotter rule", "Amber", "Ops"],
                ["Charge zone", "Amber", "Safety"],
                ["Exit mirror", "Green", "Facilities"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Incident path", "body": ["Sequence shown only where chronology matters.", "Hazard callout is semantic."]},
                {"title": "Control owner", "body": ["Every open item has a due date."]},
            ],
            "caption": "Synthetic incident diagram.",
            "interpretation": "Aisle marking and spotter rule are the blocking controls.",
        },
        "comparison": {
            "left_title": "Current control",
            "left_body": ["Markings faded", "Spotter inconsistent"],
            "right_title": "Required control",
            "right_body": ["High-contrast lanes", "Named spotter rule"],
            "verdict": "Use red only for state and remediation priority.",
        },
        "decision": {
            "headers": ["Action", "Blocker", "Due"],
            "rows": [
                ["Repaint aisles", "Night access", "Fri"],
                ["Reissue rule", "Supervisor signoff", "Mon"],
                ["Audit charge zone", "Checklist", "Wed"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "Approach", "body": "Blind aisle"},
            {"label": "02", "title": "Near miss", "body": "Spotter absent"},
            {"label": "03", "title": "Stop", "body": "Forklift halted"},
            {"label": "04", "title": "Remediate", "body": "Owner named"},
        ],
        "quadrants": [
            {"title": "High severity", "body": "Aisle markings."},
            {"title": "High control", "body": "Spotter rule."},
            {"title": "Low burden", "body": "Exit mirror."},
            {"title": "Low certainty", "body": "Charge zone."},
        ],
        "source_notes": ["Synthetic near-miss log", "No site identifiers"],
    },
    "lavender-ops": {
        "topic": "Support queue operating review",
        "title": "Support Queue Operating Review",
        "subtitle": "Synthetic ops workbench: SLA, backlog, owner lanes, and next-touch cadence.",
        "chart": {
            "title": "SLA attainment by week",
            "labels": ["W1", "W2", "W3", "W4"],
            "values": [71, 76, 82, 88],
            "note": "Ops chart keeps the queue readout beside the plot.",
        },
        "dashboard_facts": [
            {"value": "88%", "label": "SLA", "detail": "week 4"},
            {"value": "23", "label": "Backlog", "detail": "owner lanes"},
        ],
        "kpi": {"value": "88%", "label": "SLA attainment", "context": "Ops slides show lane, owner, and next touch."},
        "table": {
            "headers": ["Lane", "Backlog", "Next touch"],
            "rows": [
                ["Billing", "8", "Queue sweep"],
                ["Access", "5", "Automation test"],
                ["Renewal", "6", "CS owner"],
                ["Bug", "4", "Eng triage"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Workflow route", "body": ["Lane labels recur as eyebrows.", "Readout names next touch."]},
                {"title": "Operating cadence", "body": ["Triggers and owners are table fields."]},
            ],
            "caption": "Synthetic workflow route diagram.",
            "interpretation": "Billing backlog needs queue sweep before automation adds value.",
        },
        "comparison": {
            "left_title": "Manual queue",
            "left_body": ["Late owner routing", "Backlog hidden"],
            "right_title": "Workbench route",
            "right_body": ["Lane labels", "Next touch visible"],
            "verdict": "Ops presets should feel like a usable workbench.",
        },
        "decision": {
            "headers": ["Action", "Trigger", "Owner"],
            "rows": [
                ["Sweep billing", "Backlog >7", "Ops"],
                ["Test access bot", "5 tickets", "Automation"],
                ["Escalate bugs", "4 open", "Eng"],
            ],
        },
        "timeline": [
            {"label": "Mon", "title": "Sweep", "body": "Billing lane"},
            {"label": "Tue", "title": "Bot", "body": "Access test"},
            {"label": "Wed", "title": "CS", "body": "Renewals"},
            {"label": "Thu", "title": "Eng", "body": "Bug triage"},
        ],
        "quadrants": [
            {"title": "High backlog", "body": "Billing lane."},
            {"title": "High leverage", "body": "Access bot."},
            {"title": "Low burden", "body": "CS touch."},
            {"title": "Low certainty", "body": "Bug triage."},
        ],
        "source_notes": ["Synthetic queue ledger", "No customer data"],
    },
    "warm-terracotta": {
        "topic": "Museum membership renewal case",
        "title": "Museum Membership Renewal Case",
        "subtitle": "Synthetic human-centered brief: visit moment, friction table, behavior trend, and pilot recommendation.",
        "chart": {
            "title": "Renewal intent after visit moment",
            "labels": ["Entry", "Gallery", "Cafe", "Exit"],
            "values": [38, 52, 49, 63],
            "note": "Case-study chart links behavior signal to human implication.",
        },
        "dashboard_facts": [
            {"value": "63%", "label": "Exit intent", "detail": "after pilot prompt"},
            {"value": "4", "label": "Moments", "detail": "mapped"},
        ],
        "kpi": {"value": "63%", "label": "exit intent", "context": "Warm case pages connect metric to human moment."},
        "table": {
            "headers": ["Moment", "Friction", "Intervention"],
            "rows": [
                ["Entry", "Line unclear", "Member lane"],
                ["Gallery", "No prompt", "Guide cue"],
                ["Cafe", "Offer hidden", "Receipt note"],
                ["Exit", "No reminder", "Renewal card"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Human cue", "body": ["One place/object signal anchors the case.", "Caption stays practical."]},
                {"title": "Pilot frame", "body": ["Intervention is visible beside behavior."]},
            ],
            "caption": "Synthetic case artifact generated locally.",
            "interpretation": "Exit reminder is the lowest-burden renewal intervention.",
        },
        "comparison": {
            "left_title": "Current visit",
            "left_body": ["Renewal prompt hidden", "Friction appears late"],
            "right_title": "Pilot visit",
            "right_body": ["Moment-based cue", "Exit reminder card"],
            "verdict": "Warm pages need tangible service evidence, not abstract icons.",
        },
        "decision": {
            "headers": ["Pilot", "Beneficiary", "Signal"],
            "rows": [
                ["Exit card", "Members", "63% intent"],
                ["Member lane", "Families", "Shorter wait"],
                ["Cafe note", "Repeat visitors", "Offer recall"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "Entry", "body": "Lane clarity"},
            {"label": "02", "title": "Gallery", "body": "Guide cue"},
            {"label": "03", "title": "Cafe", "body": "Offer note"},
            {"label": "04", "title": "Exit", "body": "Renew card"},
        ],
        "quadrants": [
            {"title": "High empathy", "body": "Exit reminder."},
            {"title": "High effort", "body": "Member lane."},
            {"title": "Low proof", "body": "Cafe note."},
            {"title": "Low burden", "body": "Guide cue."},
        ],
        "source_notes": ["Synthetic visitor intercept", "No real patron data"],
    },
    "lab-report": {
        "topic": "RT-LAMP validation report",
        "title": "RT-LAMP Validation Run",
        "subtitle": "Synthetic lab report: sample metadata, controls, Ct-like readout, figure panels, and references.",
        "chart": {
            "title": "Signal threshold by sample group",
            "labels": ["Control", "Low", "Mid", "High"],
            "values": [12, 28, 54, 81],
            "note": "Lab chart keeps axis labels readable and source IDs compact.",
        },
        "dashboard_facts": [
            {"value": "24", "label": "Samples", "detail": "synthetic run"},
            {"value": "2", "label": "Review calls", "detail": "borderline"},
        ],
        "kpi": {"value": "24", "label": "samples", "context": "Use run metadata, not decorative lab icons."},
        "table": {
            "headers": ["Sample", "Signal", "Call"],
            "rows": [
                ["CTRL-01", "12", "Pass"],
                ["LOW-04", "28", "Review"],
                ["MID-07", "54", "Pass"],
                ["HIGH-12", "81", "Pass"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Run metadata", "body": ["Controls and borderline calls stay visible.", "Caption names synthetic run."]},
                {"title": "Interpretation", "body": ["Review calls should not hide in footer."]},
            ],
            "caption": "Synthetic assay panels generated locally.",
            "interpretation": "Two low-signal samples require review; controls pass.",
        },
        "comparison": {
            "left_title": "Raw readout",
            "left_body": ["Threshold only", "Borderline hidden"],
            "right_title": "Report-ready",
            "right_body": ["Call table", "Review rule explicit"],
            "verdict": "Lab slides should make the call rule inspectable.",
        },
        "decision": {
            "headers": ["Call", "Rule", "Action"],
            "rows": [
                ["Pass", "Signal >=50", "Report"],
                ["Review", "20-49", "Repeat"],
                ["Fail", "<20", "Reject run"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "Load", "body": "Samples"},
            {"label": "02", "title": "Run", "body": "RT-LAMP"},
            {"label": "03", "title": "Review", "body": "Borderline"},
            {"label": "04", "title": "Report", "body": "Call table"},
        ],
        "quadrants": [
            {"title": "High signal", "body": "Report pass."},
            {"title": "Borderline", "body": "Repeat sample."},
            {"title": "Control fail", "body": "Reject run."},
            {"title": "Low burden", "body": "Short refs."},
        ],
        "source_notes": ["Synthetic assay CSV", "No clinical sample data"],
    },
    "editorial-minimal": {
        "topic": "Public library evening access brief",
        "title": "Evening Access Civic Brief",
        "subtitle": "Synthetic editorial report: one civic question, sparse chart, structured contrast, and short sources.",
        "chart": {
            "title": "Visits by evening hour",
            "labels": ["5p", "6p", "7p", "8p"],
            "values": [24, 38, 46, 31],
            "note": "Editorial chart stays quiet and caption-like.",
        },
        "dashboard_facts": [
            {"value": "46", "label": "7p visits", "detail": "peak window"},
            {"value": "1", "label": "Argument", "detail": "per slide"},
            {"value": "8w", "label": "Review", "detail": "pilot checkpoint"},
        ],
        "kpi": {"value": "46", "label": "7p visits", "context": "Use sparingly; editorial rhythm favors argument over dashboard."},
        "table": {
            "headers": ["Question", "Signal", "Note"],
            "rows": [
                ["Who benefits?", "Students", "After work"],
                ["When?", "7p peak", "Short window"],
                ["Cost?", "Staffing", "Pilot first"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Civic cue", "body": ["One artifact or chart anchors the page.", "Whitespace is part of the argument."]},
                {"title": "Editorial line", "body": ["Keep source list short and visible."]},
            ],
            "caption": "Synthetic civic-access figure.",
            "interpretation": "The case is a focused evening window, not longer hours everywhere.",
        },
        "comparison": {
            "left_title": "All-day expansion",
            "left_body": ["Higher staffing", "Diffuse benefit"],
            "right_title": "Evening pilot",
            "right_body": ["Targeted window", "Measurable use"],
            "verdict": "The argument should feel spare, not under-built.",
        },
        "decision": {
            "headers": ["Recommendation", "Reason", "Constraint"],
            "rows": [
                ["Pilot 6-8p", "Peak visits", "Staffing"],
                ["Measure use", "Student access", "Privacy"],
                ["Review in 8 weeks", "Cost signal", "Budget"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "Frame", "body": "Civic question"},
            {"label": "02", "title": "Measure", "body": "Visits"},
            {"label": "03", "title": "Pilot", "body": "6-8p"},
            {"label": "04", "title": "Review", "body": "8 weeks"},
        ],
        "quadrants": [
            {"title": "High need", "body": "Students."},
            {"title": "High cost", "body": "All-day plan."},
            {"title": "Low burden", "body": "Evening pilot."},
            {"title": "Low proof", "body": "Anecdotes only."},
        ],
        "source_notes": ["Synthetic civic survey", "No patron records"],
    },
}


def _treatments(
    *,
    title: str,
    comparison: str,
    chart: str,
    table: str,
    figure: str,
    dashboard: str,
    decision: str,
    references: str,
) -> dict[str, str]:
    return {
        "title": title,
        "comparison": comparison,
        "chart": chart,
        "table": table,
        "figure": figure,
        "dashboard": dashboard,
        "decision": decision,
        "references": references,
    }


def _slides(*items: tuple[str, str, str]) -> list[dict[str, str]]:
    return [
        {
            "role": role,
            "variant": variant,
            "layout_note": note,
        }
        for role, variant, note in items
    ]


def _unique_strings(values: list[Any] | tuple[Any, ...]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _slugify(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return text.strip("-")


def _annotate_preset_archetype(
    raw: dict[str, Any],
    preset: str,
    fallback_id: str,
    *,
    treatment_key: str = "",
) -> dict[str, Any]:
    key = str(preset or "").strip()
    archetype = copy.deepcopy(raw)
    if not archetype:
        archetype = {
            "archetype_id": fallback_id,
            "structure": "generic structured treatment posture",
            "required_fields": ["scope", "evidence", "source"],
        }
    if treatment_key:
        archetype["treatment_key"] = treatment_key
    archetype["style_preset"] = key
    required_fields = archetype.get("required_fields") if isinstance(archetype.get("required_fields"), list) else []
    primary_variants = archetype.get("primary_variants") if isinstance(archetype.get("primary_variants"), list) else []
    signature_material = {
        "archetype_id": archetype.get("archetype_id"),
        "structure": archetype.get("structure"),
        "required_fields": required_fields,
        "title_layout": archetype.get("title_layout"),
        "footer_mode": archetype.get("footer_mode"),
        "object_pattern": archetype.get("object_pattern"),
        "primary_variants": primary_variants,
        "content_goal": archetype.get("content_goal"),
    }
    semantic_material = {
        "structure": signature_material.get("structure"),
        "object_pattern": signature_material.get("object_pattern"),
        "required_fields": required_fields,
        "primary_variants": primary_variants,
        "title_layout": signature_material.get("title_layout"),
        "footer_mode": signature_material.get("footer_mode"),
        "content_goal": signature_material.get("content_goal"),
    }
    archetype["archetype_signature"] = "::".join(
        [
            str(signature_material.get("archetype_id") or ""),
            str(signature_material.get("structure") or ""),
            "|".join(str(item) for item in required_fields if str(item).strip()),
            str(signature_material.get("title_layout") or ""),
            str(signature_material.get("footer_mode") or ""),
            str(signature_material.get("object_pattern") or ""),
            "|".join(str(item) for item in primary_variants if str(item).strip()),
            str(signature_material.get("content_goal") or ""),
        ]
    )
    archetype["semantic_signature"] = hashlib.sha256(
        json.dumps(semantic_material, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return archetype


def _preset_archetype(library: dict[str, dict[str, Any]], preset: str, fallback_id: str) -> dict[str, Any]:
    key = str(preset or "").strip()
    raw = library.get(key) or {}
    return _annotate_preset_archetype(raw, key, fallback_id)


def _reference_treatment_archetypes(
    preset: str,
    reference: dict[str, Any],
    treatment_map: dict[str, list[str]],
) -> dict[str, dict[str, Any]]:
    archetypes: dict[str, dict[str, Any]] = {
        "title": _preset_archetype(TITLE_ARCHETYPE_LIBRARY, preset, "structured-title-opener"),
        "references": _preset_archetype(REFERENCE_ARCHETYPE_LIBRARY, preset, "structured-source-posture"),
    }
    treatments = reference.get("content_treatments") if isinstance(reference.get("content_treatments"), dict) else {}
    reference_id = str(reference.get("reference_id") or f"ref-{preset}-structured").strip()
    reference_slug = _slugify(reference_id.removeprefix("ref-")) or _slugify(preset) or "reference"
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        if treatment_key in archetypes:
            continue
        defaults = CONTENT_TREATMENT_ARCHETYPE_DEFAULTS.get(treatment_key, {})
        suffix = str(defaults.get("archetype_id_suffix") or f"{treatment_key}-treatment")
        variants = [
            str(item).strip()
            for item in treatment_map.get(treatment_key, [])
            if str(item).strip() in SUPPORTED_OUTLINE_VARIANTS
        ]
        raw = {
            "archetype_id": f"{reference_slug}-{suffix}",
            "structure": str(treatments.get(treatment_key) or defaults.get("object_pattern") or "").strip(),
            "object_pattern": defaults.get("object_pattern"),
            "required_fields": list(defaults.get("required_fields") if isinstance(defaults.get("required_fields"), list) else []),
            "primary_variants": variants or list(DEFAULT_TREATMENT_VARIANT_MAP.get(treatment_key, ["standard"])),
            "content_goal": str(treatments.get(treatment_key) or "").strip(),
        }
        archetypes[treatment_key] = _annotate_preset_archetype(
            raw,
            preset,
            f"{reference_slug}-{suffix}",
            treatment_key=treatment_key,
        )
    return {key: archetypes[key] for key in REQUIRED_CONTENT_TREATMENTS if key in archetypes}


def _treatment_for_role(role: str, variant: str) -> str:
    normalized_role = str(role or "").strip().lower()
    normalized_variant = str(variant or "").strip().lower()
    if normalized_variant == "title" or normalized_role == "open":
        return "title"
    if normalized_variant in {"comparison-2col", "split", "matrix"} or normalized_role == "comparison":
        return "comparison"
    if normalized_variant == "chart" or normalized_role in {"data", "market", "proof"}:
        return "chart"
    if normalized_variant in {"table", "lab-run-results"} or normalized_role in {"method", "economics", "refs"}:
        return "table" if normalized_role != "refs" else "references"
    if normalized_variant in {"scientific-figure", "image-sidebar", "flow"} or normalized_role in {"context", "architecture"}:
        return "figure"
    if normalized_variant in {"stats", "kpi-hero"} or normalized_role == "dashboard":
        return "dashboard"
    if normalized_role in {"decision", "ask", "close", "synthesis", "plan", "timeline"}:
        return "decision"
    return "decision"


def _merge_treatment_maps(base: dict[str, list[str]], override: dict[str, Any]) -> dict[str, list[str]]:
    merged = {key: list(value) for key, value in base.items()}
    for key, value in override.items():
        if key not in REQUIRED_CONTENT_TREATMENTS:
            continue
        if isinstance(value, list):
            variants = _unique_strings(value)
        else:
            variants = _unique_strings([value])
        if variants:
            merged[key] = variants
    return merged


def _reference_layout_playbook(preset: str, reference: dict[str, Any]) -> dict[str, Any]:
    override = LAYOUT_PLAYBOOK_OVERRIDES.get(preset, {})
    signature = reference.get("signature_slide_family")
    signature_items = signature if isinstance(signature, list) else []
    treatment_map = _merge_treatment_maps(
        DEFAULT_TREATMENT_VARIANT_MAP,
        override.get("treatment_variant_map", {}) if isinstance(override.get("treatment_variant_map"), dict) else {},
    )
    slide_archetypes: list[dict[str, str]] = []
    for item in signature_items:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip() or "content"
        variant = str(item.get("variant") or "").strip() or "standard"
        if variant not in SUPPORTED_OUTLINE_VARIANTS:
            variant = "standard"
        treatment_key = _treatment_for_role(role, variant)
        if treatment_key in treatment_map and variant not in treatment_map[treatment_key]:
            treatment_map[treatment_key] = [variant, *treatment_map[treatment_key]]
        slide_archetypes.append(
            {
                "role": role,
                "variant": variant,
                "treatment_key": treatment_key,
                "layout_note": str(item.get("layout_note") or "").strip(),
            }
        )
    preferred_from_signature = [item["variant"] for item in slide_archetypes]
    preferred = _unique_strings(
        list(override.get("preferred_variants", []) if isinstance(override.get("preferred_variants"), list) else [])
        + preferred_from_signature
        + ["chart", "table", "image-sidebar", "comparison-2col", "standard"]
    )
    opening_sequence = [
        {
            "step": idx + 1,
            "role": item["role"],
            "variant": item["variant"],
            "treatment_key": item["treatment_key"],
            "layout_note": item["layout_note"],
        }
        for idx, item in enumerate(slide_archetypes[:6])
    ]
    content_rules = _unique_strings(
        list(override.get("content_rules", []) if isinstance(override.get("content_rules"), list) else [])
        + [
            "Choose slide variants from this playbook before falling back to generic cards.",
            "Every evidence slide needs a chart, table, figure, flow, stats, or structured comparison anchor.",
        ]
    )
    avoid_variants = _unique_strings(
        override.get("avoid_variants", []) if isinstance(override.get("avoid_variants"), list) else []
    )
    gallery_showcase_variants = [
        variant
        for variant in _unique_strings(
            override.get("gallery_showcase_variants", [])
            if isinstance(override.get("gallery_showcase_variants"), list)
            else []
        )
        if variant in SUPPORTED_OUTLINE_VARIANTS
    ]
    treatment_archetypes = _reference_treatment_archetypes(preset, reference, treatment_map)
    return {
        "playbook_version": LAYOUT_PLAYBOOK_VERSION,
        "style_preset": preset,
        "reference_id": reference.get("reference_id"),
        "preferred_variants": preferred,
        "treatment_variant_map": treatment_map,
        "treatment_archetypes": treatment_archetypes,
        "slide_archetypes": slide_archetypes,
        "opening_sequence": opening_sequence,
        "content_rules": content_rules,
        "avoid_variants": avoid_variants,
        "gallery_showcase_variants": gallery_showcase_variants,
        "proof_anchor_policy": "Select the strongest supported visual/evidence variant for the content; use prose-only slides only for synthesis or decisions.",
        "source_footer_policy": str(
            reference.get("content_treatments", {}).get("references")
            if isinstance(reference.get("content_treatments"), dict)
            else ""
        ),
        "authoring_instruction": "Use this playbook in structure_blueprint.slide_sequence and outline_authoring_handoff.variant_mix_plan so the preset changes slide structure, not only chrome.",
    }


RECIPE_DEFAULTS: dict[str, dict[str, Any]] = {
    "title": {
        "required_slots": ["working title", "scope/context label", "audience or use context", "one credibility chip"],
        "data_roles": ["topic", "scope", "date/period", "audience"],
        "authoring_checks": ["Title must name the deck object, not a generic category.", "Subtitle should lock scope or use context."],
    },
    "comparison": {
        "required_slots": ["left state", "right state", "decision criterion", "verdict"],
        "data_roles": ["baseline", "target/comparator", "difference driver", "decision rule"],
        "authoring_checks": ["Both sides need comparable fields.", "Verdict must be visible on the slide."],
    },
    "chart": {
        "required_slots": ["chart question", "category/time labels", "value series", "readout/caveat", "source id"],
        "data_roles": ["x/category field", "numeric value field", "target/threshold when available", "source cut/version"],
        "authoring_checks": ["Axis labels must satisfy chart_label_min_pt.", "Chart needs a written readout, not only bars/lines."],
    },
    "table": {
        "required_slots": ["row entity", "status/signal field", "action/owner field", "short source/provenance"],
        "data_roles": ["entity", "metric/state", "owner/action", "method/source"],
        "authoring_checks": ["Cells stay phrase-length.", "Split or summarize if table text would fall below body-size floor."],
    },
    "figure": {
        "required_slots": ["proof object", "caption", "interpretation", "caveat or next action"],
        "data_roles": ["figure path or generated output id", "caption source", "interpretation", "quality/crop rule"],
        "authoring_checks": ["Figure must be source-backed or synthetic/starter-labeled.", "Caption and interpretation must remain readable."],
    },
    "dashboard": {
        "required_slots": ["primary metric", "supporting metric", "state/threshold", "owner or implication"],
        "data_roles": ["primary KPI", "secondary KPI", "state/threshold", "owner/action"],
        "authoring_checks": ["Use dashboard only when multiple metrics earn one slide.", "Every metric needs a label and context."],
    },
    "decision": {
        "required_slots": ["decision/action", "evidence trigger", "owner", "caveat/date"],
        "data_roles": ["action", "evidence/trigger", "owner", "timing/risk"],
        "authoring_checks": ["Decision slide must make the action inspectable.", "Avoid generic next-step prose without owner or trigger."],
    },
    "references": {
        "required_slots": ["source id", "short source label", "claim or artifact linked", "full citation when needed"],
        "data_roles": ["source id", "source title", "claim/slide id", "URL/DOI/path"],
        "authoring_checks": ["Short IDs belong in footers.", "Move long citations to editable references tables."],
    },
}


def _storyboard_example_for_recipe(storyboard: dict[str, Any], treatment_key: str) -> dict[str, Any]:
    if treatment_key == "title":
        return {
            "title": storyboard.get("title"),
            "subtitle": storyboard.get("subtitle"),
            "topic": storyboard.get("topic"),
        }
    if treatment_key == "chart":
        chart = storyboard.get("chart") if isinstance(storyboard.get("chart"), dict) else {}
        return {
            "title": chart.get("title"),
            "labels": chart.get("labels"),
            "note": chart.get("note"),
        }
    if treatment_key == "dashboard":
        return {
            "facts": storyboard.get("dashboard_facts"),
            "kpi": storyboard.get("kpi") if isinstance(storyboard.get("kpi"), dict) else {},
        }
    if treatment_key in {"table", "decision"}:
        item = storyboard.get(treatment_key) if isinstance(storyboard.get(treatment_key), dict) else {}
        return {
            "headers": item.get("headers"),
            "example_rows": (item.get("rows") if isinstance(item.get("rows"), list) else [])[:2],
        }
    if treatment_key == "figure":
        figure = storyboard.get("figure") if isinstance(storyboard.get("figure"), dict) else {}
        return {
            "caption": figure.get("caption"),
            "section_titles": [
                str(item.get("title") or "")
                for item in figure.get("sections", [])
                if isinstance(item, dict) and str(item.get("title") or "").strip()
            ],
            "interpretation": figure.get("interpretation"),
        }
    if treatment_key == "comparison":
        comparison = storyboard.get("comparison") if isinstance(storyboard.get("comparison"), dict) else {}
        return {
            "left_title": comparison.get("left_title"),
            "right_title": comparison.get("right_title"),
            "verdict": comparison.get("verdict"),
        }
    if treatment_key == "references":
        return {
            "source_notes": storyboard.get("source_notes"),
        }
    return {}


def _recipe_signature(recipe: dict[str, Any]) -> str:
    archetype = recipe.get("treatment_archetype") if isinstance(recipe.get("treatment_archetype"), dict) else {}
    parts = [
        str(recipe.get("treatment_key") or ""),
        str(archetype.get("archetype_id") or ""),
        str(recipe.get("content_goal") or ""),
        "|".join(str(item) for item in recipe.get("primary_variants", []) if str(item).strip()),
        "|".join(str(item) for item in recipe.get("required_slots", []) if str(item).strip()),
    ]
    example = recipe.get("storyboard_example") if isinstance(recipe.get("storyboard_example"), dict) else {}
    for value in example.values():
        if isinstance(value, list):
            parts.append("|".join(str(item) for item in value[:3]))
        else:
            parts.append(str(value or ""))
    return "::".join(parts)


def _reference_content_recipe_library(preset: str, reference: dict[str, Any]) -> dict[str, Any]:
    storyboard = reference.get("example_storyboard") if isinstance(reference.get("example_storyboard"), dict) else {}
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    treatment_map = playbook.get("treatment_variant_map") if isinstance(playbook.get("treatment_variant_map"), dict) else {}
    treatments = reference.get("content_treatments") if isinstance(reference.get("content_treatments"), dict) else {}
    treatment_archetypes = (
        playbook.get("treatment_archetypes")
        if isinstance(playbook.get("treatment_archetypes"), dict)
        else {}
    )
    recipes: dict[str, dict[str, Any]] = {}
    signatures: dict[str, str] = {}
    source_posture = str(playbook.get("source_footer_policy") or treatments.get("references") or "").strip()
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        defaults = RECIPE_DEFAULTS[treatment_key]
        variants = treatment_map.get(treatment_key) if isinstance(treatment_map.get(treatment_key), list) else []
        recipe = {
            "recipe_version": CONTENT_RECIPE_LIBRARY_VERSION,
            "style_preset": preset,
            "reference_id": reference.get("reference_id"),
            "treatment_key": treatment_key,
            "primary_variants": [
                str(item).strip()
                for item in variants
                if str(item or "").strip() in SUPPORTED_OUTLINE_VARIANTS
            ],
            "content_goal": str(treatments.get(treatment_key) or "").strip(),
            "evidence_anchor": str(treatments.get(treatment_key) or "").strip(),
            "required_slots": list(defaults["required_slots"]),
            "data_roles": list(defaults["data_roles"]),
            "storyboard_example": _storyboard_example_for_recipe(storyboard, treatment_key),
            "source_posture": source_posture if treatment_key != "references" else str(treatments.get("references") or ""),
            "authoring_checks": list(defaults["authoring_checks"]),
        }
        archetype = treatment_archetypes.get(treatment_key)
        if isinstance(archetype, dict):
            recipe["treatment_archetype"] = archetype
        if not recipe["primary_variants"]:
            recipe["primary_variants"] = list(DEFAULT_TREATMENT_VARIANT_MAP.get(treatment_key, ["standard"]))
        recipe["recipe_signature"] = _recipe_signature(recipe)
        recipes[treatment_key] = recipe
        signatures[treatment_key] = recipe["recipe_signature"]
    return {
        "library_version": CONTENT_RECIPE_LIBRARY_VERSION,
        "style_preset": preset,
        "reference_id": reference.get("reference_id"),
        "purpose": "Preset-specific content-slot recipes for translating real prompts, data, charts, tables, figures, and decisions into supported outline variants.",
        "recipes": recipes,
        "recipe_signatures": signatures,
        "authoring_contract": [
            "Select a recipe by treatment_key before writing each content slide.",
            "Bind every required slot to a source field, generated artifact, citation, or explicit assumption.",
            "Use primary_variants first; fall back only when the evidence payload cannot support them.",
            "Record the chosen treatment_key on each outline slide so build-time playbook resolution stays auditable.",
        ],
    }


STYLE_REFERENCES: dict[str, dict[str, Any]] = {
    "executive-clinical": {
        "reference_id": "ref-exec-clinical-evidence-brief",
        "reference_name": "Clinical Evidence Executive Brief",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Quiet hospital-grade executive pages: large evidence headline, one controlled clinical accent, and clear implication blocks.",
        "signature_moves": [
            "left evidence rail with compact patient/pathway state labels",
            "single metric or status ribbon before details",
            "chart plus clinical implication sidebar instead of centered bullets",
        ],
        "prompt_keywords": ["clinical", "pathway", "care", "hospital", "trial", "executive", "translational"],
        "content_treatments": _treatments(
            title="Light clinical opener with one blue/teal status rail and compact context chips.",
            comparison="Two care paths with decision criteria in a low-contrast center gutter.",
            chart="Outcome chart with right-side clinical readout and n/r/source footnote.",
            table="Protocol table with semantic pass/review/fail fills and short row labels.",
            figure="Figure-first evidence panel with interpretation and caveat stack.",
            dashboard="Three clinical status bands: cohort, outcome, operational blocker.",
            decision="Recommendation strip framed as clinical action, owner, and evidence confidence.",
            references="Source-line footer with trial/report IDs; full refs table only when needed.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "clinical status rail plus one-line evidence promise"),
            ("evidence", "chart", "chart left, clinical implication stack right"),
            ("evidence", "lab-run-results", "compact protocol/status table with semantic fills"),
            ("comparison", "comparison-2col", "path A vs path B with eligibility criteria"),
            ("decision", "table", "action/reason/risk owner table"),
            ("close", "standard", "decision strip plus next evidence needed"),
        ),
        "avoid": ["decorative medical icons as evidence", "startup hype language", "tiny dense protocol tables"],
    },
    "bold-startup-narrative": {
        "reference_id": "ref-startup-market-reveal",
        "reference_name": "Market Reveal Pitch Narrative",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "High-contrast pitch pacing: oversized claim, asymmetric proof block, and punchy commercial readout.",
        "signature_moves": [
            "poster-like title slide with one proof chip, not a card cluster",
            "feature-left stats where one number owns the slide",
            "before/after comparison with an explicit market unlock",
        ],
        "prompt_keywords": ["startup", "launch", "pitch", "growth", "market", "product", "founder"],
        "content_treatments": _treatments(
            title="Poster opener with giant claim, small credibility chips, and offset accent slab.",
            comparison="Before/after or old/new behavior split with bold side labels.",
            chart="Commercial chart with one highlighted inflection and bottom proof strip.",
            table="Short pricing/segment table with the winning row emphasized.",
            figure="Product/market visual beside three proof points and one risk note.",
            dashboard="Metric stack that promotes one hero KPI and two supporting signals.",
            decision="Investor-style ask slide: decision, why now, proof, next milestone.",
            references="Minimal source IDs in footer; detailed appendix refs for sourced claims.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "poster title with proof chip cluster"),
            ("problem", "split", "old behavior vs new wedge"),
            ("evidence", "stats", "hero KPI with two supporting metrics"),
            ("proof", "chart", "growth or funnel chart with inflection annotation"),
            ("plan", "timeline", "chapter-spread milestones only when sequence matters"),
            ("ask", "table", "use-of-funds / milestone / owner table"),
        ),
        "avoid": ["generic SaaS four-card grid", "tiny source-heavy footers on pitch slides", "lab-report density"],
    },
    "data-heavy-boardroom": {
        "reference_id": "ref-boardroom-operating-review",
        "reference_name": "Boardroom Operating Review",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Dense but calm operating pages: table/chart pairs, explicit variance language, and source-backed footers.",
        "signature_moves": [
            "chart plus variance table instead of decorative metric tiles",
            "executive takeaway band at bottom, not centered prose",
            "small multiples only when labels remain readable",
        ],
        "prompt_keywords": ["dashboard", "board", "metrics", "ops review", "quarterly", "variance", "analytics"],
        "content_treatments": _treatments(
            title="Plain board title with period, scope, and decision context.",
            comparison="Plan vs actual columns with variance driver notes.",
            chart="Facts-right chart with target/actual callout and source footnote.",
            table="Compact sortable-style table, zebra bands, and bold exception rows.",
            figure="Generated figure with adjacent numbered readout, never floating alone.",
            dashboard="KPI strip across top, chart/table detail below, decision band at bottom.",
            decision="Action table: decision, metric trigger, owner, date.",
            references="Source-line footer with data cut/version; appendix table for long source notes.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "board-period header plus scope line"),
            ("dashboard", "stats", "KPI strip with variance language"),
            ("evidence", "chart", "chart left with facts-right readout"),
            ("evidence", "table", "exception rows and owner/status columns"),
            ("comparison", "matrix", "driver matrix by impact and control"),
            ("decision", "table", "decision log with trigger/owner/date"),
        ),
        "avoid": ["chart-only slides with no readout", "decorative dark hero sections", "cards that hide comparable metrics"],
    },
    "sunset-investor": {
        "reference_id": "ref-investor-unit-economics-memo",
        "reference_name": "Investor Unit Economics Memo",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Warm investor memo: confident thesis, unit-economics proof, and staged capital decisions.",
        "signature_moves": [
            "warm thesis headline with restrained rule, not full-slide gradient",
            "unit economics table paired with one market chart",
            "capital allocation decision strip with downside note",
        ],
        "prompt_keywords": ["investor", "fundraising", "unit economics", "market", "capital", "memo"],
        "content_treatments": _treatments(
            title="Warm thesis opener with one market window and compact round/ask metadata.",
            comparison="Hardware vs software, current vs scaled, or base vs upside economics.",
            chart="Market or margin chart with bottom confidence and sensitivity notes.",
            table="Unit economics table with contribution, payback, and sensitivity rows.",
            figure="Product or market figure framed by thesis, proof, caveat.",
            dashboard="Capital plan dashboard: use of funds, milestone, proof metric.",
            decision="Investment decision slide with fund/hold/monitor language.",
            references="Sparse footer IDs; long market sources in appendix references.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "thesis plus round/market metadata"),
            ("market", "chart", "market timing chart with confidence notes"),
            ("economics", "table", "unit economics and sensitivity rows"),
            ("comparison", "comparison-2col", "current model vs scaled model"),
            ("plan", "timeline", "funding milestones with proof gates"),
            ("decision", "standard", "investor decision strip and downside caveat"),
        ),
        "avoid": ["orange monotone pages", "hype claims without proof tables", "overcrowded source footers"],
    },
    "forest-research": {
        "reference_id": "ref-field-research-policy-brief",
        "reference_name": "Field Research Policy Brief",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Field-science report pages: map/figure first, plain-language interpretation, and policy consequence.",
        "signature_moves": [
            "atlas-style opener with geography/system scope",
            "figure plus observation sidebar",
            "policy tradeoff matrix using open quadrants",
        ],
        "prompt_keywords": ["field", "ecology", "climate", "biology", "sustainability", "environment", "policy"],
        "content_treatments": _treatments(
            title="Light atlas opener with scope tag, field period, and one system map/figure slot.",
            comparison="Intervention vs baseline ecological tradeoffs with source IDs.",
            chart="Minimal trend chart with plain-language interpretation below.",
            table="Evidence table grouped by site, measure, interpretation, confidence.",
            figure="Field image/map/plot first with observation and implication sidebar.",
            dashboard="Indicator dashboard: state, trend, pressure, management lever.",
            decision="Policy option table with ecological benefit, cost, uncertainty.",
            references="Source-line footer plus final references for reports/datasets.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "atlas title with scope and field-period tags"),
            ("evidence", "scientific-figure", "map/plot panel with interpretation strip"),
            ("evidence", "chart", "trend chart with plain-language conclusion"),
            ("comparison", "matrix", "tradeoff quadrants"),
            ("decision", "table", "policy option / benefit / uncertainty table"),
            ("close", "standard", "recommended lever and monitoring metric"),
        ),
        "avoid": ["decorative natural textures", "mapless policy claims", "dense academic prose blocks"],
    },
    "midnight-neon": {
        "reference_id": "ref-dark-technical-console",
        "reference_name": "Dark Technical Console",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Dark technical console: high-contrast signal panes, sparse neon, and operational readouts.",
        "signature_moves": [
            "dark command-center opener with one system diagram or status panel",
            "neon used only for state, thresholds, or active route",
            "incident/AI/security charts with console-like readout columns",
        ],
        "prompt_keywords": ["security", "AI", "cyber", "technical", "console", "model", "infrastructure", "neon"],
        "content_treatments": _treatments(
            title="Command-center opener with system state, not decorative neon wallpaper.",
            comparison="Raw vs enriched, before vs after, model A vs model B with dark divider.",
            chart="Dark chart with threshold line and right-side operational readout.",
            table="Compact console table with status chips and monotone rows.",
            figure="Architecture or screenshot-style figure with callout rail.",
            dashboard="Status console: active alerts, latency/cost/error metrics, next action.",
            decision="Escalation decision bar with severity, owner, and confidence.",
            references="Dim but readable source footer; no tiny low-contrast refs.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "command-center title with status chips"),
            ("dashboard", "stats", "console KPIs with alert severity"),
            ("comparison", "comparison-2col", "raw vs enriched technical workflow"),
            ("evidence", "chart", "threshold chart with right readout"),
            ("architecture", "flow", "short system flow with active route highlight"),
            ("decision", "standard", "escalation action bar"),
        ),
        "avoid": ["neon on every line", "low-contrast captions", "decorative code blocks"],
    },
    "paper-journal": {
        "reference_id": "ref-journal-methods-results",
        "reference_name": "Journal Methods and Results Note",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Paper-like scientific editorial: masthead, methods/result rhythm, and caption-led evidence.",
        "signature_moves": [
            "masthead title with compact abstract-like subtitle",
            "figure/caption hierarchy before interpretation",
            "methods/result/caveat structure across pages",
        ],
        "prompt_keywords": ["journal", "methods", "results", "academic", "paper", "qualitative", "literature"],
        "content_treatments": _treatments(
            title="Journal masthead with deck topic, date/scope, and abstract subtitle.",
            comparison="Method A vs method B with assumptions and caveats in small side notes.",
            chart="Minimal chart with caption and short result sentence.",
            table="Methods/results table with restrained rules and no heavy fills.",
            figure="Figure-first page with caption, panel labels, and interpretation note.",
            dashboard="Evidence ledger: claim, source, observed signal, caveat.",
            decision="Discussion slide: finding, implication, limitation, next experiment.",
            references="Academic-style source IDs and final references table.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "masthead plus abstract subtitle"),
            ("method", "table", "method/results/caveat table"),
            ("evidence", "scientific-figure", "caption-led figure panels"),
            ("evidence", "chart", "minimal chart plus result sentence"),
            ("synthesis", "comparison-2col", "interpretation vs limitation"),
            ("refs", "table", "editable references table"),
        ),
        "avoid": ["pitch-deck claims", "oversized KPI theatrics", "heavy filled cards"],
    },
    "arctic-minimal": {
        "reference_id": "ref-minimal-technical-brief",
        "reference_name": "Minimal Technical Brief",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Cool sparse technical pages: generous whitespace, precise labels, and a single visual anchor.",
        "signature_moves": [
            "single-anchor slide composition",
            "plain title plus one exact qualifier",
            "small decision strip rather than heavy callout box",
        ],
        "prompt_keywords": ["minimal", "technical brief", "postmortem", "system", "clean", "architecture"],
        "content_treatments": _treatments(
            title="Light sparse opener with one object/scope label and large quiet title.",
            comparison="Two-column comparison with low-chrome divider and concise bullets.",
            chart="Minimal chart with labels outside the plot and no decorative frame.",
            table="Short table with open rows and strong whitespace.",
            figure="One large figure or diagram with tiny caption and clear breathing room.",
            dashboard="Two or three status facts in a quiet strip; no dense metric wall.",
            decision="Small bottom decision line plus owner/date.",
            references="Standard footer; use refs only when source burden exists.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "quiet title with scope label"),
            ("context", "image-sidebar", "single anchor figure with text column"),
            ("evidence", "chart", "minimal chart, sparse labels"),
            ("dashboard", "stats", "quiet status facts strip"),
            ("comparison", "comparison-2col", "low-chrome A/B comparison"),
            ("decision", "standard", "small decision line at bottom"),
            ("refs", "table", "short references only if needed"),
        ),
        "avoid": ["many accent systems", "dense tables", "dashboard walls"],
    },
    "charcoal-safety": {
        "reference_id": "ref-risk-incident-control-room",
        "reference_name": "Risk Incident Control Room",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Safety/risk pages: severity-first hierarchy, red/amber semantic color, and action ownership.",
        "signature_moves": [
            "severity band or risk rail that carries across slides",
            "incident timeline as bands, not decorative milestones",
            "controls table with owner/status/remediation date",
        ],
        "prompt_keywords": ["risk", "safety", "incident", "postmortem", "control", "audit", "remediation"],
        "content_treatments": _treatments(
            title="Dark or charcoal risk opener with severity, system, date, and ask.",
            comparison="Current control vs required control with gap severity.",
            chart="Incident rate/severity chart with threshold and remediation readout.",
            table="Risk/control table with red/amber/green state and owner.",
            figure="Incident diagram or process figure with hazard callouts.",
            dashboard="Risk dashboard: severity, exposure, mitigation, open owner.",
            decision="Remediation decision table: action, blocker, due date.",
            references="Audit/source footer with ticket/report IDs.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "severity rail and decision ask"),
            ("timeline", "timeline", "incident sequence in bands"),
            ("dashboard", "stats", "severity/exposure/mitigation metrics"),
            ("evidence", "table", "control gap and owner table"),
            ("comparison", "comparison-2col", "current vs required control"),
            ("decision", "table", "remediation decision log"),
        ),
        "avoid": ["red as decoration", "ownerless findings", "low-contrast dark captions"],
    },
    "lavender-ops": {
        "reference_id": "ref-ops-workbench-review",
        "reference_name": "Operations Workbench Review",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Internal ops workbench: calm workflow state, SLA/queue evidence, and owner-oriented next actions.",
        "signature_moves": [
            "workflow lane labels reused as slide eyebrows",
            "workflow route or cadence slide before the metric dashboard",
            "queue/SLA dashboard with table-first detail",
            "decision table oriented around next operating move",
        ],
        "prompt_keywords": ["ops", "operations", "renewal", "queue", "workflow", "support", "internal tooling"],
        "content_treatments": _treatments(
            title="Quiet ops title with workflow lanes and operating period.",
            comparison="Manual vs automated workflow or current vs target SLA.",
            chart="Queue/SLA trend with facts-right operational interpretation.",
            table="Worklist table with priority, owner, status, and next touch.",
            figure="Workflow or product screenshot with sidebar takeaways.",
            dashboard="SLA, backlog, throughput, blocker metrics in restrained tiles.",
            decision="Operating cadence table: action, owner, trigger, follow-up.",
            references="Standard footer unless reporting source-heavy metrics.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "workflow-lane title with period tag"),
            ("architecture", "flow", "lane route with owner and trigger annotations"),
            ("plan", "timeline", "operating cadence by lane or day"),
            ("dashboard", "stats", "SLA/backlog/throughput metrics"),
            ("evidence", "table", "priority worklist table"),
            ("evidence", "chart", "queue trend with operational readout"),
            ("comparison", "matrix", "manual vs automated workflow state grid"),
            ("decision", "table", "owner/action/trigger cadence"),
        ),
        "avoid": ["purple-only decoration", "marketing hero sections", "unowned action items"],
    },
    "warm-terracotta": {
        "reference_id": "ref-human-centered-case-brief",
        "reference_name": "Human-Centered Case Brief",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Warm case-study report: human context, artifact/photo placement, and practical decision framing.",
        "signature_moves": [
            "case-study opener with place/person/object context",
            "journey or service-moment sequence before metrics",
            "image-sidebar treatment for human evidence",
            "small case cards for beneficiary, friction, and pilot logic",
            "service/experience table with friction and intervention columns",
        ],
        "prompt_keywords": ["case study", "museum", "membership", "hospitality", "community", "heritage", "service"],
        "content_treatments": _treatments(
            title="Warm editorial opener with case context and one object/place signal.",
            comparison="Audience/service before-after with tangible behavior notes.",
            chart="Simple trend or cohort chart with human implication below.",
            table="Experience table: moment, friction, intervention, expected signal.",
            figure="Photo/artifact/sidebar layout with short narrative caption.",
            dashboard="Program health: reach, retention, satisfaction, operational load.",
            decision="Recommendation slide with tradeoff, beneficiary, and next pilot.",
            references="Light footer; source table for surveys or interviews.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "case context plus object/place cue"),
            ("plan", "timeline", "journey moments with friction and intervention cues"),
            ("context", "image-sidebar", "artifact/photo with narrative caption"),
            ("proof", "cards-2", "beneficiary and pilot logic cards"),
            ("evidence", "table", "moment/friction/intervention table"),
            ("evidence", "chart", "behavior trend plus human implication"),
            ("comparison", "matrix", "experience tradeoff grid"),
            ("decision", "standard", "pilot recommendation with tradeoff"),
        ),
        "avoid": ["brown monotone palettes", "abstract icons replacing human evidence", "dense financial dashboard feel"],
    },
    "lab-report": {
        "reference_id": "ref-clean-assay-report",
        "reference_name": "Clean Assay Report",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Lab report source-first pages: specimen/run metadata, evidence objects, compact interpretation, and traceable refs.",
        "signature_moves": [
            "top/bottom lab rules or plain no-rule pages selected by stable seed",
            "table/figure first with interpretation below or beside",
            "compact footer source IDs plus editable references table",
        ],
        "prompt_keywords": ["assay", "lab", "experiment", "samples", "sequencing", "LOD", "validation", "methods"],
        "content_treatments": _treatments(
            title="Clean lab opener with run/sample scope, method, and page-rule rhythm.",
            comparison="Raw screen vs report-ready readout or method A vs method B.",
            chart="Minimal scientific chart with axis labels sized for slide and source IDs.",
            table="Lab-run-results table with pass/review/fail semantic cells.",
            figure="Scientific-figure panel grid or image-sidebar when plots need size.",
            dashboard="Run dashboard: samples, controls, failures, borderline calls.",
            decision="Bottom decision strip: repeat, accept, reject, or escalate.",
            references="Source-line footer with short IDs; final editable References table.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "run/method scope with restrained lab chrome"),
            ("evidence", "lab-run-results", "compact result table and interpretation"),
            ("evidence", "scientific-figure", "1-4 figure panels with caption"),
            ("comparison", "comparison-2col", "raw readout vs report-ready conclusion"),
            ("data", "chart", "minimal chart plus source/readability metadata"),
            ("refs", "table", "editable references table"),
        ),
        "avoid": ["text-only content slides", "long provenance in footer", "decorative icons as evidence"],
    },
    "editorial-minimal": {
        "reference_id": "ref-spare-editorial-brief",
        "reference_name": "Spare Editorial Brief",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Sparse editorial pages: typographic hierarchy, negative space, one visual or text argument at a time.",
        "signature_moves": [
            "masthead or title-rule opener with strong line breaks",
            "one image/quote/chart anchor per slide",
            "essay-like section rhythm without card walls",
        ],
        "prompt_keywords": ["editorial", "minimal", "narrative", "brief", "magazine", "qualitative", "essay"],
        "content_treatments": _treatments(
            title="Masthead opener with large type and one precise subtitle.",
            comparison="Essay-style two-column contrast with generous whitespace.",
            chart="One quiet chart with a caption-like takeaway, no heavy frame.",
            table="Very short editorial table; otherwise move detail to appendix.",
            figure="Image-sidebar or full-bleed artifact with restrained caption.",
            dashboard="Editorial signal board: one thesis plus two or three proof facts.",
            decision="Closing thesis slide with one recommendation and minimal proof list.",
            references="Small standard footer or final sources slide; never crowded.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "masthead with editorial line break"),
            ("context", "image-sidebar", "single artifact/image plus short prose"),
            ("evidence", "chart", "quiet chart and caption takeaway"),
            ("comparison", "split", "structured prose contrast with whitespace"),
            ("dashboard", "split", "thesis plus sparse proof facts"),
            ("synthesis", "standard", "one thesis and three compact supports"),
            ("refs", "table", "short source list if required"),
        ),
        "avoid": ["KPI tile walls", "busy comparison gutters", "source-heavy report density"],
    },
}


def _default_reference(preset: str) -> dict[str, Any]:
    return {
        "reference_id": f"ref-{preset or 'general'}-structured-brief",
        "reference_name": "Structured Brief",
        "source_status": "synthetic_original_publish_safe",
        "style_dna": "Generic structured report: clear hierarchy, one evidence anchor per content slide, and explicit decisions.",
        "signature_moves": ["one visual anchor per slide", "short decision strip", "source-aware footer"],
        "prompt_keywords": [preset] if preset else [],
        "content_treatments": _treatments(
            title="Large topic-specific opener with compact subtitle.",
            comparison="Two clear columns with a concise verdict.",
            chart="Chart plus short readout.",
            table="Readable summary table with short cell text.",
            figure="Figure or image paired with interpretation.",
            dashboard="Small metric set with explicit status labels.",
            decision="Action/owner/status decision block.",
            references="Footer IDs plus references slide when source-heavy.",
        ),
        "signature_slide_family": _slides(
            ("open", "title", "topic-specific opener"),
            ("evidence", "chart", "chart plus readout"),
            ("evidence", "table", "short summary table"),
            ("comparison", "comparison-2col", "A/B contrast with verdict"),
            ("decision", "standard", "decision strip"),
        ),
        "avoid": ["unsupported renderer treatments", "unreadable text", "generic card walls"],
    }


def _default_storyboard(preset: str) -> dict[str, Any]:
    return {
        "topic": f"{preset or 'general'} structured brief",
        "title": "Structured Brief Example",
        "subtitle": "Synthetic storyboard with chart, table, figure, comparison, decision, and references examples.",
        "chart": {
            "title": "Example evidence trend",
            "labels": ["A", "B", "C", "D"],
            "values": [42, 58, 63, 71],
            "note": "Synthetic chart values for reference-gallery rendering.",
        },
        "dashboard_facts": [
            {"value": "8", "label": "Treatments", "detail": "full grammar"},
            {"value": "1", "label": "Replay seed", "detail": "deterministic"},
        ],
        "kpi": {"value": "8", "label": "reference moves", "context": "Use only when the metric earns the slide."},
        "table": {
            "headers": ["Item", "Signal", "Action"],
            "rows": [
                ["Claim", "Supported", "Show proof"],
                ["Risk", "Visible", "Name owner"],
                ["Source", "Traceable", "Cite short"],
            ],
        },
        "figure": {
            "sections": [
                {"title": "Proof object", "body": ["One generated figure owns the slide.", "Sidebar carries the implication."]},
                {"title": "Replay path", "body": ["Asset path and caption stay in source JSON."]},
            ],
            "caption": "Synthetic figure generated by build_style_reference_gallery.py.",
            "interpretation": "The figure slot demonstrates proof objects, captions, and source posture.",
        },
        "comparison": {
            "left_title": "Generic chrome",
            "left_body": ["Shared title bar", "Layout chosen late"],
            "right_title": "Reference-led",
            "right_body": ["Preset grammar", "Evidence object first"],
            "verdict": "Reference first; outline second.",
        },
        "decision": {
            "headers": ["Decision", "Evidence", "Owner"],
            "rows": [
                ["Act", "Signal", "Named owner"],
                ["Watch", "Caveat", "Reviewer"],
                ["Source", "Trace", "Editor"],
            ],
        },
        "timeline": [
            {"label": "01", "title": "Frame", "body": "Pick reference"},
            {"label": "02", "title": "Bind", "body": "Choose proof"},
            {"label": "03", "title": "Build", "body": "Render outline"},
            {"label": "04", "title": "QA", "body": "Check geometry"},
        ],
        "quadrants": [
            {"title": "High proof", "body": "Use chart or figure."},
            {"title": "High action", "body": "Surface owner."},
            {"title": "Low certainty", "body": "Show caveat."},
            {"title": "Low burden", "body": "Keep refs short."},
        ],
        "source_notes": ["Synthetic reference fixture"],
    }


def preset_example_storyboard(preset: str) -> dict[str, Any]:
    """Return a publish-safe synthetic content storyboard for gallery examples."""
    key = str(preset or "").strip() or "executive-clinical"
    storyboard = copy.deepcopy(EXAMPLE_STORYBOARDS.get(key, _default_storyboard(key)))
    fallback = _default_storyboard(key)
    for field in REQUIRED_STORYBOARD_FIELDS:
        if field == "storyboard_version":
            continue
        if field not in storyboard or storyboard.get(field) in (None, "", [], {}):
            storyboard[field] = copy.deepcopy(fallback[field])
    storyboard["storyboard_version"] = EXAMPLE_STORYBOARD_VERSION
    storyboard["style_preset"] = key
    storyboard.setdefault(
        "publish_safety",
        {
            "status": "synthetic_original_publish_safe",
            "basis": "generic synthetic storyboard; no real organization, patient, customer, or public-source data",
        },
    )
    return storyboard


def preset_structural_motif(preset: str) -> dict[str, Any]:
    """Return reusable structural motifs that distinguish a preset before rendering."""
    key = str(preset or "").strip() or "executive-clinical"
    motif = copy.deepcopy(STRUCTURAL_MOTIF_LIBRARY.get(key, {}))
    if not motif:
        motif = {
            "background_structure": "generic structured report with clear hierarchy and one evidence object per content slide",
            "layout_motifs": ["single evidence anchor", "structured comparison", "decision/footer strip"],
            "content_object_rules": [
                "choose an evidence object before writing prose",
                "bind decisions to owner, trigger, and source",
                "keep source posture visible without crowding the slide",
            ],
        }
    motif["motif_library_version"] = STRUCTURAL_MOTIF_LIBRARY_VERSION
    motif["style_preset"] = key
    motif["motif_signature"] = "::".join(
        [
            str(motif.get("background_structure") or ""),
            "|".join(str(item) for item in motif.get("layout_motifs", []) if str(item).strip()),
            "|".join(str(item) for item in motif.get("content_object_rules", []) if str(item).strip()),
        ]
    )
    return motif


def preset_style_metric_profile(preset: str) -> dict[str, Any]:
    """Return quantitative style constraints agents can apply before rendering."""
    key = str(preset or "").strip() or "executive-clinical"
    profile = copy.deepcopy(STYLE_METRIC_PROFILES.get(key, {}))
    if not profile:
        profile = {
            "density_level": "medium structured brief",
            "whitespace_ratio_target": 0.28,
            "body_words_per_content_slide": [24, 48],
            "max_primary_objects": 2,
            "visual_hierarchy": "one evidence object, one interpretation, and one source cue",
            "evidence_object_mix": {"chart": 0.25, "table": 0.25, "figure": 0.25, "prose": 0.25},
            "source_burden": "medium; keep sources visible without crowding the body",
            "footer_posture": "standard footer with compact source notes",
            "artifact_bias": ["chart", "table", "figure"],
            "readability_bias": ["body 12-16 pt", "avoid text-only content slides"],
        }
    profile["metric_profile_version"] = STYLE_METRIC_PROFILE_VERSION
    profile["style_preset"] = key
    mix = profile.get("evidence_object_mix") if isinstance(profile.get("evidence_object_mix"), dict) else {}
    body_budget = (
        profile.get("body_words_per_content_slide")
        if isinstance(profile.get("body_words_per_content_slide"), list)
        else []
    )
    signature_material = {
        "density_level": profile.get("density_level"),
        "whitespace_ratio_target": profile.get("whitespace_ratio_target"),
        "body_words_per_content_slide": body_budget,
        "max_primary_objects": profile.get("max_primary_objects"),
        "visual_hierarchy": profile.get("visual_hierarchy"),
        "evidence_object_mix": {str(k): mix.get(k) for k in sorted(mix)},
        "source_burden": profile.get("source_burden"),
        "footer_posture": profile.get("footer_posture"),
        "artifact_bias": profile.get("artifact_bias"),
        "readability_bias": profile.get("readability_bias"),
    }
    profile["metric_signature"] = hashlib.sha256(
        json.dumps(signature_material, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return profile


def preset_style_reference(preset: str) -> dict[str, Any]:
    """Return a copyable synthetic style reference for a preset."""
    key = str(preset or "").strip() or "executive-clinical"
    reference = copy.deepcopy(STYLE_REFERENCES.get(key, _default_reference(key)))
    reference["catalog_version"] = STYLE_REFERENCE_VERSION
    reference["style_preset"] = key
    reference.setdefault("source_status", "synthetic_original_publish_safe")
    reference.setdefault(
        "publish_safety",
        {
            "status": "publish_safe",
            "basis": "original synthetic reference description; no proprietary slide geometry, branding, or data copied",
        },
    )
    source_intake = preset_source_intake_route(key)
    if source_intake:
        reference["style_source_intake"] = source_intake
    reference["structural_motif_library"] = preset_structural_motif(key)
    reference["style_metric_profile"] = preset_style_metric_profile(key)
    reference["example_storyboard"] = preset_example_storyboard(key)
    reference["layout_playbook"] = _reference_layout_playbook(key, reference)
    reference["content_recipe_library"] = _reference_content_recipe_library(key, reference)
    return reference


def style_reference_catalog(presets: list[str] | None = None) -> dict[str, Any]:
    """Return the full catalog or a preset-filtered subset."""
    keys = presets if presets is not None else sorted(STYLE_REFERENCES)
    return {
        "catalog_version": STYLE_REFERENCE_VERSION,
        "source_manifest_version": SOURCE_MANIFEST_VERSION,
        "references": [preset_style_reference(preset) for preset in keys],
    }


def rank_style_references(text: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Simple deterministic prompt-to-reference matcher for design scouts."""
    lowered = str(text or "").lower()
    tokens = set(re.findall(r"[a-z0-9]+", lowered))
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for preset, reference in STYLE_REFERENCES.items():
        keywords = [str(item).lower() for item in reference.get("prompt_keywords", [])]
        score = 0
        for keyword in keywords:
            keyword_tokens = set(re.findall(r"[a-z0-9]+", keyword))
            if keyword and keyword in lowered:
                score += 3
            score += len(tokens.intersection(keyword_tokens))
        family_words = set(re.findall(r"[a-z0-9]+", str(reference.get("style_dna", "")).lower()))
        score += len(tokens.intersection(family_words)) // 2
        ranked.append((score, preset, reference))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = ranked[: max(1, limit)]
    return [
        {
            "style_preset": preset,
            "score": score,
            "reference": preset_style_reference(preset),
        }
        for score, preset, _reference in selected
        if score > 0 or limit > 0
    ]


def _mix_reference_summary(match: dict[str, Any]) -> dict[str, Any]:
    reference = match.get("reference") if isinstance(match.get("reference"), dict) else {}
    playbook = reference.get("layout_playbook") if isinstance(reference.get("layout_playbook"), dict) else {}
    recipe_library = (
        reference.get("content_recipe_library")
        if isinstance(reference.get("content_recipe_library"), dict)
        else {}
    )
    return {
        "style_preset": match.get("style_preset"),
        "score": match.get("score"),
        "reference_id": reference.get("reference_id"),
        "reference_name": reference.get("reference_name"),
        "style_dna": reference.get("style_dna"),
        "structural_motif_library": reference.get("structural_motif_library"),
        "style_metric_profile": reference.get("style_metric_profile"),
        "signature_moves": reference.get("signature_moves"),
        "style_source_intake": {
            "manifest_version": (reference.get("style_source_intake") or {}).get("manifest_version")
            if isinstance(reference.get("style_source_intake"), dict)
            else None,
            "route_id": (reference.get("style_source_intake") or {}).get("route_id")
            if isinstance(reference.get("style_source_intake"), dict)
            else None,
            "source_ids": (reference.get("style_source_intake") or {}).get("source_ids")
            if isinstance(reference.get("style_source_intake"), dict)
            else [],
            "derivation_mode": (reference.get("style_source_intake") or {}).get("derivation_mode")
            if isinstance(reference.get("style_source_intake"), dict)
            else None,
        },
        "example_storyboard": {
            "storyboard_version": (reference.get("example_storyboard") or {}).get("storyboard_version")
            if isinstance(reference.get("example_storyboard"), dict)
            else None,
            "topic": (reference.get("example_storyboard") or {}).get("topic")
            if isinstance(reference.get("example_storyboard"), dict)
            else None,
            "title": (reference.get("example_storyboard") or {}).get("title")
            if isinstance(reference.get("example_storyboard"), dict)
            else None,
        },
        "preferred_variants": playbook.get("preferred_variants"),
        "opening_sequence": playbook.get("opening_sequence"),
        "content_recipe_library": {
            "library_version": recipe_library.get("library_version"),
            "recipe_signatures": recipe_library.get("recipe_signatures"),
            "authoring_contract": recipe_library.get("authoring_contract"),
        },
        "content_rules": playbook.get("content_rules"),
        "avoid_variants": playbook.get("avoid_variants"),
    }


def style_reference_mix_plan(text: str, *, limit: int = 3) -> dict[str, Any]:
    """Return a compact primary-plus-secondary reference plan for hybrid prompts."""
    matches = rank_style_references(text, limit=max(3, limit))
    positive = [match for match in matches if int(match.get("score") or 0) > 0]
    if not positive and matches:
        positive = [matches[0]]
    primary = positive[0] if positive else {}
    secondary = [
        match
        for match in positive[1:limit]
        if match.get("style_preset") != primary.get("style_preset")
    ]
    primary_reference = primary.get("reference") if isinstance(primary.get("reference"), dict) else {}
    secondary_summaries = [_mix_reference_summary(match) for match in secondary]
    treatment_mix: dict[str, dict[str, Any]] = {}
    primary_treatments = (
        primary_reference.get("content_treatments")
        if isinstance(primary_reference.get("content_treatments"), dict)
        else {}
    )
    for treatment_key in REQUIRED_CONTENT_TREATMENTS:
        borrowed_options: list[dict[str, str]] = []
        for match in secondary:
            reference = match.get("reference") if isinstance(match.get("reference"), dict) else {}
            treatments = (
                reference.get("content_treatments")
                if isinstance(reference.get("content_treatments"), dict)
                else {}
            )
            value = str(treatments.get(treatment_key) or "").strip()
            if value:
                borrowed_options.append(
                    {
                        "from_style_preset": str(match.get("style_preset") or ""),
                        "reference_id": str(reference.get("reference_id") or ""),
                        "treatment": value,
                    }
                )
        treatment_mix[treatment_key] = {
            "primary": str(primary_treatments.get(treatment_key) or ""),
            "optional_secondary_influences": borrowed_options[:2],
        }
    return {
        "mix_plan_version": STYLE_REFERENCE_MIX_PLAN_VERSION,
        "query": str(text or ""),
        "primary": _mix_reference_summary(primary) if primary else {},
        "secondary_influences": secondary_summaries,
        "treatment_mix": treatment_mix,
        "mixing_rules": [
            "Primary reference owns style_preset, layout_playbook, supported variants, and source/footer posture.",
            "Secondary references may lend a content-treatment idea only when it fits the primary playbook and renderer schema.",
            "Do not copy proprietary slide geometry or add unsupported variants, fonts, colors, or decorative chrome.",
            "Record any borrowed influence in design_contract.choice_resolution and structure_blueprint rationale.",
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Emit synthetic style-reference catalog JSON.")
    parser.add_argument("--preset", default="", help="Optional preset to emit.")
    parser.add_argument("--rank", default="", help="Optional user prompt to rank against references.")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.rank:
        payload: Any = {
            "catalog_version": STYLE_REFERENCE_VERSION,
            "matches": rank_style_references(args.rank, limit=args.limit),
            "mix_plan": style_reference_mix_plan(args.rank, limit=min(max(args.limit, 2), 4)),
        }
    elif args.preset:
        payload = preset_style_reference(args.preset)
    else:
        payload = style_reference_catalog()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
