from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "release" / "validate_release.py"

pytestmark = pytest.mark.git_repo


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def run_validator(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(VALIDATOR),
        "--pyproject",
        str(tmp_path / "pyproject.toml"),
        "--changelog",
        str(tmp_path / "CHANGELOG.md"),
        *args,
    ]
    return subprocess.run(
        cmd,
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )


def init_repo(tmp_path: Path) -> None:
    run(["git", "init"], tmp_path)
    run(["git", "config", "user.email", "maintainer@example.com"], tmp_path)
    run(["git", "config", "user.name", "Spec Kitty"], tmp_path)


def write_release_files(tmp_path: Path, version: str, changelog_body: str) -> None:
    (tmp_path / "pyproject.toml").write_text(
        dedent(
            f"""
            [project]
            name = "spec-kitty-cli"
            version = "{version}"
            description = "Spec Kitty CLI"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(changelog_body, encoding="utf-8")
    # FR-601/FR-602: keep .kittify/metadata.yaml in sync so validate_release.py passes
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(exist_ok=True)
    (kittify_dir / "metadata.yaml").write_text(
        f"spec_kitty:\n  version: {version}\n",
        encoding="utf-8",
    )


def stage_and_commit(tmp_path: Path, message: str) -> None:
    run(["git", "add", "."], tmp_path)
    run(["git", "commit", "-m", message], tmp_path)


def tag(tmp_path: Path, tag_name: str) -> None:
    run(["git", "tag", tag_name], tmp_path)


def changelog_for_versions(*versions: tuple[str, str]) -> str:
    sections = []
    for version, body in versions:
        sections.append(f"## {version}\n{body}\n")
    return "\n".join(sections)


def test_branch_mode_succeeds_with_version_bump(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "0.2.3",
        changelog_for_versions(("0.2.3", "- Initial release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap project")
    tag(tmp_path, "v0.2.3")

    write_release_files(
        tmp_path,
        "0.2.4",
        changelog_for_versions(
            ("0.2.4", "- Add automation"),
            ("0.2.3", "- Initial release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 0.2.4")

    result = run_validator(tmp_path, "--mode", "branch")

    assert result.returncode == 0, result.stderr
    assert "All required checks passed." in result.stdout


def test_branch_mode_accepts_prerelease_version_bump(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "3.0.3",
        changelog_for_versions(("3.0.3", "- Stable release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap 3.0.3")
    tag(tmp_path, "v3.0.3")

    write_release_files(
        tmp_path,
        "3.1.0a0",
        changelog_for_versions(
            ("3.1.0a0", "- Testing prerelease"),
            ("3.0.3", "- Stable release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 3.1.0a0")

    result = run_validator(tmp_path, "--mode", "branch")

    assert result.returncode == 0, result.stderr
    assert "All required checks passed." in result.stdout


def test_branch_mode_fails_without_changelog_entry(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "0.2.3",
        changelog_for_versions(("0.2.3", "- Initial release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap project")
    tag(tmp_path, "v0.2.3")

    write_release_files(
        tmp_path,
        "0.2.4",
        changelog_for_versions(("0.2.3", "- Initial release")),
    )
    stage_and_commit(tmp_path, "chore: prep 0.2.4 without changelog entry")

    result = run_validator(tmp_path, "--mode", "branch")

    assert result.returncode == 1
    assert "CHANGELOG.md lacks a populated section for 0.2.4" in result.stderr


def test_tag_mode_validates_tag_alignment(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "0.2.3",
        changelog_for_versions(("0.2.3", "- Initial release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap project")
    tag(tmp_path, "v0.2.3")

    write_release_files(
        tmp_path,
        "0.2.4",
        changelog_for_versions(
            ("0.2.4", "- Add automation"),
            ("0.2.3", "- Initial release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 0.2.4")
    tag(tmp_path, "v0.2.4")

    env = os.environ.copy()
    env.pop("GITHUB_REF", None)
    env.pop("GITHUB_REF_NAME", None)

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--mode",
            "tag",
            "--tag",
            "v0.2.4",
            "--pyproject",
            str(tmp_path / "pyproject.toml"),
            "--changelog",
            str(tmp_path / "CHANGELOG.md"),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Tag: v0.2.4" in result.stdout


def test_tag_mode_fails_on_regression(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "0.2.3",
        changelog_for_versions(("0.2.3", "- Initial release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap project")
    tag(tmp_path, "v0.2.3")

    write_release_files(
        tmp_path,
        "0.2.2",
        changelog_for_versions(
            ("0.2.2", "- Regression build"),
            ("0.2.3", "- Initial release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: regress version")

    result = run_validator(tmp_path, "--mode", "tag", "--tag", "v0.2.2")

    assert result.returncode == 1
    assert "does not advance beyond latest tag v0.2.3" in result.stderr


def test_tag_mode_accepts_prerelease_versions(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "0.2.3",
        changelog_for_versions(("0.2.3", "- Initial release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap project")
    tag(tmp_path, "v0.2.3")

    write_release_files(
        tmp_path,
        "0.3.0a0",
        changelog_for_versions(
            ("0.3.0a0", "- Testing prerelease"),
            ("0.2.3", "- Initial release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 0.3.0a0")

    result = run_validator(tmp_path, "--mode", "tag", "--tag", "v0.3.0a0")

    assert result.returncode == 0, result.stderr
    assert "Tag: v0.3.0a0" in result.stdout


def test_branch_mode_honors_tag_pattern_scope(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "2.0.0",
        changelog_for_versions(("2.0.0", "- Initial 2.x release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap 2.0.0")
    tag(tmp_path, "v2.0.0")

    write_release_files(
        tmp_path,
        "3.0.0",
        changelog_for_versions(
            ("3.0.0", "- Different release line"),
            ("2.0.0", "- Initial 2.x release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: create unrelated major line")
    tag(tmp_path, "v3.0.0")

    write_release_files(
        tmp_path,
        "2.0.1",
        changelog_for_versions(
            ("2.0.1", "- Patch release"),
            ("3.0.0", "- Different release line"),
            ("2.0.0", "- Initial 2.x release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 2.0.1")

    result_scoped = run_validator(tmp_path, "--mode", "branch", "--tag-pattern", "v2.*.*")
    assert result_scoped.returncode == 0, result_scoped.stderr

    result_unscoped = run_validator(tmp_path, "--mode", "branch")
    assert result_unscoped.returncode == 1
    assert "does not advance beyond latest tag v3.0.0" in result_unscoped.stderr


def test_tag_mode_rejects_prerelease_regression(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "1.0.0",
        changelog_for_versions(("1.0.0", "- Initial stable release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap 1.0.0")
    tag(tmp_path, "v1.0.0")

    write_release_files(
        tmp_path,
        "1.0.1a1",
        changelog_for_versions(
            ("1.0.1a1", "- Later prerelease"),
            ("1.0.0", "- Initial stable release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 1.0.1a1")
    tag(tmp_path, "v1.0.1a1")

    write_release_files(
        tmp_path,
        "1.0.1a0",
        changelog_for_versions(
            ("1.0.1a0", "- Earlier prerelease"),
            ("1.0.1a1", "- Later prerelease"),
            ("1.0.0", "- Initial stable release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: regress to 1.0.1a0")

    result = run_validator(tmp_path, "--mode", "tag", "--tag", "v1.0.1a0")

    assert result.returncode == 1
    assert "does not advance beyond latest tag v1.0.1a1" in result.stderr


def test_branch_mode_accepts_final_release_after_prerelease_tag(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "1.0.0",
        changelog_for_versions(("1.0.0", "- Initial stable release")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap 1.0.0")
    tag(tmp_path, "v1.0.0")

    write_release_files(
        tmp_path,
        "1.0.1a1",
        changelog_for_versions(
            ("1.0.1a1", "- Release candidate"),
            ("1.0.0", "- Initial stable release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 1.0.1a1")
    tag(tmp_path, "v1.0.1a1")

    write_release_files(
        tmp_path,
        "1.0.1",
        changelog_for_versions(
            ("1.0.1", "- Stable patch release"),
            ("1.0.1a1", "- Release candidate"),
            ("1.0.0", "- Initial stable release"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 1.0.1")

    result = run_validator(tmp_path, "--mode", "branch", "--tag-pattern", "v*.*.*")

    assert result.returncode == 0, result.stderr
    assert "All required checks passed." in result.stdout


def test_stable_patch_ignores_later_minor_prerelease_tag(tmp_path: Path) -> None:
    init_repo(tmp_path)
    write_release_files(
        tmp_path,
        "3.1.6",
        changelog_for_versions(("3.1.6", "- Stable hotfix")),
    )
    stage_and_commit(tmp_path, "chore: bootstrap 3.1.6")
    tag(tmp_path, "v3.1.6")

    write_release_files(
        tmp_path,
        "3.2.0a4",
        changelog_for_versions(
            ("3.2.0a4", "- Alpha train"),
            ("3.1.6", "- Stable hotfix"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 3.2.0a4")
    tag(tmp_path, "v3.2.0a4")

    write_release_files(
        tmp_path,
        "3.1.7",
        changelog_for_versions(
            ("3.1.7", "- Stable patch after alpha"),
            ("3.2.0a4", "- Alpha train"),
            ("3.1.6", "- Stable hotfix"),
        ),
    )
    stage_and_commit(tmp_path, "chore: prep 3.1.7")

    branch_result = run_validator(tmp_path, "--mode", "branch", "--tag-pattern", "v*.*.*")
    assert branch_result.returncode == 0, branch_result.stderr

    tag_result = run_validator(tmp_path, "--mode", "tag", "--tag", "v3.1.7", "--tag-pattern", "v*.*.*")
    assert tag_result.returncode == 0, tag_result.stderr
