"""Z1-T1 §3.2 item 7 / §4 N10, N11: local checkout/auth credential storage.

``<runtime_state_root>/zeitgeist-credentials``, TOML, ``filelock``-guarded
(Z1.md decision 3/4 — own file, not shared with tracker/credentials.py; uses
the existing declared-but-unused ``filelock`` dependency,
``pyproject.toml:85``). Stores ``{relay_url, token, token_issued_at,
token_kind}`` keyed by canonical repo, plus the optional FIX-M2-15
``capability_credential`` field (omitted from the stored TOML entry
entirely, not written as an empty string, whenever a caller does not pass
one — see that section below and the module's own FIX-M2-15 docstring
note).

This is a scoped subset of Z1.md §3.4's full ``checkout``/``--refresh``/
``--revoke`` CLI contract: it covers the storage primitive
(``store``/``load``/``revoke``) N10/N11 exercise, not the network canary-offer
probe (that lives in the not-yet-implemented CLI adapter — see WP01
handoff).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.zeitgeist_client import credentials

# See tests/zeitgeist_client/test_grammar.py's pytestmark comment.
pytestmark = pytest.mark.fast


@pytest.fixture()
def state_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "spec-kitty-home"))
    return tmp_path / "spec-kitty-home"


def test_store_then_load_round_trips(state_root: Path):
    credentials.store(
        repo="spec-kitty",
        relay_url="http://127.0.0.1:9999",
        token="tok-abc",
        token_kind="shared_team",
    )
    loaded = credentials.load(repo="spec-kitty")
    assert loaded is not None
    assert loaded.relay_url == "http://127.0.0.1:9999"
    assert loaded.token == "tok-abc"
    assert loaded.token_kind == "shared_team"
    assert loaded.token_issued_at  # non-empty ISO timestamp


def test_load_returns_none_when_nothing_stored(state_root: Path):
    assert credentials.load(repo="spec-kitty") is None


# --- FIX-M2-15: the second, optional capability_credential field -----------


def test_single_credential_store_round_trips_capability_credential_as_none(state_root: Path):
    """Every call site that predates FIX-M2-15 (and every self-hosted,
    single-secret deployment) never passes ``capability_credential`` —
    ``load()`` must report that as ``None``, never as an empty string or a
    KeyError, so every caller's existing "``None`` means use ``token`` for
    both gates" fallback keeps working."""
    credentials.store(repo="spec-kitty", relay_url="http://a", token="tok-a", token_kind="shared_team")
    loaded = credentials.load(repo="spec-kitty")
    assert loaded is not None
    assert loaded.capability_credential is None


def test_two_credential_store_round_trips_both_values_independently(state_root: Path):
    credentials.store(
        repo="spec-kitty",
        relay_url="http://a",
        token="team-shared-token",
        token_kind="shared_team",
        capability_credential="actor-capability-jwt",
    )
    loaded = credentials.load(repo="spec-kitty")
    assert loaded is not None
    assert loaded.token == "team-shared-token"
    assert loaded.capability_credential == "actor-capability-jwt"


def test_empty_capability_credential_is_rejected_when_provided(state_root: Path):
    with pytest.raises(ValueError):
        credentials.store(
            repo="spec-kitty",
            relay_url="http://a",
            token="tok-a",
            token_kind="shared_team",
            capability_credential="",
        )
    # Never left the store corrupted/partially written.
    assert credentials.load(repo="spec-kitty") is None


def test_stored_toml_omits_capability_credential_key_entirely_when_unset(state_root: Path):
    """Backward-compat proof, not just a `None` read-back: a config file
    written by this fix looks byte-for-byte like one written before it,
    for a single-credential checkout -- no `capability_credential = ""`
    key ever lands in the TOML entry, which would otherwise round-trip as
    an empty string rather than `None` (and, since `store()` itself
    rejects an explicit empty string, would signal the entry was written
    by something that bypassed this module's own validation)."""
    credentials.store(repo="spec-kitty", relay_url="http://a", token="tok-a", token_kind="shared_team")
    import tomllib

    with credentials.credentials_path().open("rb") as fh:
        raw = tomllib.load(fh)
    assert "capability_credential" not in raw["spec-kitty"]


def test_two_repos_hold_independent_tokens(state_root: Path):
    credentials.store(repo="spec-kitty", relay_url="http://a", token="tok-a", token_kind="shared_team")
    credentials.store(repo="zeitgeist", relay_url="http://b", token="tok-b", token_kind="shared_team")
    assert credentials.load(repo="spec-kitty").token == "tok-a"  # type: ignore[union-attr]
    assert credentials.load(repo="zeitgeist").token == "tok-b"  # type: ignore[union-attr]


def test_credentials_file_lives_under_runtime_state_root_not_tracker_file(state_root: Path):
    credentials.store(repo="spec-kitty", relay_url="http://a", token="tok-a", token_kind="shared_team")
    path = credentials.credentials_path()
    assert path.name == "zeitgeist-credentials"
    assert path.parent == state_root
    assert path != state_root / "credentials"  # tracker's own file, never shared (decision 3)


def test_n10_revoke_deletes_local_token_even_when_relay_unreachable(state_root: Path):
    credentials.store(repo="spec-kitty", relay_url="http://127.0.0.1:1", token="tok-a", token_kind="shared_team")
    # revoke() here is the local-wipe half only (§3.2 item 7): "never fails to
    # wipe locally even if the [server] offer drops" — the network half lives
    # in the not-yet-implemented CLI (`checkout --revoke`).
    credentials.revoke(repo="spec-kitty")
    assert credentials.load(repo="spec-kitty") is None


def test_n11_a_failed_refresh_never_deletes_the_previously_stored_token(state_root: Path):
    credentials.store(repo="spec-kitty", relay_url="http://a", token="tok-a", token_kind="shared_team")
    # store() itself never deletes on its own failure path; a caller doing a
    # refresh that fails its network probe (401) must simply not call
    # store()/revoke() again — asserting the storage layer has no implicit
    # "clear on any write attempt" behaviour.
    with pytest.raises(ValueError):
        credentials.store(repo="spec-kitty", relay_url="http://a", token="", token_kind="shared_team")
    still_there = credentials.load(repo="spec-kitty")
    assert still_there is not None
    assert still_there.token == "tok-a"
