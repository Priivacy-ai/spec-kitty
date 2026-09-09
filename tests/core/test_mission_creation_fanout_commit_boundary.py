"""Real create/refusal; only hosted effect boundary is replaced by a recorder.

No network request or sync queue mutation is performed by this test.
"""

import pytest
import subprocess
from pathlib import Path


def _git(repo: Path, *args: str):
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)


pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def test_protected_bootstrap_preserves_disclosed_local_source(tmp_path, monkeypatch):
    from specify_cli.core.mission_creation import create_mission_core
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    _git(tmp_path, "branch", "-M", "main")
    emitted = []
    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", lambda **kwargs: emitted.append(kwargs))
    result = create_mission_core(tmp_path, "bootstrap", allow_worktree_context=True, **_mission_summary("bootstrap"))
    assert result.feature_dir / "status.events.jsonl" in result.uncommitted_files
    assert [item["envelope"]["event_type"] for item in emitted] == ["MissionCreated", "SpecifyStarted"]
    assert all(item["log_path"].exists() for item in emitted)


def test_creation_fanout_follows_the_scaffold_commit(tmp_path, monkeypatch):
    from specify_cli.core.mission_creation import create_mission_core
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    emitted = []

    def capture(**kwargs):
        log_path = kwargs["log_path"]
        relative = log_path.relative_to(tmp_path).as_posix()
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )
        emitted.append((kwargs["envelope"]["event_type"], committed.returncode))

    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", capture)
    create_mission_core(tmp_path, "committed-first", allow_worktree_context=True, **_mission_summary("committed-first"))
    assert [event_type for event_type, _ in emitted] == ["MissionCreated", "SpecifyStarted"]
    assert all(returncode == 0 for _, returncode in emitted), emitted


def test_hard_commit_failure_does_not_fanout_discarded_creation(tmp_path, monkeypatch):
    from specify_cli.core.mission_creation import create_mission_core
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    emitted = []

    def refuse(*args, **kwargs):
        raise RuntimeError("injected scaffold commit failure")

    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", lambda **kwargs: emitted.append(kwargs))
    monkeypatch.setattr("specify_cli.core.mission_creation._commit_feature_file", refuse)
    with pytest.raises(RuntimeError, match="injected scaffold commit failure"):
        create_mission_core(tmp_path, "late-refusal", allow_worktree_context=True, **_mission_summary("late-refusal"))
    assert not emitted


def test_origin_commit_failure_preserves_evidence_without_creation_fanout(tmp_path, monkeypatch):
    from specify_cli.core import mission_creation
    from specify_cli.mission_metadata import write_meta
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    original_head = _git(tmp_path, "rev-parse", "HEAD").stdout
    committed = mission_creation._commit_feature_file
    emitted = []
    calls = []

    def bind(*, repo_root, feature_dir, meta):
        meta["origin_ticket"] = {"id": "TEST-1"}
        write_meta(feature_dir, meta)
        return True, True, None, meta

    def commit(*args, **kwargs):
        calls.append(args[2])
        if len(calls) == 2:
            raise RuntimeError("injected origin commit failure")
        return committed(*args, **kwargs)

    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", lambda **kwargs: emitted.append(kwargs))
    monkeypatch.setattr(mission_creation, "_consume_pending_origin_if_present", bind)
    monkeypatch.setattr(mission_creation, "_commit_feature_file", commit)
    with pytest.raises(RuntimeError, match="origin-ticket binding commit failed"):
        mission_creation.create_mission_core(tmp_path, "origin-failure", allow_worktree_context=True, **_mission_summary("origin-failure"))
    assert calls == ["scaffold", "origin-ticket binding"]
    assert not emitted
    assert _git(tmp_path, "rev-parse", "HEAD").stdout == original_head
    assert len(list((tmp_path / "kitty-specs").glob("*/status.events.jsonl"))) == 1


def test_head_mismatch_bootstrap_keeps_planning_target_and_disclosure(tmp_path, monkeypatch):
    from specify_cli.core.mission_creation import create_mission_core
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    _git(tmp_path, "branch", "planning-work")
    emitted = []
    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", lambda **kwargs: emitted.append(kwargs))
    result = create_mission_core(tmp_path, "other-target", target_branch="planning-work", allow_worktree_context=True, **_mission_summary("other-target"))
    assert result.target_branch == "planning-work"
    assert result.current_branch == "operator-work"
    assert result.feature_dir / "status.events.jsonl" in result.uncommitted_files
    assert [item["envelope"]["event_type"] for item in emitted] == ["MissionCreated", "SpecifyStarted"]
    assert _git(tmp_path, "branch", "--show-current").stdout.strip() == "operator-work"
