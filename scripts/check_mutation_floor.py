#!/usr/bin/env python3
"""Enforce a minimum mutation score floor.

Reads out/reports/mutation/mutation-stats.json (produced by
`mutmut export-cicd-stats`) and exits non-zero if the mutation score
falls below the MUTATION_FLOOR environment variable (integer 0-100, default 0).

Edge cases handled:
- Missing JSON file: exits 1 with a clear error
- Malformed JSON: exits 1 with a clear error
- Zero scoreable mutants (killed + survived == 0): exits 0 with a warning
- Score below floor: exits 1 with a descriptive message
"""
import json
import os
import sys
from pathlib import Path

STATS_FILE = Path("out/reports/mutation/mutation-stats.json")
FLOOR = int(os.environ.get("MUTATION_FLOOR", "0"))


def main() -> int:
    if not STATS_FILE.exists():
        print(
            f"ERROR: stats file not found at {STATS_FILE}",
            file=sys.stderr,
        )
        print(
            "Ensure `mutmut export-cicd-stats` ran before this script.",
            file=sys.stderr,
        )
        return 1

    try:
        data = json.loads(STATS_FILE.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: could not parse {STATS_FILE}: {exc}", file=sys.stderr)
        print(f"Raw content: {STATS_FILE.read_text()[:200]}", file=sys.stderr)
        return 1

    # Support both flat schema and nested-under-summary schema variants
    # to handle any differences across mutmut 3.x patch versions.
    summary = data.get("summary", data)
    killed = int(summary.get("killed", 0))
    survived = int(summary.get("survived", 0))
    total_scored = killed + survived

    if total_scored == 0:
        print(
            "WARNING: no scoreable mutants (killed + survived == 0). "
            "Skipping floor check — nothing to score.",
        )
        return 0

    score_pct = int(killed / total_scored * 100)
    print(f"Mutation score: {score_pct}%  ({killed} killed / {total_scored} scoreable)")
    print(f"Floor:          {FLOOR}%")

    if score_pct < FLOOR:
        print(
            f"\nFAIL: mutation score {score_pct}% is below the configured "
            f"floor of {FLOOR}%.",
            file=sys.stderr,
        )
        print(
            "Run the squashing campaign (WP03/WP04) and raise MUTATION_FLOOR "
            "in ci-quality.yml once the baseline is established.",
            file=sys.stderr,
        )
        return 1

    print("\nPASS: mutation score meets or exceeds the floor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
