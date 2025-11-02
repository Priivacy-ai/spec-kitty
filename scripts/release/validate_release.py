#!/usr/bin/env python3
"""Release readiness validator for Spec Kitty PyPI automation.

The script validates three core conditions before allowing a release:

1. The semantic version declared in pyproject.toml is well-formed.
2. CHANGELOG.md contains a populated section for the target version.
3. Version progression is monotonic relative to existing git tags and, in tag
   mode, matches the release tag that triggered the workflow.

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
from typing import Iterable, List, Optional, Sequence, Tuple

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for older interpreters
    import tomli as tomllib  # type: ignore


SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
CHANGELOG_HEADING_RE = re.compile(
    r"^##\s*(?:\[\s*)?(?P<version>\d+\.\d+\.\d+)(?:\s*\]|)(?:\s*-.*)?$"
)


@dataclass
class ValidationIssue:
    message: str
    hint: Optional[str] = None

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
    tag: Optional[str]
    issues: List[ValidationIssue] = field(default_factory=list)

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


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate release readiness for Spec Kitty PyPI automation"
    )
    parser.add_argument(
        "--mode",
        choices=("branch", "tag"),
        default="branch",
        help="Validation mode. 'branch' expects a version bump without a tag. "
        "'tag' enforces tag-version parity and monotonic progression.",
    )
    parser.add_argument(
        "--tag",
        help="Explicit tag (e.g., v1.2.3). Defaults to the detected GITHUB_REF or "
        "GITHUB_REF_NAME in tag mode.",
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
        "--fail-on-missing-tag",
        action="store_true",
        help="Treat missing tag detection as a hard failure (defaults to failure in tag mode).",
    )
    return parser.parse_args(argv)


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
    if not SEMVER_RE.match(version):
        raise ReleaseValidatorError(
            f"Version '{version}' is not a semantic version (expected X.Y.Z)."
        )
    return version


def read_changelog(path: Path) -> str:
    if not path.exists():
        raise ReleaseValidatorError(f"CHANGELOG not found at {path}.")
    return path.read_text(encoding="utf-8")


def changelog_has_entry(changelog: str, version: str) -> bool:
    lines = changelog.splitlines()
    capture = False
    content: List[str] = []
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


def git(*args: str, cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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


def discover_semver_tags(repo_root: Path, exclude: Optional[str] = None) -> List[str]:
    output = git("tag", "--list", "v*.*.*", cwd=repo_root)
    tags = [line.strip() for line in output.splitlines() if line.strip()]
    filtered = [tag for tag in tags if tag != exclude]
    filtered.sort(key=lambda tag: parse_semver(tag.lstrip("v")), reverse=True)
    return filtered


def parse_semver(value: str) -> Tuple[int, int, int]:
    match = SEMVER_RE.match(value)
    if not match:
        raise ReleaseValidatorError(
            f"Value '{value}' is not a valid semantic version (expected X.Y.Z)."
        )
    return tuple(int(part) for part in match.groups())


def detect_tag_from_env() -> Optional[str]:
    ref_name = os.getenv("GITHUB_REF_NAME")
    if ref_name and ref_name.startswith("v") and SEMVER_RE.match(ref_name[1:]):
        return ref_name
    ref = os.getenv("GITHUB_REF")
    if ref and ref.startswith("refs/tags/"):
        candidate = ref.rsplit("/", maxsplit=1)[-1]
        if candidate.startswith("v") and SEMVER_RE.match(candidate[1:]):
            return candidate
    return None


def validate_version_progression(
    current_version: str, existing_tags: Sequence[str]
) -> Optional[ValidationIssue]:
    if not existing_tags:
        return None
    current_tuple = parse_semver(current_version)
    latest_tuple = parse_semver(existing_tags[0].lstrip("v"))
    if current_tuple <= latest_tuple:
        return ValidationIssue(
            message=f"Version {current_version} does not advance beyond latest tag {existing_tags[0]}.",
            hint="Select a semantic version greater than previously published releases.",
        )
    return None


def ensure_tag_matches_version(version: str, tag: Optional[str]) -> Optional[ValidationIssue]:
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
    tag: Optional[str] = None
    issues: List[ValidationIssue] = []

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
                    hint="Use --tag vX.Y.Z or set GITHUB_REF_NAME when running in CI.",
                )
            )
        else:
            mismatch = ensure_tag_matches_version(version, tag)
            if mismatch:
                issues.append(mismatch)

        existing_tags = discover_semver_tags(repo_root, exclude=tag)
        progression_issue = validate_version_progression(version, existing_tags)
        if progression_issue:
            issues.append(progression_issue)
    else:
        existing_tags = discover_semver_tags(repo_root)
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


def main(argv: Optional[Sequence[str]] = None) -> int:
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
