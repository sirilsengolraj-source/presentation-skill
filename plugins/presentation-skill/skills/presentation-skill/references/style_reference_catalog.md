# Style Reference Catalog

The style reference catalog is the skill's publish-safe design-memory layer. It
does not store copied proprietary slide decks, screenshots, geometry, logos, or
data. It stores synthetic, generic reference families that describe how a
preset should present different content types.

## Why This Exists

Preset colors and header rules are not enough to make thirteen styles feel
different. Each preset needs a reusable visual grammar:

- how title slides open
- how comparisons are structured
- how charts are annotated
- how tables are made readable
- how figures and screenshots are framed
- how dashboards and decision slides work
- how sources, refs, and page numbers are handled

Agents should match the user request to one primary reference family plus
bounded secondary influences, then write a reproducible design contract that
records the selected reference mix. The primary reference owns the preset,
layout playbook, source/footer posture, and supported variants. Secondary
references may lend named content-treatment ideas only when they fit the
primary playbook and renderer schema.

The catalog has two layers:

- `scripts/style_reference_catalog.py` stores compact, publish-safe style DNA
  and content-treatment rules.
- `references/style_reference_sources.json` records license/source-intake
  routes for public resources and screenshots, while
  `scripts/style_reference_sources.py` validates those routes before a source
  can influence the catalog. Each source class must include generic style
  observations and reusable slide-pattern extracts, so the catalog stores
  teachable design memory rather than a bare link list.
- `style_reference_mix_plan_v1` ranks prompt matches into a primary reference,
  secondary influences, treatment-level borrow rules, and mixing constraints
  for reproducible hybrid prompts.
- `style_reference_structural_motif_library_v1` gives each preset a
  background structure, layout motifs, content-object rules, and motif
  signature. This is the first guard against same-looking presets: the motif
  grammar determines whether a deck behaves like an evidence rail, workflow
  workbench, atlas plate, command console, lab run report, editorial masthead,
  or case-study journey before renderer chrome is selected.
- `style_reference_metric_profile_v1` gives each preset a quantitative style
  profile: density level, whitespace target, body-word budget, maximum primary
  object count, visual hierarchy, chart/table/figure/prose mix, source burden,
  footer posture, artifact bias, readability bias, and a replayable metric
  signature.
- `style_reference_example_storyboard_v1` gives each preset a publish-safe
  synthetic topic, chart vocabulary, dashboard facts, table rows, figure
  sections, comparison frame, decision rows, and source notes. This prevents
  generated reference decks from proving only chrome differences.
- `style_reference_content_recipe_library_v1` gives each treatment key a
  reproducible content recipe: required slots, data roles, supported primary
  variants, source posture, authoring checks, and a recipe signature.
- `style_reference_starter_outline_v1` lets `init_deck_workspace.py` seed new
  workspaces with a few preset-specific, synthetic scaffold slides so the first
  outline already demonstrates the selected preset's content grammar.
- `scripts/build_style_reference_gallery.py` turns those references into
  actual synthetic slide decks with title, dashboard, comparison, chart, table,
  figure, decision, and references examples. These decks use generated generic
  figures and synthetic data, not copied template slides. The generated
  summary and release evidence include structural playbook signatures and
  content-recipe signature coverage, so a release can prove the presets differ
  in content grammar and treatment-to-layout maps as well as visual treatment.

## Publish-Safety Policy

Allowed in this repository:

- original synthetic reference descriptions
- generated example decks with generic data/content
- extracted numeric/style metadata from a user-provided or public PPTX when the
  source is not redistributed
- links and license notes for public-domain or permissively licensed sources
- recreated generic examples that do not copy proprietary branding, content,
  screenshots, exact geometry, or distinctive slide compositions

Not allowed in this repository:

- proprietary template files or screenshots without permission
- third-party brand marks, confidential data, or identifiable customer content
- copied slide layouts that are too close to a non-public source
- bundled CC-BY assets without attribution metadata

## Public Resource Use

Use public sources as inspiration or direct inputs only when their rights are
clear. Useful source classes include:

- U.S. government/public-domain material, while avoiding protected marks and
  endorsement implications. NASA's media guidance says NASA content is
  generally not subject to U.S. copyright but highlights restrictions around
  identifiers, endorsement, third-party materials, people, and AI attribution:
  https://www.nasa.gov/nasa-brand-center/images-and-media/
