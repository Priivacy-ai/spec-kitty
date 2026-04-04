#!/usr/bin/env python3
"""Release readiness validator for Spec Kitty automation.

The script validates three core conditions before allowing a release or
testing cut:

1. The version declared in pyproject.toml is well-formed.
2. CHANGELOG.md contains a populated section for the target version.
3. Version progression is monotonic relative to existing git tags and, in tag
   mode, matches the release tag that triggered the workflow.

Both validation modes accept stable versions (``X.Y.Z``) and prerelease
versions such as ``X.Y.ZaN``. Tagged prereleases publish through the same
release workflow, but GitHub marks them as prereleases and installers must opt
into them explicitly.

It is intentionally dependency-light so it can run both locally and in CI
without additional bootstrapping beyond Python 3.11.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Sequence

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for older interpreters
    import tomli as tomllib  # type: ignore


RELEASE_VERSION_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:(?P<stage>a|b|rc|alpha|beta)(?P<stage_num>\d*))?$",
    re.IGNORECASE,
)
CHANGELOG_HEADING_RE = re.compile(
    r"^##\s*(?:\[\s*)?"
    r"(?P<version>\d+\.\d+\.\d+(?:(?:a|b|rc)\d+|(?:alpha|beta)\d*)?)"
    r"(?:\s*\]|)(?:\s*-.*)?$",
    re.IGNORECASE,
)


@dataclass
class ValidationIssue:
    message: str
    hint: str | None = None

    def format(self) -> str:
        if self.hint:
            return f"{self.message} (Hint: {self.hint})"
        return self.message


@dataclass
class ValidationResult:
    ok: bool
    mode: str
    pyproject_path: Path
    changelog_path: Path
    version: str
    tag: str | None
    issues: list[ValidationIssue] = field(default_factory=list)

    def report(self) -> None:
        header = "Release Validator Summary"
        print(header)
        print("-" * len(header))
        print(f"Mode: {self.mode}")
        print(f"pyproject.toml: {self.pyproject_path}")
        print(f"CHANGELOG.md: {self.changelog_path}")
        print(f"Version: {self.version or 'N/A'}")
        print(f"Tag: {self.tag or 'N/A'}")
        if not self.ok:
            print("\nIssues detected:")
            for idx, issue in enumerate(self.issues, start=1):
                print(f"  {idx}. {issue.format()}")
        else:
            print("\nAll required checks passed.")


class ReleaseValidatorError(Exception):
    """Base exception for validator failures."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate release readiness for Spec Kitty release automation"
    )
    parser.add_argument(
        "--mode",
        choices=("branch", "tag"),
        default="branch",
        help="Validation mode. 'branch' expects a version bump without a tag. "
        "'tag' enforces tag-version parity and monotonic progression for stable "
        "or prerelease publish tags.",
    )
    parser.add_argument(
        "--tag",
        help="Explicit tag (e.g., v1.2.3 or v1.3.0a0). Defaults to the detected "
        "GITHUB_REF or GITHUB_REF_NAME in tag mode.",
    )
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml (default: %(default)s)",
    )
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.md",
        help="Path to changelog file (default: %(default)s)",
    )
    parser.add_argument(
        "--tag-pattern",
        default="v*.*.*",
        help="Git tag glob pattern used for version progression checks "
        "(default: %(default)s).",
    )
    parser.add_argument(
        "--fail-on-missing-tag",
        action="store_true",
        help="Treat missing tag detection as a hard failure (defaults to failure in tag mode).",
    )
    return parser.parse_args(argv)


def _normalize_stage(stage: str | None) -> str | None:
    if stage is None:
        return None
    lowered = stage.lower()
    if lowered == "alpha":
        return "a"
    if lowered == "beta":
        return "b"
    return lowered


def is_prerelease_version(value: str) -> bool:
    match = RELEASE_VERSION_RE.match(value)
    return bool(match and _normalize_stage(match.group("stage")) is not None)


def load_pyproject_version(path: Path) -> str:
    if not path.exists():
        raise ReleaseValidatorError(
            f"pyproject.toml not found at {path} – ensure you run from repository root."
        )
    with path.open("rb") as fp:
        data = tomllib.load(fp)
    try:
        version = data["project"]["version"]
    except KeyError as exc:  # pragma: no cover - defensive; unlikely if file well-formed
        raise ReleaseValidatorError(
            "Unable to locate [project].version in pyproject.toml."
        ) from exc
    if not isinstance(version, str):
        raise ReleaseValidatorError("pyproject version must be a string.")
    if not RELEASE_VERSION_RE.match(version):
        raise ReleaseValidatorError(
            f"Version '{version}' is not a supported release version "
            "(expected X.Y.Z or X.Y.ZaN/X.Y.ZbN/X.Y.ZrcN)."
        )
    return version


def read_changelog(path: Path) -> str:
    if not path.exists():
        raise ReleaseValidatorError(f"CHANGELOG not found at {path}.")
    return path.read_text(encoding="utf-8-sig")


