"""Gate 2: Dead-code scan.

Extracted verbatim from src/specify_cli/cli/commands/review.py (WP07).
No behaviour change.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from rich.console import Console

_IDENTIFIER_CHARCLASS = r"\w"


def scan_dead_code(
    baseline_merge_commit: str | None,
    repo_root: Path,
    console: Console,
    findings: list[dict[str, str]],
) -> None:
    """Step 2 — Dead-code scan.

    Appends findings to the provided list and prints to console.
    """
    if not baseline_merge_commit:
        console.print(
            "  [yellow]⚠[/yellow]  Dead-code scan skipped: no baseline_merge_commit in meta.json"
            " (pre-083 mission)"
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
