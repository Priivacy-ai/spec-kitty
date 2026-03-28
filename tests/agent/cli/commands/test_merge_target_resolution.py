"""Command-level regression tests for merge target resolution."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.core.context_validation import ExecutionContext


runner = CliRunner()


def _extract_json(output: str) -> dict[str, object]:
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise AssertionError(f"No JSON payload found in output:\n{output}")


def _write_meta_json(feature_dir: Path, target_branch: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "feature_number": "049",
                "slug": feature_dir.name,
                "target_branch": target_branch,
            }
        ),
        encoding="utf-8",
    )


def _force_main_repo(monkeypatch, repo_root: Path) -> None:
    monkeypatch.setattr(
        "specify_cli.core.context_validation.get_current_context",
        lambda: SimpleNamespace(
            location=ExecutionContext.MAIN_REPO,
            worktree_name=None,
            repo_root=repo_root,
        ),
    )


def _patch_merge_environment(
    monkeypatch,
    repo_root: Path,
    *,
    current_branch: str,
    existing_branches: set[str],
) -> None:
    _force_main_repo(monkeypatch, repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.find_repo_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge._enforce_git_preflight",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.detect_worktree_structure",
        lambda *_args, **_kwargs: "legacy",
    )
    monkeypatch.setattr(
        "specify_cli.core.feature_detection._get_main_repo_root",
        lambda _repo_root: repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.core.git_ops.resolve_primary_branch",
        lambda _repo_root: "main",
    )

    def fake_run_command(cmd, capture=False, check_return=True, cwd=None, **kwargs):
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, current_branch, ""
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            ref = cmd[3]
            branch = ref.removeprefix("refs/heads/").removeprefix("refs/remotes/origin/")
            if branch in existing_branches:
                return 0, branch, ""
            return 1, "", "fatal: not a valid object name"
        return 0, "", ""

    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.run_command",
        fake_run_command,
    )


def test_merge_without_feature_on_feature_branch_reads_meta_target(monkeypatch, tmp_path: Path) -> None:
    slug = "049-fix-merge-target-resolution"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    _write_meta_json(repo_root / "kitty-specs" / slug, "2.x")
    _patch_merge_environment(
        monkeypatch,
        repo_root,
        current_branch=slug,
        existing_branches={"2.x"},
    )

    result = runner.invoke(cli_app, ["merge", "--dry-run", "--json"])

    assert result.exit_code == 0
    payload = _extract_json(result.stdout)
    assert payload["feature_slug"] == slug
    assert payload["target_branch"] == "2.x"


def test_merge_without_feature_on_wp_branch_validates_inferred_target(monkeypatch, tmp_path: Path) -> None:
    slug = "049-fix-merge-target-resolution"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    _write_meta_json(repo_root / "kitty-specs" / slug, "does-not-exist")
    _patch_merge_environment(
        monkeypatch,
        repo_root,
        current_branch=f"{slug}-WP01",
        existing_branches=set(),
    )

    result = runner.invoke(cli_app, ["merge", "--dry-run", "--json"])

    assert result.exit_code == 1
    payload = _extract_json(result.stdout)
    assert payload["error"] == (
        "Target branch 'does-not-exist' (from meta.json) does not exist locally "
        f"or on origin. Check kitty-specs/{slug}/meta.json."
    )


def test_explicit_target_overrides_meta_json(monkeypatch, tmp_path: Path) -> None:
    slug = "049-fix-merge-target-resolution"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    _write_meta_json(repo_root / "kitty-specs" / slug, "2.x")
    _patch_merge_environment(
        monkeypatch,
        repo_root,
        current_branch=slug,
        existing_branches={"main"},
    )

    result = runner.invoke(
        cli_app,
        ["merge", "--dry-run", "--json", "--target", "main"],
    )

    assert result.exit_code == 0
    payload = _extract_json(result.stdout)
    assert payload["target_branch"] == "main"


def test_explicit_feature_flag_reads_meta_target(monkeypatch, tmp_path: Path) -> None:
    slug = "049-fix-merge-target-resolution"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    _write_meta_json(repo_root / "kitty-specs" / slug, "2.x")
    _patch_merge_environment(
        monkeypatch,
        repo_root,
        current_branch="main",
        existing_branches={"2.x", "main"},
    )

    result = runner.invoke(
        cli_app,
        ["merge", "--dry-run", "--json", "--feature", slug],
    )

    assert result.exit_code == 0
    payload = _extract_json(result.stdout)
    assert payload["feature_slug"] == slug
    assert payload["target_branch"] == "2.x"


def test_explicit_feature_flag_missing_meta_falls_back_to_primary(monkeypatch, tmp_path: Path) -> None:
    slug = "049-fix-merge-target-resolution"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    # No meta.json written — feature dir does not exist
    _patch_merge_environment(
        monkeypatch,
        repo_root,
        current_branch="main",
        existing_branches={"main"},
    )

    result = runner.invoke(
        cli_app,
        ["merge", "--dry-run", "--json", "--feature", slug],
    )

    assert result.exit_code == 0
    payload = _extract_json(result.stdout)
    assert payload["feature_slug"] == slug
    assert payload["target_branch"] == "main"


def test_no_feature_no_feature_branch_uses_primary_branch(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    _patch_merge_environment(
        monkeypatch,
        repo_root,
        current_branch="some-unrelated-branch",
        existing_branches={"main"},
    )

    result = runner.invoke(cli_app, ["merge", "--dry-run", "--json"])

    assert result.exit_code == 0
    payload = _extract_json(result.stdout)
    assert payload["target_branch"] == "main"


def test_feature_explicitly_targeting_main(monkeypatch, tmp_path: Path) -> None:
    slug = "049-fix-merge-target-resolution"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    _write_meta_json(repo_root / "kitty-specs" / slug, "main")
    _patch_merge_environment(
        monkeypatch,
        repo_root,
        current_branch=slug,
        existing_branches={"main"},
    )

    result = runner.invoke(cli_app, ["merge", "--dry-run", "--json"])

    assert result.exit_code == 0
    payload = _extract_json(result.stdout)
    assert payload["feature_slug"] == slug
    assert payload["target_branch"] == "main"


def test_merge_template_has_no_agent_feature_merge_references() -> None:
    """WP10: command-templates directories were deleted; shims replace them.

    Verifies no command-templates/merge.md files exist in the source tree.
    """
    src_root = Path(__file__).resolve().parents[4] / "src"
    merge_templates = list(src_root.glob("**/command-templates/merge.md"))

    # WP10: All command-templates were deleted; shim generation replaces them
    assert len(merge_templates) == 0, (
        f"command-templates/merge.md still present (WP10 deletion incomplete): {merge_templates}"
    )
