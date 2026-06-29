"""Behavior-preservation: MissionCreated fan-out fires exactly once.

PR #2172 review finding #1. The CORE↛INTEGRATION inversion routes mission
creation through ``emit_mission_created_local`` (canonical lifecycle log +
lifecycle SaaS fan-out) and ``fire_dossier_sync`` (dashboard/dossier sync) via
the ``status/adapters.py`` registry instead of direct ``sync``/``tracker``
imports. After rebasing onto main's rewired lifecycle path (#2070/#1793
lifecycle/topology, #2134 status decompose, #2158 dead-symbol gate), this test
pins the observable behaviour the inversion must preserve:

* the canonical ``MissionCreated`` event is written **exactly once** (no drop,
  no double-write),
* the daemon/SaaS lifecycle fan-out (``fire_lifecycle_saas_fanout``) fires
  **exactly once** for that event, and
* the dashboard/dossier sync (``fire_dossier_sync``) fires **exactly once**.

It drives the *real* adapter registry — registering spy observers through the
public ``register_*`` API rather than patching the fire functions — so a
double-fire or drop introduced by the rewired lifecycle path would fail here.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from specify_cli.core.mission_creation import create_mission_core
from specify_cli.status import adapters as status_adapters

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_CORE_MODULE = "specify_cli.core.mission_creation"


def _init_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"], cwd=repo, capture_output=True, check=True
    )


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").title()
    return {
        "friendly_name": title,
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so product and engineering can move "
            "forward with a clear outcome and shared understanding."
        ),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            rows.append(json.loads(line))
    return rows


@pytest.fixture
def _isolated_adapter_registry():
    """Clear the fan-out registry, install spy handlers, restore on teardown.

    Uses the real registration API so the test exercises the same fan-out path
    production uses; resetting before and after prevents cross-test bleed and
    keeps any process-wide ``sync`` registration from doing live SaaS work.
    """
    status_adapters.reset_handlers()

    lifecycle_events: list[dict[str, Any]] = []
    dossier_calls: list[tuple[Path, str, Path]] = []

    def _lifecycle_spy(*, envelope: Any = None, **_kw: Any) -> None:
        lifecycle_events.append(dict(envelope or {}))

    def _dossier_spy(feature_dir: Path, mission_slug: str, repo_root: Path) -> None:
        dossier_calls.append((feature_dir, mission_slug, repo_root))

    status_adapters.register_lifecycle_saas_fanout_handler(_lifecycle_spy)
    status_adapters.register_dossier_sync_handler(_dossier_spy)
    try:
        yield lifecycle_events, dossier_calls
    finally:
        status_adapters.reset_handlers()


def test_mission_created_fanout_fires_exactly_once(
    tmp_path: Path, _isolated_adapter_registry
) -> None:
    """One mission creation => exactly one MissionCreated event + one of each fan-out."""
    lifecycle_events, dossier_calls = _isolated_adapter_registry
    _init_repo(tmp_path)
    slug = "fire-once-mission"

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, slug, **_mission_summary(slug))

    # No drop / no double-write: exactly one MissionCreated row on the canonical log.
    rows = _read_jsonl(result.feature_dir / "status.events.jsonl")
    mission_created_rows = [r for r in rows if r.get("event_type") == "MissionCreated"]
    assert len(mission_created_rows) == 1, (
        f"Expected exactly one MissionCreated row, got {len(mission_created_rows)}: "
        f"{[r.get('event_type') for r in rows]}"
    )

    # Daemon/SaaS lifecycle publish fires exactly once for MissionCreated.
    mission_created_fanouts = [
        e for e in lifecycle_events if e.get("event_type") == "MissionCreated"
    ]
    assert len(mission_created_fanouts) == 1, (
        f"Lifecycle SaaS fan-out must fire exactly once for MissionCreated; "
        f"got {len(mission_created_fanouts)}: "
        f"{[e.get('event_type') for e in lifecycle_events]}"
    )

    # Dashboard/dossier sync fires exactly once.
    assert len(dossier_calls) == 1, (
        f"Dossier (dashboard) sync must fire exactly once; got {len(dossier_calls)}"
    )
    assert dossier_calls[0][1] == result.mission_slug


def test_mission_created_resume_does_not_double_fire(
    tmp_path: Path, _isolated_adapter_registry
) -> None:
    """Re-running create_mission_core (resume) must not duplicate the MissionCreated publish.

    ``append_lifecycle_event`` dedupes MissionCreated on ``mission_slug``, so the
    second run must NOT emit a second canonical row nor a second lifecycle
    fan-out — proving the inversion preserves idempotency on the rewired path.
    """
    lifecycle_events, _dossier_calls = _isolated_adapter_registry
    _init_repo(tmp_path)
    slug = "fire-once-resume"

    patches = (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        first = create_mission_core(tmp_path, slug, **_mission_summary(slug))
        create_mission_core(tmp_path, slug, **_mission_summary(slug))

    rows = _read_jsonl(first.feature_dir / "status.events.jsonl")
    mission_created_rows = [r for r in rows if r.get("event_type") == "MissionCreated"]
    assert len(mission_created_rows) == 1, (
        f"Resume must not duplicate MissionCreated; got {len(mission_created_rows)} rows"
    )

    mission_created_fanouts = [
        e for e in lifecycle_events if e.get("event_type") == "MissionCreated"
    ]
    assert len(mission_created_fanouts) == 1, (
        f"Resume must not re-fire the MissionCreated lifecycle publish; "
        f"got {len(mission_created_fanouts)}"
    )
