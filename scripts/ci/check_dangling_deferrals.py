#!/usr/bin/env python3
"""FR-016 — fail a pull request still carrying a dangling deferral (WP18).

ADR 2026-07-23-2 / data-model.md NI-6: ``deferred_to_consolidation`` is a
scheduled follow-up, not a finished judgement, and the mission loop's ONE
reader of the acceptance matrix (``acceptance/gates_core.py``, inside the
accept gate) runs pre-consolidation — the only phase at which a loop guardrail
could fire is also the phase that CREATES the deferral, so a guardrail there
would be circular (see the ADR's "why enforcement cannot live in the loop"
section). Enforcement therefore lives here: a consistency check that runs on
the pull request, where the consolidated tree and the acceptance-matrix
artifact are both present and something automated reads them.

This script scans every ``kitty-specs/<mission>/acceptance-matrix.json`` and
fails (non-zero exit) when any negative invariant's ``result`` is still
``deferred_to_consolidation`` — i.e. the post-consolidation verification op
(``specify_cli.acceptance.post_consolidation.verify_deferred_invariants``) has
not run, or ran but left the invariant undecided, for that mission.

Deliberately zero-coupled to ``src/specify_cli``: this is a standalone,
dependency-free script (stdlib only) so the CI step that runs it needs no
project install — it reads plain JSON off disk. The ``deferred_to_consolidation``
string is therefore duplicated from ``specify_cli.acceptance.matrix
.DEFERRED_TO_CONSOLIDATION`` rather than imported; that constant is a stable,
serialized wire value (part of the on-disk matrix schema), not an
implementation detail expected to drift independently of this check.

Malformed JSON is reported as a warning (stderr) and skipped, not treated as a
dangling deferral — matrix *validity* is a separate concern already owned by
``validate_matrix_evidence``; this check's scope is narrowly the deferral
contract (Locality of Change).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Mirrors specify_cli.acceptance.matrix.DEFERRED_TO_CONSOLIDATION — see the
# module docstring for why this is duplicated rather than imported.
DEFERRED_TO_CONSOLIDATION = "deferred_to_consolidation"  # noqa: S105  # wire value, not a secret

MATRIX_GLOB = "*/acceptance-matrix.json"

EXIT_PASS = 0
EXIT_FAIL = 1

_REMEDIATION = (
    "Dispatch the post-consolidation verification op for this mission before "
    "merging (see docs/guides/accept-and-merge.md#deferred-invariants-and-the-"
    "post-consolidation-gate)."
)


@dataclass(frozen=True)
class DanglingDeferral:
    """One negative invariant still awaiting post-consolidation judgement."""

    mission_slug: str
    invariant_id: str
    deferred_reason: str | None
    matrix_path: Path

    def describe(self) -> str:
        reason = self.deferred_reason or "no deferred_reason recorded"
        return (
            f"{self.mission_slug}: negative invariant {self.invariant_id!r} is "
            f"still {DEFERRED_TO_CONSOLIDATION!r} ({reason}) — {self.matrix_path}"
        )


def _dangling_deferrals_in_matrix(
    matrix_path: Path, data: dict[str, object]
) -> list[DanglingDeferral]:
    mission_slug = data.get("mission_slug") or matrix_path.parent.name
    invariants = data.get("negative_invariants")
    if not isinstance(invariants, list):
        return []
    found: list[DanglingDeferral] = []
    for invariant in invariants:
        if not isinstance(invariant, dict):
            continue
        if invariant.get("result") != DEFERRED_TO_CONSOLIDATION:
            continue
        found.append(
            DanglingDeferral(
                mission_slug=str(mission_slug),
                invariant_id=str(invariant.get("invariant_id", "<unknown>")),
                deferred_reason=invariant.get("deferred_reason"),
                matrix_path=matrix_path,
            )
        )
    return found


def find_dangling_deferrals(kitty_specs_root: Path) -> list[DanglingDeferral]:
    """Scan every ``acceptance-matrix.json`` under *kitty_specs_root* (FR-016).

    Returns one :class:`DanglingDeferral` per negative invariant whose ``result``
    is still ``deferred_to_consolidation``. An absent *kitty_specs_root*, or a
    matrix that fails to parse, contributes no findings (see the module
    docstring on scope) — a warning is printed to stderr for the latter so a
    silently-corrupt matrix is not mistaken for "nothing deferred".
    """
    if not kitty_specs_root.is_dir():
        return []
    dangling: list[DanglingDeferral] = []
    for matrix_path in sorted(kitty_specs_root.glob(MATRIX_GLOB)):
        try:
            data = json.loads(matrix_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(
                f"warning: {matrix_path}: could not be parsed as JSON ({exc}); "
                "skipped by the FR-016 deferral check (matrix validity is a "
                "separate gate)",
                file=sys.stderr,
            )
            continue
        if not isinstance(data, dict):
            continue
        dangling.extend(_dangling_deferrals_in_matrix(matrix_path, data))
    return dangling


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("kitty-specs"),
        help=(
            "Directory holding <mission>/acceptance-matrix.json files "
            "(default: kitty-specs)"
        ),
    )
    args = parser.parse_args(argv)

    dangling = find_dangling_deferrals(args.root)
    if not dangling:
        print("FR-016: no dangling 'deferred_to_consolidation' invariants found.")
        return EXIT_PASS

    print(
        f"FR-016: {len(dangling)} negative invariant(s) are still "
        f"{DEFERRED_TO_CONSOLIDATION!r} — the post-consolidation verification "
        "op has not resolved them for this pull request:\n",
        file=sys.stderr,
    )
    for item in dangling:
        print(f"  - {item.describe()}", file=sys.stderr)
    print(f"\n{_REMEDIATION}", file=sys.stderr)
    return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
