"""Unit tests for ``charter.pack_manager`` (WP04, T019).

Covers:
- ``YAML_KEY_MAP``: entry count, mission-type outlier, value naming conventions
- ``activate()``: None-state materialisation, existing-set append, no-duplicate,
  comment preservation, invalid-kind ValueError
- ``deactivate()``: None-state exit-1 with upgrade guidance, remove from list,
  warn-when-absent, invalid-kind ValueError
- ``list_activated()``: None-state returns None per kind, populated returns frozenset
- ``merge_defaults()``: writes absent keys, preserves present keys, backup on charter
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from charter.invocation_context import ProjectContext
from charter.pack_manager import (
    CharterPackManager,
    YAML_KEY_MAP,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a minimal .kittify/ directory with an empty config.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("# empty config\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def ctx(project_root: Path) -> ProjectContext:
    """ProjectContext built from the minimal project root."""
    return ProjectContext.from_repo(project_root)


@pytest.fixture()
def manager() -> CharterPackManager:
    return CharterPackManager()


# ---------------------------------------------------------------------------
# TestYamlKeyMap
# ---------------------------------------------------------------------------


class TestYamlKeyMap:
    def test_has_exactly_nine_entries(self) -> None:
        assert len(YAML_KEY_MAP) == 9

    def test_mission_type_maps_to_correct_key(self) -> None:
        assert YAML_KEY_MAP["mission-type"] == "mission_type_activations"

    def test_directive_maps_to_activated_directives(self) -> None:
        assert YAML_KEY_MAP["directive"] == "activated_directives"

    def test_all_values_start_with_activated_or_mission(self) -> None:
        for kind, yaml_key in YAML_KEY_MAP.items():
            assert yaml_key.startswith("activated_") or yaml_key == "mission_type_activations", f"Key '{kind}' maps to unexpected yaml_key '{yaml_key}'"


# ---------------------------------------------------------------------------
# TestActivateNoneState
# ---------------------------------------------------------------------------


class TestActivateNoneState:
    def test_activates_new_artifact_from_empty_config(self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path) -> None:
        """Activating on a fresh config materializes the default pack then adds the ID."""
        result = manager.activate(
            ctx,
            kind="directive",
            artifact_id="001-architectural-integrity-standard",
        )
        assert any("already activated" in w for w in result.warnings)
        # config.yaml must now contain the key
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "001-architectural-integrity-standard" in data["activated_directives"]

    def test_warns_about_initialization_from_default(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        result = manager.activate(
            ctx,
            kind="directive",
            artifact_id="001-architectural-integrity-standard",
        )
        assert any("initialized from default pack" in w.lower() for w in result.warnings)

    def test_default_ids_are_present_after_materialize(self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path) -> None:
        manager.activate(ctx, kind="directive", artifact_id="001-architectural-integrity-standard")
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        # At least one canonical built-in directive must be present
        assert "001-architectural-integrity-standard" in data["activated_directives"]


# ---------------------------------------------------------------------------
# TestActivateExistingSet
# ---------------------------------------------------------------------------


class TestActivateExistingSet:
    def test_appends_to_existing_list(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - 001-architectural-integrity-standard\n",
            encoding="utf-8",
        )
        ctx = ProjectContext(repo_root=project_root)
        result = manager.activate(ctx, kind="directive", artifact_id="003-decision-documentation-requirement")
        assert "003-decision-documentation-requirement" in result.activated
        data = yaml.safe_load(config.read_text())
        assert "001-architectural-integrity-standard" in data["activated_directives"]
        assert "003-decision-documentation-requirement" in data["activated_directives"]

    def test_no_duplicate_on_double_activate(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - 001-architectural-integrity-standard\n",
            encoding="utf-8",
        )
        ctx = ProjectContext(repo_root=project_root)
        manager.activate(ctx, kind="directive", artifact_id="001-architectural-integrity-standard")
        data = yaml.safe_load(config.read_text())
        assert data["activated_directives"].count("001-architectural-integrity-standard") == 1

    def test_rejects_malformed_existing_activation_set(self, manager: CharterPackManager, project_root: Path) -> None:
        """A scalar activation set must not be split into characters on write."""
        config = project_root / ".kittify" / "config.yaml"
        config.write_text("activated_directives: not-a-list\n", encoding="utf-8")
        before = config.read_text(encoding="utf-8")
        ctx = ProjectContext(repo_root=project_root)

        with pytest.raises(ValueError, match="activated_directives.*must be a list"):
            manager.activate(
                ctx,
                kind="directive",
                artifact_id="001-architectural-integrity-standard",
            )

        assert config.read_text(encoding="utf-8") == before

    def test_comments_preserved_in_config(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "# project-level comment\nactivated_directives:\n  - 001-architectural-integrity-standard\n",
            encoding="utf-8",
        )
        ctx = ProjectContext(repo_root=project_root)
        manager.activate(ctx, kind="directive", artifact_id="003-decision-documentation-requirement")
        raw = config.read_text()
        assert "# project-level comment" in raw


# ---------------------------------------------------------------------------
# TestActivateInvalidKind
# ---------------------------------------------------------------------------


class TestActivateInvalidKind:
    def test_raises_value_error_for_unknown_kind(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        with pytest.raises(ValueError, match="Unknown activation kind"):
            manager.activate(ctx, kind="nonexistent-kind", artifact_id="x")

    def test_raises_value_error_for_unknown_artifact_id(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        # WP09 delegates activation to the engine, which raises the typed
        # UnknownActivationIdError (a ValueError subclass) with the actionable
        # "Unknown <kind> ID ..." message.
        with pytest.raises(ValueError, match="Unknown directive ID"):
            manager.activate(ctx, kind="directive", artifact_id="not-a-real-directive")


# ---------------------------------------------------------------------------
# TestDeactivateNoneState
# ---------------------------------------------------------------------------


class TestDeactivateNoneState:
    def test_raises_typed_error_when_no_activation_set(
        self,
        manager: CharterPackManager,
        ctx: ProjectContext,
    ) -> None:
        """deactivate() on a None-state kind raises the typed engine error.

        WP09/T042: the legacy ``sys.exit(1)`` is gone — the activation engine
        raises NoActivationRestrictionsError (carrying the "run upgrade first"
        guidance) for the CLI (WP12) to surface, so the engine/manager never
        touch process state.
        """
        from charter.activation_engine import NoActivationRestrictionsError

        with pytest.raises(NoActivationRestrictionsError, match="spec-kitty upgrade"):
            manager.deactivate(ctx, kind="directive", artifact_id="something")


# ---------------------------------------------------------------------------
# TestDeactivateExistingSet
# ---------------------------------------------------------------------------


class TestDeactivateExistingSet:
    def test_removes_artifact_from_list(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - keep-me\n  - remove-me\n",
            encoding="utf-8",
        )
        ctx = ProjectContext(repo_root=project_root)
        result = manager.deactivate(ctx, kind="directive", artifact_id="remove-me")
        assert "remove-me" in result.deactivated
        data = yaml.safe_load(config.read_text())
        assert "remove-me" not in data["activated_directives"]
        assert "keep-me" in data["activated_directives"]

    def test_warns_when_artifact_not_in_set(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - something-else\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.deactivate(ctx, kind="directive", artifact_id="not-present")
        assert result.deactivated == []
        assert any("not in the activation set" in w for w in result.warnings)

    def test_rejects_malformed_existing_activation_set(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text("activated_directives: not-a-list\n", encoding="utf-8")
        ctx = ProjectContext(repo_root=project_root)

        with pytest.raises(ValueError, match="activated_directives.*must be a list"):
            manager.deactivate(ctx, kind="directive", artifact_id="x")


# ---------------------------------------------------------------------------
# TestListActivated
# ---------------------------------------------------------------------------


class TestListActivated:
    def test_none_for_all_kinds_on_empty_config(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        """All kinds return None when config.yaml has no activation keys."""
        result = manager.list_activated(ctx)
        assert len(result) == 9
        for kind in YAML_KEY_MAP:
            assert result[kind] is None, f"Expected None for kind '{kind}'"

    def test_returns_frozenset_for_populated_kind(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - aaa\n  - bbb\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.list_activated(ctx)
        assert result["directive"] == frozenset({"aaa", "bbb"})

    def test_other_kinds_still_none_when_one_populated(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - something\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.list_activated(ctx)
        assert result["tactic"] is None
        assert result["paradigm"] is None


# ---------------------------------------------------------------------------
# TestMergeDefaults
# ---------------------------------------------------------------------------


class TestMergeDefaults:
    def test_writes_absent_keys(self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path) -> None:
        result = manager.merge_defaults(ctx)
        assert len(result.kinds_written) == 9  # all 9 kinds were absent
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        for yaml_key in YAML_KEY_MAP.values():
            assert yaml_key in data, f"Missing key after merge_defaults: {yaml_key}"

    def test_does_not_overwrite_present_keys(self, manager: CharterPackManager, project_root: Path) -> None:
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - only-mine\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.merge_defaults(ctx)
        data = yaml.safe_load(config.read_text())
        # existing directive key must not be overwritten
        assert data["activated_directives"] == ["only-mine"]
        # other 8 absent kinds must have been written
        assert "directive" not in result.kinds_written
        assert len(result.kinds_written) == 8

    def test_creates_backup_when_charter_exists(self, manager: CharterPackManager, ctx: ProjectContext, project_root: Path) -> None:
        charter_dir = project_root / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_file = charter_dir / "charter.md"
        charter_file.write_text("# My Charter\n", encoding="utf-8")

        result = manager.merge_defaults(ctx)
        assert result.backup_path is not None
        assert result.backup_path.exists()
        assert result.backup_path.read_text() == "# My Charter\n"
        assert result.backup_path.parent.name == "backups"

    def test_no_backup_when_no_charter(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        result = manager.merge_defaults(ctx)
        assert result.backup_path is None


# ---------------------------------------------------------------------------
# TestActivateCascadeWarning
# ---------------------------------------------------------------------------


class TestActivateCascadeWarning:
    def test_cascade_true_does_not_append_manager_warning(self, manager: CharterPackManager, project_root: Path) -> None:
        """activate(cascade=True) keeps manager warnings scoped to activation state."""
        config = project_root / ".kittify" / "config.yaml"
        config.write_text(
            "activated_directives:\n  - 001-architectural-integrity-standard\n",
            encoding="utf-8",
        )
        ctx = ProjectContext.from_repo(project_root)
        result = manager.activate(
            ctx,
            kind="directive",
            artifact_id="003-decision-documentation-requirement",
            cascade=True,
        )
        assert not any("cascade" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# TestDeactivateCascadeAndInvalidKind
# ---------------------------------------------------------------------------


class TestDeactivateCascadeAndInvalidKind:
    def test_cascade_true_does_not_append_manager_warning(self, manager: CharterPackManager, project_root: Path) -> None:
        """deactivate(cascade=True) keeps manager warnings scoped to activation state."""
        config = project_root / ".kittify" / "config.yaml"
        config.write_text("activated_directives:\n  - to-remove\n", encoding="utf-8")
        ctx = ProjectContext.from_repo(project_root)
        result = manager.deactivate(ctx, kind="directive", artifact_id="to-remove", cascade=True)
        assert not any("cascade" in w.lower() for w in result.warnings)

    def test_raises_value_error_for_unknown_kind(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        """deactivate() with an unknown kind raises ValueError."""
        with pytest.raises(ValueError, match="Unknown activation kind"):
            manager.deactivate(ctx, kind="not-a-kind", artifact_id="x")


# ---------------------------------------------------------------------------
# TestListAvailable
# ---------------------------------------------------------------------------


class TestListAvailable:
    def test_raises_value_error_for_unknown_kind(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        """list_available() with an unknown kind raises ValueError."""
        with pytest.raises(ValueError, match="Unknown activation kind"):
            manager.list_available(ctx, kind="bogus-kind")

    def test_returns_nonempty_frozenset_for_directive(self, manager: CharterPackManager, ctx: ProjectContext) -> None:
        """list_available('directive') returns at least one built-in directive ID."""
        result = manager.list_available(ctx, kind="directive")
        assert isinstance(result, frozenset)
        assert len(result) > 0
