"""#3030 whole-config write refusal after machine consent-index retirement.

Raw legacy records remain readable diagnostics. Retired consent writers fail with
migration guidance, while unrelated whole-file setters still refuse an unreadable
document rather than rebuilding it and destroying bystander evidence.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from specify_cli.sync.config import (
    BackgroundDaemonPolicy,
    ConfigNotReadableError,
    SyncConfig,
)
from specify_cli.sync.consent import (
    ConsentAuthorityStatus,
    LegacyConsentMigrationRequiredError,
    backfill_uuid_consent_index,
    read_project_consent_decision,
    record_project_opt_in,
    record_project_opt_out,
    resolve_project_consent,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"
BYSTANDER = "cccccccc-0000-0000-0000-000000000003"
BYSTANDER_CHECKOUT = "/some/other/checkout"


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "home"
    root.mkdir(parents=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(root))
    monkeypatch.setenv("HOME", str(root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    return root


def _index_path() -> Path:
    return SyncConfig().config_file


def _plant_records() -> Path:
    config = SyncConfig()
    config._save(
        {
            "sync": {
                "project_consent": {
                    PROJECT_A: {"enabled": True},
                    BYSTANDER: {"enabled": True},
                },
                "checkout_overrides": {BYSTANDER_CHECKOUT: {"enabled": True}},
            }
        }
    )
    path = _index_path()
    text = path.read_text(encoding="utf-8")
    assert BYSTANDER in text
    assert BYSTANDER_CHECKOUT in text
    return path


def _corrupt_keeping_the_records(path: Path) -> bytes:
    before = path.read_bytes() + b"\n[sync\nbroken = "
    path.write_bytes(before)
    assert BYSTANDER.encode() in before
    return before


def _assert_bystanders_survive(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert BYSTANDER in text
    assert BYSTANDER_CHECKOUT in text


def test_recording_consent_over_an_unreadable_index_keeps_the_other_records() -> None:
    path = _plant_records()
    before = _corrupt_keeping_the_records(path)
    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit"):
        SyncConfig().set_project_consent(PROJECT_B, True)
    assert path.read_bytes() == before


def test_the_refusal_names_the_file_and_carries_the_fault() -> None:
    path = _plant_records()
    _corrupt_keeping_the_records(path)
    with pytest.raises(ConfigNotReadableError) as raised:
        SyncConfig().set_server_url("https://app.spec-kitty.ai")
    assert str(path) in str(raised.value)
    assert raised.value.fault is not None


def test_a_chmod_000_index_is_refused_rather_than_replaced() -> None:
    if os.name == "nt":
        pytest.skip("POSIX mode-bit assertion")
    path = _plant_records()
    before = path.read_bytes()
    path.chmod(0o000)
    try:
        with pytest.raises(ConfigNotReadableError):
            SyncConfig().set_server_url("https://app.spec-kitty.ai")
    finally:
        path.chmod(0o644)
    assert path.read_bytes() == before


def test_recording_consent_over_a_readable_index_still_writes() -> None:
    path = _plant_records()
    before = path.read_bytes()
    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit"):
        SyncConfig().set_project_consent(PROJECT_B, True)
    assert path.read_bytes() == before


def test_a_wholly_absent_index_still_accepts_the_first_grant() -> None:
    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit"):
        SyncConfig().set_project_consent(PROJECT_A, True)
    assert read_project_consent_decision(PROJECT_A).status is ConsentAuthorityStatus.ABSENT


def test_an_empty_index_file_still_accepts_a_grant() -> None:
    path = _index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    with pytest.raises(LegacyConsentMigrationRequiredError, match="explicit"):
        SyncConfig().set_project_consent(PROJECT_A, True)
    assert path.read_text(encoding="utf-8") == ""


Setter = Callable[[SyncConfig], object]


def _set_project(config: SyncConfig) -> None:
    config.set_project_consent(PROJECT_B, True)


def _set_project_bulk(config: SyncConfig) -> None:
    config.set_project_consent_bulk({PROJECT_B: True})


def _set_checkout(config: SyncConfig) -> None:
    config.set_checkout_sync_enabled(Path("/new/checkout"), True)


def _set_repository(config: SyncConfig) -> None:
    config.set_repository_sync_enabled("acme/new", True)


def _mark_unresolved(config: SyncConfig) -> None:
    config.mark_checkout_records_unresolved([BYSTANDER_CHECKOUT])


def _set_server(config: SyncConfig) -> None:
    config.set_server_url("https://app.spec-kitty.ai")


def _set_queue(config: SyncConfig) -> None:
    config.set_max_queue_size(42)


def _set_daemon(config: SyncConfig) -> None:
    config.set_background_daemon(BackgroundDaemonPolicy.MANUAL)


_SETTERS: list[tuple[str, Setter, str]] = [
    ("set_project_consent", _set_project, "retired"),
    ("set_project_consent_bulk", _set_project_bulk, "retired"),
    ("set_checkout_sync_enabled", _set_checkout, "retired"),
    ("set_repository_sync_enabled", _set_repository, "retired"),
    ("mark_checkout_records_unresolved", _mark_unresolved, "config-writer"),
    ("set_server_url", _set_server, "config-writer"),
    ("set_max_queue_size", _set_queue, "config-writer"),
    ("set_background_daemon", _set_daemon, "config-writer"),
]
_WRITER_IDS = [row[0] for row in _SETTERS]


@pytest.mark.parametrize(
    ("_name", "setter", "kind"),
    _SETTERS,
    ids=_WRITER_IDS,
)
def test_no_setter_rebuilds_the_index_from_an_empty_document(
    _name: str,
    setter: Setter,
    kind: str,
) -> None:
    path = _plant_records()
    before = _corrupt_keeping_the_records(path)
    if kind == "retired":
        with pytest.raises(LegacyConsentMigrationRequiredError):
            setter(SyncConfig())
    elif kind == "config-writer":
        with pytest.raises(ConfigNotReadableError):
            setter(SyncConfig())
    else:
        setter(SyncConfig())
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("_name", "setter", "kind"),
    _SETTERS,
    ids=_WRITER_IDS,
)
def test_every_setter_still_writes_a_readable_index(
    _name: str,
    setter: Setter,
    kind: str,
) -> None:
    path = _plant_records()
    before = path.read_bytes()
    if kind == "retired":
        with pytest.raises(LegacyConsentMigrationRequiredError):
            setter(SyncConfig())
        assert path.read_bytes() == before
    else:
        setter(SyncConfig())
        _assert_bystanders_survive(path)


def test_resolving_consent_does_not_rewrite_an_unreadable_index() -> None:
    path = _plant_records()
    before = _corrupt_keeping_the_records(path)
    assert resolve_project_consent(PROJECT_A).granted is False
    assert path.read_bytes() == before


def test_resolving_consent_still_reconciles_a_readable_index() -> None:
    path = _plant_records()
    before = path.read_bytes()
    assert resolve_project_consent(PROJECT_A).granted is False
    assert path.read_bytes() == before


def test_a_refused_reconciliation_does_not_break_the_decision() -> None:
    path = _plant_records()
    before = _corrupt_keeping_the_records(path)
    record = record_project_opt_in(PROJECT_A, actor="operator:alice")
    assert resolve_project_consent(PROJECT_A).granted is True
    assert record.generation == 1
    assert path.read_bytes() == before


@pytest.mark.parametrize("command", ["opt-in", "opt-out", "server"])
def test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli(
    command: str,
) -> None:
    path = _plant_records()
    before = _corrupt_keeping_the_records(path)
    if command == "opt-in":
        record_project_opt_in(PROJECT_A, actor="operator:alice")
    elif command == "opt-out":
        record_project_opt_out(PROJECT_A, actor="operator:alice")
    else:
        with pytest.raises(ConfigNotReadableError):
            SyncConfig().set_server_url("https://app.spec-kitty.ai")
    assert path.read_bytes() == before


def test_the_backfill_writes_nothing_over_an_unreadable_index() -> None:
    path = _plant_records()
    before = _corrupt_keeping_the_records(path)
    with pytest.raises(LegacyConsentMigrationRequiredError, match="retired"):
        backfill_uuid_consent_index()
    assert path.read_bytes() == before
