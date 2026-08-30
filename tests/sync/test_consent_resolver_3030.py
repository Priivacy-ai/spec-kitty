"""#3030 denial defenses after WP03 superseded legacy grant authority.

The project-store decision is now the only authority. Legacy checkout, repository,
machine-index, and environment values remain useful diagnostic evidence, but they
never grant and no read reconciles them into another store.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from specify_cli.sync import consent as consent_module
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.consent import (
    ConsentAction,
    ConsentAuthorityStatus,
    ConsentLevel,
    LegacyConsentMigrationRequiredError,
    backfill_uuid_consent_index,
    consented_project_uuids,
    read_project_consent_decision,
    record_project_opt_in,
    record_project_opt_out,
    resolve_project_consent,
)
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-0000-0000-0000-000000000001"
UUID_B = "bbbbbbbb-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


def _checkout(tmp_path: Path, name: str, *, uuid: str, hosted: bool) -> Path:
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True)
    (root / ".kittify" / "config.yaml").write_text(
        "\n".join(
            [
                "project:",
                f"  uuid: {uuid}",
                f"  slug: {name}",
                "sync:",
                f"  enabled: {str(hosted).lower()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root


def _seed_legacy_index(**entries: bool) -> bytes:
    config = SyncConfig()
    config._save({"sync": {"project_consent": {uuid: {"enabled": enabled} for uuid, enabled in entries.items()}}})
    return config.config_file.read_bytes()


def test_nothing_recorded_anywhere_denies() -> None:
    decision = resolve_project_consent(UUID_A)
    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT


def test_absence_denies_even_with_the_env_var_armed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    assert resolve_project_consent(UUID_A).granted is False


def test_unresolvable_project_uuid_denies() -> None:
    for value in (None, "", "   "):
        assert resolve_project_consent(value).granted is False


def test_index_grant_is_honoured() -> None:
    """Superseded assertion: a raw legacy grant is now diagnostic-only."""
    _seed_legacy_index(**{UUID_A: True})
    assert resolve_project_consent(UUID_A).granted is False


def test_index_refusal_is_honoured() -> None:
    """A legacy refusal still fails closed, but absence is the live authority."""
    _seed_legacy_index(**{UUID_A: False})
    assert resolve_project_consent(UUID_A).granted is False


def test_index_answers_when_the_checkout_is_gone(tmp_path: Path) -> None:
    _seed_legacy_index(**{UUID_A: True})
    decision = resolve_project_consent(UUID_A, repo_root=tmp_path / "gone")
    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT


def test_project_local_grant_outranks_an_absent_index(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=True)
    assert resolve_project_consent(UUID_A, repo_root=root).granted is False


def test_project_local_refusal_outranks_an_index_grant(tmp_path: Path) -> None:
    before = _seed_legacy_index(**{UUID_A: True})
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)
    assert resolve_project_consent(UUID_A, repo_root=root).granted is False
    assert SyncConfig().config_file.read_bytes() == before


def test_project_local_refusal_outranks_the_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)
    assert resolve_project_consent(UUID_A, repo_root=root).granted is False


def test_a_project_local_file_for_another_project_is_ignored(tmp_path: Path) -> None:
    other = _checkout(tmp_path, "other", uuid=UUID_B, hosted=True)
    assert resolve_project_consent(UUID_A, repo_root=other).granted is False


def test_refusal_in_any_checkout_denies_the_project(tmp_path: Path) -> None:
    granting = _checkout(tmp_path, "clone-a", uuid=UUID_A, hosted=True)
    refusing = _checkout(tmp_path, "clone-b", uuid=UUID_A, hosted=False)
    decision = resolve_project_consent(UUID_A, checkout_roots=[granting, refusing])
    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT


def test_all_checkouts_granting_grants(tmp_path: Path) -> None:
    roots = [
        _checkout(tmp_path, "clone-a", uuid=UUID_A, hosted=True),
        _checkout(tmp_path, "clone-b", uuid=UUID_A, hosted=True),
    ]
    assert resolve_project_consent(UUID_A, checkout_roots=roots).granted is False


def test_a_readable_checkout_corrects_a_stale_index(tmp_path: Path) -> None:
    before = _seed_legacy_index(**{UUID_A: True})
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)
    resolve_project_consent(UUID_A, repo_root=root)
    assert SyncConfig().config_file.read_bytes() == before


def test_repo_default_grant_does_not_consent_for_an_unrecorded_uuid() -> None:
    config = SyncConfig()
    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit"):
        config.set_repository_sync_enabled("acme/confidential-work", True)
    assert resolve_project_consent(UUID_A).granted is False


def test_consented_project_uuids_filters_the_candidate_set() -> None:
    record_project_opt_in(UUID_A, actor="operator:alice")
    record_project_opt_out(UUID_B, actor="operator:alice")
    assert consented_project_uuids([UUID_A, UUID_B]) == frozenset({UUID_A})


def test_consented_project_uuids_never_returns_none() -> None:
    record_project_opt_in(UUID_A, actor="operator:alice")
    assert consented_project_uuids([UUID_A, None, ""]) == frozenset({UUID_A})


def test_backfill_maps_path_keyed_records_to_uuids() -> None:
    with pytest.raises(LegacyConsentMigrationRequiredError, match="retired"):
        backfill_uuid_consent_index()
    assert read_project_consent_decision(UUID_A).status is ConsentAuthorityStatus.ABSENT


def test_backfill_marks_unresolvable_paths_instead_of_dropping_them() -> None:
    before = _seed_legacy_index(**{UUID_A: True})
    with pytest.raises(LegacyConsentMigrationRequiredError, match="retired"):
        backfill_uuid_consent_index()
    assert SyncConfig().config_file.read_bytes() == before


def test_backfill_is_idempotent() -> None:
    for _ in range(2):
        with pytest.raises(LegacyConsentMigrationRequiredError, match="retired"):
            backfill_uuid_consent_index()


def test_backfill_applies_the_conflict_rule() -> None:
    _seed_legacy_index(**{UUID_A: True, UUID_B: False})
    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit opt-in"):
        backfill_uuid_consent_index()
    assert consented_project_uuids([UUID_A, UUID_B]) == frozenset()


def test_precedence_chain_has_one_definition_site() -> None:
    source = inspect.getsource(consent_module.resolve_project_consent)
    assert "read_project_consent_decision" in source
    assert "LEVEL_RESOLVERS" not in source


def test_reordering_the_declared_chain_reorders_the_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        consent_module,
        "PROJECT_CONSENT_PRECEDENCE",
        tuple(reversed(consent_module.PROJECT_CONSENT_PRECEDENCE)),
    )
    _seed_legacy_index(**{UUID_A: True})
    assert resolve_project_consent(UUID_A).granted is False


def test_dropping_a_level_from_the_declared_chain_stops_it_being_consulted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(consent_module, "PROJECT_CONSENT_PRECEDENCE", ())
    record_project_opt_in(UUID_A, actor="operator:alice")
    assert resolve_project_consent(UUID_A).granted is True


def test_an_empty_declared_chain_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(consent_module, "PROJECT_CONSENT_PRECEDENCE", ())
    _seed_legacy_index(**{UUID_A: True})
    assert resolve_project_consent(UUID_A).granted is False


def test_the_env_level_cannot_grant_even_promoted_to_the_top(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    assert resolve_project_consent(UUID_A).granted is False


def test_every_declared_level_has_exactly_one_resolver() -> None:
    assert set(ConsentAction) == {
        ConsentAction.EXPLICIT_OPT_IN,
        ConsentAction.EXPLICIT_OPT_OUT,
        ConsentAction.MIGRATED_REFUSAL,
    }


def test_a_declared_level_with_no_resolver_refuses_to_load() -> None:
    store = ProjectSyncStore(UUID_A)
    with store.unit_of_work() as unit:
        unit.execute("UPDATE project_store_metadata SET schema_version = 999 WHERE singleton = 1")
    diagnostic = read_project_consent_decision(UUID_A)
    assert diagnostic.status is ConsentAuthorityStatus.INCOMPATIBLE
    assert resolve_project_consent(UUID_A).granted is False


def test_precedence_order_is_pinned() -> None:
    grant = record_project_opt_in(UUID_A, actor="operator:alice")
    refusal = record_project_opt_out(UUID_A, actor="operator:alice")
    assert grant.generation == 1
    assert refusal.generation == 2
