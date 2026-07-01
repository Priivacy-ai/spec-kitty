"""WP03 — tracker binding_ref is report-only on read paths.

Contract ``tracker-binding-report`` (C-TB-1..3):

* C-TB-1 — read-like tracker ops (``status``/``sync_pull``/``sync_push``/
  ``sync_run``/``map_list``) MUST NOT persist ``binding_ref`` to
  ``.kittify/config.yaml``; they surface the available upgrade as
  ``pending_binding_upgrade``.
* C-TB-2 — persistence happens only at an explicit, write-authorized boundary
  (``apply_binding_upgrade`` / ``bind``).
* C-TB-3 — ``pending_binding_upgrade`` is surfaced on the read result (dict key
  for dict-returning ops; instance attribute for ``map_list``).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
)
from specify_cli.tracker.saas_service import SaaSTrackerService

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    """Create a minimal .kittify directory so config save/load works."""
    (tmp_path / ".kittify").mkdir()
    return tmp_path


@pytest.fixture()
def mock_client() -> MagicMock:
    """A mock SaaSTrackerClient with read responses that omit binding_ref."""
    client = MagicMock()
    client.status.return_value = {"connected": True}
    client.pull.return_value = {"items": []}
    client.push.return_value = {"pushed": 0}
    client.run.return_value = {"pulled": 0, "pushed": 0}
    client.mappings.return_value = {"mappings": []}
    return client


def _service(
    repo_root: Path,
    mock_client: MagicMock,
    *,
    binding_ref: str | None = None,
) -> SaaSTrackerService:
    cfg = TrackerProjectConfig(
        provider="linear",
        project_slug="my-proj",
        binding_ref=binding_ref,
    )
    return SaaSTrackerService(repo_root, cfg, client=mock_client)


def _no_binding_persisted(repo_root: Path) -> None:
    """Assert config.yaml carries no binding_ref (nothing was written)."""
    loaded = load_tracker_config(repo_root)
    assert loaded.binding_ref is None


# ---------------------------------------------------------------------------
# C-TB-1 — read ops with a CHANGED server binding_ref report, never write
# ---------------------------------------------------------------------------


class TestReadPathsReportPendingUpgrade:
    def test_status_changed_binding_ref_reports_without_writing(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        """status: changed server binding_ref -> pending reported, no write."""
        svc = _service(repo_root, mock_client)
        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-new",
            "display_label": "My Project",
        }

        result = svc.status()

        # Surfaced on the result and the instance, but not persisted.
        assert result["pending_binding_upgrade"] == "bind-new"
        assert svc.pending_binding_upgrade == "bind-new"
        # In-memory config is unchanged (no opportunistic mutation).
        assert svc._config.binding_ref is None
        _no_binding_persisted(repo_root)

    def test_sync_pull_changed_binding_ref_reports_without_writing(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        svc = _service(repo_root, mock_client)
        mock_client.pull.return_value = {"items": [], "binding_ref": "bind-pull"}

        result = svc.sync_pull()

        assert result["pending_binding_upgrade"] == "bind-pull"
        assert svc.pending_binding_upgrade == "bind-pull"
        assert svc._config.binding_ref is None
        _no_binding_persisted(repo_root)

    def test_sync_push_changed_binding_ref_reports_without_writing(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        svc = _service(repo_root, mock_client)
        mock_client.push.return_value = {"pushed": 0, "binding_ref": "bind-push"}

        result = svc.sync_push()

        assert result["pending_binding_upgrade"] == "bind-push"
        _no_binding_persisted(repo_root)

    def test_sync_run_changed_binding_ref_reports_without_writing(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        svc = _service(repo_root, mock_client)
        mock_client.run.return_value = {
            "pulled": 0,
            "pushed": 0,
            "binding_ref": "bind-run",
        }

        result = svc.sync_run()

        assert result["pending_binding_upgrade"] == "bind-run"
        _no_binding_persisted(repo_root)

    def test_map_list_changed_binding_ref_reports_on_result_without_writing(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        """map_list keeps list behavior and reports pending upgrade on result."""
        svc = _service(repo_root, mock_client)
        mock_client.mappings.return_value = {
            "mappings": [{"wp_id": "WP01"}],
            "binding_ref": "bind-map",
        }

        result = svc.map_list()

        # List return behavior preserved; upgrade surfaced on result + instance.
        assert result == [{"wp_id": "WP01"}]
        assert result.pending_binding_upgrade == "bind-map"
        assert svc.pending_binding_upgrade == "bind-map"
        assert svc._config.binding_ref is None
        _no_binding_persisted(repo_root)

    def test_read_path_does_not_call_save_tracker_config(
        self, repo_root: Path, mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A read op with a changed binding_ref performs no config write."""
        save_spy = MagicMock()
        monkeypatch.setattr(
            "specify_cli.tracker.saas_service.save_tracker_config", save_spy
        )
        svc = _service(repo_root, mock_client)
        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-new",
        }

        svc.status()

        save_spy.assert_not_called()


