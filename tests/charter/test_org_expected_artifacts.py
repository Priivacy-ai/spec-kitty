"""Unit tests for ``charter.activation.org_expected_artifacts`` (WP05, T025, FR-008).

Covers contract C-4's binding shape directly, at the helper level (no
``resolve_mission_type_context`` seam involved — that integration is
``TestOrgTierExpectedArtifactsThreading`` in ``test_mission_type_profiles.py``,
T026):

- No org roots (or none with a matching file) -> ``None``.
- One org root with the file -> parsed mapping returned.
- Two org roots both with the file -> the LATER root's content wins
  (NFR-003 declared-order precedence — the opposite of FR-002's first-match).
- A custom mission type with no built-in baseline at all -> still resolves
  from the org file alone (this helper never touches the built-in tree).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.activation.org_expected_artifacts import resolve_org_expected_artifacts

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_LOGGER_NAME = "charter.activation.org_expected_artifacts"


def _write_org_expected_artifacts(org_root: Path, mission_type: str, data: dict) -> None:
    """Write ``<org_root>/<mission_type>/expected-artifacts.yaml``.

    Raw-root shape (C-4): unlike ``resolve_org_dirs`` consumers, this is a
    direct ``<org_root>/<mission_type>/`` join — no fixed ``subdir`` segment,
    since ``mission_type`` varies per call.
    """
    target_dir = org_root / mission_type
    target_dir.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with (target_dir / "expected-artifacts.yaml").open("w") as fh:
        yaml.dump(data, fh)


class TestResolveOrgExpectedArtifactsEmptyCases:
    def test_no_org_roots_returns_none(self) -> None:
        assert resolve_org_expected_artifacts([], "software-dev") is None

    def test_org_root_exists_but_no_matching_file_returns_none(self, tmp_path: Path) -> None:
        org_root = tmp_path / "org-pack"
        org_root.mkdir()
        assert resolve_org_expected_artifacts([org_root], "software-dev") is None

    def test_org_root_has_file_for_other_mission_type_returns_none(self, tmp_path: Path) -> None:
        org_root = tmp_path / "org-pack"
        _write_org_expected_artifacts(
            org_root,
            "research",
            {"schema_version": "1.0", "mission_type": "research", "manifest_version": "1"},
        )
        assert resolve_org_expected_artifacts([org_root], "software-dev") is None

    def test_file_at_corrected_missions_anchor_is_found(self, tmp_path: Path) -> None:
        """FR-001/NFR-001 RED-first pin: a pack laid out at the corrected,
        built-in-mirroring anchor (``<org_root>/missions/<mission_type>/``)
        must be found. Constructed directly rather than via
        ``_write_org_expected_artifacts`` -- that helper still writes to the
        old, pre-fix path at this point in the sequence (T003 fixes it
        later), so routing through it here would make this test's RED/GREEN
        state depend on a helper change that hasn't landed yet.
        """
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "missions" / "software-dev"
        target_dir.mkdir(parents=True)
        yaml = YAML()
        yaml.default_flow_style = False
        with (target_dir / "expected-artifacts.yaml").open("w") as fh:
            yaml.dump(
                {
                    "schema_version": "1.0",
                    "mission_type": "software-dev",
                    "manifest_version": "corrected-anchor",
                },
                fh,
            )

        result = resolve_org_expected_artifacts([org_root], "software-dev")

        assert result is not None
        assert result["manifest_version"] == "corrected-anchor"

    def test_file_only_at_old_anchor_returns_none(self, tmp_path: Path) -> None:
        """FR-003/SC-004 RED-first pin: a pack laid out ONLY at the old,
        pre-fix anchor (``<org_root>/<mission_type>/``, no ``missions/``
        segment) must resolve to ``None`` post-fix -- the old location has
        zero possible existing consumers (C-002, no sibling-fallback) and is
        not kept reachable. ``_write_org_expected_artifacts`` still writes to
        exactly this old path today, so using it here is fine and idiomatic.
        """
        org_root = tmp_path / "org-pack"
        _write_org_expected_artifacts(
            org_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "old-anchor-only",
            },
        )

        assert resolve_org_expected_artifacts([org_root], "software-dev") is None


class TestResolveOrgExpectedArtifactsSingleRoot:
    def test_single_org_root_with_file_returns_parsed_mapping(self, tmp_path: Path) -> None:
        org_root = tmp_path / "org-pack"
        _write_org_expected_artifacts(
            org_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "org-1",
                "required_always": [
                    {
                        "artifact_key": "policy.org-required",
                        "artifact_class": "policy",
                        "path_pattern": "org-policy.md",
                        "blocking": True,
                    }
                ],
            },
        )

        result = resolve_org_expected_artifacts([org_root], "software-dev")

        assert result is not None
        assert result["manifest_version"] == "org-1"
        assert result["required_always"][0]["artifact_key"] == "policy.org-required"


class TestResolveOrgExpectedArtifactsDeclaredOrderPrecedence:
    def test_two_org_roots_later_declared_root_wins(self, tmp_path: Path) -> None:
        """NFR-003: declared-order precedence, proven with a deliberately
        non-alphabetical declaration order (z-pack before a-pack) so lexical
        path sorting cannot accidentally pass this test.
        """
        first_root = tmp_path / "z-org-pack"
        second_root = tmp_path / "a-org-pack"
        _write_org_expected_artifacts(
            first_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "first-declared",
            },
        )
        _write_org_expected_artifacts(
            second_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "second-declared",
            },
        )

        result = resolve_org_expected_artifacts([first_root, second_root], "software-dev")

        assert result is not None
        assert result["manifest_version"] == "second-declared"

    def test_later_root_without_matching_file_does_not_clear_earlier_match(
        self, tmp_path: Path
    ) -> None:
        """A later ``org_roots`` entry with no matching file must not clear
        an earlier root's match -- only a later MATCH overrides, per C-4's
        "last-EXISTING-match wins" wording.
        """
        first_root = tmp_path / "z-org-pack"
        second_root = tmp_path / "a-org-pack"
        _write_org_expected_artifacts(
            first_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "only-match",
            },
        )
        second_root.mkdir()  # exists, but no expected-artifacts.yaml for software-dev

        result = resolve_org_expected_artifacts([first_root, second_root], "software-dev")

        assert result is not None
        assert result["manifest_version"] == "only-match"


class TestResolveOrgExpectedArtifactsMalformedFile:
    """Fail-closed-to-None behaviour for a present-but-unparseable file,
    mirroring ``MissionTemplateRepository.get_expected_artifacts``'s
    convention (see this module's docstring). An earlier root's good match
    still stands when a LATER root's file is malformed.
    """

    def test_malformed_yaml_file_treated_as_no_match(self, tmp_path: Path) -> None:
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "software-dev"
        target_dir.mkdir(parents=True)
        (target_dir / "expected-artifacts.yaml").write_text(
            "schema_version: [unterminated flow seq\n", encoding="utf-8"
        )

        assert resolve_org_expected_artifacts([org_root], "software-dev") is None

    def test_non_mapping_yaml_content_treated_as_no_match(self, tmp_path: Path) -> None:
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "software-dev"
        target_dir.mkdir(parents=True)
        (target_dir / "expected-artifacts.yaml").write_text(
            "- just\n- a\n- list\n", encoding="utf-8"
        )

        assert resolve_org_expected_artifacts([org_root], "software-dev") is None

    def test_malformed_yaml_file_logs_a_warning_naming_the_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A malformed org file is a genuine operator misconfiguration, not
        "this org pack legitimately doesn't override this mission type" --
        distinguishing those two must not depend on log-diffing an INFO
        line. This is the recurrence, one layer up, of the defect WP01 was
        reopened for under NFR-002 (see ``resolve_org_dirs``).
        """
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "software-dev"
        target_dir.mkdir(parents=True)
        bad_file = target_dir / "expected-artifacts.yaml"
        bad_file.write_text("schema_version: [unterminated flow seq\n", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
            result = resolve_org_expected_artifacts([org_root], "software-dev")

        assert result is None
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) == 1
        message = warning_records[0].getMessage()
        assert str(bad_file) in message

    def test_non_mapping_yaml_content_logs_a_warning_naming_the_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "software-dev"
        target_dir.mkdir(parents=True)
        bad_file = target_dir / "expected-artifacts.yaml"
        bad_file.write_text("- just\n- a\n- list\n", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
            result = resolve_org_expected_artifacts([org_root], "software-dev")

        assert result is None
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) == 1
        assert str(bad_file) in warning_records[0].getMessage()

    def test_well_formed_file_emits_no_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Negative case for the two warning tests above: a well-formed org
        file -- the ordinary "no override for this mission type" and the
        successful-override paths alike -- must NOT log a WARNING. Only a
        genuinely malformed file should.
        """
        org_root = tmp_path / "org-pack"
        _write_org_expected_artifacts(
            org_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "well-formed",
            },
        )

        with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
            result = resolve_org_expected_artifacts([org_root], "software-dev")

        assert result is not None
        assert result["manifest_version"] == "well-formed"
        assert not any(r.levelno == logging.WARNING for r in caplog.records)

    def test_later_malformed_root_does_not_clobber_earlier_good_match(
        self, tmp_path: Path
    ) -> None:
        first_root = tmp_path / "z-org-pack"
        second_root = tmp_path / "a-org-pack"
        _write_org_expected_artifacts(
            first_root,
            "software-dev",
            {
                "schema_version": "1.0",
                "mission_type": "software-dev",
                "manifest_version": "good-match",
            },
        )
        malformed_dir = second_root / "software-dev"
        malformed_dir.mkdir(parents=True)
        (malformed_dir / "expected-artifacts.yaml").write_text(
            "schema_version: [unterminated flow seq\n", encoding="utf-8"
        )

        result = resolve_org_expected_artifacts([first_root, second_root], "software-dev")

        assert result is not None
        assert result["manifest_version"] == "good-match"


class TestResolveOrgExpectedArtifactsCustomMissionType:
    def test_custom_mission_type_with_no_builtin_baseline_still_resolves(
        self, tmp_path: Path
    ) -> None:
        """A wholly org-defined custom mission type (no built-in
        ``expected-artifacts.yaml`` anywhere) is valid input -- this helper
        is authoritative with no built-in fallback of its own.
        """
        org_root = tmp_path / "org-pack"
        _write_org_expected_artifacts(
            org_root,
            "wholly-custom-type",
            {
                "schema_version": "1.0",
                "mission_type": "wholly-custom-type",
                "manifest_version": "custom-1",
            },
        )

        result = resolve_org_expected_artifacts([org_root], "wholly-custom-type")

        assert result is not None
        assert result["manifest_version"] == "custom-1"
