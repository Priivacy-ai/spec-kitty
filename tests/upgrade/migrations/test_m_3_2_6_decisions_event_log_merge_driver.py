"""Tests for migration 3.2.6_decisions_event_log_merge_driver (#2709).

The load-bearing test is the runner-level re-run binding: a consumer who already
recorded ``3.2.6_meta_traces_merge_drivers`` as ``success`` must STILL gain the
decisions.events.jsonl driver on their next upgrade. That only holds because the
decisions driver ships as its own migration id -- the runner short-circuits at
``has_migration()`` before it ever calls ``detect()``, so folding it into the
already-recorded meta+traces id would strand it forever (re-inheriting #2709).
"""

from __future__ import annotations

import subprocess
from kernel.clock import now_utc
from pathlib import Path

import pytest

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations.m_3_2_6_decisions_event_log_merge_driver import (
    DecisionsEventLogMergeDriverMigration,
)
from specify_cli.upgrade.migrations.m_3_2_6_meta_traces_merge_drivers import (
    MetaTracesMergeDriverMigration,
)
from specify_cli.upgrade.runner import MigrationRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_DECISIONS_ENTRY = "kitty-specs/**/decisions.events.jsonl merge=spec-kitty-event-log"
_META_TRACES_ID = "3.2.6_meta_traces_merge_drivers"


def _git(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *cmd], cwd=cwd, text=True, capture_output=True, check=True)


def _init_repo(tmp_path: Path) -> Path:
    _git(["init", "-b", "main"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Spec Kitty"], tmp_path)
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    return tmp_path


def test_apply_installs_decisions_driver(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    migration = DecisionsEventLogMergeDriverMigration()
    assert migration.detect(repo) is True

    result = migration.apply(repo)
    assert result.success is True

    attributes = (repo / ".gitattributes").read_text(encoding="utf-8")
    assert _DECISIONS_ENTRY in attributes
    assert (
        _git(["config", "--local", "--get", "merge.spec-kitty-event-log.driver"], repo)
        .stdout.strip()
        == "spec-kitty merge-driver-event-log %O %A %B"
    )
    assert migration.detect(repo) is False


def test_ships_as_distinct_id_from_meta_traces(tmp_path: Path) -> None:
    """A distinct id is the whole point — see the runner re-run test below."""
    assert (
        DecisionsEventLogMergeDriverMigration.migration_id
        != MetaTracesMergeDriverMigration.migration_id
    )


def test_prior_meta_traces_upgrade_does_not_strand_decisions_driver(tmp_path: Path) -> None:
    """Runner-level binding (debbie D-F1): the runner skips a migration whose id
    is already recorded BEFORE calling detect(). A repo that recorded the
    meta+traces id on a prior 3.2.6 upgrade must still gain the decisions driver,
    because it carries a DISTINCT id that is not yet recorded.

    Exercises both branches of the ``has_migration`` short-circuit so it cannot
    pass vacuously: the un-recorded distinct id is applied; recording it skips.
    """
    repo = _init_repo(tmp_path)

    # Simulate a consumer already at the 2-driver meta+traces state.
    MetaTracesMergeDriverMigration().apply(repo)
    metadata = ProjectMetadata(version="3.2.6", initialized_at=now_utc())
    metadata.record_migration(_META_TRACES_ID, "success")
    assert metadata.has_migration(_META_TRACES_ID) is True
    # decisions.events.jsonl driver absent from that consumer's .gitattributes:
    assert _DECISIONS_ENTRY not in (repo / ".gitattributes").read_text(encoding="utf-8")

    runner = MigrationRunner(repo)

    # The distinct id is NOT recorded, so _apply_migration reaches detect() and
    # applies it — instead of short-circuiting on the recorded meta+traces id.
    _result, status = runner._apply_migration(
        DecisionsEventLogMergeDriverMigration(), metadata, dry_run=False
    )
    assert status == "applied"
    assert _DECISIONS_ENTRY in (repo / ".gitattributes").read_text(encoding="utf-8")

    # Contrast: once its own id is recorded, the runner correctly skips it —
    # proving the "applied" above was the has_migration branch actually working.
    metadata.record_migration(DecisionsEventLogMergeDriverMigration.migration_id, "success")
    _result2, status2 = runner._apply_migration(
        DecisionsEventLogMergeDriverMigration(), metadata, dry_run=False
    )
    assert status2 == "skipped"
