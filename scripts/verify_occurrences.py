#!/usr/bin/env python3
"""Verify a Phase-1 excision occurrence-classification artifact.

Loads an artifact YAML (per-WP or mission-level index), walks each category
(or must_be_zero assertion), greps the repo for each target literal string in
scope respecting include/exclude globs and permitted exceptions, and fails if
the number of hits does not match ``expected_final_count`` (per-WP) or
``final_count`` (index).

Exit codes
----------
0
    All assertions green.
1
    At least one assertion violated.
2
    Usage error (missing/invalid argument) or unreadable artifact.

This script is deliberately dependency-light: it only imports ``ruamel.yaml``,
which is already in the project runtime set.
"""
from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_artifact(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    data = yaml.load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Artifact at {path} is not a YAML mapping")
    return data


def _iter_candidate_files(include_globs: list[str]) -> list[Path]:
    """Expand include_globs into concrete files under REPO_ROOT."""
    seen: set[Path] = set()
    for pattern in include_globs:
        # Path.glob handles '**' recursion and relative patterns.
        for match in REPO_ROOT.glob(pattern):
            if match.is_file():
                seen.add(match)
    return sorted(seen)


def _matches_any_glob(rel_path: str, globs: list[str]) -> bool:
    for pattern in globs:
        # fnmatch gives us classic glob semantics; also try an anchored prefix
        # so a pattern like 'src/doctrine/**' matches any descendant.
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if pattern.endswith("/**") and rel_path.startswith(pattern[:-3] + "/"):
            return True
        if pattern.endswith("**") and rel_path.startswith(pattern[:-2]):
            return True
    return False


def _is_permitted(
    rel_path: str,
    line: str,
    permitted_patterns: list[str],
) -> bool:
    """Return True if this hit should be ignored per permitted_exceptions.

    A pattern is permitted when it matches the file path as a glob, when the
    pattern appears as a literal substring of the file path, or when the
    pattern equals the matched line exactly.
    """
    for pattern in permitted_patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if pattern in rel_path:
            return True
        if pattern == line:
            return True
    return False


def _grep_in_scope(
    literal: str,
    include_globs: list[str],
    exclude_globs: list[str],
) -> list[tuple[str, int, str]]:
    """Return (relpath, line_number, line) for every occurrence of ``literal``
    in files matched by ``include_globs`` and not matched by ``exclude_globs``.
    """
    hits: list[tuple[str, int, str]] = []
    for file_path in _iter_candidate_files(include_globs):
        try:
            rel = file_path.relative_to(REPO_ROOT)
        except ValueError:
            continue
        rel_str = str(rel)
        if _matches_any_glob(rel_str, exclude_globs):
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            if literal in line:
                hits.append((rel_str, lineno, line.rstrip()))
    return hits


def _verify_per_wp(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    permitted_patterns = [
        entry["pattern"] for entry in artifact.get("permitted_exceptions") or []
    ]
    wp_id = artifact.get("wp_id", "<unknown>")
    categories = artifact.get("categories") or []
    if not isinstance(categories, list) or not categories:
        failures.append(f"{wp_id}: 'categories' is empty or missing")
        return failures
    for cat in categories:
        name = cat.get("name", "<unnamed>")
        include_globs = cat.get("include_globs") or []
        exclude_globs = cat.get("exclude_globs") or []
        expected = int(cat.get("expected_final_count", 0))
        for literal in cat.get("strings") or []:
            hits = _grep_in_scope(literal, include_globs, exclude_globs)
            real_hits = [
                h for h in hits if not _is_permitted(h[0], h[2], permitted_patterns)
            ]
            if len(real_hits) != expected:
                failures.append(
                    f"{wp_id} category '{name}' string '{literal}': "
                    f"{len(real_hits)} hits, expected {expected}"
                )
                for h in real_hits[:10]:
                    failures.append(f"    {h[0]}:{h[1]}  {h[2]}")
    return failures


def _verify_index(artifact: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    permitted_patterns = [
        entry["pattern"] for entry in artifact.get("permitted_exceptions") or []
    ]
    assertions = artifact.get("must_be_zero") or []
    if not isinstance(assertions, list) or not assertions:
        failures.append("index: 'must_be_zero' is empty or missing")
        return failures
    for assertion in assertions:
        literal = assertion["literal"]
        include_globs = assertion.get("scopes") or []
        exclude_globs = assertion.get("excluding") or []
        expected = int(assertion.get("final_count", 0))
        hits = _grep_in_scope(literal, include_globs, exclude_globs)
        real_hits = [
            h for h in hits if not _is_permitted(h[0], h[2], permitted_patterns)
        ]
        if len(real_hits) != expected:
            failures.append(
                f"index must_be_zero literal '{literal}': "
                f"{len(real_hits)} hits, expected {expected}"
            )
            for h in real_hits[:10]:
                failures.append(f"    {h[0]}:{h[1]}  {h[2]}")
    return failures


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: verify_occurrences.py <artifact.yaml>", file=sys.stderr)
        return 2
    artifact_path = Path(argv[1])
    if not artifact_path.is_file():
        print(f"Artifact not found: {artifact_path}", file=sys.stderr)
        return 2
    try:
        artifact = _load_artifact(artifact_path)
    except Exception as exc:  # noqa: BLE001 - surface any parse error
        print(f"Failed to load artifact {artifact_path}: {exc}", file=sys.stderr)
        return 2

    is_index = "wps" in artifact and "must_be_zero" in artifact
    if is_index:
        failures = _verify_index(artifact)
    else:
        failures = _verify_per_wp(artifact)

    rel = os.path.relpath(artifact_path, REPO_ROOT)
    if failures:
        print("VERIFIER FAILED")
        print(f"  artifact: {rel}")
        for line in failures:
            print(line)
        return 1
    print(f"VERIFIER GREEN for {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
