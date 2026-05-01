"""Schema validation for architecture/2.x/05_ownership_manifest.yaml.

Asserts structural completeness per data-model.md §4.
Runs in <1 s (NFR-002).
"""
import time
import warnings
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

MANIFEST_PATH = Path(__file__).parents[2] / "architecture" / "2.x" / "05_ownership_manifest.yaml"

REQUIRED_SLICE_KEYS = frozenset(
    {
        "cli_shell",
        "charter_governance",
        "doctrine",
        "runtime_mission_execution",
        "glossary",
        "lifecycle_status",
        "orchestrator_sync_tracker_saas",
        "migration_versioning",
    }
)

REQUIRED_ENTRY_FIELDS = frozenset(
    {
        "canonical_package",
        "current_state",
        "adapter_responsibilities",
        "shims",
        "seams",
        "extraction_sequencing_notes",
    }
)


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    """Load the manifest once for all tests in this module."""
    start = time.monotonic()
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST_PATH.read_text()))
    elapsed = time.monotonic() - start
    if elapsed > 1.0:
        warnings.warn(
            f"Manifest load took {elapsed:.2f}s (NFR-002 target: ≤1 s)",
            UserWarning,
            stacklevel=2,
        )
    return data


# Assertion 1 — manifest file exists and parses
def test_manifest_exists_and_parses(manifest: dict[str, Any]) -> None:
    assert isinstance(manifest, dict), "Manifest must be a YAML mapping at top level"


# Assertion 2 — exactly the 8 canonical slice keys
def test_manifest_has_exactly_eight_canonical_keys(manifest: dict[str, Any]) -> None:
    assert set(manifest.keys()) == REQUIRED_SLICE_KEYS


# Assertion 3 — each slice entry has all required fields with correct types
def test_each_slice_entry_has_required_fields(manifest: dict[str, Any]) -> None:
    for key, entry in manifest.items():
        for field in REQUIRED_ENTRY_FIELDS:
            assert field in entry, f"Slice '{key}' missing required field '{field}'"
        assert isinstance(entry["canonical_package"], str) and entry["canonical_package"], (
            f"Slice '{key}': canonical_package must be a non-empty string"
        )
        assert isinstance(entry["current_state"], list) and len(entry["current_state"]) > 0, (
            f"Slice '{key}': current_state must be a non-empty list"
        )
        assert isinstance(entry["adapter_responsibilities"], list), (
            f"Slice '{key}': adapter_responsibilities must be a list"
        )
        assert isinstance(entry["shims"], list), f"Slice '{key}': shims must be a list"
        assert isinstance(entry["seams"], list), f"Slice '{key}': seams must be a list"
        assert isinstance(entry["extraction_sequencing_notes"], str) and entry["extraction_sequencing_notes"], (
            f"Slice '{key}': extraction_sequencing_notes must be a non-empty string"
        )


# Assertion 4 — runtime slice has dependency_rules with both required sub-keys as lists
def test_runtime_slice_has_dependency_rules(manifest: dict[str, Any]) -> None:
    runtime = manifest["runtime_mission_execution"]
    assert "dependency_rules" in runtime, "runtime_mission_execution must have dependency_rules"
    dr = runtime["dependency_rules"]
    assert isinstance(dr, dict), "dependency_rules must be a mapping"
    assert "may_call" in dr and isinstance(dr["may_call"], list), (
        "dependency_rules.may_call must be a list"
    )
    assert "may_be_called_by" in dr and isinstance(dr["may_be_called_by"], list), (
        "dependency_rules.may_be_called_by must be a list"
    )


# Assertions 5+6 — dependency_rules on runtime only; no other slice has it
def test_only_runtime_slice_has_dependency_rules(manifest: dict[str, Any]) -> None:
    for key, entry in manifest.items():
        if key == "runtime_mission_execution":
            continue
        assert "dependency_rules" not in entry, (
            f"Slice '{key}' must not have dependency_rules (runtime-only field)"
        )


# Assertion 7 — charter_governance.shims is an empty list
def test_charter_governance_shims_is_empty(manifest: dict[str, Any]) -> None:
    charter = manifest["charter_governance"]
    assert charter["shims"] == [], (
        "charter_governance.shims must be [] (shim deleted by Mission functional-ownership-map-01KPDY72)"
    )


# Assertion 8 — dependency_rules references only known slice keys
def test_dependency_rules_reference_known_slice_keys(manifest: dict[str, Any]) -> None:
    dr = manifest["runtime_mission_execution"]["dependency_rules"]
    for direction in ("may_call", "may_be_called_by"):
        for ref in dr[direction]:
            assert ref in REQUIRED_SLICE_KEYS, (
                f"dependency_rules.{direction} contains unknown slice key '{ref}'"
            )


# Assertion 6 — every shims[].path that is non-empty exists on disk
def test_shim_paths_exist_if_listed(manifest: dict[str, Any]) -> None:
    """Every shim path listed in the manifest must exist on disk (data-model §4 assertion 6)."""
    repo_root = Path(__file__).parents[2]
    for key, entry in manifest.items():
        for shim in entry.get("shims", []):
            path_str = shim.get("path", "")
            if path_str:
                assert (repo_root / path_str).exists(), (
                    f"Slice '{key}' shim path '{path_str}' does not exist in repo. "
                    "Either the shim was deleted without updating the manifest, "
                    "or the manifest lists a path that was never created."
                )


# Assertion 9 — validation completes within 1 s (soft)
def test_validation_completes_within_one_second() -> None:
    """Soft timing check — emits a warning but does not fail if >1 s (NFR-002)."""
    start = time.monotonic()
    data = cast(dict[str, Any], yaml.safe_load(MANIFEST_PATH.read_text()))
    assert set(data.keys()) == REQUIRED_SLICE_KEYS
    elapsed = time.monotonic() - start
    if elapsed > 1.0:
        warnings.warn(
            f"Manifest validation took {elapsed:.2f}s; NFR-002 target is ≤1 s on a baseline dev machine.",
            UserWarning,
            stacklevel=2,
        )
