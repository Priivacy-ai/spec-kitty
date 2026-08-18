#!/usr/bin/env python3
"""Verify the sealed research bundle without importing a candidate."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

import yaml

REQUIRED_CANDIDATE_COLUMNS = {
    "candidate_id",
    "representation",
    "fact_authority_mutation_owner",
    "transform",
    "persistence_location",
    "lifecycle",
    "aggregation_fusion",
    "inference_backend",
    "egress_retention_consent",
    "scope",
    "admissibility_predicate",
    "initial_status",
    "prune_or_scope_rationale",
    "migration_rollback_contract",
    "fact_classes",
    "evidence_status",
}


def command(*args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(args, input=input_bytes, check=True, capture_output=True).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 - sealed artifact-integrity check


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def replace(value: str, replacements: dict[str, str]) -> str:
    for old in sorted(replacements, key=len, reverse=True):
        value = value.replace(old, replacements[old])
    return value


def replace_bytes(data: bytes, replacements: dict[str, str]) -> bytes:
    return replace(data.decode("utf-8"), replacements).encode("utf-8")


def main() -> None:  # noqa: C901 - keep preregistration invariants visible in one audit entry point
    parser = argparse.ArgumentParser()
    parser.add_argument("--preseal", action="store_true")
    args = parser.parse_args()
    research = Path(__file__).resolve().parent
    mission = research.parent
    repo = mission.parents[1]
    query = yaml.safe_load((research / "query-registry.yaml").read_text(encoding="utf-8"))
    revision = query["baseline_revision"]

    plan_bytes = (mission / "plan.md").read_bytes()
    plan_blob = command("git", "hash-object", "--stdin", input_bytes=plan_bytes).decode().strip()
    assert plan_blob == query["plan_blob"], (plan_blob, query["plan_blob"])

    corpus = rows(research / "corpus-manifest.csv")
    exclusions = {
        line.strip() for line in (research / "exploratory-exclusions.txt").read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")
    }
    corpus_paths = {row["path"] for row in corpus}
    assert corpus_paths.isdisjoint(exclusions)
    assert len(corpus_paths) == len(corpus) >= 12
    sampled_missions = Counter(
        row["mission"] for row in corpus if any(reason and not reason.startswith("query_fixture:") for reason in row["selection_reasons"].split(";"))
    )
    assert all(count <= 2 for count in sampled_missions.values()), sampled_missions
    for row in corpus:
        reasons = [value for value in row["selection_reasons"].split(";") if value]
        assert reasons, row["path"]
    for row in corpus:
        data = command("git", "show", f"{revision}:{row['path']}")
        blob = command("git", "hash-object", "--stdin", input_bytes=data).decode().strip()
        assert blob == row["blob_sha"], row["path"]
        assert sha(data) == row["content_sha256"], row["path"]
        assert len(data) == int(row["bytes"]), row["path"]

    exclusion_rows = rows(research / "exploratory-exclusions.csv")
    assert {row["path"] for row in exclusion_rows} == exclusions
    for row in exclusion_rows:
        value = command("git", "rev-parse", f"{revision}:{row['path']}").decode().strip()
        assert value == row["baseline_blob"], row["path"]

    coverage = rows(research / "corpus-coverage.csv")
    required_types = {"mission_type:software-dev", "mission_type:research", "mission_type:documentation"}
    assert required_types.issubset({row["stratum"] for row in coverage})
    for row in coverage:
        if row["selected_path"] != "UNAVAILABLE":
            assert row["selected_path"] in corpus_paths

    gold = rows(research / "fixtures" / "gold" / "gold-approved.csv")
    gold_ids = {row["atom_id"] for row in gold}
    gold_markdown_paths = {row["source_path"] for row in gold if row["source_path"].endswith(".md")}
    assert gold_markdown_paths.issubset(corpus_paths), gold_markdown_paths - corpus_paths
    expected_ids = {atom for item in query["queries"] for atom in item["expected_atoms"]}
    assert gold_ids == expected_ids, (gold_ids - expected_ids, expected_ids - gold_ids)
    for row in gold:
        data = command("git", "show", f"{revision}:{row['source_path']}")
        blob = command("git", "hash-object", "--stdin", input_bytes=data).decode().strip()
        assert blob == row["source_blob"], row["atom_id"]
        start, end = int(row["start_byte"]), int(row["end_byte"])
        assert 0 <= start < end <= len(data), row["atom_id"]
        assert sha(data[start:end]) == row["span_sha256"], row["atom_id"]
        query_row = next(item for item in query["queries"] if item["id"] == row["query_id"])
        assert row["critical"] == ("yes" if query_row["critical"] else "no"), row["atom_id"]

    mutation_files = ("metamorphic-fixtures.yaml", "withheld-mutations.yaml")
    mutations = [mutation for name in mutation_files for mutation in yaml.safe_load((research / "fixtures" / name).read_text(encoding="utf-8"))["mutations"]]
    baseline_data = {row["source_path"]: command("git", "show", f"{revision}:{row['source_path']}") for row in gold}
    for mutation in [{"id": "ORIGINAL", "replacements": {}}] + mutations:
        replacements = mutation["replacements"]
        for row in gold:
            data = baseline_data[row["source_path"]]
            start, end = int(row["start_byte"]), int(row["end_byte"])
            transformed = replace_bytes(data, replacements)
            transformed_span = replace_bytes(data[start:end], replacements)
            transformed_start = len(replace_bytes(data[:start], replacements))
            assert transformed[transformed_start : transformed_start + len(transformed_span)] == transformed_span, (
                mutation["id"],
                row["atom_id"],
            )

    with (research / "candidate-registry.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert set(reader.fieldnames or ()) == REQUIRED_CANDIDATE_COLUMNS
        candidates = list(reader)
    assert len(candidates) == len({row["candidate_id"] for row in candidates})
    for row in candidates:
        assert all(value.strip() for value in row.values()), row["candidate_id"]

    fixture_manifest = json.loads((research / "fixtures" / "golden-markdown" / "fixtures.json").read_text(encoding="utf-8"))
    for fixture in fixture_manifest["fixtures"]:
        assert sha(base64.b64decode(fixture["content_base64"])) == fixture["sha256"]

    gold_hash = sha((research / "fixtures" / "gold" / "gold-approved.csv").read_bytes())
    for name in ("reviewer-a-attestation.md", "reviewer-b-attestation.md", "adjudication.md"):
        text = (research / "fixtures" / "gold" / name).read_text(encoding="utf-8")
        assert gold_hash in text

    identity = yaml.safe_load((research / "fixtures" / "identity-fixtures.yaml").read_text(encoding="utf-8"))
    for fixture in identity["fixtures"]:
        identities = {tuple(value) for value in fixture["inputs"]}
        assert len(identities) == fixture["expected_unique"]

    if args.preseal:
        data_root = repo / "docs" / "research" / "docling-graph-kitty-specs" / "data"
        if data_root.exists():
            forbidden = [path for path in data_root.rglob("*") if path.is_file() and "result" in path.name]
            assert not forbidden, forbidden

    manifest_path = research / "preregistration-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        material = bytearray()
        for entry in manifest["files"]:
            path = repo / entry["path"]
            data = path.read_bytes()
            assert len(data) == entry["bytes"], entry["path"]
            assert sha(data) == entry["sha256"], entry["path"]
            material.extend(entry["path"].encode())
            material.extend(b"\0")
            material.extend(entry["sha256"].encode())
            material.extend(b"\0")
        assert sha(bytes(material)) == manifest["tree_sha256"]

    print(
        json.dumps(
            {
                "status": "pass",
                "corpus_files": len(corpus),
                "gold_atoms": len(gold),
                "candidates": len(candidates),
                "plan_blob": plan_blob,
                "preseal": args.preseal,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
