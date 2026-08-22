#!/usr/bin/env python3
"""Build a compact, reproducible synthesis input from raw result artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 - result identity


def timing(path: Path) -> tuple[float, int]:
    text = path.read_text(encoding="utf-8")
    seconds = float(re.search(r"^real ([0-9.]+)$", text, re.MULTILINE).group(1))  # type: ignore[union-attr]
    rss = int(
        re.search(r"^\s*([0-9]+)\s+maximum resident set size$", text, re.MULTILINE).group(1)  # type: ignore[union-attr]
    )
    return seconds, rss


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    mission = repo / "kitty-specs" / "docling-graph-kitty-specs-01M0A0FG"
    data = repo / "docs" / "research" / "docling-graph-kitty-specs" / "data"
    roundtrip_path = data / "roundtrip" / "roundtrip-results.json"
    roundtrip = json.loads(roundtrip_path.read_text(encoding="utf-8"))
    first = [row for row in roundtrip["results"] if row["repetition"] == 1]
    unique_span_failures = sorted(atom for row in first for atom, status in row["gold_span_oracles"].items() if status == "FAIL")
    span_statuses = [status for row in first for status in row["gold_span_oracles"].values()]
    feature_failures = sum(value["status"] == "FAIL" for row in first for value in row["feature_oracles"].values())
    storage_path = data / "document-storage.json"
    storage = json.loads(storage_path.read_text(encoding="utf-8"))
    census_path = data / "corpus-census.json"
    census = json.loads(census_path.read_text(encoding="utf-8"))
    operations = data / "operations"
    import_metrics = [timing(operations / f"import-{index}.time.txt") for index in range(1, 6)]
    version_metrics = [timing(operations / f"version-{index}.time.txt") for index in range(1, 6)]
    audit = json.loads((operations / "pip-audit.json").read_text(encoding="utf-8"))
    B0_path = mission / "research" / "results" / "B0-evaluation.json"
    B1_path = mission / "research" / "results" / "B1-evaluation.json"
    summary = {
        "schema_version": 1,
        "structural": {
            "unique_inputs": len(first),
            "total_trials": len(roundtrip["results"]),
            "exact_byte_matches": sum(row["same_bytes"] for row in roundtrip["results"]),
            "conversion_errors": sum(row["error"] is not None for row in roundtrip["results"]),
            "unstable_repeats": sum(not row["repeat_same_as_previous"] for row in roundtrip["results"]),
            "gold_span_failure_atoms": unique_span_failures,
            "gold_span_failure_count": len(unique_span_failures),
            "gold_markdown_applicable_atoms": len(span_statuses),
            "gold_span_pass_count": sum(status == "PASS" for status in span_statuses),
            "gold_non_markdown_atoms_not_applicable": 2,
            "first_run_feature_count_failures": feature_failures,
            "raw_sha256": digest(roundtrip_path),
        },
        "storage_supplementary": {**storage["summary"], "raw_sha256": digest(storage_path)},
        "operations_macos_arm64": {
            "installed_distributions": len(json.loads((operations / "packages.json").read_text())),
            "install_delta_bytes": int((operations / "install-delta-bytes.txt").read_text()),
            "first_import_seconds": import_metrics[0][0],
            "first_import_peak_rss_bytes": import_metrics[0][1],
            "warm_import_seconds_median": statistics.median(value[0] for value in import_metrics[1:]),
            "warm_import_peak_rss_bytes_median": statistics.median(value[1] for value in import_metrics[1:]),
            "version_seconds_median": statistics.median(value[0] for value in version_metrics),
            "dated_known_vulnerabilities": sum(len(dependency.get("vulns", [])) for dependency in audit.get("dependencies", [])),
            "license_rows": len(json.loads((operations / "licenses.json").read_text())),
        },
        "privacy": {
            "containment_compatibility": "FAIL",
            "conversion_privacy_behavior": "UNKNOWN",
            "network_behavior": "UNKNOWN",
            "filesystem_behavior": "UNKNOWN",
            "canary_residue_evidence": "NOT_APPLICABLE_candidate_never_started",
            "contract_failures": (data / "privacy" / "execution-contract-failures.txt").read_text().splitlines(),
            "interpretation": "Strict confinement blocked dependency startup at /dev/null before conversion; this is neither leakage nor cleanup evidence.",
        },
        "descriptive_annotation_replays_not_performance_evidence": {
            "B0": json.loads(B0_path.read_text(encoding="utf-8")),
            "B1": json.loads(B1_path.read_text(encoding="utf-8")),
            "interpretation": "Rows were materialized from sealed gold; they do not measure a reader, automation, timing, correctness, or user effort.",
        },
        "semantic": json.loads((data / "semantic-backend-status.json").read_text(encoding="utf-8")),
        "corpus": census["population"],
        "claim_limits": [
            "No end-user demand or production utility study",
            "No Linux or Windows execution",
            "No semantic extraction without approved local generative backend",
            "No fair executable B2/C5a utility benchmark under sealed v1 candidate API",
            "B0/B1 outputs are annotation replays, not baseline performance evidence",
            "No full integration latency or cold-network/cache/model-footprint measurement",
            "Supplementary storage observation was not a preregistered threshold result",
        ],
    }
    output = data / "results-summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": digest(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
