"""WP03 acceptance tests for the sole project-store consent authority."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from specify_cli.sync.config import SyncConfig
from specify_cli.sync.consent import (
    ConsentAction,
    ConsentAuthorityStatus,
    LegacyConsentMigrationRequiredError,
    import_legacy_refusal,
    read_project_consent_decision,
    record_project_opt_in,
    record_project_opt_out,
    resolve_project_consent,
    set_project_consent,
)
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.routing import disable_checkout_sync, enable_checkout_sync

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
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://app.spec-kitty.ai")


def _checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "checkout"
    (root / ".git").mkdir(parents=True)
    (root / ".kittify").mkdir()
    (root / ".kittify" / "config.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  uuid: {PROJECT_UUID}",
                "  slug: consent-test",
                "  node_id: node12345678",
                "  build_id: build-123",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(root))
    return root


@pytest.mark.parametrize(
    ("legacy_input", "seed"),
    [
        ("checkout override", lambda config: config._save({"sync": {"checkout_overrides": {"/no-such-checkout/project": {"enabled": True}}}})),
        ("repository default", lambda config: config._save({"sync": {"repo_defaults": {"acme/project": {"enabled": True}}}})),
        ("machine UUID index", lambda config: config._save({"sync": {"project_consent": {PROJECT_UUID: {"enabled": True}}}})),
        ("login and target", lambda config: config._save({"sync": {"server_url": "https://app.spec-kitty.ai"}, "auth": {"logged_in": True}})),
    ],
)
def test_implicit_grant_inputs_never_create_authority(
    legacy_input: str,
    seed: Callable[[SyncConfig], None],
) -> None:
    config = SyncConfig()
    seed(config)

    diagnostic = read_project_consent_decision(PROJECT_UUID)
    verdict = resolve_project_consent(PROJECT_UUID)

    assert diagnostic.status is ConsentAuthorityStatus.ABSENT, legacy_input
    assert verdict.granted is False, legacy_input


def test_explicit_writer_is_versioned_attributable_and_idempotent() -> None:
    first = record_project_opt_in(PROJECT_UUID, actor="operator:alice")
    retry = record_project_opt_in(PROJECT_UUID, actor="operator:alice")

    assert first == retry
    assert first.action is ConsentAction.EXPLICIT_OPT_IN
    assert first.actor == "operator:alice"
    assert first.generation == 1
    assert first.decided_at.tzinfo is not None
    assert first.schema_version == 1
    assert first.idempotency_identity == (f"consent:{PROJECT_UUID}:1:explicit_opt_in")
    assert resolve_project_consent(PROJECT_UUID).granted is True

    refusal = record_project_opt_out(PROJECT_UUID, actor="operator:alice")
    assert refusal.generation == 2
    assert refusal.action is ConsentAction.EXPLICIT_OPT_OUT
    assert resolve_project_consent(PROJECT_UUID).granted is False


def test_migration_imports_refusal_but_never_a_grant() -> None:
    refusal = import_legacy_refusal(PROJECT_UUID, actor="migration:legacy-index")
    assert refusal.generation == 1
    assert refusal.action is ConsentAction.MIGRATED_REFUSAL
    assert resolve_project_consent(PROJECT_UUID).granted is False

    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit opt-in"):
        set_project_consent(PROJECT_UUID, True)

    assert read_project_consent_decision(PROJECT_UUID).generation == 1


def test_public_opt_in_persists_offline_while_kill_switch_is_off(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _checkout(tmp_path, monkeypatch)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")

    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("local opt-in must not perform network I/O")

    monkeypatch.setattr("httpx.Client.request", reject_network)

    first = enable_checkout_sync(root, actor="operator:alice")
    retry = enable_checkout_sync(root, actor="operator:alice")
    diagnostic = read_project_consent_decision(PROJECT_UUID)

    assert first.effective_sync_enabled is True
    assert retry.effective_sync_enabled is True
    assert diagnostic.status is ConsentAuthorityStatus.GRANTED
    assert diagnostic.record is not None
    assert diagnostic.record.generation == 1
    assert diagnostic.record.actor == "operator:alice"


def test_public_opt_out_seals_retry_is_idempotent_and_reopt_in_advances(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _checkout(tmp_path, monkeypatch)
    enable_checkout_sync(root, actor="operator:alice")

    first_refusal = disable_checkout_sync(root, actor="operator:alice")
    retry_refusal = disable_checkout_sync(root, actor="operator:alice")
    regrant = enable_checkout_sync(root, actor="operator:alice")

    assert first_refusal.decision is not None
    assert retry_refusal.decision == first_refusal.decision
    assert first_refusal.decision.generation == 2
    assert first_refusal.routing.effective_sync_enabled is False
    assert regrant.effective_sync_enabled is True
    assert read_project_consent_decision(PROJECT_UUID).generation == 3

    store = ProjectSyncStore(PROJECT_UUID)
    with store.unit_of_work() as unit:
        rows = unit.execute(
            "SELECT state, consent_generation FROM consent_epochs WHERE project_uuid = ? ORDER BY epoch_id",
            (PROJECT_UUID,),
        ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("sealed", 1),
        ("sealed", None),
        ("eligible", 3),
    ]
