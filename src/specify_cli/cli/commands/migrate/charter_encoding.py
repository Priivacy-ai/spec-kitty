"""Charter-content encoding migration subcommand.

``spec-kitty migrate charter-encoding`` walks every existing mission's charter
content (``kitty-specs/*/charter/*.{yaml,md,txt}`` and
``.kittify/charter/*.{yaml,md,txt}``), detects the encoding of each file via
the WP06 chokepoint (``charter._io.load_charter_file``), and either:

- Skips the file (already pure UTF-8; idempotency pre-check passes).
- Normalizes the file to UTF-8 in-place with a provenance record.
- Surfaces the file as ambiguous (exits non-zero; manual repair required).

Implements: FR-026, FR-027, NFR-006 (idempotency).

Interactive mode (default):   prompt before each non-UTF-8 file.
``--dry-run``:                 show what would change; write nothing.
``--yes``/``-y``:              normalize without prompting; exit non-zero on
                               any ambiguous file (CI-safe).
``--json``:                    emit a JSON-stable summary on stdout at the end.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

_console = Console()
_err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Corpus patterns (FR-026 / research.md R-9)
# ---------------------------------------------------------------------------

_MISSION_CHARTER_GLOB = "kitty-specs/*/charter/*.{yaml,md,txt}"
_GLOBAL_CHARTER_GLOB = ".kittify/charter/*.{yaml,md,txt}"

_CHARTER_EXTENSIONS = (".yaml", ".md", ".txt")


# ---------------------------------------------------------------------------
# Internal data model
# ---------------------------------------------------------------------------


@dataclass
class _FileRecord:
    """Per-file result produced by the corpus scan."""

    path: Path
    action: str  # "already-utf8" | "normalized" | "ambiguous" | "dry-run-would-normalize"
    encoding: str | None = None
    confidence: float | None = None
    diagnostic_body: str | None = None


@dataclass
class _ScanSummary:
    """Aggregated result after scanning the full corpus."""

    files_inspected: int = 0
    already_utf8: list[Path] = field(default_factory=list)
    normalized: list[_FileRecord] = field(default_factory=list)
    ambiguous: list[_FileRecord] = field(default_factory=list)
    dry_run: bool = False

    @property
    def result(self) -> str:
        if self.ambiguous:
            return "ambiguous_present"
        return "success"


# ---------------------------------------------------------------------------
# Idempotency pre-check (NFR-006)
# ---------------------------------------------------------------------------


def _is_pure_utf8(path: Path) -> bool:
    """Return True if the file bytes decode cleanly as strict UTF-8.

    This cheap pre-check is the idempotency guard: already-UTF-8 files are
    skipped without invoking the chokepoint, so no new provenance records are
    written on a second run.
    """
    try:
        path.read_bytes().decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


# ---------------------------------------------------------------------------
# Corpus inventory
# ---------------------------------------------------------------------------


def _collect_charter_files(project_root: Path) -> list[Path]:
    """Return all charter files matching the corpus patterns.

    Scans:
    - ``kitty-specs/*/charter/*.{yaml,md,txt}``
    - ``.kittify/charter/*.{yaml,md,txt}``
    """
    files: list[Path] = []

    kitty_specs = project_root / "kitty-specs"
    if kitty_specs.is_dir():
        for mission_dir in sorted(kitty_specs.iterdir()):
            if not mission_dir.is_dir():
                continue
            charter_dir = mission_dir / "charter"
            if charter_dir.is_dir():
                for ext in _CHARTER_EXTENSIONS:
                    files.extend(sorted(charter_dir.glob(f"*{ext}")))

    global_charter = project_root / ".kittify" / "charter"
    if global_charter.is_dir():
        for ext in _CHARTER_EXTENSIONS:
            files.extend(sorted(global_charter.glob(f"*{ext}")))

    return files


# ---------------------------------------------------------------------------
# Core scan logic
# ---------------------------------------------------------------------------


def _scan_file(path: Path, *, dry_run: bool) -> _FileRecord:
    """Scan a single charter file via the WP06 chokepoint.

    Idempotency rule (NFR-006): if the file is already pure UTF-8, return an
    ``already-utf8`` record immediately WITHOUT invoking ``load_charter_file``.
    This prevents writing a new provenance record on every re-run.

    For non-UTF-8 files the chokepoint is invoked exactly once.  On success
    the file is rewritten as UTF-8 in-place (unless ``dry_run``).
    """
    # NFR-006 idempotency pre-check — cheap byte-level gate.
    if _is_pure_utf8(path):
        return _FileRecord(path=path, action="already-utf8")

    # Delegate to the WP06 chokepoint for detection + provenance.
    from charter._io import CharterEncodingError, load_charter_file  # noqa: PLC0415

    try:
        content = load_charter_file(path, unsafe=False)
    except CharterEncodingError as exc:
        return _FileRecord(
            path=path,
            action="ambiguous",
            diagnostic_body=exc.body,
        )

    # Chokepoint succeeded — content is now valid UTF-8 text.
    if dry_run:
        return _FileRecord(
            path=path,
            action="dry-run-would-normalize",
            encoding=content.source_encoding,
            confidence=content.confidence,
        )

    # Write normalized UTF-8 back to disk (provenance already written by chokepoint).
    path.write_text(content.text, encoding="utf-8")

    return _FileRecord(
        path=path,
        action="normalized",
        encoding=content.source_encoding,
        confidence=content.confidence,
    )


# ---------------------------------------------------------------------------
# Interactive prompting helpers
# ---------------------------------------------------------------------------


def _prompt_for_file(record_path: Path, detected: str, confidence: float) -> str:
    """Prompt the operator for a single file.  Returns 'y', 'n', or 'a' (yes-all)."""
    _console.print(
        f"\n[bold]File:[/bold] {record_path}\n"
        f"[bold]Detected:[/bold] {detected} (confidence {confidence:.2f})\n"
        "[bold]Action:[/bold] normalize to UTF-8 with provenance record?"
    )
    response = typer.prompt("  [y/N/a (yes-all)]", default="N").strip().lower()
    return response if response in ("y", "n", "a") else "n"


# ---------------------------------------------------------------------------
# Main command entrypoint (registered via migrate_cmd.py)
# ---------------------------------------------------------------------------


def run_charter_encoding_migration(
    *,
    project_root: Path,
    dry_run: bool,
    yes: bool,
    json_output: bool,
) -> int:
    """Execute the charter-encoding migration.

    Returns the intended process exit code (0 = success, non-zero = ambiguous
    files present or error).  The caller (typer command) calls
    ``raise typer.Exit(code)`` after this function returns.

    When ``json_output=True`` all human-readable progress messages are
    suppressed so that stdout carries only the final JSON payload.  Errors
    and ambiguity diagnostics are always routed to stderr.
    """
    files = _collect_charter_files(project_root)

    summary = _ScanSummary(dry_run=dry_run)
    summary.files_inspected = len(files)

    yes_all = yes  # whether we skip all remaining prompts

    for path in files:
        # NFR-006: idempotency pre-check before hitting the chokepoint.
        if _is_pure_utf8(path):
            summary.already_utf8.append(path)
            continue

        # File needs attention — run through the chokepoint.
        from charter._io import CharterEncodingError, load_charter_file  # noqa: PLC0415

        try:
            content = load_charter_file(path, unsafe=False)
        except CharterEncodingError as exc:
            record = _FileRecord(
                path=path,
                action="ambiguous",
                diagnostic_body=exc.body,
            )
            summary.ambiguous.append(record)
            # Always route to stderr (visible in both human and JSON modes).
            _err_console.print(f"[red]AMBIGUOUS:[/red] {path}")
            _err_console.print(f"  {exc.body.splitlines()[0] if exc.body else ''}")
            continue

        # File is non-UTF-8 but the chokepoint could decode it.
        detected = content.source_encoding
        confidence = content.confidence

        if dry_run:
            if not json_output:
                _console.print(
                    f"[yellow]would normalize[/yellow] {path} "
                    f"({detected}, confidence {confidence:.2f})"
                )
            record = _FileRecord(
                path=path,
                action="dry-run-would-normalize",
                encoding=detected,
                confidence=confidence,
            )
            summary.normalized.append(record)
            continue

        if not yes_all and not yes:
            # Interactive mode: ask operator.
            response = _prompt_for_file(path, detected, confidence)
            if response == "a":
                yes_all = True
            elif response != "y":
                if not json_output:
                    _console.print(f"  [dim]skipped: {path}[/dim]")
                summary.already_utf8.append(path)  # treat as skipped / already-handled
                continue

        # Apply normalization: rewrite UTF-8 to disk.
        # (Chokepoint has already written provenance record as a side effect of the try block above.)
        path.write_text(content.text, encoding="utf-8")
        record = _FileRecord(
            path=path,
            action="normalized",
            encoding=detected,
            confidence=confidence,
        )
        summary.normalized.append(record)
        if not json_output:
            _console.print(
                f"  [green]normalized[/green] {path} "
                f"({detected} → utf-8, confidence {confidence:.2f})"
            )

    # Emit summary: JSON to stdout (machine-readable), or human text to console.
    if json_output:
        _emit_json_summary(summary)
    else:
        _emit_human_summary(summary)

    # Exit non-zero if any ambiguous files remain (FR-027, --yes CI contract).
    return 1 if summary.ambiguous else 0


# ---------------------------------------------------------------------------
# Summary renderers
# ---------------------------------------------------------------------------


def _emit_json_summary(summary: _ScanSummary) -> None:
    """Print a JSON-stable summary to stdout (FR-027)."""
    payload = {
        "result": summary.result,
        "files_inspected": summary.files_inspected,
        "already_utf8": [str(p) for p in summary.already_utf8],
        "normalized": [
            {
                "path": str(r.path),
                "encoding": r.encoding,
                "confidence": r.confidence,
            }
            for r in summary.normalized
        ],
        "ambiguous": [
            {
                "path": str(r.path),
                "diagnostic_body": r.diagnostic_body,
            }
            for r in summary.ambiguous
        ],
        "dry_run": summary.dry_run,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def _emit_human_summary(summary: _ScanSummary) -> None:
    """Print a human-readable summary to the console."""
    prefix = "[dim](dry-run)[/dim] " if summary.dry_run else ""
    _console.print(f"\n{prefix}[bold]charter-encoding migration summary[/bold]")
    _console.print(f"  Files inspected  : {summary.files_inspected}")
    _console.print(f"  Already UTF-8    : {len(summary.already_utf8)}")
    _console.print(
        f"  Normalized       : {len(summary.normalized)}"
        + (" (would normalize)" if summary.dry_run else "")
    )
    if summary.ambiguous:
        _console.print(
            f"  [red]Ambiguous        : {len(summary.ambiguous)} (manual repair required)[/red]"
        )
        for rec in summary.ambiguous:
            _console.print(f"    [red]{rec.path}[/red]")
    else:
        _console.print("  [green]Ambiguous        : 0[/green]")

    if summary.dry_run:
        _console.print("\n[dim]Dry run — no files were modified.[/dim]")
    elif not summary.ambiguous:
        _console.print("\n[green]Done.[/green] Charter corpus is UTF-8 compliant.")
