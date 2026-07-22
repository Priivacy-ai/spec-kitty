"""Transactional status-transition integration tests for issue #1356."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from specify_cli.coordination.status_transition import (
    emit_status_transition_batch_transactional,
    emit_status_transition_transactional,
    read_current_wp_state_transactional,
    read_event_stream_transactional,
    read_events_transactional,
)
from specify_cli.coordination.status_service import (
    EventLogReadContract,
    EventLogWriteContract,
    StatusContractError,
    append_event_log,
    append_event_stream_log,
    merge_append_preserving_coordination_event_log_bytes,
    read_event_log,
)
from specify_cli.coordination.transaction import BookkeepingCommitFailed, BookkeepingWorktreeMissing
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.status.models import (
    InnerStateChanged,
    Lane,
    ReviewOverride,
    Status,
    StatusEvent,
    TransitionRequest,
    WPInnerStateDelta,
)

pytest_plugins = ("tests.conftest_saas_sink",)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "status-transaction"
MID8 = "01KT1356"
MISSION_ID = "01KT1356000000000000000000"
MISSION_DIRNAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIRNAME}"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.invalid")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    feature_dir = r / "kitty-specs" / MISSION_DIRNAME
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "coordination_branch": COORD_BRANCH,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _git(r, "add", "kitty-specs")
    _git(r, "commit", "-q", "-m", "seed mission")
    _git(r, "branch", COORD_BRANCH)
    return r


def _request(repo: Path) -> TransitionRequest:
    return TransitionRequest(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        to_lane="claimed",
        actor="issue-1356-test",
        repo_root=repo,
    )


def _status_event(event_id: str, *, to_lane: str = "claimed") -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane(to_lane),
        at="2026-06-01T00:00:00+00:00",
        actor="contract-test",
        force=False,
        execution_mode="worktree",
    )


def _seed_planned_on_coord(repo: Path) -> StatusEvent:
    """Seed WP01 out of the non-display 'genesis' state into 'planned'.

    A fresh WP derives from_lane 'genesis', so the first lane transition must
    be genesis -> planned (as finalize-tasks does). The seed is written and
    committed directly on the coordination branch via a throwaway worktree, so
    it does not fan out — only the transition under test does.
    """
    seed_event = StatusEvent(
        event_id="01SEEDGENESIS0000000000001",
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.GENESIS,
        to_lane=Lane.PLANNED,
        at="2026-05-31T00:00:00+00:00",
        actor="seed",
        force=False,
        reason="seed",
        execution_mode="worktree",
    )
    worktree = repo / ".worktrees" / "seed-genesis"
    _git(repo, "worktree", "add", "-q", str(worktree), COORD_BRANCH)
    coord_feature_dir = worktree / "kitty-specs" / MISSION_DIRNAME
    append_event_log(
        EventLogWriteContract.coordination_transaction_append(coord_feature_dir),
        seed_event,
    )
    _git(worktree, "add", "kitty-specs")
    _git(worktree, "commit", "-q", "-m", "seed genesis->planned")
    _git(repo, "worktree", "remove", "-f", str(worktree))
    return seed_event


def test_transactional_emit_fans_out_only_after_commit(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    _seed_planned_on_coord(repo)
    event = emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 1
    assert mock_saas_sink.last_kwargs["causation_id"] == event.event_id

    show = _git(repo, "show", f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/status.events.jsonl")
    assert event.event_id in show.stdout


def test_transactional_claim_and_binding_use_one_atomic_stream_append(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A coord claim and its resolved binding are one crash-atomic file replace."""
    from specify_cli.status import store as status_store

    _seed_planned_on_coord(repo)
    request = _request(repo)
    request.annotation_delta = WPInnerStateDelta(
        role="implementer",
        agent_profile="python-pedro",
        model="claude-opus-4-6",
    )
    original_append = status_store._append_serialized_atomic
    appended_units: list[list[dict[str, object]]] = []

    def _capture(feature_dir: Path, payloads: list[dict[str, object]]) -> None:
        appended_units.append(payloads)
        original_append(feature_dir, payloads)

    monkeypatch.setattr(status_store, "_append_serialized_atomic", _capture)

    emit_status_transition_transactional(request, sync_dossier=False)

    assert len(appended_units) == 1  # golden-count: cardinality-is-contract
    assert [payload.get("kind", "transition") for payload in appended_units[0]] == [
        "transition",
        "annotation",
    ]


