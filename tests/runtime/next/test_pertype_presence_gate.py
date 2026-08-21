"""Live per-type presence gate + stray-spec.md delete (FR-011/012, #3597).

Mission rc3-charter-gate-predicate-inversion-01M0GGT1, WP05 (plan.md §WP04b).
Depends on WP04's artifact-filename seam
(``specify_cli.runtime.resolver.required_artifacts_for`` /
``resolve_configured_artifact_name``, #3599): ``gather_artifact_presence``
(``runtime.next.runtime_bridge_io``) now consults the resolved per-type
``path_pattern`` set for the (mission_family, step_id) pair instead of the
previously-closed ``_PRESENCE_FILE_TAGS`` 10-tuple.

AC-10 (fail-closed both directions): a custom mission family gates on its
OWN filename -- present -> passes, absent -> blocks -- as long as it ships
an ``expected-artifacts.yaml`` with a blocking ``path_pattern`` entry at the
step being gathered for. Both directions are asserted here (a present-only
test would permit a fail-open gate, the exact defect this mission kills).

The ``evaluate_guards_strict`` ``UnregisteredMissionFamilyError`` strict-raise
is a DISTINCT, retained concern (guard-table *dispatch* for a genuinely
unregistered family) -- not removed by this change; see the ADR
(``docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md``,
"Custom-family gate mechanism").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.missions import MissionTemplateRepository
from runtime.next.runtime_bridge_cores import (
    UnregisteredMissionFamilyError,
    evaluate_guards_strict,
)
from runtime.next.runtime_bridge_io import gather_artifact_presence

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_CUSTOM_MISSION_TYPE = "custom-family"
_CUSTOM_STEP_ID = "custom-step"
_CUSTOM_FILENAME = "custom-artifact.md"

_CUSTOM_EXPECTED_ARTIFACTS_YAML = f"""\
schema_version: "1.0"
mission_type: "{_CUSTOM_MISSION_TYPE}"
manifest_version: "1"
required_always: []
required_by_step:
  {_CUSTOM_STEP_ID}:
    - artifact_key: "output.custom.main"
      artifact_class: "output"
      path_pattern: "{_CUSTOM_FILENAME}"
      blocking: true
optional_always: []
"""


@pytest.fixture
def custom_mission_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point ``MissionTemplateRepository.default()`` at a temp missions root
    shipping a custom mission type's own ``expected-artifacts.yaml`` -- the
    ADR's data-driven custom-family gate mechanism (no ``_GUARD_TABLES``
    code registration)."""
    missions_root = tmp_path / "missions-root"
    custom_dir = missions_root / _CUSTOM_MISSION_TYPE
    custom_dir.mkdir(parents=True)
    (custom_dir / "expected-artifacts.yaml").write_text(
        _CUSTOM_EXPECTED_ARTIFACTS_YAML, encoding="utf-8"
    )

    monkeypatch.setattr(
        MissionTemplateRepository,
        "default",
        classmethod(lambda cls: MissionTemplateRepository(missions_root)),
    )


class TestCustomFamilyPresenceGateFailsClosedBothDirections:
    """AC-10: ``gather_artifact_presence`` -- the named entry point -- gates
    a custom family on its own filename, both directions."""

    def test_present_filename_is_detected(
        self, tmp_path: Path, custom_mission_repo: None
    ) -> None:
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        (feature_dir / _CUSTOM_FILENAME).write_text("# custom\n", encoding="utf-8")

        snapshot = gather_artifact_presence(
            feature_dir, mission_family=_CUSTOM_MISSION_TYPE, step_id=_CUSTOM_STEP_ID
        )

        assert _CUSTOM_FILENAME in snapshot.present_artifacts

    def test_absent_filename_is_not_detected(
        self, tmp_path: Path, custom_mission_repo: None
    ) -> None:
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        # _CUSTOM_FILENAME deliberately NOT created.

        snapshot = gather_artifact_presence(
            feature_dir, mission_family=_CUSTOM_MISSION_TYPE, step_id=_CUSTOM_STEP_ID
        )

        assert _CUSTOM_FILENAME not in snapshot.present_artifacts

    def test_unrelated_builtin_filename_never_leaks_into_custom_family(
        self, tmp_path: Path, custom_mission_repo: None
    ) -> None:
        """A custom family's presence set is genuinely per-type -- a
        built-in filename that happens to also exist on disk (e.g.
        ``spec.md``) is not spuriously reported present for a custom
        family/step that never declared it."""
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")

        snapshot = gather_artifact_presence(
            feature_dir, mission_family=_CUSTOM_MISSION_TYPE, step_id=_CUSTOM_STEP_ID
        )

        assert snapshot.present_artifacts == frozenset()


def test_unregistered_family_guard_dispatch_strict_raise_is_retained(
    tmp_path: Path,
) -> None:
    """The ``evaluate_guards_strict`` ``UnregisteredMissionFamilyError``
    strict-raise stays for guard-table *dispatch* of a genuinely
    unregistered family -- a distinct concern from presence gathering
    (per the ADR); this WP must not remove it. No custom manifest is
    installed here, so ``gather_artifact_presence`` itself degrades
    gracefully (empty presence set), and the raise happens one layer up,
    at guard-table lookup."""
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir()

    snapshot = gather_artifact_presence(
        feature_dir, mission_family="totally-unregistered-family", step_id="whatever"
    )

    with pytest.raises(UnregisteredMissionFamilyError):
        evaluate_guards_strict(snapshot)