- Public health/science sources such as CDC/ATSDR materials that are public
  domain unless otherwise noted. CDC's agency-material guidance requires
  attribution/disclaimer and warns that contractor, grantee, third-party,
  state/local, and logo materials can be restricted:
  https://www.cdc.gov/other/agencymaterials.html
- Accessibility guidance from Section508.gov for PowerPoint structure,
  contrast, reading order, and template hygiene:
  https://www.section508.gov/create/presentations/
- Public design-system guidance from USWDS for civic information hierarchy,
  accessible components, status labels, and policy/service structure:
  https://designsystem.digital.gov/
- GOV.UK Design System guidance for plain-language headings, summary lists,
  task-oriented structure, and restrained public-service typography:
  https://design-system.service.gov.uk/
- Carbon data-visualization guidance for chart annotation, dashboard
  hierarchy, light/dark themes, state, and threshold readouts:
  https://carbondesignsystem.com/data-visualization/getting-started/
- CC BY templates or examples only with attribution preserved in notes,
  source metadata, or an editable references/credits slide. For example,
  SlidesCarnival templates are CC BY 4.0 and require credit plus care with
  bundled photographs/credits:
  https://www.slidescarnival.com/terms-of-use

When in doubt, extract or describe the style at a high level and recreate a
generic synthetic reference instead of storing the original.

## Source-Intake Manifest

Public-source inspiration must be recorded before it becomes reusable style
memory:

```bash
python3 scripts/style_reference_sources.py --validate
python3 scripts/style_reference_sources.py --preset lab-report
```

The manifest stores:

- source URL, status, license summary, and checked date
- per-source `source_verification` with checked URL/date, evidence summary,
  and verified scope
- allowed extraction modes: `metadata_only`, `synthetic_reconstruction`, or
  `linked_attribution`
- generic style observations and reusable slide-pattern extracts that agents
  may translate into original synthetic examples
- forbidden materials such as logos, third-party assets, people/likenesses,
  copied screenshots, private data, or distinctive slide geometry
- attribution/disclaimer posture for direct use
- per-preset intake routes and the synthetic content required to replace the
  original material

The current implementation validates 13 preset routes against eight public
source classes: NASA media guidance, CDC agency-material guidance,
Section508.gov presentation accessibility guidance, SlidesCarnival CC BY
template terms, USWDS public design-system guidance, GOV.UK Design System
guidance, Carbon data-visualization guidance, and CFPB data-visualization
guidance. These are intake routes, not bundled template assets. Generated
gallery decks remain synthetic and generic.

## Descriptor Inspiration Corpus

The descriptor corpus is the scalable design-memory layer for public design
systems, presentation tooling, template indexes, and slide-design writing:

```bash
python3 scripts/style_inspiration_corpus.py --validate
python3 scripts/style_inspiration_corpus.py --preset lab-report \
  --prompt "assay validation report with figures and source footers"
```

It is intentionally descriptor-only. It stores URLs, rights posture, allowed
extractions, forbidden materials, layout families, palette/type descriptors,
content-treatment affinity, per-preset routes, and a subagent contract. It does
not store raw PPTX files, screenshots, logos, proprietary text, or copied slide
geometry. Large-scale scraping should feed a normalized descriptor queue and
synthetic reconstruction notes; only verified descriptors should enter the
skill repo.

The router prompt includes a compact `style_inspiration_corpus` block so a
style scout can choose a primary preset route, inspect a few source descriptors,
and decide whether any secondary preset should lend a specific treatment. The
main agent must still record deterministic choices in the design contract:
selected preset, source IDs, style seed, treatment mix, contact-sheet use cases,
and safety statement.

## Large Public Deck Corpus

The large corpus is the scalable public-usage index behind dynamic style
scouting:

```bash
python3 scripts/large_style_corpus.py --validate --min-records 2000 --min-family-records 10
python3 scripts/large_style_corpus.py --compact-context \
  --primary-family lab-report \
  --prompt "assay validation report with generated figures and refs"
```

