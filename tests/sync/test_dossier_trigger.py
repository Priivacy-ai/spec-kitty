"""Tests for trigger_feature_dossier_sync_if_enabled helper."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from specify_cli.sync.dossier_pipeline import (
    DossierSyncResult,
    trigger_feature_dossier_sync_if_enabled,
)

pytestmark = pytest.mark.fast

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
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(uuid, True)


class TestTriggerDisabled:
    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=False)
    def test_returns_none_when_sync_disabled(
        self, mock_saas: MagicMock, tmp_path: Path,
    ) -> None:
        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path, "047-feat", tmp_path,
        )
        assert result is None

class TestTriggerEnabled:
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
            dossier=None, events_emitted=0, body_outcomes=[],
        )

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path, "047-feat", tmp_path,
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
            tmp_path, "047-feat", tmp_path,
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
            tmp_path, "047-feat", tmp_path,
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
    def test_machine_arming_alone_does_not_trigger_dossier_sync(
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
        """#3030 FR-031 (E5): ``is_saas_sync_enabled()`` is arming, never a grant.

        Identical to ``test_calls_sync_feature_dossier`` except that the project has
        no consent record. Measured before the gate landed: ``sync_feature_dossier``
        was called once, and everything below it — dossier events carrying the
        mission slug, the snapshot write, drift detection, and the body enqueue —
        ran on a machine-global flag alone. That flag is the 2026-07-27 incident's
        own mechanism.
        """
        from uuid import UUID

        from specify_cli.identity.project import ProjectIdentity

        mock_identity.return_value = ProjectIdentity(
            project_uuid=UUID(TEST_UUID),
            project_slug="test-proj",
            node_id="abcdef123456",
        )
        mock_body_queue_cls.return_value = MagicMock()
        mock_sync.return_value = DossierSyncResult(
            dossier=None, events_emitted=0, body_outcomes=[],
        )

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path, "047-feat", tmp_path,
        )

        mock_sync.assert_not_called()
        assert result is None

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.identity.project.resolve_identity", side_effect=RuntimeError("boom"))
    def test_never_raises_on_internal_error(
        self,
        mock_identity: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path, "047-feat", tmp_path,
        )
        assert result is None