def test_production_implement_lifecycle_persists_two_hops_and_binding_atomically(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real planned implementation start is one crash-atomic durability unit."""
    from specify_cli.status import start_implementation_status
    from specify_cli.status import store as status_store

    _seed_planned_on_coord(repo)
    original_append = status_store._append_serialized_atomic
    appended_units: list[list[dict[str, object]]] = []

    def _capture(feature_dir: Path, payloads: list[dict[str, object]]) -> None:
        appended_units.append(payloads)
        original_append(feature_dir, payloads)

    monkeypatch.setattr(status_store, "_append_serialized_atomic", _capture)

    start_implementation_status(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        actor={
            "role": "implementer",
            "profile": "python-pedro",
            "tool": "claude",
            "model": "claude-opus-4-6",
        },
        workspace_context="worktree:/var/empty/wp01",
        execution_mode="worktree",
        repo_root=repo,
        annotation_delta=WPInnerStateDelta(
            role="implementer",
            agent_profile="python-pedro",
            model="claude-opus-4-6",
        ),
        sync_dossier=False,
    )

    assert len(appended_units) == 1  # golden-count: cardinality-is-contract
    assert [payload.get("kind", "transition") for payload in appended_units[0]] == [
        "transition",
        "transition",
        "annotation",
    ]


def test_transactional_read_targets_coordination_branch(repo: Path) -> None:
    seed = _seed_planned_on_coord(repo)
    request = _request(repo)
    request.annotation_delta = WPInnerStateDelta(
        agent="claude",
        assignee="implementer",
    )
    event = emit_status_transition_transactional(request, sync_dossier=False)

    events = read_events_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        repo_root=repo,
    )

    # The coordination branch carries the genesis->planned seed plus the
    # planned->claimed transition under test.
    assert [e.event_id for e in events] == [seed.event_id, event.event_id]
    stream = read_event_stream_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        repo_root=repo,
    )
    assert [item.event_id for item in stream.transitions] == [seed.event_id, event.event_id]
    assert len(stream.annotations) == 1  # golden-count: cardinality-is-contract
    assert stream.annotations[0].delta.agent == "claude"
    assert not (repo / "kitty-specs" / MISSION_DIRNAME / "status.events.jsonl").exists()


def test_review_gate_reads_subtask_annotations_from_unmaterialized_coord_branch(
    repo: Path,
) -> None:
    """The review gate must not fall back to stale primary runtime state."""
    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-test.md").write_text(
        "---\nwork_package_id: WP01\ndependencies: []\nsubtasks: [T001]\n---\n# WP01\n",
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "add authored subtask roster")

    _seed_planned_on_coord(repo)
    request = _request(repo)
    request.annotation_delta = WPInnerStateDelta(subtasks={"T001": Status.DONE})
    emit_status_transition_transactional(request, sync_dossier=False)

    from specify_cli.status import TransitionRequest
    from specify_cli.status import emit as status_emit
    from specify_cli.status.aggregate import MissionStatus

    aggregate = MissionStatus(
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        mid8=MID8,
        topology="coordination",
        read_dir=feature_dir,
        repo_root=repo,
        coordination_branch=COORD_BRANCH,
    )
    transition = TransitionRequest(
        feature_dir=feature_dir,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        to_lane=Lane.FOR_REVIEW,
        actor="review-gate",
        repo_root=repo,
    )
    worktrees_dir = repo / ".worktrees"
    worktrees_before_read = (
        tuple(sorted(candidate.name for candidate in worktrees_dir.iterdir()))
        if worktrees_dir.exists()
        else ()
    )

    subtasks_complete, evidence = aggregate._resolve_review_gate_inputs(
        request=transition,
        from_lane_str=str(Lane.IN_PROGRESS),
        resolved_to_lane=str(Lane.FOR_REVIEW),
        status_emit=status_emit,
        lane_in_progress=Lane.IN_PROGRESS,
        lane_for_review=Lane.FOR_REVIEW,
    )

    assert subtasks_complete is True
    assert evidence is True
    assert not (feature_dir / "status.events.jsonl").exists()
    worktrees_after_read = (
        tuple(sorted(candidate.name for candidate in worktrees_dir.iterdir()))
        if worktrees_dir.exists()
        else ()
    )
    assert worktrees_after_read == worktrees_before_read


def test_merge_done_evidence_reads_unmaterialized_coord_branch(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Merge evidence and runtime agent come from the committed coord stream."""
    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-test.md").write_text(
        "---\nwork_package_id: WP01\ndependencies: []\nsubtasks: []\n---\n# WP01\n",
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "add merge planning artifact")

    _seed_planned_on_coord(repo)
    review = ReviewOverride(
        at="2026-07-21T00:00:00+00:00",
        actor="reviewer-renata",
        wp_id="WP01",
        reason="approved",
    )
    approved = StatusEvent(
        event_id="01MERGEAPPROVED00000000000",
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.APPROVED,
        at=review.at,
        actor="reviewer-renata",
        force=True,
        execution_mode="worktree",
    )
    annotation = InnerStateChanged(
        event_id="01H22222222222222222222222",
        wp_id="WP01",
        at=review.at,
        actor="reviewer-renata",
        delta=WPInnerStateDelta(agent="claude", review=review),
    )
    worktree = repo / ".worktrees" / "seed-merge-state"
    _git(repo, "worktree", "add", "-q", str(worktree), COORD_BRANCH)
    coord_feature_dir = worktree / "kitty-specs" / MISSION_DIRNAME
    append_event_stream_log(
        EventLogWriteContract.coordination_transaction_append(coord_feature_dir),
        [approved, annotation],
    )
    _git(worktree, "add", "kitty-specs")
    _git(worktree, "commit", "-q", "-m", "seed approved merge state")
    _git(repo, "worktree", "remove", "-f", str(worktree))

    emit_mock = Mock()
    monkeypatch.setattr(
        "specify_cli.coordination.status_transition.emit_status_transition_transactional",
        emit_mock,
    )
    from specify_cli.merge.done_bookkeeping import _mark_wp_merged_done

    _mark_wp_merged_done(repo, MISSION_SLUG, "WP01", "main")

    emit_mock.assert_called_once()
    done_request = emit_mock.call_args.args[0]
    assert done_request.to_lane == Lane.DONE
    assert done_request.evidence["review"]["reviewer"] == "reviewer-renata"
    assert not (feature_dir / "status.events.jsonl").exists()
    assert not any((repo / ".worktrees").iterdir())


