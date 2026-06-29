#!/usr/bin/env python3
"""Discover, validate, and compact a descriptor-only public slide corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MANIFEST = ROOT / "references" / "large_style_corpus_sources.json"
DEFAULT_CATALOG = ROOT / "references" / "large_style_corpus_catalog.json"
DEFAULT_DIGEST = ROOT / "references" / "large_style_corpus_catalog.md"
LARGE_STYLE_CORPUS_VERSION = "large_style_corpus_v1"
SOURCE_MANIFEST_VERSION = "large_style_corpus_source_manifest_v1"
STORAGE_RULE = "descriptor_only_no_raw_decks"

STYLE_FAMILY_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "lab-report": {
        "keywords": [
            "lab",
            "assay",
            "experiment",
            "validation",
            "genomics",
            "biology",
            "biomedical",
            "methods",
            "results",
            "sample",
            "sequencing",
            "diagnostic",
        ],
        "layout_tags": ["figure-first", "result-table", "method-readout", "source-footer"],
        "palette_tokens": ["white lab canvas", "muted cyan accent", "ink grid"],
        "typography_tokens": ["compact scientific headings", "caption-rich evidence"],
        "content_treatments": ["scientific figures", "assay tables", "run metadata", "references"],
    },
    "forest-research": {
        "keywords": [
            "research",
            "ecology",
            "field",
            "environment",
            "analysis",
            "model",
            "dataset",
            "survey",
            "study",
        ],
        "layout_tags": ["evidence plates", "field-note sidebars", "chart-plus-interpretation"],
        "palette_tokens": ["soft green", "earth neutral", "paper white"],
        "typography_tokens": ["research report hierarchy", "caption-forward labels"],
        "content_treatments": ["study design", "plots", "field observations", "method caveats"],
    },
    "paper-journal": {
        "keywords": [
            "paper",
            "journal",
            "academic",
            "lecture",
            "thesis",
            "seminar",
            "course",
            "university",
            "literature",
        ],
        "layout_tags": ["journal spread", "citation rail", "equation or figure plate"],
        "palette_tokens": ["paper", "black ink", "subtle rule"],
        "typography_tokens": ["article-like section labels", "small references"],
        "content_treatments": ["paper summary", "method comparison", "equations", "bibliography"],
    },
    "executive-clinical": {
        "keywords": [
            "clinical",
            "healthcare",
            "medical",
            "patient",
            "hospital",
            "trial",
            "care",
            "diagnosis",
            "outcomes",
        ],
        "layout_tags": ["executive evidence brief", "clinical KPI strip", "decision readout"],
        "palette_tokens": ["clinical blue", "white", "status accent"],
        "typography_tokens": ["executive headings", "readable metric labels"],
        "content_treatments": ["clinical outcomes", "risk/benefit", "patient cohorts", "decision tables"],
    },
    "data-heavy-boardroom": {
        "keywords": [
            "dashboard",
            "metrics",
            "analytics",
            "quarterly",
            "business",
            "kpi",
            "revenue",
            "performance",
            "review",
            "finance",
        ],
        "layout_tags": ["dashboard grid", "KPI rail", "board memo table"],
        "palette_tokens": ["boardroom neutral", "blue-gray", "status color"],
        "typography_tokens": ["dense executive labels", "numeric hierarchy"],
        "content_treatments": ["dashboards", "KPI cards", "variance tables", "trend charts"],
    },
    "charcoal-safety": {
        "keywords": [
            "risk",
            "security",
            "safety",
            "incident",
            "audit",
            "compliance",
            "threat",
            "governance",
            "privacy",
            "cyber",
        ],
        "layout_tags": ["risk register", "incident timeline", "control matrix"],
        "palette_tokens": ["charcoal", "signal red", "amber status"],
        "typography_tokens": ["risk memo labels", "compact controls"],
        "content_treatments": ["risk matrix", "control tables", "incident summaries", "mitigation plans"],
    },
    "bold-startup-narrative": {
        "keywords": [
            "startup",
            "pitch",
            "demo",
            "product",
            "launch",
            "growth",
            "founder",
            "market",
            "customer",
            "traction",
        ],
        "layout_tags": ["narrative reveal", "product proof", "market wedge"],
        "palette_tokens": ["bold accent", "high contrast", "launch color"],
        "typography_tokens": ["large decisive headings", "short proof copy"],
        "content_treatments": ["problem/solution", "traction proof", "product screenshots", "growth loops"],
    },
    "sunset-investor": {
        "keywords": [
            "investor",
            "funding",
            "venture",
            "market",
            "pitch",
            "deck",
            "business",
            "financial",
            "revenue",
            "valuation",
        ],
        "layout_tags": ["investor storyline", "market sizing", "financial bridge"],
        "palette_tokens": ["warm accent", "deep neutral", "deal-room highlight"],
        "typography_tokens": ["investor memo headings", "concise numbers"],
        "content_treatments": ["market map", "business model", "financial chart", "ask/use of funds"],
    },
    "editorial-minimal": {
        "keywords": [
            "editorial",
            "report",
            "story",
            "keynote",
            "design",
            "talk",
            "conference",
            "portfolio",
            "essay",
        ],
        "layout_tags": ["editorial masthead", "large image/text contrast", "essay spread"],
        "palette_tokens": ["black and white", "single accent", "gallery white"],
        "typography_tokens": ["magazine-like heading", "measured body copy"],
        "content_treatments": ["narrative sections", "image-led spreads", "quotes", "annotated examples"],
    },
    "arctic-minimal": {
        "keywords": [
            "minimal",
            "clean",
            "whitepaper",
            "technical",
            "architecture",
            "spec",
            "systems",
            "overview",
        ],
        "layout_tags": ["sparse technical grid", "thin rules", "architecture frame"],
        "palette_tokens": ["cool gray", "ice blue", "white field"],
        "typography_tokens": ["quiet technical labels", "low-contrast metadata"],
        "content_treatments": ["architecture diagrams", "technical summaries", "spec tables", "minimal charts"],
    },
    "midnight-neon": {
        "keywords": [
            "ai",
            "llm",
            "machine",
            "learning",
            "developer",
            "agent",
            "openai",
            "chatgpt",
            "codex",
            "cyber",
            "crypto",
        ],
        "layout_tags": ["dark console", "code-demo spread", "neon metric strip"],
        "palette_tokens": ["dark canvas", "neon cyan", "violet accent"],
        "typography_tokens": ["developer talk hierarchy", "monospace labels"],
        "content_treatments": ["code demos", "AI workflow", "model charts", "security readouts"],
    },
    "lavender-ops": {
        "keywords": [
            "ops",
            "operations",
            "roadmap",
            "workflow",
            "sprint",
            "team",
            "planning",
            "product",
            "process",
            "program",
        ],
        "layout_tags": ["workflow board", "roadmap bands", "operating cadence"],
        "palette_tokens": ["lavender accent", "cool neutral", "soft status"],
        "typography_tokens": ["ops labels", "planning metadata"],
        "content_treatments": ["roadmaps", "workflow diagrams", "team status", "operating metrics"],
    },
    "warm-terracotta": {
        "keywords": [
            "workshop",
            "community",
            "policy",
            "civic",
            "training",
            "field",
            "culture",
            "education",
            "public",
            "service",
        ],
        "layout_tags": ["workshop canvas", "civic explainer", "field report"],
        "palette_tokens": ["terracotta", "warm neutral", "public-service accent"],
        "typography_tokens": ["human-scale headings", "plain language labels"],
        "content_treatments": ["workshop prompts", "policy summaries", "community findings", "training steps"],
    },
}

AI_AGENT_TERMS = {
    "ai",
    "agent",
    "agents",
    "llm",
    "gpt",
    "chatgpt",
    "openai",
    "claude",
    "codex",
    "copilot",
    "autogen",
    "crew",
    "langchain",
    "slidev-ai",
    "generated",
}
DECK_LIKE_PATH_TERMS = (
    "slide",
    "slides",
    "presentation",
    "presentations",
    "deck",
    "talk",
    "talks",
    "lecture",
    "lectures",
    "pitch",
    "keynote",
    "workshop",
    "conference",
    "training",
    "marp",
    "slidev",
    "reveal",
)
LOW_CONFIDENCE_MARKDOWN_NAMES = {
    "readme.md",
    "contributing.md",
    "license.md",
    "skill.md",
    "help.md",
    "api.md",
}

REQUIRED_RECORD_FIELDS = (
    "deck_id",
    "provider",
    "source_url",
    "repository",
    "repository_url",
    "path",
    "file_name",
    "extension",
    "deck_format",
    "deck_system",
    "deck_like_evidence",
    "rights_posture",
    "primary_style_family",
    "style_family_scores",
    "descriptor_tags",
    "layout_tags",
    "palette_tokens",
    "typography_tokens",
    "content_treatments",
    "agent_usage_signal",
    "overlap_key",
    "discovery",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_source_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or DEFAULT_SOURCE_MANIFEST)


def load_large_style_corpus(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_CATALOG
    if not target.exists():
        return {}
    return _load_json(target)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _tokens(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9+#.-]+", text.lower()) if token}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _deck_id(provider: str, repository: str, path: str) -> str:
    text = f"{provider}|{repository.lower()}|{path.lower()}".encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:20]


def _extension(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    return suffix or "unknown"


def _deck_format(extension: str) -> str:
    return {
        "pptx": "editable-powerpoint",
        "ppt": "legacy-powerpoint",
        "pdf": "rendered-pdf",
        "md": "markdown-source",
        "mdx": "markdown-source",
        "html": "web-presentation",
        "htm": "web-presentation",
        "odp": "open-document-presentation",
        "key": "keynote",
        "ipynb": "notebook-slides",
    }.get(extension, "deck-like-file")


def _deck_system(path: str, extension: str, text: str) -> str:
    lower = f"{path} {text}".lower()
    if "slidev" in lower:
        return "slidev-markdown"
    if "marp" in lower:
        return "marp-markdown"
    if "reveal.js" in lower or "revealjs" in lower or "/reveal" in lower:
        return "reveal-js"
    if extension in {"pptx", "ppt"}:
        return "powerpoint"
    if extension == "pdf":
        return "exported-pdf"
    if extension == "odp":
        return "opendocument"
    if extension == "key":
        return "keynote"
    if extension in {"md", "mdx"}:
        return "markdown-slides"
    if extension in {"html", "htm"}:
        return "web-slides"
    return "deck-like-file"


def _deck_like_evidence(path: str, extension: str, query_text: str) -> dict[str, Any]:
    lower_path = path.lower()
    lower_query = query_text.lower()
    name = Path(lower_path).name
    path_hits = sorted(term for term in DECK_LIKE_PATH_TERMS if term in lower_path)
    query_hits = sorted(term for term in DECK_LIKE_PATH_TERMS if term in lower_query)
    if extension in {"pptx", "ppt", "odp", "key"}:
        confidence = "high"
        accepted = True
    elif extension == "pdf":
        accepted = bool(path_hits or query_hits)
        confidence = "high" if path_hits else "medium"
    elif extension in {"md", "mdx", "html", "htm"}:
        accepted = name not in LOW_CONFIDENCE_MARKDOWN_NAMES and bool(path_hits)
        confidence = "medium" if accepted else "low"
    else:
        accepted = bool(path_hits)
        confidence = "low" if accepted else "reject"
    return {
        "accepted": accepted,
        "confidence": confidence,
        "path_hits": path_hits[:8],
        "query_hits": query_hits[:8],
    }


def _record_is_likely_deck_like(record: dict[str, Any]) -> bool:
    evidence = record.get("deck_like_evidence") if isinstance(record.get("deck_like_evidence"), dict) else {}
    if evidence:
        return bool(evidence.get("accepted"))
    path = str(record.get("path") or "")
    extension = str(record.get("extension") or _extension(path))
    query_terms = " ".join(_string_list((record.get("discovery") or {}).get("query_terms") if isinstance(record.get("discovery"), dict) else []))
    return bool(_deck_like_evidence(path, extension, query_terms).get("accepted"))


def _path_shape(path: str) -> str:
    lower = path.lower()
    name = Path(lower).name
    if re.fullmatch(r"_?slides?\.[a-z0-9]+", name):
        return "generic-slides-file"
    if "pitch" in lower:
        return "pitch-named"
    if "deck" in lower:
        return "deck-named"
    if "presentation" in lower:
        return "presentation-named"
    if "talk" in lower:
        return "talk-named"
    if "lecture" in lower:
        return "lecture-named"
    if len(Path(lower).parts) >= 4:
        return "nested-archive-path"
    return "topic-named"


def _repo_from_item(item: dict[str, Any]) -> dict[str, Any]:
    repo = item.get("repository") if isinstance(item.get("repository"), dict) else {}
    name = str(repo.get("nameWithOwner") or repo.get("fullName") or "").strip()
    return {
        "name": name,
        "url": str(repo.get("url") or (f"https://github.com/{name}" if name else "")).strip(),
        "is_fork": bool(repo.get("isFork")),
        "is_private": bool(repo.get("isPrivate")),
    }


def _owner(repository: str) -> str:
    return repository.split("/", 1)[0] if "/" in repository else repository


def _family_scores(text: str, target_families: list[str]) -> dict[str, int]:
    token_set = _tokens(text)
    scores: dict[str, int] = {}
    for family, descriptor in STYLE_FAMILY_DESCRIPTORS.items():
        score = 0
        if family in target_families:
            score += 7
        for keyword in descriptor["keywords"]:
            keyword_text = str(keyword).lower()
            if keyword_text in text.lower():
                score += 3
            elif keyword_text in token_set:
                score += 2
        for term in family.split("-"):
            if len(term) > 3 and term in token_set:
                score += 1
        if score:
            scores[family] = score
    if not scores:
        fallback = target_families[0] if target_families else "editorial-minimal"
        scores[fallback] = 1
    return dict(sorted(scores.items(), key=lambda item: (-item[1], item[0])))


def _descriptor_tags(text: str, deck_system: str, extension: str, target_families: list[str]) -> list[str]:
    token_set = _tokens(text)
    tags: list[str] = [deck_system, _deck_format(extension)]
    term_map = {
        "chart": ["chart", "charts", "plot", "plots", "graph", "graphs"],
        "table": ["table", "tables", "matrix", "spreadsheet"],
        "dashboard": ["dashboard", "kpi", "metrics", "scorecard"],
        "figure": ["figure", "figures", "image", "images", "diagram"],
        "research": ["research", "study", "paper", "academic", "science"],
        "pitch": ["pitch", "startup", "investor", "market"],
        "policy": ["policy", "governance", "civic", "public"],
        "risk": ["risk", "security", "safety", "incident", "audit"],
        "training": ["workshop", "training", "lecture", "course"],
        "ai-agent": list(AI_AGENT_TERMS),
    }
    for tag, terms in term_map.items():
        if any(term in token_set or term in text.lower() for term in terms):
            tags.append(tag)
    tags.extend(target_families[:3])
    return sorted(dict.fromkeys(tags))


def _content_treatments(tags: list[str], primary_family: str) -> list[str]:
    treatments = list(STYLE_FAMILY_DESCRIPTORS.get(primary_family, {}).get("content_treatments", []))
    if "dashboard" in tags:
        treatments.extend(["dashboard grid", "KPI summary"])
    if "chart" in tags:
        treatments.extend(["annotated charts", "trend readout"])
    if "table" in tags:
        treatments.extend(["editable tables", "decision matrix"])
    if "figure" in tags:
        treatments.extend(["figure plate", "captioned visual"])
    if "ai-agent" in tags:
        treatments.extend(["AI workflow", "agent/tooling comparison"])
    return sorted(dict.fromkeys(treatments))[:8]


def _agent_signal(text: str) -> dict[str, Any]:
    lower = text.lower()
    hits = sorted(term for term in AI_AGENT_TERMS if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower))
    return {
        "has_signal": bool(hits),
        "terms": hits,
        "signal_type": "ai_agent_or_ai_deck_context" if hits else "none",
    }


def _distinctiveness_score(
    *,
    path: str,
    deck_system: str,
    extension: str,
    primary_family: str,
    tags: list[str],
    agent_signal: dict[str, Any],
    target_families: list[str],
) -> int:
    score = 10
    if bool(agent_signal.get("has_signal")):
        score += 12
    if deck_system in {"slidev-markdown", "marp-markdown", "reveal-js"}:
        score += 7
    if extension in {"pptx", "odp", "md", "html"}:
        score += 4
    if primary_family in target_families:
        score += 3
    if _path_shape(path) not in {"generic-slides-file", "topic-named"}:
        score += 2
    score += min(6, len(tags))
    return score


def _normalize_record(item: dict[str, Any], query: dict[str, Any]) -> dict[str, Any] | None:
    repo = _repo_from_item(item)
    repository = repo["name"]
    path = str(item.get("path") or "").strip()
    source_url = str(item.get("url") or "").strip()
    if not repository or not path or not source_url.startswith("https://"):
        return None
    provider = str(query.get("provider") or "github_code_search")
    extension = _extension(path)
    target_families = _string_list(query.get("target_families"))
    classification_text = " ".join(
        [
            repository,
            path,
            str(query.get("terms") or ""),
            str(query.get("design_signal") or ""),
            " ".join(target_families),
        ]
    )
    deck_like_evidence = _deck_like_evidence(path, extension, classification_text)
    if not deck_like_evidence.get("accepted"):
        return None
    deck_system = _deck_system(path, extension, classification_text)
    scores = _family_scores(classification_text, target_families)
    primary_family = next(iter(scores))
    tags = _descriptor_tags(classification_text, deck_system, extension, target_families)
    agent_signal = _agent_signal(classification_text)
    overlap_key = "|".join([deck_system, primary_family, _deck_format(extension), _path_shape(path)])
    descriptor = STYLE_FAMILY_DESCRIPTORS.get(primary_family, {})
    record = {
        "deck_id": _deck_id(provider, repository, path),
        "provider": provider,
        "source_url": source_url,
        "repository": repository,
        "repository_owner": _owner(repository),
        "repository_url": repo["url"],
        "repository_is_fork": repo["is_fork"],
        "repository_is_private": repo["is_private"],
        "path": path,
        "file_name": Path(path).name,
        "extension": extension,
        "deck_format": _deck_format(extension),
        "deck_system": deck_system,
        "deck_like_evidence": deck_like_evidence,
        "rights_posture": "metadata_only_public_github_license_unverified",
        "primary_style_family": primary_family,
        "style_family_scores": scores,
        "descriptor_tags": tags,
        "layout_tags": list(descriptor.get("layout_tags", []))[:6],
        "palette_tokens": list(descriptor.get("palette_tokens", []))[:5],
        "typography_tokens": list(descriptor.get("typography_tokens", []))[:5],
        "content_treatments": _content_treatments(tags, primary_family),
        "agent_usage_signal": agent_signal,
        "overlap_key": overlap_key,
        "path_shape": _path_shape(path),
        "distinctiveness_score": _distinctiveness_score(
            path=path,
            deck_system=deck_system,
            extension=extension,
            primary_family=primary_family,
            tags=tags,
            agent_signal=agent_signal,
            target_families=target_families,
        ),
        "discovery": {
            "query_ids": [str(query.get("query_id") or "")],
            "query_terms": [str(query.get("terms") or "")],
            "target_families": target_families,
            "design_signals": [str(query.get("design_signal") or "")],
        },
    }
    return record


def _merge_record(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    discovery = existing.get("discovery") if isinstance(existing.get("discovery"), dict) else {}
    incoming_discovery = incoming.get("discovery") if isinstance(incoming.get("discovery"), dict) else {}
    for key in ("query_ids", "query_terms", "target_families", "design_signals"):
        merged = _string_list(discovery.get(key)) + _string_list(incoming_discovery.get(key))
        discovery[key] = sorted(dict.fromkeys(merged))
    existing["discovery"] = discovery
    if int(incoming.get("distinctiveness_score") or 0) > int(existing.get("distinctiveness_score") or 0):
        for key in (
            "primary_style_family",
            "style_family_scores",
            "descriptor_tags",
            "layout_tags",
            "palette_tokens",
            "typography_tokens",
            "content_treatments",
            "agent_usage_signal",
            "overlap_key",
            "path_shape",
            "distinctiveness_score",
        ):
            existing[key] = incoming.get(key)


def _run_gh_search_code(
    query: dict[str, Any],
    default_limit: int,
    *,
    rate_limit_retries: int = 1,
    rate_limit_sleep_sec: int = 65,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    terms = str(query.get("terms") or "").strip()
    if not terms:
        return [], {"query_id": query.get("query_id"), "status": "skipped", "reason": "empty_terms"}
    limit = int(query.get("limit") or default_limit)
    term_parts = shlex.split(terms) or [terms]
    cmd = [
        "gh",
        "search",
        "code",
        *term_parts,
        "--limit",
        str(limit),
        "--json",
        "repository,path,url",
    ]
    if query.get("extension"):
        cmd.extend(["--extension", str(query["extension"])])
    if query.get("filename"):
        cmd.extend(["--filename", str(query["filename"])])
    if query.get("match"):
        cmd.extend(["--match", str(query["match"])])
    attempts: list[dict[str, Any]] = []
    proc: subprocess.CompletedProcess[str] | None = None
    started = time.time()
    for attempt in range(rate_limit_retries + 1):
        proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, check=False)
        stderr_tail = proc.stderr[-500:] if proc.stderr else ""
        attempts.append(
            {
                "attempt": attempt + 1,
                "returncode": proc.returncode,
                "stderr_tail": stderr_tail,
            }
        )
        rate_limited = proc.returncode != 0 and "rate limit" in stderr_tail.lower()
        if not rate_limited or attempt >= rate_limit_retries:
            break
        time.sleep(rate_limit_sleep_sec)
    duration = round(time.time() - started, 3)
    assert proc is not None
    report = {
        "query_id": query.get("query_id"),
        "status": "ok" if proc.returncode == 0 else "error",
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "duration_seconds": duration,
        "attempts": attempts,
        "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
    }
    if proc.returncode != 0:
        return [], report
    try:
        payload = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        report.update({"status": "error", "reason": f"json_decode_error: {exc}"})
        return [], report
    if not isinstance(payload, list):
        report.update({"status": "error", "reason": "json_payload_not_list"})
        return [], report
    report["result_count"] = len(payload)
    return [item for item in payload if isinstance(item, dict)], report


def _run_gh_tree_index(entry: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    repo = str(entry.get("repo") or "").strip()
    query_id = str(entry.get("query_id") or repo)
    if not repo or "/" not in repo:
        return [], {"query_id": query_id, "status": "skipped", "reason": "missing_repo"}
    started = time.time()
    meta_cmd = ["gh", "api", f"repos/{repo}"]
    meta_proc = subprocess.run(meta_cmd, cwd=str(ROOT), text=True, capture_output=True, check=False)
    if meta_proc.returncode != 0:
        return [], {
            "query_id": query_id,
            "status": "error",
            "provider": "github_tree_index",
            "command": " ".join(meta_cmd),
            "returncode": meta_proc.returncode,
            "duration_seconds": round(time.time() - started, 3),
            "stderr_tail": meta_proc.stderr[-500:] if meta_proc.stderr else "",
        }
    try:
        meta = json.loads(meta_proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return [], {"query_id": query_id, "status": "error", "reason": f"repo_meta_json_error: {exc}"}
    branch = str(meta.get("default_branch") or "main")
    tree_cmd = ["gh", "api", f"repos/{repo}/git/trees/{branch}?recursive=1"]
    tree_proc = subprocess.run(tree_cmd, cwd=str(ROOT), text=True, capture_output=True, check=False)
    duration = round(time.time() - started, 3)
    report = {
        "query_id": query_id,
        "status": "ok" if tree_proc.returncode == 0 else "error",
        "provider": "github_tree_index",
        "command": " ".join(tree_cmd),
        "returncode": tree_proc.returncode,
        "duration_seconds": duration,
        "stderr_tail": tree_proc.stderr[-500:] if tree_proc.stderr else "",
    }
    if tree_proc.returncode != 0:
        return [], report
    try:
        tree_payload = json.loads(tree_proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        report.update({"status": "error", "reason": f"tree_json_error: {exc}"})
        return [], report
    tree = tree_payload.get("tree") if isinstance(tree_payload.get("tree"), list) else []
    repo_url = str(meta.get("html_url") or f"https://github.com/{repo}")
    items: list[dict[str, Any]] = []
    for node in tree:
        if not isinstance(node, dict) or node.get("type") != "blob":
            continue
        path = str(node.get("path") or "").strip()
        extension = _extension(path)
        if extension not in {"pptx", "ppt", "pdf", "odp", "key", "md", "mdx", "html", "htm"}:
            continue
        evidence = _deck_like_evidence(path, extension, str(entry.get("design_signal") or ""))
        if not evidence.get("accepted"):
            continue
        items.append(
            {
                "repository": {
                    "nameWithOwner": repo,
                    "url": repo_url,
                    "isFork": bool(meta.get("fork")),
                    "isPrivate": bool(meta.get("private")),
                },
                "path": path,
                "url": f"{repo_url}/blob/{quote(branch, safe='')}/{quote(path, safe='/')}",
            }
        )
    report["result_count"] = len(items)
    report["tree_truncated"] = bool(tree_payload.get("truncated"))
    return items, report


def discover_large_style_corpus(
    source_manifest: dict[str, Any],
    *,
    limit_total: int,
    query_limit: int,
    sleep_ms: int,
    seed_catalog: dict[str, Any] | None = None,
    skip_successful_existing: bool = False,
    only_query_ids: set[str] | None = None,
    force_query_limit: bool = False,
    max_consecutive_errors: int = 4,
    rate_limit_retries: int = 1,
    rate_limit_sleep_sec: int = 65,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queries = source_manifest.get("queries") if isinstance(source_manifest.get("queries"), list) else []
    records: dict[str, dict[str, Any]] = {}
    reports: list[dict[str, Any]] = []
    skipped_query_ids: set[str] = set()
    if isinstance(seed_catalog, dict) and seed_catalog:
        for record in seed_catalog.get("records", []):
            if not isinstance(record, dict):
                continue
            if not _record_is_likely_deck_like(record):
                continue
            record = dict(record)
            if not isinstance(record.get("deck_like_evidence"), dict):
                query_terms = " ".join(
                    _string_list(
                        (record.get("discovery") or {}).get("query_terms")
                        if isinstance(record.get("discovery"), dict)
                        else []
                    )
                )
                record["deck_like_evidence"] = _deck_like_evidence(
                    str(record.get("path") or ""),
                    str(record.get("extension") or _extension(str(record.get("path") or ""))),
                    query_terms,
                )
            provider = str(record.get("provider") or "")
            repository = str(record.get("repository") or "")
            path = str(record.get("path") or "")
            if not provider or not repository or not path:
                continue
            dedupe_key = f"{provider}|{repository.lower()}|{path.lower()}"
            records[dedupe_key] = record
        for report in seed_catalog.get("query_reports", []):
            if not isinstance(report, dict):
                continue
            reports.append({**report, "resumed_from_catalog": True})
            if skip_successful_existing and report.get("status") == "ok":
                query_id = str(report.get("query_id") or "")
                if query_id:
                    skipped_query_ids.add(query_id)
    consecutive_errors = 0
    for query in queries:
        if not isinstance(query, dict):
            continue
        query = {**query}
        query.setdefault("provider", "github_code_search")
        if force_query_limit:
            query["limit"] = query_limit
        query_id = str(query.get("query_id") or "")
        if only_query_ids and query_id not in only_query_ids:
            continue
        if query_id in skipped_query_ids:
            continue
        results, report = _run_gh_search_code(
            query,
            query_limit,
            rate_limit_retries=rate_limit_retries,
            rate_limit_sleep_sec=rate_limit_sleep_sec,
        )
        reports.append(report)
        if report.get("status") == "error":
            consecutive_errors += 1
            stderr_tail = str(report.get("stderr_tail") or "").lower()
            if consecutive_errors >= max_consecutive_errors and "rate limit" in stderr_tail:
                reports.append(
                    {
                        "query_id": "collector_abort",
                        "status": "aborted",
                        "reason": "max_consecutive_rate_limit_errors",
                        "max_consecutive_errors": max_consecutive_errors,
                    }
                )
                break
        else:
            consecutive_errors = 0
        for item in results:
            record = _normalize_record(item, query)
            if not record:
                continue
            dedupe_key = f"{record['provider']}|{record['repository'].lower()}|{record['path'].lower()}"
            if dedupe_key in records:
                _merge_record(records[dedupe_key], record)
            else:
                records[dedupe_key] = record
        if limit_total and len(records) >= limit_total * 2:
            successful_reports = sum(1 for item in reports if item.get("status") == "ok")
            if successful_reports >= max(8, len(queries) // 3):
                break
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000)
    tree_entries = source_manifest.get("tree_repositories") if isinstance(source_manifest.get("tree_repositories"), list) else []
    for entry in tree_entries:
        if not isinstance(entry, dict):
            continue
        entry = {**entry, "provider": "github_tree_index"}
        query_id = str(entry.get("query_id") or "")
        if only_query_ids and query_id not in only_query_ids:
            continue
        if query_id in skipped_query_ids:
            continue
        results, report = _run_gh_tree_index(entry)
        reports.append(report)
        for item in results:
            record = _normalize_record(item, entry)
            if not record:
                continue
            dedupe_key = f"{record['provider']}|{record['repository'].lower()}|{record['path'].lower()}"
            if dedupe_key in records:
                _merge_record(records[dedupe_key], record)
            else:
                records[dedupe_key] = record
        if limit_total and len(records) >= limit_total * 2:
            break
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000)
    return list(records.values()), reports


def _all_families(source_manifest: dict[str, Any]) -> list[str]:
    families = _string_list(source_manifest.get("style_families"))
    return families or list(STYLE_FAMILY_DESCRIPTORS)


def _select_balanced_records(
    records: list[dict[str, Any]],
    *,
    source_manifest: dict[str, Any],
    target_count: int,
    min_per_family: int,
    max_per_repository: int,
    max_per_owner: int,
    max_per_overlap_key: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    families = _all_families(source_manifest)
    records = _rebalance_records_for_family_floor(records, families=families, min_per_family=min_per_family)
    ordered = sorted(
        records,
        key=lambda item: (
            -int(item.get("distinctiveness_score") or 0),
            str(item.get("primary_style_family") or ""),
            str(item.get("repository") or ""),
            str(item.get("path") or ""),
        ),
    )
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    repo_counts: Counter[str] = Counter()
    owner_counts: Counter[str] = Counter()
    overlap_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    skip_reasons: Counter[str] = Counter()

    def add(record: dict[str, Any], reason: str) -> None:
        selected.append({**record, "balance_reason": reason})
        selected_ids.add(str(record.get("deck_id")))
        repo_counts[str(record.get("repository") or "")] += 1
        owner_counts[str(record.get("repository_owner") or "")] += 1
        overlap_counts[str(record.get("overlap_key") or "")] += 1
        family_counts[str(record.get("primary_style_family") or "")] += 1

    def family_floor_met() -> bool:
        return all(family_counts[family] >= min_per_family for family in families)

    for record in ordered:
        if len(selected) >= target_count and family_floor_met():
            break
        deck_id = str(record.get("deck_id") or "")
        if deck_id in selected_ids:
            continue
        family = str(record.get("primary_style_family") or "")
        need_family = family in families and family_counts[family] < min_per_family
        repo = str(record.get("repository") or "")
        owner = str(record.get("repository_owner") or "")
        overlap = str(record.get("overlap_key") or "")
        if not need_family and repo_counts[repo] >= max_per_repository:
            skip_reasons["repository_cap"] += 1
            continue
        if not need_family and owner_counts[owner] >= max_per_owner:
            skip_reasons["owner_cap"] += 1
            continue
        if not need_family and overlap_counts[overlap] >= max_per_overlap_key:
            skip_reasons["overlap_cap"] += 1
            continue
        add(record, "balanced_priority" if not need_family else "family_floor")

    for record in ordered:
        if len(selected) >= target_count and family_floor_met():
            break
        deck_id = str(record.get("deck_id") or "")
        if deck_id in selected_ids:
            continue
        add(record, "target_fill_after_overlap_guard")

    diagnostics = {
        "raw_unique_records": len(records),
        "selected_records": len(selected),
        "target_count": target_count,
        "min_per_family": min_per_family,
        "family_floor_met": family_floor_met(),
        "skip_reasons": dict(skip_reasons),
        "max_per_repository": max_per_repository,
        "max_per_owner": max_per_owner,
        "max_per_overlap_key": max_per_overlap_key,
    }
    return selected[:target_count], diagnostics


def _rebalance_records_for_family_floor(
    records: list[dict[str, Any]],
    *,
    families: list[str],
    min_per_family: int,
) -> list[dict[str, Any]]:
    if min_per_family <= 0:
        return records
    out = [dict(record) for record in records]
    counts: Counter[str] = Counter(str(record.get("primary_style_family") or "") for record in out)
    by_id = {str(record.get("deck_id") or ""): record for record in out}
    changed: set[str] = set()
    for family in families:
        needed = max(0, min_per_family - counts.get(family, 0))
        if needed == 0:
            continue
        candidates = sorted(
            [
                record
                for record in out
                if str(record.get("deck_id") or "") not in changed
                and str(record.get("primary_style_family") or "") != family
                and int((record.get("style_family_scores") or {}).get(family, 0)) > 0
                and counts.get(str(record.get("primary_style_family") or ""), 0) > min_per_family
            ],
            key=lambda record: (
                -int((record.get("style_family_scores") or {}).get(family, 0)),
                -int(record.get("distinctiveness_score") or 0),
                str(record.get("deck_id") or ""),
            ),
        )
        for record in candidates[:needed]:
            deck_id = str(record.get("deck_id") or "")
            target = by_id.get(deck_id)
            if not target:
                continue
            previous = str(target.get("primary_style_family") or "")
            descriptor = STYLE_FAMILY_DESCRIPTORS.get(family, {})
            counts[previous] -= 1
            counts[family] += 1
            target["primary_style_family"] = family
            target["layout_tags"] = list(descriptor.get("layout_tags", []))[:6]
            target["palette_tokens"] = list(descriptor.get("palette_tokens", []))[:5]
            target["typography_tokens"] = list(descriptor.get("typography_tokens", []))[:5]
            target["content_treatments"] = _content_treatments(_string_list(target.get("descriptor_tags")), family)
            target["overlap_key"] = "|".join(
                [
                    str(target.get("deck_system") or ""),
                    family,
                    str(target.get("deck_format") or ""),
                    str(target.get("path_shape") or ""),
                ]
            )
            target["family_rebalance"] = {
                "from": previous,
                "to": family,
                "reason": "secondary_affinity_family_floor",
            }
            changed.add(deck_id)
            if counts[family] >= min_per_family:
                break
    return out


def _counter_dict(counter: Counter[str], limit: int | None = None) -> dict[str, int]:
    items = counter.most_common(limit)
    return {key: count for key, count in items}


def _family_summaries(records: list[dict[str, Any]], families: list[str]) -> dict[str, Any]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_family[str(record.get("primary_style_family") or "")].append(record)
    summaries: dict[str, Any] = {}
    for family in families:
        family_records = by_family.get(family, [])
        descriptor = STYLE_FAMILY_DESCRIPTORS.get(family, {})
        deck_systems = Counter(str(record.get("deck_system") or "") for record in family_records)
        formats = Counter(str(record.get("deck_format") or "") for record in family_records)
        treatments = Counter(
            treatment
            for record in family_records
            for treatment in _string_list(record.get("content_treatments"))
        )
        tags = Counter(tag for record in family_records for tag in _string_list(record.get("descriptor_tags")))
        sample_records = sorted(
            family_records,
            key=lambda item: (-int(item.get("distinctiveness_score") or 0), str(item.get("repository") or "")),
        )[:8]
        summaries[family] = {
            "record_count": len(family_records),
            "descriptor": {
                "layout_tags": descriptor.get("layout_tags", []),
                "palette_tokens": descriptor.get("palette_tokens", []),
                "typography_tokens": descriptor.get("typography_tokens", []),
                "content_treatments": descriptor.get("content_treatments", []),
            },
            "top_deck_systems": _counter_dict(deck_systems, 6),
            "top_formats": _counter_dict(formats, 5),
            "top_descriptor_tags": _counter_dict(tags, 10),
            "top_content_treatments": _counter_dict(treatments, 10),
            "sample_record_ids": [record.get("deck_id") for record in sample_records],
            "sample_sources": [
                {
                    "deck_id": record.get("deck_id"),
                    "repository": record.get("repository"),
                    "path": record.get("path"),
                    "deck_system": record.get("deck_system"),
                    "source_url": record.get("source_url"),
                }
                for record in sample_records[:5]
            ],
        }
    return summaries


def build_catalog(
    records: list[dict[str, Any]],
    *,
    source_manifest: dict[str, Any],
    query_reports: list[dict[str, Any]],
    selection_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    families = _all_families(source_manifest)
    family_counts = Counter(str(record.get("primary_style_family") or "") for record in records)
    format_counts = Counter(str(record.get("deck_format") or "") for record in records)
    system_counts = Counter(str(record.get("deck_system") or "") for record in records)
    owner_counts = Counter(str(record.get("repository_owner") or "") for record in records)
    repo_counts = Counter(str(record.get("repository") or "") for record in records)
    overlap_counts = Counter(str(record.get("overlap_key") or "") for record in records)
    ai_count = sum(1 for record in records if bool(record.get("agent_usage_signal", {}).get("has_signal")))
    targets = source_manifest.get("deck_targets") if isinstance(source_manifest.get("deck_targets"), dict) else {}
    return {
        "catalog_version": LARGE_STYLE_CORPUS_VERSION,
        "generated_at_utc": _now_iso(),
        "source_manifest_version": source_manifest.get("manifest_version"),
        "source_manifest_path": str(DEFAULT_SOURCE_MANIFEST.relative_to(ROOT)),
        "policy": source_manifest.get("policy") if isinstance(source_manifest.get("policy"), dict) else {},
        "targets": targets,
        "summary": {
            "record_count": len(records),
            "unique_repository_count": len(repo_counts),
            "unique_owner_count": len(owner_counts),
            "ai_agent_signal_count": ai_count,
            "style_family_counts": {family: family_counts.get(family, 0) for family in families},
            "deck_format_counts": _counter_dict(format_counts),
            "deck_system_counts": _counter_dict(system_counts),
            "top_repository_counts": _counter_dict(repo_counts, 12),
            "top_owner_counts": _counter_dict(owner_counts, 12),
            "top_overlap_keys": _counter_dict(overlap_counts, 12),
            "successful_query_count": sum(1 for item in query_reports if item.get("status") == "ok"),
            "failed_query_count": sum(1 for item in query_reports if item.get("status") == "error"),
        },
        "selection_diagnostics": selection_diagnostics,
        "family_summaries": _family_summaries(records, families),
        "query_reports": query_reports,
        "records": records,
    }


def validate_source_manifest(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if source_manifest.get("manifest_version") != SOURCE_MANIFEST_VERSION:
        failures.append({"path": "manifest_version", "reason": "wrong_version"})
    policy = source_manifest.get("policy") if isinstance(source_manifest.get("policy"), dict) else {}
    if policy.get("storage_rule") != STORAGE_RULE:
        failures.append({"path": "policy.storage_rule", "reason": "wrong_storage_rule"})
    forbidden = set(_string_list(policy.get("forbidden_materials")))
    for required in ("raw third-party PPTX files", "raw screenshots from third-party decks"):
        if required not in forbidden:
            failures.append({"path": "policy.forbidden_materials", "reason": "missing_required_rule", "value": required})
    if len(_string_list(source_manifest.get("style_families"))) < 10:
        failures.append({"path": "style_families", "reason": "too_few_families"})
    queries = source_manifest.get("queries") if isinstance(source_manifest.get("queries"), list) else []
    if len(queries) < 20:
        failures.append({"path": "queries", "reason": "too_few_queries", "count": len(queries)})
    seen: set[str] = set()
    for idx, query in enumerate(queries):
        if not isinstance(query, dict):
            failures.append({"path": f"queries[{idx}]", "reason": "not_object"})
            continue
        query_id = str(query.get("query_id") or "").strip()
        if not query_id:
            failures.append({"path": f"queries[{idx}].query_id", "reason": "missing"})
        elif query_id in seen:
            failures.append({"path": f"queries[{idx}].query_id", "reason": "duplicate", "value": query_id})
        seen.add(query_id)
        if not str(query.get("terms") or "").strip():
            failures.append({"path": f"queries[{idx}].terms", "reason": "missing"})
        if not _string_list(query.get("target_families")):
            failures.append({"path": f"queries[{idx}].target_families", "reason": "missing"})
    return failures


def validate_large_style_corpus(
    catalog: dict[str, Any],
    *,
    min_records: int = 0,
    min_family_records: int = 0,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if catalog.get("catalog_version") != LARGE_STYLE_CORPUS_VERSION:
        failures.append({"path": "catalog_version", "reason": "wrong_version"})
    policy = catalog.get("policy") if isinstance(catalog.get("policy"), dict) else {}
    if policy.get("storage_rule") != STORAGE_RULE:
        failures.append({"path": "policy.storage_rule", "reason": "wrong_storage_rule"})
    records = catalog.get("records") if isinstance(catalog.get("records"), list) else []
    if len(records) < min_records:
        failures.append({"path": "records", "reason": "too_few_records", "count": len(records), "minimum": min_records})
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    banned_fields = {"raw_content", "screenshot", "image_data", "deck_binary", "slide_text"}
    family_counts: Counter[str] = Counter()
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            failures.append({"path": f"records[{idx}]", "reason": "not_object"})
            continue
        path_prefix = f"records[{idx}]"
        for field in REQUIRED_RECORD_FIELDS:
            if field not in record or record.get(field) in (None, "", []):
                failures.append({"path": f"{path_prefix}.{field}", "reason": "missing"})
        extra_banned = sorted(field for field in record if field in banned_fields)
        if extra_banned:
            failures.append({"path": path_prefix, "reason": "banned_raw_material_fields", "fields": extra_banned})
        deck_id = str(record.get("deck_id") or "")
        if deck_id in seen_ids:
            failures.append({"path": f"{path_prefix}.deck_id", "reason": "duplicate", "value": deck_id})
        seen_ids.add(deck_id)
        source_url = str(record.get("source_url") or "")
        if not source_url.startswith("https://"):
            failures.append({"path": f"{path_prefix}.source_url", "reason": "must_be_https", "value": source_url})
        source_key = f"{record.get('provider')}|{record.get('repository')}|{record.get('path')}"
        if source_key in seen_sources:
            failures.append({"path": path_prefix, "reason": "duplicate_source_key", "value": source_key})
        seen_sources.add(source_key)
        if bool(record.get("repository_is_private")):
            failures.append({"path": f"{path_prefix}.repository_is_private", "reason": "private_repository_result"})
        if not _record_is_likely_deck_like(record):
            failures.append({"path": f"{path_prefix}.deck_like_evidence", "reason": "low_confidence_deck_like_record"})
        family_counts[str(record.get("primary_style_family") or "")] += 1
    family_summaries = catalog.get("family_summaries") if isinstance(catalog.get("family_summaries"), dict) else {}
    for family in STYLE_FAMILY_DESCRIPTORS:
        if family not in family_summaries:
            failures.append({"path": f"family_summaries.{family}", "reason": "missing"})
        if min_family_records and family_counts.get(family, 0) < min_family_records:
            failures.append(
                {
                    "path": f"summary.style_family_counts.{family}",
                    "reason": "too_few_family_records",
                    "count": family_counts.get(family, 0),
                    "minimum": min_family_records,
                }
            )
    return failures


def _record_score_for_query(record: dict[str, Any], query: str, primary_family: str = "") -> int:
    text = " ".join(
        [
            str(record.get("repository") or ""),
            str(record.get("path") or ""),
            " ".join(_string_list(record.get("descriptor_tags"))),
            " ".join(_string_list(record.get("content_treatments"))),
            str(record.get("deck_system") or ""),
            str(record.get("primary_style_family") or ""),
        ]
    ).lower()
    tokens = _tokens(query)
    score = int(record.get("distinctiveness_score") or 0)
    family = str(record.get("primary_style_family") or "")
    if primary_family and family == primary_family:
        score += 25
    for token in tokens:
        if len(token) > 2 and token in text:
            score += 4
    if bool(record.get("agent_usage_signal", {}).get("has_signal")) and {"ai", "agent", "llm", "chatgpt", "openai"} & tokens:
        score += 10
    return score


def compact_large_style_corpus_context(
    query: str = "",
    *,
    primary_family: str = "",
    catalog: dict[str, Any] | None = None,
    max_families: int = 5,
    max_records: int = 12,
) -> dict[str, Any]:
    payload = catalog if isinstance(catalog, dict) else load_large_style_corpus()
    if not payload:
        return {
            "catalog_version": LARGE_STYLE_CORPUS_VERSION,
            "available": False,
            "reason": "large_style_corpus_catalog.json not found",
        }
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    family_summaries = payload.get("family_summaries") if isinstance(payload.get("family_summaries"), dict) else {}
    query_text = str(query or "")
    family_rank: list[tuple[int, str, dict[str, Any]]] = []
    for family, summary in family_summaries.items():
        if not isinstance(summary, dict):
            continue
        score = 0
        if primary_family and family == primary_family:
            score += 100
        descriptor_text = json.dumps(summary.get("descriptor", {}), ensure_ascii=True).lower()
        for token in _tokens(query_text):
            if len(token) > 2 and token in descriptor_text:
                score += 5
        score += int(summary.get("record_count") or 0) // 25
        family_rank.append((score, family, summary))
    family_rank.sort(key=lambda item: (-item[0], item[1]))
    ranked_records = sorted(
        [record for record in records if isinstance(record, dict)],
        key=lambda record: (-_record_score_for_query(record, query_text, primary_family), str(record.get("deck_id") or "")),
    )[:max_records]
    return {
        "catalog_version": payload.get("catalog_version"),
        "available": True,
        "policy": {
            "storage_rule": payload.get("policy", {}).get("storage_rule") if isinstance(payload.get("policy"), dict) else None,
            "agent_use_rule": payload.get("policy", {}).get("agent_use_rule") if isinstance(payload.get("policy"), dict) else None,
            "rights_posture": payload.get("policy", {}).get("rights_posture") if isinstance(payload.get("policy"), dict) else None,
        },
        "summary": payload.get("summary"),
        "selected_family_summaries": [
            {
                "style_family": family,
                "record_count": summary.get("record_count"),
                "descriptor": summary.get("descriptor"),
                "top_deck_systems": summary.get("top_deck_systems"),
                "top_content_treatments": summary.get("top_content_treatments"),
                "sample_sources": summary.get("sample_sources"),
            }
            for _, family, summary in family_rank[:max_families]
        ],
        "sample_records": [
            {
                "deck_id": record.get("deck_id"),
                "source_url": record.get("source_url"),
                "repository": record.get("repository"),
                "path": record.get("path"),
                "deck_system": record.get("deck_system"),
                "primary_style_family": record.get("primary_style_family"),
                "descriptor_tags": record.get("descriptor_tags"),
                "layout_tags": record.get("layout_tags"),
                "content_treatments": record.get("content_treatments"),
                "agent_usage_signal": record.get("agent_usage_signal"),
            }
            for record in ranked_records
        ],
        "mixing_rule": (
            "Pick one primary style family from selected_family_summaries, then borrow at most "
            "two named treatment ideas from sample_records. Convert borrowed ideas into original "
            "synthetic slide structure; do not copy source decks, screenshots, text, logos, or geometry."
        ),
    }


def write_digest(catalog: dict[str, Any], output: Path) -> None:
    summary = catalog.get("summary") if isinstance(catalog.get("summary"), dict) else {}
    lines = [
        "# Large Style Corpus Catalog",
        "",
        "Descriptor-only public deck index for LLM routing and synthetic reconstruction. It stores URLs, inferred style metadata, and family summaries only.",
        "",
        f"- Catalog version: `{catalog.get('catalog_version')}`",
        f"- Generated: `{catalog.get('generated_at_utc')}`",
        f"- Records: `{summary.get('record_count', 0)}`",
        f"- Unique repositories: `{summary.get('unique_repository_count', 0)}`",
        f"- AI/agent signal records: `{summary.get('ai_agent_signal_count', 0)}`",
        "",
        "## Use Rules",
        "",
        "- Treat each record as an inspiration pointer, not a template asset.",
        "- Do not download, screenshot, copy text from, or reproduce third-party decks unless a later source route clears that specific use.",
        "- Use family summaries to choose a primary style grammar, then create original synthetic layouts in `outline.json`.",
        "",
        "## Family Coverage",
        "",
    ]
    family_summaries = catalog.get("family_summaries") if isinstance(catalog.get("family_summaries"), dict) else {}
    for family, family_summary in family_summaries.items():
        if not isinstance(family_summary, dict):
            continue
        lines.extend(
            [
                f"### {family}",
                "",
                f"- Records: `{family_summary.get('record_count', 0)}`",
                f"- Top systems: `{json.dumps(family_summary.get('top_deck_systems', {}), sort_keys=True)}`",
                f"- Top treatments: `{json.dumps(family_summary.get('top_content_treatments', {}), sort_keys=True)}`",
                "- Sample records:",
            ]
        )
        for sample in family_summary.get("sample_sources", [])[:3]:
            if not isinstance(sample, dict):
                continue
            lines.append(
                f"  - `{sample.get('deck_id')}` `{sample.get('deck_system')}` "
                f"{sample.get('repository')} / `{sample.get('path')}`"
            )
        lines.append("")
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", default=str(DEFAULT_SOURCE_MANIFEST), help="Discovery source manifest")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Large style corpus catalog path")
    parser.add_argument("--discover", action="store_true", help="Run public metadata discovery with gh search code")
    parser.add_argument("--limit-total", type=int, default=2000, help="Selected record target for discovery")
    parser.add_argument("--query-limit", type=int, default=90, help="Default per-query result limit")
    parser.add_argument("--sleep-ms", type=int, default=250, help="Delay between provider queries")
    parser.add_argument("--resume-existing", action="store_true", help="Seed discovery from the existing catalog")
    parser.add_argument(
        "--rerun-successful-existing",
        action="store_true",
        help="With --resume-existing, rerun queries that already succeeded in the existing catalog",
    )
    parser.add_argument(
        "--only-query-ids",
        default="",
        help="Comma-separated manifest query IDs to run; useful for targeted resumable batches",
    )
    parser.add_argument("--force-query-limit", action="store_true", help="Use --query-limit for every manifest query")
    parser.add_argument("--max-consecutive-errors", type=int, default=4, help="Abort discovery after repeated provider errors")
    parser.add_argument("--rate-limit-retries", type=int, default=1, help="Retries for provider rate-limit responses")
    parser.add_argument("--rate-limit-sleep-sec", type=int, default=65, help="Backoff for provider rate-limit responses")
    parser.add_argument("--min-family-records", type=int, default=10, help="Minimum records per style family")
    parser.add_argument("--max-per-repository", type=int, default=8, help="Soft cap per repository before fill")
    parser.add_argument("--max-per-owner", type=int, default=40, help="Soft cap per owner before fill")
    parser.add_argument("--max-per-overlap-key", type=int, default=80, help="Soft cap per overlap key before fill")
    parser.add_argument("--validate", action="store_true", help="Validate source manifest and catalog")
    parser.add_argument("--min-records", type=int, default=0, help="Minimum record count for validation")
    parser.add_argument("--write-digest", action="store_true", help="Write markdown digest next to the catalog")
    parser.add_argument("--digest-output", default=str(DEFAULT_DIGEST), help="Markdown digest output path")
    parser.add_argument("--compact-context", action="store_true", help="Emit compact LLM context")
    parser.add_argument("--prompt", default="", help="Prompt/query text for compact context")
    parser.add_argument("--primary-family", default="", help="Preferred style family for compact context")
    parser.add_argument("--max-context-records", type=int, default=12, help="Sample records in compact context")
    return parser.parse_args()


def main() -> int:
    args = _args()
    source_manifest_path = Path(args.source_manifest).expanduser().resolve()
    catalog_path = Path(args.catalog).expanduser().resolve()
    source_manifest = load_source_manifest(source_manifest_path)
    source_failures = validate_source_manifest(source_manifest)

    if args.discover:
        seed_catalog = load_large_style_corpus(catalog_path) if args.resume_existing else None
        only_query_ids = {
            item.strip()
            for item in str(args.only_query_ids or "").split(",")
            if item.strip()
        }
        records, query_reports = discover_large_style_corpus(
            source_manifest,
            limit_total=args.limit_total,
            query_limit=args.query_limit,
            sleep_ms=args.sleep_ms,
            seed_catalog=seed_catalog,
            skip_successful_existing=bool(args.resume_existing and not args.rerun_successful_existing),
            only_query_ids=only_query_ids or None,
            force_query_limit=args.force_query_limit,
            max_consecutive_errors=args.max_consecutive_errors,
            rate_limit_retries=args.rate_limit_retries,
            rate_limit_sleep_sec=args.rate_limit_sleep_sec,
        )
        selected, diagnostics = _select_balanced_records(
            records,
            source_manifest=source_manifest,
            target_count=args.limit_total,
            min_per_family=args.min_family_records,
            max_per_repository=args.max_per_repository,
            max_per_owner=args.max_per_owner,
            max_per_overlap_key=args.max_per_overlap_key,
        )
        catalog = build_catalog(
            selected,
            source_manifest=source_manifest,
            query_reports=query_reports,
            selection_diagnostics=diagnostics,
        )
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.write_digest:
            write_digest(catalog, Path(args.digest_output).expanduser().resolve())
        failures = source_failures + validate_large_style_corpus(
            catalog,
            min_records=min(args.min_records or args.limit_total, args.limit_total),
            min_family_records=args.min_family_records,
        )
        print(
            json.dumps(
                {
                    "passed": not failures,
                    "catalog": str(catalog_path),
                    "record_count": catalog["summary"]["record_count"],
                    "unique_repository_count": catalog["summary"]["unique_repository_count"],
                    "ai_agent_signal_count": catalog["summary"]["ai_agent_signal_count"],
                    "successful_query_count": catalog["summary"]["successful_query_count"],
                    "failed_query_count": catalog["summary"]["failed_query_count"],
                    "family_counts": catalog["summary"]["style_family_counts"],
                    "failures": failures,
                },
                indent=2,
            )
        )
        return 0 if not failures else 1

    catalog = load_large_style_corpus(catalog_path)
    if args.compact_context:
        context = compact_large_style_corpus_context(
            args.prompt,
            primary_family=args.primary_family,
            catalog=catalog,
            max_records=args.max_context_records,
        )
        print(json.dumps(context, indent=2))
        return 0

    failures = source_failures + validate_large_style_corpus(
        catalog,
        min_records=args.min_records,
        min_family_records=args.min_family_records if args.min_records else 0,
    )
    if args.write_digest and catalog:
        write_digest(catalog, Path(args.digest_output).expanduser().resolve())
    print(
        json.dumps(
            {
                "passed": not failures,
                "source_manifest": str(source_manifest_path),
                "catalog": str(catalog_path),
                "record_count": len(catalog.get("records", [])) if isinstance(catalog, dict) else 0,
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
