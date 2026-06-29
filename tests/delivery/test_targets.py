"""Acceptance tests for the delivery-target registry (WP04, FR-002 / FR-012, C-002).

These tests pin **observable registry/DB state** (NFR-001), never internal call
sequencing. The headline behaviours they lock are:

* two distinct URLs (same scope) → two distinct target rows;
* the same canonical URL + same scope registers idempotently (one row), enforced
  by ``UNIQUE(url_hash, team_slug, user_email)`` (C-002);
* deployment metadata is recorded as provenance but **never** keys identity — a
  changed ``deployment_id`` under a stable URL does NOT fork identity, while a
  changed *stable* field (``server_instance_id``) raises an **advisory**
  :class:`ResetSignal` (FR-012);
* generated identifiers (``url_hash``, ``target_id``) are ASCII-only even for
  accented-Latin scope input (charter Identifier Safety).
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.delivery import (
    DeliveryTarget,
    DeliveryTargetRegistry,
    InvalidTargetUrlError,
    ResetSignal,
    SqliteDeliveryTargetRegistry,
    canonicalize_url,
    compute_url_hash,
)
from specify_cli.sync.target_authority import (
    OverrideMode,
    QueueScopeStatus,
    ResolvedSyncTarget,
)

pytestmark = pytest.mark.fast

URL_A = "https://target-a.example"
URL_B = "https://target-b.example"
TEAM = "acme"
EMAIL = "dev@acme.example"


@pytest.fixture
def registry() -> Iterator[SqliteDeliveryTargetRegistry]:
    reg = SqliteDeliveryTargetRegistry(":memory:")
    try:
        yield reg
    finally:
        reg.close()


def _resolved(
    url: str,
    *,
    team: str | None = TEAM,
    user: str | None = EMAIL,
    queue_db_path: Path,
) -> ResolvedSyncTarget:
    """Build a real WP01 ``ResolvedSyncTarget`` without invoking the resolver."""
    return ResolvedSyncTarget(
        configured_server_url=url,
        env_server_url=None,
        override_mode=OverrideMode.NONE,
        resolved_server_url=url,
        user_id=user,
        team_slug=team,
        derived_queue_scope=f"{url}|{user or ''}|{team or ''}",
        queue_db_path=queue_db_path,
        active_queue_scope_status=QueueScopeStatus.ABSENT,
    )


# --------------------------------------------------------------------------
# Identity: two URLs → two targets; same URL+scope → one row (UNIQUE/upsert)
# --------------------------------------------------------------------------


def test_two_urls_same_scope_yield_two_targets(registry: SqliteDeliveryTargetRegistry) -> None:
    a = registry.register(url=URL_A, team_slug=TEAM, user_email=EMAIL)
    b = registry.register(url=URL_B, team_slug=TEAM, user_email=EMAIL)

    assert a.url_hash != b.url_hash
    assert a.target_id != b.target_id
    assert len(registry.list_targets()) == 2


def test_same_url_same_scope_is_idempotent(registry: SqliteDeliveryTargetRegistry) -> None:
    first = registry.register(url=URL_A, team_slug=TEAM, user_email=EMAIL)
    again = registry.register(url=URL_A, team_slug=TEAM, user_email=EMAIL)

    assert first.target_id == again.target_id
    assert len(registry.list_targets()) == 1


def test_distinct_scope_yields_distinct_target(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(url=URL_A, team_slug=TEAM, user_email=EMAIL)
    registry.register(url=URL_A, team_slug="other-team", user_email=EMAIL)
    registry.register(url=URL_A, team_slug=TEAM, user_email="someone@else.example")

    assert len(registry.list_targets()) == 3


def test_anonymous_scope_none_and_empty_collapse(registry: SqliteDeliveryTargetRegistry) -> None:
    none_scope = registry.register(url=URL_A, team_slug=None, user_email=None)
    empty_scope = registry.register(url=URL_A, team_slug="", user_email="")

    assert none_scope.target_id == empty_scope.target_id
    assert len(registry.list_targets()) == 1
    assert none_scope.team_slug == ""
    assert none_scope.user_email == ""


# --------------------------------------------------------------------------
# Canonicalization equivalence + url_hash
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant",
    [
        "https://x.example/",
        "https://X.EXAMPLE",
        "https://x.example:443",
        "https://x.example:443/",
    ],
)
def test_cosmetic_url_variants_canonicalize_equal(variant: str) -> None:
    base = canonicalize_url("https://x.example")
    assert canonicalize_url(variant) == base
    assert compute_url_hash(canonicalize_url(variant)) == compute_url_hash(base)


def test_cosmetic_variants_register_as_one_target(registry: SqliteDeliveryTargetRegistry) -> None:
    for variant in ("https://x.example", "https://x.example/", "https://X.EXAMPLE:443"):
        registry.register(url=variant, team_slug=TEAM, user_email=EMAIL)
    assert len(registry.list_targets()) == 1


def test_distinct_endpoints_hash_distinct() -> None:
    assert compute_url_hash(canonicalize_url(URL_A)) != compute_url_hash(canonicalize_url(URL_B))


def test_url_hash_is_one_way_digest() -> None:
    digest = compute_url_hash(canonicalize_url(URL_A))
    assert URL_A not in digest
    assert len(digest) == 64  # sha256 hexdigest


@pytest.mark.parametrize(
    "bad", ["", "   ", "not-a-url", "://missing-scheme", "https://", "https://x.example:notaport"]
)
def test_malformed_url_raises(bad: str) -> None:
    with pytest.raises(InvalidTargetUrlError):
        canonicalize_url(bad)


def test_non_default_port_is_preserved() -> None:
    canonical = canonicalize_url("https://x.example:8443")
    assert canonical == "https://x.example:8443"
    # A non-default port is identity-significant: distinct from the default-port URL.
    assert compute_url_hash(canonical) != compute_url_hash(canonicalize_url("https://x.example"))


def test_idn_host_canonicalizes_to_ascii() -> None:
    canonical = canonicalize_url("https://café.example/")
    assert canonical.isascii() is True
    assert "xn--" in canonical  # IDNA/punycode-encoded host


def test_unencodable_idn_host_falls_back_to_ascii() -> None:
    # A non-ASCII label too long to IDNA-encode must still yield an ASCII
    # canonical URL via the allowlist fallback (Identifier Safety, defensive).
    canonical = canonicalize_url("https://" + ("é" * 64) + ".example")
    assert canonical.isascii() is True


# --------------------------------------------------------------------------
# Deployment metadata recorded as provenance — never keyed on
# --------------------------------------------------------------------------


def test_provenance_absent_is_valid(registry: SqliteDeliveryTargetRegistry) -> None:
    target = registry.register(url=URL_A, team_slug=TEAM, user_email=EMAIL)
    assert target.server_instance_id is None
    assert target.deployment_id is None
    assert target.environment_name is None
    assert target.git_sha is None


def test_full_provenance_round_trips(registry: SqliteDeliveryTargetRegistry) -> None:
    meta = {
        "server_instance_id": "srv-1",
        "deployment_id": "dep-1",
        "environment_name": "preview-x",
        "git_sha": "abc123",
    }
    registry.register(url=URL_A, team_slug=TEAM, user_email=EMAIL, deployment_metadata=meta)
    stored = registry.get(compute_url_hash(canonicalize_url(URL_A)), TEAM, EMAIL)
    assert stored is not None
    assert stored.server_instance_id == "srv-1"
    assert stored.deployment_id == "dep-1"
    assert stored.environment_name == "preview-x"
    assert stored.git_sha == "abc123"


def test_partial_provenance_is_storable(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        deployment_metadata={"deployment_id": "only-dep"},
    )
    stored = registry.get(compute_url_hash(canonicalize_url(URL_A)), TEAM, EMAIL)
    assert stored is not None
    assert stored.deployment_id == "only-dep"
    assert stored.server_instance_id is None


def test_new_metadata_updates_provenance_without_forking(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        deployment_metadata={"server_instance_id": "srv-1", "deployment_id": "dep-1"},
    )
    registry.register(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        deployment_metadata={"server_instance_id": "srv-1", "deployment_id": "dep-2"},
    )
    assert len(registry.list_targets()) == 1
    stored = registry.get(compute_url_hash(canonicalize_url(URL_A)), TEAM, EMAIL)
    assert stored is not None
    assert stored.deployment_id == "dep-2"  # latest provenance recorded


# --------------------------------------------------------------------------
# FR-012: advisory reset-detection (stable-field change flags; dep_id is noise)
# --------------------------------------------------------------------------


def test_reset_flagged_on_stable_field_change(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        deployment_metadata={"server_instance_id": "srv-1"},
    )
    signal = registry.detect_reset(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        new_deployment_metadata={"server_instance_id": "srv-2"},
    )
    assert isinstance(signal, ResetSignal)
    assert "server_instance_id" in signal.changed_fields
    # detect_reset is read-only: no identity fork.
    assert len(registry.list_targets()) == 1


def test_deployment_id_only_change_is_not_a_reset(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        deployment_metadata={"server_instance_id": "srv-1", "deployment_id": "dep-1"},
    )
    signal = registry.detect_reset(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        new_deployment_metadata={"server_instance_id": "srv-1", "deployment_id": "dep-2"},
    )
    assert signal is None
    assert len(registry.list_targets()) == 1


def test_reset_none_when_target_unregistered(registry: SqliteDeliveryTargetRegistry) -> None:
    signal = registry.detect_reset(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        new_deployment_metadata={"server_instance_id": "srv-1"},
    )
    assert signal is None


def test_reset_none_when_no_prior_metadata(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(url=URL_A, team_slug=TEAM, user_email=EMAIL)  # no metadata
    signal = registry.detect_reset(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        new_deployment_metadata={"server_instance_id": "srv-1"},
    )
    assert signal is None  # appearing metadata is not a reset


def test_reset_none_when_incoming_metadata_absent(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        deployment_metadata={"server_instance_id": "srv-1"},
    )
    signal = registry.detect_reset(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        new_deployment_metadata=None,
    )
    assert signal is None


def test_reset_lists_multiple_changed_stable_fields(registry: SqliteDeliveryTargetRegistry) -> None:
    registry.register(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        deployment_metadata={"server_instance_id": "srv-1", "git_sha": "aaa"},
    )
    signal = registry.detect_reset(
        url=URL_A,
        team_slug=TEAM,
        user_email=EMAIL,
        new_deployment_metadata={"server_instance_id": "srv-2", "git_sha": "bbb"},
    )
    assert signal is not None
    assert set(signal.changed_fields) == {"server_instance_id", "git_sha"}


# --------------------------------------------------------------------------
# WP01 integration: identity derived from ResolvedSyncTarget
# --------------------------------------------------------------------------


def test_register_from_resolved_derives_identity(
    registry: SqliteDeliveryTargetRegistry, tmp_path: Path
) -> None:
    target = registry.register_from_resolved(
        _resolved(URL_A, queue_db_path=tmp_path / "queue.db")
    )
    assert target.url_hash == compute_url_hash(canonicalize_url(URL_A))
    assert target.team_slug == TEAM
    assert target.user_email == EMAIL


def test_register_from_resolved_anonymous(
    registry: SqliteDeliveryTargetRegistry, tmp_path: Path
) -> None:
    target = registry.register_from_resolved(
        _resolved(URL_A, team=None, user=None, queue_db_path=tmp_path / "queue.db")
    )
    assert target.team_slug == ""
    assert target.user_email == ""
    assert len(registry.list_targets()) == 1


# --------------------------------------------------------------------------
# Identifier Safety (charter — binding): non-ASCII scope → ASCII identifiers
# --------------------------------------------------------------------------


def test_non_ascii_scope_produces_ascii_identifiers(registry: SqliteDeliveryTargetRegistry) -> None:
    target = registry.register(
        url=URL_A,
        team_slug="café-équipe",
        user_email="björn@acme.example",
        deployment_metadata={"environment_name": "pré-prod"},
    )
    assert target.target_id.isascii() is True
    assert target.url_hash.isascii() is True


# --------------------------------------------------------------------------
# Seam: the concrete registry satisfies the WP04 protocol (IC-01 / C-001)
# --------------------------------------------------------------------------


def test_registry_satisfies_protocol(registry: SqliteDeliveryTargetRegistry) -> None:
    assert isinstance(registry, DeliveryTargetRegistry)


def test_public_surface_exposes_value_objects() -> None:
    assert DeliveryTarget is not None
    assert ResetSignal is not None


def test_registry_is_a_context_manager() -> None:
    with SqliteDeliveryTargetRegistry(":memory:") as reg:
        target = reg.register(url=URL_A, team_slug=TEAM, user_email=EMAIL)
        assert target.url_hash == compute_url_hash(canonicalize_url(URL_A))
        assert len(reg.list_targets()) == 1
