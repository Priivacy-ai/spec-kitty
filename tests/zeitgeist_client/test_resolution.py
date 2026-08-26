"""E3 credential resolution (EXPERIMENTAL-spec-kitty#9): cached relay
credential, capability mint on miss/expiry, short-TTL negative answers.

Three layers are covered separately:

- :func:`resolution.repo_slug_and_host` — the ``owner/repo`` + host Team
  Kitty admits by, from a checkout's origin URL; hosted forms only.
- :class:`resolution.SaasCapabilityGateway` — the two HTTP calls against
  the endpoints' real wire shapes (respx), including every non-2xx the
  resolver has to tell apart.
- the resolution core (:func:`resolution.resolve_credentials` over a real
  git clone at the bottom, its identity-free core everywhere else) — cache
  hit/expiry, negative TTL, force-after-403, and "never cache a transient
  failure".

The gateway double in the core tests is a scripted subclass of the real
class: it records its calls and plays back answers/exceptions per layer,
so no core branch depends on HTTP and no HTTP test depends on the store.
"""

from __future__ import annotations

import json as json_module
import subprocess
from pathlib import Path

import httpx
import pytest
import respx

from kernel.clock import now_utc, parse_iso, timedelta

from specify_cli.saas_client.errors import SaasAuthError
from specify_cli.zeitgeist_client import credentials, resolution
from specify_cli.zeitgeist_client.resolution import (
    KIND_PRESENCE,
    CapabilityDenied,
    GatewayError,
    MintedCredential,
    SaasCapabilityGateway,
)

pytestmark = pytest.mark.fast


def _iso_in(seconds: float) -> str:
    return (now_utc() + timedelta(seconds=seconds)).isoformat()


MINT_BODY = {
    "session_ref": "01ABC",
    "deployment_id": "dep-1",
    "repo_slug": "acme/widget",
    "kind": "presence",
    "relay_url": "http://127.0.0.1:9100",
    "relay_token": "shared-bearer",
    "capability_credential": "actor-jwt",
    "expires_at": _iso_in(3600),
}


@pytest.fixture()
def state_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "spec-kitty-home"))
    return tmp_path / "spec-kitty-home"


class ScriptedGateway(SaasCapabilityGateway):
    """Records calls, plays back scripted outcomes. Never touches the
    network -- __init__ is deliberately not chained."""

    def __init__(
        self,
        *,
        admission: object = None,
        mint: object = None,
    ) -> None:
        self.admission_script = admission if admission is not None else {"admitted": True}
        self.mint_script = (
            mint
            if mint is not None
            else MintedCredential(
                relay_url="http://relay",
                relay_token="bearer",
                capability_credential="jwt",
                expires_at=_iso_in(3600),
            )
        )
        self.admission_calls: list[dict[str, str | None]] = []
        self.mint_calls: list[dict[str, str | None]] = []

    def check_repo_admission(self, *, repo_slug: str, host: str | None = None) -> resolution.AdmissionAnswer:
        self.admission_calls.append({"repo_slug": repo_slug, "host": host})
        outcome = self.admission_script
        if isinstance(outcome, Exception):
            raise outcome
        return resolution.AdmissionAnswer(
            admitted=bool(outcome.get("admitted", False)),  # type: ignore[union-attr]
            team_slug=(outcome or {}).get("team_slug"),  # type: ignore[union-attr]
            reason=(outcome or {}).get("reason"),  # type: ignore[union-attr]
        )

    def mint_capability(
        self,
        *,
        repo_slug: str,
        kind: str = KIND_PRESENCE,
        team_slug: str | None = None,
    ) -> MintedCredential:
        self.mint_calls.append({"repo_slug": repo_slug, "kind": kind, "team_slug": team_slug})
        outcome = self.mint_script
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, MintedCredential)
        return outcome


