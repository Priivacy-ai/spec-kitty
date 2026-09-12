"""Detect drift between the slash-command registry and its committed reference.

Implements FR-001 / FR-002 of mission ``docs-gate-hardening``: keep
``docs/api/slash-commands.md`` mirroring the canonical consumer-command
registry so the page cannot silently drift.

The gate is **check-only** (no generator) and **bidirectional**. The authority
is :data:`specify_cli.shims.registry.CONSUMER_SKILLS` — a frozenset of the
consumer-facing slash commands, import-asserted equal to
``PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS``. This script never forks or
re-parses a second command set.

A command is *documented* when the reference carries a top-level
``## /spec-kitty.<name>`` heading. Two rule IDs are emitted:

* ``SLASH-MISSING`` — the registry names a command the reference omits.
* ``SLASH-EXTRA``   — the reference names a command the registry does not carry
  (retired or unknown).

The check is pure in-process set arithmetic: no subprocess, no network.
Importing :data:`CONSUMER_SKILLS` transitively initializes ``specify_cli``
(~140ms), which is acceptable (NFR-004).
"""

from __future__ import annotations

# Guard against a network upgrade check firing when the registry import
# initializes the ``specify_cli`` package.
import os as _os  # noqa: E402

_os.environ.setdefault("SPEC_KITTY_NO_UPGRADE_CHECK", "1")

import argparse  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from collections.abc import Iterable, Sequence  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Final  # noqa: E402

__all__ = [
    "DEFAULT_REFERENCE_PATH",
    "RULE_IDS",
    "Finding",
    "build_parser",
    "evaluate",
    "extract_documented_commands",
    "main",
]

# docs/api/ is canonical for the slash-command reference.
DEFAULT_REFERENCE_PATH: Final[str] = "docs/api/slash-commands.md"

RULE_IDS: Final[tuple[str, ...]] = ("SLASH-MISSING", "SLASH-EXTRA")

# A documented command is a top-level ``## /spec-kitty.<name>`` heading.
# NB: this deliberately does NOT match the space form ``spec-kitty foo`` used
# by the sibling CLI-reference gate — that gate's ``_HEADING_RE`` would not
# match the slash+dot form, so a dedicated extractor is required.
_HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^##\s+/spec-kitty\.([a-z0-9-]+)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class Finding:
    """A single drift offender."""

    rule_id: str
    command: str
    detail: str


def extract_documented_commands(text: str) -> set[str]:
    """Return the set of commands documented via ``## /spec-kitty.<name>``."""
    return {m.group(1) for m in _HEADING_RE.finditer(text)}


def evaluate(*, documented: set[str], registry: Iterable[str]) -> list[Finding]:
    """Return findings for the symmetric difference of documented vs registry.

    ``SLASH-MISSING`` for commands in the registry but not documented;
    ``SLASH-EXTRA`` for documented commands absent from the registry.
    Findings are sorted by (rule_id, command) for deterministic output.
    """
    registry_set = set(registry)
    findings: list[Finding] = []
    for command in sorted(registry_set - documented):
        findings.append(
            Finding(
                rule_id="SLASH-MISSING",
                command=command,
                detail=(
                    f"`/spec-kitty.{command}` is a consumer command in the "
                    "registry but has no `## /spec-kitty."
                    f"{command}` heading in the reference."
                ),
            )
        )
    for command in sorted(documented - registry_set):
        findings.append(
            Finding(
                rule_id="SLASH-EXTRA",
                command=command,
                detail=(
                    f"`/spec-kitty.{command}` is documented but is not a "
                    "consumer command in the registry (retired or unknown)."
                ),
            )
        )
    return findings


def _load_registry() -> set[str]:
    """Return the canonical consumer-command registry."""
    from specify_cli.shims.registry import CONSUMER_SKILLS

    return {str(command) for command in CONSUMER_SKILLS}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_slash_command_freshness",
        description=(
            "Validate docs/api/slash-commands.md against the canonical "
            "consumer slash-command registry (CONSUMER_SKILLS)."
        ),
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path(DEFAULT_REFERENCE_PATH),
        help=f"Path to the reference (default: {DEFAULT_REFERENCE_PATH}).",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Emit findings to stdout for CI annotations (default: stderr).",
    )
    return parser


def _emit_findings(findings: Iterable[Finding], *, ci: bool) -> None:
    stream = sys.stdout if ci else sys.stderr
    has_any = False
    for finding in findings:
        has_any = True
        stream.write(f"{finding.rule_id} {finding.command}: {finding.detail}\n")
    if not has_any:
        sys.stderr.write("check_slash_command_freshness: clean.\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.reference.exists():
        sys.stderr.write(
            f"SLASH-INPUT-MISSING  reference file not found: {args.reference}\n"
        )
        return 2

    documented = extract_documented_commands(
        args.reference.read_text(encoding="utf-8")
    )
    findings = evaluate(documented=documented, registry=_load_registry())
    _emit_findings(findings, ci=args.ci)
    return 1 if findings else 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
