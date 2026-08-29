"""Exact, auth-derived remote admission audience acceptance tests."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from specify_cli.sync.target_authority import (
    AdmissionAudience,
    OverrideMode,
    QueueScopeStatus,
    ResolvedSyncTarget,
    build_admission_audience,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


def _resolved(url: str, tmp_path: Path) -> ResolvedSyncTarget:
    return ResolvedSyncTarget(
        configured_server_url=url,
        env_server_url=None,
        override_mode=OverrideMode.NONE,
        resolved_server_url=url,
        user_id="untrusted-display@example.test",
        team_slug="untrusted-selector",
        derived_queue_scope="irrelevant",
        queue_db_path=tmp_path / "irrelevant.db",
        active_queue_scope_status=QueueScopeStatus.ABSENT,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("HTTPS://APP.SPEC-KITTY.AI:443/api/v1/", "https://app.spec-kitty.ai"),
        ("http://localhost:8000/sync/", "http://localhost:8000"),
        ("http://127.0.0.1:80/anything", "http://127.0.0.1"),
    ),
)
def test_audience_normalizes_origin_and_ignores_route_path(
    raw: str,
    expected: str,
    tmp_path: Path,
) -> None:
    audience = build_admission_audience(
        _resolved(raw, tmp_path),
        account_identity="account-17",
        private_teamspace_id="teamspace-23",
        project_uuid=PROJECT,
        configuration_generation=1,
    )

    assert audience.normalized_server_origin == expected
    assert audience.account_identity == "account-17"
    assert audience.private_teamspace_id == "teamspace-23"
    assert audience.project_uuid.storage_token == PROJECT


def test_every_tuple_member_changes_remote_audience_without_a_token_surface(tmp_path: Path) -> None:
    base = build_admission_audience(
        _resolved("https://one.example", tmp_path),
        account_identity="account-a",
        private_teamspace_id="team-a",
        project_uuid=PROJECT,
        configuration_generation=4,
    )
    variants = (
        build_admission_audience(
            _resolved("https://two.example", tmp_path),
            account_identity="account-a",
            private_teamspace_id="team-a",
            project_uuid=PROJECT,
            configuration_generation=4,
        ),
        build_admission_audience(
            _resolved("https://one.example", tmp_path),
            account_identity="account-b",
            private_teamspace_id="team-a",
            project_uuid=PROJECT,
            configuration_generation=4,
        ),
        build_admission_audience(
            _resolved("https://one.example", tmp_path),
            account_identity="account-a",
            private_teamspace_id="team-b",
            project_uuid=PROJECT,
            configuration_generation=4,
        ),
        build_admission_audience(
            _resolved("https://one.example", tmp_path),
            account_identity="account-a",
            private_teamspace_id="team-a",
            project_uuid="aaaaaaaa-0000-0000-0000-000000000002",
            configuration_generation=4,
        ),
        build_admission_audience(
            _resolved("https://one.example", tmp_path),
            account_identity="account-a",
            private_teamspace_id="team-a",
            project_uuid=PROJECT,
            configuration_generation=5,
        ),
    )

    assert all(item != base for item in variants)
    assert isinstance(base, AdmissionAudience)
    parameters = inspect.signature(build_admission_audience).parameters
    assert "token" not in parameters
    assert "team_slug" not in parameters
    assert "repository_slug" not in parameters


def test_diagnostics_are_pseudonymous_and_payload_free(tmp_path: Path) -> None:
    audience = build_admission_audience(
        _resolved("https://private.example/secret-route", tmp_path),
        account_identity="account-secret",
        private_teamspace_id="teamspace-secret",
        project_uuid=PROJECT,
        configuration_generation=1,
    )

    rendered = repr(audience.to_diagnostics_dict())
    assert "account-secret" not in rendered
    assert "teamspace-secret" not in rendered
    assert "secret-route" not in rendered
    assert audience.to_diagnostics_dict()["category"] == "project_sync_admission_audience"
