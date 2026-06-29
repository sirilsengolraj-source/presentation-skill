# v0.8.0

This release packages `presentation-skill` as a Codex plugin marketplace entry
so people can install it from the Codex plugin browser instead of manually
copying a skill folder.

## What changed

- Added `.agents/plugins/marketplace.json` with a **Presentation Skill**
  marketplace entry.
- Added `plugins/presentation-skill/.codex-plugin/plugin.json` with public
  plugin metadata, screenshots, keywords, starter prompts, and MIT license
  metadata.
- Added a synced plugin skill snapshot under
  `plugins/presentation-skill/skills/presentation-skill`.
- Added `scripts/sync_plugin_snapshot.py` so future releases can refresh the
  plugin snapshot from the root skill deterministically.
- Updated README install docs with `codex plugin marketplace add` usage.

## Install

```bash
codex plugin marketplace add sirilsengolraj-source/presentation-skill --ref v0.8.0
```

Then open `/plugins` in Codex and install `presentation-skill` from the
**Presentation Skill** marketplace.

## Validation

- `python3 scripts/sync_plugin_snapshot.py`
- `python3 <plugin-creator>/scripts/validate_plugin.py plugins/presentation-skill`
- `python3 -m json.tool .agents/plugins/marketplace.json`
- `python3 -m json.tool agents/discovery.json`
- `npm run check:python`
- `npm run check:node`
