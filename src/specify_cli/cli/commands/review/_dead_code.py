"""Gate 2: Dead-code scan.

Extracted verbatim from src/specify_cli/cli/commands/review.py (WP07).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from rich.console import Console

from ._diagnostics import MissionReviewDiagnostic

_IDENTIFIER_CHARCLASS = r"\w"


def scan_dead_code(
    baseline_merge_commit: str | None,
    repo_root: Path,
    console: Console,
    findings: list[dict[str, str]],
    *,
    mission_id: str | None = None,
    mission_slug: str | None = None,
) -> None:
    """Step 2 — Dead-code scan.

    Appends findings to the provided list and prints to console.

    Issue #989: when ``baseline_merge_commit`` is missing on a **modern**
    mission (one whose ``meta.json`` has ``mission_id`` set, the canonical
    ULID introduced by mission 083), this gate now fails with
    ``LIGHTWEIGHT_REVIEW_MISSING_BASELINE``. Genuinely legacy missions
    (no ``mission_id``) retain the historical skip-pass behavior but are
    tagged with ``LEGACY_MISSION_DEAD_CODE_SKIP`` so the path is greppable
    and the skip cannot be confused with a clean pass.
    """
    if not baseline_merge_commit:
        if mission_id:
            # Modern mission with no baseline → fail-hard (FR-004, FR-005).
            remediation = (
                "Run `spec-kitty merge` to bake baseline_merge_commit into meta.json, "
                "or rerun review with `--mode post-merge` after merge."
            )
            console.print(
                f"  [red]✗[/red]  Dead-code scan: missing baseline_merge_commit "
                f"({MissionReviewDiagnostic.LIGHTWEIGHT_REVIEW_MISSING_BASELINE})"
            )
            console.print(f"       remediation: {remediation}")
            findings.append(
                {
                    "type": "dead_code_baseline_missing",
                    "diagnostic_code": str(
                        MissionReviewDiagnostic.LIGHTWEIGHT_REVIEW_MISSING_BASELINE
                    ),
                    "mission_id": mission_id,
                    "mission_slug": mission_slug or "",
                    "remediation": remediation,
                }
            )
            return
        # Legacy mission (no mission_id) — preserve skip-pass but tag it (FR-006).
        console.print(
            f"  [yellow]⚠[/yellow]  Dead-code scan skipped: no baseline_merge_commit in meta.json"
            f" (legacy / pre-083 mission, {MissionReviewDiagnostic.LEGACY_MISSION_DEAD_CODE_SKIP})"
        )
        return

    diff_result = subprocess.run(
        ["git", "diff", f"{baseline_merge_commit}..HEAD", "--", "src/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    diff_output = diff_result.stdout

    new_symbols: list[tuple[str, str]] = []  # (symbol_name, source_file)
    current_file = ""
    for line in diff_output.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            m = re.match(
                rf"^\+\s*(def|class)\s+([A-Za-z]{_IDENTIFIER_CHARCLASS}*)\s*[\(:]",
                line,
            )
            if m and not m.group(2).startswith("_"):
                new_symbols.append((m.group(2), current_file))

    dead_symbols: list[dict[str, str]] = []
    for symbol, defined_in in new_symbols:
        grep_result = subprocess.run(
            ["grep", "-r", "--include=*.py", "-l", symbol, "src/"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        callers = [
            f
            for f in grep_result.stdout.strip().splitlines()
            if f != defined_in and "test" not in f
        ]
        if not callers:
            dead_symbols.append({"symbol": symbol, "file": defined_in})
            findings.append(
                {"type": "dead_code", "symbol": symbol, "file": defined_in}
            )

    if dead_symbols:
        console.print(
            f"  [red]✗[/red]  Dead-code scan: {len(dead_symbols)} unreferenced public symbol(s)"
        )
        for d in dead_symbols:
            console.print(f"       {d['file']}  {d['symbol']}")
    else:
        console.print(
            "  [green]✓[/green]  Dead-code scan: 0 unreferenced public symbols"
        )