def test_primary_checkout_event_log_read_remains_explicit(repo: Path) -> None:
    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    event = _status_event("01PRIMARY00000000000000000")

    append_event_log(EventLogWriteContract.primary_checkout_append(feature_dir), event)
    events = read_event_log(EventLogReadContract.primary_checkout(feature_dir))

    assert [e.event_id for e in events] == [event.event_id]
    assert (feature_dir / "status.events.jsonl").exists()


def test_coordination_branch_ref_read_ignores_stale_primary_checkout(repo: Path) -> None:
    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    primary_event = _status_event("01PRIMARYSTALE00000000000", to_lane="planned")
    coord_event = _status_event("01COORDCURRENT00000000000", to_lane="claimed")
    append_event_log(EventLogWriteContract.primary_checkout_append(feature_dir), primary_event)

    worktree = repo / ".worktrees" / "seed-coord"
    _git(repo, "worktree", "add", "-q", str(worktree), COORD_BRANCH)
    coord_feature_dir = worktree / "kitty-specs" / MISSION_DIRNAME
    append_event_log(
        EventLogWriteContract.coordination_transaction_append(coord_feature_dir),
        coord_event,
    )
    _git(worktree, "add", "kitty-specs")
    _git(worktree, "commit", "-q", "-m", "seed coord event")
    _git(repo, "worktree", "remove", "-f", str(worktree))

    events = read_event_log(
        EventLogReadContract.coordination_branch_ref(
            repo_root=repo,
            destination_ref=COORD_BRANCH,
            feature_dir=coord_feature_dir,
            parser_feature_dir=feature_dir,
        )
    )

    assert [e.event_id for e in events] == [coord_event.event_id]
    assert read_event_log(EventLogReadContract.primary_checkout(feature_dir))[0].event_id == primary_event.event_id