# ---------------------------------------------------------------------------
# repo_slug_and_host: the identity Team Kitty admits by
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("git@github.com:acme/widget.git", ("acme/widget", "github.com")),
        ("https://github.com/acme/widget.git", ("acme/widget", "github.com")),
        ("ssh://git@gitlab.com:2222/org/team/repo.git", ("org/team/repo", "gitlab.com")),
        ("git@gitlab.com:org/team/repo.git", ("org/team/repo", "gitlab.com")),
        # Case is normalized: the server stores and matches slugs lowercase.
        ("https://GitHub.com/ACME/Widget.GIT", ("acme/widget", "github.com")),
        # A .git suffix is optional on either form.
        ("git@github.com:acme/widget", ("acme/widget", "github.com")),
    ],
)
def test_hosted_remote_urls_parse_to_slug_and_host(origin: str, expected: tuple[str, str]) -> None:
    assert resolution.repo_slug_and_host(origin) == expected


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "/srv/git/widget.git",  # bare local path
        "./sibling-repo",
        "../elsewhere/repo.git",
        "file:///srv/git/widget.git",  # file scheme
        "/home/dev/clones/widget.git",  # local-path origin of a test clone
        "git@github.com:single-segment",  # no owner segment
    ],
)
def test_non_hosted_remotes_have_nothing_to_ask_about(origin: str) -> None:
    """A local or unparseable remote yields (None, None): guessing an
    ``owner/repo`` from it would be exactly the spoofable identity
    repo_identity refuses to mint."""
    assert resolution.repo_slug_and_host(origin) == (None, None)


class TestStoreKey:
    """spec-kitty#129: the credential store is keyed by the full
    ``(host, owner/repo)`` identity, not the bare repo NAME."""

    def test_key_is_host_then_slug(self) -> None:
        assert resolution.store_key(host="github.com", repo_slug="acme/widget") == "github.com/acme/widget"

    def test_same_name_under_different_owners_yields_distinct_keys(self) -> None:
        assert resolution.store_key(host="github.com", repo_slug="acme/widget") != resolution.store_key(host="github.com", repo_slug="evil/widget")

    def test_same_slug_on_different_hosts_yields_distinct_keys(self) -> None:
        assert resolution.store_key(host="github.com", repo_slug="acme/widget") != resolution.store_key(host="gitlab.com", repo_slug="acme/widget")

    def test_unknown_host_still_keys_uniquely_by_slug(self) -> None:
        # No hosted grammar produces an empty host, so "" cannot collide
        # with a real host segment.
        assert resolution.store_key(host=None, repo_slug="acme/widget") == "/acme/widget"


# ---------------------------------------------------------------------------
# SaasCapabilityGateway against the endpoints' real wire shapes (respx)
# ---------------------------------------------------------------------------

BASE = "http://teamkitty.test"
ADMISSION = f"{BASE}/api/v1/sync/repo-admission/"
MINT = f"{BASE}/api/v1/live/capability/cli/"


def _gateway(**kwargs: object) -> SaasCapabilityGateway:
    return SaasCapabilityGateway(BASE, "test-token", **kwargs)  # type: ignore[arg-type]


class TestAdmissionPreFlight:
    def test_sends_slug_and_host_query_params(self) -> None:
        with respx.mock:
            route = respx.get(ADMISSION).respond(200, json={"admitted": False, "reason": "no_match"})
            answer = _gateway().check_repo_admission(repo_slug="acme/widget", host="github.com")
        assert route.called
        sent = dict(httpx.QueryParams(route.calls[0].request.url.query))
        assert sent == {"repo_slug": "acme/widget", "host": "github.com"}
        assert answer.admitted is False
        assert answer.reason == "no_match"

    def test_omits_host_param_when_unknown(self) -> None:
        with respx.mock:
            route = respx.get(ADMISSION).respond(200, json={"admitted": False, "reason": "no_match"})
            _gateway().check_repo_admission(repo_slug="acme/widget")
        sent = dict(httpx.QueryParams(route.calls[0].request.url.query))
        assert sent == {"repo_slug": "acme/widget"}

    def test_parses_admitted_shape_with_team_slug(self) -> None:
        with respx.mock:
            respx.get(ADMISSION).respond(
                200,
                json={
                    "admitted": True,
                    "team": {"id": "T1", "slug": "acme", "name": "Acme"},
                    "provider": "github",
                    "repo_slug": "acme/widget",
                },
            )
            answer = _gateway().check_repo_admission(repo_slug="acme/widget")
        assert answer.admitted is True
        assert answer.team_slug == "acme"

    @pytest.mark.parametrize("status", [401, 403, 500])
    def test_any_non_2xx_is_a_transient_gateway_error(self, status: int) -> None:
        """The pre-flight never produces a cached answer from a status
        code -- an unusable session must not read as 'no team'."""
        with respx.mock:
            respx.get(ADMISSION).respond(status, text="denied")
            with pytest.raises(GatewayError):
                _gateway().check_repo_admission(repo_slug="acme/widget")

    def test_transport_fault_raises_gateway_error(self) -> None:
        with respx.mock:
            respx.get(ADMISSION).mock(side_effect=httpx.ConnectError("refused"))
            with pytest.raises(GatewayError):
                _gateway().check_repo_admission(repo_slug="acme/widget")

    def test_unreadable_body_raises_gateway_error(self) -> None:
        with respx.mock:
            respx.get(ADMISSION).respond(200, text="not json")
            with pytest.raises(GatewayError):
                _gateway().check_repo_admission(repo_slug="acme/widget")


