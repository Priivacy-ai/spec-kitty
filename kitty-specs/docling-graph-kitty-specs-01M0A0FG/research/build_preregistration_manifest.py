#!/usr/bin/env python3
"""Hash the immutable confirmatory bundle; exclude gathering/results ledgers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

FILES = [
    "baseline-procedures.yaml",
    "build_gold.py",
    "build_preregistration_manifest.py",
    "candidate-registry.csv",
    "corpus-coverage.csv",
    "corpus-manifest.csv",
    "evaluate_answers.py",
    "evaluate_recorded_answers.py",
    "exploratory-exclusions.csv",
    "exploratory-exclusions.txt",
    "genericity-protocol.yaml",
    "privacy_candidate.py",
    "probe-procedures.yaml",
    "probe_operations.sh",
    "probe_privacy.sh",
    "probe_roundtrip.py",
    "query-registry.yaml",
    "reviewer-protocol.yaml",
    "select_corpus.py",
    "verify_preregistration.py",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 - sealed cross-repository bundle identity


def main() -> None:
    research = Path(__file__).resolve().parent
    mission = research.parent
    repo = mission.parents[1]
    paths = [research / value for value in FILES]
    paths.extend(sorted((research / "fixtures").rglob("*")))
    paths.extend([mission / "plan.md", mission / "spec.md"])
    paths = sorted({path for path in paths if path.is_file()})
    entries: list[dict[str, int | str]] = []
    tree_material = bytearray()
    for path in paths:
        data = path.read_bytes()
        relative = path.relative_to(repo).as_posix()
        value = digest(data)
        entries.append({"path": relative, "sha256": value, "bytes": len(data)})
        tree_material.extend(relative.encode())
        tree_material.extend(b"\0")
        tree_material.extend(value.encode())
        tree_material.extend(b"\0")
    manifest = {
        "schema_version": 1,
        "sealed_at": "2026-08-18",
        "actor": "/root",
        "spec_kitty_baseline": "cf0f7e3a7",
        "docling_graph_revision": "19815e3147503f78a06e263255667e237830bab9",
        "plan_commit": "4d7a8122875698e32f977d36a03176969a4b6842",
        "plan_blob": "2724af81159191e1382d258fc0701b38b8faee67",
        "candidate_execution_before_seal": False,
        "tree_sha256": digest(bytes(tree_material)),
        "files": entries,
    }
    output = research / "preregistration-manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(entries), "tree_sha256": manifest["tree_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
