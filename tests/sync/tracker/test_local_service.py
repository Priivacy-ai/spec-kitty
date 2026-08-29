"""Tests for LocalTrackerService — beads/fp direct-connector extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.credentials import TrackerCredentialStore
from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict
from specify_cli.tracker.local_service import (
    LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
    LocalTrackerEgressRefusedError,
    LocalTrackerService,
    LocalTrackerServiceError,
)
from specify_cli.tracker.service import TrackerService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.unit, pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Create a minimal repo root with .kittify directory."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    return tmp_path


@pytest.fixture()
def cred_path(tmp_path: Path) -> Path:
    """Isolated credential file path."""
    return tmp_path / ".spec-kitty" / "credentials"


def _make_service(
    repo_root: Path,
    config: TrackerProjectConfig | None = None,
    cred_path: Path | None = None,
) -> LocalTrackerService:
    svc = LocalTrackerService(repo_root, config or TrackerProjectConfig())
    if cred_path is not None:
        svc.credential_store = TrackerCredentialStore(path=cred_path)
    return svc


def _read_config_payload(repo_root: Path) -> dict[str, Any]:
    """Read `.kittify/config.yaml` as a raw mapping -- used to assert a sibling top-level
    block (e.g. `sync:`) survived a `bind`, independently of `TrackerProjectConfig`'s own
    parsing of the `tracker:` sub-block (FR-011 A1's control)."""
    from ruamel.yaml import YAML

    yaml = YAML()
    config_path = repo_root / ".kittify" / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.load(handle) or {}
    return dict(payload) if isinstance(payload, dict) else {}


def _seed_committed_tracker_config(repo_root: Path, *, egress: str) -> None:
    """Commit a `tracker.egress` decision plus a sibling `sync:` block directly, bypassing
    `LocalTrackerService.bind` entirely -- this is the pre-bind, on-disk state FR-011 site A1
    must not erase."""
    config_path = repo_root / ".kittify" / "config.yaml"
    config_path.write_text(
        "tracker:\n"
        "  provider: beads\n"
        "  workspace: old-ws\n"
        f"  egress: {egress}\n"
        "sync:\n"
        "  enabled: true\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# bind
# ---------------------------------------------------------------------------


class TestBind:
    def test_bind_stores_config_and_credentials(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        config = svc.bind(
            provider="beads",
            workspace="my-ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={"command": "beads"},
        )
        assert config.provider == "beads"
        assert config.workspace == "my-ws"

        # Config persisted to disk
        loaded = load_tracker_config(repo)
        assert loaded.provider == "beads"
        assert loaded.workspace == "my-ws"

        # Credentials persisted
        stored = svc.credential_store.get_provider("beads")
        assert stored["command"] == "beads"

    def test_bind_normalizes_provider(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        config = svc.bind(
            provider="  FP  ",
            workspace="ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={"command": "fp"},
        )
        assert config.provider == "fp"

    def test_bind_no_credentials(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        config = svc.bind(
            provider="beads",
            workspace="ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={},
        )
        assert config.provider == "beads"
        # No credentials stored — get_provider returns empty dict
        assert svc.credential_store.get_provider("beads") == {}

    def test_bind_with_doctrine_field_owners(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        owners = {"title": "external", "status": "local"}
        config = svc.bind(
            provider="fp",
            workspace="ws",
            ownership_mode="split",
            ownership_field_owners=owners,
            credentials={"command": "fp"},
        )
        assert config.ownership_mode == "split"
        assert config.ownership_field_owners == owners


# ---------------------------------------------------------------------------
# FR-011 site A1: bind must carry a committed egress decision forward
# (T024). Pinned in both directions, with the sibling `sync:` block asserted
# present as the control -- proves the file was written and the rest
# survived, so a missing `egress` key is erasure, not a write failure.
# ---------------------------------------------------------------------------


class TestBindPreservesEgress:
    """`LocalTrackerService.bind` (`local_service.py:57`) built a **fresh**
    `TrackerProjectConfig` from only its own keyword arguments and saved that -- discarding a
    committed `tracker.egress` decision on every bind. Erasing a `refused` is a silent
    fail-open; erasing a `permitted` silently withdraws a working local binding (#3108)."""

    def test_bind_preserves_committed_refused_egress(self, repo: Path, cred_path: Path) -> None:
        _seed_committed_tracker_config(repo, egress="refused")
        svc = _make_service(repo, cred_path=cred_path)

        svc.bind(
            provider="beads",
            workspace="new-ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={},
        )

        loaded = load_tracker_config(repo)
        assert loaded.egress == "refused", "a committed refusal must outlive a bind (FR-011 A1)"
        payload = _read_config_payload(repo)
        assert payload.get("sync", {}).get("enabled") is True, "sibling sync: block control"

    def test_bind_preserves_committed_permitted_egress(self, repo: Path, cred_path: Path) -> None:
        _seed_committed_tracker_config(repo, egress="permitted")
        svc = _make_service(repo, cred_path=cred_path)

        svc.bind(
            provider="beads",
            workspace="new-ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={},
        )

        loaded = load_tracker_config(repo)
        assert loaded.egress == "permitted", "a committed grant must outlive a bind (FR-011 A1)"
        payload = _read_config_payload(repo)
        assert payload.get("sync", {}).get("enabled") is True, "sibling sync: block control"


class TestTrackerServiceBindPreservesEgressEndToEnd:
    """The end-to-end `TrackerService.bind` preservation pin (T024 step 2) -- this pin is
    WP04's, not WP02's. WP02 fixed `service.py:163` to hand `LocalTrackerService` the loaded
    config, but that fix is inert on disk until `LocalTrackerService.bind` itself stops
    discarding it (`TestBindPreservesEgress` above). WP02 could not have earned this pin: it
    is forbidden `local_service.py`, and a pin it could write would have been red before its
    own fix and red after -- only the fix in *this* file makes it green."""

    def test_trackerservice_bind_preserves_committed_refused_egress(self, repo: Path) -> None:
        _seed_committed_tracker_config(repo, egress="refused")

        service = TrackerService(repo)
        service.bind(
            provider="beads",
            workspace="new-ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={},
        )

        loaded = load_tracker_config(repo)
        assert loaded.egress == "refused", "TrackerService.bind must preserve a committed refusal on disk"
        payload = _read_config_payload(repo)
        assert payload.get("sync", {}).get("enabled") is True, "sibling sync: block control"

    def test_trackerservice_bind_preserves_committed_permitted_egress(self, repo: Path) -> None:
        _seed_committed_tracker_config(repo, egress="permitted")

        service = TrackerService(repo)
        service.bind(
            provider="beads",
            workspace="new-ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={},
        )

        loaded = load_tracker_config(repo)
        assert loaded.egress == "permitted", "TrackerService.bind must preserve a committed grant on disk"
        payload = _read_config_payload(repo)
        assert payload.get("sync", {}).get("enabled") is True, "sibling sync: block control"


# ---------------------------------------------------------------------------
# FR-001: the tracker-egress verdict gates sync_pull/sync_push/sync_run as
# the first executable statement, ahead of _load_runtime (T022).
# ---------------------------------------------------------------------------


class TestEgressGate:
    """A refusing project must be told it refused, before anything is read or created on its
    behalf -- never a silent no-op, never `_load_runtime`'s own errors standing in for the
    refusal (T022's edge case: the verdict outranks configuration completeness)."""

    def test_sync_pull_refuses_when_neither_channel_permits(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        with pytest.raises(LocalTrackerEgressRefusedError):
            svc.sync_pull()

    def test_sync_push_refuses_when_neither_channel_permits(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        with pytest.raises(LocalTrackerEgressRefusedError):
            svc.sync_push()

    def test_sync_run_refuses_when_neither_channel_permits(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        with pytest.raises(LocalTrackerEgressRefusedError):
            svc.sync_run()

    def test_gate_outranks_incomplete_binding_error(self, repo: Path, cred_path: Path) -> None:
        """An incomplete binding (provider set, workspace missing) in a refusing project must
        surface the egress refusal, not `_load_runtime`'s 'incomplete' error -- telling an
        operator to finish a binding they are not permitted to use is worse advice than
        telling them why they are refused."""
        broken_config = TrackerProjectConfig(provider="beads", workspace=None)
        save_tracker_config(repo, broken_config)
        svc = _make_service(repo, cred_path=cred_path)

        with pytest.raises(LocalTrackerEgressRefusedError):
            svc.sync_push()

    def test_permitted_egress_reaches_past_the_gate(self, repo: Path, cred_path: Path) -> None:
        """Positive control: a Channel-2 grant reaches past the gate -- the next failure
        (unconfigured tracker, from `_load_runtime`) proves the gate did not swallow this
        call silently."""
        config_path = repo / ".kittify" / "config.yaml"
        config_path.write_text("tracker:\n  egress: permitted\n", encoding="utf-8")
        svc = _make_service(repo, cred_path=cred_path)

        with pytest.raises(LocalTrackerServiceError, match="not configured") as exc_info:
            svc.sync_push()
        assert not isinstance(exc_info.value, LocalTrackerEgressRefusedError)


class TestRefusalMessageIdentity:
    """FR-012 / T023 step 3: the raised message equals `verdict.message` for the same
    verdict, so a later edit that re-composes text at the raise site reds. The exception also
    carries `verdict.remedies` unchanged, because a raise site must render both fields
    together, never `message` alone (review round 1, MEDIUM-3)."""

    def test_sync_push_raises_with_verdict_message_and_remedies_verbatim(
        self, repo: Path, cred_path: Path
    ) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        expected = tracker_egress_verdict(
            repo,
            destination=EgressDestination.LOCAL_SUBPROCESS,
            # Exactly what `LocalTrackerService` passes: this test compares the raised
            # message against a re-derived one, so a different fragment here would compare
            # two strings that were never meant to agree.
            identifiers=LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
        )
        assert expected.refused, "precondition: nothing consents at either channel"

        with pytest.raises(LocalTrackerEgressRefusedError) as exc_info:
            svc.sync_push()

        assert exc_info.value.message == expected.message
        assert exc_info.value.remedies == expected.remedies

    def test_rendered_text_carries_both_message_and_remedies(self, repo: Path, cred_path: Path) -> None:
        """The highest false-red risk this WP carries: at LOCAL_SUBPROCESS the Channel-2 grant
        remedy lives only in `remedies`, never folded into `message`. Rendering `message`
        alone would silently drop it from what `_run_or_exit` prints."""
        svc = _make_service(repo, cred_path=cred_path)
        expected = tracker_egress_verdict(
            repo,
            destination=EgressDestination.LOCAL_SUBPROCESS,
            # Exactly what `LocalTrackerService` passes: this test compares the raised
            # message against a re-derived one, so a different fragment here would compare
            # two strings that were never meant to agree.
            identifiers=LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
        )
        assert expected.remedies, "precondition: this verdict has at least one remedy to drop"

        with pytest.raises(LocalTrackerEgressRefusedError) as exc_info:
            svc.sync_push()

        rendered = str(exc_info.value)
        assert expected.message in rendered
        for remedy in expected.remedies:
            assert remedy in rendered


# ---------------------------------------------------------------------------
# unbind
# ---------------------------------------------------------------------------


class TestUnbind:
    def test_unbind_clears_config_and_credentials(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        # Bind first
        svc.bind(
            provider="beads",
            workspace="ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={"command": "beads"},
        )
        # Verify bound
        assert load_tracker_config(repo).is_configured

        # Unbind
        svc.unbind()

        # Config cleared
        loaded = load_tracker_config(repo)
        assert not loaded.is_configured

        # Credentials cleared
        assert svc.credential_store.get_provider("beads") == {}

    def test_unbind_without_provider_does_not_crash(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        # Unbind when nothing is configured — should not raise
        svc.unbind()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_unconfigured(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        result = svc.status()
        assert result["configured"] is False
        assert result["provider"] is None
        assert result["issue_count"] == 0
        assert result["mapping_count"] == 0

    def test_status_configured(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={"command": "beads"},
        )

        with patch.object(
            svc, "_run_async", return_value=[]
        ):
            result = svc.status()

        assert result["configured"] is True
        assert result["provider"] == "beads"
        assert result["workspace"] == "ws"
        assert result["credentials_present"] is True


# ---------------------------------------------------------------------------
# sync operations — verify delegation to connector
# ---------------------------------------------------------------------------


class TestSyncOperations:
    """Verify sync_pull/push/run wire up to the direct connector correctly.

    We mock _build_engine to avoid needing the spec_kitty_tracker package.
    """

    def _setup_bound_service(self, repo: Path, cred_path: Path) -> LocalTrackerService:
        # T026 (C-012(1)): one committed config line -- `tracker.egress: permitted` -- so
        # FR-001's gate (T022) does not refuse this class's own delegation-assertion fixture,
        # which records no consent at either channel. This is possible only because T024
        # already landed: before it, `bind` below would have discarded this decision by
        # building a fresh `TrackerProjectConfig` from only its keyword arguments.
        save_tracker_config(repo, TrackerProjectConfig(egress="permitted"))
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={"command": "beads"},
        )
        return svc

    def _mock_engine_result(self) -> MagicMock:
        """Create a mock sync result compatible with _sync_result()."""
        result = MagicMock()
        result.stats.pulled_created = 1
        result.stats.pulled_updated = 2
        result.stats.pushed_created = 0
        result.stats.pushed_updated = 0
        result.stats.skipped = 0
        result.conflicts = []
        result.errors = []
        return result

    def test_sync_pull_delegates_to_connector(self, repo: Path, cred_path: Path) -> None:
        svc = self._setup_bound_service(repo, cred_path)
        mock_result = self._mock_engine_result()

        mock_connector = MagicMock()
        mock_connector.name = "beads"
        mock_engine = MagicMock()
        mock_engine.checkpoint = MagicMock()

        async def mock_pull(limit: int = 100) -> Any:
            return mock_result

        mock_engine.pull = mock_pull

        with patch.object(svc, "_build_engine", return_value=(mock_connector, mock_engine)):
            with patch(
                "specify_cli.tracker.local_service.TrackerSqliteStore"
            ) as MockStore:
                mock_store = MagicMock()
                mock_store.get_checkpoint.return_value = None
                MockStore.return_value = mock_store

                result = svc.sync_pull(limit=50)

        assert result["provider"] == "beads"
        assert result["stats"]["pulled_created"] == 1
        assert result["stats"]["pulled_updated"] == 2

    def test_sync_push_delegates_to_connector(self, repo: Path, cred_path: Path) -> None:
        svc = self._setup_bound_service(repo, cred_path)
        mock_result = self._mock_engine_result()

        mock_connector = MagicMock()
        mock_connector.name = "beads"
        mock_engine = MagicMock()

        async def mock_push(limit: int = 100) -> Any:
            return mock_result

        mock_engine.push = mock_push

        with patch.object(svc, "_build_engine", return_value=(mock_connector, mock_engine)):
            with patch(
                "specify_cli.tracker.local_service.TrackerSqliteStore"
            ) as MockStore:
                mock_store = MagicMock()
                MockStore.return_value = mock_store

                result = svc.sync_push(limit=50)

        assert result["provider"] == "beads"

    def test_sync_run_delegates_to_connector(self, repo: Path, cred_path: Path) -> None:
        svc = self._setup_bound_service(repo, cred_path)
        mock_result = self._mock_engine_result()

        mock_connector = MagicMock()
        mock_connector.name = "beads"
        mock_engine = MagicMock()
        mock_engine.checkpoint = MagicMock()

        async def mock_sync(limit: int = 100) -> Any:
            return mock_result

        mock_engine.sync = mock_sync

        with patch.object(svc, "_build_engine", return_value=(mock_connector, mock_engine)):
            with patch(
                "specify_cli.tracker.local_service.TrackerSqliteStore"
            ) as MockStore:
                mock_store = MagicMock()
                mock_store.get_checkpoint.return_value = None
                MockStore.return_value = mock_store

                result = svc.sync_run(limit=50)

        assert result["provider"] == "beads"


# ---------------------------------------------------------------------------
# map_add / map_list
# ---------------------------------------------------------------------------


class TestMapOperations:
    def test_map_add_and_list_roundtrip(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={"command": "beads"},
        )

        mock_ref_cls = MagicMock()
        mock_store = MagicMock()
        mock_store.list_mappings.return_value = [
            {
                "wp_id": "WP01",
                "external_id": "BEAD-1",
                "external_key": "K1",
                "external_url": None,
            }
        ]

        with patch.object(svc, "_load_runtime", return_value=(
            load_tracker_config(repo),
            {"command": "beads"},
            mock_store,
        )):
            with patch(
                "specify_cli.tracker.local_service.LocalTrackerService.map_add",
                wraps=None,
            ):
                # Directly test map_list via the mocked runtime
                mappings = svc.map_list()

        assert len(mappings) == 1
        assert mappings[0]["wp_id"] == "WP01"

    def test_map_add_calls_upsert(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        svc.bind(
            provider="beads",
            workspace="ws",
            ownership_mode="external_authoritative",
            ownership_field_owners={},
            credentials={"command": "beads"},
        )

        mock_store = MagicMock()
        config = load_tracker_config(repo)

        # Build a fake spec_kitty_tracker.models module with ExternalRef
        mock_external_ref_instance = MagicMock()
        mock_external_ref_cls = MagicMock(return_value=mock_external_ref_instance)
        fake_models = MagicMock()
        fake_models.ExternalRef = mock_external_ref_cls

        import sys

        with patch.object(svc, "_load_runtime", return_value=(
            config,
            {"command": "beads"},
            mock_store,
        )):
            with patch.dict(sys.modules, {"spec_kitty_tracker": MagicMock(), "spec_kitty_tracker.models": fake_models}):
                svc.map_add(
                    wp_id="WP01",
                    external_id="BEAD-1",
                    external_key="K1",
                    external_url=None,
                )

        mock_external_ref_cls.assert_called_once_with(
            system="beads",
            workspace="ws",
            id="BEAD-1",
            key="K1",
            url=None,
        )
        mock_store.upsert_mapping.assert_called_once_with(
            wp_id="WP01", ref=mock_external_ref_instance,
        )


# ---------------------------------------------------------------------------
# _load_runtime
# ---------------------------------------------------------------------------


class TestLoadRuntime:
    def test_load_runtime_raises_when_not_configured(self, repo: Path, cred_path: Path) -> None:
        svc = _make_service(repo, cred_path=cred_path)
        with pytest.raises(LocalTrackerServiceError, match="not configured"):
            svc._load_runtime()

    def test_load_runtime_raises_when_provider_missing(self, repo: Path, cred_path: Path) -> None:
        # Save config with provider but no workspace
        broken_config = TrackerProjectConfig(provider="beads", workspace=None)
        save_tracker_config(repo, broken_config)

        svc = _make_service(repo, cred_path=cred_path)
        with pytest.raises(LocalTrackerServiceError, match="not configured|incomplete"):
            svc._load_runtime()


class TestLocalSyncPublishUnsupported:
    """#3168: local providers (beads/fp) have no snapshot-publish transport.

    ``TrackerService.sync_publish`` delegates unconditionally to the backend, so
    a local binding used to hit ``AttributeError: 'LocalTrackerService' object has
    no attribute 'sync_publish'`` -- which the CLI's ``_run_or_exit`` does NOT catch
    (it catches ``RuntimeError``/``ValueError``), so the operator saw a raw traceback.
    It must surface a clean ``LocalTrackerServiceError`` (a ``RuntimeError`` subclass).
    """

    def test_local_sync_publish_raises_local_tracker_service_error(self, repo: Path) -> None:
        svc = _make_service(repo)
        with pytest.raises(LocalTrackerServiceError, match="not supported for local providers"):
            svc.sync_publish()

    def test_facade_sync_publish_on_local_binding_raises_cleanly_not_attributeerror(
        self, repo: Path
    ) -> None:
        # The real regression path: the CLI calls TrackerService.sync_publish, which
        # delegates to the resolved (local) backend. Before #3168 this raised
        # AttributeError; it must be a RuntimeError-family error the CLI can render.
        svc = _make_service(repo)
        with patch.object(TrackerService, "_resolve_backend", return_value=svc):
            with pytest.raises(LocalTrackerServiceError):
                TrackerService(repo).sync_publish()
        # RuntimeError subclass == caught by the CLI's _run_or_exit (exit 1, clean message).
        assert issubclass(LocalTrackerServiceError, RuntimeError)


# ---------------------------------------------------------------------------
# No SaaS imports
# ---------------------------------------------------------------------------


class TestNoSaaSImports:
    """Verify no SaaS-related imports leak into local_service module."""

    def test_no_saas_client_import(self) -> None:
        """No SaaS module is *imported* here -- asserted over the parsed import statements.

        Previously a substring scan (``"saas_client" not in source``) that banned the token
        anywhere in the file, prose included. That was both too weak and too strong: it missed
        ``from specify_cli.tracker import saas_client`` and ``import
        specify_cli.tracker.saas_client as _c`` (neither contains the banned literal
        ``from specify_cli.tracker.saas``), while red-ing a docstring that merely *explains*
        why this module does not import the hosted client -- which is exactly the prose a
        reader needs to not "tidy" the separation away. Parsing the imports pins the real
        contract and is indifferent to comments and docstrings.
        """
        import ast

        import specify_cli.tracker.local_service as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        imported: list[str] = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                imported.append(base)
                imported.extend(f"{base}.{a.name}" for a in node.names)

        offenders = [m for m in imported if "saas" in m.lower()]
        assert not offenders, (
            "local_service.py imports SaaS infrastructure; this module's contract is that "
            f"only local connector infrastructure lives here: {offenders}"
        )
        assert not any("SaaSTrackerClient" in m for m in imported), imported

    def test_no_sync_auth_import(self) -> None:
        import specify_cli.tracker.local_service as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # CredentialStore from sync/auth should not appear
        assert "sync.auth" not in source
        assert "from specify_cli.sync" not in source


# ---------------------------------------------------------------------------
# FR-017 / SC-019 / T025 step 4: the docstrings this Mission falsifies or adds, pinned by one
# test so a later revert of any one of them reds. Originally five; the egress-single-authority
# mission (WP03) retired the fifth (`_classify_channel1`'s own docstring) along with the
# function itself -- see the test's own docstring for why that is a refresh, not a loosening.
# ---------------------------------------------------------------------------


def test_fr017_surviving_docstrings_are_not_falsified() -> None:
    """Pins the FR-017 deliverables that survive the egress-single-authority mission (WP03):
    the three docstrings this WP amends (`local_service.py`'s module docstring,
    `_check_sync_readiness`, `_check_binding_readiness`) and WP03's own authored module
    docstring on `egress_verdict.py`. A later revert of *any* one of these reds this single
    test -- verified by temporarily mutating each in a scratch copy, never a source edit during
    a verification run.

    Originally pinned a fifth docstring, `_classify_channel1`'s own -- retired here (not
    softened, not silently dropped) because the function itself is **delete**d, **not
    migrate**d by the egress-single-authority mission (research.md Decision 3/4, C-002): there
    is no docstring left to falsify. Its four required literals
    (`invocation/adapters.py:81`/`Q3`/`delete`/`not migrate`) survive on the module docstring
    below, which records the classifier's retirement in full.
    """
    import specify_cli.tracker.egress_verdict as egress_verdict_mod
    import specify_cli.tracker.local_service as local_service_mod
    from specify_cli.cli.commands.tracker import _check_binding_readiness, _check_sync_readiness

    # 1. local_service.py's module docstring no longer claims zero consultation of any
    # consent/verdict machinery -- it records that this module consults the tracker-egress
    # verdict, which in turn reaches the hosted-sync consent chain.
    local_doc = local_service_mod.__doc__ or ""
    assert "egress" in local_doc.lower() and "verdict" in local_doc.lower(), local_doc

    # 2. _check_sync_readiness: "without going through the SaaS surface at all" is false the
    # moment the local sync entry points consult the hosted-sync consent chain via Channel 1.
    sync_doc = _check_sync_readiness.__doc__ or ""
    assert "tracker_egress_verdict" in sync_doc, sync_doc
    assert "Channel 1" in sync_doc, sync_doc

    # 3. _check_binding_readiness mirrors the former and must not silently inherit a claim
    # that is no longer true for the sync entry points -- it names the distinction instead.
    binding_doc = _check_binding_readiness.__doc__ or ""
    assert "tracker_egress_verdict" in binding_doc, binding_doc
    assert "does not" in binding_doc.lower(), binding_doc

    # 4. WP03's authored module docstring -- SC-019's literal strings, so the retirement
    # condition (Bundle B's Q3) cannot be softened into a "consider revisiting", even though
    # the classifier it once described has itself been retired.
    doc = egress_verdict_mod.__doc__ or ""
    for literal in ("invocation/adapters.py:81", "Q3", "delete", "not migrate"):
        assert literal in doc, (literal, doc)
