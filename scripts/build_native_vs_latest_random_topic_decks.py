#!/usr/bin/env python3
"""Build Codex native vs latest presentation-skill random-topic evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageStat
except Exception:  # pragma: no cover - visual artifact dependency
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]

import build_random_topic_comparison_decks as random_builder
from design_catalog_selector import DESIGN_CATALOG_VERSION, RANDOM_SEED, RELEASE_VERSION, design_catalog_summary


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTDIR = ROOT / "decks" / "native-vs-latest-random-topics-20260623"
NATIVE_NODE = Path("/Users/sirilarockiam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")


NATIVE_JS = r"""
import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

async function writeBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function addText(slide, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = style;
  return shape;
}

function addBox(slide, position, fill = "white", line = "slate-200") {
  return slide.shapes.add({
    geometry: "roundRect",
    position,
    fill,
    line: { style: "solid", fill: line, width: 1 },
    borderRadius: "rounded-lg",
    shadow: "shadow-sm",
  });
}

function addFooter(slide, text, pageNo) {
  addText(slide, text, { left: 72, top: 676, width: 700, height: 24 }, { fontSize: 11, color: "slate-500" });
  addText(slide, pageNo, { left: 1130, top: 676, width: 80, height: 24 }, { fontSize: 11, color: "slate-500" });
}

function metricCards(slide, metrics, accent, dark) {
  const count = metrics.length;
  const gutter = 38;
  const cardWidth = count <= 2 ? 460 : 320;
  const totalWidth = cardWidth * count + gutter * Math.max(0, count - 1);
  const startX = Math.max(72, (1280 - totalWidth) / 2);
  for (let i = 0; i < metrics.length; i++) {
    const metric = metrics[i];
    const x = startX + i * (cardWidth + gutter);
    addBox(slide, { left: x, top: 188, width: cardWidth, height: 230 }, "slate-50", "slate-200");
    addText(slide, metric[0], { left: x + 28, top: 222, width: cardWidth - 56, height: 70 }, { fontSize: 45, bold: true, color: accent });
    addText(slide, metric[1], { left: x + 28, top: 306, width: cardWidth - 56, height: 38 }, { fontSize: 22, bold: true, color: dark });
    addText(slide, metric[2], { left: x + 28, top: 352, width: cardWidth - 56, height: 46 }, { fontSize: 16, color: "slate-600" });
  }
}

function buildDeck(caseSpec) {
  const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  const page = { left: 72, top: 58, width: 1136, height: 604 };
  const accent = caseSpec.accent || "teal-600";
  const dark = caseSpec.dark || "slate-950";

  {
    const slide = deck.slides.add();
    slide.background.fill = caseSpec.bg || "slate-50";
    addText(slide, "CODEX NATIVE BASELINE", { left: page.left, top: page.top, width: 330, height: 32 }, { fontSize: 13, bold: true, color: "slate-500" });
    addText(slide, caseSpec.title, { left: page.left, top: 165, width: 780, height: 135 }, { fontSize: 52, bold: true, color: dark });
    addText(slide, caseSpec.subtitle, { left: page.left, top: 315, width: 780, height: 68 }, { fontSize: 22, color: "slate-600" });
    addBox(slide, { left: 862, top: 152, width: 276, height: 276 }, "white", "slate-200");
    addText(slide, "editable objects\nsimple layout\nno corpus router", { left: 900, top: 226, width: 210, height: 130 }, { fontSize: 24, bold: true, color: accent });
    addFooter(slide, "Bundled Codex Presentations skill baseline", "1/4");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = "white";
    addText(slide, caseSpec.key_title, { left: page.left, top: 58, width: 1040, height: 84 }, { fontSize: 35, bold: true, color: dark });
    addText(slide, caseSpec.key_subtitle, { left: page.left, top: 148, width: 1040, height: 42 }, { fontSize: 18, color: "slate-600" });
    addBox(slide, { left: page.left, top: 230, width: 510, height: 250 }, "slate-50", "slate-200");
    addBox(slide, { left: 698, top: 230, width: 510, height: 250 }, "slate-50", "slate-200");
    addText(slide, caseSpec.left_title, { left: 108, top: 262, width: 430, height: 36 }, { fontSize: 25, bold: true, color: dark });
    addText(slide, caseSpec.left_body.map((x) => `- ${x}`).join("\n"), { left: 108, top: 314, width: 420, height: 120 }, { fontSize: 18, color: "slate-700" });
    addText(slide, caseSpec.right_title, { left: 734, top: 262, width: 430, height: 36 }, { fontSize: 25, bold: true, color: accent });
    addText(slide, caseSpec.right_body.map((x) => `- ${x}`).join("\n"), { left: 734, top: 314, width: 420, height: 120 }, { fontSize: 18, color: "slate-700" });
    const verdict = slide.shapes.add({ geometry: "rect", position: { left: 160, top: 536, width: 960, height: 54 }, fill: dark, line: { style: "solid", fill: dark, width: 0 } });
    verdict.text = caseSpec.verdict;
    verdict.text.style = { fontSize: 18, bold: true, color: "white" };
    addFooter(slide, "Synthetic comparison fixture", "2/4");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = "white";
    addText(slide, "Metrics that should stay readable", { left: page.left, top: 58, width: 950, height: 70 }, { fontSize: 36, bold: true, color: dark });
    addText(slide, "Native baseline uses KPI cards rather than corpus-selected chart/table grammar.", { left: page.left, top: 124, width: 930, height: 38 }, { fontSize: 18, color: "slate-600" });
    metricCards(slide, caseSpec.metrics, accent, dark);
    addFooter(slide, "Native metric-card layout", "3/4");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = "white";
    addText(slide, "Decision table keeps the next step explicit", { left: page.left, top: 58, width: 1040, height: 66 }, { fontSize: 35, bold: true, color: dark });
    const colX = [82, 430, 820];
    const widths = [300, 340, 300];
    const headers = ["Choice", "Scope", "Call"];
    for (let i = 0; i < headers.length; i++) {
      addText(slide, headers[i], { left: colX[i], top: 168, width: widths[i], height: 34 }, { fontSize: 18, bold: true, color: accent });
    }
    for (let r = 0; r < caseSpec.decision_rows.length; r++) {
      const y = 226 + r * 88;
      addBox(slide, { left: 72, top: y - 10, width: 1136, height: 68 }, r % 2 === 0 ? "slate-50" : "white", "slate-200");
      for (let c = 0; c < 3; c++) {
        addText(slide, caseSpec.decision_rows[r][c], { left: colX[c], top: y, width: widths[c], height: 48 }, { fontSize: 17, color: c === 0 ? dark : "slate-700", bold: c === 0 });
      }
    }
    addFooter(slide, "Native editable table approximation", "4/4");
  }

  return deck;
}

