#!/usr/bin/env python3
"""Inventory the frozen tracked kitty-specs population without a checkout walk."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath

PATTERNS = {
    "table_rows": re.compile(r"^\|.*\|\s*$", re.MULTILINE),
    "checkboxes": re.compile(r"^\s*[-*] \[[ xX]\]", re.MULTILINE),
    "fences": re.compile(r"^```", re.MULTILINE),
    "html_comments": re.compile(r"<!--", re.MULTILINE),
    "wiki_links": re.compile(r"\[\[[^]]+\]\]"),
    "markdown_links": re.compile(r"\[[^]]+\]\([^)]+\)"),
    "cross_file_ids": re.compile(r"\b(?:FR|WP|AC|DR|QR|SC|NFR)-?[0-9]+\b"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="cf0f7e3a7")
    parser.add_argument("--exclude-mission", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--long", args.revision, "--", "kitty-specs"],
        check=True,
        capture_output=True,
    ).stdout
    items: list[tuple[str, int, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, encoded_path = record.split(b"\t", 1)
        _mode, kind, blob, size = header.split()
        path = encoded_path.decode()
        if kind != b"blob" or f"kitty-specs/{args.exclude_mission}/" in path:
            continue
        items.append((blob.decode(), int(size), path))

    extension_files: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    basenames: Counter[str] = Counter()
    mission_names: set[str] = set()
    for _blob, size, path in items:
        suffix = PurePosixPath(path).suffix.lower() or "<none>"
        extension_files[suffix] += 1
        extension_bytes[suffix] += size
        basenames[PurePosixPath(path).name] += 1
        parts = PurePosixPath(path).parts
        if len(parts) > 2:
            mission_names.add(parts[1])

    markdown = [(blob, path) for blob, _size, path in items if path.endswith(".md")]
    batch = subprocess.run(
        ["git", "cat-file", "--batch"],
        input=("\n".join(blob for blob, _path in markdown) + "\n").encode(),
        check=True,
        capture_output=True,
    ).stdout
    cursor = 0
    syntax_occurrences: Counter[str] = Counter()
    syntax_files: Counter[str] = Counter()
    for expected_blob, path in markdown:
        line_end = batch.index(b"\n", cursor)
        actual_blob, kind, encoded_size = batch[cursor:line_end].decode().split()
        if actual_blob != expected_blob or kind != "blob":
            raise RuntimeError(f"unexpected cat-file frame for {path}")
        size = int(encoded_size)
        start = line_end + 1
        end = start + size
        text = batch[start:end].decode("utf-8", errors="replace")
        for name, pattern in PATTERNS.items():
            count = len(pattern.findall(text))
            syntax_occurrences[name] += count
            syntax_files[name] += bool(count)
        non_ascii = sum(ord(character) > 127 for character in text)
        syntax_occurrences["non_ascii_characters"] += non_ascii
        syntax_files["non_ascii_characters"] += bool(non_ascii)
        cursor = end + 1

    result = {
        "schema_version": 1,
        "revision": args.revision,
        "selector": "git ls-tree -r -z --long; git cat-file --batch",
        "excluded_mission": args.exclude_mission,
        "population": {
            "mission_directories": len(mission_names),
            "tracked_files": len(items),
            "tracked_bytes": sum(size for _blob, size, _path in items),
        },
        "extensions": {key: {"files": extension_files[key], "bytes": extension_bytes[key]} for key in sorted(extension_files)},
        "authority_basenames": {
            name: basenames[name]
            for name in (
                "meta.json",
                "spec.md",
                "plan.md",
                "tasks.md",
                "wps.yaml",
                "status.events.jsonl",
                "status.json",
                "mission-events.jsonl",
                "acceptance-matrix.json",
                "retrospective.yaml",
            )
        },
        "markdown_syntax_occurrences": dict(sorted(syntax_occurrences.items())),
        "markdown_files_with_syntax": dict(sorted(syntax_files.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["population"], sort_keys=True))


if __name__ == "__main__":
    main()
