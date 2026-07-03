"""Tasks-domain gate-visibility assertion (FR-009, mission tasks-py-degod-wave2-01KWH9EQ).

The gate-coverage ratchet (``test_gate_coverage.py`` +
``_gate_coverage_baseline.json``) blocks *new* orphan files suite-wide, but the
baseline itself is legally growable via ``--update-baseline``. FR-009 prohibits
that growth path for the tasks domain specifically: absorbing a tasks-domain
path into the baseline is a violation, not a fix (spec C-006).

This module makes that prohibition PERMANENT rather than a one-time census:
if any ``orphan_files`` entry in the committed baseline matches the FR-009
glob, this test goes red — regardless of how the entry got there.

The census artifact (evidence side of FR-009) lives at
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/marker-census.md``.
"""

from __future__ import annotations

from fnmatch import fnmatch

import pytest

from tests.architectural._gate_coverage import load_baseline

# Architectural-directory convention (see test_tasks_command_surface.py):
# selected by the core-misc ``architectural`` shard via the ``architectural``
# marker; ``fast`` keeps it in the developer fast loop too (pure JSON read).
pytestmark = [pytest.mark.architectural, pytest.mark.fast]

# FR-009 glob — hardcoded verbatim from the mission spec
# (kitty-specs/tasks-py-degod-wave2-01KWH9EQ/spec.md, FR-009): the tasks-domain
# test surface is ``tests/tasks/**``,
# ``tests/specify_cli/cli/commands/agent/test_tasks*``, plus every test file
# this mission added (the byte-freeze suite and seam tests all live under the
# ``test_tasks*`` glob; the two architectural files are named explicitly).
# Do NOT narrow these patterns to make a red pass — that is the
# definition-shrinking evasion the mission squad flagged.
_FR009_GLOB: tuple[str, ...] = (
    "tests/tasks/**",
    "tests/specify_cli/cli/commands/agent/test_tasks*",
    "tests/architectural/test_tasks_command_surface.py",
    "tests/architectural/test_tasks_domain_gate_visibility.py",
)


def tasks_domain_orphans(orphan_files: list[str]) -> list[str]:
    """Return the ``orphan_files`` entries that fall in the FR-009 tasks domain.

    Pure check function — driven by both the real-baseline assertion and the
    theater test below, so the wiring itself is proven to fire (DIRECTIVE_043
    non-vacuity).
    """
    return sorted(
        path
        for path in orphan_files
        if any(fnmatch(path.replace("\\", "/"), pattern) for pattern in _FR009_GLOB)
    )


def test_no_tasks_domain_path_in_orphan_baseline() -> None:
    """FR-009: the committed orphan baseline must contain no tasks-domain file.

    A red here means someone ran ``--update-baseline`` while a tasks-domain
    test file was selected by zero CI gates. The fix is to mark/route the file
    into a gate (see marker-census.md for the per-file gate mapping), never to
    keep the baseline entry.
    """
    baseline = load_baseline()
    orphans = baseline.get("orphan_files", [])
    assert isinstance(orphans, list)
    offenders = tasks_domain_orphans(orphans)
    assert offenders == [], (
        "FR-009 violation: tasks-domain test file(s) entered the gate-coverage "
        f"orphan baseline (selected by ZERO CI gates): {offenders}. "
        "Add/repair markers so a ci-quality.yml gate selects the file; do not "
        "absorb it into _gate_coverage_baseline.json."
    )


def test_theater_synthetic_tasks_orphan_fires() -> None:
    """Non-vacuity: a synthetic baseline with tasks-domain orphans is detected.

    Drives the SAME check function the real assertion uses, one synthetic path
    per FR-009 pattern family, and requires every one to be flagged while the
    genuinely-out-of-domain entries are not.
    """
    synthetic_baseline: dict[str, object] = {
        "orphan_files": [
            # In-domain: one per FR-009 pattern family.
            "tests/tasks/test_synthetic_orphan.py",
            "tests/tasks/nested/test_synthetic_nested.py",
            "tests/specify_cli/cli/commands/agent/test_tasks_synthetic.py",
            "tests/architectural/test_tasks_command_surface.py",
            "tests/architectural/test_tasks_domain_gate_visibility.py",
            # Out-of-domain: real current baseline residents; must NOT match.
            "tests/_support/git_template/test_git_template.py",
            "tests/specify_cli/cli/commands/agent/test_workflow.py",
        ]
    }
    orphans = synthetic_baseline["orphan_files"]
    assert isinstance(orphans, list)
    offenders = tasks_domain_orphans(orphans)
    assert offenders == [
        "tests/architectural/test_tasks_command_surface.py",
        "tests/architectural/test_tasks_domain_gate_visibility.py",
        "tests/specify_cli/cli/commands/agent/test_tasks_synthetic.py",
        "tests/tasks/nested/test_synthetic_nested.py",
        "tests/tasks/test_synthetic_orphan.py",
    ]
    # And the assertion form used by the real test fires on this input.
    with pytest.raises(AssertionError):
        assert tasks_domain_orphans(orphans) == []
