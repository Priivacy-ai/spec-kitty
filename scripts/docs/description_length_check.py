"""``description`` length gate (NFR-003).

Every published page must carry a ``description`` whose length is **50-180**
characters (the SEO band the DocFX build publishes into ``<meta name=...>`` and
the social cards). Today nothing *validates* this: ``seo_postprocess.py``
**emits** a description into the rendered HTML but never checks its length, and
the inventory rulers do not look at ``description`` at all. This module is the
**net-new** gate that closes that hole.

It mirrors the established docs-ruler contract (cf.
:mod:`scripts.docs.related_validator`): **report-only by default** (exit ``0``,
C-002) so it can land green against a not-yet-authored tree, with a wired
``--strict`` flag that flips the exit to non-zero. WP14 turns the default on as
part of flipping Mission A's rulers to blocking; WP12 authors the per-page
descriptions that make the strict run green.

A violation is one of:

* ``missing``   — no ``description`` key, or it is blank;
* ``too_short`` — ``len(description) < 50``;
* ``too_long``  — ``len(description) > 180``.

Output shape::

    { "checked_count": int,
      "violations": [ {"path": str, "reason": str, "length": int | null} ] }

where ``checked_count`` is the number of pages examined — so a "0 violations"
result can never silently mean "0 checked".

Depends only on the standard library plus ``ruamel.yaml`` (via
:func:`scripts.docs._inventory.parse_frontmatter`). No new dependency.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from scripts.docs._inventory import parse_frontmatter

__all__ = [
    "DEFAULT_DOCS_ROOT",
    "MAX_DESCRIPTION_LENGTH",
    "MIN_DESCRIPTION_LENGTH",
    "LengthReport",
    "LengthViolation",
    "build_parser",
    "check_description_length",
    "main",
    "validate_descriptions",
]

DEFAULT_DOCS_ROOT: Final[str] = "docs"

#: Content-invariant doc subtree excluded from the description gate. ADR decision
#: bodies are byte-identical to their pre-move originals (C-002, enforced by
#: ``test_adr_content_invariance``) and carry only bare ``status`` frontmatter —
#: by design they have no ``description``. Holding them to the 50-180 band would
#: make the gate un-flippable to blocking against a correct tree.
_EXCLUDE_PREFIXES: Final[tuple[str, ...]] = ("docs/adr/",)

#: Inclusive description length band (NFR-003). 50 and 180 are both **valid**;
#: 49 and 181 are violations. These boundaries are the gate's whole contract.
MIN_DESCRIPTION_LENGTH: Final[int] = 50
MAX_DESCRIPTION_LENGTH: Final[int] = 180

_REASON_MISSING: Final[str] = "missing"
_REASON_TOO_SHORT: Final[str] = "too_short"
_REASON_TOO_LONG: Final[str] = "too_long"


@dataclass(slots=True, frozen=True)
class LengthViolation:
    """A page whose ``description`` is missing or out of the 50-180 band."""

    path: str
    reason: str
    length: int | None

    def as_dict(self) -> dict[str, object]:
        """Serialize to the contract's ``{path, reason, length}`` shape."""
        return {"path": self.path, "reason": self.reason, "length": self.length}


@dataclass(slots=True, frozen=True)
class LengthReport:
    """Result of a ``description`` length walk."""

    checked_count: int = 0
    violations: list[LengthViolation] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        """Serialize to the contract's JSON shape."""
        return {
            "checked_count": self.checked_count,
            "violations": [v.as_dict() for v in self.violations],
        }


def check_description_length(description: str | None) -> str | None:
    """Return a violation reason for ``description``, or ``None`` when valid.

    A length of exactly 50 or 180 is **valid** (inclusive band). ``None`` and
    blank-after-strip descriptions are ``missing``.
    """
    if description is None or not description.strip():
        return _REASON_MISSING
    length = len(description)
    if length < MIN_DESCRIPTION_LENGTH:
        return _REASON_TOO_SHORT
    if length > MAX_DESCRIPTION_LENGTH:
        return _REASON_TOO_LONG
    return None


def validate_descriptions(*, docs_root: Path, repo_root: Path) -> LengthReport:
    """Walk ``docs_root`` and validate every page's ``description`` length.

    Parameters
    ----------
    docs_root:
        Directory whose ``*.md`` files are scanned for frontmatter.
    repo_root:
        Base against which page paths are rendered repo-relative in the report.
    """
    checked = 0
    violations: list[LengthViolation] = []

    if not docs_root.exists() or not docs_root.is_dir():
        return LengthReport(checked_count=0, violations=[])

    for md_path in sorted(docs_root.rglob("*.md")):
        if _repo_relative(md_path, repo_root).startswith(_EXCLUDE_PREFIXES):
            continue  # content-invariant ADR bodies carry no description (C-002)
        description = _read_description(md_path)
        checked += 1
        reason = check_description_length(description)
        if reason is None:
            continue
        violations.append(
            LengthViolation(
                path=_repo_relative(md_path, repo_root),
                reason=reason,
                length=None if description is None else len(description),
            )
        )

    violations.sort(key=lambda v: v.path)
    return LengthReport(checked_count=checked, violations=violations)


def _read_description(md_path: Path) -> str | None:
    """Return the ``description`` frontmatter value (``None`` if absent)."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    raw = parse_frontmatter(text).get("description")
    return raw if isinstance(raw, str) else None


def _repo_relative(path: Path, repo_root: Path) -> str:
    """Render ``path`` as a POSIX repo-relative string (best-effort)."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def build_parser() -> argparse.ArgumentParser:
    """Build the length-gate CLI parser."""
    parser = argparse.ArgumentParser(
        prog="description_length_check",
        description=(
            "Validate docs/ frontmatter 'description' length is 50-180 chars. "
            "Report-only (exit 0) unless --strict is passed."
        ),
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=Path(DEFAULT_DOCS_ROOT),
        help=f"Docs tree to scan (default: {DEFAULT_DOCS_ROOT}).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Base for rendering repo-relative page paths (default: cwd).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON instead of a human summary.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero when any description is missing/out-of-band. Wired "
            "but OFF by default (report-only, C-002); WP14 turns it on."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = build_parser().parse_args(argv)
    report = validate_descriptions(docs_root=args.docs_root, repo_root=args.repo_root)
    _emit(report, as_json=args.json)
    if args.strict and report.violations:
        return 1
    return 0


def _emit(report: LengthReport, *, as_json: bool) -> None:
    """Print the report — JSON payload or a human-readable summary."""
    if as_json:
        sys.stdout.write(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n")
        return

    sys.stdout.write(
        f"description_length_check: checked {report.checked_count} page(s); "
        f"{len(report.violations)} violation(s).\n"
    )
    for violation in report.violations:
        sys.stdout.write(
            f"  {violation.reason.upper()} {violation.path} "
            f"(length={violation.length})\n"
        )


if __name__ == "__main__":  # pragma: no cover - module-level CLI guard
    raise SystemExit(main())
