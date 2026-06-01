"""Unit tests for ``charter.invocation_context``."""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.invocation_context import (
    ContextPreconditionError,
    OperationalContext,
    ProjectContext,
    build_operational_context,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ContextPreconditionError
# ---------------------------------------------------------------------------


class TestContextPreconditionError:
    def test_field_and_context_type_set(self) -> None:
        err = ContextPreconditionError(field="repo_root", context_type="ProjectContext")
        assert err.field == "repo_root"
        assert err.context_type == "ProjectContext"

    def test_str_message_format(self) -> None:
        err = ContextPreconditionError(field="pack_context", context_type="ProjectContext")
        msg = str(err)
        assert "pack_context" in msg
        assert "ProjectContext" in msg

    def test_is_runtime_error(self) -> None:
        err = ContextPreconditionError(field="x", context_type="Y")
        assert isinstance(err, RuntimeError)


# ---------------------------------------------------------------------------
# ProjectContext construction
# ---------------------------------------------------------------------------


class TestProjectContextDefaults:
    def test_all_none_defaults_valid(self) -> None:
        ctx = ProjectContext()
        assert ctx.repo_root is None
        assert ctx.pack_context is None
        assert ctx.org_root is None
        assert ctx.specs_dir is None
        assert ctx.architecture_dir is None

    def test_frozen_cannot_set_field(self) -> None:
        ctx = ProjectContext()
        with pytest.raises((AttributeError, TypeError)):
            ctx.repo_root = Path("/tmp")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ProjectContext.from_repo()
# ---------------------------------------------------------------------------


class TestProjectContextFromRepo:
    def test_repo_root_populated(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.repo_root == tmp_path

    def test_pack_context_non_none(self, tmp_path: Path) -> None:
        """from_repo() always populates pack_context even without .kittify/."""
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.pack_context is not None

    def test_specs_dir_detected_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "kitty-specs").mkdir()
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.specs_dir == tmp_path / "kitty-specs"

    def test_specs_dir_none_when_absent(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.specs_dir is None

    def test_architecture_dir_detected_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "architecture").mkdir()
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.architecture_dir == tmp_path / "architecture"

    def test_architecture_dir_none_when_absent(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.architecture_dir is None

    def test_no_raise_without_kittify(self, tmp_path: Path) -> None:
        """from_repo() must not raise when .kittify/ directory is absent.

        PackContext.from_config() is responsible for graceful absent-config
        handling (WP02 contract). This test verifies the contract end-to-end.
        """
        assert not (tmp_path / ".kittify").exists()
        ctx = ProjectContext.from_repo(tmp_path)
        assert ctx.repo_root == tmp_path


# ---------------------------------------------------------------------------
# Guard methods
# ---------------------------------------------------------------------------


class TestProjectContextGuards:
    def test_require_repo_root_returns_value(self) -> None:
        ctx = ProjectContext(repo_root=Path("/some/path"))
        assert ctx.require_repo_root() == Path("/some/path")

    def test_require_repo_root_raises_when_none(self) -> None:
        ctx = ProjectContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_repo_root()
        assert exc_info.value.field == "repo_root"
        assert exc_info.value.context_type == "ProjectContext"

    def test_require_pack_context_returns_value(self, tmp_path: Path) -> None:
        ctx = ProjectContext.from_repo(tmp_path)
        pc = ctx.require_pack_context()
        assert pc is not None

    def test_require_pack_context_raises_when_none(self) -> None:
        ctx = ProjectContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_pack_context()
        assert exc_info.value.field == "pack_context"
        assert exc_info.value.context_type == "ProjectContext"

    def test_require_org_root_raises_when_none(self) -> None:
        ctx = ProjectContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_org_root()
        assert exc_info.value.field == "org_root"
        assert exc_info.value.context_type == "ProjectContext"


# ---------------------------------------------------------------------------
# OperationalContext
# ---------------------------------------------------------------------------


class TestOperationalContext:
    def test_all_none_defaults(self) -> None:
        ctx = OperationalContext()
        assert ctx.active_model is None
        assert ctx.active_profile is None
        assert ctx.active_role is None
        assert ctx.current_activity is None
        assert ctx.tech_stack == frozenset()

    def test_require_active_profile_raises_when_none(self) -> None:
        ctx = OperationalContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_active_profile()
        assert exc_info.value.field == "active_profile"
        assert exc_info.value.context_type == "OperationalContext"

    def test_require_active_profile_returns_value(self) -> None:
        ctx = OperationalContext(active_profile="python-pedro")
        assert ctx.require_active_profile() == "python-pedro"

    def test_require_active_role_raises_when_none(self) -> None:
        ctx = OperationalContext()
        with pytest.raises(ContextPreconditionError) as exc_info:
            ctx.require_active_role()
        assert exc_info.value.field == "active_role"
        assert exc_info.value.context_type == "OperationalContext"

    def test_require_active_role_returns_value(self) -> None:
        ctx = OperationalContext(active_role="implementer")
        assert ctx.require_active_role() == "implementer"


class TestBuildOperationalContext:
    def test_returns_operational_context_instance(self) -> None:
        ctx = build_operational_context()
        assert isinstance(ctx, OperationalContext)

    def test_all_fields_none(self) -> None:
        ctx = build_operational_context()
        assert ctx.active_profile is None
        assert ctx.active_role is None
        assert ctx.tech_stack == frozenset()
