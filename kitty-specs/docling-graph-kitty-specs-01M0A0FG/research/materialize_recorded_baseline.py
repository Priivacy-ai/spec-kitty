#!/usr/bin/env python3
"""Replay sealed annotations for format inspection; never score as baseline evidence."""

from __future__ import annotations

import argparse
import csv
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

# Researcher-selected annotations believed to be representable by current readers.
# No reader is invoked here. This set cannot measure exposure, correctness, effort,
# or automation and is retained only to expose the invalid v1 benchmark shape.
B1_STRUCTURED_ATOMS = {
    "A001",
    "A004",
    "A005",
    "A006",
    "A007",
    "A008",
    "A009",
    "A010",
    "A011",
    "A016",
    "A019",
    "A020",
    "A021",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=["B0", "B1"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gold_path = Path(__file__).resolve().parent / "fixtures" / "gold" / "gold-approved.csv"
    with gold_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if args.candidate == "B1":
        rows = [row for row in rows if row["atom_id"] in B1_STRUCTURED_ATOMS]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{field: row[field] for field in FIELDS if field != "status"}, "status": "asserted"})


if __name__ == "__main__":
    main()