async function main() {
  const specPath = process.argv[2];
  const cases = JSON.parse(await fs.readFile(specPath, "utf8"));
  for (const caseSpec of cases) {
    const outDir = caseSpec.native_dir;
    await fs.mkdir(outDir, { recursive: true });
    const deck = buildDeck(caseSpec);
    for (const [index, slide] of deck.slides.items.entries()) {
      const stem = `slide-${String(index + 1).padStart(2, "0")}`;
      const png = await deck.export({ slide, format: "png", scale: 1 });
      await writeBlob(path.join(outDir, "renders", `${stem}.png`), png);
      const layout = await slide.export({ format: "layout" });
      await fs.writeFile(path.join(outDir, "renders", `${stem}.layout.json`), await layout.text());
    }
    const pptx = await PresentationFile.exportPptx(deck);
    await pptx.save(path.join(outDir, `${caseSpec.slug}-codex-native.pptx`));
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
"""


def _run(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, Any]:
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    if result.stdout:
        print(result.stdout, end="")
    return {
        "command": cmd,
        "returncode": result.returncode,
        "stdout_tail": (result.stdout or "")[-2400:],
    }


def _run_checked(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, Any]:
    entry = _run(cmd, cwd=cwd, env=env)
    if entry["returncode"] != 0:
        raise RuntimeError(f"command failed ({entry['returncode']}): {' '.join(cmd)}")
    return entry


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fingerprint(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _native_skill_dir() -> Path:
    base = Path.home() / ".codex" / "plugins" / "cache" / "openai-primary-runtime" / "presentations"
    candidates = sorted(base.glob("*/skills/presentations"), key=lambda item: item.parts[-3])
    if not candidates:
        raise RuntimeError(f"could not find bundled Presentations skill under {base}")
    return candidates[-1]


def _node_bin() -> str:
    if NATIVE_NODE.exists():
        return str(NATIVE_NODE)
    found = shutil.which("node")
    if not found:
        raise RuntimeError("node is required to run the bundled native presentation builder")
    return found


def _metric_specs(topic: dict[str, Any]) -> list[list[str]]:
    values = topic["chart_values"]
    labels = topic["chart_categories"]
    metrics = [
        [str(max(values)), "Peak index", labels[values.index(max(values))]],
        [str(min(values)), "Low index", labels[values.index(min(values))]],
        [str(len(topic["table_rows"])), "Rows", "Decision/evidence table"],
    ]
    return metrics


def _native_case_spec(topic: dict[str, Any], native_dir: Path) -> dict[str, Any]:
    palette = topic["palette"]
    return {
        "slug": topic["slug"],
        "title": topic["title"],
        "subtitle": topic["subtitle"],
        "short": topic["topic_type"],
        "key_title": f"{topic['topic_type'].title()} needs a clear operating readout",
        "key_subtitle": "Same synthetic topic; this arm uses the bundled Codex presentation baseline.",
        "left_title": topic["left_title"],
        "left_body": topic["left_body"],
        "right_title": topic["right_title"],
        "right_body": topic["right_body"],
        "verdict": "Baseline is editable and useful, but intentionally does not use the corpus router.",
        "metrics": _metric_specs(topic),
        "decision_rows": [row[:3] for row in topic["decision_rows"][:3]],
        "accent": palette[1],
        "dark": "#111827",
        "bg": "#F8FAFC",
        "native_dir": str(native_dir),
    }


def _build_native_decks(topics: list[dict[str, Any]], outdir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    skill_dir = _native_skill_dir()
    node = _node_bin()
    scratch = Path(tempfile.mkdtemp(prefix="native-vs-latest-codex-"))
    setup = skill_dir / "container_tools" / "setup_artifact_tool_workspace.mjs"
    setup_result = _run_checked([node, str(setup), "--workspace", str(scratch)], cwd=ROOT)
    spec_path = scratch / "native_topic_specs.json"
    script_path = scratch / "build_native_topics.mjs"
    specs = [_native_case_spec(topic, outdir / "cases" / topic["slug"] / "native-codex") for topic in topics]
    _write_json(spec_path, specs)
    script_path.write_text(NATIVE_JS, encoding="utf-8")
    build_result = _run_checked([node, str(script_path), str(spec_path)], cwd=scratch)

    records: list[dict[str, Any]] = []
    for topic in topics:
        native_dir = outdir / "cases" / topic["slug"] / "native-codex"
        pptx = native_dir / f"{topic['slug']}-codex-native.pptx"
        render_paths = sorted((native_dir / "renders").glob("slide-*.png"))
        records.append(
            {
                "topic_slug": topic["slug"],
                "topic_title": topic["title"],
                "mode": "native-codex",
                "comparison_arm": "codex_native_skill",
                "label": "Codex native skill",
                "workspace": str(native_dir),
                "pptx": str(pptx),
                "pptx_fingerprint": _fingerprint(pptx),
                "renders_dir": str(native_dir / "renders"),
                "render_paths": [str(path) for path in render_paths],
                "render_count": len(render_paths),
                "native_skill_dir": str(skill_dir),
                "native_builder": "OpenAI bundled Presentations skill via @oai/artifact-tool",
                "notes": "Generated by a deterministic script following the bundled native skill's artifact-tool route.",
            }
        )
    return records, {"setup": setup_result, "build": build_result, "scratch": str(scratch), "skill_dir": str(skill_dir)}


def _patch_random_builder_outdir(outdir: Path) -> None:
    try:
        random_builder.RELEASE_EVIDENCE_DIR = str(outdir.relative_to(ROOT))
    except ValueError:
        random_builder.RELEASE_EVIDENCE_DIR = str(outdir)


def _build_latest_decks(topics: list[dict[str, Any]], outdir: Path) -> list[dict[str, Any]]:
    _patch_random_builder_outdir(outdir)
    records: list[dict[str, Any]] = []
    for topic in topics:
        record = random_builder._build_workspace(topic, mode="corpus", outdir=outdir)  # noqa: SLF001
        record["comparison_arm"] = "presentation_skill_latest"
        record["label"] = f"presentation-skill v{RELEASE_VERSION}"
        record["notes"] = "Generated by the latest corpus-routed presentation-skill builder."
        records.append(record)
    return records


def _nonblank_image(path: Path) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {"path": str(path), "nonblank": False, "reason": "pillow_unavailable"}
    image = Image.open(path).convert("L")
    extrema = ImageStat.Stat(image).extrema[0]
    return {"path": str(path), "size": list(image.size), "luma_extrema": list(extrema), "nonblank": extrema[1] - extrema[0] > 10}


def _build_pair_sheet(topic: dict[str, Any], native: dict[str, Any], latest: dict[str, Any], outdir: Path) -> dict[str, Any]:
    if Image is None or ImageDraw is None or ImageStat is None:
        raise RuntimeError("Pillow is required to build contact sheets")
    thumb_size = (440, 248)
    slide_count = max(len(native["render_paths"]), len(latest["render_paths"]))
    row_height = 306
    header_height = 185
    width = 1160
    height = header_height + slide_count * row_height + 72
    image = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(image)
    draw.text((46, 32), topic["title"], fill="#111827", font=random_builder._font(31, bold=True))  # noqa: SLF001
    draw.text(
        (48, 76),
        "Left: Codex native skill. Right: latest presentation-skill corpus router.",
        fill="#4B5563",
        font=random_builder._font(17),  # noqa: SLF001
    )
    left_x, right_x = 154, 654
    draw.text((left_x, 132), "Codex native skill", fill="#111827", font=random_builder._font(21, bold=True))  # noqa: SLF001
    draw.text((right_x, 132), f"presentation-skill v{RELEASE_VERSION}", fill="#111827", font=random_builder._font(21, bold=True))  # noqa: SLF001
    draw.text((right_x, 158), topic["corpus_family"], fill="#4B5563", font=random_builder._font(14))  # noqa: SLF001
    for idx in range(slide_count):
        row_y = header_height + idx * row_height
        draw.text((46, row_y + 100), f"S{idx + 1}", fill="#64748B", font=random_builder._font(18, bold=True))  # noqa: SLF001
        for x, record in ((left_x, native), (right_x, latest)):
            if idx < len(record["render_paths"]):
                thumb = random_builder._thumb(Path(record["render_paths"][idx]), thumb_size)  # noqa: SLF001
                image.paste(thumb, (x, row_y))
            else:
                draw.rectangle((x, row_y, x + thumb_size[0], row_y + thumb_size[1]), fill="#EEF2F7")
                draw.text((x + 132, row_y + 108), "No slide", fill="#94A3B8", font=random_builder._font(20, bold=True))  # noqa: SLF001
            draw.rectangle((x, row_y, x + thumb_size[0], row_y + thumb_size[1]), outline="#CBD5E1", width=2)
    draw.text(
        (46, height - 44),
        "Latest arm records descriptor-only corpus context; no external source decks, screenshots, logos, copied text, or copied geometry are bundled.",
        fill="#6B7280",
        font=random_builder._font(13),  # noqa: SLF001
    )
    path = outdir / "contact_sheets" / f"{topic['slug']}_codex_native_vs_latest.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    stat = ImageStat.Stat(image.convert("L"))
    return {
        "topic_slug": topic["slug"],
        "path": str(path),
        "size": list(image.size),
        "luma_extrema": list(stat.extrema[0]),
        "nonblank": bool(stat.extrema[0][1] - stat.extrema[0][0] > 10),
    }


def _build_topic_preview_sheet(topic: dict[str, Any], native: dict[str, Any], latest: dict[str, Any], outdir: Path) -> dict[str, Any]:
    if Image is None or ImageDraw is None or ImageStat is None:
        raise RuntimeError("Pillow is required to build contact sheets")
    thumb_size = (520, 293)
    width = 1240
    height = 610
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw.text((42, 32), topic["title"], fill="#111827", font=random_builder._font(31, bold=True))  # noqa: SLF001
    draw.text(
        (44, 76),
        "Same topic, one representative content slide from each generator.",
        fill="#4B5563",
        font=random_builder._font(17),  # noqa: SLF001
    )
    left_x, right_x = 74, 646
    y = 160
    draw.text((left_x, 124), "Codex native skill", fill="#111827", font=random_builder._font(21, bold=True))  # noqa: SLF001
    draw.text((right_x, 124), f"presentation-skill v{RELEASE_VERSION}", fill="#111827", font=random_builder._font(21, bold=True))  # noqa: SLF001
    draw.text((right_x, 150), topic["corpus_family"], fill="#64748B", font=random_builder._font(14))  # noqa: SLF001
    native_paths = native["render_paths"]
    latest_paths = latest["render_paths"]
    samples = [
        (left_x, native_paths[1] if len(native_paths) > 1 else native_paths[0]),
        (right_x, latest_paths[1] if len(latest_paths) > 1 else latest_paths[0]),
    ]
    for x, path_value in samples:
        thumb = random_builder._thumb(Path(path_value), thumb_size)  # noqa: SLF001
        image.paste(thumb, (x, y))
        draw.rectangle((x, y, x + thumb_size[0], y + thumb_size[1]), outline="#CBD5E1", width=2)
    draw.text(
        (74, 482),
        "Native baseline: simple editable artifact-tool composition.",
        fill="#374151",
        font=random_builder._font(16),  # noqa: SLF001
    )
    draw.text(
        (646, 482),
        "Latest skill: descriptor-corpus route plus preset-specific content grammar.",
        fill="#374151",
        font=random_builder._font(16),  # noqa: SLF001
    )
    draw.text(
        (74, 538),
        "Full six-row evidence sheet for this topic is saved alongside this preview.",
        fill="#6B7280",
        font=random_builder._font(13),  # noqa: SLF001
    )
    path = outdir / "contact_sheets" / f"{topic['slug']}_codex_native_vs_latest_preview.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    stat = ImageStat.Stat(image.convert("L"))
    return {
        "topic_slug": topic["slug"],
        "path": str(path),
        "size": list(image.size),
        "luma_extrema": list(stat.extrema[0]),
        "nonblank": bool(stat.extrema[0][1] - stat.extrema[0][0] > 10),
    }


def _build_overview_sheet(topics: list[dict[str, Any]], native_records: list[dict[str, Any]], latest_records: list[dict[str, Any]], outdir: Path) -> dict[str, Any]:
    if Image is None or ImageDraw is None or ImageStat is None:
        raise RuntimeError("Pillow is required to build contact sheets")
    by_native = {record["topic_slug"]: record for record in native_records}
    by_latest = {record["topic_slug"]: record for record in latest_records}
    thumb_size = (410, 231)
    row_height = 286
    header_height = 178
    width = 1320
    height = header_height + len(topics) * row_height + 190
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw.text((54, 36), "Codex Native vs Latest Presentation Skill", fill="#111827", font=random_builder._font(39, bold=True))  # noqa: SLF001
    draw.text(
        (56, 92),
        f"Same {len(topics)} random topics. Left column: native Codex baseline. Right column: corpus-routed presentation-skill v{RELEASE_VERSION}.",
        fill="#4B5563",
        font=random_builder._font(18),  # noqa: SLF001
    )
    left_x, right_x = 356, 832
    draw.text((left_x, 142), "Codex native skill", fill="#111827", font=random_builder._font(22, bold=True))  # noqa: SLF001
    draw.text((right_x, 142), f"presentation-skill v{RELEASE_VERSION}", fill="#111827", font=random_builder._font(22, bold=True))  # noqa: SLF001
    for idx, topic in enumerate(topics):
        y = header_height + idx * row_height
        random_builder._draw_label(  # noqa: SLF001
            draw,
            (56, y + 38),
            topic["title"],
            width=245,
            font=random_builder._font(20, bold=True),  # noqa: SLF001
            fill="#111827",
        )
        draw.text((56, y + 116), topic["corpus_family"], fill="#64748B", font=random_builder._font(15))  # noqa: SLF001
        native_paths = by_native[topic["slug"]]["render_paths"]
        latest_paths = by_latest[topic["slug"]]["render_paths"]
        samples = [
            (left_x, native_paths[1] if len(native_paths) > 1 else native_paths[0]),
            (right_x, latest_paths[1] if len(latest_paths) > 1 else latest_paths[0]),
        ]
        for x, path_value in samples:
            thumb = random_builder._thumb(Path(path_value), thumb_size)  # noqa: SLF001
            image.paste(thumb, (x, y))
            draw.rectangle((x, y, x + thumb_size[0], y + thumb_size[1]), outline="#CBD5E1", width=2)
        draw.line((54, y + row_height - 24, width - 54, y + row_height - 24), fill="#E5E7EB", width=1)
    y2 = header_height + len(topics) * row_height + 24
    draw.text((56, y2), "Evidence scope", fill="#111827", font=random_builder._font(27, bold=True))  # noqa: SLF001
    lines = [
        f"Decks built: {len(native_records) + len(latest_records)} plus one gallery deck",
        f"Latest corpus-routed cases: {len(latest_records)} / {len(topics)}",
        f"Outlines with 2,000-record corpus context: {sum(1 for item in latest_records if item.get('outline_large_corpus_context_present'))} / {len(topics)}",
        "Native arm uses the bundled Presentations artifact-tool route; latest arm uses this repo's corpus router and preset system.",
        "All topics and data are synthetic; corpus storage is descriptor-only.",
    ]
    yy = y2 + 43
    for line in lines:
        draw.text((76, yy), f"- {line}", fill="#374151", font=random_builder._font(18))  # noqa: SLF001
        yy += 29
    path = outdir / "contact_sheets" / "all_topics_codex_native_vs_latest.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    stat = ImageStat.Stat(image.convert("L"))
    return {
        "path": str(path),
        "size": list(image.size),
        "luma_extrema": list(stat.extrema[0]),
        "nonblank": bool(stat.extrema[0][1] - stat.extrema[0][0] > 10),
    }


def _build_gallery_deck(outdir: Path, overview_sheet: dict[str, Any], preview_sheets: list[dict[str, Any]]) -> dict[str, Any]:
    workspace = outdir / "comparison-gallery"
    builder_script = str((ROOT / "scripts" / "build_native_vs_latest_random_topic_decks.py").resolve())
    _run_checked(
        [
            sys.executable,
            str(ROOT / "scripts" / "init_deck_workspace.py"),
            "--workspace",
            str(workspace),
            "--title",
            "Codex Native vs Latest Presentation Skill",
            "--style-preset",
            "editorial-minimal",
            "--overwrite",
            "--user-prompt",
            "gallery deck comparing Codex native skill output to latest presentation-skill corpus-routed output",
        ]
    )
    asset_dir = workspace / "assets" / "comparisons"
    asset_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    for source in [overview_sheet["path"], *[item["path"] for item in preview_sheets]]:
        src = Path(source)
        dest = asset_dir / src.name
        shutil.copy2(src, dest)
        copied.append({"source": str(src), "relative": str(dest.relative_to(workspace))})
    slides: list[dict[str, Any]] = [
        {
            "slide_id": "s1",
            "type": "title",
            "title": "Codex Native vs Latest Presentation Skill",
            "subtitle": f"Eight random topics built two ways: bundled native baseline vs presentation-skill v{RELEASE_VERSION}",
        },
        {
            "slide_id": "s2",
            "type": "content",
            "variant": "image-sidebar",
            "title": "All topics at a glance",
            "assets": {"hero_image": copied[0]["relative"]},
            "caption": "Left column is the bundled Codex native baseline; right column is the corpus-routed presentation-skill output.",
            "sidebar_sections": [
                {"title": "Scope", "body": "Same eight synthetic random topics generated through two reproducible paths."},
                {"title": "Latest arm", "body": "Uses descriptor corpus, preset routing, generated data artifacts, and style contracts."},
                {"title": "Native arm", "body": "Uses the bundled Presentations artifact-tool route as a simple baseline."},
            ],
            "sources": ["Local comparison builder"],
        },
    ]
    for idx, item in enumerate(copied[1:], start=3):
        title = Path(item["relative"]).stem.replace("_codex_native_vs_latest_preview", "").replace("-", " ").replace("_", " ").title()
        slides.append(
            {
                "slide_id": f"s{idx}",
                "type": "content",
                "variant": "image-sidebar",
                "title": title,
                "assets": {"hero_image": item["relative"]},
                "caption": "Left column: Codex native skill. Right column: latest presentation-skill corpus route.",
                "sidebar_sections": [
                    {"title": "Inspect", "body": "Compare hierarchy, figure/table treatment, footer/source handling, and structure rhythm."},
                    {"title": "Caveat", "body": "This is a deterministic native baseline, not a human-tuned native deck."},
                ],
                "sources": ["Local comparison builder"],
            }
        )
    _write_json(
        workspace / "outline.json",
        {
            "title": "Codex Native vs Latest Presentation Skill",
            "subtitle": "Rendered comparison evidence",
            "deck_style": {
                "visual_density": "medium",
                "style_seed": "native-vs-latest-random-topics",
                "footer_page_numbers": True,
            },
            "slides": slides,
        },
    )
    _write_json(
        workspace / "design_brief.json",
        {
            "topic": "Codex Native vs Latest Presentation Skill",
            "content_maturity": "technical/educational",
            "audience_posture": "coworkers/operators",
            "format_promise": "Compact gallery deck that embeds rendered native-vs-latest comparison sheets.",
            "design_dna": "editorial report",
            "style_system": {"style_preset": "editorial-minimal", "style_seed": "native-vs-latest-random-topics"},
            "readability_contract": {
                "min_title_pt": 26,
                "min_body_pt": 12,
                "min_caption_pt": 7.5,
                "chart_label_min_pt": 7,
                "min_chart_label_pt": 7,
                "footer_reserved_inches": 0.28,
                "max_title_lines": 2,
                "max_slide_words": 90,
                "max_slide_chars": 620,
                "table_density_rule": "No dense tables in the gallery; use rendered contact sheets as the evidence object.",
                "whitespace_rule": "Keep contact sheets large and use sidebars only for short inspection notes.",
                "figure_crop_rule": "Use generated contact sheets without exterior whitespace or decorative cropping.",
            },
            "title_page_concept": {
                "chosen_archetype": "comparison gallery opener",
                "dominant_element": "Codex native vs latest",
                "supporting_element": "Eight random topic comparison",
                "why_this_could_only_be_this_deck": "It shows the exact evidence gallery generated by the native-vs-latest builder.",
            },
            "structure_strategy": {
                "primary_scaffold": "title, overview sheet, one pair sheet per topic",
                "repeated_elements": ["image-sidebar contact sheet slides", "short inspection sidebar", "local source footer"],
                "allowed_variations": ["image-sidebar"],
                "container_policy": "Let rendered sheets be the primary objects; keep text secondary.",
                "rhythm_break_plan": "The overview sheet starts broad; each following slide zooms into one topic pair.",
            },
            "analysis_artifact_plan": {
                "candidate_data_files": [],
                "required_scripts": [builder_script],
                "figure_scripts": [builder_script],
                "artifact_registry": [
                    {
                        "id": Path(item["relative"]).stem,
                        "path": item["relative"],
                        "producer": builder_script,
                        "used_on_slides": [f"s{idx + 2}"],
                        "provenance": "Generated locally from rendered deck images.",
                    }
                    for idx, item in enumerate(copied)
                ],
                "rebuild_commands": [f"python3 {builder_script} --outdir {outdir} --overwrite"],
            },
            "speed_contract": {
                "renderer": "pptxgenjs",
                "first_pass": "Build gallery from existing rendered preview sheets.",
                "render_policy": "Render after the gallery deck is built for final inspection.",
                "asset_policy": "Use local generated contact sheets only.",
                "conversion_hint": "Use scripts/render_slides.py after build_workspace.py finishes.",
            },
            "qa_contract": {
                "required_checks": [
                    "python3 scripts/validate_planning.py --workspace <deck>",
                    "python3 scripts/build_workspace.py --workspace <deck> --qa --skip-render --overwrite",
                    "python3 scripts/report_delivery_readiness.py --workspace <deck> --allow-skip-render",
                ],
                "fail_on": ["planning_errors", "overflow", "overlap", "whitespace", "placeholder_text"],
                "placeholder_checks": True,
            },
            "acceptance_evidence": ["build/qa/report.json", "build/renders"],
            "agent_execution_plan": {
                "phases": [
                    {"id": "copy_preview_sheets", "owner": "script", "status": "complete"},
                    {"id": "build_gallery", "owner": "script", "status": "complete_after_build"},
                    {"id": "render_gallery", "owner": "script", "status": "complete_after_render"},
                ]
            },
        },
    )
    _write_json(
        workspace / "content_plan.json",
        {
            "thesis": "Rendered sheets make native-vs-latest differences inspectable.",
            "audience": "Skill-quality reviewers",
            "visual_strategy": "Use contact sheets as the evidence object and keep explanatory text brief.",
            "slide_plan": [
                {"slide_id": slide["slide_id"], "role": "comparison", "message": slide["title"], "variant": slide.get("variant", "title"), "visual_strategy": "rendered contact sheet"}
                for slide in slides
            ],
        },
    )
    _write_json(workspace / "evidence_plan.json", {"source_policy": "local_generated_evidence", "items": []})
    _write_json(
        workspace / "asset_plan.json",
        {
            "images": [
                {
                    "name": Path(item["relative"]).stem,
                    "path": item["relative"],
                    "purpose": "Rendered comparison evidence sheet for gallery deck",
                    "used_on_slides": [f"s{idx + 2}"],
                    "source": "Generated by scripts/build_native_vs_latest_random_topic_decks.py",
                    "source_note": "Local generated contact sheet from rendered deck images; no external asset.",
                    "license": "Original synthetic artifact for this repository",
                    "provenance": "scripts/build_native_vs_latest_random_topic_decks.py",
                }
                for idx, item in enumerate(copied)
            ],
            "charts": [],
            "tables": [],
            "backgrounds": [],
            "generated_images": [],
            "icons": [],
        },
    )
    (workspace / "notes.md").write_text(
        "# Codex Native vs Latest Presentation Skill\n\n"
        "Generated from local rendered sheets. External corpus sources are descriptor-only metadata.\n",
        encoding="utf-8",
    )
    _run_checked(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_workspace.py"),
            "--workspace",
            str(workspace),
            "--qa",
            "--skip-render",
            "--overwrite",
            "--renderer",
            "pptxgenjs",
        ]
    )
    style_contract = json.loads((workspace / "style_contract.json").read_text(encoding="utf-8"))
    pptx_path = workspace / style_contract["build"]["output_pptx"]
    render_dir = workspace / "build" / "renders"
    _run_checked(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_slides.py"),
            "--input",
            str(pptx_path),
            "--outdir",
            str(render_dir),
            "--format",
            "png",
        ]
    )
    return {
        "workspace": str(workspace),
        "pptx": str(pptx_path),
        "pptx_fingerprint": _fingerprint(pptx_path),
        "renders_dir": str(render_dir),
        "render_count": len(list(render_dir.glob("slide-*.png"))),
        "qa_summary": random_builder._qa_summary(workspace),  # noqa: SLF001
    }


def _write_notes(path: Path, manifest: dict[str, Any]) -> None:
    quality = manifest.get("quality") or {}

    def display(path_value: str) -> str:
        try:
            return str(Path(path_value).resolve().relative_to(ROOT))
        except ValueError:
            return path_value

    lines = [
        "# Codex Native vs Latest Presentation Skill",
        "",
        "Same 8 random synthetic topics, generated two ways.",
        "",
        "- Left column: bundled Codex native Presentations skill baseline generated through `@oai/artifact-tool`.",
        f"- Right column: `presentation-skill` v{RELEASE_VERSION}, routed through the descriptor corpus and preset system in this repo.",
        "- The latest arm uses descriptor-only corpus context, generated data artifacts where applicable, and topic-to-style routing.",
        "- The native arm is a deterministic baseline, not a human-tuned native deck.",
        "",
        "## Evidence",
        "",
        f"- Manifest: `{display(manifest['manifest_path'])}`",
        f"- Gallery deck: `{display(manifest['gallery_deck']['pptx'])}`",
        f"- Overview contact sheet: `{display(manifest['overview_contact_sheet']['path'])}`",
        "- Full pair contact sheets: `contact_sheets/*_codex_native_vs_latest.png`",
        "- Gallery preview sheets: `contact_sheets/*_codex_native_vs_latest_preview.png`",
        "",
        "## Snapshot",
        "",
        f"- Topics: `{manifest['topic_count']}`",
        f"- Decks: `{manifest['deck_count']}` plus one gallery deck",
        f"- Native decks rendered: `{quality.get('native_rendered_count')}` / `{manifest['topic_count']}`",
        f"- Latest decks rendered: `{quality.get('latest_rendered_count')}` / `{manifest['topic_count']}`",
        f"- Latest outlines with corpus context: `{quality.get('latest_corpus_context_count')}` / `{manifest['topic_count']}`",
        f"- Nonblank contact sheets: `{quality.get('nonblank_contact_sheet_count')}` / `{quality.get('contact_sheet_count')}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_native_vs_latest(outdir: Path, *, overwrite: bool = False) -> dict[str, Any]:
    outdir = outdir.expanduser().resolve()
    if outdir.exists() and overwrite:
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    topics = random_builder.TOPICS
    native_records, native_commands = _build_native_decks(topics, outdir)
    latest_records = _build_latest_decks(topics, outdir)
    by_native = {record["topic_slug"]: record for record in native_records}
    by_latest = {record["topic_slug"]: record for record in latest_records}
    pair_sheets = [
        _build_pair_sheet(topic, by_native[topic["slug"]], by_latest[topic["slug"]], outdir)
        for topic in topics
    ]
    preview_sheets = [
        _build_topic_preview_sheet(topic, by_native[topic["slug"]], by_latest[topic["slug"]], outdir)
        for topic in topics
    ]
    overview_sheet = _build_overview_sheet(topics, native_records, latest_records, outdir)
    gallery = _build_gallery_deck(outdir, overview_sheet, preview_sheets)
    contact_sheets = [overview_sheet, *pair_sheets, *preview_sheets]
    notes_path = outdir / "NATIVE_VS_LATEST_NOTES.md"
    manifest_path = outdir / "manifest.json"
    manifest: dict[str, Any] = {
        "manifest_version": "native_vs_latest_random_topics_v1",
        "release_version": RELEASE_VERSION,
        "random_seed": RANDOM_SEED,
        "output_dir": str(outdir),
        "comparison_model": "codex_native_skill_vs_presentation_skill_latest",
        "comparison_labels": {
            "left_column": "Codex native skill",
            "right_column": f"presentation-skill v{RELEASE_VERSION}",
        },
        "native_skill": {
            "implementation": "OpenAI bundled Presentations skill via @oai/artifact-tool",
            "skill_dir": native_commands.get("skill_dir"),
            "deterministic_baseline": True,
        },
        "latest_skill": {
            "implementation": "presentation-skill corpus-routed builder",
            "design_catalog_version": DESIGN_CATALOG_VERSION,
            "design_catalog_summary": design_catalog_summary(topics),
            "descriptor_only_corpus": True,
        },
        "topic_count": len(topics),
        "deck_count": len(native_records) + len(latest_records),
        "topics": [
            {
                "slug": topic["slug"],
                "title": topic["title"],
                "native_preset": "bundled-native-baseline",
                "latest_preset": topic["corpus_preset"],
                "corpus_family": topic["corpus_family"],
                "borrowed_treatment_labels": topic["tags"],
                "data_example": bool(topic.get("data_example")),
            }
            for topic in topics
        ],
        "cases": [*native_records, *latest_records],
        "pair_contact_sheets": pair_sheets,
        "preview_contact_sheets": preview_sheets,
        "overview_contact_sheet": overview_sheet,
        "gallery_deck": gallery,
        "native_commands": native_commands,
        "notes": str(notes_path),
        "manifest_path": str(manifest_path),
    }
    manifest["quality"] = {
        "native_rendered_count": sum(1 for record in native_records if record.get("render_count")),
        "latest_rendered_count": sum(1 for record in latest_records if record.get("render_count")),
        "latest_corpus_context_count": sum(1 for record in latest_records if record.get("outline_large_corpus_context_present")),
        "contact_sheet_count": len(contact_sheets),
        "nonblank_contact_sheet_count": sum(1 for sheet in contact_sheets if sheet.get("nonblank")),
        "contact_sheet_nonblank_pass": all(bool(sheet.get("nonblank")) for sheet in contact_sheets),
        "gallery_render_count": gallery.get("render_count"),
        "latest_visual_warning_total": sum(
            int((record.get("visual_review_summary") or {}).get("warning_count") or 0)
            for record in latest_records
        ),
        "latest_readability_warning_total": sum(
            int((record.get("qa_summary") or {}).get("planning_warning_count") or 0)
            + int((record.get("qa_summary") or {}).get("design_warning_count") or 0)
            for record in latest_records
        ),
    }
    _write_notes(notes_path, manifest)
    _write_json(manifest_path, manifest)
    return manifest


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Output directory for comparison run")
    parser.add_argument("--overwrite", action="store_true", help="Replace the output directory before building")
    return parser.parse_args()


def main() -> int:
    args = _args()
    manifest = build_native_vs_latest(Path(args.outdir), overwrite=args.overwrite)
    print(
        json.dumps(
            {
                "passed": True,
                "manifest_path": manifest["manifest_path"],
                "deck_count": manifest["deck_count"],
                "gallery_pptx": manifest["gallery_deck"]["pptx"],
                "overview_contact_sheet": manifest["overview_contact_sheet"]["path"],
                "quality": manifest["quality"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