class TestCapabilityMint:
    def test_success_parses_the_full_credential_triple(self) -> None:
        with respx.mock:
            route = respx.post(MINT).respond(201, json=MINT_BODY)
            minted = _gateway(team_slug="acme").mint_capability(repo_slug="acme/widget")
        assert route.called
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["X-Team-Slug"] == "acme"
        assert json_module.loads(request.content) == {"repo_slug": "acme/widget", "kind": "presence"}
        assert minted.relay_url == MINT_BODY["relay_url"]
        assert minted.relay_token == MINT_BODY["relay_token"]
        assert minted.capability_credential == MINT_BODY["capability_credential"]
        assert minted.expires_at == MINT_BODY["expires_at"]

    def test_per_call_team_slug_overrides_the_static_selector(self) -> None:
        """The mint is asked of the team the pre-flight proved admits the
        repo, not whichever membership the local auth context happens to
        name — Team Kitty treats ``X-Team-Slug`` as a hard selector, so a
        member of teams A+B whose context selects A would deterministically
        403 a mint for a repo only B admits."""
        with respx.mock:
            route = respx.post(MINT).respond(201, json=MINT_BODY)
            _gateway(team_slug="team-a").mint_capability(repo_slug="acme/widget", team_slug="team-b")
        assert route.calls[0].request.headers["X-Team-Slug"] == "team-b"

    def test_no_override_falls_back_to_the_static_selector(self) -> None:
        with respx.mock:
            route = respx.post(MINT).respond(201, json=MINT_BODY)
            _gateway(team_slug="team-a").mint_capability(repo_slug="acme/widget")
        assert route.calls[0].request.headers["X-Team-Slug"] == "team-a"

    def test_neither_override_nor_static_sends_no_team_header(self) -> None:
        with respx.mock:
            route = respx.post(MINT).respond(201, json=MINT_BODY)
            _gateway().mint_capability(repo_slug="acme/widget")
        assert "X-Team-Slug" not in route.calls[0].request.headers

    def test_denial_carries_the_status_code(self) -> None:
        with respx.mock:
            respx.post(MINT).respond(403, json={"detail": "Capability denied.", "code": "repository_not_admitted"})
            with pytest.raises(CapabilityDenied) as exc_info:
                _gateway().mint_capability(repo_slug="acme/widget")
        assert exc_info.value.status_code == 403

    def test_unauthenticated_mint_is_also_a_capability_denied(self) -> None:
        with respx.mock:
            respx.post(MINT).respond(401)
            with pytest.raises(CapabilityDenied) as exc_info:
                _gateway().mint_capability(repo_slug="acme/widget")
        assert exc_info.value.status_code == 401

    def test_server_error_is_transient(self) -> None:
        with respx.mock:
            respx.post(MINT).respond(503, json={"detail": "mint_failed"})
            with pytest.raises(GatewayError) as exc_info:
                _gateway().mint_capability(repo_slug="acme/widget")
        assert not isinstance(exc_info.value, CapabilityDenied)

    def test_body_missing_relay_fields_is_transient_not_fatal(self) -> None:
        with respx.mock:
            respx.post(MINT).respond(201, json={"session_ref": "01ABC"})
            with pytest.raises(GatewayError):
                _gateway().mint_capability(repo_slug="acme/widget")

    def test_single_credential_response_yields_none_capability_field(self) -> None:
        body = dict(MINT_BODY, capability_credential="")
        with respx.mock:
            respx.post(MINT).respond(201, json=body)
            minted = _gateway().mint_capability(repo_slug="acme/widget")
        # Same reading as credentials.load: absent/empty means "use token".
        assert minted.capability_credential is None


