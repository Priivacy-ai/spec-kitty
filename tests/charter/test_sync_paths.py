"""Parity coverage for charter sync path helpers across both import paths."""

from importlib import import_module
from pathlib import Path

import pytest

charter_sync = import_module("charter.sync")
specify_cli_sync = import_module("specify_cli.charter.sync")

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


@pytest.mark.parametrize("sync_module", [charter_sync, specify_cli_sync])
def test_sync_path_helpers_use_standard_bundle_paths(tmp_path: Path, sync_module) -> None:
    """Each sync module should resolve the charter bundle paths consistently."""
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    charter_path = charter_dir / "charter.md"
    charter_path.write_text(SAMPLE_CHARTER, encoding="utf-8")

    result = sync_module.sync(charter_path, charter_dir, force=True)

    assert result.synced is True
    assert result.files_written == EXPECTED_CHARTER_FILES

    refresh_result = sync_module.ensure_charter_bundle_fresh(tmp_path)
    assert refresh_result is not None
    assert refresh_result.synced is False

    governance = sync_module.load_governance_config(tmp_path)
    directives = sync_module.load_directives_config(tmp_path)

    assert governance.model_dump() is not None
    assert directives.model_dump() is not None
