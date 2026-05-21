"""Build the 3.2 CLI reference markdown from the live Typer surface.

Implements ``contracts/build_cli_reference.md`` (FR-007 / FR-008).

The script:

1. Discovers every visible command path via :func:`scripts.docs._typer_walker.walk`.
2. Captures each path's ``--help`` output via ``subprocess.run(["uv", "run",
   "spec-kitty", *path, "--help"])`` and normalizes the result (strip ANSI,
   collapse blank-line runs, preserve fenced code blocks).
3. Emits a sectioned markdown document grouped by top-level command/group.
4. Honours ``--mode {generated, hybrid, hand}`` for the
   ``<!-- BEGIN GENERATED -->`` / ``<!-- END GENERATED -->`` envelope.

The script never patches Typer; it only inspects the registered tree. It
refuses to overwrite a working-tree-dirty target unless ``--force`` is
passed.
"""

from __future__ import annotations

# CRITICAL: enforce env flags BEFORE any specify_cli import.
import os as _os

_os.environ.setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
_os.environ.setdefault("SPEC_KITTY_NO_UPGRADE_CHECK", "1")

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import typer  # noqa: F401  (kept for type-discoverable imports in tests)

from scripts.docs._typer_walker import CommandPathEntry, walk

__all__ = [
    "BEGIN_MARKER",
    "DEFAULT_AGENT_REFERENCE_PATH",
    "DEFAULT_REFERENCE_PATH",
    "END_MARKER",
    "Mode",
    "build_parser",
    "capture_help",
    "main",
    "render_document",
    "render_section",
    "strip_ansi",
    "normalize_help_text",
]


DEFAULT_REFERENCE_PATH: Final[str] = "docs/reference/cli-commands.md"
DEFAULT_AGENT_REFERENCE_PATH: Final[str] = "docs/reference/agent-subcommands.md"

BEGIN_MARKER: Final[str] = "<!-- BEGIN GENERATED -->"
END_MARKER: Final[str] = "<!-- END GENERATED -->"

Mode = Literal["generated", "hybrid", "hand"]

# Matches CSI escape sequences (colors, cursor moves) emitted by Rich.
_ANSI_RE: Final[re.Pattern[str]] = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# OSC sequences (clipboard / title)
_OSC_RE: Final[re.Pattern[str]] = re.compile(r"\x1b\][^\x07]*\x07")


# ---------------------------------------------------------------------------
# Subprocess help capture + normalization
# ---------------------------------------------------------------------------


def strip_ansi(text: str) -> str:
    """Remove ANSI CSI / OSC escape sequences from ``text``."""
    text = _ANSI_RE.sub("", text)
    text = _OSC_RE.sub("", text)
    return text


def normalize_help_text(text: str) -> str:
    """Canonicalize help output for deterministic markdown emission.

    Steps:
    1. Strip ANSI sequences.
    2. Strip trailing whitespace per line.
    3. Collapse runs of >2 blank lines to a single blank line.
    4. Strip leading/trailing whitespace from the full string and append a
       single trailing newline.
    """
    text = strip_ansi(text)
    lines = [line.rstrip() for line in text.splitlines()]
    out_lines: list[str] = []
    blanks = 0
    for line in lines:
        if not line:
            blanks += 1
            if blanks <= 1:
                out_lines.append("")
        else:
            blanks = 0
            out_lines.append(line)
    while out_lines and out_lines[0] == "":
        out_lines.pop(0)
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    return "\n".join(out_lines) + "\n" if out_lines else ""


