"""Focused unit tests for the auto-rebase take-theirs recognition seam.

Regression coverage for the #2070-delegation / #2090-partition decoupling: the
auto-rebase "managed-artifact reconciliation" set is a SUPERSET of the
surface-residue set. Delegating solely to
``mission_runtime.is_coordination_artifact_residue_path`` (the #2070 change)
dropped the PRIMARY-partition planning-LAYOUT artifacts (``lanes.json`` /
``tasks/WP*.md``) after #2090 moved them out of the residue set, halting
auto-rebase on a ``lanes.json`` conflict. These tests pin the two arms of
``_is_coordination_owned_artifact`` directly so the intent is documented and
fast to verify, independent of the heavier on-disk git integration tests.
"""

from __future__ import annotations

import pytest

from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.lanes.auto_rebase import _is_coordination_owned_artifact

# Pure-logic predicate tests (no subprocess/git/tmp_path): `fast` is a registered
# marker (pytest.ini) and is the marker the lanes CI shard selects
# (`tests/lanes/ ... -m "fast and not windows_ci"` in ci-quality.yml), so these
# tests run in a CI gate instead of falling into the zero-gate orphan set. The
# sibling test_auto_rebase_additive.py uses `git_repo` only because it builds a
# real repo; these tests do not, so `fast` matches their nature.
pytestmark = pytest.mark.fast

_SLUG = "managed-artifacts-01KVZP8E"


def _rel(name: str) -> str:
    return f"{KITTY_SPECS_DIR}/{_SLUG}/{name}"


@pytest.mark.parametrize(
    "rel_path",
    [
        # Arm 2 — mission-owned planning LAYOUT (PRIMARY-partition, NOT surface
        # residue post-#2090, yet auto-rebase resolves take-theirs).
        _rel("lanes.json"),
        _rel("tasks/WP08-renderer-unit-tests.md"),
        # Arm 1 — surface residue drawn from the single authority.
        _rel("issue-matrix.md"),
        _rel("analysis-report.md"),
        _rel("acceptance-matrix.json"),
    ],
)
def test_take_theirs_recognizes_managed_artifacts(rel_path: str) -> None:
    assert _is_coordination_owned_artifact(rel_path) is True


@pytest.mark.parametrize(
    "rel_path",
    [
        # Author-owned narrative planning docs — Manual halt, never take-theirs.
        _rel("plan.md"),
        _rel("tasks.md"),
        # Planning SOURCE docs — never take-theirs.
        _rel("spec.md"),
        _rel("data-model.md"),
        _rel("research.md"),
        # Code files outside kitty-specs/ — never coordination-owned.
        "src/specify_cli/lanes/auto_rebase.py",
        # An unrelated top-level file.
        "README.md",
    ],
)
def test_take_theirs_excludes_non_managed_paths(rel_path: str) -> None:
    assert _is_coordination_owned_artifact(rel_path) is False


@pytest.mark.parametrize(
    "rel_path",
    [
        _rel("status.events.jsonl"),
        _rel("status.json"),
    ],
)
def test_status_artifacts_are_residue_but_intercepted_before_this_arm(
    rel_path: str,
) -> None:
    """Status artifacts ARE surface residue per the authority, so the predicate
    reports True — but ``_resolve_managed_artifact_conflicts`` routes them to the
    union / rematerialize arms BEFORE consulting this predicate, so they are never
    resolved take-theirs. This pins that the take-theirs predicate itself does not
    special-case them (the orchestration ordering is the guard)."""
    assert _is_coordination_owned_artifact(rel_path) is True
