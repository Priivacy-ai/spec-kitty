"""Resolver-level acceptance tests for the canonical sync Target Authority (WP01).

These pin contract §1's *Required tests* and SC-008 at the resolver level as
observable state on the returned :class:`ResolvedSyncTarget` (NFR-001 — assert
state, not call order):

* all eight contract §1 fields populated;
* env/config disagreement can never split the resolved target from the derived
  queue scope (SC-008);
* a stale ``active_queue_scope`` is reported as a diagnostic but never used as
  authority.

No network, no daemon, no real port — the resolver is pure/in-process.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.sync.queue import write_active_scope
from specify_cli.sync.target_authority import (
    DEFAULT_SERVER_URL,
    OverrideMode,
    QueueScopeStatus,
    ResolvedSyncTarget,
    SyncTargetSplitBrainError,
    resolve_sync_target,
)

pytestmark = [pytest.mark.fast]

CONFIG_URL = "https://config.example.com"
ENV_URL = "https://env.example.com"


@pytest.fixture
def target_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate all sync global state under a throwaway ``SPEC_KITTY_HOME``.

    Also clears ``SPEC_KITTY_SAAS_URL`` and neutralises the encrypted-session
    scope read so the diagnostic stays deterministic and network-free; tests
    that need those sources re-patch them explicitly.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    monkeypatch.setattr(
        "specify_cli.sync.target_authority.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: None,
    )
    return tmp_path


def _write_config(root: Path, server_url: str) -> None:
    (root / "config.toml").write_text(
        f'[sync]\nserver_url = "{server_url}"\n', encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# T006 / contract §1: all eight fields populated
# ---------------------------------------------------------------------------


def test_all_fields_populated_under_env_equals_config(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = CONFIG_URL  # env == config, no override

    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")

    assert isinstance(target, ResolvedSyncTarget)
    assert target.configured_server_url == CONFIG_URL
    assert target.env_server_url == CONFIG_URL
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == CONFIG_URL
    assert target.user_id == "alice@example.com"
    assert target.team_slug == "team-red"
    assert target.derived_queue_scope  # non-empty deterministic key
    assert isinstance(target.queue_db_path, Path)
    assert target.queue_db_path.name.startswith("queue-")
    assert target.active_queue_scope_status is QueueScopeStatus.ABSENT


def test_to_diagnostics_dict_is_json_safe_with_all_keys(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")

    diag = target.to_diagnostics_dict()
    # WP11/contract §6 consumes this as the ``target_authority`` JSON section.
    assert set(diag) == {
        "configured_server_url",
        "env_server_url",
        "override_mode",
        "resolved_server_url",
        "user_id",
        "team_slug",
        "derived_queue_scope",
        "queue_db_path",
        "active_queue_scope_status",
    }
    assert diag["override_mode"] == "none"
    assert diag["active_queue_scope_status"] == "absent"
    assert isinstance(diag["queue_db_path"], str)
    # Must round-trip through JSON (literal tokens, no enums/Path objects).
    json.dumps(diag)


def test_neither_config_nor_env_falls_back_to_default(target_root: Path) -> None:
    # No config.toml written, SPEC_KITTY_SAAS_URL cleared by the fixture.
    target = resolve_sync_target()

    assert target.configured_server_url is None
    assert target.env_server_url is None
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == DEFAULT_SERVER_URL
    assert target.user_id is None
    assert target.team_slug is None
    assert target.derived_queue_scope


def test_corrupt_config_toml_is_treated_as_no_configured_url(target_root: Path) -> None:
    # Invalid TOML must degrade to "no configured key", not raise into authority.
    (target_root / "config.toml").write_text("this is = = not valid toml", encoding="utf-8")
    target = resolve_sync_target()
    assert target.configured_server_url is None
    assert target.resolved_server_url == DEFAULT_SERVER_URL


def test_non_table_sync_key_is_treated_as_no_configured_url(target_root: Path) -> None:
    # A malformed ``sync`` value (scalar, not a table) yields no configured URL.
    (target_root / "config.toml").write_text('sync = "oops"\n', encoding="utf-8")
    target = resolve_sync_target()
    assert target.configured_server_url is None
    assert target.resolved_server_url == DEFAULT_SERVER_URL


def test_resolved_target_is_immutable(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_sync_target()
    with pytest.raises((AttributeError, TypeError)):
        target.resolved_server_url = "https://mutated.example.com"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T002 / override_mode classification
# ---------------------------------------------------------------------------


def test_env_equals_config_is_not_an_override(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = CONFIG_URL + "/"  # trailing slash only
    target = resolve_sync_target()
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == CONFIG_URL


def test_missing_config_with_matching_env_is_not_override(target_root: Path) -> None:
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = DEFAULT_SERVER_URL
    target = resolve_sync_target()
    assert target.configured_server_url is None
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == DEFAULT_SERVER_URL


def test_missing_config_with_differing_env_is_process_override(target_root: Path) -> None:
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL
    target = resolve_sync_target()
    assert target.configured_server_url is None
    assert target.override_mode is OverrideMode.PROCESS_OVERRIDE
    assert target.resolved_server_url == ENV_URL


# ---------------------------------------------------------------------------
# T005 / SC-008: split-brain can never resolve one target while scoping another
# ---------------------------------------------------------------------------


def test_whole_process_override_resolves_url_and_scope_consistently(
    target_root: Path,
) -> None:
    _write_config(target_root, CONFIG_URL)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL  # disagrees with config
    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")

    # Whole-process override (default): both the resolved URL AND the derived
    # scope reflect the env target — it is impossible to scope one target while
    # resolving another (SC-008).
    assert target.override_mode is OverrideMode.PROCESS_OVERRIDE
    assert target.resolved_server_url == ENV_URL
    assert "env.example.com" in target.derived_queue_scope
    assert "config.example.com" not in target.derived_queue_scope


def test_ambiguous_setup_only_disagreement_fails_closed(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL
    with pytest.raises(SyncTargetSplitBrainError) as excinfo:
        resolve_sync_target(process_wide_override=False)

    message = str(excinfo.value)
    # Operator-actionable: both URLs and both source names appear.
    assert CONFIG_URL in message
    assert ENV_URL in message
    assert "SPEC_KITTY_SAAS_URL" in message
    assert excinfo.value.configured_server_url == CONFIG_URL
    assert excinfo.value.env_server_url == ENV_URL


# ---------------------------------------------------------------------------
# T003 / C-002: scope is derived from the resolved target, never injected
# ---------------------------------------------------------------------------


def test_scope_is_deterministic_for_same_inputs(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    a = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    b = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    assert a.derived_queue_scope == b.derived_queue_scope
    assert a.queue_db_path == b.queue_db_path


def test_different_resolved_url_changes_scope_and_db_path(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    config_target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")

    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL  # process override → env wins
    env_target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")

    assert config_target.derived_queue_scope != env_target.derived_queue_scope
    assert config_target.queue_db_path != env_target.queue_db_path


def test_changing_identity_changes_scope(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    alice = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    bob = resolve_sync_target(user_id="bob@example.com", team_slug="team-red")
    assert alice.derived_queue_scope != bob.derived_queue_scope


def test_unauthenticated_identity_still_yields_a_usable_scope(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_sync_target()  # no user/team
    assert target.derived_queue_scope
    assert target.queue_db_path.name.startswith("queue-")


def test_db_path_is_a_pure_function_of_the_scope(target_root: Path) -> None:
    from specify_cli.sync.queue import scope_db_path

    _write_config(target_root, CONFIG_URL)
    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    assert target.queue_db_path == scope_db_path(target.derived_queue_scope)


def test_no_public_parameter_injects_scope_or_db_path() -> None:
    import inspect

    params = set(inspect.signature(resolve_sync_target).parameters)
    assert "scope" not in params
    assert "queue_scope" not in params
    assert "db_path" not in params
    assert "queue_db_path" not in params


# ---------------------------------------------------------------------------
# Identifier Safety (binding charter rule): ASCII-only derived identifiers
# ---------------------------------------------------------------------------


def test_accented_latin_identity_yields_ascii_only_identifiers(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_sync_target(user_id="José", team_slug="café-équipe")

    assert target.derived_queue_scope.isascii()
    assert target.queue_db_path.name.isascii()
    assert str(target.queue_db_path).isascii()


# ---------------------------------------------------------------------------
# T004 / contract §1: active_queue_scope is a diagnostic, never authority
# ---------------------------------------------------------------------------


def test_absent_when_no_cached_scope(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    assert target.active_queue_scope_status is QueueScopeStatus.ABSENT


def test_matches_when_cached_scope_equals_derived(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    first = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    write_active_scope(first.derived_queue_scope)

    second = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    assert second.active_queue_scope_status is QueueScopeStatus.MATCHES
    assert second.derived_queue_scope == first.derived_queue_scope


def test_stale_cache_is_reported_but_never_authoritative(target_root: Path) -> None:
    from specify_cli.sync.queue import scope_db_path

    _write_config(target_root, CONFIG_URL)
    write_active_scope("https://stale.example.com|ghost@example.com|old-team")

    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")

    assert target.active_queue_scope_status is QueueScopeStatus.STALE_NON_AUTHORITATIVE
    # The recomputed (derived) value wins; the stale cache is never used.
    assert target.derived_queue_scope != "https://stale.example.com|ghost@example.com|old-team"
    assert target.queue_db_path == scope_db_path(target.derived_queue_scope)


def test_credentials_scope_is_consulted_for_diagnostic(target_root: Path) -> None:
    from specify_cli.sync.queue import build_queue_scope

    _write_config(target_root, CONFIG_URL)
    (target_root / "credentials").write_text(
        f"""
