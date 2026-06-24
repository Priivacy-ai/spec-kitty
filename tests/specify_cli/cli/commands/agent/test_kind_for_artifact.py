"""Unit tests for ``_kind_for_artifact`` (write-surface-coherence WP02 / T007).

``_commit_to_branch`` maps its ``artifact_type`` string to a canonical
:class:`~mission_runtime.MissionArtifactKind` via ``_kind_for_artifact``. Every
mapped type is a PRIMARY planning kind (planning artifacts live with their
mission on the primary surface), and an UNMAPPED type raises loudly rather than
silently defaulting to ``SPEC`` (DECISION 1: the kind must be named, not guessed).
"""

from __future__ import annotations

import pytest

from mission_runtime import MissionArtifactKind
from specify_cli.cli.commands.agent.mission import _kind_for_artifact

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.mark.parametrize(
    ("artifact_type", "expected"),
    [
        ("spec", MissionArtifactKind.SPEC),
        ("plan", MissionArtifactKind.FINALIZED_EXECUTION_PLAN),
        ("tasks", MissionArtifactKind.TASKS_INDEX),
    ],
)
def test_kind_for_artifact_maps_known_types(
    artifact_type: str, expected: MissionArtifactKind
) -> None:
    """Each known planning ``artifact_type`` maps to its canonical primary kind."""
    assert _kind_for_artifact(artifact_type) == expected


def test_kind_for_artifact_raises_on_unmapped_type() -> None:
    """An unmapped artifact type raises (no silent SPEC default) — DECISION 1."""
    with pytest.raises(KeyError) as excinfo:
        _kind_for_artifact("definitely-not-a-known-artifact")
    # The message names the offending type and points at the mapping to extend.
    assert "definitely-not-a-known-artifact" in str(excinfo.value)
    assert "_ARTIFACT_TYPE_TO_KIND" in str(excinfo.value)


def test_kind_for_artifact_only_returns_primary_kinds() -> None:
    """All mapped kinds are PRIMARY kinds — none route through coordination.

    A regression that mapped a planning ``artifact_type`` to a coordination kind
    (e.g. ``STATUS_STATE`` / ``ANALYSIS_REPORT``) would wrongly route the planning
    artifact to the coordination branch — the split-brain this mission closes.
    """
    coord_kinds = {
        MissionArtifactKind.STATUS_STATE,
        MissionArtifactKind.ANALYSIS_REPORT,
        MissionArtifactKind.ACCEPTANCE_MATRIX,
        MissionArtifactKind.ISSUE_MATRIX,
    }
    for artifact_type in ("spec", "plan", "tasks"):
        assert _kind_for_artifact(artifact_type) not in coord_kinds
