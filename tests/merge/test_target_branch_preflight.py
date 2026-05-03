"""WP06 target branch synchronization preflight tests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

import specify_cli.merge.preflight as preflight_mod
from specify_cli.cli.commands.merge import (
    _enforce_target_branch_sync_preflight,
    _target_branch_sync_payload,
)
from specify_cli.merge.preflight import (
    focused_pr_branch_name,
    inspect_target_branch_sync,
    refresh_target_branch_tracking_ref,
    target_branch_sync_remediation,
)

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(repo: Path, path: str, content: str, message: str) -> None:
    file_path = repo / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    _run(["git", "add", path], cwd=repo)
    _run(["git", "-c", "commit.gpgsign=false", "commit", "-m", message], cwd=repo)


def _configured_clone(remote: Path, target: Path) -> Path:
    _run(["git", "clone", "-b", "main", str(remote), str(target)])
    _run(["git", "config", "user.email", "test@example.com"], cwd=target)
    _run(["git", "config", "user.name", "Test User"], cwd=target)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=target)
    return target


@pytest.fixture()
def synced_repo(tmp_path: Path) -> tuple[Path, Path]:
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    repo = tmp_path / "repo"
    _run(["git", "init", "--bare", str(origin)])
    _run(["git", "init", "-b", "main", str(seed)])
    _run(["git", "config", "user.email", "test@example.com"], cwd=seed)
    _run(["git", "config", "user.name", "Test User"], cwd=seed)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=seed)
    _commit(seed, "README.md", "initial\n", "initial")
    _run(["git", "remote", "add", "origin", str(origin)], cwd=seed)
    _run(["git", "push", "-u", "origin", "main"], cwd=seed)
    _run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=origin)
    return _configured_clone(origin, repo), origin


def test_target_branch_preflight_detects_local_main_ahead(
    synced_repo: tuple[Path, Path],
) -> None:
    repo, _origin = synced_repo
    _commit(repo, "ahead.txt", "local only\n", "local ahead")

    status = inspect_target_branch_sync(repo, "main")

    assert status.state == "ahead"
    assert status.ahead_count == 1
    assert status.behind_count == 0
    assert status.tracking_branch == "origin/main"


def test_target_branch_preflight_detects_local_main_behind(
    synced_repo: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    repo, origin = synced_repo
    updater = _configured_clone(origin, tmp_path / "updater")
    _commit(updater, "remote.txt", "remote only\n", "remote ahead")
    _run(["git", "push", "origin", "main"], cwd=updater)
    _run(["git", "fetch", "origin", "main"], cwd=repo)

    status = inspect_target_branch_sync(repo, "main")

    assert status.state == "behind"
    assert status.ahead_count == 0
    assert status.behind_count == 1


def test_target_branch_preflight_uses_origin_branch_when_upstream_unset(
    synced_repo: tuple[Path, Path],
) -> None:
    repo, _origin = synced_repo
    _run(["git", "branch", "--unset-upstream", "main"], cwd=repo)

    status = inspect_target_branch_sync(repo, "main")

    assert status.state == "in_sync"
    assert status.tracking_branch == "origin/main"


def test_target_branch_preflight_reports_missing_local_branch(
    synced_repo: tuple[Path, Path],
) -> None:
    repo, _origin = synced_repo

    status = inspect_target_branch_sync(repo, "missing-main")

    assert status.state == "missing_local_branch"
    assert status.tracking_branch is None


def test_target_branch_preflight_reports_no_tracking_branch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _run(["git", "init", "-b", "main", str(repo)])
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test User"], cwd=repo)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=repo)
    _commit(repo, "README.md", "initial\n", "initial")

    status = inspect_target_branch_sync(repo, "main")

    assert status.state == "no_tracking_branch"
    assert status.tracking_branch is None


def test_target_branch_preflight_reports_no_tracking_when_rev_list_fails(
    synced_repo: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _origin = synced_repo
    original_git = preflight_mod._git

    def fake_git(_repo_root: Path, args: list[str]) -> SimpleNamespace:
        if args[:2] == ["rev-list", "--left-right"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="bad revision")
        return original_git(_repo_root, args)

    monkeypatch.setattr(preflight_mod, "_git", fake_git)

    status = inspect_target_branch_sync(repo, "main")

    assert status.state == "no_tracking_branch"
    assert status.tracking_branch == "origin/main"


def test_target_branch_preflight_detects_local_main_diverged(
    synced_repo: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    repo, origin = synced_repo
    updater = _configured_clone(origin, tmp_path / "updater")
    _commit(updater, "remote.txt", "remote only\n", "remote ahead")
    _run(["git", "push", "origin", "main"], cwd=updater)
    _run(["git", "fetch", "origin", "main"], cwd=repo)
    _commit(repo, "local.txt", "local only\n", "local ahead")

    status = inspect_target_branch_sync(repo, "main")

    assert status.state == "diverged"
    assert status.ahead_count == 1
    assert status.behind_count == 1


def test_merge_preflight_blocks_unsafe_target_with_non_destructive_guidance(
    synced_repo: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _origin = synced_repo
    _commit(repo, "ahead.txt", "local only\n", "local ahead")
    status = inspect_target_branch_sync(repo, "main")

    with pytest.raises(typer.Exit) as exc_info:
        _enforce_target_branch_sync_preflight(
            repo,
            target_branch="main",
            mission_slug="release-320-workflow-reliability-01KQKV85",
            mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
        )

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    assert "diagnostic_code: TARGET_BRANCH_NOT_SYNCHRONIZED" in output
    assert "branch_or_work_package: main" in output
    assert "violated_invariant: local_target_branch_must_match_tracking_branch" in output
    remediation = target_branch_sync_remediation(
        status,
        mission_slug="release-320-workflow-reliability-01KQKV85",
        mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
    )
    assert any("git fetch origin main" in line for line in remediation)
    assert any("git log --oneline --left-right" in line for line in remediation)
    assert any("git switch -c kitty/pr/release-320-workflow-reliability-01KQKV85-to-main" in line for line in remediation)
    assert all("reset" not in line.lower() or "do not use" in line.lower() for line in remediation)
    assert focused_pr_branch_name("release-320-workflow-reliability-01KQKV85", "main") in "\n".join(remediation)

    payload = _target_branch_sync_payload(
        status,
        mission_slug="release-320-workflow-reliability-01KQKV85",
        mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
    )
    assert payload["diagnostic_code"] == "TARGET_BRANCH_NOT_SYNCHRONIZED"
    assert payload["branch_or_work_package"] == "main"
    assert payload["violated_invariant"] == "local_target_branch_must_match_tracking_branch"
    assert payload["remediation"] == remediation


def test_merge_preflight_fetches_before_detecting_remote_main_behind(
    synced_repo: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    repo, origin = synced_repo
    updater = _configured_clone(origin, tmp_path / "updater")
    _commit(updater, "remote.txt", "remote only\n", "remote ahead")
    _run(["git", "push", "origin", "main"], cwd=updater)

    stale_status = inspect_target_branch_sync(repo, "main")
    assert stale_status.state == "in_sync"

    with pytest.raises(typer.Exit) as exc_info:
        _enforce_target_branch_sync_preflight(
            repo,
            target_branch="main",
            mission_slug="release-320-workflow-reliability-01KQKV85",
            mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
        )

    assert exc_info.value.exit_code == 1
    refreshed_status = inspect_target_branch_sync(repo, "main")
    assert refreshed_status.state == "behind"
    assert refreshed_status.behind_count == 1


def test_refresh_target_branch_tracking_ref_allows_repo_without_origin(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _run(["git", "init", "-b", "main", str(repo)])

    status = refresh_target_branch_tracking_ref(repo, "main")

    assert status.attempted is False
    assert status.success is True
    assert status.remote_name == "origin"


def test_merge_preflight_reports_refresh_failure_as_json(
    synced_repo: tuple[Path, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _origin = synced_repo
    missing_remote = tmp_path / "missing.git"
    _run(["git", "remote", "set-url", "origin", str(missing_remote)], cwd=repo)

    with pytest.raises(typer.Exit) as exc_info:
        _enforce_target_branch_sync_preflight(
            repo,
            target_branch="main",
            mission_slug="release-320-workflow-reliability-01KQKV85",
            mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
            json_output=True,
        )

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    assert '"diagnostic_code": "TARGET_BRANCH_REFRESH_FAILED"' in output
    assert '"remote_name": "origin"' in output
    assert "git fetch origin main" in output