[user]
username = "alice@example.com"
team_slug = "team-red"

[server]
url = "{CONFIG_URL}"
""".strip(),
        encoding="utf-8",
    )
    # The resolver derives the same scope from the same URL + identity, so the
    # credentials-cached scope matches.
    expected = build_queue_scope(
        server_url=CONFIG_URL, username="alice@example.com", team_slug="team-red"
    )
    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    assert target.derived_queue_scope == expected
    assert target.active_queue_scope_status is QueueScopeStatus.MATCHES


def test_session_scope_read_returning_value_is_consulted(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(target_root, CONFIG_URL)
    target_probe = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")

    monkeypatch.setattr(
        "specify_cli.sync.target_authority.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: target_probe.derived_queue_scope,
    )
    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    assert target.active_queue_scope_status is QueueScopeStatus.MATCHES


def test_corrupt_session_scope_read_is_treated_as_absent(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(target_root, CONFIG_URL)

    def _boom(*, allow_rehydrate: bool = True) -> str:
        raise RuntimeError("corrupt session store")

    monkeypatch.setattr(
        "specify_cli.sync.target_authority.read_queue_scope_from_session", _boom
    )
    target = resolve_sync_target(user_id="alice@example.com", team_slug="team-red")
    # A corrupt cache must never raise into authority; it degrades to ``absent``.
    assert target.active_queue_scope_status is QueueScopeStatus.ABSENT