Its source manifest lives in
`references/large_style_corpus_sources.json`; the generated catalog lives in
`references/large_style_corpus_catalog.json`, with a human-readable digest in
`references/large_style_corpus_catalog.md`. The discovery command uses public
GitHub metadata routes for Slidev, Marp, reveal.js, PPTX, PDF, ODP, investor,
lab, clinical, dashboard, risk, policy, workshop, and AI-agent deck signals.
The catalog stores only URLs, repository/path metadata, inferred style
families, content-treatment tags, and overlap/selection diagnostics. It does
not store raw decks, screenshots, slide text, logos, or copied geometry.

Use this layer when the curated preset examples feel too similar or when the
prompt asks for a style family that should reflect real public usage. The
LLM/subagent workflow is:

- choose one primary style family from the compact corpus context
- borrow at most two named treatment ideas from source records or secondary
  families
- translate those ideas into original synthetic layouts and supported renderer
  variants
- record the selected family, borrowed treatment names, style seed, and safety
  statement in the design contract
- replace redundant-looking presets by drawing from underrepresented family
  summaries, not by copying a source deck

AI-agent-created or AI-tooling deck records get a priority signal in the
catalog because they are useful examples of agent-era structure, but they are
subject to the same descriptor-only rule.

## Preset Contact-Sheet Collections

Rendered style-reference galleries now include a browseable mini library under
each preset:

- `overview`: title, comparison, chart, table, figure, dashboard, decision, and
  references examples for the preset
- `data_evidence`: chart, table, figure, and dashboard examples
- `decision_sources`: comparison, decision, references, and title/source
  posture examples

These collections solve a different problem than the global contact sheets. The
global sheets compare one treatment across presets; the per-preset sheets show
how one preset behaves across several use cases, which is the faster browsing
path when an agent has already selected a style. Release evidence fingerprints
each sheet and fails if any preset/use-case collection is missing or lacks the
expected treatment thumbnails.

## Catalog Shape

Each preset reference should include:

- `catalog_version`
- `style_preset`
- `reference_id`
- `reference_name`
- `source_status`
- `style_source_intake`
- `structural_motif_library`
- `style_metric_profile`
- `example_storyboard`
- `style_dna`
- `signature_moves`
- `prompt_keywords`
- `content_treatments`
- `signature_slide_family`
- `layout_playbook`
- `content_recipe_library`
- `publish_safety`
- `avoid`

`content_treatments` must cover:

- `title`
- `comparison`
- `chart`
- `table`
- `figure`
- `dashboard`
- `decision`
- `references`

`layout_playbook` must include:

- `playbook_version: style_reference_layout_playbook_v1`
- `preferred_variants`: ordered supported outline variants for the preset
- `treatment_variant_map`: title/comparison/chart/table/figure/dashboard/
  decision/references mapped to supported outline variants
- `treatment_archetypes`: named archetypes for every treatment key: `title`,
  `comparison`, `chart`, `table`, `figure`, `dashboard`, `decision`, and
  `references`. Each entry includes an archetype ID, structure, required
  fields, object pattern or renderer posture, primary variants when relevant,
  and a replayable signature. These prove body-slide grammar differs even when
  multiple presets share the same supported renderer variant.
- `slide_archetypes`: role, variant, treatment key, and layout note records
- `opening_sequence`: the first reference-specific slide moves
- `content_rules`: practical authoring rules that change structure
- `avoid_variants`: variants that make the preset collapse into a generic deck
- `gallery_showcase_variants`: preset-specific variants used first in the
  generated gallery so each preset demonstrates distinct, useful structures
  instead of only color/header differences

`structural_motif_library` must include:

- `motif_library_version: style_reference_structural_motif_library_v1`
- `background_structure`: the preset's reusable page system
- `layout_motifs`: named structural moves such as evidence rail, workflow
  lanes, atlas opener, command console, semantic result table, or case journey
- `content_object_rules`: rules that decide where charts, tables, figures,
  decisions, caveats, and sources live
- `motif_signature`: replayable signature used by smoke checks and release
  evidence to prove each preset has distinct structure

`style_metric_profile` must include:

- `metric_profile_version: style_reference_metric_profile_v1`
- `density_level`: human-readable density posture such as sparse technical
  brief, clean lab report, or operating dashboard
- `whitespace_ratio_target`: approximate target blank/safe-area share for
  content slides
- `body_words_per_content_slide`: low/high body-word budget before the outline
  should split a slide or convert prose into a visual object
- `max_primary_objects`: maximum chart/table/figure/prose objects before a
  slide should split
