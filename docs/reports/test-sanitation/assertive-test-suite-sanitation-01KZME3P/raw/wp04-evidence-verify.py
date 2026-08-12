"""Reject duplicate WP04 result fingerprints and verdict-count drift."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
LEDGER = REPORT / "dispositions/WP04.yaml"
RESULTS = HERE / "wp04-results.json"


def consistency_errors(
    groups: list[dict[str, Any]],
    ledger_counts: Counter[str],
    declared_counts: dict[str, int],
) -> list[str]:
    errors: list[str] = []
    fingerprints = [group.get("fingerprint") for group in groups]
    if len(fingerprints) != len(set(fingerprints)):
        errors.append("duplicate fingerprints")
    group_counts = Counter(group.get("verdict") for group in groups)
    if group_counts != ledger_counts:
        errors.append(f"group/ledger count drift: {dict(group_counts)} != {dict(ledger_counts)}")
    if group_counts != Counter(declared_counts):
        errors.append(f"group/declared count drift: {dict(group_counts)} != {declared_counts}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    ledger = yaml.safe_load(LEDGER.read_text())
    results = json.loads(RESULTS.read_text())
    groups = results["groups"]
    ledger_counts = Counter(row["verdict"] for row in ledger["dispositions"])
    errors = consistency_errors(groups, ledger_counts, results["verdict_counts"])

    duplicate_fixture = [*groups, groups[0]]
    duplicate_rejected = "duplicate fingerprints" in consistency_errors(duplicate_fixture, ledger_counts, results["verdict_counts"])
    drift_fixture = dict(results["verdict_counts"])
    drift_fixture["KEEP"] += 1
    drift_rejected = any("declared count drift" in error for error in consistency_errors(groups, ledger_counts, drift_fixture))
    if not duplicate_rejected or not drift_rejected:
        errors.append("negative consistency selftest failed")

    record = {
        "schema_version": "wp04-evidence-consistency/v1",
        "verifier_path": Path(__file__).resolve().relative_to(Path.cwd()).as_posix(),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),  # noqa: TID251 - evidence integrity
        "ledger_path": LEDGER.relative_to(Path.cwd()).as_posix(),
        "ledger_sha256": hashlib.sha256(LEDGER.read_bytes()).hexdigest(),  # noqa: TID251 - evidence integrity
        "results_path": RESULTS.relative_to(Path.cwd()).as_posix(),
        "results_sha256": hashlib.sha256(RESULTS.read_bytes()).hexdigest(),  # noqa: TID251 - evidence integrity
        "group_rows": len(groups),
        "unique_fingerprints": len({group["fingerprint"] for group in groups}),
        "verdict_counts": dict(ledger_counts),
        "duplicate_fixture_rejected": duplicate_rejected,
        "count_drift_fixture_rejected": drift_rejected,
        "errors": errors,
        "valid": not errors,
    }
    args.receipt.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
