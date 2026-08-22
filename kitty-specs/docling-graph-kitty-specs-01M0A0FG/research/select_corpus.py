#!/usr/bin/env python3
"""Deterministically select a confirmatory Markdown corpus from a Git tree."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

BASELINE = "cf0f7e3a7"
MAX_PER_MISSION = 2
MIN_UNIQUE = 12
MAX_RUNNABLE_BYTES = 2 * 1024 * 1024
MISSION = "docling-graph-kitty-specs-01M0A0FG"
QUERY_FIXTURE_PATHS = {
    "F-GOLD-A001": "kitty-specs/execution-context-unification-01KTPKST/tasks/WP12-sync-daemon-singleton-reaper.md",
    "F-GOLD-A015": "kitty-specs/execution-context-unification-01KTPKST/spec.md",
    "F-EXEC-WP12": "kitty-specs/execution-context-unification-01KTPKST/tasks/WP12-sync-daemon-singleton-reaper/review-cycle-2.md",
    "F-WORKTREE-WP02": "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
    "F-GATE-PREPLAN": "kitty-specs/gate-read-surface-completion-01KVW9B0/research/priti-preplan.md",
    "F-ID-COLLISION": "kitty-specs/test-suite-friction-remediation-01KXDKBX/spec.md",
}
FEATURES = {
    "frontmatter": r"^---$",
    "table": r"^\|.*\|\s*$",
    "fence": r"^```",
    "link": r"\[[^]]+\]\([^)]+\)",
    "html_comment": r"<!--",
    "checkbox": r"^\s*[-*] \[[ xX]\]",
    "non_ascii": r"[^\x00-\x7F]",
    "cross_file_id": r"(FR|WP|AC|DR|QR|SC|NFR)-?[0-9]+",
}
LEGACY_RE = re.compile(r"^\d{3}-")
ULID_RE = re.compile(r"-[0-9A-HJKMNP-TV-Z]{8,}(?:-|$)")


@dataclass
class Item:
    mode: str
    blob: str
    size: int
    path: str
    mission: str
    role: str
    era: str
    mission_type: str = "unknown"
    topology: str = "unknown"
    mission_acceptance: str = "unknown"
    content_sha256: str = ""
    features: set[str] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)


def git(*args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(["git", *args], check=True, capture_output=True)
    return result.stdout if binary else result.stdout.decode("utf-8", errors="strict")


def classify_role(path: str) -> str:
    name = Path(path).name
    if name == "spec.md":
        return "spec"
    if name == "plan.md":
        return "plan"
    if name == "tasks.md":
        return "tasks"
    if re.fullmatch(r"review-cycle-\d+\.md", name):
        return "wp_review"
    if "/tasks/WP" in path:
        return "wp_prompt"
    if name in {"research.md", "findings.md"} or "/research/" in path:
        return "research_findings"
    return "other"


def parse_meta(revision: str, mission: str) -> tuple[str, str, str]:
    try:
        raw = git("show", f"{revision}:kitty-specs/{mission}/meta.json")
        data = json.loads(str(raw))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return "unknown", "unknown", "unknown"
    mission_type = str(data.get("mission_type") or data.get("type") or "unknown")
    topology = str(data.get("topology") or data.get("coordination", {}).get("topology") or "unknown")
    acceptance = "accepted" if data.get("accepted_at") or data.get("acceptance_history") else "not_accepted"
    return mission_type, topology, acceptance


def content_hashes(blobs: list[str]) -> dict[str, str]:
    unique = sorted(set(blobs))
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        input=("\n".join(unique) + "\n").encode(),
        check=True,
        capture_output=True,
    ).stdout
    cursor = 0
    hashes: dict[str, str] = {}
    for expected in unique:
        line_end = result.index(b"\n", cursor)
        header = result[cursor:line_end].decode().split()
        if header[:2] != [expected, "blob"]:
            raise RuntimeError(f"unexpected cat-file header: {header}")
        size = int(header[2])
        start = line_end + 1
        end = start + size
        hashes[expected] = hashlib.sha256(  # noqa: TID251 - frozen corpus content identity
            result[start:end]
        ).hexdigest()
        if result[end : end + 1] != b"\n":
            raise RuntimeError("invalid cat-file batch framing")
        cursor = end + 1
    return hashes


def grep_feature(revision: str, pattern: str) -> set[str]:
    result = subprocess.run(
        ["git", "grep", "-I", "-l", "-E", pattern, revision, "--", "kitty-specs/**/*.md"],
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr)
    prefix = f"{revision}:"
    return {line.removeprefix(prefix) for line in result.stdout.splitlines()}


def load_items(root: Path, revision: str) -> list[Item]:
    exclusions = {line.strip() for line in (root / "research" / "exploratory-exclusions.txt").read_text().splitlines() if line.strip() and not line.startswith("#")}
    raw = git("ls-tree", "-r", "-z", "--long", revision, "--", "kitty-specs", binary=True)
    items: list[Item] = []
    for record in bytes(raw).split(b"\0"):
        if not record:
            continue
        header, path_b = record.split(b"\t", 1)
        mode_b, _kind, blob_b, size_b = header.split()
        path = path_b.decode()
        if not path.endswith(".md") or path in exclusions or f"kitty-specs/{MISSION}/" in path:
            continue
        parts = Path(path).parts
        mission = parts[1] if len(parts) > 2 else "unknown"
        era = "legacy" if LEGACY_RE.search(mission) else ("ulid" if ULID_RE.search(mission) else "other")
        items.append(
            Item(
                mode_b.decode(),
                blob_b.decode(),
                int(size_b),
                path,
                mission,
                classify_role(path),
                era,
            )
        )
    metadata = {mission: parse_meta(revision, mission) for mission in sorted({item.mission for item in items})}
    hashes = content_hashes([item.blob for item in items])
    for item in items:
        item.mission_type, item.topology, item.mission_acceptance = metadata[item.mission]
        item.content_sha256 = hashes[item.blob]
    by_path = {item.path: item for item in items}
    for name, pattern in FEATURES.items():
        for path in grep_feature(revision, pattern):
            if path in by_path:
                by_path[path].features.add(name)
    return items


def select(items: list[Item]) -> tuple[list[Item], list[tuple[str, str]]]:  # noqa: C901 - frozen strata stay visible in one selector
    chosen: dict[str, Item] = {}
    mission_counts: defaultdict[str, int] = defaultdict(int)
    coverage: list[tuple[str, str]] = []

    def take(
        reason: str,
        candidates: list[Item],
        *,
        presorted: bool = False,
        allow_mission_overflow: bool = False,
    ) -> None:
        ordered = candidates if presorted else sorted(candidates, key=lambda item: (item.content_sha256, item.path))
        selected = next(
            (item for item in ordered if item.path not in chosen and (allow_mission_overflow or mission_counts[item.mission] < MAX_PER_MISSION)),
            None,
        )
        if selected is None:
            selected = next((item for item in ordered if item.path in chosen), None)
        if selected is None:
            coverage.append((reason, "UNAVAILABLE"))
            return
        if selected.path not in chosen:
            chosen[selected.path] = selected
            mission_counts[selected.mission] += 1
        if reason not in selected.reasons:
            selected.reasons.append(reason)
        coverage.append((reason, selected.path))

    for role in ("spec", "plan", "tasks", "wp_prompt", "wp_review", "research_findings", "other"):
        take(f"role:{role}", [item for item in items if item.role == role])
    for era in ("legacy", "ulid"):
        take(f"era:{era}", [item for item in items if item.era == era])
    for mission_type in ("software-dev", "research", "documentation"):
        take(f"mission_type:{mission_type}", [item for item in items if item.mission_type == mission_type])
    for fixture_id, path in QUERY_FIXTURE_PATHS.items():
        take(
            f"query_fixture:{fixture_id}",
            [item for item in items if item.path == path],
            allow_mission_overflow=True,
        )

    by_size = sorted(items, key=lambda item: (item.size, item.path))
    for name, percentile in (("small", 0.0), ("median", 0.5), ("p90", 0.9)):
        rank = max(0, math.ceil(percentile * len(by_size)) - 1)
        target = by_size[rank].size
        take(
            f"size:{name}",
            sorted(items, key=lambda item: (abs(item.size - target), item.content_sha256, item.path)),
            presorted=True,
        )
    take(
        "size:large_runnable",
        sorted(
            (item for item in items if item.size <= MAX_RUNNABLE_BYTES),
            key=lambda item: (-item.size, item.content_sha256, item.path),
        ),
        presorted=True,
    )

    for topology in sorted({item.topology for item in items if item.topology != "unknown"}):
        take(f"topology:{topology}", [item for item in items if item.topology == topology])
    for acceptance in ("accepted", "not_accepted"):
        take(
            f"mission_acceptance:{acceptance}",
            [item for item in items if item.mission_acceptance == acceptance],
        )
    for feature in FEATURES:
        take(f"syntax:{feature}", [item for item in items if feature in item.features])
    take("control:no_target_syntax", [item for item in items if not item.features])

    for item in sorted(items, key=lambda candidate: (candidate.content_sha256, candidate.path)):
        if len(chosen) >= MIN_UNIQUE:
            break
        if item.path not in chosen and mission_counts[item.mission] < MAX_PER_MISSION:
            chosen[item.path] = item
            mission_counts[item.mission] += 1
            item.reasons.append("minimum_unique_fill")
    return sorted(chosen.values(), key=lambda item: item.path), coverage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default=BASELINE)
    parser.add_argument("--mission-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coverage-output", type=Path, required=True)
    args = parser.parse_args()
    items = load_items(args.mission_root, args.revision)
    selected, coverage = select(items)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "revision",
                "path",
                "blob_sha",
                "content_sha256",
                "bytes",
                "mission",
                "role",
                "era",
                "mission_type",
                "topology",
                "mission_acceptance",
                "features",
                "selection_reasons",
            ]
        )
        for item in selected:
            writer.writerow(
                [
                    args.revision,
                    item.path,
                    item.blob,
                    item.content_sha256,
                    item.size,
                    item.mission,
                    item.role,
                    item.era,
                    item.mission_type,
                    item.topology,
                    item.mission_acceptance,
                    ";".join(sorted(item.features)),
                    ";".join(item.reasons),
                ]
            )
    with args.coverage_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stratum", "selected_path"])
        writer.writerows(coverage)


if __name__ == "__main__":
    main()