- `visual_hierarchy`: the scan path a user should perceive first
- `evidence_object_mix`: chart/table/figure/prose weighting that guides
  artifact selection and content-treatment choice
- `source_burden` and `footer_posture`: how much proof/source material the
  preset should carry visibly
- `artifact_bias` and `readability_bias`: concrete constraints for generated
  figures, editable charts/tables, captions, and text-size decisions
- `metric_signature`: replayable signature used by smoke checks and release
  evidence to prove every preset has distinct source-side style metrics

`content_recipe_library` must include:

- `library_version: style_reference_content_recipe_library_v1`
- `recipes` for every required treatment key
- each recipe's `primary_variants`, `required_slots`, `data_roles`,
  `storyboard_example`, `source_posture`, `treatment_archetype`,
  `authoring_checks`, and `recipe_signature`
- `recipe_signatures`, keyed by treatment, so replay/audit code can compare
  content grammar across builds without reopening the full catalog text

`example_storyboard` must include:

- `storyboard_version: style_reference_example_storyboard_v1`
- `topic`, `title`, and `subtitle`
- `chart` with slide-readable labels and values
- `dashboard_facts` and optional `kpi`
- `table` and `decision` headers/rows
- `figure` sidebar/panel sections, caption, and interpretation
- `comparison` left/right state and verdict
- `source_notes` proving the examples are synthetic and publish-safe

## Prompt Matching And Mix Plans

Use the catalog CLI to inspect how a user prompt maps to references:

```bash
python3 scripts/style_reference_catalog.py \
  --rank "clinical investor unit economics memo for hospital pathway decision"
```

The output includes `matches` plus `mix_plan`. Use `mix_plan.primary` for the
deck's preset, `style_reference_layout_playbook_v1`, opening sequence, and
footer/source rules. Use `mix_plan.secondary_influences` only as content
strategy hints. The generated design contract should record the primary
reference, secondary influences, treatment-level choices, and any rejected
borrowed ideas in `choice_resolution`. Carry the selected preset's
`renderer_treatment_signature` and `renderer_treatment_defaults` with the
reference so title/footer/chart/table/figure/stats/matrix/callout posture can
be audited and replayed without reopening the full style reference text.
Carry the selected `content_recipe_library` version and recipe signatures in
the design contract's `structure_replay`, and carry the selected
`style_metric_profile` version/signature plus density, whitespace, word-budget,
object-count, and evidence-mix fields in `style_replay`. Outline-authoring
handoffs should record selected recipes in
`contract_alignment.content_recipe_library_used`, record the metric values in
`contract_alignment.style_metric_profile_used`, and keep each outline slide's
`treatment_key` so build-time playbook resolution remains auditable.

`npm run check:style-reference` is the regression gate for this layer. It
validates schema/source/storyboard coverage and now also checks one strong
prompt for every loadable preset, including top score and score-margin floors.
It also checks hybrid prompts where the primary reference must stay stable and
the expected secondary influence must appear in the mix plan. When adding a
new preset or changing `prompt_keywords`, add or update these probes so prompt
routing remains reproducible instead of only visually plausible.

## Workspace Starter Scaffolds

`scripts/init_deck_workspace.py` now creates starter outlines with
`metadata.starter_outline_version: style_reference_starter_outline_v1`. After
the stable title and core-message slides, it adds up to three synthetic
style-reference scaffold slides selected from the preset playbook. For example,
`lab-report` starts with table/scientific-figure/comparison grammar, while
startup and dashboard-oriented presets can start with hero metrics, stat tiles,
matrixes, image sidebars, or flow diagrams.

These slides are style memory, not final content. They are marked with:

- `starter_kind: style_reference`
- `source_status: synthetic_style_reference_scaffold` in `content_plan.json`
- source/ref markers showing the synthetic reference family

For figure/sidebar/flow/card/matrix starters, initialization also writes small
deterministic local assets under `assets/style_reference/` and
`assets/icons/`. These are generated placeholders, not bundled third-party
media, and exist only so the scaffold can render and pass strict QA before the
author replaces it with real sourced evidence.

Authoring agents should replace them with topic-specific sourced content before
delivery. Cleanup-aware artifact binding removes them alongside the legacy
`s2` starter when `cleanup_default_starter` is enabled, and readiness logic
treats them as starter material rather than proof that the outline has been
fully authored.

