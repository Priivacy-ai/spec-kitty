"""Unit coverage for negotiated client-side admission (#3620, WP1).

* :func:`server_requires_strict_admission` — default False, explicit strict
  signals (env, config, handshake), and per-origin memoization.
* :func:`maybe_admit_locally` — the full guard matrix (consent / session /
  non-strict / not-already-admitted) and the labeled write it performs when
  every guard holds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.auth.session import StoredSession, Team
from specify_cli.delivery.targets import (
    LOCAL_NONSTRICT_AUDIENCE_PREFIX,
    ProjectDeliveryTargetRegistry,
)
from specify_cli.sync.admission_negotiation import (
    STRICT_ADMISSION_ENV_VAR,
    maybe_admit_locally,
    reset_strict_admission_cache,
    server_requires_strict_admission,
)
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_context import AdmissionState
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.target_authority import (
    OverrideMode,
    QueueScopeStatus,
    ResolvedSyncTarget,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000010"


@pytest.fixture(autouse=True)
def _isolated_strict_admission_cache() -> None:
    """Every test starts and ends with an empty memoization cache."""
    reset_strict_admission_cache()
    yield
    reset_strict_admission_cache()


def _target(server_url: str = "https://app.spec-kitty.ai", *, tmp_path: Path | None = None) -> ResolvedSyncTarget:
    return ResolvedSyncTarget(
        configured_server_url=server_url,
        env_server_url=None,
        override_mode=OverrideMode.NONE,
        resolved_server_url=server_url,
        user_id="operator@example.com",
        team_slug="private-teamspace-1",
        derived_queue_scope="scope-1",
        queue_db_path=(tmp_path or Path("/tmp")) / "queue.db",
        active_queue_scope_status=QueueScopeStatus.ABSENT,
    )


# --------------------------------------------------------------------------- #
# server_requires_strict_admission                                            #
# --------------------------------------------------------------------------- #


class TestServerRequiresStrictAdmission:
    def test_default_is_non_strict(self) -> None:
        assert server_requires_strict_admission("https://app.spec-kitty.ai") is False

    def test_env_override_is_strict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "1")
        assert server_requires_strict_admission("https://strict-env.example") is True

    def test_env_override_accepts_common_truthy_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "true")
        assert server_requires_strict_admission("https://strict-env-2.example") is True

    def test_env_falsy_value_stays_non_strict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "0")
        assert server_requires_strict_admission("https://strict-env-3.example") is False

    def test_handshake_admission_required_is_strict(self) -> None:
        handshake = {"admission": {"required": True}}
        assert server_requires_strict_admission("https://handshake.example", handshake=handshake) is True

    def test_handshake_admission_required_false_is_non_strict(self) -> None:
        handshake = {"admission": {"required": False}}
        assert server_requires_strict_admission("https://handshake-false.example", handshake=handshake) is False

    def test_handshake_missing_admission_key_is_non_strict(self) -> None:
        assert server_requires_strict_admission("https://handshake-empty.example", handshake={}) is False

    def test_config_table_strict_admission_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "specify_cli.sync.sync_runtime._read_event_sync_table",
            lambda: {"strict_admission": True},
        )
        assert server_requires_strict_admission("https://config-strict.example") is True

    def test_memoization_caches_first_result_per_origin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        origin = "https://memoized.example"
        first = server_requires_strict_admission(origin)
        assert first is False
        # The env flips AFTER the first resolution; the cached value must win.
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "1")
        second = server_requires_strict_admission(origin)
        assert second is False, "resolution must be memoized per origin, not re-evaluated per call"

    def test_reset_cache_clears_memoization(self, monkeypatch: pytest.MonkeyPatch) -> None:
        origin = "https://reset-me.example"
        assert server_requires_strict_admission(origin) is False
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "1")
        reset_strict_admission_cache()
        assert server_requires_strict_admission(origin) is True

    def test_different_origins_resolve_independently(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert server_requires_strict_admission("https://a.example") is False
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "1")
        assert server_requires_strict_admission("https://b.example") is True
        # The first origin's cached (non-strict) resolution is untouched.
        assert server_requires_strict_admission("https://a.example") is False

    def test_live_handshake_is_not_masked_by_cached_non_strict_verdict(self) -> None:
        """A per-call strict handshake wins even after an origin cached non-strict.

        Regression (#3626 landing review): the memo caches only the
        process-stable env/config inputs. A ``handshake=None`` resolution for an
        origin used to poison the cache so a *later* strict handshake for that
        same origin returned the stale non-strict value — exactly the transition
        that goes live when the SaaS #795 server starts advertising the
        handshake mid-process. The handshake must be evaluated live, ahead of
        the cache.
        """
        origin = "https://handshake-after-cache.example"
        # First call with no handshake caches the non-strict env/config verdict.
        assert server_requires_strict_admission(origin) is False
        # A subsequent strict handshake for the SAME origin must not be masked.
        assert (
            server_requires_strict_admission(origin, handshake={"admission": {"required": True}})
            is True
        )
        # The cached env/config verdict for a handshake-less call is unchanged.
        assert server_requires_strict_admission(origin) is False


# --------------------------------------------------------------------------- #
# maybe_admit_locally — the guard matrix                                      #
# --------------------------------------------------------------------------- #


def _session(*, private_teamspace: bool = True) -> StoredSession:
    from kernel.clock import now_utc, timedelta

    if private_teamspace:
        teams = [Team(id="team-private-1", name="Private", role="owner", is_private_teamspace=True)]
    else:
        teams = [Team(id="team-shared-1", name="Shared", role="member")]
    now = now_utc()
    return StoredSession(
        user_id="user-1",
        email="operator@example.com",
        name="Operator",
        teams=teams,
        default_team_id=teams[0].id,
        access_token="access-token",
        refresh_token="refresh-token",
        session_id="session-1",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=None,
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="device_code",
    )


class _FakeTokenManager:
    def __init__(self, session: StoredSession | None) -> None:
        self._session = session

    def get_current_session(self) -> StoredSession | None:
        return self._session


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    return ProjectSyncStore(PROJECT)


def _admitted_row(store: ProjectSyncStore):
    with store.unit_of_work() as unit:
        return ProjectDeliveryTargetRegistry(store).get_current(unit)


def _authenticate(monkeypatch: pytest.MonkeyPatch, *, private_teamspace: bool = True, no_session: bool = False) -> None:
    manager = _FakeTokenManager(None if no_session else _session(private_teamspace=private_teamspace))
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: manager)


class TestMaybeAdmitLocally:
    def test_all_guards_pass_writes_labeled_admitted_row(
        self,
        store: ProjectSyncStore,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        record_project_opt_in(PROJECT, actor="test-actor")
        _authenticate(monkeypatch)

        maybe_admit_locally(store, target=_target(tmp_path=tmp_path), routing_project_uuid=PROJECT)

        row = _admitted_row(store)
        assert row is not None
        assert row.admission_state is AdmissionState.ADMITTED
        assert row.admission_generation == 1
        assert row.binding_audience == f"{LOCAL_NONSTRICT_AUDIENCE_PREFIX}https://app.spec-kitty.ai"
        assert row.account_identity == "operator@example.com"
        assert row.private_teamspace_id == "team-private-1"

    def test_no_consent_is_noop(
        self,
        store: ProjectSyncStore,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _authenticate(monkeypatch)

        maybe_admit_locally(store, target=_target(tmp_path=tmp_path), routing_project_uuid=PROJECT)

        assert _admitted_row(store) is None

    def test_no_session_is_noop(
        self,
        store: ProjectSyncStore,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        record_project_opt_in(PROJECT, actor="test-actor")
        _authenticate(monkeypatch, no_session=True)

        maybe_admit_locally(store, target=_target(tmp_path=tmp_path), routing_project_uuid=PROJECT)

        assert _admitted_row(store) is None

    def test_no_private_teamspace_is_noop(
        self,
        store: ProjectSyncStore,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        record_project_opt_in(PROJECT, actor="test-actor")
        _authenticate(monkeypatch, private_teamspace=False)

        maybe_admit_locally(store, target=_target(tmp_path=tmp_path), routing_project_uuid=PROJECT)

        assert _admitted_row(store) is None

    def test_strict_server_is_noop(
        self,
        store: ProjectSyncStore,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        record_project_opt_in(PROJECT, actor="test-actor")
        _authenticate(monkeypatch)
        monkeypatch.setenv(STRICT_ADMISSION_ENV_VAR, "1")

        maybe_admit_locally(store, target=_target(tmp_path=tmp_path), routing_project_uuid=PROJECT)

        assert _admitted_row(store) is None

    def test_already_admitted_is_noop_and_idempotent(
        self,
        store: ProjectSyncStore,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        record_project_opt_in(PROJECT, actor="test-actor")
        _authenticate(monkeypatch)
        target = _target(tmp_path=tmp_path)

        maybe_admit_locally(store, target=target, routing_project_uuid=PROJECT)
        first_row = _admitted_row(store)
        assert first_row is not None

        # A second dispatch call must not re-mint or otherwise disturb the row
        # (AC-3): same identity, same generation, same label.
        maybe_admit_locally(store, target=target, routing_project_uuid=PROJECT)
        second_row = _admitted_row(store)
        assert second_row == first_row

    def test_repeated_calls_do_not_duplicate_rows(
        self,
        store: ProjectSyncStore,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        record_project_opt_in(PROJECT, actor="test-actor")
        _authenticate(monkeypatch)
        target = _target(tmp_path=tmp_path)

        for _ in range(3):
            maybe_admit_locally(store, target=target, routing_project_uuid=PROJECT)

        with store.unit_of_work() as unit:
            targets = ProjectDeliveryTargetRegistry(store).list_targets(unit)
        assert len(targets) == 1


class TestAdmitLocallyDirectIdempotency:
    """Direct coverage for admit_locally's already-admitted short-circuit.

    ``maybe_admit_locally`` never reaches this branch (it pre-empts on an
    already-ADMITTED row before calling ``admit_locally``), so exercise it
    directly: a repeat call with the identical audience returns the current
    row unchanged rather than rewriting it (AC-3, N-1).
    """

    def test_repeat_call_same_audience_returns_current_row_unchanged(
        self,
        store: ProjectSyncStore,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.target_authority import build_admission_audience

        audience = build_admission_audience(
            _target(tmp_path=tmp_path),
            account_identity="operator@example.com",
            private_teamspace_id="team-private-1",
            project_uuid=PROJECT,
            configuration_generation=1,
        )
        registry = ProjectDeliveryTargetRegistry(store)
        with store.unit_of_work() as unit:
            first = registry.admit_locally(unit, audience)
            # Second call sees its own committed row and short-circuits.
            second = registry.admit_locally(unit, audience)

        assert first.admission_state is AdmissionState.ADMITTED
        assert second == first
        assert second.binding_audience == f"{LOCAL_NONSTRICT_AUDIENCE_PREFIX}https://app.spec-kitty.ai"
        assert second.admission_generation == 1


class TestLocalAdmissionWireContract:
    """Pin what the local self-admission actually puts on the wire.

    Landing-pass security review (#3626) confirmed the local admission proof
    *is* transmitted — the `binding_audience` a locally-admitted context carries
    rides onto every delivery via ``attach_admission_proof``. That is by design
    (the paired #795 handoff relies on a strict server *receiving* the label to
    reject it — degrade, not corruption). The contract that matters is therefore
    not "nothing is sent" but "what is sent is honestly SELF-LABELED, never a
    forged server-issued proof": the wire `binding_audience` carries the
    ``local-nonstrict:`` prefix, so a strict server can distinguish and reject
    it rather than be fooled.
    """

    def test_wire_proof_is_self_labeled_local_nonstrict_never_forged(self) -> None:
        from specify_cli.saas_client.admission import (
            ProjectWriteAdmissionProof,
            attach_admission_proof,
        )

        # A context minted by maybe_admit_locally carries this exact audience.
        local_audience = f"{LOCAL_NONSTRICT_AUDIENCE_PREFIX}https://app.spec-kitty.ai"
        proof = ProjectWriteAdmissionProof(
            project_uuid=PROJECT,
            admission_generation=1,
            binding_audience=local_audience,
        )

        wire = attach_admission_proof({"event_id": "01HZZ"}, proof)

        # The label IS on the wire (not stripped) ...
        assert wire["binding_audience"] == local_audience
        # ... and it is honestly self-identifying as a LOCAL admission, so a
        # strict server can tell it apart from a server-issued audience and
        # reject it — it never poses as a forged server proof.
        assert str(wire["binding_audience"]).startswith(LOCAL_NONSTRICT_AUDIENCE_PREFIX)
        assert wire["admission_generation"] == 1