def capture_help(
    path: tuple[str, ...],
    *,
    cmd_runner: Sequence[str] = ("uv", "run", "spec-kitty"),
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> str:
    """Capture the normalized ``--help`` output for the given command path."""
    full_cmd: list[str] = [*cmd_runner, *path, "--help"]
    proc_env = dict(_os.environ)
    if env:
        proc_env.update(env)
    proc_env.setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    proc_env.setdefault("SPEC_KITTY_NO_UPGRADE_CHECK", "1")
    proc_env.setdefault("NO_COLOR", "1")
    proc_env.setdefault("TERM", "dumb")
    result = subprocess.run(  # noqa: S603
        full_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=proc_env,
        check=False,
    )
    return normalize_help_text(result.stdout or "")


# ---------------------------------------------------------------------------
# Document rendering
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RenderedSection:
    """A single markdown section for one command path."""

    path: tuple[str, ...]
    kind: str
    deprecated: bool
    body: str


def render_section(entry: CommandPathEntry, help_text: str) -> RenderedSection:
    """Render a single markdown section for ``entry`` with normalized help."""
    title = "spec-kitty " + " ".join(entry.path)
    deprecated_banner = (
        "> **Deprecated**: " + (entry.help_summary or "this command is deprecated") + "\n\n"
        if entry.deprecated
        else ""
    )
    summary_line = (
        f"_{entry.help_summary}_\n\n" if entry.help_summary and not entry.deprecated else ""
    )
    body = (
        f"## {title}\n\n"
        f"{deprecated_banner}{summary_line}"
        "```\n"
        f"{help_text.rstrip()}\n"
        "```\n"
    )
    return RenderedSection(
        path=entry.path,
        kind=entry.kind,
        deprecated=entry.deprecated,
        body=body,
    )


def render_document(
    sections: Sequence[RenderedSection],
    *,
    title: str,
    include_hidden_sections: Sequence[RenderedSection] | None = None,
) -> str:
    """Compose the full generated markdown body (without envelope markers)."""
    parts: list[str] = [f"# {title}\n"]
    for section in sections:
        parts.append(section.body)
    if include_hidden_sections:
        parts.append("## Internal / hidden commands\n")
        parts.append(
            "> The following commands are hidden from the default `--help` "
            "output but documented here for internal reference.\n\n"
        )
        for section in include_hidden_sections:
            parts.append(section.body)
    return "\n".join(parts).rstrip() + "\n"


def wrap_with_markers(generated: str, *, existing: str | None) -> str:
    """Embed ``generated`` between BEGIN/END markers, preserving outside prose.

    If ``existing`` already contains the markers, splice the new generated
    block in place. Otherwise, append the markers at the end of the file
    (or write a fresh file with only the markers if existing is None/empty).
    """
    new_block = f"{BEGIN_MARKER}\n{generated.rstrip()}\n{END_MARKER}\n"
    if not existing:
        return new_block
    if BEGIN_MARKER in existing and END_MARKER in existing:
        before, _, rest = existing.partition(BEGIN_MARKER)
        _, _, after = rest.partition(END_MARKER)
        return before.rstrip() + ("\n\n" if before.strip() else "") + new_block + (
            "\n" + after.lstrip() if after.strip() else ""
        )
    return existing.rstrip() + "\n\n" + new_block


# ---------------------------------------------------------------------------
# Target safety: refuse to write to a dirty file
# ---------------------------------------------------------------------------


def is_target_dirty(target: Path, *, repo_root: Path) -> bool:
    """Return ``True`` if ``target`` has uncommitted edits in the working tree."""
    if not target.exists():
        return False
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["git", "status", "--porcelain", "--", str(target)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        # If git is unreachable, do not block writes — surface via stderr.
        return False
    return bool(result.stdout.strip())


# ---------------------------------------------------------------------------
# Path partitioning
# ---------------------------------------------------------------------------


def partition_paths(
    entries: Iterable[CommandPathEntry],
    *,
    include_hidden: bool,
) -> tuple[list[CommandPathEntry], list[CommandPathEntry], list[CommandPathEntry]]:
    """Partition entries into (main, agent_tree, hidden_appendix)."""
    main: list[CommandPathEntry] = []
    agents: list[CommandPathEntry] = []
    hidden: list[CommandPathEntry] = []
    for e in entries:
        if e.hidden:
            if include_hidden:
                hidden.append(e)
            continue
        if e.path and e.path[0] == "agent":
            agents.append(e)
        else:
            main.append(e)
    return main, agents, hidden


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_cli_reference",
        description="Build docs/reference/cli-commands.md from the live Typer surface.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_REFERENCE_PATH),
        help=f"Destination markdown file (default: {DEFAULT_REFERENCE_PATH}).",
    )
    parser.add_argument(
        "--agent-output",
        type=Path,
        default=Path(DEFAULT_AGENT_REFERENCE_PATH),
        help=f"Destination for the agent subtree (default: {DEFAULT_AGENT_REFERENCE_PATH}).",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Append an appendix listing hidden command paths.",
    )
    parser.add_argument(
        "--mode",
        choices=("generated", "hybrid", "hand"),
        default="hybrid",
        help="Output mode: generated (whole file), hybrid (marker envelope), or hand (classification only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered document to stdout instead of writing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target even if it has uncommitted changes.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (used for git dirty-check).",
    )
    parser.add_argument(
        "--skip-help-capture",
        action="store_true",
        help="Skip the subprocess --help capture (used by unit tests).",
    )
    return parser


def _load_existing(target: Path) -> str | None:
    if not target.exists():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except OSError:
        return None


def _write_or_dry_run(target: Path, body: str, *, dry_run: bool) -> None:
    if dry_run:
        sys.stdout.write(f"--- {target} ---\n{body}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def _classification_table(entries: Sequence[CommandPathEntry]) -> str:
    """Render the deprecation/internal classification table for hand mode."""
    rows: list[str] = [
        "## Classification table\n",
        "| Path | Kind | Status | Summary |",
        "|------|------|--------|---------|",
    ]
    for e in entries:
        if not (e.deprecated or e.hidden):
            continue
        status = "deprecated" if e.deprecated else "hidden"
        summary = e.help_summary.replace("|", "\\|")
        rows.append(
            f"| `spec-kitty {' '.join(e.path)}` | {e.kind} | {status} | {summary} |"
        )
    return "\n".join(rows) + "\n"


def _generate_for_target(
    target: Path,
    *,
    entries: Sequence[CommandPathEntry],
    title: str,
    include_hidden_entries: Sequence[CommandPathEntry],
    mode: Mode,
    dry_run: bool,
    skip_help_capture: bool,
) -> None:
    sections: list[RenderedSection] = []
    for e in entries:
        if e.hidden:
            continue
        help_text = "" if skip_help_capture else capture_help(e.path)
        sections.append(render_section(e, help_text))
    hidden_sections: list[RenderedSection] = []
    for e in include_hidden_entries:
        help_text = "" if skip_help_capture else capture_help(e.path)
        hidden_sections.append(render_section(e, help_text))

    if mode == "hand":
        body = _classification_table([*entries, *include_hidden_entries])
        _write_or_dry_run(target, body, dry_run=dry_run)
        return

    generated_body = render_document(
        sections,
        title=title,
        include_hidden_sections=hidden_sections or None,
    )

    if mode == "generated":
        _write_or_dry_run(target, generated_body, dry_run=dry_run)
        return

    # hybrid
    existing = _load_existing(target)
    body = wrap_with_markers(generated_body, existing=existing)
    _write_or_dry_run(target, body, dry_run=dry_run)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if _os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC") != "1":
        sys.stderr.write(
            "BUILD-ENV-MISSING-SAAS-SYNC\n  SPEC_KITTY_ENABLE_SAAS_SYNC=1 must "
            "be set before import.\n"
        )
        return 3

    # Import the live typer surface (lazy to keep the script importable
    # under unit-test environments that mock specify_cli).
    try:
        from specify_cli import app
        from specify_cli.cli.commands import register_commands
    except Exception as exc:  # pragma: no cover - guarded environment
        sys.stderr.write(f"BUILD-IMPORT-ERROR\n  {exc}\n")
        return 2

    _saved_argv = sys.argv[:]
    sys.argv = ["spec-kitty", "--help"]
    try:
        register_commands(app)
    finally:
        sys.argv = _saved_argv

    entries = walk(app)

    main_entries, agent_entries, hidden_entries = partition_paths(
        entries, include_hidden=args.include_hidden
    )

    repo_root = args.repo_root.resolve()
    if not args.dry_run and not args.force:
        for target in (args.output, args.agent_output):
            if is_target_dirty(target, repo_root=repo_root):
                sys.stderr.write(
                    f"BUILD-TARGET-DIRTY  {target}\n  Target has uncommitted "
                    "edits. Stash, commit, or pass --force.\n"
                )
                return 3

    _generate_for_target(
        args.output,
        entries=main_entries,
        title="CLI Command Reference",
        include_hidden_entries=hidden_entries,
        mode=args.mode,
        dry_run=args.dry_run,
        skip_help_capture=args.skip_help_capture,
    )
    _generate_for_target(
        args.agent_output,
        entries=agent_entries,
        title="Agent Subcommand Reference",
        include_hidden_entries=[],
        mode=args.mode,
        dry_run=args.dry_run,
        skip_help_capture=args.skip_help_capture,
    )

    visible_count = len([e for e in entries if not e.hidden])
    hidden_count = len([e for e in entries if e.hidden])
    deprecated_count = len([e for e in entries if e.deprecated])
    sys.stderr.write(
        f"build_cli_reference: visible={visible_count} hidden={hidden_count} "
        f"deprecated={deprecated_count} mode={args.mode}\n"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
