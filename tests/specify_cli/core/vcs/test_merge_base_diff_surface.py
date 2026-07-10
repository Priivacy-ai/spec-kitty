"""Direct tests for the canonical merge-base/diff surface.

Covers ``git_merge_base``, ``git_diff_names``, and ``merge_base_changed_files``
in ``specify_cli.core.vcs.git`` (mission merge-base-diff-ssot-01KX44SD).

Prefers a real temp git repo for behaviour; mocks subprocess only for the
failure-exit cases that are hard to stage with a real repo (a non-zero exit
from ``git merge-base``/``git diff`` themselves).
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.core.vcs.git import (
    git_diff_names,
    git_diff_names_checked,
    git_merge_base,
    merge_base_changed_files,
)

pytestmark = pytest.mark.git_repo


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=str(cwd), capture_output=True, check=True)


def _commit(repo, filename, content, message):
    (repo / filename).parent.mkdir(parents=True, exist_ok=True)
    (repo / filename).write_text(content)
    _run(["git", "add", filename], repo)
    _run(["git", "commit", "-m", message], repo)


def _make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", str(repo)], tmp_path)
    _run(["git", "config", "user.email", "test@test.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    _commit(repo, "README.md", "init\n", "init")
    _run(["git", "branch", "-M", "main"], repo)
    return repo


class TestGitMergeBase:
    def test_normal_merge_base(self, tmp_path):
        repo = _make_repo(tmp_path)
        _run(["git", "branch", "side"], repo)
        _commit(repo, "src/a.py", "main change\n", "main change")

        mb = git_merge_base(repo, "HEAD", "side")

        assert mb is not None
        assert len(mb) == 40  # full SHA

    def test_non_zero_exit_returns_none(self, tmp_path):
        repo = _make_repo(tmp_path)

        mb = git_merge_base(repo, "HEAD", "does-not-exist")

        assert mb is None

    def test_empty_stdout_returns_none(self, tmp_path):
        repo = _make_repo(tmp_path)
        fake_result = MagicMock(returncode=0, stdout="  \n")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake_result):
            mb = git_merge_base(repo, "HEAD", "HEAD")

        assert mb is None

    def test_never_raises_on_git_failure(self, tmp_path):
        repo = _make_repo(tmp_path)
        fake_result = MagicMock(returncode=128, stdout="")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake_result):
            mb = git_merge_base(repo, "HEAD", "unrelated")

        assert mb is None


class TestGitDiffNames:
    def test_normal_diff_returns_n_files(self, tmp_path):
        repo = _make_repo(tmp_path)
        base = git_merge_base(repo, "HEAD", "HEAD")
        _commit(repo, "src/a.py", "one\n", "a")
        _commit(repo, "src/b.py", "two\n", "b")

        names = git_diff_names(repo, base, "HEAD")

        assert set(names) == {"src/a.py", "src/b.py"}

    def test_non_zero_exit_returns_empty_tuple(self, tmp_path):
        repo = _make_repo(tmp_path)
        fake_result = MagicMock(returncode=1, stdout="")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake_result):
            names = git_diff_names(repo, "HEAD", "HEAD")

        assert names == ()

    def test_pathspec_restricts_output(self, tmp_path):
        repo = _make_repo(tmp_path)
        base = git_merge_base(repo, "HEAD", "HEAD")
        _commit(repo, "kitty-specs/spec.md", "spec\n", "spec change")
        _commit(repo, "src/other.py", "other\n", "other change")

        names = git_diff_names(repo, base, "HEAD", pathspec="kitty-specs/")

        assert names == ("kitty-specs/spec.md",)

    def test_diff_filter_is_passed_through(self, tmp_path):
        repo = _make_repo(tmp_path)
        base = "abc123"
        fake_result = MagicMock(returncode=0, stdout="")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake_result) as mock_run:
            git_diff_names(repo, base, "HEAD", diff_filter="AMR")

        called_cmd = mock_run.call_args.args[0]
        assert "--diff-filter=AMR" in called_cmd

    def test_non_head_branch_target_fences_f1(self, tmp_path):
        """F1 fence: git_diff_names must diff an arbitrary ``head``, not HEAD.

        Builds a side branch with commits HEAD does NOT have, then diffs
        ``mb`` against that side branch (not HEAD). If a future change
        silently swapped this call to the HEAD-relative convenience, this
        test would fail red because HEAD has no changes relative to the
        merge-base.
        """
        repo = _make_repo(tmp_path)
        _run(["git", "branch", "side"], repo)
        _run(["git", "checkout", "side"], repo)
        _commit(repo, "src/side_only.py", "side\n", "side change")
        _run(["git", "checkout", "main"], repo)

        mb = git_merge_base(repo, "HEAD", "side")
        assert mb is not None

        # HEAD has no changes relative to the merge-base (side moved, not main).
        assert git_diff_names(repo, mb, "HEAD") == ()

        # Diffing against the side branch (head != HEAD) reports its file.
        names = git_diff_names(repo, mb, "side")
        assert names == ("src/side_only.py",)

    def test_two_arg_form_equivalent_to_range_form(self, tmp_path):
        """Documents the silent <mb>..HEAD -> two-arg rewrite three sites undergo."""
        repo = _make_repo(tmp_path)
        _commit(repo, "src/a.py", "one\n", "a")
        _commit(repo, "src/b.py", "two\n", "b")
        mb = git_merge_base(repo, "HEAD", "HEAD~2")
        assert mb is not None

        two_arg = git_diff_names(repo, mb, "HEAD")

        raw = subprocess.run(
            ["git", "diff", "--name-only", f"{mb}..HEAD"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=True,
        )
        raw_names = tuple(line.strip() for line in raw.stdout.splitlines() if line.strip())

        assert set(two_arg) == set(raw_names)


class TestMergeBaseChangedFiles:
    def test_no_merge_base_returns_empty(self, tmp_path):
        repo = _make_repo(tmp_path)

        result = merge_base_changed_files(repo, "does-not-exist")

        assert result == ()

    def test_diff_failure_returns_empty(self, tmp_path):
        repo = _make_repo(tmp_path)

        def fake_run(cmd, **_kwargs):
            if "merge-base" in cmd:
                return MagicMock(returncode=0, stdout="deadbeef\n")
            return MagicMock(returncode=1, stdout="")

        with patch("specify_cli.core.vcs.git.subprocess.run", side_effect=fake_run):
            result = merge_base_changed_files(repo, "HEAD")

        assert result == ()

    def test_composes_merge_base_and_diff(self, tmp_path):
        repo = _make_repo(tmp_path)
        _run(["git", "branch", "base-branch"], repo)
        _commit(repo, "src/a.py", "one\n", "a")

        result = merge_base_changed_files(repo, "base-branch")

        assert result == ("src/a.py",)

    def test_pathspec_and_diff_filter_thread_through(self, tmp_path):
        repo = _make_repo(tmp_path)
        _run(["git", "branch", "base-branch"], repo)
        _commit(repo, ".github/workflows/ci.yml", "ci\n", "ci change")
        _commit(repo, "src/other.py", "other\n", "other change")

        result = merge_base_changed_files(
            repo, "base-branch", pathspec=".github/workflows", diff_filter="AMR",
        )

        assert result == (".github/workflows/ci.yml",)


class TestGitDiffNamesChecked:
    """Fail-distinguishing variant: ``None`` on git failure vs ``()`` on empty diff."""

    def test_non_zero_exit_returns_none(self, tmp_path):
        fake = MagicMock(returncode=129, stdout="")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake):
            assert git_diff_names_checked(tmp_path, "base", "head") is None

    def test_empty_diff_returns_empty_tuple_not_none(self, tmp_path):
        # The load-bearing distinction: a genuinely-empty diff is () (success),
        # NOT None (failure). Fail-closed callers rely on this.
        fake = MagicMock(returncode=0, stdout="\n")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake):
            assert git_diff_names_checked(tmp_path, "base", "head") == ()

    def test_success_returns_paths(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="a.py\nb.py\n")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake):
            assert git_diff_names_checked(tmp_path, "base", "head") == ("a.py", "b.py")

    def test_pathspec_and_diff_filter_passthrough(self, tmp_path):
        fake = MagicMock(returncode=0, stdout="")
        with patch(
            "specify_cli.core.vcs.git.subprocess.run", return_value=fake
        ) as mock_run:
            git_diff_names_checked(
                tmp_path, "base", "head", pathspec="x/", diff_filter="AMR"
            )
        cmd = mock_run.call_args.args[0]
        assert "--diff-filter=AMR" in cmd
        assert cmd[-2:] == ["--", "x/"]

    def test_git_diff_names_maps_none_to_empty_tuple(self, tmp_path):
        # The fail-open wrapper collapses the checked variant's None to ().
        fake = MagicMock(returncode=1, stdout="")
        with patch("specify_cli.core.vcs.git.subprocess.run", return_value=fake):
            assert git_diff_names_checked(tmp_path, "base", "head") is None
            assert git_diff_names(tmp_path, "base", "head") == ()
