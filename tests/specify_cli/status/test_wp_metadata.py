"""WP03 / FR-005+FR-006: Unit and CI tests for WPMetadata Pydantic model.

T012 — Unit tests for WPMetadata model and validators.
T013 — CI validation test ensuring all kitty-specs WP files pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from specify_cli.status.wp_metadata import WPMetadata, read_wp_frontmatter


# ─────────────────────────────────────────────────────────────
# T012: WPMetadata unit tests
# ─────────────────────────────────────────────────────────────


class TestWPMetadataMinimal:
    """Minimal required fields produce a valid instance."""

    def test_valid_minimal(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="Setup")
        assert meta.work_package_id == "WP01"
        assert meta.title == "Setup"
        assert meta.dependencies == []
        assert meta.base_branch is None
        assert meta.base_commit is None
        assert meta.shell_pid is None

    def test_valid_two_digit_id(self) -> None:
        meta = WPMetadata(work_package_id="WP99", title="Last")
        assert meta.work_package_id == "WP99"

    def test_valid_three_digit_id(self) -> None:
        meta = WPMetadata(work_package_id="WP100", title="Extended")
        assert meta.work_package_id == "WP100"


class TestWPMetadataFull:
    """All fields populated."""

    def test_valid_full(self) -> None:
        meta = WPMetadata(
            work_package_id="WP03",
            title="Full Model Test",
            dependencies=["WP01", "WP02"],
            base_branch="main",
            base_commit="abc1234",
            created_at="2026-04-06T10:00:00Z",
            planning_base_branch="feature/test",
            merge_target_branch="feature/test",
            branch_strategy="standard",
            requirement_refs=["FR-001", "FR-002"],
            execution_mode="code_change",
            owned_files=["src/foo.py"],
            authoritative_surface="src/foo.py",
            subtasks=["T001", "T002"],
            phase="Phase 1",
            assignee="claude",
            agent="claude",
            shell_pid=12345,
            history=[{"at": "2026-01-01", "actor": "system", "action": "created"}],
            mission_id="01ABC",
            wp_code="WP03",
            branch_strategy_override=None,
        )
        assert meta.work_package_id == "WP03"
        assert meta.dependencies == ["WP01", "WP02"]
        assert meta.shell_pid == 12345
        assert meta.phase == "Phase 1"
        assert len(meta.history) == 1


class TestWPMetadataRequired:
    """Missing required fields raise ValidationError."""

    def test_missing_work_package_id(self) -> None:
        with pytest.raises(ValidationError, match="work_package_id"):
            WPMetadata(title="No ID")  # type: ignore[call-arg]

    def test_missing_title(self) -> None:
        with pytest.raises(ValidationError, match="title"):
            WPMetadata(work_package_id="WP01")  # type: ignore[call-arg]


class TestWPMetadataValidators:
    """Field validators enforce patterns and constraints."""

    def test_invalid_wp_id_too_few_digits(self) -> None:
        with pytest.raises(ValidationError, match="work_package_id"):
            WPMetadata(work_package_id="WP1", title="Bad")

    def test_invalid_wp_id_no_digits(self) -> None:
        with pytest.raises(ValidationError, match="work_package_id"):
            WPMetadata(work_package_id="WP", title="Bad")

    def test_invalid_wp_id_lowercase(self) -> None:
        with pytest.raises(ValidationError, match="work_package_id"):
            WPMetadata(work_package_id="wp01", title="Bad")

    def test_empty_title(self) -> None:
        with pytest.raises(ValidationError, match="title"):
            WPMetadata(work_package_id="WP01", title="")

    def test_whitespace_only_title(self) -> None:
        with pytest.raises(ValidationError, match="title"):
            WPMetadata(work_package_id="WP01", title="   ")

    def test_invalid_base_commit(self) -> None:
        with pytest.raises(ValidationError, match="base_commit"):
            WPMetadata(work_package_id="WP01", title="T", base_commit="not-hex")

    def test_valid_base_commit_short(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", base_commit="abc1234")
        assert meta.base_commit == "abc1234"

    def test_valid_base_commit_full(self) -> None:
        sha = "a" * 40
        meta = WPMetadata(work_package_id="WP01", title="T", base_commit=sha)
        assert meta.base_commit == sha

    def test_base_commit_none_is_valid(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", base_commit=None)
        assert meta.base_commit is None


class TestWPMetadataShellPid:
    """shell_pid coercion from string/empty to int/None."""

    def test_string_coercion(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", shell_pid="18377")  # type: ignore[arg-type]
        assert meta.shell_pid == 18377

    def test_empty_string_to_none(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", shell_pid="")  # type: ignore[arg-type]
        assert meta.shell_pid is None

    def test_none_stays_none(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", shell_pid=None)
        assert meta.shell_pid is None

    def test_int_stays_int(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", shell_pid=42)
        assert meta.shell_pid == 42

    def test_large_pid_string(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", shell_pid="2451078")  # type: ignore[arg-type]
        assert meta.shell_pid == 2451078


class TestWPMetadataPhaseCoercion:
    """phase coercion from non-string types."""

    def test_integer_phase(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", phase=1)  # type: ignore[arg-type]
        assert meta.phase == "1"

    def test_string_phase(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", phase="Phase 2")
        assert meta.phase == "Phase 2"

    def test_none_phase(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T", phase=None)
        assert meta.phase is None


class TestWPMetadataExtraFields:
    """extra='forbid' rejects unknown fields; formerly-extra fields are declared."""

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            WPMetadata(
                work_package_id="WP01",
                title="T",
                custom_field="value",  # type: ignore[call-arg]
            )

    def test_lane_as_declared_field(self) -> None:
        """'lane' is now a declared optional field."""
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
            lane="planned",
        )
        assert meta.lane == "planned"

    def test_task_type_as_declared_field(self) -> None:
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
            task_type="implement",
        )
        assert meta.task_type == "implement"

    def test_agent_profile_as_declared_field(self) -> None:
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
            agent_profile="python-implementer",
        )
        assert meta.agent_profile == "python-implementer"


class TestWPMetadataFrozen:
    """Model is immutable."""

    def test_frozen_rejects_assignment(self) -> None:
        meta = WPMetadata(work_package_id="WP01", title="T")
        with pytest.raises(ValidationError):
            meta.title = "Changed"


class TestWPMetadataLegacyNormalization:
    """Model-level pre-processing for legacy field names and types."""

    def test_work_package_title_fallback(self) -> None:
        """Legacy 'work_package_title' is used when 'title' is absent."""
        meta = WPMetadata.model_validate(
            {
                "work_package_id": "WP01",
                "work_package_title": "Foundation Layer",
            }
        )
        assert meta.title == "Foundation Layer"

    def test_title_takes_precedence(self) -> None:
        """When both 'title' and 'work_package_title' exist, 'title' wins."""
        meta = WPMetadata.model_validate(
            {
                "work_package_id": "WP01",
                "title": "Preferred",
                "work_package_title": "Fallback",
            }
        )
        assert meta.title == "Preferred"

    def test_dependencies_string_empty_list(self) -> None:
        """Dependencies stored as string '[]' are parsed to empty list."""
        meta = WPMetadata.model_validate(
            {
                "work_package_id": "WP01",
                "title": "T",
                "dependencies": "[]",
            }
        )
        assert meta.dependencies == []

    def test_dependencies_string_csv(self) -> None:
        """Dependencies as comma-separated string are parsed to list."""
        meta = WPMetadata.model_validate(
            {
                "work_package_id": "WP01",
                "title": "T",
                "dependencies": "WP01, WP02",
            }
        )
        assert meta.dependencies == ["WP01", "WP02"]


class TestWPMetadataRoundTrip:
    """NFR-004: Round-trip safe serialization."""

    def test_model_dump_preserves_values(self) -> None:
        data = {
            "work_package_id": "WP01",
            "title": "Setup",
            "dependencies": ["WP02"],
            "phase": "Phase 1",
            "shell_pid": 123,
        }
        meta = WPMetadata.model_validate(data)
        dumped = meta.model_dump()
        assert dumped["work_package_id"] == "WP01"
        assert dumped["title"] == "Setup"
        assert dumped["dependencies"] == ["WP02"]
        assert dumped["phase"] == "Phase 1"
        assert dumped["shell_pid"] == 123

    def test_model_dump_preserves_extra(self) -> None:
        meta = WPMetadata.model_validate(
            {
                "work_package_id": "WP01",
                "title": "T",
                "lane": "planned",
                "task_type": "implement",
            }
        )
        dumped = meta.model_dump()
        assert dumped["lane"] == "planned"
        assert dumped["task_type"] == "implement"


# ─────────────────────────────────────────────────────────────
# T010: read_wp_frontmatter() tests
# ─────────────────────────────────────────────────────────────


class TestReadWpFrontmatter:
    """Tests for the read_wp_frontmatter() convenience loader."""

    def test_valid_wp_file(self, tmp_path: Path) -> None:
        wp_file = tmp_path / "WP01-setup.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ntitle: Setup Task\ndependencies: []\n---\n\n# Body\n\nSome content.\n",
            encoding="utf-8",
        )
        meta, body = read_wp_frontmatter(wp_file)
        assert meta.work_package_id == "WP01"
        assert meta.title == "Setup Task"
        assert "Body" in body

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        wp_file = tmp_path / "WP99-bad.md"
        wp_file.write_text(
            "---\ntitle: No ID\n---\n\nBody\n",
            encoding="utf-8",
        )
        with pytest.raises(ValidationError, match="work_package_id"):
            read_wp_frontmatter(wp_file)

    def test_shell_pid_string_in_file(self, tmp_path: Path) -> None:
        wp_file = tmp_path / "WP01-pid.md"
        wp_file.write_text(
            '---\nwork_package_id: WP01\ntitle: PID Test\nshell_pid: "405597"\n---\n\nBody\n',
            encoding="utf-8",
        )
        meta, _ = read_wp_frontmatter(wp_file)
        assert meta.shell_pid == 405597

    def test_extra_fields_in_file(self, tmp_path: Path) -> None:
        """Fields formerly stored as extras are now declared on the model."""
        wp_file = tmp_path / "WP01-extra.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ntitle: Extra\nlane: planned\nagent_profile: python-implementer\n---\n\nBody\n",
            encoding="utf-8",
        )
        meta, _ = read_wp_frontmatter(wp_file)
        assert meta.lane == "planned"
        assert meta.agent_profile == "python-implementer"


# ─────────────────────────────────────────────────────────────
# T013: CI validation — all kitty-specs WP files must validate
# ─────────────────────────────────────────────────────────────


class TestCIValidation:
    """SC-004 / C-003: All active WP files pass WPMetadata.model_validate()."""

    @staticmethod
    def _find_kitty_specs_root() -> Path | None:
        """Walk up from cwd to find the kitty-specs directory."""
        cwd = Path.cwd()
        for candidate in [cwd, *cwd.parents]:
            ks = candidate / "kitty-specs"
            if ks.is_dir():
                return ks
        return None

    def test_all_kitty_specs_wp_files_validate(self) -> None:
        """All active WP files pass WPMetadata.model_validate().

        Files with broken YAML (e.g. unresolved merge conflicts) are
        reported separately — they indicate a repo hygiene issue, not a
        model defect.
        """
        ks_root = self._find_kitty_specs_root()
        if ks_root is None:
            pytest.skip("kitty-specs/ not found — likely running outside repo root")

        wp_files = sorted(ks_root.glob("*/tasks/WP*.md"))
        assert len(wp_files) > 0, "No WP files found in kitty-specs/"

        validation_failures: list[str] = []
        yaml_errors: list[str] = []

        for wp_file in wp_files:
            try:
                read_wp_frontmatter(wp_file)
            except ValidationError as e:
                validation_failures.append(f"{wp_file.relative_to(ks_root.parent)}: {e}")
            except Exception as e:
                # FrontmatterError (broken YAML, merge conflicts, etc.)
                yaml_errors.append(f"{wp_file.relative_to(ks_root.parent)}: {e}")

        msg_parts = []
        if validation_failures:
            msg_parts.append(f"{len(validation_failures)} WP file(s) failed model validation:\n" + "\n".join(validation_failures))
        if yaml_errors:
            msg_parts.append(f"{len(yaml_errors)} WP file(s) have broken YAML (merge conflicts?):\n" + "\n".join(yaml_errors))

        # Validation errors are hard failures; YAML errors are warnings
        assert not validation_failures, "\n\n".join(msg_parts)


# ─────────────────────────────────────────────────────────────
# T-update: WPMetadata.update() — immutable field mutation
# ─────────────────────────────────────────────────────────────


class TestWPMetadataUpdate:
    """update() returns a NEW WPMetadata with specified fields changed."""

    def _make_base(self, **overrides: Any) -> WPMetadata:
        defaults = {"work_package_id": "WP01", "title": "Base"}
        return WPMetadata.model_validate({**defaults, **overrides})

    # -- basic single-field update --

    def test_update_single_field(self) -> None:
        base = self._make_base(lane="planned")
        updated = base.update(lane="in_progress")
        assert updated.lane == "in_progress"
        assert updated is not base

    def test_update_preserves_unchanged_fields(self) -> None:
        base = self._make_base(lane="planned", agent="claude", title="Original")
        updated = base.update(lane="in_progress")
        assert updated.title == "Original"
        assert updated.agent == "claude"
        assert updated.work_package_id == "WP01"

    # -- multi-field update --

    def test_update_multiple_fields(self) -> None:
        base = self._make_base()
        updated = base.update(lane="in_progress", agent="gemini", phase="Phase 2")
        assert updated.lane == "in_progress"
        assert updated.agent == "gemini"
        assert updated.phase == "Phase 2"

    # -- list field replacement --

    def test_update_replaces_list_field(self) -> None:
        base = self._make_base(dependencies=["WP02"])
        updated = base.update(dependencies=["WP02", "WP03"])
        assert updated.dependencies == ["WP02", "WP03"]
        assert base.dependencies == ["WP02"]  # original unchanged

    # -- None fields --

    def test_update_can_set_field_to_none(self) -> None:
        base = self._make_base(agent="claude")
        updated = base.update(agent=None)
        assert updated.agent is None

    # -- immutability contract --

    def test_update_does_not_mutate_original(self) -> None:
        base = self._make_base(lane="planned", dependencies=["WP02"])
        _ = base.update(lane="in_progress", dependencies=["WP03"])
        assert base.lane == "planned"
        assert base.dependencies == ["WP02"]

    def test_original_stays_frozen_after_update(self) -> None:
        base = self._make_base()
        _ = base.update(lane="in_progress")
        with pytest.raises(ValidationError):
            base.title = "Mutated"

    # -- validation still fires --

    def test_update_validates_fields(self) -> None:
        base = self._make_base()
        with pytest.raises(ValidationError, match="title"):
            base.update(title="")

    def test_update_validates_base_commit(self) -> None:
        base = self._make_base()
        with pytest.raises(ValidationError, match="base_commit"):
            base.update(base_commit="not-hex")

    # -- rejects unknown fields --

    def test_update_rejects_unknown_field(self) -> None:
        base = self._make_base()
        with pytest.raises(TypeError, match="unknown_field"):
            base.update(unknown_field="bad")

    # -- no-op update returns equal (but new) instance --

    def test_update_no_args_returns_equal_copy(self) -> None:
        base = self._make_base(lane="planned")
        updated = base.update()
        assert updated == base
        assert updated is not base

    # -- chaining --

    def test_chained_updates(self) -> None:
        base = self._make_base()
        result = base.update(lane="planned").update(lane="in_progress").update(agent="claude")
        assert result.lane == "in_progress"
        assert result.agent == "claude"


# ─────────────────────────────────────────────────────────────
# T-builder: WPMetadata.builder() — fluent multi-step composition
# ─────────────────────────────────────────────────────────────


class TestWPMetadataBuilder:
    """builder() returns a _Builder for fluent multi-step field composition."""

    def _make_base(self, **overrides: Any) -> WPMetadata:
        defaults = {"work_package_id": "WP01", "title": "Base"}
        return WPMetadata.model_validate({**defaults, **overrides})

    # -- basic builder flow --

    def test_builder_set_and_build(self) -> None:
        base = self._make_base(lane="planned")
        result = base.builder().set(lane="in_progress").build()
        assert result.lane == "in_progress"
        assert result is not base

    def test_builder_multiple_set_calls(self) -> None:
        base = self._make_base()
        result = base.builder().set(lane="in_progress").set(agent="claude").set(phase="Phase 1").build()
        assert result.lane == "in_progress"
        assert result.agent == "claude"
        assert result.phase == "Phase 1"

    def test_builder_last_set_wins(self) -> None:
        base = self._make_base()
        result = base.builder().set(lane="planned").set(lane="in_progress").build()
        assert result.lane == "in_progress"

    # -- append_to_history --

    def test_builder_append_to_history(self) -> None:
        entry1 = {"at": "2026-01-01", "actor": "system", "action": "created"}
        base = self._make_base(history=[entry1])
        entry2 = {"at": "2026-01-02", "actor": "claude", "action": "started"}
        result = base.builder().append_to_history(entry2).build()
        assert len(result.history) == 2
        assert result.history[0] == entry1
        assert result.history[1] == entry2

    def test_builder_append_to_history_on_empty(self) -> None:
        base = self._make_base()
        entry = {"at": "2026-01-01", "actor": "system", "action": "created"}
        result = base.builder().append_to_history(entry).build()
        assert result.history == [entry]

    def test_builder_append_does_not_mutate_original(self) -> None:
        entry1 = {"at": "2026-01-01", "actor": "system", "action": "created"}
        base = self._make_base(history=[entry1])
        entry2 = {"at": "2026-01-02", "actor": "claude", "action": "started"}
        _ = base.builder().append_to_history(entry2).build()
        assert len(base.history) == 1

    # -- append_dependency --

    def test_builder_append_dependency(self) -> None:
        base = self._make_base(dependencies=["WP02"])
        result = base.builder().append_dependency("WP03").build()
        assert result.dependencies == ["WP02", "WP03"]
        assert base.dependencies == ["WP02"]

    def test_builder_append_dependency_on_empty(self) -> None:
        base = self._make_base()
        result = base.builder().append_dependency("WP02").build()
        assert result.dependencies == ["WP02"]

    # -- combined set + append --

    def test_builder_set_and_append_combined(self) -> None:
        base = self._make_base(lane="planned")
        entry = {"at": "2026-01-01", "actor": "claude", "action": "claimed"}
        result = base.builder().set(lane="in_progress").set(agent="claude").append_to_history(entry).build()
        assert result.lane == "in_progress"
        assert result.agent == "claude"
        assert len(result.history) == 1

    # -- validation fires on build --

    def test_builder_validates_on_build(self) -> None:
        base = self._make_base()
        with pytest.raises(ValidationError, match="title"):
            base.builder().set(title="").build()

    # -- rejects unknown fields in set --

    def test_builder_set_rejects_unknown_field(self) -> None:
        base = self._make_base()
        with pytest.raises(TypeError, match="bogus"):
            base.builder().set(bogus="bad")

    # -- builder does not modify source --

    def test_builder_does_not_modify_source(self) -> None:
        base = self._make_base(lane="planned")
        builder = base.builder()
        builder.set(lane="in_progress")
        # Before build(), base is still unchanged
        assert base.lane == "planned"

    # -- build can be called multiple times for different results --

    def test_builder_reusable_across_builds(self) -> None:
        base = self._make_base(lane="planned")
        builder = base.builder().set(agent="claude")
        r1 = builder.build()
        r2 = builder.set(lane="in_progress").build()
        assert r1.lane == "planned"
        assert r1.agent == "claude"
        assert r2.lane == "in_progress"
        assert r2.agent == "claude"
