#!/usr/bin/env python3
"""Hash-bind each executed probe to its invocation, environment, and seal."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

SEAL_COMMIT = "e6fcdb4ba96f8e3da0a2d4b22595ada602290232"
SEAL_TREE = "15bb54c3989210ec095123d520f5c4a2a327bace9d40fc6bcadcd8190e73cf33"
BASELINE = "cf0f7e3a7db149f8b73006f9bca8bb97df880704"
DOCLING_GRAPH = "19815e3147503f78a06e263255667e237830bab9"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 - publication integrity


def entry(path: Path, repo: Path) -> dict[str, int | str]:
    return {
        "path": path.relative_to(repo).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha(path),
    }


def write_manifest(
    *,
    repo: Path,
    output: Path,
    probe_id: str,
    scope: str,
    commands: list[str],
    procedure: Path | None,
    files: list[Path],
    environment: dict[str, str],
) -> None:
    files = sorted(path for path in files if path.is_file() and path != output)
    mtimes = [datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat() for path in files]
    manifest = {
        "schema_version": 1,
        "probe_id": probe_id,
        "scope": scope,
        "manifest_created_at": "2026-08-18",
        "result_mtime_range_utc": [min(mtimes), max(mtimes)],
        "executed_after_seal": True,
        "preregistration_commit": SEAL_COMMIT,
        "preregistration_tree_sha256": SEAL_TREE,
        "spec_kitty_revision": BASELINE,
        "docling_graph_revision": DOCLING_GRAPH,
        "commands": commands,
        "working_directory": "$REPOSITORY_ROOT",
        "environment": environment,
        "procedure": entry(procedure, repo) if procedure else None,
        "files": [entry(path, repo) for path in files],
    }
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    mission = repo / "kitty-specs" / "docling-graph-kitty-specs-01M0A0FG"
    research = mission / "research"
    data = repo / "docs" / "research" / "docling-graph-kitty-specs" / "data"
    common = {
        "platform": "macOS 15.7.7 arm64 Darwin 24.6.0",
        "python": "3.11.11",
        "docling_graph": "1.9.1",
        "docling": "2.120.3",
        "docling_core": "2.91.0",
    }
    roundtrip = data / "roundtrip"
    probe_python = Path("/tmp/docling-graph-probe.ucoiUH/env/bin/python")  # noqa: S108 - recorded probe environment
    packages = json.loads(
        subprocess.check_output(
            ["uv", "pip", "list", "--python", probe_python.as_posix(), "--format", "json"],
            text=True,
        )
    )
    (roundtrip / "environment-packages.json").write_text(
        json.dumps(sorted(packages, key=lambda item: item["name"].lower()), indent=2) + "\n",
        encoding="utf-8",
    )
    write_manifest(
        repo=repo,
        output=roundtrip / "execution-manifest.json",
        probe_id="confirmatory-structural-roundtrip",
        scope="sealed_confirmatory",
        commands=[
            "$PROBE_ENV/bin/python "
            "kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/probe_roundtrip.py "
            "--manifest kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/corpus-manifest.csv "
            "--fixtures kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/fixtures/golden-markdown/fixtures.json "
            "--gold kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/fixtures/gold/gold-approved.csv "
            "--output-dir docs/research/docling-graph-kitty-specs/data/roundtrip --repetitions 3"
        ],
        procedure=research / "probe_roundtrip.py",
        files=list(roundtrip.rglob("*")),
        environment=common,
    )
    operations = data / "operations"
    write_manifest(
        repo=repo,
        output=operations / "execution-manifest.json",
        probe_id="bounded-operations",
        scope="sealed_confirmatory_bounded_macos_only",
        commands=[
            "kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/probe_operations.sh "
            "../sources/docling-graph docs/research/docling-graph-kitty-specs/data/operations"
        ],
        procedure=research / "probe_operations.sh",
        files=list(operations.rglob("*")),
        environment={**common, "uv": (operations / "uv-version.txt").read_text().strip()},
    )
    privacy = data / "privacy"
    write_manifest(
        repo=repo,
        output=privacy / "execution-manifest.json",
        probe_id="privacy-confinement",
        scope="sealed_confirmatory_blocked_before_conversion",
        commands=[
            "kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/probe_privacy.sh "
            "$PROBE_ENV/bin/python "
            "kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/privacy_candidate.py "
            "docs/research/docling-graph-kitty-specs/data/privacy"
        ],
        procedure=research / "probe_privacy.sh",
        files=list(privacy.rglob("*")),
        environment=common,
    )
    semantic = data / "semantic"
    write_manifest(
        repo=repo,
        output=semantic / "execution-manifest.json",
        probe_id="semantic-backend-availability",
        scope="environment_inventory_no_candidate_execution",
        commands=["ollama --version", "ollama list"],
        procedure=None,
        files=[*semantic.rglob("*"), data / "semantic-backend-status.json"],
        environment={"platform": common["platform"], "ollama": "0.24.0"},
    )
    write_manifest(
        repo=repo,
        output=data / "document-storage-execution-manifest.json",
        probe_id="supplementary-doclingdocument-storage",
        scope="supplementary_postseal_not_preregistered",
        commands=[
            "$PROBE_ENV/bin/python "
            "kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/probe_document_storage.py "
            "--manifest kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/corpus-manifest.csv "
            "--output docs/research/docling-graph-kitty-specs/data/document-storage.json"
        ],
        procedure=research / "probe_document_storage.py",
        files=[data / "document-storage.json"],
        environment=common,
    )
    write_manifest(
        repo=repo,
        output=data / "corpus-census-execution-manifest.json",
        probe_id="frozen-corpus-census",
        scope="repository_forensics",
        commands=[
            ".venv/bin/python kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/corpus_census.py "
            "--revision cf0f7e3a7 --exclude-mission docling-graph-kitty-specs-01M0A0FG "
            "--output docs/research/docling-graph-kitty-specs/data/corpus-census.json"
        ],
        procedure=research / "corpus_census.py",
        files=[data / "corpus-census.json"],
        environment={"platform": common["platform"], "python": common["python"]},
    )
    print("execution manifests written")


if __name__ == "__main__":
    main()
