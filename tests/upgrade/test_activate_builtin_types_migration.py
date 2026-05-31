"""Tests for m_3_2_7_activate_builtin_mission_types migration (WP12 / FR-019).

Covers:
* Migration on project without mission_type_activations — adds all four built-ins.
* Migration on project with existing entries — idempotent (no change).
* Existing config sections (agents, org_packs) are preserved.
* Dry-run mode — reports changes but does not write to disk.
* No config.yaml present — gracefully returns success with a note.
* YAML formatting preserved — ruamel.yaml round-trip retains comments.
* detect() returns True only when migration is needed.
* can_apply() returns False when config path is not a file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

from specify_cli.upgrade.migrations.m_3_2_7_activate_builtin_mission_types import (
    ActivateBuiltinMissionTypesMigration,
    _BUILTIN_MISSION_TYPES,
)


@pytest.fixture
def migration() -> ActivateBuiltinMissionTypesMigration:
    return ActivateBuiltinMissionTypesMigration()


def _write_config(tmp_path: Path, content: str) -> Path:
    """Create .kittify/config.yaml with the given content and return the path."""
    config_dir = tmp_path / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


# ---------------------------------------------------------------------------
# detect()
# ---------------------------------------------------------------------------


def test_detect_returns_true_when_key_absent(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    _write_config(tmp_path, "agents:\n  available:\n    - claude\n")
    assert migration.detect(tmp_path) is True


def test_detect_returns_true_when_key_empty_list(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    _write_config(tmp_path, "mission_type_activations: []\n")
    assert migration.detect(tmp_path) is True


def test_detect_returns_false_when_key_present(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    _write_config(
        tmp_path,
        "mission_type_activations:\n  - software-dev\n",
    )
    assert migration.detect(tmp_path) is False


def test_detect_returns_false_when_no_config(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    assert migration.detect(tmp_path) is False


# ---------------------------------------------------------------------------
# can_apply()
# ---------------------------------------------------------------------------


def test_can_apply_no_config(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    ok, reason = migration.can_apply(tmp_path)
    assert ok is True
    assert reason == ""


def test_can_apply_valid_config(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    _write_config(tmp_path, "agents:\n  available:\n    - claude\n")
    ok, reason = migration.can_apply(tmp_path)
    assert ok is True
    assert reason == ""


def test_can_apply_returns_false_when_path_is_directory(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    config_dir = tmp_path / ".kittify"
    config_dir.mkdir(parents=True)
    # Create config.yaml as a directory (edge case)
    (config_dir / "config.yaml").mkdir()
    ok, reason = migration.can_apply(tmp_path)
    assert ok is False
    assert "not a file" in reason


# ---------------------------------------------------------------------------
# apply(): project without mission_type_activations
# ---------------------------------------------------------------------------


def test_apply_adds_all_four_builtins(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """Migration adds all four built-in mission types when key is absent."""
    config_file = _write_config(
        tmp_path, "agents:\n  available:\n    - claude\n"
    )

    result = migration.apply(tmp_path)

    assert result.success
    assert len(result.errors) == 0
    assert any("Added" in c for c in result.changes_made)

    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    data = yaml.load(config_file.read_text()) or {}
    assert "mission_type_activations" in data
    written = data["mission_type_activations"]
    assert sorted(written) == sorted(_BUILTIN_MISSION_TYPES)


def test_apply_adds_all_four_builtins_minimal_config(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """Works on a minimal config.yaml with no pre-existing sections."""
    config_file = _write_config(tmp_path, "{}\n")
    result = migration.apply(tmp_path)
    assert result.success

    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    data = yaml.load(config_file.read_text()) or {}
    assert set(data["mission_type_activations"]) == set(_BUILTIN_MISSION_TYPES)


# ---------------------------------------------------------------------------
# apply(): idempotency
# ---------------------------------------------------------------------------


def test_apply_idempotent_when_entries_already_present(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """Migration is a no-op when mission_type_activations already has entries."""
    original = "mission_type_activations:\n  - software-dev\n"
    config_file = _write_config(tmp_path, original)

    result = migration.apply(tmp_path)

    assert result.success
    # Content must not have changed
    assert config_file.read_text(encoding="utf-8") == original


def test_apply_idempotent_preserves_partial_custom_list(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """A user-curated list (e.g., only software-dev) is never modified."""
    original = "mission_type_activations:\n  - software-dev\n  - research\n"
    config_file = _write_config(tmp_path, original)

    migration.apply(tmp_path)

    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    data = yaml.load(config_file.read_text()) or {}
    assert sorted(data["mission_type_activations"]) == sorted(
        ["software-dev", "research"]
    )


# ---------------------------------------------------------------------------
# apply(): existing config preserved
# ---------------------------------------------------------------------------


def test_apply_preserves_agents_section(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """Other config sections are untouched after migration."""
    config_file = _write_config(
        tmp_path,
        (
            "agents:\n"
            "  available:\n"
            "    - claude\n"
            "    - opencode\n"
            "  auto_commit: true\n"
            "org_packs:\n"
            "  - my-pack\n"
        ),
    )

    migration.apply(tmp_path)

    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    data = yaml.load(config_file.read_text()) or {}
    assert "agents" in data
    assert data["agents"]["available"] == ["claude", "opencode"]
    assert data["agents"]["auto_commit"] is True
    assert data["org_packs"] == ["my-pack"]
    assert "mission_type_activations" in data


# ---------------------------------------------------------------------------
# apply(): dry-run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """Dry-run returns success and changes but does not write to disk."""
    original = "agents:\n  available:\n    - claude\n"
    config_file = _write_config(tmp_path, original)

    result = migration.apply(tmp_path, dry_run=True)

    assert result.success
    assert any("Would add" in c for c in result.changes_made)
    # File must be untouched
    assert config_file.read_text(encoding="utf-8") == original


def test_dry_run_idempotent_when_already_present(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """Dry-run is a no-op (and succeeds) when key already exists."""
    original = "mission_type_activations:\n  - software-dev\n"
    config_file = _write_config(tmp_path, original)

    result = migration.apply(tmp_path, dry_run=True)

    assert result.success
    assert config_file.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# apply(): no config.yaml
# ---------------------------------------------------------------------------


def test_apply_no_config_returns_success(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """Gracefully handles a project with no config.yaml."""
    result = migration.apply(tmp_path)
    assert result.success
    assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# YAML formatting preserved
# ---------------------------------------------------------------------------


def test_ruamel_roundtrip_preserves_comments(
    tmp_path: Path, migration: ActivateBuiltinMissionTypesMigration
) -> None:
    """ruamel.yaml round-trip should not destroy inline comments."""
    config_with_comment = (
        "# Main config\n"
        "agents:\n"
        "  available:\n"
        "    - claude  # primary agent\n"
    )
    config_file = _write_config(tmp_path, config_with_comment)

    migration.apply(tmp_path)

    content_after = config_file.read_text(encoding="utf-8")
    # The comment on the 'agents' line should survive the round-trip
    assert "# Main config" in content_after
    assert "primary agent" in content_after


# ---------------------------------------------------------------------------
# Built-in list consistency sanity check
# ---------------------------------------------------------------------------


def test_builtin_types_contains_expected_ids() -> None:
    """_BUILTIN_MISSION_TYPES must contain the four canonical built-in IDs."""
    assert set(_BUILTIN_MISSION_TYPES) == {
        "software-dev",
        "documentation",
        "research",
        "plan",
    }
