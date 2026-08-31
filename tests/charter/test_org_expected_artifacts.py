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

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.activation.org_expected_artifacts import resolve_org_expected_artifacts
from charter.offering.missions.repository import MalformedManifestError

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_org_expected_artifacts(org_root: Path, mission_type: str, data: dict) -> None:
    """Write ``<org_root>/missions/<mission_type>/expected-artifacts.yaml``.

    Raw-root shape (C-4): unlike ``resolve_org_dirs`` consumers, this is a
    direct ``<org_root>/missions/<mission_type>/`` join — no fixed ``subdir``
    segment beyond the built-in-mirroring ``missions/`` anchor, since
    ``mission_type`` varies per call.
    """
    target_dir = org_root / "missions" / mission_type
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
        not kept reachable. Constructed directly rather than via
        ``_write_org_expected_artifacts`` -- that helper is corrected to the
        new anchor in this same file (T003), so routing this old-anchor case
        through it would make the fixture track whatever path the helper
        currently writes to instead of pinning the specific old path this
        test exists to prove is unreachable.
        """
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "software-dev"
        target_dir.mkdir(parents=True)
        yaml = YAML()
        yaml.default_flow_style = False
        with (target_dir / "expected-artifacts.yaml").open("w") as fh:
            yaml.dump(
                {
                    "schema_version": "1.0",
                    "mission_type": "software-dev",
                    "manifest_version": "old-anchor-only",
                },
                fh,
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
    """Fail-loud behaviour for a present-but-unparseable file (WP03,
    FR-007/FR-008/#3412) -- superseded from this class's pre-WP03
    warn-and-swallow-to-``None`` convention. A malformed org file is a
    genuine operator misconfiguration an operator authored and expected to
    take effect (C-006), so it now raises ``MalformedManifestError``
    instead of being treated as "no matching file" -- see
    ``tests/charter/activation/test_org_expected_artifacts.py`` for the
    red-first regression pins (#3412) that drove this widening.
    """

    def test_malformed_yaml_file_raises_malformed_manifest_error(
        self, tmp_path: Path
    ) -> None:
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "missions" / "software-dev"
        target_dir.mkdir(parents=True)
        bad_file = target_dir / "expected-artifacts.yaml"
        bad_file.write_text("schema_version: [unterminated flow seq\n", encoding="utf-8")

        with pytest.raises(MalformedManifestError) as excinfo:
            resolve_org_expected_artifacts([org_root], "software-dev")

        assert excinfo.value.path == bad_file

    def test_non_mapping_yaml_content_raises_malformed_manifest_error(
        self, tmp_path: Path
    ) -> None:
        org_root = tmp_path / "org-pack"
        target_dir = org_root / "missions" / "software-dev"
        target_dir.mkdir(parents=True)
        bad_file = target_dir / "expected-artifacts.yaml"
        bad_file.write_text("- just\n- a\n- list\n", encoding="utf-8")

        with pytest.raises(MalformedManifestError) as excinfo:
            resolve_org_expected_artifacts([org_root], "software-dev")

        assert excinfo.value.path == bad_file

    def test_well_formed_file_resolves_without_raising(self, tmp_path: Path) -> None:
        """Negative case for the two raise tests above: a well-formed org
        file resolves normally. Only a genuinely malformed file raises.
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

        result = resolve_org_expected_artifacts([org_root], "software-dev")

        assert result is not None
        assert result["manifest_version"] == "well-formed"

    def test_later_malformed_root_raises_even_with_earlier_good_match(
        self, tmp_path: Path
    ) -> None:
        """C-006 / spec Edge Cases: a broken file that would be the
        *effective* override (the last root reached with a matching file)
        fails loud -- it is NOT silently replaced by an earlier root's good
        match. This is the inverse of this class's pre-WP03 behaviour
        (formerly ``..._does_not_clobber_earlier_good_match``), which
        assumed the opposite: that a later malformed root would be skipped
        in favour of the earlier good one.
        """
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
        malformed_dir = second_root / "missions" / "software-dev"
        malformed_dir.mkdir(parents=True)
        bad_file = malformed_dir / "expected-artifacts.yaml"
        bad_file.write_text("schema_version: [unterminated flow seq\n", encoding="utf-8")

        with pytest.raises(MalformedManifestError) as excinfo:
            resolve_org_expected_artifacts([first_root, second_root], "software-dev")

        assert excinfo.value.path == bad_file


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