# ---------------------------------------------------------------------------
# Expiry interpretation (verbatim stamps, caller policy lives here)
# ---------------------------------------------------------------------------


def test_expired_true_only_for_a_past_stamp() -> None:
    assert resolution._expired(_iso_in(-1)) is True
    assert resolution._expired(_iso_in(3600)) is False


def test_missing_or_garbled_stamps_never_expire() -> None:
    assert resolution._expired(None) is False
    assert resolution._expired("") is False
    assert resolution._expired("not-a-stamp") is False


def test_naive_stamp_never_raises_and_never_expires() -> None:
    """[controller-qa] MAJOR regression: ``expires_at`` is stored verbatim
    from the mint, and a stamp with no UTC offset parses fine but cannot be
    compared against the aware clock — ``aware >= naive`` raises
    ``TypeError``, which used to escape ``_expired`` (it caught only
    ``ValueError``) and then ``resolve_credentials`` itself, straight into
    the fire-and-forget seam. A naive stamp is treated like any other
    unparseable one: never expired, never raised."""
    assert resolution._expired("2026-08-25T12:00:00") is False  # naive, in the past


# ---------------------------------------------------------------------------
# The resolution core: cache, mint, negative TTL, force
# ---------------------------------------------------------------------------


KEY = "widget"
SLUG = "acme/widget"
HOST = "github.com"


class TestCacheShortCircuits:
    def test_unexpired_positive_answers_without_touching_the_network(self, state_root: Path) -> None:
        credentials.store(
            repo=KEY,
            relay_url="http://cached",
            token="tok",
            token_kind="presence",
            expires_at=_iso_in(3600),
        )
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.relay_url == "http://cached"
        assert gateway.admission_calls == [] and gateway.mint_calls == []

    def test_unexpired_negative_answers_no_without_network(self, state_root: Path) -> None:
        """A repo no team admits costs one lookup per TTL window, never one
        per transition."""
        credentials.store_negative(repo=KEY, reason="no_match", expires_at=_iso_in(300))
        gateway = ScriptedGateway()
        assert resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False) is None
        assert gateway.admission_calls == [] and gateway.mint_calls == []

    def test_force_skips_both_cached_answers_and_remints(self, state_root: Path) -> None:
        """The relay-403 recovery path: even a perfectly fresh credential is
        discarded when the caller says the relay just refused it."""
        credentials.store(repo=KEY, relay_url="http://stale", token="tok", token_kind="presence", expires_at=_iso_in(3600))
        credentials.store_negative(repo="other", reason="no_match", expires_at=_iso_in(300))
        gateway = ScriptedGateway(admission={"admitted": False, "reason": "no_match"})
        assert resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=True) is None
        assert len(gateway.admission_calls) == 1
        assert credentials.load_negative(repo=KEY) is not None

    def test_naive_stamp_on_a_stored_credential_answers_from_cache(self, state_root: Path) -> None:
        """[controller-qa] MAJOR regression, end to end through the cache
        path: a stored entry whose verbatim stamp has no UTC offset must
        answer from the store — never raise out of resolution."""
        credentials.store(
            repo=KEY,
            relay_url="http://naive",
            token="tok",
            token_kind="presence",
            expires_at="2026-08-25T12:00:00",
        )
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.relay_url == "http://naive"
        # Answered from cache — no network was touched deciding it.
        assert gateway.admission_calls == [] and gateway.mint_calls == []

    def test_naive_stamp_on_a_negative_answer_stays_silent_without_raising(self, state_root: Path) -> None:
        """And on the negative path: an unparseable-at-comparison stamp must
        not turn "stay silent" into "raise"."""
        credentials.store_negative(repo=KEY, reason="no_match", expires_at="2026-08-25T12:00:00")
        gateway = ScriptedGateway()
        assert resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False) is None
        assert gateway.admission_calls == [] and gateway.mint_calls == []


