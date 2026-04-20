"""Schema validation tests for architecture/2.x/shim-registry.yaml (FR-011)."""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.compat.registry import RegistrySchemaError, validate_registry

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _REPO_ROOT / "architecture" / "2.x" / "shim-registry.yaml"

_VALID_ENTRY: dict[str, object] = {
    "legacy_path": "specify_cli.old_module",
    "canonical_import": "new_module",
    "introduced_in_release": "3.2.0",
    "removal_target_release": "3.3.0",
    "tracker_issue": "#615",
    "grandfathered": False,
}


def _entry(**overrides: object) -> dict[str, object]:
    return {**_VALID_ENTRY, **overrides}


class TestLiveRegistry:
    def test_live_registry_passes_validation(self) -> None:
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        with _REGISTRY_PATH.open() as fp:
            data = yaml.load(fp)
        validate_registry(data)

    def test_live_registry_is_empty_baseline(self) -> None:
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        with _REGISTRY_PATH.open() as fp:
            data = yaml.load(fp)
        assert data["shims"] == [], "Baseline registry must be empty at mission-615 start"


class TestTopLevelStructure:
    def test_non_dict_top_level_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="top-level"):
            validate_registry(["not", "a", "dict"])

    def test_missing_shims_key_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="top-level"):
            validate_registry({"other_key": []})

    def test_shims_not_a_list_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="top-level.shims"):
            validate_registry({"shims": "not-a-list"})

    def test_empty_shims_list_is_valid(self) -> None:
        validate_registry({"shims": []})

    def test_valid_full_entry_passes(self) -> None:
        validate_registry({"shims": [_entry()]})


class TestRequiredFields:
    @pytest.mark.parametrize(
        "field",
        [
            "legacy_path",
            "canonical_import",
            "introduced_in_release",
            "removal_target_release",
            "tracker_issue",
            "grandfathered",
        ],
    )
    def test_missing_required_field_raises(self, field: str) -> None:
        bad = {k: v for k, v in _VALID_ENTRY.items() if k != field}
        with pytest.raises(RegistrySchemaError) as exc_info:
            validate_registry({"shims": [bad]})
        assert field in "\n".join(exc_info.value.errors)


class TestLegacyPath:
    def test_bad_legacy_path_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="legacy_path"):
            validate_registry({"shims": [_entry(legacy_path="123-invalid")]})

    def test_duplicate_legacy_path_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="legacy_path"):
            validate_registry({"shims": [_entry(), _entry()]})

    def test_dotted_legacy_path_is_valid(self) -> None:
        validate_registry({"shims": [_entry(legacy_path="specify_cli.charter.context")]})


class TestCanonicalImport:
    def test_string_canonical_import_is_valid(self) -> None:
        validate_registry({"shims": [_entry(canonical_import="charter.context")]})

    def test_list_canonical_import_is_valid(self) -> None:
        validate_registry({"shims": [_entry(canonical_import=["charter.context", "charter.bundle"])]})

    def test_empty_list_canonical_import_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="canonical_import"):
            validate_registry({"shims": [_entry(canonical_import=[])]})

    def test_invalid_string_canonical_import_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="canonical_import"):
            validate_registry({"shims": [_entry(canonical_import="123-bad")]})

    def test_non_string_non_list_canonical_import_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="canonical_import"):
            validate_registry({"shims": [_entry(canonical_import=42)]})


class TestVersionFields:
    def test_bad_semver_introduced_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="introduced_in_release"):
            validate_registry({"shims": [_entry(introduced_in_release="3.2")]})

    def test_bad_semver_removal_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="removal_target_release"):
            validate_registry({"shims": [_entry(removal_target_release="next")]})

    def test_removal_before_introduced_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="removal_target_release"):
            validate_registry(
                {"shims": [_entry(introduced_in_release="3.3.0", removal_target_release="3.2.0")]}
            )

    def test_removal_equal_introduced_is_valid(self) -> None:
        validate_registry(
            {"shims": [_entry(introduced_in_release="3.2.0", removal_target_release="3.2.0")]}
        )

    def test_prerelease_semver_is_valid(self) -> None:
        validate_registry(
            {"shims": [_entry(introduced_in_release="3.2.0a1", removal_target_release="3.3.0")]}
        )


class TestTrackerIssue:
    def test_hash_ref_tracker_is_valid(self) -> None:
        validate_registry({"shims": [_entry(tracker_issue="#123")]})

    def test_url_tracker_is_valid(self) -> None:
        validate_registry({"shims": [_entry(tracker_issue="https://github.com/org/repo/issues/1")]})

    def test_bad_tracker_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="tracker_issue"):
            validate_registry({"shims": [_entry(tracker_issue="not-a-ref")]})


class TestGrandfathered:
    def test_string_true_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="grandfathered"):
            validate_registry({"shims": [_entry(grandfathered="true")]})

    def test_bool_true_is_valid(self) -> None:
        validate_registry({"shims": [_entry(grandfathered=True)]})

    def test_bool_false_is_valid(self) -> None:
        validate_registry({"shims": [_entry(grandfathered=False)]})


class TestOptionalFields:
    def test_empty_extension_rationale_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="extension_rationale"):
            validate_registry({"shims": [_entry(extension_rationale="")]})

    def test_non_empty_extension_rationale_is_valid(self) -> None:
        validate_registry({"shims": [_entry(extension_rationale="External consumer SLA requires extra window")]})

    def test_non_string_notes_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="notes"):
            validate_registry({"shims": [_entry(notes=42)]})

    def test_string_notes_is_valid(self) -> None:
        validate_registry({"shims": [_entry(notes="Some context")]})

    def test_missing_optional_fields_is_valid(self) -> None:
        validate_registry({"shims": [_entry()]})


class TestAccumulatingErrors:
    def test_multiple_errors_reported_at_once(self) -> None:
        bad = {
            "legacy_path": "123bad",
            "canonical_import": 42,
            "introduced_in_release": "bad",
            "removal_target_release": "bad",
            "tracker_issue": "no",
            "grandfathered": "yes",
        }
        with pytest.raises(RegistrySchemaError) as exc_info:
            validate_registry({"shims": [bad]})
        errors = exc_info.value.errors
        assert len(errors) >= 4, f"Expected multiple errors, got {errors}"
