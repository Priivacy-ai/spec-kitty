"""Unit tests for charter.mission_type_profiles (WP05).

Covers:
- MissionTypeProfile.mission_type accepts any str (no Literal constraint)
- UnknownMissionTypeError carries mission_type_id and registered_ids
- resolve_mission_type_governance() uses existing_mission_types() for validation
- Backward-compat: the hard-fail policy still works for truly unknown types

T034 — update ATDD test suite: MissionTypeProfile(mission_type="custom-type", ...)
       succeeds; UnknownMissionTypeError raised by resolve_action_sequence.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from charter.mission_type_profiles import (
    MissionTypeProfile,
    UnknownMissionTypeError,
    resolve_mission_type_governance,
)


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# T029 — MissionTypeProfile.mission_type is now str (no Literal constraint)
# ---------------------------------------------------------------------------


class TestMissionTypeProfileOpenStr:
    """MissionTypeProfile.mission_type MUST accept any string at model construction
    time. The Literal constraint was removed in T029 (FR-009).
    """

    def test_canonical_types_still_accepted(self) -> None:
        """The four canonical mission types remain valid."""
        for mt in ("software-dev", "documentation", "research", "plan"):
            profile = MissionTypeProfile(mission_type=mt)
            assert profile.mission_type == mt

    def test_custom_type_accepted_without_validation_error(self) -> None:
        """MissionTypeProfile(mission_type='custom-type') MUST NOT raise ValidationError.

        Before T029 this would fail with pydantic.ValidationError because the
        field was typed as Literal["software-dev", "documentation", "research", "plan"].
        After T029 the annotation is str — any value is accepted at model time.
        """
        profile = MissionTypeProfile(mission_type="custom-type")
        assert profile.mission_type == "custom-type"

    def test_arbitrary_string_accepted(self) -> None:
        """Any non-empty string is valid at model construction time."""
        profile = MissionTypeProfile(mission_type="compliance-audit")
        assert profile.mission_type == "compliance-audit"

    def test_pydantic_validation_error_not_raised_for_unknown(self) -> None:
        """The historical ValidationError for non-Literal values MUST NOT be raised."""
        try:
            from pydantic import ValidationError  # noqa: PLC0415
        except ImportError:
            pytest.skip("pydantic not installed")

        # This used to raise: before T029, any value outside the Literal set
        # caused a pydantic ValidationError at construction time.
        try:
            profile = MissionTypeProfile(mission_type="totally-custom")
        except ValidationError:
            pytest.fail(
                "MissionTypeProfile raised pydantic.ValidationError for "
                "mission_type='totally-custom'. T029 requires the annotation "
                "to be str, not Literal[...]. Remove the Literal constraint."
            )
        assert profile.mission_type == "totally-custom"


# ---------------------------------------------------------------------------
# T030 — UnknownMissionTypeError carries registered_ids
# ---------------------------------------------------------------------------


class TestUnknownMissionTypeError:
    """UnknownMissionTypeError MUST include registered_ids (FR-009)."""

    def test_message_contains_mission_type_id(self) -> None:
        """The exception message MUST contain the unknown mission_type_id verbatim."""
        err = UnknownMissionTypeError("compliance-audit")
        assert "compliance-audit" in str(err)

    def test_message_contains_registered_ids_when_provided(self) -> None:
        """When registered_ids are provided, the message lists them."""
        err = UnknownMissionTypeError(
            "compliance-audit",
            registered_ids=["documentation", "plan", "research", "software-dev"],
        )
        msg = str(err)
        assert "compliance-audit" in msg
        assert "documentation" in msg
        assert "software-dev" in msg

    def test_registered_ids_attribute_is_set(self) -> None:
        """err.registered_ids MUST be the list passed at construction."""
        ids = ["documentation", "plan", "research", "software-dev"]
        err = UnknownMissionTypeError("unknown-type", registered_ids=ids)
        assert err.registered_ids == ids

    def test_registered_ids_defaults_to_empty_list(self) -> None:
        """When no registered_ids are provided, the attribute defaults to []."""
        err = UnknownMissionTypeError("something")
        assert err.registered_ids == []

    def test_mission_type_id_attribute_is_set(self) -> None:
        """err.mission_type_id MUST equal the first positional argument."""
        err = UnknownMissionTypeError("compliance-audit", registered_ids=["software-dev"])
        assert err.mission_type_id == "compliance-audit"

    def test_is_value_error_subclass(self) -> None:
        """UnknownMissionTypeError MUST remain a ValueError subclass."""
        err = UnknownMissionTypeError("bad-type")
        assert isinstance(err, ValueError)

    def test_formatted_message_matches_fr009_contract(self) -> None:
        """FR-009: message format is 'Unknown mission type X. Registered types: A, B, C.'"""
        err = UnknownMissionTypeError(
            "compliance-audit",
            registered_ids=["documentation", "plan", "research", "software-dev"],
        )
        msg = str(err)
        assert "Unknown mission type" in msg
        assert "compliance-audit" in msg
        assert "Registered types:" in msg


# ---------------------------------------------------------------------------
# T033 — resolve_mission_type_governance uses existing_mission_types()
# ---------------------------------------------------------------------------


def _git_init_minimal(repo_root: Path) -> None:
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


class TestResolveMissionTypeGovernanceValidation:
    """resolve_mission_type_governance() uses existing_mission_types() for
    validation (T033).
    """

    def test_known_type_resolves_successfully(self, tmp_path: Path) -> None:
        """A mission type returned by existing_mission_types() resolves without error."""
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "test-mission-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_type": "software-dev", "mission_slug": "test-mission-001"}),
            encoding="utf-8",
        )

        # Mock existing_mission_types to return a controlled set including software-dev
        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=["documentation", "plan", "research", "software-dev"],
        ):
            payload = resolve_mission_type_governance(tmp_path, feature_dir)

        assert payload.mission_type == "software-dev"

    def test_unknown_type_raises_unknown_mission_type_error(self, tmp_path: Path) -> None:
        """A mission type not in existing_mission_types() raises UnknownMissionTypeError."""
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "unknown-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {"mission_type": "totally-custom-type", "mission_slug": "unknown-001"}
            ),
            encoding="utf-8",
        )

        # Mock: no project overrides, limited activation set
        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["documentation", "plan", "research", "software-dev"],
            ),
            patch(
                "charter.mission_type_profiles._project_has_doctrine_overrides",
                return_value=False,
            ),pytest.raises(UnknownMissionTypeError) as exc_info
        ):
            resolve_mission_type_governance(tmp_path, feature_dir)

        assert "totally-custom-type" in str(exc_info.value)

    def test_error_includes_registered_ids(self, tmp_path: Path) -> None:
        """UnknownMissionTypeError from resolve_mission_type_governance carries registered_ids."""
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "unknown-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {"mission_type": "compliance-audit", "mission_slug": "unknown-001"}
            ),
            encoding="utf-8",
        )

        activated = ["documentation", "plan", "research", "software-dev"]
        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=activated,
            ),
            patch(
                "charter.mission_type_profiles._project_has_doctrine_overrides",
                return_value=False,
            ),pytest.raises(UnknownMissionTypeError) as exc_info
        ):
            resolve_mission_type_governance(tmp_path, feature_dir)

        err = exc_info.value
        assert err.registered_ids == activated

    def test_project_with_overrides_does_not_hard_fail_for_unknown_type(
        self, tmp_path: Path
    ) -> None:
        """When project has doctrine overrides, unknown type skips the profile
        (no hard fail).
        """
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "custom-mission-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {"mission_type": "custom-type", "mission_slug": "custom-mission-001"}
            ),
            encoding="utf-8",
        )

        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["documentation", "plan", "research", "software-dev"],
            ),
            patch(
                "charter.mission_type_profiles._project_has_doctrine_overrides",
                return_value=True,
            ),
        ):
            # Should NOT raise — project overrides bypass the unknown-type check
            payload = resolve_mission_type_governance(tmp_path, feature_dir)

        assert payload.mission_type == "custom-type"

    def test_missing_mission_type_key_raises_value_error(self, tmp_path: Path) -> None:
        """meta.json without 'mission_type' key raises ValueError (not UnknownMissionTypeError)."""
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "no-type-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_slug": "no-type-001"}),
            encoding="utf-8",
        )

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=["software-dev"],
        ), pytest.raises((ValueError,)) as exc_info:
            resolve_mission_type_governance(tmp_path, feature_dir)

        # The error must mention the missing key, not be an UnknownMissionTypeError
        assert "mission_type" in str(exc_info.value)
