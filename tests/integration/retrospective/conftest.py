"""Shared fixtures for WP11 retrospective integration tests.

Provides:
  - ``tmp_repo``: a function-scoped fixture that copies a named fixture
    mission into ``tmp_path`` with a fresh mission_id, giving each test
    a clean isolated repo.
  - ``make_completed_record``: factory for minimal completed RetrospectiveRecord.
  - ``make_skipped_record``: factory for minimal skipped RetrospectiveRecord.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Literal

import pytest
import ulid as _ulid_mod

from specify_cli.retrospective.schema import (
    ActorRef,
    MissionIdentity,
    Mode,
    ModeSourceSignal,
    RecordProvenance,
    RetrospectiveRecord,
)

# ---------------------------------------------------------------------------
# Shared actor references
# ---------------------------------------------------------------------------

HUMAN_ACTOR = ActorRef(kind="human", id="test-operator@example.com", profile_id=None)
AGENT_ACTOR = ActorRef(kind="agent", id="facilitator", profile_id="retrospective-facilitator")
RUNTIME_ACTOR = ActorRef(kind="runtime", id="next", profile_id=None)

# ---------------------------------------------------------------------------
# Fixture directory
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Record factories
# ---------------------------------------------------------------------------


def make_completed_record(
    *,
    mission_id: str,
    mission_slug: str,
    mission_type: str = "software-dev",
    mode_value: Literal["autonomous", "human_in_command"] = "autonomous",
) -> RetrospectiveRecord:
    """Build a minimal valid completed RetrospectiveRecord."""
    now = "2026-04-27T11:00:00+00:00"
    return RetrospectiveRecord(
        schema_version="1",
        mission=MissionIdentity(
            mission_id=mission_id,
            mid8=mission_id[:8],
            mission_slug=mission_slug,
            mission_type=mission_type,
            mission_started_at="2026-04-27T10:00:00+00:00",
            mission_completed_at=now,
        ),
        mode=Mode(
            value=mode_value,
            source_signal=ModeSourceSignal(kind="environment", evidence="SPEC_KITTY_MODE"),
        ),
        status="completed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at=now,
        actor=AGENT_ACTOR,
        provenance=RecordProvenance(
            authored_by=AGENT_ACTOR,
            runtime_version="0.0.0-test",
            written_at=now,
            schema_version="1",
        ),
    )


def make_skipped_record(
    *,
    mission_id: str,
    mission_slug: str,
    skip_reason: str,
) -> RetrospectiveRecord:
    """Build a minimal valid skipped RetrospectiveRecord."""
    now = "2026-04-27T11:00:00+00:00"
    return RetrospectiveRecord(
        schema_version="1",
        mission=MissionIdentity(
            mission_id=mission_id,
            mid8=mission_id[:8],
            mission_slug=mission_slug,
            mission_type="software-dev",
            mission_started_at="2026-04-27T10:00:00+00:00",
            mission_completed_at=None,
        ),
        mode=Mode(
            value="human_in_command",
            source_signal=ModeSourceSignal(kind="environment", evidence="SPEC_KITTY_MODE"),
        ),
        status="skipped",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at=None,
        actor=HUMAN_ACTOR,
        provenance=RecordProvenance(
            authored_by=HUMAN_ACTOR,
            runtime_version="0.0.0-test",
            written_at=now,
            schema_version="1",
        ),
        skip_reason=skip_reason,
    )


# ---------------------------------------------------------------------------
# tmp_repo fixture factory
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> TmpRepoFactory:
    """Return a factory that creates isolated mission repos from fixtures."""
    return TmpRepoFactory(tmp_path)


class TmpRepoFactory:
    """Creates isolated per-test mission repos from fixture directories.

    Usage::

        def test_something(tmp_repo):
            repo, feature_dir, mission_id = tmp_repo("software-dev-min")
    """

    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path
        self._counter = 0

    def __call__(self, fixture_name: str) -> tuple[Path, Path, str]:
        """Copy fixture into tmp_path, assign a fresh mission_id.

        Args:
            fixture_name: Name of the fixture directory under fixtures/.

        Returns:
            (repo_root, feature_dir, mission_id)
            - repo_root: the isolated repo root
            - feature_dir: kitty-specs/<slug>/ directory
            - mission_id: the freshly minted ULID for this test
        """
        src = _FIXTURES_DIR / fixture_name
        if not src.is_dir():
            raise FileNotFoundError(f"Fixture directory not found: {src}. Available fixtures: {[d.name for d in _FIXTURES_DIR.iterdir() if d.is_dir()]}")

        self._counter += 1
        dest_name = f"repo-{self._counter}-{fixture_name}"
        repo_root = self._tmp_path / dest_name
        shutil.copytree(src, repo_root)

        # Mint a fresh mission_id for this test run.
        mission_id = str(_ulid_mod.ULID())

        # Rewrite meta.json with the fresh mission_id.
        kitty_specs = repo_root / "kitty-specs"
        for mission_dir in kitty_specs.iterdir():
            if not mission_dir.is_dir():
                continue
            meta_path = mission_dir / "meta.json"
            if meta_path.exists():
                meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["mission_id"] = mission_id
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                feature_dir = mission_dir
                return repo_root, feature_dir, mission_id

        raise RuntimeError(f"Fixture '{fixture_name}' has no kitty-specs/<slug>/meta.json. Please add a meta.json to the fixture.")


# ---------------------------------------------------------------------------
# Convenience event-log readers (used across test modules)
# ---------------------------------------------------------------------------


def read_events(feature_dir: Path) -> list[dict[str, Any]]:
    """Read all lines from status.events.jsonl."""
    events_path = feature_dir / "status.events.jsonl"
    if not events_path.exists():
        return []
    return [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def event_names(feature_dir: Path) -> list[str]:
    """Return the ordered list of event_name values from the event log."""
    return [e["event_name"] for e in read_events(feature_dir)]
