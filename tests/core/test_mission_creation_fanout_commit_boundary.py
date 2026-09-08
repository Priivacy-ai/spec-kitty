"""Real create/refusal; only hosted effect boundary is replaced by a recorder.

No network request or sync queue mutation is performed by this test.
"""
import pytest
import subprocess
from tests.acceptance.test_first_run_path_3_2_6_1 import _git


def test_protected_refusal_retains_local_source_for_published_mission(tmp_path, monkeypatch):
    from specify_cli.core.mission_creation import create_mission_core
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    _git(tmp_path, "branch", "-M", "main")
    emitted = []

    def capture(**kwargs):
        emitted.append(kwargs)

    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", capture)
    with pytest.raises(RuntimeError, match="refusing to commit to protected branch"):
        create_mission_core(tmp_path, "discarded", allow_worktree_context=True, **_mission_summary("discarded"))
    created = [item for item in emitted if item["envelope"]["event_type"] == "MissionCreated"]
    # A preflight fix may correctly prevent all fanout; emitted events must retain their source.
    assert all(item["log_path"].exists() for item in created), created


def test_creation_fanout_follows_the_scaffold_commit(tmp_path, monkeypatch):
    from specify_cli.core.mission_creation import create_mission_core
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    emitted = []

    def capture(**kwargs):
        log_path = kwargs["log_path"]
        relative = log_path.relative_to(tmp_path).as_posix()
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative}"], cwd=tmp_path, capture_output=True, check=False,
        )
        emitted.append((kwargs["envelope"]["event_type"], committed.returncode))

    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", capture)
    create_mission_core(tmp_path, "committed-first", allow_worktree_context=True, **_mission_summary("committed-first"))
    assert {event_type for event_type, _ in emitted} >= {"MissionCreated", "SpecifyStarted"}
    assert all(returncode == 0 for _, returncode in emitted), emitted


def test_late_commit_refusal_does_not_fanout_discarded_creation(tmp_path, monkeypatch):
    from specify_cli.core.mission_creation import create_mission_core
    from specify_cli.git.commit_helpers import ProtectedBranchRefused
    from tests.core.test_mission_create_scaffold_rollback import _init_git_repo, _mission_summary

    _init_git_repo(tmp_path)
    emitted = []

    def refuse(*args, **kwargs):
        raise ProtectedBranchRefused(destination_ref="main", worktree_root=tmp_path, commit_message="scaffold")

    monkeypatch.setattr("specify_cli.status.adapters.fire_lifecycle_saas_fanout", lambda **kwargs: emitted.append(kwargs))
    monkeypatch.setattr("specify_cli.core.mission_creation._commit_feature_file", refuse)
    with pytest.raises(RuntimeError, match="refusing to commit to protected branch"):
        create_mission_core(tmp_path, "late-refusal", allow_worktree_context=True, **_mission_summary("late-refusal"))
    assert not emitted
