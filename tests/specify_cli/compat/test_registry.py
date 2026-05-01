"""Unit tests for specify_cli.compat.registry — load_registry() and ShimEntry."""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from specify_cli.compat.registry import (
    _validate_canonical_import,
    _validate_entry,
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

    def test_extra_unknown_keys_raise_on_load(self, tmp_path: Path) -> None:
        entry = {**_VALID_ENTRY, "future_field": "preserve-compat"}
        root = _write_registry(tmp_path, {"shims": [entry]})
        with pytest.raises(RegistrySchemaError, match="future_field"):
            load_registry(root)


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

    def test_extra_unknown_keys_raise_schema_error(self) -> None:
        """Unknown keys are rejected — only the declared ShimEntry fields are allowed."""
        entry = {**_VALID_ENTRY, "unknown_future_field": "some_value"}
        with pytest.raises(RegistrySchemaError, match="unknown_future_field"):
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
        entries = [{**_VALID_ENTRY, "legacy_path": f"module.sub_{i}"} for i in range(50)]
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


# ---------------------------------------------------------------------------
# Mutation-aware kills for 2026-04-20 survivors (WP01, FR-001).
#
# Each class below targets the survivor set from
# docs/development/mutation-testing-findings.md, applying the patterns
# documented in src/doctrine/styleguides/shipped/mutation-aware-test-design.
# Patterns cited in the docstring; specific mutant IDs cited per test.
# ---------------------------------------------------------------------------


class TestValidateEntryMutationKills:
    """Kill _validate_entry survivors: mutants 7, 8, 16, 34, 36, 53, 54.

    The common pattern is ``None``-substitution on positional args to helper
    validators and on error-string payloads. Kill strategy: assert on exact
    error-message shape (index + field + reason) so the mutated call paths
    produce observably different output.
    """

    def test_missing_field_error_contains_field_name_not_none(self) -> None:
        """Kills mutant 7: errors.append(None) replacing the missing-field message."""
        errors: list[str] = []
        # Missing: grandfathered. Other required fields present.
        entry = {k: v for k, v in _VALID_ENTRY.items() if k != "grandfathered"}
        _validate_entry(0, entry, set(), errors)
        # If mutant 7 ran, errors would contain None (or f"entry[{i}].{key}" replaced by None).
        assert all(isinstance(e, str) for e in errors)
        assert any("grandfathered" in e and "required field is missing" in e for e in errors)

    def test_invalid_legacy_path_error_contains_entry_index(self) -> None:
        """Kills mutant 8: _validate_legacy_path(None, ...) masks the entry index."""
        errors: list[str] = []
        entry = dict(_VALID_ENTRY, legacy_path="123-not-a-dotted-name")
        _validate_entry(7, entry, set(), errors)
        # Index 7 must appear — not entry[None]
        assert any("entry[7]" in e and "legacy_path" in e for e in errors)
        assert not any("entry[None]" in e for e in errors)

    def test_invalid_canonical_import_error_contains_entry_index(self) -> None:
        """Kills mutant 16: _validate_canonical_import(None, ...) masks the entry index."""
        errors: list[str] = []
        entry = dict(_VALID_ENTRY, canonical_import=42)
        _validate_entry(3, entry, set(), errors)
        assert any("entry[3]" in e and "canonical_import" in e for e in errors)
        assert not any("entry[None]" in e for e in errors)

    def test_invalid_version_order_error_contains_entry_index(self) -> None:
        """Kills mutant 34: _validate_version_order(None, ...) masks the entry index."""
        errors: list[str] = []
        entry = dict(
            _VALID_ENTRY,
            introduced_in_release="3.3.0",
            removal_target_release="3.2.0",
        )
        _validate_entry(5, entry, set(), errors)
        assert any("entry[5]" in e and "removal_target_release" in e for e in errors)
        assert not any("entry[None]" in e for e in errors)

    def test_invalid_version_order_appends_to_caller_errors(self) -> None:
        """Kills mutant 36: _validate_version_order(i, entry, None) swallows the error.

        Original behaviour: version-order error is appended to the caller's errors list.
        Mutant: called with None, which would AttributeError on .append. Raising would
        be visible; silent pass means the mutant accidentally succeeded. Regardless,
        the caller's errors list must receive the version-order message.
        """
        errors: list[str] = []
        entry = dict(
            _VALID_ENTRY,
            introduced_in_release="3.3.0",
            removal_target_release="3.2.0",
        )
        _validate_entry(0, entry, set(), errors)
        assert any(">= introduced_in_release" in e for e in errors), "version-order error did not reach caller's errors list"

    def test_non_bool_grandfathered_error_reports_actual_type(self) -> None:
        """Kills mutant 53: type(gf).__name__ → type(None).__name__.

        Boundary Pair pattern: assert the error message names the actual offending
        type ("str"), not "NoneType" from the mutation.
        """
        errors: list[str] = []
        entry = dict(_VALID_ENTRY, grandfathered="yes")
        _validate_entry(0, entry, set(), errors)
        assert any("grandfathered" in e and "str" in e for e in errors)
        assert not any("NoneType" in e for e in errors)

    def test_invalid_optional_field_error_contains_entry_index(self) -> None:
        """Kills mutant 54: _validate_optional_fields(None, ...) masks the entry index."""
        errors: list[str] = []
        entry = dict(_VALID_ENTRY, extension_rationale="   ")  # whitespace-only
        _validate_entry(9, entry, set(), errors)
        assert any("entry[9]" in e and "extension_rationale" in e for e in errors)
        assert not any("entry[None]" in e for e in errors)


class TestValidateCanonicalImportMutationKills:
    """Kill _validate_canonical_import survivors: mutants 7–12.

    Pattern mix: Non-Identity Inputs (valid vs invalid items), exact message
    assertions (replaces None-substitution on error strings), and Boundary Pair
    on the list-vs-scalar discriminator.
    """

    def test_valid_list_of_dotted_names_produces_no_error(self) -> None:
        """Kills mutants 8 (truthy inversion), 9 (regex negation removed), 10 (match(None)).

        Non-Identity Inputs: a list of VALID dotted names must produce zero errors.
        Mutants flip the validation polarity so that valid inputs incorrectly
        trigger errors; the bare match(None) mutant crashes on the first item.
        """
        errors: list[str] = []
        _validate_canonical_import(0, ["module.a", "module.b", "module.c"], errors)
        assert errors == []

    def test_valid_single_string_produces_no_error(self) -> None:
        """Reinforcement for the scalar path."""
        errors: list[str] = []
        _validate_canonical_import(0, "module.submodule.Class", errors)
        assert errors == []

    def test_list_item_error_message_names_the_field_and_index(self) -> None:
        """Kills mutant 11: errors.append(None) on per-list-item error.

        Exact-shape assertion: the error string must name both the entry index,
        the sub-index, and the "dotted identifier" descriptor.
        """
        errors: list[str] = []
        _validate_canonical_import(2, ["valid.module", "123-bad"], errors)
        assert len(errors) == 1
        assert isinstance(errors[0], str)
        assert "entry[2].canonical_import[1]" in errors[0]
        assert "dotted identifier" in errors[0]

    def test_non_str_non_list_input_error_message_names_the_field(self) -> None:
        """Kills mutant 12: errors.append(None) on else-branch.

        Bi-Directional Logic on the outer discriminator: cover the non-str,
        non-list branch explicitly with a dict input. Exact-shape assertion.
        """
        errors: list[str] = []
        _validate_canonical_import(4, {"not": "a string or list"}, errors)
        assert len(errors) == 1
        assert isinstance(errors[0], str)
        assert "entry[4].canonical_import" in errors[0]
        assert "string or list of strings" in errors[0]

    def test_integer_input_produces_specific_error(self) -> None:
        """Secondary kill for mutant 12 using a different non-str non-list type."""
        errors: list[str] = []
        _validate_canonical_import(0, 42, errors)
        assert len(errors) == 1
        assert "string or list of strings" in errors[0]


class TestValidateVersionOrderMutationKills:
    """Kill _validate_version_order survivors: mutants 10, 12.

    Bi-Directional Logic: mutants flip ``and`` → ``or`` in defensive type/format
    guards. Test with MIXED inputs (one valid, one invalid) where the truthy
    polarity of AND vs OR diverges.
    """

    def test_one_field_str_one_not_returns_silently(self) -> None:
        """Kills mutant 10: ``isinstance(introduced, str) and isinstance(removal, str)``
        → ``or``. When only introduced is a string, the mutant proceeds to call
        ``_SEMVER.match(None)`` which raises ``TypeError``; the original short-circuits.
        """
        errors: list[str] = []
        _validate_version_order(
            0,
            {"introduced_in_release": "3.2.0", "removal_target_release": None},
            errors,
        )
        assert errors == []

    def test_both_fields_non_str_returns_silently(self) -> None:
        """Original: ``not(False and False)`` = True → return.
        Mutant: ``not(False or False)`` = True → return. Same behaviour.
        Keep this test for defensive coverage; not a direct kill but adjacent."""
        errors: list[str] = []
        _validate_version_order(
            0,
            {"introduced_in_release": 42, "removal_target_release": None},
            errors,
        )
        assert errors == []

    def test_one_semver_one_non_semver_string_returns_silently(self) -> None:
        """Kills mutant 12: ``_SEMVER.match(introduced) and _SEMVER.match(removal)``
        → ``or``. With only one matching, original returns silently; mutant proceeds
        to Version() which raises InvalidVersion, caught and appended as an error.
        """
        errors: list[str] = []
        _validate_version_order(
            0,
            {"introduced_in_release": "1.0.0", "removal_target_release": "not-semver"},
            errors,
        )
        # Original returns silently because the format check filters out non-SEMVER.
        # If the mutant were live, Version("not-semver") would raise InvalidVersion
        # → error appended.
        assert errors == []


class TestValidateRegistryMessageKills:
    """Kill validate_registry survivors: mutants 7, 11.

    Pattern: exact-string assertions on error messages replace the "XX-prefixed"
    placeholder mutations.
    """

    def test_top_level_non_mapping_exact_error_message(self) -> None:
        """Kills mutant 7: error string wrapped in ``XX...XX`` sentinels."""
        with pytest.raises(RegistrySchemaError) as exc_info:
            validate_registry("not a mapping")
        errors = exc_info.value.errors
        assert errors == ["top-level: must be a mapping with a 'shims' key"]

    def test_missing_shims_key_exact_error_message(self) -> None:
        """Kills mutant 7 via the alternate branch (dict without shims key)."""
        with pytest.raises(RegistrySchemaError) as exc_info:
            validate_registry({"other_key": []})
        errors = exc_info.value.errors
        assert errors == ["top-level: must be a mapping with a 'shims' key"]

    def test_shims_non_list_exact_error_message(self) -> None:
        """Kills mutant 11: error string wrapped in ``XX...XX`` sentinels."""
        with pytest.raises(RegistrySchemaError) as exc_info:
            validate_registry({"shims": "not a list"})
        errors = exc_info.value.errors
        assert errors == ["top-level.shims: must be a list"]


class TestRegistrySchemaErrorMessageKills:
    """Kill RegistrySchemaError.__init__ survivor: mutant 4.

    Pattern: exact assertion on the separator inserted by ``"\\n".join(errors)``.
    Mutant replaces the separator with ``"XX\\nXX"`` — kill by asserting the
    exact string form of the rendered message.
    """

    def test_str_uses_single_newline_separator(self) -> None:
        exc = RegistrySchemaError(["first error", "second error"])
        assert str(exc) == "first error\nsecond error"

    def test_str_does_not_contain_sentinel_markers(self) -> None:
        exc = RegistrySchemaError(["a", "b"])
        assert "XX" not in str(exc)

    def test_single_error_has_no_separator(self) -> None:
        exc = RegistrySchemaError(["only one"])
        assert str(exc) == "only one"


# ---------------------------------------------------------------------------
# Residual — not killed in WP01 (documented under:
# docs/development/mutation-testing-findings.md → WP01 residuals).
#
# * specify_cli.compat.registry.x__validate_canonical_import__mutmut_7
#     empty/unloadable mutant (mutmut ``find_mutant`` fails)
# * specify_cli.compat.registry.x_validate_registry__mutmut_18
#     empty/unloadable mutant (mutmut ``find_mutant`` fails)
# * specify_cli.compat.registry.x_load_registry__mutmut_14
#     functionally equivalent: YAML(typ="safe") vs YAML(typ=None) produce
#     identical observable output for our shim-registry input shape (plain
#     dict/list of strings/bools; no tags, no dates, no preserved formatting).
#     The safety guarantee is preserved by ruamel's tag-rejection policy in
#     both loaders. Kill would require an unsafe-tag test that neither loader
#     accepts — moot.
# ---------------------------------------------------------------------------
