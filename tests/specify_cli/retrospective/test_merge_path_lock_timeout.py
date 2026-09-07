"""Merge-path retrospective L1 take is finite (WP01 T007, FR-003 b / NFR-003).

``run_retrospective_postcondition`` runs on the ``spec-kitty merge`` completion
path under the merge-global sentinel. Its status-lock takes must never wait
forever: a contended lock surfaces as a structured
``FeatureStatusLockTimeoutError`` that the terminus' fail-open handlers turn
into a failed retrospective step (a warning naming the lock and its holder),
not into a repo-wide merge refusal.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import specify_cli.post_merge.retrospective_terminus as terminus
from specify_cli.post_merge.retrospective_terminus import run_retrospective_postcondition
from specify_cli.retrospective.lifecycle_events import _resolve_lock_timeout
from specify_cli.status import BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS, feature_status_lock
from specify_cli.workspace.root_resolver import resolve_status_lock_root

pytestmark = [pytest.mark.unit]

MISSION_SLUG = "017-merge-path-timeout"


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    fd = tmp_path / "kitty-specs" / MISSION_SLUG
    fd.mkdir(parents=True)
    (fd / "meta.json").write_text(
        json.dumps({"mission_id": "01HXYZ0000000000000000000A", "mission_slug": MISSION_SLUG}),
        encoding="utf-8",
    )
    return fd


def _patch_resolver(feature_dir: Path) -> Any:
    return patch("specify_cli.retrospective.writer.resolve_retrospective_home", return_value=feature_dir)


def test_capture_runs_inside_the_bounded_timeout_scope(feature_dir: Path, tmp_path: Path) -> None:
    """Every appender reached from the capture (bridge included) inherits the bound."""
    observed: list[float] = []

    def _capture(**_kwargs: Any) -> None:
        observed.append(_resolve_lock_timeout(None))

    with _patch_resolver(feature_dir), patch.object(terminus, "_invoke_capture", side_effect=_capture):
        run_retrospective_postcondition(mission_slug=MISSION_SLUG, repo_root=tmp_path)
    assert observed == [BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS]
    assert _resolve_lock_timeout(None) == -1.0, "scope must not leak past the terminus"


def test_contended_lock_fails_the_retrospective_step_not_the_merge(
    feature_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(terminus, "BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS", 0.3)
    lock_root = resolve_status_lock_root(feature_dir)
    ready = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        with feature_status_lock(lock_root, feature_dir.name, timeout=5):
            ready.set()
            release.wait(timeout=15)

    holder = threading.Thread(target=_hold, name="merge-path-holder")
    holder.start()
    try:
        assert ready.wait(timeout=5)
        started = time.monotonic()
        with (
            caplog.at_level(logging.WARNING),
            _patch_resolver(feature_dir),
            patch.object(terminus, "_invoke_capture", side_effect=RuntimeError("capture boom")),
        ):
            # Must return (fail-open), never raise, and never wait unboundedly.
            run_retrospective_postcondition(mission_slug=MISSION_SLUG, repo_root=tmp_path)
        elapsed = time.monotonic() - started
    finally:
        release.set()
        holder.join(timeout=15)
    assert not holder.is_alive()
    assert elapsed < 5.0, f"merge-path retrospective step waited {elapsed:.1f}s"
    text = caplog.text
    assert "could not emit capture_failed event" in text
    assert "Timed out acquiring status lock" in text
    assert f"{feature_dir.name}.status.lock" in text
    assert "held by pid" in text and "merge-path-holder" in text
    # Nothing landed in the log while the holder owned the lock.
    assert not (feature_dir / "status.events.jsonl").exists()