## Generated Reference Gallery

To build actual synthetic reference decks for every loadable preset:

```bash
python3 scripts/build_style_reference_gallery.py \
  --outdir decks/style-reference-gallery-20260620 \
  --build \
  --qa
```

To render slide images, the overall contact sheets, and one treatment-specific
contact sheet per required treatment key when LibreOffice rendering is
available:

```bash
python3 scripts/build_style_reference_gallery.py \
  --outdir decks/style-reference-gallery-20260620 \
  --build \
  --qa \
  --render
```

Use the generated decks as examples of the reference grammar, not as fixed
templates to clone. The useful artifact is the mapping from topic/preset to
content treatments, `style_reference_layout_playbook_v1`, slide-level
`treatment_key` values, content-recipe traces, and slide variants.
The gallery `summary.json` records slide counts, rendered image counts,
variant sequences, chart/table treatment sequences, treatment buckets,
renderer-treatment signatures, per-deck QA summaries, aggregate QA totals, the
rendered contact sheet paths, per-treatment contact-sheet paths, and a sibling
`release_evidence.json` with contact-sheet fingerprints, treatment slide
coverage, content-signature uniqueness, content-recipe signature coverage,
renderer-treatment coverage, deck-level visual-diversity hashes, and
per-treatment rendered visual signatures. The per-treatment section records
nonblank counts, deterministic quantized-thumbnail signatures, coarse layout
hash counts, and nearest layout pairs for every required treatment key, so a
release can show whether dashboards, tables, charts, figures, comparisons,
decisions, titles, and references are actually diverging in rendered output.
Dashboard examples are explicit `treatment_key: "dashboard"` slides even when
their renderer variant is `chart`, `table`, `lab-run-results`, `flow`,
`matrix`, or `standard`, so dashboards can behave like a clinical run ledger,
board chart workbench, console route, safety matrix, sparse editorial readout,
or ops worklist rather than collapsing into a shared stat-card page.
Rendered release evidence enforces a minimum unique coarse-layout count for
each treatment family; color-only or header-only differences should not satisfy
the release gate.
Use those fields as compact release evidence when comparing preset breadth or
auditing whether styles are actually diverging.

## Build-Time Resolution

`scripts/build_workspace.py` applies the selected preset's
`style_reference_layout_playbook_v1` while writing `build/outline_resolved.json`.
It is conservative: source `outline.json` remains unchanged, explicit authored
variants win, and only generic compatible slides are upgraded. For example, a
lab-report slide with `variant: "standard"`, `treatment_key: "table"`, and a
real table payload can resolve to `lab-run-results`; a chart treatment needs
chart data, and a scientific-figure treatment needs figure payloads. Each
resolved choice is recorded under slide-level
`resolved_treatments.style_reference_layout` and summarized in
`resolved_treatment_summary.style_reference_layout`.
Use `npm run check:style-reference-resolution` after changing this resolver,
the layout playbook variant maps, or generic-to-specific compatibility rules.
That smoke initializes every preset, builds the same generic evidence outline,
and verifies 13 unique resolved variant signatures in
`build/outline_resolved.json`.

## Current Implementation

- Catalog source: `scripts/style_reference_catalog.py`
- Source-intake manifest: `references/style_reference_sources.json`
- Source-intake validator: `scripts/style_reference_sources.py`
- Generated example decks: `scripts/build_style_reference_gallery.py`
- Preset bridge: `scripts/style_treatment_profiles.py`
- Design-contract prompt: `scripts/emit_design_contract_prompt.py`
- Contract applicator: `scripts/apply_design_contract.py`
- Outline-authoring prompt: `scripts/emit_outline_authoring_prompt.py`
- Outline-handoff applicator: `scripts/apply_outline_authoring_handoff.py`
- Build-time resolved outline: `scripts/build_workspace.py`
- Fast catalog/routing coverage check: `npm run check:style-reference`
- Fast all-preset starter check: `npm run check:style-reference-starters`
- Fast all-preset build-time resolution check: `npm run check:style-reference-resolution`
- Fast all-preset generated-gallery check: `npm run check:style-reference-gallery`
- Rendered release-evidence check: `npm run check:style-reference-release`
- Broader seeded treatment smoke: `npm run check:style-mix`