class TestScopeRevalidation:
    """Squad finding on #123: the store key is the bare repo NAME, which two
    differently-hosted repos can share -- a same-name checkout must not be
    served a credential minted for a different (host, repo_slug)."""

    def test_cache_hit_for_the_same_scope_is_trusted(self, state_root: Path) -> None:
        credentials.store(
            repo=KEY,
            relay_url="http://cached",
            token="tok",
            token_kind="presence",
            expires_at=_iso_in(3600),
            host=HOST,
            repo_slug=SLUG,
        )
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.relay_url == "http://cached"
        assert gateway.admission_calls == [] and gateway.mint_calls == []

    def test_cache_hit_scoped_to_a_different_repo_slug_falls_through_to_a_fresh_check(self, state_root: Path) -> None:
        """A hostile same-name checkout must not read someone else's cached
        admitted credential -- a scope mismatch is a cache miss, not a hit."""
        credentials.store(
            repo=KEY,
            relay_url="http://someone-elses-relay",
            token="someone-elses-token",
            token_kind="presence",
            expires_at=_iso_in(3600),
            host=HOST,
            repo_slug="other-owner/widget",
        )
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.relay_url == "http://relay"  # freshly minted, not the mismatched cache entry
        assert len(gateway.admission_calls) == 1
        assert len(gateway.mint_calls) == 1

    def test_cache_hit_scoped_to_a_different_host_falls_through_to_a_fresh_check(self, state_root: Path) -> None:
        credentials.store(
            repo=KEY,
            relay_url="http://someone-elses-relay",
            token="someone-elses-token",
            token_kind="presence",
            expires_at=_iso_in(3600),
            host="gitlab.com",
            repo_slug=SLUG,
        )
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.relay_url == "http://relay"
        assert len(gateway.admission_calls) == 1

    def test_legacy_entry_with_no_recorded_scope_is_still_trusted(self, state_root: Path) -> None:
        """Every credential minted before this fix (and every manual
        `zeitgeist checkout`) has no recorded scope -- it must keep being
        served from cache exactly as before, or every existing checkout
        would silently re-mint on its next transition."""
        credentials.store(
            repo=KEY,
            relay_url="http://legacy",
            token="legacy-tok",
            token_kind="presence",
            expires_at=_iso_in(3600),
        )
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.relay_url == "http://legacy"
        assert gateway.admission_calls == [] and gateway.mint_calls == []

    def test_a_fresh_mint_records_its_own_scope(self, state_root: Path) -> None:
        gateway = ScriptedGateway()
        resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        stored = credentials.load(repo=KEY)
        assert stored is not None
        assert stored.repo_slug == SLUG
        assert stored.host == HOST


class TestNotAdmitted:
    def test_admission_miss_stores_a_short_ttl_negative(self, state_root: Path) -> None:
        gateway = ScriptedGateway(admission={"admitted": False, "reason": "no_match"})
        assert resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False) is None
        negative = credentials.load_negative(repo=KEY)
        assert negative is not None
        assert negative.reason == "no_match"
        # The stamp really is a ~NEGATIVE_TTL_S horizon, parsed back.
        expiry = now_utc() + timedelta(seconds=resolution.NEGATIVE_TTL_S)
        assert resolution._expired(negative.expires_at) is False
        assert negative.expires_at is not None and abs((_parse(negative.expires_at) - expiry).total_seconds()) < 5

    def test_expired_negative_asks_again_and_can_flip_to_admitted(self, state_root: Path) -> None:
        credentials.store_negative(repo=KEY, reason="no_match", expires_at=_iso_in(-1))
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert credentials.load_negative(repo=KEY) is None


