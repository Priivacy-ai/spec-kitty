"""WP03 ratchets for retired implicit and bulk consent writers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from specify_cli.sync.config import SyncConfig
from specify_cli.sync.consent import (
    ConsentAuthorityStatus,
    LegacyConsentMigrationRequiredError,
    backfill_uuid_consent_index,
    read_project_consent_decision,
)
from specify_cli.sync.routing import write_local_sync_enabled

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _runtime_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))


@pytest.mark.parametrize(
    "writer",
    [
        lambda config, root: config.set_project_consent(PROJECT_UUID, True),
        lambda config, root: config.set_project_consent_bulk({PROJECT_UUID: True}),
        lambda config, root: config.set_checkout_sync_enabled(root, True),
        lambda config, root: config.set_repository_sync_enabled("acme/project", True),
        lambda config, root: write_local_sync_enabled(root, True),
        lambda config, root: backfill_uuid_consent_index(),
    ],
)
def test_every_legacy_writer_fails_with_guidance_and_creates_no_grant(
    tmp_path: Path,
    writer: Callable[[SyncConfig, Path], object],
) -> None:
    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit"):
        writer(SyncConfig(), tmp_path)

    assert read_project_consent_decision(PROJECT_UUID).status is ConsentAuthorityStatus.ABSENT


def test_legacy_grant_records_are_read_only_diagnostics_not_authority() -> None:
    config = SyncConfig()
    config._save(
        {
            "sync": {
                "checkout_overrides": {"/no-such-checkout/project": {"enabled": True}},
                "repo_defaults": {"acme/project": {"enabled": True}},
                "project_consent": {PROJECT_UUID: {"enabled": True}},
            }
        }
    )

    assert config.get_project_consent(PROJECT_UUID) is True
    assert read_project_consent_decision(PROJECT_UUID).status is ConsentAuthorityStatus.ABSENT
