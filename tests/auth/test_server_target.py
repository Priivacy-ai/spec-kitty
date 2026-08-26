"""Acceptance tests for the canonical hosted-server target resolver (issue #5).

Re-homed and slimmed down from the deleted ``tests/sync/test_target_authority.py``
(``specify_cli.sync.target_authority``) to match the surviving surface at
``specify_cli.auth.server_target``: no queue scope, no user/team identity, no
network. What remains is the precedence contract (env over config over
:data:`DEFAULT_SERVER_URL`) and the fail-closed split-brain guard.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.auth.server_target import (
    DEFAULT_SERVER_URL,
    SAAS_URL_ENV_VAR,
    OverrideMode,
    ResolvedServerTarget,
    ServerTargetSplitBrainError,
    resolve_server_target,
)

pytestmark = [pytest.mark.fast]

CONFIG_URL = "https://config.example.com"
ENV_URL = "https://env.example.com"


@pytest.fixture
def target_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate config.toml under a throwaway ``SPEC_KITTY_HOME`` with no env leakage."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.delenv(SAAS_URL_ENV_VAR, raising=False)
    return tmp_path


def _write_config(root: Path, server_url: str) -> None:
    (root / "config.toml").write_text(f'[sync]\nserver_url = "{server_url}"\n', encoding="utf-8")


# ---------------------------------------------------------------------------
# Fields + JSON-safety
# ---------------------------------------------------------------------------


def test_all_fields_populated_under_env_equals_config(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(target_root, CONFIG_URL)
    monkeypatch.setenv(SAAS_URL_ENV_VAR, CONFIG_URL)  # env == config, no override

    target = resolve_server_target()

    assert isinstance(target, ResolvedServerTarget)
    assert target.configured_server_url == CONFIG_URL
    assert target.env_server_url == CONFIG_URL
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == CONFIG_URL


def test_to_diagnostics_dict_is_json_safe_with_all_keys(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_server_target()

    diag = target.to_diagnostics_dict()
    assert set(diag) == {
        "configured_server_url",
        "env_server_url",
        "override_mode",
        "resolved_server_url",
    }
    assert diag["override_mode"] == "none"
    json.dumps(diag)  # must round-trip through JSON


def test_neither_config_nor_env_falls_back_to_default(target_root: Path) -> None:
    target = resolve_server_target()

    assert target.configured_server_url is None
    assert target.env_server_url is None
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == DEFAULT_SERVER_URL


def test_corrupt_config_toml_is_treated_as_no_configured_url(target_root: Path) -> None:
    (target_root / "config.toml").write_text("this is = = not valid toml", encoding="utf-8")
    target = resolve_server_target()
    assert target.configured_server_url is None
    assert target.resolved_server_url == DEFAULT_SERVER_URL


def test_non_table_sync_key_is_treated_as_no_configured_url(target_root: Path) -> None:
    (target_root / "config.toml").write_text('sync = "oops"\n', encoding="utf-8")
    target = resolve_server_target()
    assert target.configured_server_url is None
    assert target.resolved_server_url == DEFAULT_SERVER_URL


def test_resolved_target_is_immutable(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_server_target()
    with pytest.raises((AttributeError, TypeError)):
        target.resolved_server_url = "https://mutated.example.com"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# override_mode classification — env > config precedence
# ---------------------------------------------------------------------------


def test_env_equals_config_is_not_an_override(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(target_root, CONFIG_URL)
    monkeypatch.setenv(SAAS_URL_ENV_VAR, CONFIG_URL + "/")  # trailing slash only
    target = resolve_server_target()
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == CONFIG_URL


def test_missing_config_with_matching_env_is_not_override(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(SAAS_URL_ENV_VAR, DEFAULT_SERVER_URL)
    target = resolve_server_target()
    assert target.configured_server_url is None
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == DEFAULT_SERVER_URL


def test_missing_config_with_differing_env_is_process_override(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(SAAS_URL_ENV_VAR, ENV_URL)
    target = resolve_server_target()
    assert target.configured_server_url is None
    assert target.override_mode is OverrideMode.PROCESS_OVERRIDE
    assert target.resolved_server_url == ENV_URL


def test_config_set_with_differing_env_and_process_override_env_wins(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(target_root, CONFIG_URL)
    monkeypatch.setenv(SAAS_URL_ENV_VAR, ENV_URL)  # disagrees with config
    target = resolve_server_target(process_wide_override=True)

    assert target.override_mode is OverrideMode.PROCESS_OVERRIDE
    assert target.resolved_server_url == ENV_URL


# ---------------------------------------------------------------------------
# Fail-closed split-brain guard (process_wide_override=False)
# ---------------------------------------------------------------------------


def test_ambiguous_setup_only_disagreement_fails_closed(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(target_root, CONFIG_URL)
    monkeypatch.setenv(SAAS_URL_ENV_VAR, ENV_URL)
    with pytest.raises(ServerTargetSplitBrainError) as excinfo:
        resolve_server_target(process_wide_override=False)

    message = str(excinfo.value)
    # Operator-actionable: both URLs and the env var name appear.
    assert CONFIG_URL in message
    assert ENV_URL in message
    assert SAAS_URL_ENV_VAR in message
    assert excinfo.value.configured_server_url == CONFIG_URL
    assert excinfo.value.env_server_url == ENV_URL


def test_env_equals_config_never_raises_even_with_process_wide_override_false(
    target_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(target_root, CONFIG_URL)
    monkeypatch.setenv(SAAS_URL_ENV_VAR, CONFIG_URL)
    target = resolve_server_target(process_wide_override=False)
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == CONFIG_URL


def test_no_env_never_raises_even_with_process_wide_override_false(target_root: Path) -> None:
    _write_config(target_root, CONFIG_URL)
    target = resolve_server_target(process_wide_override=False)
    assert target.override_mode is OverrideMode.NONE
    assert target.resolved_server_url == CONFIG_URL