def test_read_contract_cannot_be_used_as_write_contract(repo: Path) -> None:
    event = _status_event("01CONTRACTFAIL000000000000")

    with pytest.raises(StatusContractError):
        append_event_log(  # type: ignore[arg-type]
            EventLogReadContract.primary_checkout(repo / "kitty-specs" / MISSION_DIRNAME),
            event,
        )


def test_wrong_write_target_fails_loudly(repo: Path) -> None:
    event = _status_event("01WRONGTARGET000000000000")
    primary_feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    coordination_feature_dir = repo / ".worktrees" / "coord" / "kitty-specs" / MISSION_DIRNAME

    with pytest.raises(StatusContractError, match="primary_checkout_append"):
        append_event_log(
            EventLogWriteContract.primary_checkout_append(coordination_feature_dir),
            event,
        )

    with pytest.raises(StatusContractError, match="coordination_transaction_append"):
        append_event_log(
            EventLogWriteContract.coordination_transaction_append(primary_feature_dir),
            event,
        )


def test_wrong_read_source_fails_loudly(repo: Path) -> None:
    primary_feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    coordination_feature_dir = repo / ".worktrees" / "coord" / "kitty-specs" / MISSION_DIRNAME

    with pytest.raises(StatusContractError, match="primary_checkout"):
        read_event_log(EventLogReadContract.primary_checkout(coordination_feature_dir))

    with pytest.raises(StatusContractError, match="coordination_worktree"):
        read_event_log(EventLogReadContract.coordination_worktree(primary_feature_dir))


def test_append_preserving_coordination_merge_keeps_existing_history() -> None:
    coord = b'{"event_id":"existing"}\n'
    incoming = b'{"event_id":"existing"}\n{"event_id":"new"}\n'

    merged = merge_append_preserving_coordination_event_log_bytes(coord, incoming)

    assert merged == b'{"event_id":"existing"}\n{"event_id":"new"}\n'


def test_transactional_read_does_not_create_coordination_worktree(repo: Path) -> None:
    assert not (repo / ".worktrees").exists()

    events = read_events_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        repo_root=repo,
    )

    assert events == []
    assert not (repo / ".worktrees").exists()
    assert _git(repo, "status", "--short").stdout == ""


