"""Coverage for charter sync path helpers.

As of WP05 (complexity-code-smell-remediation), ``specify_cli.charter.sync``
no longer exists as a separate module — it was a duplicate that has been
deleted. The canonical implementation is ``charter.sync``, re-exported via
the ``specify_cli.charter`` backward-compatibility shim. This test suite
covers the canonical module only; C-005 backward-compat is tested by the
smoke import assertion below.
"""

from importlib import import_module
from pathlib import Path
import warnings

import pytest

pytestmark = pytest.mark.fast

EXPECTED_CHARTER_FILES = [
    "governance.yaml",
    "directives.yaml",
    "metadata.yaml",
]

SAMPLE_CHARTER = """# Testing Standards

## Coverage Requirements
- Minimum 80% code coverage
"""


def _import_legacy_charter_module():
    """Import the legacy shim after any test-driven module resets."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return import_module("specify_cli.charter")


def test_sync_shim_re_exports_canonical_sync() -> None:
    """specify_cli.charter.sync must be the same callable as charter.sync (C-005)."""
    from charter.sync import sync as canonical_sync

    assert _import_legacy_charter_module().sync is canonical_sync


def test_sync_path_helpers_use_standard_bundle_paths(tmp_path: Path) -> None:
    """Canonical sync module resolves charter bundle paths consistently."""
    charter_sync = import_module("charter.sync")
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    charter_path = charter_dir / "charter.md"
    charter_path.write_text(SAMPLE_CHARTER, encoding="utf-8")

    result = charter_sync.sync(charter_path, charter_dir, force=True)

    assert result.synced is True
    assert result.files_written == EXPECTED_CHARTER_FILES

    refresh_result = charter_sync.ensure_charter_bundle_fresh(tmp_path)
    assert refresh_result is not None
    assert refresh_result.synced is False

    governance = charter_sync.load_governance_config(tmp_path)
    directives = charter_sync.load_directives_config(tmp_path)

    assert governance.model_dump() is not None
    assert directives.model_dump() is not None
