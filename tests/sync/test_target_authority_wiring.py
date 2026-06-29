"""Integration wiring tests for the canonical Target Authority (WP02, contract §1).

WP01 produced the descriptive :class:`ResolvedSyncTarget` and proved its
invariants at the resolver level. WP02 *wires the live runtime surfaces onto
it*: readiness, the daemon-owner identity, and the sync-boundary preflight
identity must all key off the **one** resolved target so that env/config
disagreement can never derive the queue scope for one target while a surface
posts to another (SC-008), and a stale ``active_queue_scope`` is never used as
authority (contract §1 rule, C-002).

These assert **observable state** (URLs, scope strings, db paths) across the
rewired surfaces — never internal call order (NFR-001). No network, no daemon,
no real port: the resolver and every probe here are pure/in-process.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.saas import readiness
from specify_cli.sync.owner import compute_foreground_identity
from specify_cli.sync.preflight import collect_foreground_identity
from specify_cli.sync.queue import write_active_scope
from specify_cli.sync.target_authority import (
    QueueScopeStatus,
    resolve_sync_target,
)

pytestmark = [pytest.mark.fast]

CONFIG_URL = "https://config.example.com"
ENV_URL = "https://env.example.com"
USER = "alice@example.com"
TEAM = "team-red"


class _NoSession:
    """Token-manager stub exposing no current session (read-only, no network)."""

    def get_current_session(self) -> None:
        return None


@pytest.fixture
def wiring_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate all sync global state under a throwaway ``SPEC_KITTY_HOME``.

    Clears ``SPEC_KITTY_SAAS_URL`` and neutralises every encrypted-session read
    seam so identity is driven only by the on-disk ``credentials`` file,
    ``config.toml`` and the env var — deterministic and network-free. Tests that
    want an env override re-set ``SPEC_KITTY_SAAS_URL`` explicitly.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    # Resolver diagnostic + owner identity both read the session store; force
    # them to "no cached session" so only credentials/config/env drive state.
    monkeypatch.setattr(
        "specify_cli.sync.target_authority.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: None,
    )
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_session",
        lambda *, allow_rehydrate=True: None,
    )
    # Preflight reads the session via the token-manager singleton directly.
    monkeypatch.setattr(
        "specify_cli.auth.manager.get_token_manager", lambda: _NoSession()
    )
    return tmp_path


def _write_config(root: Path, server_url: str) -> None:
    (root / "config.toml").write_text(
        f'[sync]\nserver_url = "{server_url}"\n', encoding="utf-8"
    )


def _write_credentials(root: Path, *, server_url: str, user: str, team: str) -> None:
    (root / "credentials").write_text(
        f"""
[user]
username = "{user}"
team_slug = "{team}"

