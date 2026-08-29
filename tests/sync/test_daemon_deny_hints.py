"""WP03 acceptance tests for narrowing-only daemon deny hints."""

from __future__ import annotations

import json
from kernel.clock import UTC, datetime, timedelta
from pathlib import Path

import pytest

from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.deny_hints import (
    DenyHintAction,
    DenyHintStatus,
    deny_hint_path,
    enumerate_deny_hint_project_uuids,
    publish_deny_hint,
    read_deny_hint,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"
NOW = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _runtime_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))


def test_hint_schema_is_atomic_payload_free_and_cannot_represent_grant() -> None:
    hint = publish_deny_hint(
        PROJECT_UUID,
        action=DenyHintAction.DENY,
        authority_generation=4,
        reason_category="absent",
        now=NOW,
    )
    document = json.loads(deny_hint_path(PROJECT_UUID).read_text(encoding="utf-8"))

    assert set(document) == {
        "action",
        "authority_generation",
        "checksum",
        "expires_at",
        "layout_version",
        "reason_category",
    }
    assert hint.action is DenyHintAction.DENY
    assert "grant" not in json.dumps(document).lower()
    with pytest.raises(ValueError):
        DenyHintAction("grant")


def test_only_current_integrity_checked_denial_can_skip_authority() -> None:
    publish_deny_hint(
        PROJECT_UUID,
        action=DenyHintAction.REVOKE,
        authority_generation=2,
        reason_category="explicit_opt_out",
        now=NOW,
    )

    current = read_deny_hint(PROJECT_UUID, expected_generation=2, now=NOW)
    generation_stale = read_deny_hint(PROJECT_UUID, expected_generation=3, now=NOW)
    expired = read_deny_hint(
        PROJECT_UUID,
        expected_generation=2,
        now=NOW + timedelta(hours=1),
    )

    assert current.status is DenyHintStatus.VALID_DENY
    assert current.requires_authority is False
    assert generation_stale.status is DenyHintStatus.STALE_DENY
    assert generation_stale.requires_authority is True
    assert "stale" in generation_stale.diagnostic
    assert expired.status is DenyHintStatus.STALE_DENY
    assert expired.requires_authority is True


def test_missing_malformed_and_grant_valued_hints_require_authority() -> None:
    missing = read_deny_hint(PROJECT_UUID, expected_generation=1, now=NOW)
    assert missing.status is DenyHintStatus.AUTHORITY_REQUIRED

    path = deny_hint_path(PROJECT_UUID)
    path.parent.mkdir(parents=True)
    path.write_text("not json", encoding="utf-8")
    assert read_deny_hint(PROJECT_UUID, expected_generation=1, now=NOW).requires_authority

    path.write_text(
        json.dumps(
            {
                "action": "grant",
                "authority_generation": 1,
                "checksum": "forged",
                "expires_at": (NOW + timedelta(minutes=1)).isoformat(),
                "layout_version": 1,
                "reason_category": "absent",
            }
        ),
        encoding="utf-8",
    )
    assert read_deny_hint(PROJECT_UUID, expected_generation=1, now=NOW).requires_authority


def test_opt_out_publishes_after_commit_and_opt_in_removes_after_commit() -> None:
    refusal = record_project_opt_out(PROJECT_UUID, actor="operator:alice")
    assert (
        read_deny_hint(
            PROJECT_UUID,
            expected_generation=refusal.generation,
        ).status
        is DenyHintStatus.VALID_DENY
    )

    record_project_opt_in(PROJECT_UUID, actor="operator:alice")
    assert not deny_hint_path(PROJECT_UUID).exists()


def test_enumeration_never_creates_project_stores_or_decisions() -> None:
    publish_deny_hint(
        PROJECT_UUID,
        action=DenyHintAction.DENY,
        authority_generation=1,
        reason_category="absent",
        now=NOW,
    )
    runtime = deny_hint_path(PROJECT_UUID).parents[2]

    discovered = enumerate_deny_hint_project_uuids()

    assert tuple(str(value) for value in discovered) == (PROJECT_UUID,)
    assert not (runtime / "projects" / PROJECT_UUID / "sync" / "sync.db").exists()
