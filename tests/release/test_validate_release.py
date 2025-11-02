from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "release" / "validate_release.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