[server]
url = "{server_url}"
""".strip(),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# T008 — readiness keys off the resolved target (not a separate env-only read)
# ---------------------------------------------------------------------------


def test_readiness_host_config_keys_off_resolved_target(wiring_root: Path) -> None:
    """When env opts in, readiness reports the single resolved target URL.

    The D-5 opt-in gate is via ``SPEC_KITTY_SAAS_URL``; once set, the URL is the
    canonical ``resolved_server_url`` so readiness and sync agree (contract §1).
    """
    _write_config(wiring_root, CONFIG_URL)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = CONFIG_URL  # env == config, opted in

    probed = readiness._probe_host_config()
    resolved = resolve_sync_target().resolved_server_url

    assert probed == CONFIG_URL
    assert probed == resolved


def test_readiness_targets_env_under_whole_process_override(wiring_root: Path) -> None:
    """When env overrides config, readiness probes the env (resolved) URL.

    This is the readiness SC-008 proof: readiness can never green-light the
    config URL while sync posts to the env URL — both are the one resolved
    target.
    """
    _write_config(wiring_root, CONFIG_URL)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL

    probed = readiness._probe_host_config()
    target = resolve_sync_target()

    assert target.resolved_server_url == ENV_URL
    assert probed == ENV_URL  # same resolved target, not the config URL


def test_readiness_env_presence_gate_preserved(wiring_root: Path) -> None:
    """D-5 opt-in gate preserved: config-only (env unset) ⇒ absent host.

    Config-file ``[sync].server_url`` alone never opts a machine into hosted
    readiness; only ``SPEC_KITTY_SAAS_URL`` does. Owner/preflight still derive
    their scope from the resolved (config) target — readiness simply requires
    the explicit env opt-in.
    """
    _write_config(wiring_root, CONFIG_URL)
    # env cleared by the fixture, config present.
    assert readiness._probe_host_config() is None


def test_readiness_host_config_absent_when_no_source(wiring_root: Path) -> None:
    """Neither config nor env configured ⇒ readiness reports an absent host."""
    # No config.toml written; env cleared by the fixture.
    assert readiness._probe_host_config() is None


# ---------------------------------------------------------------------------
# T009 / SC-008 — owner identity scope + URL follow the one resolved target
# ---------------------------------------------------------------------------


def test_owner_identity_follows_resolved_target_under_split_brain(
    wiring_root: Path,
) -> None:
    """Daemon-owner identity cannot scope one target while posting to another.

    config and env disagree; the whole-process override resolves env. The owner
    record's ``server_url`` AND ``auth_scope`` AND ``queue_db_path`` must all
    reflect that single resolved (env) target — the structural SC-008 fix.
    """
    _write_config(wiring_root, CONFIG_URL)
    _write_credentials(wiring_root, server_url=CONFIG_URL, user=USER, team=TEAM)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL  # disagrees with config

    identity = compute_foreground_identity(allow_network=False)
    target = resolve_sync_target(user_id=USER, team_slug=TEAM)

    assert identity["server_url"] == ENV_URL
    assert identity["auth_scope"] == target.derived_queue_scope
    assert identity["queue_db_path"] == str(target.queue_db_path)
    # The derived scope is keyed to the env target, never the config target.
    assert "env.example.com" in identity["auth_scope"]
    assert "config.example.com" not in identity["auth_scope"]


def test_preflight_identity_follows_resolved_target_under_split_brain(
    wiring_root: Path,
) -> None:
    """Preflight foreground identity derives scope from the resolved target."""
    _write_config(wiring_root, CONFIG_URL)
    _write_credentials(wiring_root, server_url=CONFIG_URL, user=USER, team=TEAM)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL

    fg = collect_foreground_identity(repo_root=wiring_root)
    target = resolve_sync_target(user_id=USER, team_slug=TEAM)

    assert fg.server_url == ENV_URL
    assert fg.queue_db_path == target.queue_db_path
    assert "env.example.com" not in str(target.queue_db_path)  # digest is opaque


# ---------------------------------------------------------------------------
# T009 / contract §1 — stale active_queue_scope reported, never authoritative
# ---------------------------------------------------------------------------


def test_stale_active_queue_scope_ignored_by_owner_identity(
    wiring_root: Path,
) -> None:
    """A stale cached scope is a diagnostic only — the derived scope wins."""
    _write_config(wiring_root, CONFIG_URL)
    _write_credentials(wiring_root, server_url=CONFIG_URL, user=USER, team=TEAM)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = ENV_URL
    write_active_scope("https://stale.example.com|ghost@example.com|old-team")

    identity = compute_foreground_identity(allow_network=False)
    target = resolve_sync_target(user_id=USER, team_slug=TEAM)

    # Identity uses the freshly derived scope, not the stale cache.
    assert identity["auth_scope"] == target.derived_queue_scope
    assert "stale.example.com" not in identity["auth_scope"]
    # The cache is still surfaced as a diagnostic (never as authority).
    assert (
        target.active_queue_scope_status is QueueScopeStatus.STALE_NON_AUTHORITATIVE
    )


# ---------------------------------------------------------------------------
# T011 — single-target coherence: every surface shares one resolved URL
# ---------------------------------------------------------------------------


def test_single_resolved_url_across_surfaces(wiring_root: Path) -> None:
    """Readiness, owner, and preflight all share the one resolved-target URL.

    Env and config agree (no override): every surface — including readiness,
    which is opted in by the matching env var — keys off the same
    ``resolved_server_url``.
    """
    _write_config(wiring_root, CONFIG_URL)
    _write_credentials(wiring_root, server_url=CONFIG_URL, user=USER, team=TEAM)
    import os

    os.environ["SPEC_KITTY_SAAS_URL"] = CONFIG_URL  # opt readiness in; no override

    target = resolve_sync_target(user_id=USER, team_slug=TEAM)
    readiness_url = readiness._probe_host_config()
    owner_url = compute_foreground_identity(allow_network=False)["server_url"]
    preflight_url = collect_foreground_identity(repo_root=wiring_root).server_url

    assert target.resolved_server_url == CONFIG_URL
    assert readiness_url == CONFIG_URL
    assert owner_url == CONFIG_URL
    assert preflight_url == CONFIG_URL
