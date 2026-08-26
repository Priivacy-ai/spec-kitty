"""Persistence contracts for PRIMARY spec-review evidence."""

from __future__ import annotations

from kernel.clock import UTC, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
import yaml

from mission_runtime import CommitTarget, TopologySurface
from mission_runtime.resolution import ResolvedSurface
from specify_cli.spec_review.models import ReviewStatus, SpecReviewRun
from specify_cli.spec_review.storage import SpecReviewWriteError, store_spec_review


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _run(run_id: str = "run-contract") -> SpecReviewRun:
    return SpecReviewRun(
        run_id=run_id,
        mission="demo",
        spec_sha256="a" * 64,
        transport="opencode-loopback",
        requested_model_route="stealth/ox-alpha",
        actual_model="unverified",
        rubric_version="v1",
        started_at=datetime(2026, 8, 23, tzinfo=UTC),
        completed_at=datetime(2026, 8, 23, tzinfo=UTC),
        status=ReviewStatus.COMPLETED,
        diagnostic_code=None,
        findings=(),
    )


def _route_to(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(
        "specify_cli.spec_review.storage.resolve_artifact_surface",
        lambda repo, mission, kind: ResolvedSurface(root, TopologySurface.PRIMARY),
    )
    monkeypatch.setattr(
        "specify_cli.spec_review.storage.placement_seam",
        lambda repo, mission: type("Seam", (), {"write_target": lambda self, kind: CommitTarget("codex/demo")})(),
    )


def test_store_uses_resolver_surface_and_serializes_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mission_root = tmp_path / "canonical-mission"
    mission_root.mkdir()
    _route_to(monkeypatch, mission_root)

    stored = store_spec_review(repo_root=tmp_path, mission_slug="demo", run=_run())

    assert stored.path == mission_root / "reviews" / "spec-review-run-contract.yaml"
    assert stored.commit_target.ref == "codex/demo"
    document = yaml.safe_load(stored.path.read_text(encoding="utf-8"))
    assert document["schema"] == "spec-review-run/v1"
    assert document["summary"]["total"] == 0


def test_store_retries_only_local_collision(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mission_root = tmp_path / "canonical-mission"
    mission_root.mkdir()
    _route_to(monkeypatch, mission_root)
    occupied = mission_root / "reviews" / "spec-review-run-contract.yaml"
    occupied.parent.mkdir()
    occupied.write_text("existing", encoding="utf-8")

    stored = store_spec_review(
        repo_root=tmp_path, mission_slug="demo", run=_run(), next_run_id=lambda: "run-retry"
    )

    assert stored.run_id == "run-retry"
    assert occupied.read_text(encoding="utf-8") == "existing"
    assert stored.path.exists()


def test_store_rejects_symlink_escape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mission_root = tmp_path / "canonical-mission"
    outside = tmp_path / "outside"
    mission_root.mkdir()
    outside.mkdir()
    try:
        (mission_root / "reviews").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this Windows host")
    _route_to(monkeypatch, mission_root)

    with pytest.raises(SpecReviewWriteError, match="SYMLINK"):
        store_spec_review(repo_root=tmp_path, mission_slug="demo", run=_run())
    assert not list(outside.iterdir())


def test_concurrent_writers_publish_distinct_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mission_root = tmp_path / "canonical-mission"
    mission_root.mkdir()
    _route_to(monkeypatch, mission_root)

    with ThreadPoolExecutor(max_workers=8) as executor:
        stored = list(
            executor.map(
                lambda index: store_spec_review(
                    repo_root=tmp_path, mission_slug="demo", run=_run(f"run-{index}")
                ),
                range(8),
            )
        )

    assert len({entry.path for entry in stored}) == 8
    assert len(list((mission_root / "reviews").glob("spec-review-*.yaml"))) == 8