# ---------------------------------------------------------------------------
# No-op cases: absent / unchanged binding_ref -> nothing pending, no write
# ---------------------------------------------------------------------------


class TestReadPathsNoOp:
    def test_status_absent_binding_ref_is_noop(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        svc = _service(repo_root, mock_client)
        mock_client.status.return_value = {"connected": True}

        result = svc.status()

        assert result["pending_binding_upgrade"] is None
        assert svc.pending_binding_upgrade is None
        _no_binding_persisted(repo_root)

    def test_status_unchanged_binding_ref_is_noop(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        svc = _service(repo_root, mock_client, binding_ref="bind-abc")
        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-abc",  # same as stored
        }

        result = svc.status()

        assert result["pending_binding_upgrade"] is None
        assert svc.pending_binding_upgrade is None

    def test_map_list_absent_binding_ref_is_noop(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        svc = _service(repo_root, mock_client)
        mock_client.mappings.return_value = {"mappings": []}

        result = svc.map_list()

        assert result.pending_binding_upgrade is None
        assert svc.pending_binding_upgrade is None
        _no_binding_persisted(repo_root)


# ---------------------------------------------------------------------------
# C-TB-2 — explicit apply persists; bind persists
# ---------------------------------------------------------------------------


class TestExplicitApplyPersists:
    def test_apply_binding_upgrade_persists_to_config(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        """Explicit apply writes binding_ref to config.yaml (write-authorized)."""
        svc = _service(repo_root, mock_client)
        # A read first reports the upgrade as pending (no write).
        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-new",
            "display_label": "My Project",
        }
        svc.status()
        assert svc.pending_binding_upgrade == "bind-new"
        _no_binding_persisted(repo_root)

        # Operator opts in -> persisted.
        updated = svc.apply_binding_upgrade(
            svc.pending_binding_upgrade,
            display_label="My Project",
        )

        assert updated.binding_ref == "bind-new"
        assert svc._config.binding_ref == "bind-new"
        # Pending cleared after a successful apply.
        assert svc.pending_binding_upgrade is None

        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "bind-new"
        assert loaded.display_label == "My Project"

    def test_apply_binding_upgrade_preserves_extra_fields(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        """Forward-compat: unknown config fields survive an explicit apply."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
            _extra={"future_flag": True},
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        svc.apply_binding_upgrade("bind-new")

        assert svc._config.binding_ref == "bind-new"
        assert svc._config._extra == {"future_flag": True}

    def test_bind_persists_binding(
        self, repo_root: Path, mock_client: MagicMock
    ) -> None:
        """The explicit bind boundary still persists (write-authorized)."""
        svc = _service(repo_root, mock_client)

        result = svc.bind(provider="linear", project_slug="new-proj")

        assert result.provider == "linear"
        loaded = load_tracker_config(repo_root)
        assert loaded.provider == "linear"
        assert loaded.project_slug == "new-proj"
