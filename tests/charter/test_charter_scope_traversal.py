"""Regression tests for P2 bug: CharterScope.root accepted path traversal.

Before the fix (2026-05, Robert adversarial review), the ``root`` field
validator only checked for non-emptiness.  An operator could supply
``root: "../../etc"`` in ``.kittify/config.yaml::charter_scopes`` and the
scope resolver would walk outside the repository.

The fix adds a Pydantic ``field_validator`` that rejects absolute paths and
entries containing ``..`` segments, plus a defence-in-depth check in
``CharterScope.resolve`` that asserts the resolved path stays inside
``repo_root``.
"""

from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Pydantic validator — _CharterScopeEntry
# ---------------------------------------------------------------------------


class TestCharterScopeEntryRootValidator:
    """_CharterScopeEntry.root must reject absolute paths and ``..`` segments."""

    def test_relative_safe_path_is_accepted(self) -> None:
        from charter.scope import CharterScopeConfig  # noqa: PLC0415

        config = CharterScopeConfig.model_validate(
            {"charter_scopes": [{"root": "packages/auth", "name": "auth"}]}
        )
        assert config.charter_scopes[0].root == "packages/auth"

    @pytest.mark.parametrize(
        "evil_root",
        [
            "/etc",
            "/absolute/path",
            "../../etc",
            "../sibling",
            "packages/../../etc",
            "a/b/../../../evil",
        ],
    )
    def test_absolute_or_dotdot_root_is_rejected(self, evil_root: str) -> None:
        """Absolute paths and ``..`` segments must raise ValidationError at parse time."""
        from pydantic import ValidationError  # noqa: PLC0415

        from charter.scope import CharterScopeConfig  # noqa: PLC0415

        with pytest.raises(ValidationError, match="(?i)absolute|\\.\\."):
            CharterScopeConfig.model_validate(
                {"charter_scopes": [{"root": evil_root}]}
            )

    def test_empty_root_still_rejected(self) -> None:
        """The original non-empty check must still fire."""
        from pydantic import ValidationError  # noqa: PLC0415

        from charter.scope import CharterScopeConfig  # noqa: PLC0415

        with pytest.raises(ValidationError):
            CharterScopeConfig.model_validate({"charter_scopes": [{"root": ""}]})


# ---------------------------------------------------------------------------
# Defence-in-depth in CharterScope.resolve
# ---------------------------------------------------------------------------


class TestCharterScopeResolveDefenceInDepth:
    """CharterScope.resolve must not return a scope outside repo_root even if
    a malicious entry somehow passed validation."""

    def test_resolve_rejects_root_outside_repo(self, tmp_path: Path) -> None:
        """If a config entry resolves outside repo_root, resolve() must raise."""
        from charter.scope import CharterScope, CharterScopeConflict  # noqa: PLC0415

        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        feature_dir = repo_root / "packages" / "auth"
        feature_dir.mkdir(parents=True)

        # Write a config with a symlinked root that would escape repo_root
        # if not caught by the validator.  We bypass the Pydantic validator
        # directly to test the runtime guard.
        from charter.scope import CharterScopeConfig  # noqa: PLC0415

        # Force-construct a config entry with a safe-looking root that after
        # resolution escapes repo_root via a real symlink on the filesystem.
        outside = tmp_path / "outside"
        outside.mkdir()
        link = repo_root / "escape-link"
        link.symlink_to(outside)

        # The entry root "escape-link" looks relative and has no ``..``, so
        # the Pydantic validator passes.  After resolve(), it points outside.
        config = CharterScopeConfig.model_validate(
            {"charter_scopes": [{"root": "escape-link"}]}
        )

        # Mock _load_charter_scope_config to return this config.
        from unittest.mock import patch  # noqa: PLC0415

        with patch(
            "charter.scope._load_charter_scope_config", return_value=config
        ), pytest.raises(CharterScopeConflict, match="(?i)outside|traversal"):
            CharterScope.resolve(repo_root, feature_dir)
