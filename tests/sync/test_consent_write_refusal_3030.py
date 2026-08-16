"""#3030 whole-config write refusal after machine consent-index retirement.

Raw legacy records remain readable diagnostics. Retired consent writers fail with
migration guidance, while unrelated whole-file setters still refuse an unreadable
document rather than rebuilding it and destroying bystander evidence.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from specify_cli.sync.config import SyncConfig

pytestmark = pytest.mark.fast

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"
BYSTANDER = "cccccccc-0000-0000-0000-000000000003"

#: A second bystander record of a different *type*, so the assertion is not limited to
#: the one table the consent writers happen to touch.  ``resolve()`` mirrors the
#: canonical key stored by ``SyncConfig`` on both Windows and POSIX.
BYSTANDER_CHECKOUT = Path("some/other/checkout").resolve()
_BYSTANDER_CHECKOUT_SERIALIZED = str(BYSTANDER_CHECKOUT).replace("\\", "\\\\")


def _posix_permission_oracle_unavailable(
    geteuid: Callable[[], int] | None = getattr(os, "geteuid", None),
) -> bool:
    """Return whether chmod-based unreadability cannot be observed faithfully."""
    return geteuid is None or geteuid() == 0


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
    config.set_project_consent(PROJECT_A, True)
    config.set_project_consent(BYSTANDER, True)
    config.set_checkout_sync_enabled(BYSTANDER_CHECKOUT, True)

    path = _index_path()
    text = path.read_text(encoding="utf-8")
    assert BYSTANDER in text, "precondition: the bystander's grant is on disk"
    assert _bystander_checkout_survives(text), "precondition: the bystander override is on disk"
    return path


def _bystander_checkout_survives(text: str) -> bool:
    """Recognize the planted override independently of TOML separator escaping."""
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return _BYSTANDER_CHECKOUT_SERIALIZED in text
    sync = parsed.get("sync", {})
    overrides = sync.get("checkout_overrides", {}) if isinstance(sync, dict) else {}
    if not isinstance(overrides, dict):
        return False
    for path, entry in overrides.items():
        parts = tuple(part for part in str(path).replace("\\", "/").split("/") if part)
        if parts[-3:] == ("some", "other", "checkout") and isinstance(entry, dict):
            return entry.get("enabled") is True
    return False


def _assert_bystanders_survive(path: Path, what: str) -> None:
    """The consequence, asserted on records nothing under test ever names."""
    text = path.read_text(encoding="utf-8") if path.exists() else "<the index file is gone>"
    assert BYSTANDER in text, f"{what} rebuilt the unreadable index from an empty document: an uninvolved project's grant is gone and cannot be recovered"
    assert _bystander_checkout_survives(text), f"{what} discarded an uninvolved checkout override"


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


@pytest.mark.skipif(
    _posix_permission_oracle_unavailable(),
    reason="requires a non-root POSIX permission oracle",
)
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


def _mark_bystander_unresolved(config: SyncConfig) -> None:
    """Use the stored key when readable, but still exercise refusal on a fault."""
    stored_paths = list(config.get_all_checkout_sync_records())
    config.mark_checkout_records_unresolved(
        stored_paths or [str(BYSTANDER_CHECKOUT)],
    )


def _writers() -> list[tuple[str, object]]:
    from specify_cli.sync.config import BackgroundDaemonPolicy

    return [
        ("set_project_consent", lambda c: c.set_project_consent(PROJECT_B, True)),
        ("set_project_consent_bulk", lambda c: c.set_project_consent_bulk({PROJECT_B: True})),
        ("set_checkout_sync_enabled", lambda c: c.set_checkout_sync_enabled(Path("/new/checkout"), True)),
        ("set_repository_sync_enabled", lambda c: c.set_repository_sync_enabled("acme/repo", True)),
        (
            "mark_checkout_records_unresolved",
            _mark_bystander_unresolved,
        ),
        ("set_server_url", lambda c: c.set_server_url("https://example.invalid")),
        ("set_max_queue_size", lambda c: c.set_max_queue_size(42)),
        ("set_background_daemon", lambda c: c.set_background_daemon(BackgroundDaemonPolicy.MANUAL)),
    ]


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
