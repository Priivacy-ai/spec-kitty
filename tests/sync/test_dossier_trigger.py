"""Tests for trigger_feature_dossier_sync_if_enabled helper."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from specify_cli.sync.dossier_pipeline import (
    DossierSyncResult,
    trigger_feature_dossier_sync_if_enabled,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

TEST_UUID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture(autouse=True)
def _isolated_consent_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-case machine state for the consent index (#3030 FR-031, E5).

    ``trigger_feature_dossier_sync_if_enabled`` now asks whether the resolved project
    consents, not only whether the machine is armed. These cases would otherwise read
    (and write) the developer's real record for ``TEST_UUID``.
    """
    home = tmp_path / "trigger-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))


def _grant(uuid: str = TEST_UUID) -> None:
    """Record the per-project consent the pipeline gate now requires."""
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(uuid, actor="test:dossier-trigger")


class TestTriggerDisabled:
    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=False)
    def test_returns_none_when_sync_disabled(
        self,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path,
            "047-feat",
            tmp_path,
        )
        assert result is None

class TestTriggerEnabled:
    @pytest.mark.parametrize(
        ("saas_enabled", "consent_decision"),
        [
            (True, "granted"),
            (True, "refused"),
            (False, "absent"),
        ],
    )
    def test_real_trigger_captures_events_and_body_on_one_unit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        saas_enabled: bool,
        consent_decision: str,
    ) -> None:
        """The live trigger/adapter/emitter path never reopens its active store."""
        from uuid import UUID

        import specify_cli.sync as sync_package
        import specify_cli.sync.project_store as project_store_module
        from specify_cli.dossier.emitter_adapter import register_dossier_emitter
        from specify_cli.identity.project import ProjectIdentity
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue
        from specify_cli.sync.emitter import EventEmitter
        from specify_cli.sync.queue import OfflineQueue
        from specify_cli.sync.project_store import ProjectSyncStore

        feature_dir = tmp_path / "kitty-specs" / "047-feat"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Private mission\n", encoding="utf-8")
        identity = ProjectIdentity(
            project_uuid=UUID(TEST_UUID),
            project_slug="test-proj",
            node_id="abcdef123456",
        )
        if consent_decision == "granted":
            _grant()
        elif consent_decision == "refused":
            from specify_cli.sync.consent import record_project_opt_out

            record_project_opt_out(TEST_UUID, actor="test:dossier-trigger-refusal")

        setup_store = ProjectSyncStore(TEST_UUID)
        with setup_store.unit_of_work():
            pass
        setup_layout = setup_store.layout_generation()
        setup_layout.begin_cutover("t033-real-trigger")
        setup_layout.publish_project_only(
            "t033-real-trigger",
            verify_exact=lambda: True,
        )

        emitter = EventEmitter(queue=object())  # type: ignore[arg-type]

        def remote_forbidden(*args: object, **kwargs: object) -> object:
            del args, kwargs
            raise AssertionError("explicit dossier capture reached ambient or remote routing")

        monkeypatch.setattr(emitter, "_get_identity", remote_forbidden)
        monkeypatch.setattr(emitter, "_get_team_slug", remote_forbidden)
        monkeypatch.setattr(emitter, "_get_git_metadata", remote_forbidden)
        monkeypatch.setattr(emitter, "_route_event", remote_forbidden)
        monkeypatch.setattr("specify_cli.sync.events.get_emitter", lambda: emitter)
        register_dossier_emitter(sync_package._dossier_emit_via_sync)  # type: ignore[attr-defined]

        monkeypatch.setattr(
            "specify_cli.sync.feature_flags.is_saas_sync_enabled",
            lambda: saas_enabled,
        )
        monkeypatch.setattr(
            "specify_cli.identity.project.resolve_identity",
            lambda _root: identity,
        )
        monkeypatch.setattr(
            "specify_cli.core.paths.get_feature_target_branch",
            lambda _root, _slug: "develop",
        )
        monkeypatch.setattr(
            "specify_cli.mission.get_mission_type",
            lambda _feature: "software-dev",
        )
        monkeypatch.setattr(
            "specify_cli.sync.namespace.resolve_manifest_version",
            lambda _mission: "1",
        )
        monkeypatch.setattr(
            "specify_cli.dossier.drift_detector.detect_drift",
            lambda **_kwargs: (False, None),
        )

        store_opens: list[str] = []
        event_connections: list[int] = []
        body_connections: list[int] = []
        sqlite_opens: list[object] = []
        begin_statements: list[str] = []
        original_store_init = ProjectSyncStore.__init__
        original_queue_event = OfflineQueue.queue_event
        original_body_enqueue = OfflineBodyUploadQueue.enqueue
        original_connect = project_store_module.sqlite3.connect

        class RecordingConnection:
            def __init__(self, connection: object) -> None:
                self.connection = connection

            def execute(self, statement: str, *args: object) -> object:
                if statement.strip().upper().startswith("BEGIN"):
                    begin_statements.append(statement.strip().upper())
                return self.connection.execute(statement, *args)  # type: ignore[attr-defined]

            def __getattr__(self, name: str) -> object:
                return getattr(self.connection, name)

        def record_connect(*args: object, **kwargs: object) -> RecordingConnection:
            connection = original_connect(*args, **kwargs)  # type: ignore[arg-type]
            sqlite_opens.append(connection)
            return RecordingConnection(connection)

        def record_store_init(self: ProjectSyncStore, project_uuid: str) -> None:
            store_opens.append(project_uuid)
            original_store_init(self, project_uuid)

        def record_queue_event(
            self: OfflineQueue,
            event: dict[str, object],
            **kwargs: object,
        ) -> bool:
            event_connections.append(self._unit.connection_identity)  # type: ignore[attr-defined]
            return original_queue_event(self, event, **kwargs)  # type: ignore[arg-type]

        def record_body_enqueue(
            self: OfflineBodyUploadQueue,
            *args: object,
            **kwargs: object,
        ) -> object:
            body_connections.append(self.unit_of_work_identity)
            return original_body_enqueue(self, *args, **kwargs)  # type: ignore[arg-type]

        with monkeypatch.context() as capture_patch:
            capture_patch.setattr(ProjectSyncStore, "__init__", record_store_init)
            capture_patch.setattr(OfflineQueue, "queue_event", record_queue_event)
            capture_patch.setattr(
                OfflineBodyUploadQueue,
                "enqueue",
                record_body_enqueue,
            )
            capture_patch.setattr(
                project_store_module.sqlite3,
                "connect",
                record_connect,
            )
            result = trigger_feature_dossier_sync_if_enabled(
                feature_dir,
                "047-feat",
                tmp_path,
            )

        assert result is not None
        assert result.events_emitted >= 2
        assert any(outcome.reason == "enqueued" for outcome in result.body_outcomes)
        assert store_opens == [TEST_UUID]
        assert len(sqlite_opens) == 1
        assert begin_statements == ["BEGIN IMMEDIATE"]
        assert event_connections
        assert body_connections
        assert set(event_connections + body_connections) == {event_connections[0]}

        with setup_store.unit_of_work() as unit:
            event_count = unit.execute(
                "SELECT COUNT(*) FROM outbox_tasks WHERE project_uuid = ? AND task_kind = 'event'",
                (TEST_UUID,),
            ).fetchone()
            body_count = unit.execute(
                "SELECT COUNT(*) FROM body_upload_tasks WHERE project_uuid = ?",
                (TEST_UUID,),
            ).fetchone()
        assert event_count is not None and int(event_count[0]) >= 2
        assert body_count == (1,)

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.identity.project.resolve_identity")
    @patch("specify_cli.core.paths.get_feature_target_branch", return_value="main")
    @patch("specify_cli.mission.get_mission_type", return_value="software-dev")
    @patch("specify_cli.sync.namespace.resolve_manifest_version", return_value="1")
    @patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue")
    @patch("specify_cli.sync.dossier_pipeline.sync_feature_dossier")
    def test_calls_sync_feature_dossier(
        self,
        mock_sync: MagicMock,
        mock_body_queue_cls: MagicMock,
        mock_manifest: MagicMock,
        mock_mission: MagicMock,
        mock_target: MagicMock,
        mock_identity: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from uuid import UUID

        from specify_cli.identity.project import ProjectIdentity

        mock_identity.return_value = ProjectIdentity(
            project_uuid=UUID(TEST_UUID),
            project_slug="test-proj",
            node_id="abcdef123456",
        )
        _grant()

        mock_body_queue = MagicMock()
        mock_body_queue_cls.return_value = mock_body_queue

        mock_sync.return_value = DossierSyncResult(
            dossier=None,
            events_emitted=0,
            body_outcomes=[],
        )

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path,
            "047-feat",
            tmp_path,
        )

        mock_sync.assert_called_once()
        assert mock_sync.call_args.kwargs["body_queue"] is mock_body_queue
        assert result is not None

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.identity.project.resolve_identity")
    def test_returns_none_when_no_project_uuid(
        self,
        mock_identity: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.identity.project import ProjectIdentity

        mock_identity.return_value = ProjectIdentity(
            project_uuid=None,
            project_slug="test-proj",
            node_id="abcdef123456",
        )

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path,
            "047-feat",
            tmp_path,
        )
        assert result is None

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.identity.project.resolve_identity")
    @patch("specify_cli.core.paths.get_feature_target_branch", return_value="main")
    @patch("specify_cli.mission.get_mission_type", return_value="software-dev")
    @patch("specify_cli.sync.namespace.resolve_manifest_version", return_value="1")
    @patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue")
    @patch("specify_cli.sync.dossier_pipeline.sync_feature_dossier")
    def test_returns_none_when_body_queue_creation_fails(
        self,
        mock_sync: MagicMock,
        mock_body_queue_cls: MagicMock,
        mock_manifest: MagicMock,
        mock_mission: MagicMock,
        mock_target: MagicMock,
        mock_identity: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from uuid import UUID

        from specify_cli.identity.project import ProjectIdentity

        mock_identity.return_value = ProjectIdentity(
            project_uuid=UUID(TEST_UUID),
            project_slug="test-proj",
            node_id="abcdef123456",
        )
        # Without this the case would go green on the consent gate instead of the
        # queue failure it is named for — the same "green for the wrong reason" the
        # old machine-arming-only gate produced everywhere else in this file.
        _grant()

        mock_body_queue_cls.side_effect = RuntimeError("queue init failed")

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path,
            "047-feat",
            tmp_path,
        )
        mock_sync.assert_not_called()
        assert result is None

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.identity.project.resolve_identity")
    @patch("specify_cli.core.paths.get_feature_target_branch", return_value="main")
    @patch("specify_cli.mission.get_mission_type", return_value="software-dev")
    @patch("specify_cli.sync.namespace.resolve_manifest_version", return_value="1")
    @patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue")
    @patch("specify_cli.sync.dossier_pipeline.sync_feature_dossier")
    def test_absent_egress_grant_still_invokes_local_dossier_capture(
        self,
        mock_sync: MagicMock,
        mock_body_queue_cls: MagicMock,
        mock_manifest: MagicMock,
        mock_mission: MagicMock,
        mock_target: MagicMock,
        mock_identity: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """No egress grant suppresses transport, not project-isolated capture."""
        from uuid import UUID

        from specify_cli.identity.project import ProjectIdentity

        mock_identity.return_value = ProjectIdentity(
            project_uuid=UUID(TEST_UUID),
            project_slug="test-proj",
            node_id="abcdef123456",
        )
        mock_body_queue_cls.return_value = MagicMock()
        mock_sync.return_value = DossierSyncResult(
            dossier=None,
            events_emitted=0,
            body_outcomes=[],
        )

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path,
            "047-feat",
            tmp_path,
        )

        mock_sync.assert_called_once()
        assert result is not None

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.identity.project.resolve_identity", side_effect=RuntimeError("boom"))
    def test_never_raises_on_internal_error(
        self,
        mock_identity: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path,
            "047-feat",
            tmp_path,
        )
        assert result is None