class TestMintPaths:
    def test_miss_mints_and_stores_under_the_canonical_key(self, state_root: Path) -> None:
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert gateway.admission_calls == [{"repo_slug": SLUG, "host": HOST}]
        assert gateway.mint_calls == [{"repo_slug": SLUG, "kind": "presence", "team_slug": None}]
        assert stored is not None
        assert stored.relay_url == "http://relay"
        assert stored.token_kind == "presence"
        assert stored.capability_credential == "jwt"
        # What came back is what the store holds -- same entry, same key.
        assert credentials.load(repo=KEY) == stored
        assert credentials.load_negative(repo=KEY) is None

    def test_mint_is_asked_of_the_team_admission_named(self, state_root: Path) -> None:
        """[squad] MAJOR regression: a member of teams A+B whose local auth
        context selects A, for a repo only B admits. The pre-flight answers
        ``admitted=true`` *naming B* — that slug is the disambiguating datum,
        and the mint must carry it as its ``X-Team-Slug``, or Team Kitty
        re-checks admission against A and deterministically 403s an admitted
        member into a cached negative."""
        gateway = ScriptedGateway(admission={"admitted": True, "team_slug": "team-b"})
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert gateway.mint_calls == [{"repo_slug": SLUG, "kind": "presence", "team_slug": "team-b"}]
        assert stored is not None
        # And the positive answer is cached, not a 5-minute silence.
        assert credentials.load(repo=KEY) == stored

    def test_mint_403_becomes_a_negative_answer(self, state_root: Path) -> None:
        """Membership revoked between pre-flight and mint: Team Kitty said
        no about THIS repo, so remember the no briefly."""
        gateway = ScriptedGateway(mint=CapabilityDenied("denied", status_code=403))
        assert resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False) is None
        negative = credentials.load_negative(repo=KEY)
        assert negative is not None
        assert negative.reason == "capability_denied"

    def test_mint_401_caches_nothing(self, state_root: Path) -> None:
        """An unusable session says nothing about the repo -- next call must
        ask again, not inherit a false 'not admitted'."""
        gateway = ScriptedGateway(mint=CapabilityDenied("unauthorized", status_code=401))
        assert resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False) is None
        assert credentials.load(repo=KEY) is None
        assert credentials.load_negative(repo=KEY) is None

    @pytest.mark.parametrize(
        "failure",
        [
            GatewayError("timeout"),
            GatewayError("HTTP 500"),
        ],
    )
    def test_transient_failures_cache_nothing(self, state_root: Path, failure: Exception) -> None:
        """A Team Kitty blip must not pin a false 'no team' onto an admitted
        repo for the whole negative TTL."""
        gateway = ScriptedGateway(admission=failure)
        assert resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False) is None
        assert credentials.load(repo=KEY) is None
        assert credentials.load_negative(repo=KEY) is None

    def test_expired_positive_credential_falls_through_to_the_mint(self, state_root: Path) -> None:
        credentials.store(
            repo=KEY,
            relay_url="http://old",
            token="old-tok",
            token_kind="presence",
            expires_at=_iso_in(-1),
        )
        gateway = ScriptedGateway()
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert len(gateway.mint_calls) == 1
        assert stored is not None
        assert stored.token == "bearer"


def _parse(stamp: str):
    return parse_iso(stamp)


# ---------------------------------------------------------------------------
# resolve_credentials end to end over a real clone: canonical key + slug
# derivation wired together (the only git-backed tests in this file)
# ---------------------------------------------------------------------------


