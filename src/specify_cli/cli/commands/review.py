"""spec-kitty review --mission <handle>: Post-merge mission validation gate.

Performs four checks and writes kitty-specs/<slug>/mission-review-report.md:

1. WP lane check — all WPs must be in ``done`` (hard failure if not).
2. Dead-code scan — heuristic grep for new public symbols introduced by the
   mission diff that have no non-test callers.  Requires ``baseline_merge_commit``
   in meta.json (absent for pre-083 missions → step is skipped with a warning).
3. BLE001 audit — flags ``# noqa: BLE001`` suppressions in ``auth/`` and
   ``cli/commands/`` that lack inline justification text.
4. Report writer — writes ``mission-review-report.md`` with YAML frontmatter
   containing ``verdict``, ``reviewed_at``, and ``findings`` count.

Verdict enum:
  pass             — all checks clean
  pass_with_notes  — informational findings only (no WP lane failures)
  fail             — one or more WPs not in done lane

Exit codes:
  0 — pass or pass_with_notes
  1 — fail (WPs not done or hard findings)
  2 — mission not found / ambiguous handle

Known false-positives in the dead-code scan
-------------------------------------------
The scan is heuristic (grep-based, not AST-level):

* Symbols exported via ``__all__`` are flagged if no call-site grep matches.
* Entry-point functions registered in ``pyproject.toml`` or ``setup.cfg`` are
  not detected as callers.
* Dynamic dispatch patterns (``getattr(module, name)()``) are invisible to grep.
* Protocol / ABC method implementations show as unused if only called through
  the abstract interface.

False positives are purely informational; they appear as ``pass_with_notes``,
not ``fail``, and should be reviewed manually before acting on them.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from typing import Annotated

import typer

from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.status.reducer import materialize
from specify_cli.task_utils import TaskCliError, find_repo_root

_IDENTIFIER_CHARCLASS = r"\w"


def review_mission(
    mission: Annotated[
        str,
        typer.Option("--mission", help="Mission handle (id, mid8, or slug)."),
    ] = "",
) -> None:
    """Validate a merged mission: WP lane check, dead-code scan, BLE001 audit.

    Writes kitty-specs/<slug>/mission-review-report.md with a machine-readable
    verdict.  See module docstring for known false-positive scenarios in the
    dead-code scan step.
    """
    from rich.console import Console

    console = Console()

    # ------------------------------------------------------------------
    # Resolve repo root
    # ------------------------------------------------------------------
    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2)

    # ------------------------------------------------------------------
    # Resolve mission handle → feature_dir
    # ------------------------------------------------------------------
    handle = mission.strip()
    if not handle:
        console.print("[red]Error:[/red] --mission is required.")
        raise typer.Exit(2)

    resolved = resolve_mission_handle(handle, repo_root)
    feature_dir = resolved.feature_dir
    mission_slug = resolved.mission_slug

    # ------------------------------------------------------------------
    # Read meta.json for display fields and baseline_merge_commit
    # ------------------------------------------------------------------
    meta_path = feature_dir / "meta.json"
    meta: dict[str, object] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    friendly_name: str = str(meta.get("friendly_name") or mission_slug)
    _bmc_raw = meta.get("baseline_merge_commit")
    baseline_merge_commit: str | None = str(_bmc_raw) if _bmc_raw else None

    console.print(f"\nReviewing mission: {friendly_name} ({mission_slug})\n")

    findings: list[dict[str, str]] = []

    # ==================================================================
    # Step 1 — WP lane check
    # ==================================================================
    snapshot = materialize(feature_dir)
    non_done = [
        wp_id
        for wp_id, state in snapshot.work_packages.items()
        if state.get("lane") != "done"
    ]
    if non_done:
        console.print(
            f"  [red]✗[/red]  WP lane check: {len(non_done)} WP(s) not in done"
        )
        for wp_id in non_done:
            lane_val = snapshot.work_packages[wp_id].get("lane", "unknown")
            console.print(f"       {wp_id}: {lane_val}")
            findings.append(
                {"type": "wp_not_done", "wp_id": wp_id, "lane": str(lane_val)}
            )
    else:
        console.print(
            f"  [green]✓[/green]  WP lane check: all {len(snapshot.work_packages)} WP(s) in done"
        )

    # ==================================================================
    # Step 2 — Dead-code scan
    # ==================================================================
    if not baseline_merge_commit:
        console.print(
            "  [yellow]⚠[/yellow]  Dead-code scan skipped: no baseline_merge_commit in meta.json"
            " (pre-083 mission)"
        )
    else:
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

    # ==================================================================
    # Step 3 — BLE001 unjustified suppression audit
    # ==================================================================
    search_dirs = [
        repo_root / "src" / "specify_cli" / "auth",
        repo_root / "src" / "specify_cli" / "cli" / "commands",
    ]
    ble001_findings: list[dict[str, str]] = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        grep_result = subprocess.run(
            ["grep", "-rn", "noqa: BLE001", str(search_dir)],
            capture_output=True,
            text=True,
        )
        for raw_line in grep_result.stdout.strip().splitlines():
            parts = raw_line.split(":", 2)
            if len(parts) < 3:
                continue
            file_path, line_no, content = parts[0], parts[1], parts[2]
            ble_match = re.search(r"noqa: BLE001(.*)$", content)
            if ble_match:
                after = ble_match.group(1).strip().lstrip(",").strip()
                # Remove other rule codes (e.g. ", S110") from the tail
                after = re.sub(r"^[A-Z0-9,\s]+", "", after).strip()
                if not after or after in ("—", "-", "–"):
                    ble001_findings.append(
                        {"file": file_path, "line": line_no, "content": content.strip()}
                    )
                    findings.append(
                        {"type": "ble001_suppression", "file": file_path, "line": line_no}
                    )

    if ble001_findings:
        console.print(
            f"  [red]✗[/red]  BLE001 audit: {len(ble001_findings)} unjustified suppression(s)"
        )
        for b in ble001_findings:
            console.print(f"       {b['file']}:{b['line']}")
    else:
        console.print("  [green]✓[/green]  BLE001 audit: 0 unjustified suppressions")

    # ==================================================================
    # Step 4 — Write report
    # ==================================================================
    wp_not_done_count = sum(1 for f in findings if f["type"] == "wp_not_done")
    if wp_not_done_count > 0:
        verdict = "fail"
    elif findings:
        verdict = "pass_with_notes"
    else:
        verdict = "pass"

    reviewed_at = datetime.now(UTC).isoformat()
    report_lines = [
        "---",
        f"verdict: {verdict}",
        f"reviewed_at: {reviewed_at}",
        f"findings: {len(findings)}",
        "---",
        "",
    ]
    if findings:
        report_lines.append("## Findings")
        report_lines.append("")
        for f in findings:
            if f["type"] == "wp_not_done":
                report_lines.append(
                    f"- **wp_not_done** `{f['wp_id']}`: lane is `{f.get('lane', 'unknown')}`"
                )
            elif f["type"] == "dead_code":
                report_lines.append(
                    f"- **dead_code** `{f['file']}` — `{f['symbol']}`: no non-test callers found"
                )
            elif f["type"] == "ble001_suppression":
                report_lines.append(
                    f"- **ble001_suppression** `{f['file']}:{f['line']}`: no inline justification"
                )
    else:
        report_lines.append("No findings.")

    report_path = feature_dir / "mission-review-report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Summary output
    # ------------------------------------------------------------------
    if verdict == "pass":
        verdict_color = "green"
    elif verdict == "pass_with_notes":
        verdict_color = "yellow"
    else:
        verdict_color = "red"
    console.print(
        f"\nVerdict: [{verdict_color}]{verdict}[/{verdict_color}]  ({len(findings)} finding(s))"
    )
    try:
        rel_report = report_path.relative_to(repo_root)
    except ValueError:
        rel_report = report_path
    console.print(f"Report written: {rel_report}")

    if verdict == "fail":
        raise typer.Exit(1)


__all__ = ["review_mission"]