def test_transactional_emit_skips_fanout_when_commit_rolls_back(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    # Seed planned before installing the rejecting hook so the transition
    # under test is genesis-free (claimed is reachable from planned).
    _seed_planned_on_coord(repo)

    hooks_dir = repo / ".git" / "hooks-reject"
    hooks_dir.mkdir()
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    _git(repo, "config", "core.hooksPath", str(hooks_dir))

    with pytest.raises(BookkeepingCommitFailed):
        emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 0
    # The coord branch still carries only the seed (genesis->planned); the
    # rolled-back claimed transition must NOT have been committed.
    committed = _git(
        repo,
        "show",
        f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/status.events.jsonl",
        check=False,
    )
    assert committed.returncode == 0
    assert '"to_lane": "planned"' in committed.stdout
    assert '"to_lane": "claimed"' not in committed.stdout


def test_transactional_emit_fails_closed_when_coordination_branch_missing(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    _git(repo, "branch", "-D", COORD_BRANCH)

    with pytest.raises(BookkeepingWorktreeMissing):
        emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 0
    assert not (repo / "kitty-specs" / MISSION_DIRNAME / "status.events.jsonl").exists()


def test_transactional_emit_fails_closed_on_malformed_meta(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    (repo / "kitty-specs" / MISSION_DIRNAME / "meta.json").write_text(
        "{bad json",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Malformed JSON"):
        emit_status_transition_transactional(_request(repo), sync_dossier=False)

    assert mock_saas_sink.call_count == 0
    assert not (repo / "kitty-specs" / MISSION_DIRNAME / "status.events.jsonl").exists()


def _seed_coord_branch_without_meta(repo: Path) -> StatusEvent:
    """Set up the coordination branch the way a real mission has it.

    On the coordination branch the mission folder holds the status log but no
    ``meta.json`` — ``meta.json`` only lives in the normal checkout. We also
    record WP01 as ``planned`` so the work-start batch has a valid starting
    point. This is done in a temporary worktree that we delete before adding the
    real one, because git won't let the same branch be checked out twice at once.
    """
    seed_event = StatusEvent(
        event_id="01SEEDGENESIS0000000000001",
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.GENESIS,
        to_lane=Lane.PLANNED,
        at="2026-05-31T00:00:00+00:00",
        actor="seed",
        force=False,
        reason="seed",
        execution_mode="worktree",
    )
    worktree = repo / ".worktrees" / "seed-coord-nometa"
    _git(repo, "worktree", "add", "-q", str(worktree), COORD_BRANCH)
    coord_feature_dir = worktree / "kitty-specs" / MISSION_DIRNAME
    (coord_feature_dir / "meta.json").unlink()
    append_event_log(
        EventLogWriteContract.coordination_transaction_append(coord_feature_dir),
        seed_event,
    )
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "coord: status surface without meta")
    _git(repo, "worktree", "remove", "-f", str(worktree))
    return seed_event


def test_transactional_batch_rejects_request_without_any_feature_dir(repo: Path) -> None:
    """A batch whose first request carries neither feature_dir nor mission_dir fails fast.

    The transactional batch needs a folder to anchor identity + the same-WP
    consistency check on. If the first request supplies neither ``feature_dir``
    nor ``mission_dir`` (both default to ``None``) it must raise ``TypeError``
    before touching git — alongside the existing missing-slug / missing-wp guard
    — rather than crashing deeper in identity resolution.
    """
    request = TransitionRequest(
        feature_dir=None,
        mission_dir=None,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        to_lane="claimed",
        actor="no-feature-dir-test",
        repo_root=repo,
    )

    with pytest.raises(
        TypeError, match="requires feature_dir/mission_dir, mission_slug, and wp_id"
    ):
        emit_status_transition_batch_transactional([request], sync_dossier=False)


def test_transactional_batch_same_wp_under_coord_topology_does_not_misfire(
    repo: Path,
    mock_saas_sink: Any,
) -> None:
    """Starting a work package on a coordination-mode mission used to crash here.

    Such a mission lives in two folders: the normal checkout and a separate
    coordination worktree. The batch that starts a work package points at the
    coordination folder, but the guard compared it against the normal-checkout
    folder and rejected the batch as "more than one work package" — crashing
    start-implementation. This builds that two-folder setup and checks the batch
    now succeeds.
    """
    seed = _seed_coord_branch_without_meta(repo)

    # Register the coordination worktree (in real life it already exists by the
    # time work starts) and pass the full mission-folder name, the way the
    # orchestrator does. This makes the requests point at the coordination folder
    # while the mission's identity still resolves to the normal checkout — the
    # mismatch that used to trip the guard.
    coord_worktree = CoordinationWorkspace.worktree_path(repo, MISSION_DIRNAME, MID8)
    _git(repo, "worktree", "add", "-q", str(coord_worktree), COORD_BRANCH)
    coord_feature_dir = coord_worktree / "kitty-specs" / MISSION_DIRNAME

    def _coord_request(to_lane: str) -> TransitionRequest:
        return TransitionRequest(
            feature_dir=coord_feature_dir,
            mission_slug=MISSION_DIRNAME,
            wp_id="WP01",
            to_lane=to_lane,
            actor="coord-batch-test",
            repo_root=repo,
        )

    events = emit_status_transition_batch_transactional(
        [_coord_request("claimed"), _coord_request("in_progress")],
        sync_dossier=False,
    )

    assert [e.to_lane for e in events] == [Lane.CLAIMED, Lane.IN_PROGRESS]
    assert events[0].from_lane == seed.to_lane  # planned -> claimed


def _seed_planned_on_primary(repo: Path) -> StatusEvent:
    """Append a genesis->planned seed directly to the primary checkout log."""
    seed_event = StatusEvent(
        event_id="01SEEDPRIMARY000000000001",
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        wp_id="WP01",
        from_lane=Lane.GENESIS,
        to_lane=Lane.PLANNED,
        at="2026-05-31T00:00:00+00:00",
        actor="seed",
        force=False,
        reason="seed",
        execution_mode="worktree",
    )
    append_event_log(
        EventLogWriteContract.primary_checkout_append(repo / "kitty-specs" / MISSION_DIRNAME),
        seed_event,
    )
    return seed_event


def test_transactional_read_falls_back_to_primary_when_coord_branch_deleted(repo: Path) -> None:
    """A deleted coordination branch must not mis-read WPs as genesis (#1847).

    Post-merge cleanup deletes the coordination branch while meta.json still
    declares it. The read path must then report lanes from the primary
    checkout event log instead of reading the dangling ref as empty.
    """
    from specify_cli.coordination.status_transition import read_current_wp_state_transactional

    seed = _seed_planned_on_primary(repo)
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "merge mission artifacts to main")
    _git(repo, "branch", "-D", COORD_BRANCH)

    lane, actor = read_current_wp_state_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        repo_root=repo,
    )
    assert lane == Lane.PLANNED
    assert actor == "seed"

    events = read_events_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_SLUG,
        repo_root=repo,
    )
    assert [e.event_id for e in events] == [seed.event_id]


