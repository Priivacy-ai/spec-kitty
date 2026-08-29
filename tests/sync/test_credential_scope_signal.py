"""Credential parsing as a queue-scope signal (WP01 / IC-01, FR-004 / FR-009).

The #3293 consent-ledger cutover narrowed
``specify_cli.sync.queue.read_queue_scope_from_credentials`` to a JSON-only read
of an explicit ``queue_scope`` field. The supported on-disk credential form (a
TOML file with ``[user]`` / ``[server]`` tables) stopped yielding a scope, so
the setup-plan hosted-sync path once treated a genuinely-authenticated host as
unauthenticated (regression #3425, research.md Decision 1 "credential half").
Setup-plan authentication now comes exclusively from the canonical
``TokenManager.session_assessment``; this parser supplies queue identity only.

These tests pin the remaining queue-scope contract:

* T002 — the restored parser yields the canonical ``server|user|team`` piped
  scope for a TOML credentials file, still returns ``None`` for absent/garbage
  input, and preserves the explicit-JSON ``queue_scope`` path.
* T003 — parsing materialises no physical queue DB and has no hosted side effect.
* T004 — **physical-store invariance (INV-6):** restoring credential parsing does
  NOT change which physical store a live write lands in. The authoritative store
  path (``resolve_sync_target(...).queue_db_path``) is derived from the passed
  identity via ``_derive_queue_scope`` and is inert to the credential read — this
  is the guard against a C-003 / FR-009 revert of #3293's ProjectSyncStore
  selection.

Isolation is mandatory: every test pins BOTH ``SPEC_KITTY_HOME`` **and** ``HOME``
(plus ``XDG_*`` / ``APPDATA``) to a throwaway temp root. This dev box's real
``~/.spec-kitty`` is a live legacy root (plan.md:131-133); pinning only ``HOME``
is insufficient because scope/credential paths key off ``SPEC_KITTY_HOME``. No
network, no ambient auth, no real credentials file.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


@pytest.fixture
def isolated_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Pin BOTH ``SPEC_KITTY_HOME`` and ``HOME`` (+ platform equivalents) to tmp.

    Scope/credential resolution keys off ``SPEC_KITTY_HOME``
    (``paths.get_runtime_root``); ``HOME`` / ``USERPROFILE`` catch any
    ``Path.home()``-relative helper. ``SPEC_KITTY_SAAS_URL`` and the encrypted
    session read are neutralised so the resolver stays deterministic and
    network-free. ``monkeypatch.setenv`` restores every var (incl.
    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` set inside a test) on teardown, so gate
    short-circuit state never leaks to sibling tests.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    # Neutralise the encrypted-session scope read so the gate/resolver depend
    # only on the on-disk credentials under test (no ambient auth).
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: None,
    )
    monkeypatch.setattr(
        "specify_cli.sync.target_authority.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: None,
    )
    return tmp_path


def _credentials_path(root: Path) -> Path:
    # ``SPEC_KITTY_HOME`` is used verbatim as the runtime base (not suffixed);
    # see ``paths.windows_paths.get_runtime_root``.
    return root / "credentials"


def _write_toml_credentials(
    root: Path,
    *,
    username: str = "tester@example.com",
    url: str = "https://spec-kitty-dev.fly.dev",
    team_slug: str = "t-private",
) -> None:
    """Write the supported on-disk credential form (TOML ``[user]``/``[server]``)."""
    _credentials_path(root).write_text(
        f'[user]\nusername = "{username}"\nteam_slug = "{team_slug}"\n'
        f'[server]\nurl = "{url}"\n',
        encoding="utf-8",
    )


def _write_json_credentials(root: Path, *, queue_scope: str) -> None:
    """Write the explicit-JSON credential form (#3293's ``queue_scope`` field)."""
    _credentials_path(root).write_text(
        f'{{"queue_scope": "{queue_scope}"}}',
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# T002 — restored parser yields an auth signal (unit level)
# ---------------------------------------------------------------------------


def test_toml_credentials_yield_piped_scope_signal(isolated_home: Path) -> None:
    """A supported TOML credentials file yields the canonical piped scope.

    ``preflight._read_scope_identity_local_only`` splits this value on ``"|"``
    expecting ``server|user|team`` (preflight.py:479-484), so the restored parse
    must produce exactly that order.
    """
    from specify_cli.sync.queue import read_queue_scope_from_credentials

    _write_toml_credentials(
        isolated_home,
        username="tester@example.com",
        url="https://spec-kitty-dev.fly.dev",
        team_slug="t-private",
    )

    scope = read_queue_scope_from_credentials()

    assert scope == "https://spec-kitty-dev.fly.dev|tester@example.com|t-private"
    parts = scope.split("|")
    assert len(parts) == 3
    assert parts[1] == "tester@example.com"
    assert parts[2] == "t-private"


def test_json_explicit_queue_scope_still_returned(isolated_home: Path) -> None:
    """#3293's explicit-JSON ``queue_scope`` path is preserved (no regression)."""
    from specify_cli.sync.queue import read_queue_scope_from_credentials

    _write_json_credentials(isolated_home, queue_scope="explicit-scope-token")

    assert read_queue_scope_from_credentials() == "explicit-scope-token"


def test_absent_credentials_yield_none(isolated_home: Path) -> None:
    from specify_cli.sync.queue import read_queue_scope_from_credentials

    assert not _credentials_path(isolated_home).exists()
    assert read_queue_scope_from_credentials() is None


def test_garbage_credentials_yield_none_not_raise(isolated_home: Path) -> None:
    """Corrupt/partial credentials return ``None`` defensively, never raise."""
    from specify_cli.sync.queue import read_queue_scope_from_credentials

    _credentials_path(isolated_home).write_text("{not json and [not toml", encoding="utf-8")
    assert read_queue_scope_from_credentials() is None

    # Partial TOML (missing username / url) is incomplete → no false positive.
    _credentials_path(isolated_home).write_text('[server]\nurl = "https://x"\n', encoding="utf-8")
    assert read_queue_scope_from_credentials() is None


# ---------------------------------------------------------------------------
# T003 — queue-scope parsing has no physical-store side effect
# ---------------------------------------------------------------------------


def test_parser_materialises_no_queue_db(isolated_home: Path) -> None:
    """T003: reading the queue-scope signal touches no physical store."""
    from specify_cli.sync.queue import read_queue_scope_from_credentials

    _write_toml_credentials(isolated_home)
    assert read_queue_scope_from_credentials() is not None

    created_dbs = list(isolated_home.rglob("queue*.db"))
    assert created_dbs == [], f"parser must not materialise a queue DB, found: {created_dbs}"


# ---------------------------------------------------------------------------
# T004 — physical-store invariance (INV-6 / FR-009 / C-003 revert guard)
# ---------------------------------------------------------------------------


def test_authoritative_store_path_is_inert_to_credential_parse(
    isolated_home: Path,
) -> None:
    """INV-6: restoring credential parsing must NOT steer the authoritative store.

    ``resolve_sync_target(...).queue_db_path`` is the ProjectSyncStore-owned live
    -write selection. It is derived from the *passed* identity via
    ``_derive_queue_scope`` (target_authority.py:465-466), which never reads
    credentials. So the resolved DB path must be byte-for-byte identical whether
    the credentials file is absent, a TOML form (now parsed), or an explicit-JSON
    form. If a future change let the credential read steer the physical store,
    this assertion fails loudly — that is the whole point of the guard.
    """
    from specify_cli.sync.target_authority import resolve_sync_target

    def _resolved_path() -> Path:
        # Coerce at the typed boundary: ``specify_cli.*`` is ``Any`` to mypy
        # under follow_imports=skip, so pin the ``Path`` return explicitly.
        return Path(
            resolve_sync_target(
                user_id="tester@example.com", team_slug="t-private"
            ).queue_db_path
        )

    creds = _credentials_path(isolated_home)

    # Arm 1: no credentials on disk.
    if creds.exists():
        creds.unlink()
    baseline = _resolved_path()

    # Arm 2: TOML credentials (the form the restored parser now recognises).
    _write_toml_credentials(isolated_home)
    with_toml = _resolved_path()

    # Arm 3: explicit-JSON credentials.
    _write_json_credentials(isolated_home, queue_scope="explicit-scope-token")
    with_json = _resolved_path()

    assert with_toml == baseline, (
        "restored credential parse changed the authoritative store path — "
        "C-003/FR-009 revert of ProjectSyncStore selection"
    )
    assert with_json == baseline


def test_readonly_preflight_store_uses_derived_scope_not_raw_credential(
    isolated_home: Path,
) -> None:
    """The preflight's read-only DB path derives its scope from the resolver.

    ``_resolve_queue_db_path_readonly`` routes credential *identity* through
    ``resolve_sync_target(...).derived_queue_scope`` → ``scope_db_path`` — it never
    feeds the raw credential string into ``scope_db_path``. So the reported DB path
    equals the authoritative scoped path for the same identity, proving the
    credential read is an auth/identity signal, not a physical-store selector.
    """
    from specify_cli.sync import preflight
    from specify_cli.sync.queue import scope_db_path
    from specify_cli.sync.target_authority import resolve_sync_target

    _write_toml_credentials(
        isolated_home, username="tester@example.com", team_slug="t-private"
    )

    reported = preflight._resolve_queue_db_path_readonly()
    authoritative_scope = resolve_sync_target(
        user_id="tester@example.com", team_slug="t-private"
    ).derived_queue_scope

    assert reported == Path(scope_db_path(authoritative_scope))
