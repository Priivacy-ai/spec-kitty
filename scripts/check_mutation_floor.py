#!/usr/bin/env python3
"""Advisory mutation score check.

Reads out/reports/mutation/mutation-stats.json (produced by
`mutmut export-cicd-stats`) and reports whether the mutation score
meets the MUTATION_FLOOR threshold.

This script is advisory only — it never fails the CI job.  When the
floor is not met it writes a markdown summary to GITHUB_STEP_SUMMARY
listing the score and notable surviving mutants.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

STATS_FILE = Path("out/reports/mutation/mutation-stats.json")
FLOOR = int(os.environ.get("MUTATION_FLOOR", "0"))
SUMMARY_FILE = os.environ.get("GITHUB_STEP_SUMMARY", "")


def _write_summary(md: str) -> None:
    """Append markdown to the GitHub Actions step summary (if available)."""
    print(md)
    if SUMMARY_FILE:
        with open(SUMMARY_FILE, "a") as f:
            f.write(md + "\n")


def _get_surviving_mutants(limit: int = 20) -> list[str]:
    """Ask mutmut for the list of surviving mutants."""
    try:
        result = subprocess.run(
            ["mutmut", "results"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and not line.startswith("To apply")
        ]
        return lines[:limit]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def main() -> int:
    if not STATS_FILE.exists():
        _write_summary(
            "## Mutation Testing\n\n"
            "⚠️ No mutation stats found — `mutmut export-cicd-stats` may have failed.\n"
        )
        return 0

    try:
        data = json.loads(STATS_FILE.read_text())
    except json.JSONDecodeError as exc:
        _write_summary(
            "## Mutation Testing\n\n"
            f"⚠️ Could not parse stats file: {exc}\n"
        )
        return 0

    summary = data.get("summary", data)
    killed = int(summary.get("killed", 0))
    survived = int(summary.get("survived", 0))
    total_scored = killed + survived

    if total_scored == 0:
        reason = (
            "mutmut crashed or the environment was not prepared correctly"
            if data.get("execution_failed")
            else "no scoreable mutants produced"
        )
        _write_summary(
            "## Mutation Testing\n\n"
            f"⚠️ No scoreable mutants — {reason}.\n"
        )
        return 0

    score_pct = int(killed / total_scored * 100)
    icon = "✅" if score_pct >= FLOOR else "⚠️"
    status = "meets" if score_pct >= FLOOR else "below"

    md = (
        f"## Mutation Testing\n\n"
        f"{icon} **Score: {score_pct}%** ({killed} killed / {total_scored} scoreable) "
        f"— {status} advisory floor of {FLOOR}%\n"
    )

    if score_pct < FLOOR:
        survivors = _get_surviving_mutants()
        if survivors:
            md += "\n<details>\n<summary>Surviving mutants (first 20)</summary>\n\n```\n"
            md += "\n".join(survivors)
            md += "\n```\n</details>\n"

    _write_summary(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
