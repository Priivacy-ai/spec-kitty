#!/usr/bin/env python3
"""Normalize machine-specific strings while preserving pre-publication hashes."""

from __future__ import annotations

import hashlib
import json
import platform
import re
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 - publication integrity


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    data_root = repo / "docs" / "research" / "docling-graph-kitty-specs" / "data"
    output = data_root / "redaction-manifest.json"
    prior_rows: dict[str, dict[str, object]] = {}
    if output.exists():
        prior = json.loads(output.read_text(encoding="utf-8"))
        prior_rows = {row["path"]: row for row in prior.get("files", []) if "/data/roundtrip/" not in row["path"]}
    replacements = [
        (re.escape(repo.as_posix()), "$REPOSITORY_ROOT", "repository_path"),
        (re.escape(Path.home().as_posix()), "$USER_HOME", "user_home"),
        (r"/private/var/folders/[^\s:'\"]+", "$TEMP_PATH", "temporary_path"),
        (r"/var/folders/[^\s:'\"]+", "$TEMP_PATH", "temporary_path"),
        (
            r"/tmp/docling-(?:operations|privacy|graph-probe)\.[^/\s:'\"]+",  # noqa: S108 - normalization regex
            "$PROBE_TEMP",
            "probe_path",
        ),
        (re.escape(platform.node()), "$HOSTNAME", "hostname"),
    ]
    for path in sorted(data_root.rglob("*")):
        if not path.is_file() or path == output or path.suffix in {".png", ".pdf"}:
            continue
        if path.is_relative_to(data_root / "roundtrip"):
            continue
        original = path.read_bytes()
        try:
            text = original.decode("utf-8")
        except UnicodeDecodeError:
            continue
        categories: dict[str, int] = {}
        normalized = text
        for pattern, replacement, category in replacements:
            normalized, count = re.subn(pattern, replacement, normalized)
            if count:
                categories[category] = categories.get(category, 0) + count
        if normalized == text:
            continue
        normalized_bytes = normalized.encode("utf-8")
        path.write_bytes(normalized_bytes)
        row = {
            "path": path.relative_to(repo).as_posix(),
            "original_sha256": digest(original),
            "published_sha256": digest(normalized_bytes),
            "replacement_categories": categories,
        }
        prior_rows[row["path"]] = row
    manifest = {
        "schema_version": 1,
        "purpose": "publication-safe normalization of machine-specific paths and hostname",
        "content_semantics_changed": False,
        "files": sorted(prior_rows.values(), key=lambda row: str(row["path"])),
    }
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    residual = []
    for path in sorted(data_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if Path.home().as_posix() in text or platform.node() in text or "spec-kitty-20260818" in text:
            residual.append(path.relative_to(repo).as_posix())
    if residual:
        raise SystemExit(f"machine-specific strings remain: {residual}")
    print(json.dumps({"normalized_files": len(prior_rows), "manifest": output.relative_to(repo).as_posix()}))


if __name__ == "__main__":
    main()