# ---------------------------------------------------------------------------
# M6 error contract (PR #1850): the fail-closed surface refusal
# (StatusReadPathNotFound — coord worktree root materialized, mission dir
# absent) must never escape the transactional paths as a raw traceback. The
# transaction identity anchors on the canonical primary dir the structured
# refusal already carries; failures stay structured (Bookkeeping* errors).
# ---------------------------------------------------------------------------


def _materialize_coord_root_without_mission_dir(repo: Path) -> Path:
    """The fail-closed window: coord worktree root exists, mission dir absent."""
    coord_root = repo / ".worktrees" / f"{MISSION_DIRNAME}-coord"
    coord_root.mkdir(parents=True)
    return coord_root


def _canonical_slug_request(repo: Path) -> TransitionRequest:
    """Request carrying the canonical mission-dir name (what resolvers hand over)."""
    return TransitionRequest(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_DIRNAME,
        wp_id="WP01",
        to_lane="planned",
        actor="m6-error-contract-test",
        repo_root=repo,
    )


def test_transactional_read_survives_fail_closed_surface_refusal(repo: Path) -> None:
    _materialize_coord_root_without_mission_dir(repo)

    events = read_events_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_DIRNAME,
        repo_root=repo,
    )

    assert events == []


def test_transactional_wp_state_read_survives_fail_closed_surface_refusal(
    repo: Path,
) -> None:
    _materialize_coord_root_without_mission_dir(repo)

    lane, actor = read_current_wp_state_transactional(
        feature_dir=repo / "kitty-specs" / MISSION_DIRNAME,
        mission_slug=MISSION_DIRNAME,
        wp_id="WP01",
        repo_root=repo,
    )

    assert lane == Lane.GENESIS
    assert actor is None


def test_transactional_emit_fail_closed_surface_refusal_stays_structured(
    repo: Path,
) -> None:
    """The emit path refuses with a structured Bookkeeping error, not a raw leak.

    The mkdir'd coord root is not a valid git worktree, so after identity
    resolution succeeds the transaction refuses with its own structured
    BOOKKEEPING_WORKTREE_MISSING error — never a raw StatusReadPathNotFound.
    """
    _materialize_coord_root_without_mission_dir(repo)

    with pytest.raises(BookkeepingWorktreeMissing):
        emit_status_transition_transactional(
            _canonical_slug_request(repo), sync_dossier=False
        )
