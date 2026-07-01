"""Tests for spec-kitty doctor ops orphan detection and stale sweep."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Literal

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.doctor import ops as ops_module
from specify_cli.doctor.ops import close_stale_ops, list_orphan_ops
from specify_cli.invocation.executor import ProfileInvocationExecutor
from specify_cli.invocation.record import OpCompletedEvent
from specify_cli.invocation.writer import EVENTS_DIR

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()

_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)


def _write_op(
    path: Path,
    *,
    completed: bool,
    started_at: str = "2026-06-05T00:00:00+00:00",
) -> None:
    events = [
        {
            "event": "started",
            "invocation_id": path.stem,
            "profile_id": "implementer-fixture",
            "action": "implement",
            "started_at": started_at,
        }
    ]
    if completed:
        events.append(
            {
                "event": "completed",
                "invocation_id": path.stem,
                "profile_id": "implementer-fixture",
                "action": "",
                "completed_at": "2026-06-05T00:01:00+00:00",
            }
        )
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")


def test_list_orphan_ops_ignores_missing_dir(tmp_path: Path) -> None:
    assert list_orphan_ops(tmp_path) == []


def test_list_orphan_ops_returns_started_only_files(tmp_path: Path) -> None:
    ops_dir = tmp_path / EVENTS_DIR
    ops_dir.mkdir()
    orphan = ops_dir / "01KTBE0RQY9XKTV0PE49PJDMRM.jsonl"
    closed = ops_dir / "01KTBE0RQY9XKTV0PE49PJDMRN.jsonl"
    _write_op(orphan, completed=False)
    _write_op(closed, completed=True)
    for name in ("ops-index.jsonl", "lifecycle.jsonl", "propagation-errors.jsonl"):
        (ops_dir / name).write_text("{}\n", encoding="utf-8")

    assert list_orphan_ops(tmp_path) == [orphan]


def test_doctor_ops_json_reports_orphan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".kittify").mkdir()
    ops_dir = tmp_path / EVENTS_DIR
    ops_dir.mkdir()
    orphan = ops_dir / "01KTBE0RQY9XKTV0PE49PJDMRM.jsonl"
    _write_op(orphan, completed=False)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli_app, ["doctor", "ops", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output) == [{"path": f"{EVENTS_DIR}/{orphan.name}"}]


# ---------------------------------------------------------------------------
# close_stale_ops (WP04 — T015/T017/T018)
# ---------------------------------------------------------------------------


def _ops_dir(tmp_path: Path) -> Path:
    ops_dir = tmp_path / EVENTS_DIR
    ops_dir.mkdir(exist_ok=True)
    return ops_dir


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _read_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_sweep_closes_only_stale_ops(tmp_path: Path) -> None:
    ops_dir = _ops_dir(tmp_path)
    stale = ops_dir / "01KTBE0RQY9XKTV0PE49PJD001.jsonl"
    fresh = ops_dir / "01KTBE0RQY9XKTV0PE49PJD002.jsonl"
    _write_op(stale, completed=False, started_at=_iso(_NOW - timedelta(hours=48)))
    _write_op(fresh, completed=False, started_at=_iso(_NOW - timedelta(hours=1)))

    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 1
    assert report.skipped_fresh == 1
    assert report.threshold_hours == 24.0
    by_id = {entry.invocation_id: entry for entry in report.open_ops}
    assert by_id[stale.stem].action_taken == "closed_abandoned"
    assert by_id[stale.stem].age_hours == pytest.approx(48.0)
    assert by_id[fresh.stem].action_taken == "none"
    # The fresh op was not touched on disk.
    assert all(event["event"] == "started" for event in _read_events(fresh))


def test_sweep_writes_closed_by_and_outcome_verbatim(tmp_path: Path) -> None:
    ops_dir = _ops_dir(tmp_path)
    stale = ops_dir / "01KTBE0RQY9XKTV0PE49PJD003.jsonl"
    _write_op(stale, completed=False, started_at=_iso(_NOW - timedelta(hours=100)))

    close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    events = _read_events(stale)
    assert len(events) == 2
    completed = events[1]
    assert completed["event"] == "completed"
    assert completed["outcome"] == "abandoned"
    assert completed["closed_by"] == "doctor_sweep"


def test_sweep_propagates_completed_event_when_sync_enabled(tmp_path: Path) -> None:
    """D1/R1 fix: sweep closes go through the shared SaaS propagator (FR-008 parity)."""
    from unittest.mock import patch

    from specify_cli.invocation.propagator import InvocationSaaSPropagator

    ops_dir = _ops_dir(tmp_path)
    stale = ops_dir / "01KTBE0RQY9XKTV0PE49PJD030.jsonl"
    _write_op(stale, completed=False, started_at=_iso(_NOW - timedelta(hours=48)))
    submitted: list[object] = []

    def _spy_submit(self: object, record: object) -> None:
        submitted.append(record)

    with patch.object(InvocationSaaSPropagator, "submit", _spy_submit):
        report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 1
    assert len(submitted) == 1, "exactly one (completed) event must be submitted"
    record = submitted[0]
    assert isinstance(record, OpCompletedEvent)
    assert record.invocation_id == stale.stem
    assert record.outcome == "abandoned"
    assert record.closed_by == "doctor_sweep"


def test_sweep_sync_disabled_closes_locally_without_propagation(tmp_path: Path) -> None:
    """Sync-gated: with sync disabled, the SaaS client is never consulted but
    the swept Op is still closed locally (LOCAL-FIRST invariant)."""
    from unittest.mock import MagicMock, patch

    from specify_cli.invocation import propagator as propagator_mod

    ops_dir = _ops_dir(tmp_path)
    stale = ops_dir / "01KTBE0RQY9XKTV0PE49PJD031.jsonl"
    _write_op(stale, completed=False, started_at=_iso(_NOW - timedelta(hours=48)))

    # Run propagation synchronously so the sync-gate is exercised in-test.
    def _sync_submit(
        self: propagator_mod.InvocationSaaSPropagator, record: object
    ) -> None:
        propagator_mod._propagate_one(record, tmp_path)  # type: ignore[arg-type]

    client_spy = MagicMock()
    with (
        patch.object(propagator_mod.InvocationSaaSPropagator, "submit", _sync_submit),
        patch.object(
            propagator_mod, "resolve_sync_routing", return_value=False  # sync explicitly disabled
        ),
        patch.object(propagator_mod, "_get_saas_client", client_spy),
    ):
        report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 1
    client_spy.assert_not_called()
    events = _read_events(stale)
    assert [event["event"] for event in events] == ["started", "completed"], (
        "local completed event must be written even when sync is disabled"
    )


def test_sweep_fires_auto_commit_per_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ops_dir = _ops_dir(tmp_path)
    for suffix in ("004", "005"):
        _write_op(
            ops_dir / f"01KTBE0RQY9XKTV0PE49PJD{suffix}.jsonl",
            completed=False,
            started_at=_iso(_NOW - timedelta(hours=48)),
        )
    commits: list[str] = []
    monkeypatch.setattr(
        ProfileInvocationExecutor, "_current_branch", lambda self: "main"
    )
    monkeypatch.setattr(
        "specify_cli.invocation.executor.safe_commit",
        lambda **kwargs: commits.append(str(kwargs["message"])),
    )

    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 2
    assert len(commits) == 2  # one auto-commit per close


def test_sweep_threshold_zero_sweeps_all(tmp_path: Path) -> None:
    ops_dir = _ops_dir(tmp_path)
    for hours, suffix in ((48, "006"), (0.01, "007")):
        _write_op(
            ops_dir / f"01KTBE0RQY9XKTV0PE49PJD{suffix}.jsonl",
            completed=False,
            started_at=_iso(_NOW - timedelta(hours=hours)),
        )

    report = close_stale_ops(tmp_path, threshold_hours=0, now=_NOW)

    assert report.swept == 2
    assert report.skipped_fresh == 0
    assert all(entry.action_taken == "closed_abandoned" for entry in report.open_ops)


def test_sweep_fresh_only_sweeps_nothing(tmp_path: Path) -> None:
    ops_dir = _ops_dir(tmp_path)
    fresh = ops_dir / "01KTBE0RQY9XKTV0PE49PJD008.jsonl"
    _write_op(fresh, completed=False, started_at=_iso(_NOW - timedelta(hours=2)))

    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 0
    assert report.skipped_fresh == 1
    assert not report.has_errors


def test_sweep_unparseable_started_at_treated_stale_with_warning(tmp_path: Path) -> None:
    ops_dir = _ops_dir(tmp_path)
    broken = ops_dir / "01KTBE0RQY9XKTV0PE49PJD009.jsonl"
    _write_op(broken, completed=False, started_at="not-a-timestamp")

    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 1
    entry = report.open_ops[0]
    assert entry.action_taken == "closed_abandoned"
    assert entry.age_hours is None
    assert entry.parse_warning is not None


def test_sweep_handles_naive_started_at_without_crash(tmp_path: Path) -> None:
    ops_dir = _ops_dir(tmp_path)
    naive = ops_dir / "01KTBE0RQY9XKTV0PE49PJD010.jsonl"
    _write_op(
        naive,
        completed=False,
        started_at=(_NOW - timedelta(hours=48)).replace(tzinfo=None).isoformat(),
    )

    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.open_ops[0].age_hours == pytest.approx(48.0)
    assert report.swept == 1


def test_sweep_race_concurrent_close_reports_already_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ops_dir = _ops_dir(tmp_path)
    stale = ops_dir / "01KTBE0RQY9XKTV0PE49PJD011.jsonl"
    _write_op(stale, completed=False, started_at=_iso(_NOW - timedelta(hours=48)))

    # Simulate the race: enumeration sees the op, then a manual close lands
    # between enumeration and the sweep's close attempt.
    enumerated = list_orphan_ops(tmp_path)
    ProfileInvocationExecutor(tmp_path).complete_invocation(
        stale.stem, outcome="done", closed_by="agent"
    )
    monkeypatch.setattr(ops_module, "list_orphan_ops", lambda repo_root: enumerated)

    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 0
    assert not report.has_errors
    assert report.open_ops[0].action_taken == "already_closed"
    # The manual close is untouched — no misattribution.
    events = _read_events(stale)
    assert len(events) == 2
    assert events[1]["closed_by"] == "agent"


def test_sweep_per_op_error_recorded_and_sweep_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ops_dir = _ops_dir(tmp_path)
    bad = ops_dir / "01KTBE0RQY9XKTV0PE49PJD012.jsonl"
    good = ops_dir / "01KTBE0RQY9XKTV0PE49PJD013.jsonl"
    for path in (bad, good):
        _write_op(path, completed=False, started_at=_iso(_NOW - timedelta(hours=48)))

    real_complete = ProfileInvocationExecutor.complete_invocation

    def flaky(
        self: ProfileInvocationExecutor,
        invocation_id: str,
        outcome: Literal["done", "failed", "abandoned"],
        evidence_ref: str | None = None,
        artifact_refs: list[str] | None = None,
        commit_sha: str | None = None,
        *,
        closed_by: Literal["agent", "doctor_sweep"],
    ) -> OpCompletedEvent:
        if invocation_id == bad.stem:
            raise OSError("disk full")
        return real_complete(
            self,
            invocation_id,
            outcome,
            evidence_ref,
            artifact_refs,
            commit_sha,
            closed_by=closed_by,
        )

    monkeypatch.setattr(ProfileInvocationExecutor, "complete_invocation", flaky)

    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)

    assert report.swept == 1
    assert report.has_errors
    by_id = {entry.invocation_id: entry for entry in report.open_ops}
    assert by_id[bad.stem].error is not None
    assert by_id[good.stem].action_taken == "closed_abandoned"


def _generate_synthetic_ops(ops_dir: Path, count: int, started_at: str) -> None:
    for i in range(count):
        invocation_id = f"01KTPERF{i:018d}"
        line = json.dumps(
            {
                "event": "started",
                "invocation_id": invocation_id,
                "profile_id": "perf-fixture",
                "action": "implement",
                "started_at": started_at,
            }
        )
        (ops_dir / f"{invocation_id}.jsonl").write_text(line + "\n", encoding="utf-8")


@pytest.mark.quarantine  # perf budget CI-machine-dependent (2.96s vs 0.5s) (Wave-0 orphan-bind triage #2295, #2034/#2283)
def test_sweep_enumeration_perf_1k_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default-suite extrapolation of NFR-002: 1,000 files in < 0.5 s (close mocked)."""
    ops_dir = _ops_dir(tmp_path)
    _generate_synthetic_ops(ops_dir, 1000, _iso(_NOW - timedelta(hours=48)))
    monkeypatch.setattr(
        ProfileInvocationExecutor,
        "complete_invocation",
        lambda self, invocation_id, *a, **k: None,
    )

    start = time.perf_counter()
    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)
    elapsed = time.perf_counter() - start

    assert report.swept == 1000
    assert elapsed < 0.5, f"1k-file sweep took {elapsed:.3f}s (budget 0.5s)"


@pytest.mark.slow
def test_sweep_nfr_002_10k_files_under_5s(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Authoritative NFR-002 check: 10,000 Op files swept in < 5 s (close mocked)."""
    ops_dir = _ops_dir(tmp_path)
    _generate_synthetic_ops(ops_dir, 10_000, _iso(_NOW - timedelta(hours=48)))
    monkeypatch.setattr(
        ProfileInvocationExecutor,
        "complete_invocation",
        lambda self, invocation_id, *a, **k: None,
    )

    start = time.perf_counter()
    report = close_stale_ops(tmp_path, threshold_hours=24.0, now=_NOW)
    elapsed = time.perf_counter() - start

    assert report.swept == 10_000
    assert elapsed < 5.0, f"10k-file sweep took {elapsed:.3f}s (NFR-002 budget 5s)"
