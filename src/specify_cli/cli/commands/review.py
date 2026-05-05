"""spec-kitty review --mission <handle>: Post-merge mission validation gate.

Performs four checks and writes kitty-specs/<slug>/mission-review-report.md:

1. WP lane check — all WPs must be in ``done`` (hard failure if not).
2. Dead-code scan — heuristic grep for new public symbols introduced by the
   mission diff that have no non-test callers.  Requires ``baseline_merge_commit``
   in meta.json (absent for pre-083 missions → step is skipped with a warning).
3. BLE001 audit — flags scoped auth/storage ``# noqa: BLE001`` suppressions
   that lack a specific inline safety justification.
4. Report writer — writes ``mission-review-report.md`` with YAML frontmatter
   containing ``verdict``, ``reviewed_at``, and ``findings`` count.

Verdict enum:
  pass             — all checks clean
  pass_with_notes  — informational findings only (no WP lane failures)
  fail             — one or more WPs not in done lane or hard findings exist

Exit codes:
  0 — pass or pass_with_notes
  1 — fail (WPs not done, hard findings, or unjustified BLE001 suppressions)
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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.post_merge.review_artifact_consistency import (
    find_rejected_review_artifact_conflicts,
    format_review_artifact_conflict,
    review_artifact_conflict_diagnostic,
)
from specify_cli.status.reducer import materialize
from specify_cli.task_utils import TaskCliError, find_repo_root

_IDENTIFIER_CHARCLASS = r"\w"
_BLE001_NOQA_RE = re.compile(r"#\s*noqa:\s*(?P<body>[^#]*)", re.IGNORECASE)
_BROAD_EXCEPTION_HANDLER_RE = re.compile(
    r"^\s*except\s+"
    r"(?:Exception(?:\s+as\s+\w+)?|\([^#\n]*\bException\b[^#\n]*\)(?:\s+as\s+\w+)?)"
    r"\s*:"
)
_AUTH_STORAGE_BLE001_COMMAND_FILES = frozenset(
    {
        "src/specify_cli/cli/commands/auth.py",
        "src/specify_cli/cli/commands/_auth_doctor.py",
        "src/specify_cli/cli/commands/_auth_login.py",
        "src/specify_cli/cli/commands/_auth_logout.py",
        "src/specify_cli/cli/commands/_auth_status.py",
    }
)
_AUTH_STORAGE_BLE001_AUTH_PREFIX = "src/specify_cli/auth/"
_GENERIC_BLE001_REASONS = frozenset(
    {
        "all exceptions",
        "ble001",
        "blanket",
        "broad catch",
        "broad exception",
        "catch all",
        "catchall",
        "exception",
        "fixme",
        "generic",
        "ignore",
        "ignored",
        "noqa",
        "suppress",
        "suppression",
        "temp",
        "temporary",
        "todo",
    }
)
_BLE001_REMEDIATION = (
    "Add a specific safety reason after '# noqa: BLE001' that names the "
    "boundary, translation, logging, downgrade, or cleanup behavior; otherwise "
    "narrow the exception type."
)


@dataclass(frozen=True)
class Ble001SuppressionFinding:
    """Actionable finding for a scoped auth/storage BLE001 suppression."""

    file: str
    line: int
    suppression: str
    reason: str
    remediation: str = _BLE001_REMEDIATION


def _repo_relative_path(file_path: str | Path, repo_root: Path | None = None) -> str:
    path = Path(file_path)
    if repo_root is not None:
        try:
            return path.resolve(strict=False).relative_to(
                repo_root.resolve(strict=False)
            ).as_posix()
        except ValueError:
            pass

    normalized = path.as_posix().lstrip("/")
    marker = "src/specify_cli/"
    marker_index = normalized.find(marker)
    if marker_index >= 0:
        return normalized[marker_index:]
    return normalized


def _is_auth_storage_ble001_scoped_path(
    file_path: str | Path,
    *,
    repo_root: Path | None = None,
) -> bool:
    repo_path = _repo_relative_path(file_path, repo_root)
    return repo_path.startswith(
        _AUTH_STORAGE_BLE001_AUTH_PREFIX
    ) or repo_path in _AUTH_STORAGE_BLE001_COMMAND_FILES


def _ble001_reason_from_line(line_text: str) -> str | None:
    noqa_match = _BLE001_NOQA_RE.search(line_text)
    if noqa_match is None:
        return None

    body = noqa_match.group("body")
    ble_match = re.search(r"\bBLE001\b(?P<after>.*)$", body)
    if ble_match is None:
        return None

    after = ble_match.group("after")
    while True:
        next_code = re.match(r"\s*,\s*[A-Z]{1,4}\d{3}\b(?P<rest>.*)$", after)
        if next_code is None:
            break
        after = next_code.group("rest")

    return re.sub(r"^\s*[-–—:]+\s*", "", after).strip()


def _is_broad_exception_handler(line_text: str) -> bool:
    return _BROAD_EXCEPTION_HANDLER_RE.search(line_text) is not None


def _is_generic_ble001_reason(reason: str) -> bool:
    normalized = re.sub(r"[\W_]+", " ", reason.casefold()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return not normalized or normalized in _GENERIC_BLE001_REASONS


def audit_auth_storage_ble001_line(
    file_path: str | Path,
    line_number: int,
    line_text: str,
    *,
    repo_root: Path | None = None,
) -> Ble001SuppressionFinding | None:
    """Return a finding for an unjustified scoped auth/storage BLE001 suppression."""
    if not _is_auth_storage_ble001_scoped_path(file_path, repo_root=repo_root):
        return None

    reason = _ble001_reason_from_line(line_text)
    if reason is None:
        if not _is_broad_exception_handler(line_text):
            return None
        reason = ""
    elif not _is_generic_ble001_reason(reason):
        return None

    return Ble001SuppressionFinding(
        file=str(file_path),
        line=line_number,
        suppression=line_text.strip(),
        reason=reason,
    )


def collect_auth_storage_ble001_findings(
    repo_root: Path,
) -> list[Ble001SuppressionFinding]:
    """Scan contract-scoped auth/storage files for unjustified BLE001 suppressions."""
    candidates: list[Path] = []
    auth_dir = repo_root / _AUTH_STORAGE_BLE001_AUTH_PREFIX
    if auth_dir.exists():
        candidates.extend(path for path in auth_dir.rglob("*.py") if path.is_file())

    for relative_file in _AUTH_STORAGE_BLE001_COMMAND_FILES:
        path = repo_root / relative_file
        if path.exists():
            candidates.append(path)

    findings: list[Ble001SuppressionFinding] = []
    for path in sorted(set(candidates)):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line_text in enumerate(lines, start=1):
            finding = audit_auth_storage_ble001_line(
                path,
                line_number,
                line_text,
                repo_root=repo_root,
            )
            if finding is not None:
                findings.append(finding)
    return findings


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

    review_artifact_conflicts = find_rejected_review_artifact_conflicts(feature_dir)
    if review_artifact_conflicts:
        console.print(
            "  [red]✗[/red]  Review artifact consistency: latest rejected artifact "
            "exists for terminal WP(s)"
        )
        for conflict in review_artifact_conflicts:
            diagnostic = review_artifact_conflict_diagnostic(
                conflict,
                repo_root=repo_root,
            )
            console.print(
                f"       {format_review_artifact_conflict(conflict, repo_root=repo_root)}"
            )
            console.print(f"       diagnostic_code: {diagnostic['diagnostic_code']}")
            console.print(
                f"       branch_or_work_package: {diagnostic['branch_or_work_package']}"
            )
            console.print(
                f"       violated_invariant: {diagnostic['violated_invariant']}"
            )
            for line in diagnostic["remediation"]:
                console.print(f"       remediation: {line}")
            findings.append(
                {
                    "type": "rejected_review_artifact",
                    "wp_id": conflict.wp_id,
                    "lane": conflict.lane,
                    "artifact_path": str(conflict.artifact_path),
                    "diagnostic_code": str(diagnostic["diagnostic_code"]),
                    "branch_or_work_package": str(
                        diagnostic["branch_or_work_package"]
                    ),
                    "violated_invariant": str(diagnostic["violated_invariant"]),
                    "remediation": "; ".join(
                        str(line) for line in diagnostic["remediation"]
                    ),
                    "latest_review_cycle_verdict": str(
                        diagnostic["latest_review_cycle_verdict"]
                    ),
                }
            )
    else:
        console.print(
            "  [green]✓[/green]  Review artifact consistency: no terminal WP has a latest rejected artifact"
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
    ble001_findings = collect_auth_storage_ble001_findings(repo_root)
    for finding in ble001_findings:
        findings.append(
            {
                "type": "ble001_suppression",
                "file": finding.file,
                "line": str(finding.line),
                "content": finding.suppression,
                "remediation": finding.remediation,
            }
        )

    if ble001_findings:
        console.print(
            f"  [red]✗[/red]  BLE001 audit: {len(ble001_findings)} unjustified suppression(s)"
        )
        for finding in ble001_findings:
            console.print(f"       {finding.file}:{finding.line}")
            console.print(f"       suppression: {finding.suppression}")
            console.print(f"       remediation: {finding.remediation}")
    else:
        console.print("  [green]✓[/green]  BLE001 audit: 0 unjustified suppressions")

    # ==================================================================
    # Step 4 — Write report
    # ==================================================================
    hard_failure_count = sum(
        1
        for f in findings
        if f["type"]
        in {"wp_not_done", "rejected_review_artifact", "ble001_suppression"}
    )
    if hard_failure_count > 0:
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
                    f"- **ble001_suppression** `{f['file']}:{f['line']}`: "
                    f"`{f.get('content', 'unknown')}`; "
                    f"remediation=`{f.get('remediation', _BLE001_REMEDIATION)}`"
                )
            elif f["type"] == "rejected_review_artifact":
                report_lines.append(
                    f"- **rejected_review_artifact** `{f['wp_id']}`: lane is "
                    f"`{f.get('lane', 'unknown')}`, latest artifact is "
                    f"`{f.get('artifact_path', 'unknown')}`; "
                    f"diagnostic_code=`{f.get('diagnostic_code', 'unknown')}`, "
                    f"branch_or_work_package=`{f.get('branch_or_work_package', 'unknown')}`, "
                    f"violated_invariant=`{f.get('violated_invariant', 'unknown')}`, "
                    f"remediation=`{f.get('remediation', 'unknown')}`"
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


__all__ = [
    "Ble001SuppressionFinding",
    "audit_auth_storage_ble001_line",
    "collect_auth_storage_ble001_findings",
    "review_mission",
]
