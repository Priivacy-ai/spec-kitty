#!/usr/bin/env python3
"""Score a recorded B0/B1 answer CSV against original sealed gold."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = [
    "query_id",
    "fixture_id",
    "atom_type",
    "subject",
    "predicate",
    "object",
    "source_path",
    "source_blob",
    "start_byte",
    "end_byte",
    "status",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=["B0", "B1"], required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gold_path = Path(__file__).resolve().parent / "fixtures" / "gold" / "gold-approved.csv"
    with gold_path.open(newline="", encoding="utf-8") as handle:
        gold = list(csv.DictReader(handle))
    with args.answers.open(newline="", encoding="utf-8") as handle:
        answers = list(csv.DictReader(handle))
    expected = sorted(tuple(("asserted" if field == "status" else row[field]) for field in FIELDS) for row in gold)
    actual = sorted(tuple(row.get(field, "") for field in FIELDS) for row in answers)
    result = {
        "schema_version": 1,
        "candidate": args.candidate,
        "pass": expected == actual,
        "expected_count": len(expected),
        "actual_count": len(actual),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