def changelog_has_entry(changelog: str, version: str) -> bool:
    lines = changelog.splitlines()
    capture = False
    content: list[str] = []
    for line in lines:
        heading = CHANGELOG_HEADING_RE.match(line)
        if heading:
            if capture:
                break
            capture = heading.group("version") == version
            continue
        if capture:
            content.append(line.strip())
    if not capture:
        return False
    return any(fragment for fragment in content if fragment)


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ReleaseValidatorError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def find_repo_root(start: Path) -> Path:
    try:
        output = git("rev-parse", "--show-toplevel", cwd=start)
    except ReleaseValidatorError as exc:
        raise ReleaseValidatorError(
            "Unable to locate git repository root. Ensure git is installed and run this script "
            "inside the Spec Kitty repository."
        ) from exc
    return Path(output)


def discover_release_tags(
    repo_root: Path, tag_pattern: str, exclude: str | None = None
) -> list[str]:
    output = git("tag", "--list", tag_pattern, cwd=repo_root)
    tags = [line.strip() for line in output.splitlines() if line.strip()]
    filtered = [
        tag
        for tag in tags
        if tag != exclude
        and tag.startswith("v")
        and RELEASE_VERSION_RE.match(tag.lstrip("v"))
    ]
    filtered.sort(key=lambda tag: parse_release_version(tag.lstrip("v")), reverse=True)
    return filtered


def parse_release_version(value: str) -> tuple[int, int, int, int, int]:
    match = RELEASE_VERSION_RE.match(value)
    if not match:
        raise ReleaseValidatorError(
            f"Value '{value}' is not a valid release version "
            "(expected X.Y.Z or X.Y.ZaN/X.Y.ZbN/X.Y.ZrcN)."
        )

    stage = _normalize_stage(match.group("stage"))
    stage_number = int(match.group("stage_num") or "0")
    stage_rank = {
        "a": 0,
        "b": 1,
        "rc": 2,
        None: 3,
    }[stage]
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        stage_rank,
        stage_number,
    )


def detect_tag_from_env() -> str | None:
    ref_name = os.getenv("GITHUB_REF_NAME")
    if ref_name and ref_name.startswith("v") and RELEASE_VERSION_RE.match(ref_name[1:]):
        return ref_name
    ref = os.getenv("GITHUB_REF")
    if ref and ref.startswith("refs/tags/"):
        candidate = ref.rsplit("/", maxsplit=1)[-1]
        if candidate.startswith("v") and RELEASE_VERSION_RE.match(candidate[1:]):
            return candidate
    return None


def validate_version_progression(
    current_version: str, existing_tags: Sequence[str]
) -> ValidationIssue | None:
    if not existing_tags:
        return None
    current_tuple = parse_release_version(current_version)
    latest_tuple = parse_release_version(existing_tags[0].lstrip("v"))
    if current_tuple <= latest_tuple:
        return ValidationIssue(
            message=f"Version {current_version} does not advance beyond latest tag {existing_tags[0]}.",
            hint="Select a stable or prerelease version greater than previously published releases.",
        )
    return None


def ensure_tag_matches_version(version: str, tag: str | None) -> ValidationIssue | None:
    expected = f"v{version}"
    if not tag:
        return ValidationIssue(
            message="No release tag detected.",
            hint="Pass --tag, set GITHUB_REF_NAME, or run in branch mode.",
        )
    if tag != expected:
        return ValidationIssue(
            message=f"Tag {tag} does not match project version {version}.",
            hint=f"Retag the commit as {expected} or bump the version in pyproject.toml.",
        )
    return None


def run_validation(args: argparse.Namespace) -> ValidationResult:
    pyproject_path = Path(args.pyproject).resolve()
    changelog_path = Path(args.changelog).resolve()
    version = ""
    tag: str | None = None
    issues: list[ValidationIssue] = []

    try:
        version = load_pyproject_version(pyproject_path)
        changelog_text = read_changelog(changelog_path)
    except ReleaseValidatorError as exc:
        issues.append(ValidationIssue(str(exc)))
        return ValidationResult(
            ok=False,
            mode=args.mode,
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            version=version,
            tag=tag,
            issues=issues,
        )

    repo_root = find_repo_root(pyproject_path.parent)

    if not changelog_has_entry(changelog_text, version):
        issues.append(
            ValidationIssue(
                message=f"CHANGELOG.md lacks a populated section for {version}.",
                hint="Add release notes under a '## {version}' heading.",
            )
        )

    if args.mode == "tag":
        tag = args.tag or detect_tag_from_env()
        if not tag:
            issues.append(
                ValidationIssue(
                    message="No tag supplied and none detected from environment.",
                    hint="Use --tag vX.Y.Z or vX.Y.ZaN, or set GITHUB_REF_NAME when running in CI.",
                )
            )
        else:
            mismatch = ensure_tag_matches_version(version, tag)
            if mismatch:
                issues.append(mismatch)

        existing_tags = discover_release_tags(
            repo_root, tag_pattern=args.tag_pattern, exclude=tag
        )
        progression_issue = validate_version_progression(version, existing_tags)
        if progression_issue:
            issues.append(progression_issue)
    else:
        existing_tags = discover_release_tags(repo_root, tag_pattern=args.tag_pattern)
        progression_issue = validate_version_progression(version, existing_tags)
        if progression_issue:
            issues.append(progression_issue)

    ok = len(issues) == 0
    return ValidationResult(
        ok=ok,
        mode=args.mode,
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
        version=version,
        tag=tag,
        issues=issues,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_validation(args)
    result.report()
    if result.ok:
        return 0
    for issue in result.issues:
        print(f"ERROR: {issue.format()}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