def _checkout_with_origin(bare: Path, dest: Path, origin: str) -> Path:
    """A minimal checkout whose origin claims ``origin``."""
    bare.mkdir(parents=True)
    subprocess.run(["git", "init", "--bare", "-q"], cwd=bare, check=True, capture_output=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(dest)], check=True, capture_output=True)
    subprocess.run(["git", "remote", "set-url", "origin", origin], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=dest, check=True, capture_output=True)
    (dest / "f.txt").write_text("x")
    subprocess.run(["git", "add", "f.txt"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=dest, check=True, capture_output=True)
    return dest


@pytest.fixture()
def clone(tmp_path: Path) -> Path:
    """A checkout whose origin claims to be github.com/acme/widget."""
    return _checkout_with_origin(
        tmp_path / "gh" / "acme" / "widget.git",
        tmp_path / "work" / "acme" / "widget",
        "https://github.com/acme/widget.git",
    )


class TestResolveCredentialsEndToEnd:
    def test_identity_and_slug_are_derived_from_the_checkout_itself(self, state_root: Path, clone: Path, instead_of_rewrite: str) -> None:
        gateway = ScriptedGateway()
        stored = resolution.resolve_credentials(clone, gateway=gateway)  # type: ignore[arg-type]
        assert stored is not None
        # Store key: the (host, owner/repo) identity Team Kitty admits by ...
        assert credentials.load(repo="github.com/acme/widget") == stored
        # ... while Team Kitty is asked about the owner/repo slug + host.
        # The fixture rewrites github.com onto a machine-local transport
        # proxy; the checkout's own origin must win (#81) — a proxy host
        # here was Team Kitty being asked to admit a forge it never knew.
        assert gateway.admission_calls == [{"repo_slug": "acme/widget", "host": "github.com"}]
        assert instead_of_rewrite not in str(gateway.admission_calls)

    def test_second_call_never_leaves_the_machine(self, state_root: Path, clone: Path) -> None:
        first = ScriptedGateway()
        assert resolution.resolve_credentials(clone, gateway=first) is not None  # type: ignore[arg-type]
        second = ScriptedGateway()
        cached = resolution.resolve_credentials(clone, gateway=second)  # type: ignore[arg-type]
        assert cached is not None
        assert second.admission_calls == [] and second.mint_calls == []

    def test_directory_with_no_git_identity_stays_silent(self, state_root: Path, tmp_path: Path) -> None:
        plain = tmp_path / "not-a-repo"
        plain.mkdir()
        gateway = ScriptedGateway()
        assert resolution.resolve_credentials(plain, gateway=gateway) is None  # type: ignore[arg-type]
        assert gateway.admission_calls == []

    def test_local_path_origin_has_nothing_to_ask_about(self, state_root: Path, tmp_path: Path) -> None:
        bare = tmp_path / "server" / "acme" / "widget.git"
        bare.mkdir(parents=True)
        subprocess.run(["git", "init", "--bare", "-q"], cwd=bare, check=True, capture_output=True)
        dest = tmp_path / "local-only"
        subprocess.run(["git", "clone", "-q", str(bare), str(dest)], check=True, capture_output=True)
        gateway = ScriptedGateway()
        assert resolution.resolve_credentials(dest, gateway=gateway) is None  # type: ignore[arg-type]
        assert gateway.admission_calls == []


ACME_KEY = "github.com/acme/widget"
EVIL_KEY = "github.com/evil/widget"


class TestTwoCheckoutProbe:
    """spec-kitty#129's acceptance probe: ``acme/widget`` and ``evil/widget``
    are two same-named checkouts that differ in owner. Under the bare-name
    store key they shared ONE entry — the second checkout could be served
    (or overwrite) the first's cached credential, each resolution evicted
    the other's token back onto the network, and one checkout's "not
    admitted" negative silenced the other for the whole TTL."""

    @pytest.fixture()
    def two_clones(self, tmp_path: Path) -> tuple[Path, Path]:
        acme = _checkout_with_origin(
            tmp_path / "gh-acme" / "widget.git",
            tmp_path / "work" / "acme" / "widget",
            "https://github.com/acme/widget.git",
        )
        evil = _checkout_with_origin(
            tmp_path / "gh-evil" / "widget.git",
            tmp_path / "work" / "evil" / "widget",
            "https://github.com/evil/widget.git",
        )
        return acme, evil

    def test_each_checkout_mints_and_stores_under_its_own_key(self, state_root: Path, two_clones: tuple[Path, Path]) -> None:
        acme, evil = two_clones
        acme_gateway = ScriptedGateway()
        evil_gateway = ScriptedGateway()
        first = resolution.resolve_credentials(acme, gateway=acme_gateway)  # type: ignore[arg-type]
        second = resolution.resolve_credentials(evil, gateway=evil_gateway)  # type: ignore[arg-type]
        assert first is not None and second is not None
        # Distinct keys: neither entry is reachable under the other's.
        assert credentials.load(repo=ACME_KEY) == first
        assert credentials.load(repo=EVIL_KEY) == second
        assert credentials.load(repo="widget") is None
        # And each mint was asked about its own owner/repo slug.
        assert [call["repo_slug"] for call in acme_gateway.mint_calls] == ["acme/widget"]
        assert [call["repo_slug"] for call in evil_gateway.mint_calls] == ["evil/widget"]

    def test_second_checkout_mints_its_own_not_the_first_cached_one(self, state_root: Path, two_clones: tuple[Path, Path]) -> None:
        acme, evil = two_clones
        assert resolution.resolve_credentials(acme, gateway=ScriptedGateway()) is not None  # type: ignore[arg-type]
        evil_gateway = ScriptedGateway(
            mint=MintedCredential(
                relay_url="http://evil-relay",
                relay_token="evil-bearer",
                capability_credential="evil-jwt",
                expires_at=_iso_in(3600),
            )
        )
        stored = resolution.resolve_credentials(evil, gateway=evil_gateway)  # type: ignore[arg-type]
        assert stored is not None
        # Minted its own credential for its own slug -- not a re-serve of the
        # entry acme's resolution had already cached under the shared name.
        assert stored.relay_url == "http://evil-relay"
        assert [call["repo_slug"] for call in evil_gateway.mint_calls] == ["evil/widget"]
        assert credentials.load(repo=EVIL_KEY) == stored

    def test_one_checkouts_cached_answer_survives_the_other_resolving(self, state_root: Path, two_clones: tuple[Path, Path]) -> None:
        """Under the shared key each checkout's mint evicted the other's,
        forcing both onto the network on every transition; distinct keys
        keep both caches warm."""
        acme, evil = two_clones
        assert resolution.resolve_credentials(acme, gateway=ScriptedGateway()) is not None  # type: ignore[arg-type]
        assert resolution.resolve_credentials(evil, gateway=ScriptedGateway()) is not None  # type: ignore[arg-type]
        fresh_gateway = ScriptedGateway()
        cached = resolution.resolve_credentials(acme, gateway=fresh_gateway)  # type: ignore[arg-type]
        assert cached is not None
        assert fresh_gateway.admission_calls == [] and fresh_gateway.mint_calls == []

    def test_not_admitted_for_one_does_not_silence_the_other(self, state_root: Path, two_clones: tuple[Path, Path]) -> None:
        acme, evil = two_clones
        evil_gateway = ScriptedGateway(admission={"admitted": False, "reason": "no_match"})
        assert resolution.resolve_credentials(evil, gateway=evil_gateway) is None  # type: ignore[arg-type]
        assert credentials.load_negative(repo=EVIL_KEY) is not None
        acme_gateway = ScriptedGateway()
        stored = resolution.resolve_credentials(acme, gateway=acme_gateway)  # type: ignore[arg-type]
        # Admitted all along -- evil's negative must not answer for it.
        assert stored is not None
        assert len(acme_gateway.mint_calls) == 1


class TestDefaultGatewayConstruction:
    def test_env_config_builds_the_real_gateway(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "http://saas.test")
        monkeypatch.setenv("SPEC_KITTY_SAAS_TOKEN", "tok")
        monkeypatch.setenv("SPEC_KITTY_TEAM_SLUG", "acme")
        built = resolution._default_gateway(tmp_path)
        assert built is not None
        assert built._base_url == "http://saas.test"

    def test_nothing_configured_raises_saas_auth_error(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        monkeypatch.delenv("SPEC_KITTY_SAAS_TOKEN", raising=False)
        monkeypatch.delenv("SPEC_KITTY_TEAM_SLUG", raising=False)
        empty_root = tmp_path / "checkout-without-auth-file"
        (empty_root / ".git").mkdir(parents=True)
        with pytest.raises(SaasAuthError):
            resolution._default_gateway(empty_root)

    def test_unconfigured_checkout_resolves_quietly_to_none(self, state_root: Path, monkeypatch: pytest.MonkeyPatch, clone: Path) -> None:
        """The full quiet path: a real checkout, nothing configured -- the
        seam must see None, never an exception."""
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        monkeypatch.delenv("SPEC_KITTY_SAAS_TOKEN", raising=False)
        monkeypatch.delenv("SPEC_KITTY_TEAM_SLUG", raising=False)
        assert resolution.resolve_credentials(clone, auth_repo_root=clone) is None
        assert credentials.load(repo="github.com/acme/widget") is None


# --- #10: the admitting team is recorded with the mint ----------------------


class TestMintRecordsAdmittingTeam:
    def test_fresh_mint_stores_the_admission_answered_team_slug(self, state_root: Path) -> None:
        """The pre-flight is the one place the admitting team's slug is ever
        in hand; dropping it would leave `spec-kitty routes` nothing to name."""
        gateway = ScriptedGateway(admission={"admitted": True, "team_slug": "demo"})
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.team == "demo"
        assert credentials.load(repo=KEY) == stored

    def test_admission_without_a_team_slug_stores_team_none(self, state_root: Path) -> None:
        gateway = ScriptedGateway(admission={"admitted": True})
        stored = resolution._resolve(key=KEY, repo_slug=SLUG, host=HOST, gateway=gateway, kind=KIND_PRESENCE, force=False)
        assert stored is not None
        assert stored.team is None
