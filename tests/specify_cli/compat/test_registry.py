"""Unit tests for specify_cli.compat.registry — load_registry() and ShimEntry."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from specify_cli.compat.registry import (
    _validate_canonical_import,
    _validate_version_order,
    RegistrySchemaError,
    ShimEntry,
    load_registry,
    validate_registry,
)

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ENTRY: dict[str, object] = {
    "legacy_path": "specify_cli.old_module",
    "canonical_import": "new_module",
    "introduced_in_release": "3.2.0",
    "removal_target_release": "3.3.0",
    "tracker_issue": "#615",
    "grandfathered": False,
}


def _write_registry(tmp_path: Path, payload: object) -> Path:
    """Write payload as YAML to the canonical shim-registry location."""
    registry_dir = tmp_path / "architecture" / "2.x"
    registry_dir.mkdir(parents=True)
    registry_path = registry_dir / "shim-registry.yaml"
    yaml = YAML()
    with registry_path.open("w") as fp:
        yaml.dump(payload, fp)
    return tmp_path


def _write_raw_registry(tmp_path: Path, content: str) -> Path:
    """Write raw string content to the canonical shim-registry path."""
    registry_dir = tmp_path / "architecture" / "2.x"
    registry_dir.mkdir(parents=True)
    (registry_dir / "shim-registry.yaml").write_text(content)
    return tmp_path


# ---------------------------------------------------------------------------
# ShimEntry dataclass
# ---------------------------------------------------------------------------


class TestShimEntry:
    def test_required_fields_only(self) -> None:
        entry = ShimEntry(
            legacy_path="specify_cli.old",
            canonical_import="specify_cli.new",
            introduced_in_release="3.2.0",
            removal_target_release="3.3.0",
            tracker_issue="#1",
            grandfathered=False,
        )
        assert entry.extension_rationale is None
        assert entry.notes is None

    def test_all_fields(self) -> None:
        entry = ShimEntry(
            legacy_path="specify_cli.old",
            canonical_import=["specify_cli.new_a", "specify_cli.new_b"],
            introduced_in_release="3.2.0",
            removal_target_release="3.3.0",
            tracker_issue="https://github.com/org/repo/issues/1",
            grandfathered=True,
            extension_rationale="SLA constraint",
            notes="Some context",
        )
        assert entry.grandfathered is True
        assert isinstance(entry.canonical_import, list)
        assert len(entry.canonical_import) == 2

    def test_frozen_raises_on_mutation(self) -> None:
        entry = ShimEntry(
            legacy_path="specify_cli.old",
            canonical_import="specify_cli.new",
            introduced_in_release="3.2.0",
            removal_target_release="3.3.0",
            tracker_issue="#1",
            grandfathered=False,
        )
        with pytest.raises((AttributeError, TypeError)):
            entry.grandfathered = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# load_registry() — happy paths
# ---------------------------------------------------------------------------


class TestLoadRegistryHappyPath:
    def test_empty_registry_returns_empty_list(self, tmp_path: Path) -> None:
        root = _write_registry(tmp_path, {"shims": []})
        result = load_registry(root)
        assert result == []

    def test_single_entry_returns_one_shim_entry(self, tmp_path: Path) -> None:
        root = _write_registry(tmp_path, {"shims": [_VALID_ENTRY]})
        result = load_registry(root)
        assert len(result) == 1
        assert isinstance(result[0], ShimEntry)
        assert result[0].legacy_path == "specify_cli.old_module"
        assert result[0].canonical_import == "new_module"
        assert result[0].grandfathered is False

    def test_multiple_entries_returned_in_order(self, tmp_path: Path) -> None:
        entries = [
            {**_VALID_ENTRY, "legacy_path": "a.b.c"},
            {**_VALID_ENTRY, "legacy_path": "x.y.z"},
        ]
        root = _write_registry(tmp_path, {"shims": entries})
        result = load_registry(root)
        assert len(result) == 2
        assert result[0].legacy_path == "a.b.c"
        assert result[1].legacy_path == "x.y.z"

    def test_list_canonical_import_preserved(self, tmp_path: Path) -> None:
        entry = {**_VALID_ENTRY, "canonical_import": ["mod.a", "mod.b"]}
        root = _write_registry(tmp_path, {"shims": [entry]})
        result = load_registry(root)
        assert result[0].canonical_import == ["mod.a", "mod.b"]

    def test_optional_fields_set_when_present(self, tmp_path: Path) -> None:
        entry = {
            **_VALID_ENTRY,
            "extension_rationale": "Needed for SLA",
            "notes": "Extra context",
        }
        root = _write_registry(tmp_path, {"shims": [entry]})
        result = load_registry(root)
        assert result[0].extension_rationale == "Needed for SLA"
        assert result[0].notes == "Extra context"

    def test_optional_fields_default_to_none_when_absent(self, tmp_path: Path) -> None:
        root = _write_registry(tmp_path, {"shims": [_VALID_ENTRY]})
        result = load_registry(root)
        assert result[0].extension_rationale is None
        assert result[0].notes is None

    def test_grandfathered_true_preserved(self, tmp_path: Path) -> None:
        entry = {**_VALID_ENTRY, "grandfathered": True}
        root = _write_registry(tmp_path, {"shims": [entry]})
        result = load_registry(root)
        assert result[0].grandfathered is True


# ---------------------------------------------------------------------------
# load_registry() — missing file
# ---------------------------------------------------------------------------


class TestLoadRegistryMissingFile:
    def test_missing_registry_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="shim-registry"):
            load_registry(tmp_path)

    def test_error_message_contains_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError) as exc_info:
            load_registry(tmp_path)
        assert "shim-registry.yaml" in str(exc_info.value)

    def test_missing_architecture_dir_raises(self, tmp_path: Path) -> None:
        # No architecture/ directory at all
        with pytest.raises(FileNotFoundError):
            load_registry(tmp_path)


# ---------------------------------------------------------------------------
# load_registry() — malformed YAML → RegistrySchemaError
# ---------------------------------------------------------------------------


class TestLoadRegistryMalformedYaml:
    def test_invalid_yaml_raises_registry_schema_error(self, tmp_path: Path) -> None:
        # Deliberately broken YAML: unclosed bracket
        root = _write_raw_registry(tmp_path, "shims: [\n  {legacy_path: foo\n")
        with pytest.raises(RegistrySchemaError, match="YAML parse error"):
            load_registry(root)

    def test_yaml_error_is_chained(self, tmp_path: Path) -> None:
        root = _write_raw_registry(tmp_path, "shims: [\n  {bad: yaml:")
        with pytest.raises(RegistrySchemaError) as exc_info:
            load_registry(root)
        assert exc_info.value.__cause__ is not None

    def test_errors_list_contains_yaml_error_message(self, tmp_path: Path) -> None:
        root = _write_raw_registry(tmp_path, "shims: [\n  {unclosed:")
        with pytest.raises(RegistrySchemaError) as exc_info:
            load_registry(root)
        assert any("YAML" in e for e in exc_info.value.errors)

    def test_binary_junk_raises_registry_schema_error(self, tmp_path: Path) -> None:
        registry_dir = tmp_path / "architecture" / "2.x"
        registry_dir.mkdir(parents=True)
        (registry_dir / "shim-registry.yaml").write_bytes(b"\xff\xfe" + b"\x00" * 20)
        with pytest.raises((RegistrySchemaError, UnicodeDecodeError)):
            load_registry(tmp_path)


# ---------------------------------------------------------------------------
# load_registry() — schema validation errors propagate
# ---------------------------------------------------------------------------


class TestLoadRegistrySchemaErrors:
    def test_missing_required_field_raises_schema_error(self, tmp_path: Path) -> None:
        bad = {k: v for k, v in _VALID_ENTRY.items() if k != "grandfathered"}
        root = _write_registry(tmp_path, {"shims": [bad]})
        with pytest.raises(RegistrySchemaError) as exc_info:
            load_registry(root)
        assert "grandfathered" in "\n".join(exc_info.value.errors)

    def test_duplicate_legacy_path_raises_schema_error(self, tmp_path: Path) -> None:
        root = _write_registry(tmp_path, {"shims": [_VALID_ENTRY, _VALID_ENTRY]})
        with pytest.raises(RegistrySchemaError, match="legacy_path"):
            load_registry(root)

    def test_invalid_semver_raises_schema_error(self, tmp_path: Path) -> None:
        entry = {**_VALID_ENTRY, "introduced_in_release": "not-a-version"}
        root = _write_registry(tmp_path, {"shims": [entry]})
        with pytest.raises(RegistrySchemaError):
            load_registry(root)

    def test_wrong_top_level_structure_raises(self, tmp_path: Path) -> None:
        root = _write_registry(tmp_path, ["not", "a", "dict"])
        with pytest.raises(RegistrySchemaError, match="top-level"):
            load_registry(root)

    def test_empty_file_raises_schema_error(self, tmp_path: Path) -> None:
        root = _write_raw_registry(tmp_path, "")
        with pytest.raises(RegistrySchemaError):
            load_registry(root)


# ---------------------------------------------------------------------------
# RegistrySchemaError
# ---------------------------------------------------------------------------


class TestRegistrySchemaError:
    def test_errors_attribute_preserved(self) -> None:
        exc = RegistrySchemaError(["err1", "err2"])
        assert exc.errors == ["err1", "err2"]

    def test_str_contains_all_errors(self) -> None:
        exc = RegistrySchemaError(["error A", "error B"])
        assert "error A" in str(exc)
        assert "error B" in str(exc)

    def test_single_error_preserved(self) -> None:
        exc = RegistrySchemaError(["only error"])
        assert exc.errors == ["only error"]


# ---------------------------------------------------------------------------
# Adversarial inputs to validate_registry
# ---------------------------------------------------------------------------


class TestAdversarialValidation:
    def test_entry_as_none_raises(self) -> None:
        with pytest.raises(RegistrySchemaError):
            validate_registry({"shims": [None]})

    def test_entry_as_integer_raises(self) -> None:
        with pytest.raises(RegistrySchemaError):
            validate_registry({"shims": [42]})

    def test_entry_as_list_raises(self) -> None:
        with pytest.raises(RegistrySchemaError):
            validate_registry({"shims": [["a", "b"]]})

    def test_all_wrong_types_accumulates_errors(self) -> None:
        """All wrong-type fields → multiple errors reported in one raise."""
        bad = {
            "legacy_path": 123,
            "canonical_import": None,
            "introduced_in_release": True,
            "removal_target_release": [],
            "tracker_issue": 0,
            "grandfathered": "maybe",
        }
        with pytest.raises(RegistrySchemaError) as exc_info:
            validate_registry({"shims": [bad]})
        assert len(exc_info.value.errors) >= 5

    def test_extra_unknown_keys_are_tolerated(self) -> None:
        """Unknown keys do not cause validation failure — only missing required keys matter."""
        entry = {**_VALID_ENTRY, "unknown_future_field": "some_value"}
        validate_registry({"shims": [entry]})

    def test_whitespace_only_extension_rationale_raises(self) -> None:
        with pytest.raises(RegistrySchemaError, match="extension_rationale"):
            validate_registry({"shims": [dict(_VALID_ENTRY, extension_rationale="   ")]})

    def test_http_tracker_url_is_valid(self) -> None:
        entry = {**_VALID_ENTRY, "tracker_issue": "http://jira.example.com/PROJ-42"}
        validate_registry({"shims": [entry]})

    def test_canonical_import_list_with_invalid_item_raises(self) -> None:
        entry = {**_VALID_ENTRY, "canonical_import": ["valid.module", "123-invalid"]}
        with pytest.raises(RegistrySchemaError, match="canonical_import"):
            validate_registry({"shims": [entry]})

    def test_very_long_dotted_path_is_valid(self) -> None:
        long_path = ".".join(["a"] * 20)
        entry = {**_VALID_ENTRY, "legacy_path": long_path}
        validate_registry({"shims": [entry]})

    def test_three_digit_tracker_issue_is_valid(self) -> None:
        entry = {**_VALID_ENTRY, "tracker_issue": "#999"}
        validate_registry({"shims": [entry]})

    def test_many_entries_unique_paths(self) -> None:
        entries = [
            {**_VALID_ENTRY, "legacy_path": f"module.sub_{i}"}
            for i in range(50)
        ]
        validate_registry({"shims": entries})


# ---------------------------------------------------------------------------
# _validate_canonical_import — branch coverage for line 63, 66
# ---------------------------------------------------------------------------


class TestValidateCanonicalImport:
    def test_string_failing_dotted_name_regex_emits_error(self) -> None:
        errors: list[str] = []
        _validate_canonical_import(0, "123-not-a-dotted-name", errors)
        assert len(errors) == 1
        assert "canonical_import" in errors[0]
        assert "dotted identifier" in errors[0]

    def test_empty_list_emits_error(self) -> None:
        errors: list[str] = []
        _validate_canonical_import(0, [], errors)
        assert len(errors) == 1
        assert "list must not be empty" in errors[0]

    def test_empty_list_does_not_iterate(self) -> None:
        errors: list[str] = []
        _validate_canonical_import(0, [], errors)
        assert len(errors) == 1  # only the empty-list error, no per-item errors


# ---------------------------------------------------------------------------
# _validate_version_order — branch coverage for lines 83-85
# ---------------------------------------------------------------------------


class TestValidateVersionOrder:
    def test_removal_before_introduced_emits_error(self) -> None:
        errors: list[str] = []
        entry = {"introduced_in_release": "3.3.0", "removal_target_release": "3.2.0"}
        _validate_version_order(0, entry, errors)
        assert len(errors) == 1
        assert "removal_target_release" in errors[0]
        assert ">= introduced_in_release" in errors[0]

    def test_invalid_version_string_emits_error(self) -> None:
        # "1.2.3z1" passes _SEMVER (any [a-z] letter) but is not valid PEP 440
        errors: list[str] = []
        entry = {"introduced_in_release": "1.2.3z1", "removal_target_release": "1.2.3z2"}
        _validate_version_order(0, entry, errors)
        assert len(errors) == 1
        assert "not valid semver" in errors[0]

    def test_equal_versions_are_valid(self) -> None:
        errors: list[str] = []
        entry = {"introduced_in_release": "3.2.0", "removal_target_release": "3.2.0"}
        _validate_version_order(0, entry, errors)
        assert errors == []


# ---------------------------------------------------------------------------
# validate_registry — branch coverage for lines 130, 137
# ---------------------------------------------------------------------------


class TestValidateRegistryBranches:
    def test_notes_as_integer_raises_schema_error(self) -> None:
        entry = {**_VALID_ENTRY, "notes": 42}
        with pytest.raises(RegistrySchemaError, match="notes"):
            validate_registry({"shims": [entry]})

    def test_shims_not_a_list_raises_schema_error(self) -> None:
        with pytest.raises(RegistrySchemaError, match="top-level.shims"):
            validate_registry({"shims": "not-a-list"})
