"""Coverage for charter sync path helpers.

consolidate-charter-bundle (IC-04 / WP04, T028c): ``sync()``'s
prose->triad write is retired -- it always reports ``synced=False`` /
``files_written=[]`` now. Canonical-root resolution
(``ensure_charter_bundle_fresh``) and the ``charter.yaml``-sourced
governance/directives loaders are unaffected.
"""

from importlib import import_module
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

SAMPLE_CHARTER = """# Testing Standards

## Coverage Requirements
- Minimum 80% code coverage
"""


def test_sync_path_helpers_use_standard_bundle_paths(tmp_path: Path) -> None:
    """Canonical sync module resolves charter bundle paths consistently."""
    charter_sync = import_module("charter.sync")
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    charter_path = charter_dir / "charter.md"
    charter_path.write_text(SAMPLE_CHARTER, encoding="utf-8")

    result = charter_sync.sync(charter_path, charter_dir, force=True)

    assert result.synced is False
    assert result.files_written == []

    refresh_result = charter_sync.ensure_charter_bundle_fresh(tmp_path)
    assert refresh_result is not None
    assert refresh_result.synced is False

    governance = charter_sync.load_governance_config(tmp_path)
    directives = charter_sync.load_directives_config(tmp_path)

    assert governance.model_dump() is not None
    assert directives.model_dump() is not None
