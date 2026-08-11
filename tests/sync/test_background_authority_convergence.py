"""WP08 background convergence through the public body-drain entry point."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest

from specify_cli.sync import body_transport
from specify_cli.sync.background import BackgroundSyncService
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.deny_hints import DenyHintAction, publish_deny_hint
from specify_cli.sync.layout_generation import LayoutAuthorityError
from specify_cli.sync.namespace import NamespaceRef, UploadOutcome, UploadStatus
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.transport_attempts import DeliveryOutcome

pytestmark = pytest.mark.fast

PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _publish_project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    try:
        authority.begin_cutover("wp08-background")
    except LayoutAuthorityError as exc:
        if "already project-only" not in str(exc):
            raise
        return
    authority.publish_project_only("wp08-background", verify_exact=lambda: True)


def _admit_project(project_uuid: str, *, target: str = "https://app.spec-kitty.ai") -> ProjectSyncStore:
    record_project_opt_in(project_uuid, actor="wp08-test")
    store = ProjectSyncStore(project_uuid)
    _publish_project_only(store)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, ?, 'account-1', 'teamspace-1', 4, "
            "'admitted', '1', 'private-teamspace:teamspace-1')",
            (project_uuid, target),
        )
    return store


def _consented_project_without_admission(project_uuid: str) -> ProjectSyncStore:
    record_project_opt_in(project_uuid, actor="wp08-test")
    store = ProjectSyncStore(project_uuid)
    _publish_project_only(store)
    return store


def _service() -> BackgroundSyncService:
    config = MagicMock()
    config.resolve_runtime_target.return_value = SimpleNamespace(resolved_server_url="https://app.spec-kitty.ai")
    return BackgroundSyncService(queue=MagicMock(), config=config)


def _enqueue_body(store: ProjectSyncStore, content_hash: str = "abc123") -> str:
    with store.unit_of_work() as unit:
        queue = OfflineBodyUploadQueue(unit, store.layout_generation())
        result = queue.enqueue(
            NamespaceRef(
                project_uuid=store.project_uuid.storage_token,
                mission_slug="mission",
                target_branch="main",
                mission_type="software-dev",
                manifest_version="1",
            ),
            "spec.md",
            content_hash,
            "# Spec\n",
            len(b"# Spec\n"),
        )
        assert result.value == "enqueued"
        return cast("str", queue.drain()[0].row_id)


@pytest.fixture(autouse=True)
def _runtime_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr("specify_cli.sync.background._fetch_access_token_sync", lambda: "token")
    manager = MagicMock()
    manager.get_current_session.return_value = SimpleNamespace(
        email="account-1",
        teams=[SimpleNamespace(id="teamspace-1", is_private_teamspace=True)],
    )
    monkeypatch.setattr("specify_cli.sync.background.get_token_manager", lambda: manager)


def test_public_background_drain_records_body_attempt_and_result(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _admit_project(PROJECT_B)
    _enqueue_body(store)
    push = MagicMock(
        return_value=UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc123",
        )
    )
    monkeypatch.setattr(body_transport, "_send_content_request", push)

    _service().drain_body_uploads_only()

    push.assert_called_once()
    with store.unit_of_work() as unit:
        assert unit.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "uploaded"
        attempt = unit.execute("SELECT state, project_uuid, target_generation, admission_generation FROM delivery_attempts").fetchone()
        result = unit.execute("SELECT outcome, target_generation, admission_generation FROM delivery_results").fetchone()
    assert attempt == ("succeeded", PROJECT_B, 4, "1")
    assert result == (DeliveryOutcome.DELIVERED.value, 4, "1")


def test_public_background_drain_withholds_unadmitted_and_cross_target_without_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unadmitted = _consented_project_without_admission(PROJECT_A)
    cross_target = _admit_project(PROJECT_B, target="https://other.example.test")
    _enqueue_body(unadmitted)
    _enqueue_body(cross_target)
    push = MagicMock()
    monkeypatch.setattr(body_transport, "_send_content_request", push)

    _service().drain_body_uploads_only()

    push.assert_not_called()
    for store in (unadmitted, cross_target):
        with store.unit_of_work() as unit:
            assert unit.execute("SELECT COUNT(*) FROM delivery_attempts").fetchone()[0] == 0
            assert unit.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "pending"


def test_project_a_revocation_does_not_block_project_b_public_background_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_a = _admit_project(PROJECT_A)
    store_b = _admit_project(PROJECT_B)
    _enqueue_body(store_a, "hash-a")
    _enqueue_body(store_b, "hash-b")
    record_project_opt_out(PROJECT_A, actor="wp08-test")
    push = MagicMock(
        return_value=UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.ALREADY_EXISTS,
            reason="duplicate",
            content_hash="hash-b",
        )
    )
    monkeypatch.setattr(body_transport, "_send_content_request", push)

    _service().drain_body_uploads_only()

    push.assert_called_once()
    with store_a.unit_of_work() as unit_a:
        assert unit_a.execute("SELECT COUNT(*) FROM delivery_attempts").fetchone()[0] == 0
        assert unit_a.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "pending"
    with store_b.unit_of_work() as unit_b:
        assert unit_b.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "uploaded"
        assert unit_b.execute("SELECT outcome FROM delivery_results").fetchone()[0] == DeliveryOutcome.DUPLICATE.value


def test_colliding_body_task_ids_update_only_the_selected_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_a = _admit_project(PROJECT_A)
    store_b = _admit_project(PROJECT_B)
    _enqueue_body(store_a, "same-hash")
    _enqueue_body(store_b, "same-hash")
    with store_a.unit_of_work() as unit_a:
        colliding_id = str(unit_a.execute("SELECT body_task_id FROM body_upload_tasks").fetchone()[0])
    with store_b.unit_of_work() as unit_b:
        unit_b.execute("UPDATE body_upload_tasks SET body_task_id = ?", (colliding_id,))
    record_project_opt_out(PROJECT_A, actor="wp08-test")
    monkeypatch.setattr(
        body_transport,
        "_send_content_request",
        MagicMock(
            return_value=UploadOutcome(
                artifact_path="spec.md",
                status=UploadStatus.UPLOADED,
                reason="stored",
                content_hash="same-hash",
            )
        ),
    )

    _service().drain_body_uploads_only()

    with store_a.unit_of_work() as unit_a:
        assert unit_a.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "pending"
    with store_b.unit_of_work() as unit_b:
        assert unit_b.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "uploaded"


def test_public_background_drain_uses_current_target_generation_after_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _admit_project(PROJECT_B)
    _enqueue_body(store)
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET configuration_generation = 5, admission_generation = '2' WHERE project_uuid = ?",
            (PROJECT_B,),
        )
    push = MagicMock(
        return_value=UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc123",
        )
    )
    monkeypatch.setattr(body_transport, "_send_content_request", push)

    _service().drain_body_uploads_only()

    push.assert_called_once()
    with store.unit_of_work() as unit:
        attempt = unit.execute("SELECT target_generation, admission_generation FROM delivery_attempts").fetchone()
        result = unit.execute("SELECT target_generation, admission_generation FROM delivery_results").fetchone()
    assert attempt == (5, "2")
    assert result == (5, "2")


def test_public_background_drain_requires_current_account_and_private_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _admit_project(PROJECT_B)
    _enqueue_body(store)
    manager = MagicMock()
    manager.get_current_session.return_value = SimpleNamespace(
        email="another-account@example.test",
        teams=[SimpleNamespace(id="another-private-team", is_private_teamspace=True)],
    )
    monkeypatch.setattr("specify_cli.sync.background.get_token_manager", lambda: manager)
    push = MagicMock()
    monkeypatch.setattr(body_transport, "_send_content_request", push)

    _service().drain_body_uploads_only()

    push.assert_not_called()
    with store.unit_of_work() as unit:
        assert unit.execute("SELECT COUNT(*) FROM delivery_attempts").fetchone()[0] == 0
        assert unit.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "pending"


def test_valid_observed_deny_hint_skips_only_its_project_store_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_a = _admit_project(PROJECT_A)
    store_b = _admit_project(PROJECT_B)
    _enqueue_body(store_a, "hash-a")
    _enqueue_body(store_b, "hash-b")
    refusal = record_project_opt_out(PROJECT_A, actor="wp08-test")
    service = _service()
    service._observed_consent_generations[PROJECT_A] = refusal.generation

    from specify_cli.sync import project_store as project_store_module

    opened: list[Path] = []
    real_connect = project_store_module.sqlite3.connect

    def tracked_connect(database: object, *args: object, **kwargs: object) -> object:
        opened.append(Path(str(database)))
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(project_store_module.sqlite3, "connect", tracked_connect)
    monkeypatch.setattr(
        body_transport,
        "_send_content_request",
        MagicMock(
            return_value=UploadOutcome(
                artifact_path="spec.md",
                status=UploadStatus.UPLOADED,
                reason="stored",
                content_hash="hash-b",
            )
        ),
    )

    service.drain_body_uploads_only()

    assert store_a.database_path not in opened
    assert store_b.database_path in opened


def test_uncertain_hint_with_missing_store_does_not_create_authority() -> None:
    publish_deny_hint(
        PROJECT_A,
        action=DenyHintAction.DENY,
        authority_generation=1,
        reason_category="absent",
    )
    store = ProjectSyncStore(PROJECT_A)
    assert not store.database_path.exists()

    _service().drain_body_uploads_only()

    assert not store.database_path.exists()


def test_corrupt_project_a_store_does_not_stop_project_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corrupt_a = ProjectSyncStore(PROJECT_A)
    corrupt_a.database_path.parent.mkdir(parents=True)
    corrupt_a.database_path.write_bytes(b"not sqlite")
    store_b = _admit_project(PROJECT_B)
    _enqueue_body(store_b, "hash-b")
    push = MagicMock(
        return_value=UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.ALREADY_EXISTS,
            reason="duplicate",
            content_hash="hash-b",
        )
    )
    monkeypatch.setattr(body_transport, "_send_content_request", push)

    _service().drain_body_uploads_only()

    push.assert_called_once()
    with store_b.unit_of_work() as unit:
        assert unit.execute("SELECT state FROM body_upload_tasks").fetchone()[0] == "uploaded"
