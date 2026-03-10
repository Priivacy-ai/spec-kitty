"""Helpers for feature metadata repair during upgrades."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specify_cli.core.git_ops import resolve_primary_branch

_BRANCH_PATTERNS = (
    re.compile(r"(?im)^\*\*target branch\*\*:\s*`?([^\n`]+)`?\s*$"),
    re.compile(r"(?im)^\*\*base branch\*\*:\s*`?([^\n`]+)`?\s*$"),
    re.compile(r"(?im)^target repo branch:\s*`?([^\n`]+)`?\s*$"),
    re.compile(r"(?im)^branch:\s*`?([^\n`]+)`?\s*$"),
    re.compile(r"(?i)must be done on .*?`([^`]+)` branch"),
    re.compile(r"(?i)all work packages branch from and merge back to [`“]?([^`”\n]+)[`”]?"),
    re.compile(r"(?i)merge back to [`“]?([^`”\n]+)[`”]?"),
    re.compile(r"(?i)repository[^\n]*branch [`(]?([A-Za-z0-9._/-]+)"),
)


def load_feature_meta(feature_dir: Path) -> dict[str, Any] | None:
    """Load ``meta.json`` for a feature if it exists and is valid."""
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def write_feature_meta(feature_dir: Path, meta: dict[str, Any]) -> None:
    """Write ``meta.json`` with stable formatting."""
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def infer_target_branch(
    feature_dir: Path,
    repo_root: Path,
    *,
    fallback: str | None = None,
) -> str:
    """Infer ``target_branch`` from explicit feature docs or repo context."""
    fallback_branch = fallback or resolve_primary_branch(repo_root)
    candidates: list[str] = []

    for name in ("spec.md", "plan.md", "tasks.md", "quickstart.md"):
        doc = feature_dir / name
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8", errors="ignore")
        for pattern in _BRANCH_PATTERNS:
            for raw in pattern.findall(content):
                candidate = _normalize_branch_candidate(raw)
                if candidate and candidate not in candidates:
                    candidates.append(candidate)

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1 and fallback_branch in candidates:
        return fallback_branch
    return fallback_branch


def infer_mission(
    feature_dir: Path,
    *,
    existing_meta: dict[str, Any] | None = None,
) -> str:
    """Infer a feature mission when ``meta.json`` is missing."""
    if existing_meta:
        mission = str(existing_meta.get("mission", "")).strip()
        if mission:
            return mission

    if (feature_dir / "research").exists():
        return "research"
    return "software-dev"


def infer_created_at(
    feature_dir: Path,
    *,
    now: datetime | None = None,
) -> str:
    """Infer a stable ``created_at`` timestamp from the earliest file mtime."""
    timestamps = [
        path.stat().st_mtime
        for path in feature_dir.rglob("*")
        if path.is_file()
    ]
    if feature_dir.exists():
        timestamps.append(feature_dir.stat().st_mtime)

    if timestamps:
        created_at = datetime.fromtimestamp(min(timestamps), tz=timezone.utc)
    else:
        created_at = now or datetime.now(timezone.utc)
    return created_at.isoformat()


def build_baseline_feature_meta(
    feature_dir: Path,
    repo_root: Path,
    *,
    existing_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimum viable ``meta.json`` payload for a feature."""
    feature_slug = feature_dir.name
    feature_number, _, slug_tail = feature_slug.partition("-")
    meta = dict(existing_meta or {})

    _set_if_blank(
        meta,
        "feature_number",
        feature_number if feature_number.isdigit() else "",
    )
    _set_if_blank(meta, "slug", feature_slug)
    _set_if_blank(meta, "feature_slug", feature_slug)
    _set_if_blank(
        meta,
        "friendly_name",
        slug_tail.replace("-", " ").strip() or feature_slug,
    )
    _set_if_blank(meta, "mission", infer_mission(feature_dir, existing_meta=meta))
    _set_if_blank(
        meta,
        "target_branch",
        infer_target_branch(feature_dir, repo_root),
    )
    _set_if_blank(meta, "created_at", infer_created_at(feature_dir))
    return meta


def _normalize_branch_candidate(value: str) -> str | None:
    """Normalize a branch candidate extracted from feature docs."""
    cleaned = value.strip()
    if not cleaned:
        return None
    if " or " in cleaned.lower():
        return None
    cleaned = cleaned.strip("`'\"*[]() ")
    match = re.search(r"[A-Za-z0-9._/-]+", cleaned)
    if match is None:
        return None
    return match.group(0)


def _set_if_blank(meta: dict[str, Any], key: str, value: Any) -> None:
    """Populate a metadata field when it is missing or blank."""
    current = meta.get(key)
    if current is None:
        meta[key] = value
        return

    if isinstance(current, str) and not current.strip():
        meta[key] = value
