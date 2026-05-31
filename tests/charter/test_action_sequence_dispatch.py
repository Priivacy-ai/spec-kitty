"""Tests for charter API: existing_mission_types() and resolve_action_sequence() (WP05).

T035 — write charter API tests covering:
- existing_mission_types() returns sorted built-in types when no charter config exists
- existing_mission_types() returns only activated types when charter config specifies activation
- resolve_action_sequence("software-dev", repo_root) returns the built-in action sequence
- resolve_action_sequence("nonexistent", repo_root) raises UnknownMissionTypeError with registered_ids
- UnknownMissionTypeError.registered_ids contains the sorted list of activated types
- MissionTypeProfile(mission_type="anything", ...) succeeds (no Literal constraint at model time)

Patching strategy:
- existing_mission_types() uses a lazy import of PackContext inside the function.
  Tests for existing_mission_types() itself patch the lazy-imported module at its
  source path using sys.modules injection.
- Tests for resolve_action_sequence() patch existing_mission_types() directly
  (at charter.mission_type_profiles.existing_mission_types) and inject
  MissionTypeRepository via sys.modules for the inner import.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from charter.mission_type_profiles import (
    MissionTypeProfile,
    UnknownMissionTypeError,
    existing_mission_types,
    resolve_action_sequence,
)


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers: mock PackContext and MissionTypeRepository
# ---------------------------------------------------------------------------


def _make_pack_context(activated: frozenset[str]) -> MagicMock:
    """Return a mock PackContext with the given activated_mission_types."""
    ctx = MagicMock()
    ctx.activated_mission_types = activated
    return ctx


def _make_mission_type(
    id_: str,
    action_sequence: list[str],
    extends: str | None = None,
) -> MagicMock:
    """Return a mock MissionType with the given fields."""
    mt = MagicMock()
    mt.id = id_
    mt.action_sequence = action_sequence
    mt.extends = extends
    return mt


def _make_repo(*mission_types: MagicMock) -> MagicMock:
    """Return a mock MissionTypeRepository that serves the given mission types."""
    index = {mt.id: mt for mt in mission_types}
    repo = MagicMock()
    repo.get.side_effect = lambda k: index.get(k)
    return repo


def _inject_pack_context_mock(activated: frozenset[str]) -> tuple[MagicMock, dict]:
    """Inject a mock PackContext module into sys.modules for lazy-import patching.

    Returns (mock_ctx, saved_modules) where saved_modules can be used to restore
    the original sys.modules state.
    """
    mock_ctx = _make_pack_context(activated)
    mock_pack_context_cls = MagicMock()
    mock_pack_context_cls.from_config.return_value = mock_ctx

    # Build a fake charter.pack_context module
    fake_module = types.ModuleType("charter.pack_context")
    fake_module.PackContext = mock_pack_context_cls  # type: ignore[attr-defined]

    saved: dict = {}
    for key in ("charter.pack_context",):
        saved[key] = sys.modules.get(key)

    sys.modules["charter.pack_context"] = fake_module
    return mock_ctx, saved


def _restore_modules(saved: dict) -> None:
    """Restore sys.modules to the state before _inject_pack_context_mock."""
    for key, val in saved.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val


def _inject_mission_type_repository_mock(
    mock_repo: MagicMock,
) -> dict:
    """Inject a mock MissionTypeRepository module into sys.modules.

    Returns saved_modules for cleanup.
    """
    mock_repo_cls = MagicMock()
    mock_repo_cls.default.return_value = mock_repo

    # Need both the package and the specific module
    fake_pkg = types.ModuleType("doctrine.missions")
    fake_module = types.ModuleType("doctrine.missions.mission_type_repository")
    fake_module.MissionTypeRepository = mock_repo_cls  # type: ignore[attr-defined]

    saved: dict = {}
    for key in ("doctrine.missions", "doctrine.missions.mission_type_repository"):
        saved[key] = sys.modules.get(key)

    # Only inject the specific module (don't override doctrine.missions if it exists)
    if "doctrine.missions" not in sys.modules:
        sys.modules["doctrine.missions"] = fake_pkg
    sys.modules["doctrine.missions.mission_type_repository"] = fake_module
    return saved


# ---------------------------------------------------------------------------
# existing_mission_types()
# ---------------------------------------------------------------------------


class TestExistingMissionTypes:
    """existing_mission_types() returns the sorted list of activated mission type IDs."""

    def test_returns_builtin_defaults_when_no_config(self, tmp_path: Path) -> None:
        """When no charter config exists, all four built-in types are returned (fallback)."""
        builtin = frozenset({"software-dev", "documentation", "research", "plan"})
        mock_ctx, saved = _inject_pack_context_mock(builtin)
        try:
            result = existing_mission_types(tmp_path)
        finally:
            _restore_modules(saved)

        assert result == sorted(builtin)

    def test_returns_sorted_list(self, tmp_path: Path) -> None:
        """existing_mission_types() MUST return a sorted list."""
        activated = frozenset({"software-dev", "documentation", "plan"})
        mock_ctx, saved = _inject_pack_context_mock(activated)
        try:
            result = existing_mission_types(tmp_path)
        finally:
            _restore_modules(saved)

        assert result == sorted(activated)
        assert isinstance(result, list)

    def test_returns_only_activated_types(self, tmp_path: Path) -> None:
        """When charter config specifies activation, only activated types are returned."""
        activated = frozenset({"software-dev", "documentation"})
        mock_ctx, saved = _inject_pack_context_mock(activated)
        try:
            result = existing_mission_types(tmp_path)
        finally:
            _restore_modules(saved)

        assert "software-dev" in result
        assert "documentation" in result
        assert "research" not in result
        assert "plan" not in result

    def test_returns_custom_type_when_activated(self, tmp_path: Path) -> None:
        """A custom mission type activated in config appears in the returned list."""
        activated = frozenset({"software-dev", "compliance-audit"})
        mock_ctx, saved = _inject_pack_context_mock(activated)
        try:
            result = existing_mission_types(tmp_path)
        finally:
            _restore_modules(saved)

        assert "compliance-audit" in result
        assert "software-dev" in result


# ---------------------------------------------------------------------------
# resolve_action_sequence()
# ---------------------------------------------------------------------------


class TestResolveActionSequence:
    """resolve_action_sequence() returns the built-in action sequence and raises
    UnknownMissionTypeError for unregistered types.
    """

    def test_software_dev_returns_builtin_sequence(self, tmp_path: Path) -> None:
        """resolve_action_sequence('software-dev', repo_root) returns the built-in sequence."""
        expected = ["specify", "plan", "tasks", "implement", "review"]
        software_dev = _make_mission_type("software-dev", expected)
        mock_repo = _make_repo(software_dev)
        saved = _inject_mission_type_repository_mock(mock_repo)

        try:
            with patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["documentation", "plan", "research", "software-dev"],
            ):
                result = resolve_action_sequence("software-dev", tmp_path)
        finally:
            _restore_modules(saved)

        assert result == expected

    def test_nonexistent_raises_unknown_mission_type_error(self, tmp_path: Path) -> None:
        """resolve_action_sequence('nonexistent', ...) raises UnknownMissionTypeError."""
        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=["documentation", "plan", "research", "software-dev"],
        ), pytest.raises(UnknownMissionTypeError) as exc_info:
            resolve_action_sequence("nonexistent-type", tmp_path)

        assert "nonexistent-type" in str(exc_info.value)

    def test_error_carries_registered_ids(self, tmp_path: Path) -> None:
        """The UnknownMissionTypeError raised carries sorted activated IDs in registered_ids."""
        registered = ["documentation", "plan", "research", "software-dev"]

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=registered,
        ), pytest.raises(UnknownMissionTypeError) as exc_info:
            resolve_action_sequence("unknown-type", tmp_path)

        err = exc_info.value
        assert err.registered_ids == registered

    def test_result_is_a_list(self, tmp_path: Path) -> None:
        """resolve_action_sequence() returns a list, not another iterable type."""
        software_dev = _make_mission_type(
            "software-dev",
            ["specify", "plan", "tasks", "implement", "review"],
        )
        mock_repo = _make_repo(software_dev)
        saved = _inject_mission_type_repository_mock(mock_repo)

        try:
            with patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["software-dev"],
            ):
                result = resolve_action_sequence("software-dev", tmp_path)
        finally:
            _restore_modules(saved)

        assert isinstance(result, list)

    def test_not_cached_across_calls(self, tmp_path: Path) -> None:
        """resolve_action_sequence() reads fresh from disk on each invocation (FR-007)."""
        software_dev = _make_mission_type(
            "software-dev",
            ["specify", "plan", "tasks", "implement", "review"],
        )

        call_count = 0

        def counting_repo_factory() -> MagicMock:
            nonlocal call_count
            call_count += 1
            return _make_repo(software_dev)

        mock_repo_cls = MagicMock()
        mock_repo_cls.default.side_effect = counting_repo_factory

        fake_module = types.ModuleType("doctrine.missions.mission_type_repository")
        fake_module.MissionTypeRepository = mock_repo_cls  # type: ignore[attr-defined]

        saved: dict = {}
        for key in ("doctrine.missions.mission_type_repository",):
            saved[key] = sys.modules.get(key)
        sys.modules["doctrine.missions.mission_type_repository"] = fake_module

        try:
            with patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["software-dev"],
            ):
                resolve_action_sequence("software-dev", tmp_path)
                resolve_action_sequence("software-dev", tmp_path)
        finally:
            _restore_modules(saved)

        # MissionTypeRepository.default() should be called twice (no caching)
        assert call_count == 2

    def test_extends_chain_resolved_when_own_sequence_empty(self, tmp_path: Path) -> None:
        """When a mission type has an extends: field and empty action_sequence,
        the parent's action_sequence is used.
        """
        parent = _make_mission_type(
            "software-dev",
            ["specify", "plan", "tasks", "implement", "review"],
        )
        child = _make_mission_type("custom-dev", [], extends="software-dev")
        mock_repo = _make_repo(parent, child)
        saved = _inject_mission_type_repository_mock(mock_repo)

        try:
            with patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["software-dev", "custom-dev"],
            ):
                result = resolve_action_sequence("custom-dev", tmp_path)
        finally:
            _restore_modules(saved)

        assert result == ["specify", "plan", "tasks", "implement", "review"]

    def test_own_sequence_takes_priority_over_extends(self, tmp_path: Path) -> None:
        """When a mission type has its own action_sequence, it takes priority over extends:."""
        parent = _make_mission_type(
            "software-dev",
            ["specify", "plan", "tasks", "implement", "review"],
        )
        child = _make_mission_type(
            "custom-dev",
            ["design", "build", "ship"],
            extends="software-dev",
        )
        mock_repo = _make_repo(parent, child)
        saved = _inject_mission_type_repository_mock(mock_repo)

        try:
            with patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["software-dev", "custom-dev"],
            ):
                result = resolve_action_sequence("custom-dev", tmp_path)
        finally:
            _restore_modules(saved)

        assert result == ["design", "build", "ship"]


# ---------------------------------------------------------------------------
# T034 — MissionTypeProfile Literal constraint removed
# ---------------------------------------------------------------------------


class TestMissionTypeProfileNoLiteralConstraint:
    """T034: MissionTypeProfile(mission_type='anything') succeeds at model time.

    These tests document the behavior change introduced by T029 — the Literal
    constraint is gone, so any string value is accepted by the Pydantic model.
    Runtime validation (UnknownMissionTypeError) is deferred to call time via
    existing_mission_types() / resolve_action_sequence().
    """

    def test_custom_mission_type_succeeds_at_model_time(self) -> None:
        """'compliance-audit' succeeds at MissionTypeProfile construction (no Literal)."""
        profile = MissionTypeProfile(mission_type="compliance-audit")
        assert profile.mission_type == "compliance-audit"

    def test_validation_error_not_raised_for_custom_types(self) -> None:
        """Historical ValidationError for out-of-Literal values MUST NOT be raised."""
        from pydantic import ValidationError  # noqa: PLC0415

        custom_types = [
            "compliance-audit",
            "security-review",
            "data-migration",
            "platform-engineering",
        ]
        for mt in custom_types:
            try:
                profile = MissionTypeProfile(mission_type=mt)
                assert profile.mission_type == mt
            except ValidationError as exc:
                pytest.fail(
                    f"MissionTypeProfile raised ValidationError for mission_type={mt!r}. "
                    f"T029 requires str annotation, not Literal[...]. Error: {exc}"
                )

    def test_resolve_action_sequence_raises_for_unactivated_custom_type(
        self, tmp_path: Path
    ) -> None:
        """Even though MissionTypeProfile accepts 'custom-type', resolve_action_sequence
        raises UnknownMissionTypeError if that type is not activated.
        """
        registered = ["documentation", "plan", "research", "software-dev"]

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=registered,
        ), pytest.raises(UnknownMissionTypeError) as exc_info:
            resolve_action_sequence("custom-type", tmp_path)

        err = exc_info.value
        assert err.mission_type_id == "custom-type"
        assert "custom-type" in str(err)
        assert err.registered_ids == registered
