"""Tests for constitution template migration (m_0_13_0_update_constitution_templates).

WP10: This migration is permanently inert because command-templates were deleted.
Shim generation (spec-kitty agent shim) replaces template-based agent commands.
"""

import pytest

from specify_cli.upgrade.migrations.m_0_13_0_update_constitution_templates import (
    UpdateConstitutionTemplatesMigration,
)

pytestmark = pytest.mark.fast


@pytest.fixture
def migration():
    """Return the migration instance."""
    return UpdateConstitutionTemplatesMigration()


def test_detect_always_returns_false(tmp_path, migration):
    """WP10: detect() must always return False (migration is inert)."""
    assert migration.detect(tmp_path) is False


def test_can_apply_always_returns_false(tmp_path, migration):
    """WP10: can_apply() must return False (templates removed)."""
    result, reason = migration.can_apply(tmp_path)
    assert result is False
    assert "WP10" in reason or "command templates" in reason.lower()


def test_apply_is_still_callable(tmp_path, migration):
    """WP10: apply() should not raise even though migration is inert."""
    # can_apply returns False, but apply() should handle gracefully
    result = migration.apply(tmp_path, dry_run=False)
    # apply() logic may succeed or fail, but should not crash
    assert isinstance(result.success, bool)
