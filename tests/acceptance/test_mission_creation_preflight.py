"""Independent PR4051 regressions: exercise real CLI, no product edits."""
from pathlib import Path

import pytest

from tests.acceptance.test_first_run_path_3_2_6_1 import (
    _cli, _git, _missions, _unwrapped,
    project as project,
)


def test_numbered_slug_protected_refusal_leaves_no_orphan(project):
    result = _cli(project, "agent", "mission", "create", "068-task-list", "--json")
    assert result.returncode != 0
    assert "refusing to commit to protected branch" in _unwrapped(result)
    assert _missions(project) == [], _missions(project)


def test_head_mismatch_recovery_does_not_duplicate_mission(project):
    _git(project, "checkout", "-b", "operator-work")
    _git(project, "branch", "planning-work")
    failed = _cli(project, "agent", "mission", "create", "branch-recovery", "--target-branch", "planning-work", "--json")
    assert failed.returncode != 0, _unwrapped(failed)
    assert "checkout planning-work" in _unwrapped(failed), _unwrapped(failed)
    _git(project, "checkout", "planning-work")
    retried = _cli(project, "agent", "mission", "create", "branch-recovery", "--json")
    assert retried.returncode == 0, _unwrapped(retried)
    assert len(_missions(project)) == 1, _missions(project)


@pytest.mark.parametrize('topology', ['single_branch', 'lanes'])
def test_unborn_branch_flat_cli_refuses_without_scaffold(tmp_path: Path, topology: str):
    repo = tmp_path / topology
    repo.mkdir()
    _git(repo, 'init', '-b', 'my-first-mission')
    _git(repo, 'config', 'user.email', 'review@example.com')
    _git(repo, 'config', 'user.name', 'Review')
    initialized = _cli(repo, 'init', '.', '--ai', 'claude')
    assert initialized.returncode == 0, _unwrapped(initialized)
    assert not list((repo / '.git' / 'refs' / 'heads').glob('*'))
    result = _cli(repo, 'agent', 'mission', 'create', 'task-list', '--topology', topology, '--json')
    actual = {'exit_nonzero': result.returncode != 0,
              'has_initial_commit_remedy': 'git commit' in _unwrapped(result),
              'missions': _missions(repo)}
    expected = {'exit_nonzero': True, 'has_initial_commit_remedy': True, 'missions': []}
    assert actual == expected, f'{actual}\n{_unwrapped(result)}'


def test_committed_owned_checkout_does_not_use_primary_unborn_head(project: Path):
    owned = project.parent / 'owned-checkout'
    _git(project, 'worktree', 'add', str(owned), '-b', 'owned-work')
    _git(project, 'checkout', '--orphan', 'primary-unborn')
    result = _cli(owned, 'agent', 'mission', 'create', 'owned-valid',
                  '--owned-checkout', str(owned), '--topology', 'coord', '--json')
    assert result.returncode == 0, _unwrapped(result)
    assert len(_missions(owned)) == 1
