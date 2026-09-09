#!/usr/bin/env python3
"""Local pre-PR gate-selection parity consumer (FR-016 / #2476, WP18).

Answers, for a developer working locally before opening a PR, "which CI
gates/shards will my current diff select" — resolved through the SAME single
gate-selection authority CI itself uses (:mod:`scripts.ci.gate_selection`,
built in WP07). This module never re-parses ``.github/workflows/ci-router.yml``
and never re-encodes the path->group / group->job routing as a second
hand-maintained map: doing so would silently drift from CI's answer, which is
exactly the #2476 hazard the authority exists to close. There is ONE
authority; it is imported here and by WP17's completeness oracle
(``tests/architectural/_ci_integrity_oracle.py``) — this is its third and
last committed consumer (contract ``router-two-authority.md`` Invariant 3).

Two concerns, kept separate:

* **The changed-path set** — computed locally via the canonical
  merge-base -> ``git diff --name-only`` idiom
  (:func:`specify_cli.core.vcs.git.merge_base_changed_files`; mission
  ``merge-base-diff-ssot-01KX44SD`` — this module never re-implements that
  idiom itself).
* **The gate/shard selection** — resolved by calling
  :func:`scripts.ci.gate_selection.select_gates` with that path set. This
  module contributes NO routing knowledge of its own; :func:`resolve_selection`
  is a deliberate one-line pass-through, kept as its own named seam so both
  this module's tests and any future caller have one obvious proof point that
  the reuse is real.

Usage::

    python scripts/ci/local_gate_parity.py [--base-ref origin/main]

or via the ``make ci-parity`` target (T096), which wires this entrypoint. Run
it before opening a PR to see the router job/shard set your diff selects,
without waiting on a CI round-trip; the flow is documented for operators in
``kitty-specs/ci-pipeline-reinstatement-01M1X35E/quickstart.md`` under
"Local pre-PR parity" (T098 — that mission planning artifact is updated on
the planning/coordination branch, not from this implementation lane, per the
kitty-specs protected-path guard).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ci.gate_selection import GateSelection, Router, select_gates  # noqa: E402
from specify_cli.core.vcs.git import merge_base_changed_files  # noqa: E402

__all__ = [
    "DEFAULT_BASE_REF_CANDIDATES",
    "ParityReport",
    "build_report",
    "format_report",
    "local_changed_paths",
    "main",
    "resolve_selection",
]

#: Tried in order when the caller does not pin a ``--base-ref``; the last
#: candidate is always returned even if unresolved, so callers still get a
#: value to diff against (git itself then reports the real failure via an
#: empty changed-path set rather than this module raising).
DEFAULT_BASE_REF_CANDIDATES: tuple[str, ...] = ("origin/main", "main")


@dataclass(frozen=True)
class ParityReport:
    """The local pre-PR parity answer: what changed, and what it selects."""

    base_ref: str
    changed_paths: tuple[str, ...]
    selection: GateSelection


def resolve_selection(changed_paths: Iterable[str], *, router: Router | None = None) -> GateSelection:
    """Resolve the gate/shard selection for *changed_paths*.

    A thin, intentional pass-through to
    :func:`scripts.ci.gate_selection.select_gates` — the single authority
    (#2476). This function carries no routing logic of its own; it exists so
    the local entrypoint (and its tests) have one obvious, importable seam
    proving that reuse rather than a second parser.
    """
    return select_gates(changed_paths, router=router)


def _resolve_base_ref(repo_root: Path, candidates: Iterable[str]) -> str:
    """Return the first *candidates* entry that resolves in *repo_root*.

    Falls back to the last candidate when none resolve, so the caller always
    gets a ref to diff against; a genuinely bad ref then surfaces through
    :func:`local_changed_paths` returning an empty tuple (git's own failure
    mode), not a raised exception here.
    """
    resolved = tuple(candidates)
    for ref in resolved:
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=repo_root,
            capture_output=True,
            timeout=5,
            check=False,
        )
        if probe.returncode == 0:
            return ref
    return resolved[-1]


def local_changed_paths(repo_root: Path, base_ref: str) -> tuple[str, ...]:
    """Changed paths since the merge-base with *base_ref* (HEAD-relative).

    Delegates entirely to the canonical
    :func:`specify_cli.core.vcs.git.merge_base_changed_files` idiom — this
    module never re-implements ``git merge-base`` / ``git diff --name-only``
    itself (mission ``merge-base-diff-ssot-01KX44SD``).
    """
    # `specify_cli.*` is `follow_imports = skip` under mypy (pyproject.toml), so the
    # call resolves as `Any`; the explicit annotation pins the declared return shape
    # instead of propagating `Any` out of this function.
    changed: tuple[str, ...] = merge_base_changed_files(repo_root, base_ref)
    return changed


def build_report(
    *,
    repo_root: Path | None = None,
    base_ref: str | None = None,
    router: Router | None = None,
) -> ParityReport:
    """Build the full local parity report for *repo_root* (default: this repo)."""
    repo = repo_root or _REPO_ROOT
    ref = base_ref or _resolve_base_ref(repo, DEFAULT_BASE_REF_CANDIDATES)
    changed = local_changed_paths(repo, ref)
    selection = resolve_selection(changed, router=router)
    return ParityReport(base_ref=ref, changed_paths=changed, selection=selection)


def format_report(report: ParityReport) -> str:
    """Render *report* as the human-readable summary the CLI prints."""
    lines = [
        f"Local gate parity vs {report.base_ref} (#2476)",
        f"Changed paths ({len(report.changed_paths)}):",
    ]
    lines.extend(f"  - {path}" for path in report.changed_paths)
    if not report.changed_paths:
        lines.append("  (none)")
    if report.selection.unmatched_src:
        lines.append("Unmatched src/** change -> fail-closed run-all (FR-004): every group is selected.")
    lines.append(f"Selected jobs ({len(report.selection.selected_jobs)}):")
    lines.extend(f"  - {job}" for job in sorted(report.selection.selected_jobs))
    lines.append(f"Selected code shards ({len(report.selection.selected_code_shards)}):")
    if report.selection.selected_code_shards:
        lines.extend(f"  - {job}" for job in sorted(report.selection.selected_code_shards))
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint (T096): preview locally which CI gates/shards a diff selects."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        default=None,
        help=(f"Ref to diff the merge-base against (default: the first of {DEFAULT_BASE_REF_CANDIDATES} that resolves)."),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root to run git commands in (default: this checkout).",
    )
    args = parser.parse_args(argv)
    report = build_report(repo_root=args.repo_root, base_ref=args.base_ref)
    print(format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
