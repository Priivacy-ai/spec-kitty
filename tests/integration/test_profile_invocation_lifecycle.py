"""Profile-invocation lifecycle integration test for `spec-kitty next` (#843).

WP07 — charter-e2e-hardening-tranche-2-01KQ9NVQ.

Locks FR-007 / NFR-006: when `spec-kitty next` issues a composed action and
then advances it via `--result success`, the runtime MUST write paired
``started`` + ``completed`` lifecycle records under
``.kittify/events/profile-invocations/`` whose ``action`` matches the issued
step and whose ``outcome`` is in the canonical vocabulary
(``done | failed | abandoned``). The brief's expected ``skipped|blocked``
mapping is NOT in scope — see research.md R5 for the canonical-vocabulary
correction. Public ``next --result`` strings are coerced to the canonical
vocabulary inside :mod:`specify_cli.invocation.record` (``coerce_outcome``).

This test reuses the trail-record assertion pattern from
``tests/integration/test_documentation_runtime_walk.py`` so it stays
consistent with existing runtime-walk coverage. It exercises the runtime via
``decide_next_via_runtime`` rather than the CLI subprocess so it can run
hermetically in CI without a configured CLI environment, while still
proving the same end-to-end lifecycle path as ``next --json`` /
``next --result success --json`` (both call the same bridge).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.next.runtime_bridge import decide_next_via_runtime


# ---------------------------------------------------------------------------
# Fixtures — minimal repo + research-mission feature_dir
# ---------------------------------------------------------------------------


def _init_min_repo(repo_root: Path) -> None:
    """Initialize a minimal git repo to anchor the runtime."""
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    (repo_root / "README.md").write_text("# test", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"], cwd=repo_root, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )


def _scaffold_research_feature(repo_root: Path, mission_slug: str) -> Path:
    """Create a research mission feature_dir with the first-action gate artifact.

    The research mission's first composed action is ``scoping``; its happy-path
    gate artifact is ``research-questions.md``. Authoring the artifact lets
    the dispatch advance through the post-execution guard chain so the trail
    file is closed with a canonical ``done`` outcome.
    """
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_type": "research"}),
        encoding="utf-8",
    )
    (feature_dir / "research-questions.md").write_text(
        "# research questions\n", encoding="utf-8"
    )
    return feature_dir


@pytest.fixture
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    repo_root = tmp_path / "repo"
    _init_min_repo(repo_root)
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)
    monkeypatch.delenv("KITTIFY_MISSION_PATHS", raising=False)
    yield repo_root


# ---------------------------------------------------------------------------
# Test — paired lifecycle records for one composed action issued by `next`
# ---------------------------------------------------------------------------

# Research-mission composed actions (cf. research.md R5 + runtime_bridge
# _COMPOSED_ACTIONS_BY_MISSION). The first action issued by the planner is
# ``scoping``.
_RESEARCH_ACTIONS: frozenset[str] = frozenset(
    {"scoping", "methodology", "gathering", "synthesis", "output"}
)


def test_paired_started_completed_records_for_composed_next(
    isolated_repo: Path,
) -> None:
    """FR-007 / NFR-006: walking one composed action via ``next`` writes paired
    ``started`` + ``completed`` records with canonical outcome ``done``.

    The walk:

    1. ``next`` issue (``--result`` absent / ``needs_initialization``) — runtime
       resolves the first composed action (``scoping``) and writes a ``started``
       lifecycle record at issue time.
    2. ``next --result success`` — runtime advances the issued action; the
       composed dispatch closes the trail with a ``completed`` record whose
       ``outcome`` is the canonical token ``done`` (per
       :func:`specify_cli.invocation.record.coerce_outcome`).

    Reads the trail directly so the assertion stays out of the C-007 forbidden
    patch surface used in the documentation runtime walk.
    """
    _scaffold_research_feature(isolated_repo, "demo-lifecycle-walk")

    # Issue step (no advance yet).
    issued = decide_next_via_runtime(
        "test-operator",
        "demo-lifecycle-walk",
        "needs_initialization",
        isolated_repo,
    )
    assert issued.mission == "research", (
        f"Expected mission='research'; got {issued.mission!r}."
    )
    assert issued.step_id in _RESEARCH_ACTIONS, (
        f"Issued step {issued.step_id!r} not in canonical research actions "
        f"{sorted(_RESEARCH_ACTIONS)}."
    )
    issued_action = issued.step_id

    # Advance the issued step — composition dispatch closes the trail.
    decide_next_via_runtime(
        "test-operator",
        "demo-lifecycle-walk",
        "success",
        isolated_repo,
    )

    # The lifecycle directory MUST exist after one round-trip.
    invocations_dir = (
        isolated_repo / ".kittify" / "events" / "profile-invocations"
    )
    assert invocations_dir.is_dir(), (
        f"Invocations dir missing: {invocations_dir}. The runtime did not "
        "write any lifecycle records for the composed action."
    )

    trail_files = sorted(invocations_dir.glob("*.jsonl"))
    assert trail_files, (
        f"No JSONL trail files under {invocations_dir}. The composition "
        "dispatch did not produce a paired invocation trail."
    )

    # FR-007: at least one trail file MUST contain a paired started+completed
    # pair where action matches the issued step and outcome is canonical
    # ``done``. Other trails (e.g., for nested invocations) are tolerated as
    # long as one matches the FR-007 contract end-to-end.
    canonical_outcomes = {"done", "failed", "abandoned"}
    matched: list[Path] = []
    for trail in trail_files:
        events: list[dict[str, object]] = []
        for raw in trail.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if not events:
            continue

        started_events = [e for e in events if e.get("event") == "started"]
        completed_events = [e for e in events if e.get("event") == "completed"]
        if not started_events or not completed_events:
            continue

        first_started = started_events[0]
        if first_started.get("action") != issued_action:
            continue

        # invocation_id must match across started + completed.
        started_id = first_started.get("invocation_id")
        last_completed = completed_events[-1]
        completed_id = last_completed.get("invocation_id")
        assert started_id == completed_id, (
            f"Trail {trail.name}: started invocation_id {started_id!r} != "
            f"completed invocation_id {completed_id!r}. Lifecycle pairing is "
            "broken — these MUST share an invocation_id."
        )

        # FR-007 canonical outcome contract.
        outcome = last_completed.get("outcome")
        assert outcome in canonical_outcomes, (
            f"Trail {trail.name}: completed outcome {outcome!r} is not in the "
            f"canonical vocabulary {sorted(canonical_outcomes)}. "
            "coerce_outcome should have mapped 'success' -> 'done'."
        )
        # The walk drove --result=success which canonicalises to 'done'.
        assert outcome == "done", (
            f"Trail {trail.name}: expected outcome='done' for a successful "
            f"advance; got {outcome!r}."
        )

        matched.append(trail)

    assert matched, (
        "No trail file contained a paired started+completed lifecycle for "
        f"the issued action {issued_action!r}. Trails inspected: "
        f"{[t.name for t in trail_files]!r}."
    )
