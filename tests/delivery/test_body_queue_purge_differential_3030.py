"""Project-store body purge differential for the #3030 remediation."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from specify_cli.delivery.retention import purge_project_body_uploads
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast, pytest.mark.usefixtures("canonical_home"),
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

# R1b (#3121): home isolation is provided by the canonical SPEC_KITTY_HOME owner
# (``canonical_home``, root conftest) via the module-level ``usefixtures`` mark above, replacing a
# local ``_isolated_home`` autouse fixture that pinned the identical ``tmp_path/"home"``.


PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("body-purge-test")
    authority.publish_project_only("body-purge-test", verify_exact=lambda: True)


def _enqueue(queue: OfflineBodyUploadQueue, artifact_path: str, body: str) -> str:
    result = queue.enqueue(
        NamespaceRef(
            project_uuid=queue.project_uuid,
            mission_slug="047-payroll",
            target_branch="develop",
            mission_type="software-dev",
            manifest_version="1",
        ),
        artifact_path,
        f"hash-{artifact_path}",
        body,
        len(body.encode()),
    )
    assert result.value == "enqueued"
    return next(task.row_id for task in queue.drain() if task.artifact_path == artifact_path)


def _row_count(unit: ProjectUnitOfWork) -> int:
    row = unit.execute(
        "SELECT COUNT(*) FROM body_upload_tasks WHERE project_uuid = ?",
        (unit.project_uuid.storage_token,),
    ).fetchone()
    assert row is not None
    return int(cast("str | int | float | bytes", row[0]))


class _ReadCountingQueue(OfflineBodyUploadQueue):
    reads = 0

    def count_by_project(self) -> dict[str, int]:
        self.reads += 1
        return super().count_by_project()


def test_purge_is_dry_run_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = ProjectSyncStore(PROJECT_A)
    _project_only(store)
    with store.unit_of_work() as unit:
        queue = OfflineBodyUploadQueue(unit, store.layout_generation())
        _enqueue(queue, "spec.md", "# confidential spec")
        result = purge_project_body_uploads(PROJECT_A, body_queue=queue)
        assert result.dry_run is True
        assert result.removed == 0
        assert result.target_before == result.target_after == 1
        assert _row_count(unit) == 1


def test_purge_physically_deletes_a_and_leaves_b_byte_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)
    _project_only(store_a)
    with store_b.unit_of_work() as unit_b:
        queue_b = OfflineBodyUploadQueue(unit_b, store_b.layout_generation())
        row_b = _enqueue(queue_b, "spec.md", "# secret B")
        before_b = unit_b.execute(
            "SELECT body_task_id, body_reference FROM body_upload_tasks WHERE project_uuid = ?",
            (PROJECT_B,),
        ).fetchall()
        assert len(before_b) == 1 and str(before_b[0][0]) == row_b

    with store_a.unit_of_work() as unit_a:
        queue_a = OfflineBodyUploadQueue(unit_a, store_a.layout_generation())
        first = _enqueue(queue_a, "spec.md", "# secret A")
        second = _enqueue(queue_a, "plan.md", "# secret A plan")
        queue_a.mark_uploaded(second)
        before_a = unit_a.execute(
            "SELECT body_task_id, body_reference FROM body_upload_tasks WHERE project_uuid = ? ORDER BY body_task_id",
            (PROJECT_A,),
        ).fetchall()
        assert {str(row[0]) for row in before_a} == {first, second}

        result = purge_project_body_uploads(
            PROJECT_A,
            body_queue=queue_a,
            dry_run=False,
        )

        assert result.removed == 2
        assert result.target_before == 2
        assert result.target_after == 0
        assert result.other_project_differential == 0
        assert result.is_exact
        assert _row_count(unit_a) == 0

    with store_b.unit_of_work() as unit_b:
        after_b = unit_b.execute(
            "SELECT body_task_id, body_reference FROM body_upload_tasks WHERE project_uuid = ?",
            (PROJECT_B,),
        ).fetchall()
        assert after_b == before_b


def test_purge_rejects_queue_owner_mismatch_before_reading_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store_b = ProjectSyncStore(PROJECT_B)
    _project_only(store_b)
    with store_b.unit_of_work() as unit_b:
        queue_b = _ReadCountingQueue(unit_b, store_b.layout_generation())
        _enqueue(queue_b, "spec.md", "# secret B")
        with pytest.raises(ValueError, match="store owner"):
            purge_project_body_uploads(
                PROJECT_A,
                body_queue=queue_b,
                dry_run=False,
            )
        assert queue_b.reads == 0
