# Discovery and Adoption Kit

This file is the compact share and routing layer for people, coding agents,
and directories that need to understand what `presentation-skill` is without
reading the full skill contract.

## One-Line Description

Source-first PowerPoint generation for Codex, ChatGPT, and OpenAI-style agents:
write `outline.json`, build editable `.pptx` decks with scripts, and run layout
QA before delivery.

## Short Description

`presentation-skill` treats a deck like code. It gives agents a structured
PowerPoint workflow with 13 slide variants, 13 style families, descriptor-only
style atoms, generated chart/table/figure artifacts, saved workspaces, and a
QA loop for geometry, visual review, readability, placeholder text, and
reproducibility.

## Best Search Phrases

- Codex PowerPoint skill
- ChatGPT PowerPoint skill
- OpenAI agent presentation generator
- source-first PPTX generator
- editable PowerPoint deck generator for agents
- pptxgenjs slide deck skill
- agent-built presentation QA
- lab report PowerPoint generator
- scientific figure slide deck generator
- investor deck generator with QA
- board memo slide deck generator
- presentation workspace for agents

## Agent Trigger Phrases

Use this skill when a user asks for:

- a PowerPoint, PPTX, slide deck, presentation, pitch deck, board deck, or report deck
- a lab report, clinical summary, scientific figure deck, or data-heavy results deck
- a deck generated from JSON, CSV, Excel, local data, charts, tables, or figures
- redesign, rebuild, layout QA, readability QA, or before/after comparison of a deck
- a reusable workspace that can be rebuilt later

Do not use it for pure text brainstorming when no deck artifact is needed.

## What Makes It Different

- The deck source is editable JSON, not hidden one-off drawing code.
- The renderer has actual slide grammars: title, section, cards, split,
  timeline, stats, KPI, comparison, matrix, chart, lab results, scientific
  figure, and Mermaid flow.
- Presets change structure and evidence posture, not only color.
- Style context comes from descriptor-only records and composable atoms, not
  bundled proprietary slide screenshots.
- Generated data artifacts can produce slide-ready figures, editable chart
  JSON, and compact summary tables from local data.
- QA is part of the workflow, with geometry checks, visual-review prompts, and
  placeholder-text detection.

## Proof Links

- README variant proof board:
  `decks/native-vs-latest-random-topics-20260623/readme_images/presentation_skill_variant_proof.png`
- README style-family proof board:
  `decks/native-vs-latest-random-topics-20260623/readme_images/presentation_skill_style_family_proof.png`
- Codex-native vs updated comparison:
  `decks/native-vs-latest-random-topics-20260623/readme_images/codex_native_vs_updated_clean_three_topics.png`
- Latest release evidence:
  <https://github.com/siril9/presentation-skill/releases/tag/v0.8.0>

## Example Prompts

```text
Use presentation-skill to build a 7-slide editable PowerPoint deck on remote
spirometry follow-up. Treat outline.json as source, choose a clinical/report
preset, include at least one chart and one decision table, and run QA.
```

```text
Use presentation-skill to create a lab-style PPTX from this CSV. Generate a
figure, an editable chart, and a compact summary table. Keep sources in
footer-safe text and make the deck rebuildable next month.
```

```text
Use presentation-skill to redesign this investor update as a source-first deck.
Avoid generic card grids, use KPI and comparison slides only where the story
needs them, and verify readable text sizes before delivery.
```

## Shareable Blurb

I built an MIT-licensed Codex/ChatGPT presentation skill that treats
PowerPoint decks like source code: `outline.json` is the source, scripts build
editable `.pptx`, and QA checks layout, visual issues, placeholder text, and
reproducibility. It ships with 13 slide variants, 13 style families, generated
chart/table/figure artifacts, descriptor-only style atoms, and reusable
workspaces.

## Adoption Checklist

- README first screen shows real slide-range evidence.
- GitHub topics include Codex, ChatGPT, PPTX, PowerPoint, and agent terms.
- `package.json` keywords cover human and package-search discovery.
- `SKILL.md` frontmatter includes aliases for fuzzy agent matching.
- `agents/openai.yaml` and `agents/discovery.json` give agent-readable routing.
- Release assets include proof boards and before/after comparisons.
- Issue templates collect real deck-quality feedback from users.
- The Codex plugin marketplace lives at `.agents/plugins/marketplace.json`
  and exposes `plugins/presentation-skill`.
- `docs/PROMOTION.md` contains copy-ready posts and a curation request.
