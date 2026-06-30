# Promotion Kit

Copy, trim, and post these snippets when sharing `presentation-skill`.

## Canonical Links

- Repository: <https://github.com/siril9/presentation-skill>
- Release: <https://github.com/siril9/presentation-skill/releases/tag/v0.8.0>
- Install:

```bash
codex plugin marketplace add siril9/presentation-skill --ref v0.8.0
```

Then open `/plugins` in Codex and install `presentation-skill` from the
**Presentation Skill** marketplace.

## One-Liner

MIT-licensed Codex plugin for source-first PowerPoint generation: agents write
`outline.json`, build editable `.pptx` decks, route style/content structure,
generate chart/table/figure artifacts, and run layout QA before delivery.

## Short Post

I built an MIT-licensed Codex plugin for generating PowerPoint decks from
structured JSON.

The idea is to treat a deck like code: `outline.json` is the source, a script
builds the editable `.pptx`, and a QA loop checks geometry, rendered slides,
placeholder text, readable type sizes, and reproducibility.

It includes 13 slide variants, 13 style families, a descriptor-only style atom
corpus, chart/table/figure artifact workflows, and workspace mode for decks you
need to rebuild later.

Install:

```bash
codex plugin marketplace add siril9/presentation-skill --ref v0.8.0
```

Repo and release:
<https://github.com/siril9/presentation-skill>
<https://github.com/siril9/presentation-skill/releases/tag/v0.8.0>

I am looking for feedback from people who build lab reports, board decks,
clinical summaries, investor updates, or agent-generated documents.

## Hacker News

Title:

```text
Show HN: A Codex plugin for source-first PowerPoint generation
```

Body:

```text
I built an MIT-licensed Codex plugin for generating PowerPoint decks from structured JSON.

The idea is to treat a deck like code: outline.json is the source, a script builds the editable .pptx, and a validation loop checks layout geometry, rendered slide images, placeholder text, readable type sizes, and reproducibility.

It ships with 13 slide variants, 13 style families, descriptor-only style atoms, chart/table/figure artifact workflows, and workspace mode for decks you need to rebuild later.

Install:
codex plugin marketplace add siril9/presentation-skill --ref v0.8.0

Release evidence includes renderer/style proof boards and Codex-native vs updated-skill comparisons:
https://github.com/siril9/presentation-skill/releases/tag/v0.8.0

I am mostly looking for feedback on whether source-first / QA-loop workflows are useful for agent-built documents, and what would make generated decks feel closer to strong human-designed consulting, lab, or report decks.
```

## OpenAI Developer Community

```text
I released presentation-skill, an MIT-licensed Codex plugin for source-first PowerPoint/PPTX generation.

It packages a reusable agent workflow: write outline.json, build an editable pptxgenjs deck, choose a preset/style route, generate chart/table/figure artifacts where useful, and run geometry/render/placeholder/readability QA before delivery.

Install:
codex plugin marketplace add siril9/presentation-skill --ref v0.8.0

Repo:
https://github.com/siril9/presentation-skill

I would like feedback from Codex users on two things:
1. Whether plugin-packaged document-generation workflows are useful.
2. What constraints or examples would make agent-built decks feel more like thoughtful human-designed work.
```

## Reddit / Discord

```text
I open-sourced a Codex plugin for generating editable PowerPoint decks from structured JSON.

It treats a deck like source code: outline.json -> pptxgenjs -> editable .pptx -> QA checks. It includes slide variants, style families, generated charts/tables/figures, and reproducible workspace mode.

Install:
codex plugin marketplace add siril9/presentation-skill --ref v0.8.0

Repo:
https://github.com/siril9/presentation-skill

Useful feedback: where the generated decks still feel like AI output, which styles are missing, and what real workflows need stronger data/artifact handling.
```

## X / LinkedIn

```text
I released presentation-skill: an MIT-licensed Codex plugin for source-first PowerPoint generation.

outline.json -> editable .pptx -> layout/render/readability QA.

13 slide variants, 13 style families, chart/table/figure artifacts, and reproducible workspace mode.

Install:
codex plugin marketplace add siril9/presentation-skill --ref v0.8.0

https://github.com/siril9/presentation-skill
```

## OpenAI Curation Request

Use this in Codex `/feedback` or an OpenAI developer/community channel.

```text
I would like to submit presentation-skill for consideration as a globally discoverable Codex plugin.

Repository:
https://github.com/siril9/presentation-skill

Release:
https://github.com/siril9/presentation-skill/releases/tag/v0.8.0

Install:
codex plugin marketplace add siril9/presentation-skill --ref v0.8.0

It is an MIT-licensed plugin for source-first PowerPoint/PPTX generation. It bundles a reusable skill workflow for editable deck generation from outline.json, pptxgenjs rendering, style/content routing, data artifact creation, and QA checks for geometry, rendered slides, placeholder text, readability, and reproducibility.

The repository includes proof-board images, release evidence, a plugin manifest, repo marketplace metadata, and validation commands. I would appreciate guidance on any requirements for inclusion in the public/curated Codex plugin directory.
```

## Workspace Share Message

```text
I shared presentation-skill with you in Codex.

It is a plugin for building editable PowerPoint decks from structured JSON with chart/table/figure artifacts and layout QA.

Try:
Use presentation-skill to build a 7-slide editable PowerPoint deck on remote spirometry follow-up. Include one chart, one decision table, and run QA before delivery.
```

## Posting Checklist

- Include the install command.
- Link to the release, not only the repo.
- Include one proof-board image when the platform supports images.
- Ask for specific feedback: style misses, real workflows, chart/table/figure gaps.
- Do not claim it is in the global Codex plugin directory unless OpenAI curates it.
